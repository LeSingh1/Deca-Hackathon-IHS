"""
Pre-demo smoke tests. Each assertion maps to a demo-day failure mode.

Run: pytest -q
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src import pipeline
from src.agents import contract_diff, email_drafter, negotiator, quote_hunter, scout
from src.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# 1) /healthz returns OK
def test_healthz_ok(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "shadowbuyer"
    assert "services" in body and isinstance(body["services"], dict)


# 2) Full pipeline runs with no env vars
def test_pipeline_runs_with_no_env() -> None:
    out = pipeline.run()
    # Every stage present.
    for stage in ("scout", "quote_hunter", "negotiator", "contract_diff", "evermind_writes", "summary"):
        assert stage in out, f"missing stage: {stage}"
    # Negotiator produces 6 negotiation turns + 1 referee turn.
    assert len(out["negotiator"]["turns"]) == 7
    # Summary math sane.
    s = out["summary"]
    assert s["ok"] is True
    assert s["vendor"] == "Datadog"
    assert s["competing_vendor"] == "New Relic"
    assert s["final_price_per_host_mo"] < s["list_price_per_host_mo"]
    assert s["annual_savings_vs_list_usd"] > 0
    assert s["winning_strategy"] in ("hardball", "diplomat")
    # Evermind writes happen even with no keys (local fallback).
    assert s["evermind_writes"] >= 8
    assert s["evermind_backend_counts"].get("local", 0) == s["evermind_writes"]


# 3) Pipeline runs with FAKE env vars and falls back cleanly to mock
def test_pipeline_falls_back_with_fake_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    # Point both adapters at totally unreachable hosts so the HTTP attempts fail fast.
    monkeypatch.setenv("TOKENROUTER_API_KEY", "fake-test-key")
    monkeypatch.setenv("TOKENROUTER_BASE_URL", "http://127.0.0.1:9/v1")  # closed port
    monkeypatch.setenv("EVERMIND_API_KEY", "fake-test-key")
    monkeypatch.setenv("EVERMIND_BASE_URL", "http://127.0.0.1:9")

    out = pipeline.run()

    # Pipeline didn't crash; produced identical structural output to the no-env path.
    assert len(out["negotiator"]["turns"]) == 7
    assert out["summary"]["ok"] is True
    assert out["contract_diff"]["redline_count"] >= 14
    # Negotiator turns must still be marked mocked because TokenRouter call failed.
    for turn in out["negotiator"]["turns"]:
        assert turn["mocked"] is True, f"expected mock fallback after live failure, got live in {turn}"
    # Evermind writes still landed via local fallback (live PUT failed silently).
    backends = out["summary"]["evermind_backend_counts"]
    assert backends.get("local", 0) > 0


# 4) Contract Diff: 15 redlines, with the two doc-pitch beats flagged high
def test_contract_diff_pitch_beats() -> None:
    out = contract_diff.run()
    # Doc pitch line says "14 deviations" — we exceed that with 15. Either is acceptable.
    assert out["redline_count"] >= 14
    keys = {r["clause_key"]: r for r in out["redlines"]}

    # Auto-renewal trap — high severity, the doc explicitly names this.
    assert "auto_renewal" in keys, "auto-renewal clause must be flagged"
    assert keys["auto_renewal"]["severity"] == "high"

    # Missing data-deletion clause — high severity, also doc-named.
    assert "data_deletion" in keys, "data-deletion clause must be flagged as missing"
    assert keys["data_deletion"]["severity"] == "high"
    assert keys["data_deletion"]["vendor_text"] == "(missing from vendor MSA)"

    # Severity counts populated; at least a few "high" items so the demo card has weight.
    sev = out["severity_counts"]
    assert sev["high"] >= 5
    assert sum(sev.values()) == out["redline_count"]


# 5) Email drafter produces a complete AE email using the winning strategy
def test_email_drafter_complete() -> None:
    s = scout.run("observability")
    q = quote_hunter.run(s["vendors"])
    n = negotiator.run(q["quotes"])
    em = email_drafter.to_dict(email_drafter.draft(n, q["quotes"][0], q["quotes"][1]))

    # Required fields populated.
    for field in ("to", "from", "subject", "body", "strategy", "cites", "dry_run"):
        assert field in em, f"missing field: {field}"
        assert em[field] != ""

    # Strategy matches what the referee picked.
    assert em["strategy"] == n["winner"]
    assert em["strategy"] in ("hardball", "diplomat")

    # Email is addressed to the target AE, not a generic placeholder.
    assert em["to"] == q["quotes"][0]["ae_email"]

    # Body cites concrete numbers from the negotiation (final price and term).
    assert f"${n['final_price_per_host_mo']:.2f}" in em["body"]
    # And at least one cite carries the final price for downstream rendering.
    assert any("final_price" in c for c in em["cites"])

    # Dry-run: never actually delivered.
    assert em["dry_run"] is True


# 6) /api/sponsor-health returns all 11 sponsors with env_status
def test_sponsor_health_eleven(client: TestClient) -> None:
    r = client.get("/api/sponsor-health")
    assert r.status_code == 200
    body = r.json()
    assert body["all_eleven_wired"] is True
    assert body["total"] == 11
    assert len(body["sponsors"]) == 11

    names = {s["name"] for s in body["sponsors"]}
    expected = {
        "AgentField", "TokenRouter", "Qwen Cloud", "Z.ai",
        "Evermind", "Nosana", "Bright Data", "Actionbook",
        "Zeabur", "Qoder", "Butterbase",
    }
    assert names == expected, f"missing or extra sponsors: {names ^ expected}"

    # Every sponsor row carries env_status, owner, code_ref.
    for s in body["sponsors"]:
        assert s["env_status"] in ("live", "mock", "n/a")
        assert s["owner"]
        assert s["code_ref"]
