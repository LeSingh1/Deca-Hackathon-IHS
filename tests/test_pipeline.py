"""
End-to-end pipeline on mocks, the approval gate, live-model routing, and the API.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from src.agents import fixtures
from src.executor import actions
from src.finance import (PricingPlan, StatementProfile, annual_savings, early_termination_cost,
                         effective_rate, mca_true_apr, net_switch_benefit, plan_monthly_cost)
from src.llm import client as llm_client
from src.llm.guard import numbers_ok
from src.llm.models import AGENTS, model_for
from src.runs import RunManager


def _run(reply: str = "YES"):
    return RunManager().start(phone="+15550100", media=["fixture:statement_marios_trattoria_oct"],
                              pace="instant", auto_approve=reply, background=False)


def _one(run, name):
    evs = [e for e in run.events if e["event"] == name]
    assert len(evs) == 1, f"expected one {name}, got {len(evs)}"
    return evs[0]


# ---------------------------------------------------------------- zero env vars
def test_zero_env_full_run_numbers_match_calculators() -> None:
    run = _run()
    names = [e["event"] for e in run.events]
    assert names[0] == "run_started" and names[-1] == "done"
    assert "error" not in names
    assert set(_one(run, "run_started")["services"].values()) == {"mock"}

    # Recompute every headline number straight from the fixtures + calculators.
    st = fixtures.load("statement_marios_trattoria_oct")
    total = round(sum(li["amount"] for li in st["line_items"]), 2)
    cur = effective_rate(total, st["monthly_volume"])
    profile = StatementProfile(st["monthly_volume"], st["transaction_count"], 1862.40, 141.30, 69.95)
    hb = fixtures.load("negotiation")["ladder"]["hardball"][2]
    new_cost = plan_monthly_cost(PricingPlan(label="hb", markup_pct=hb["markup_pct"], per_txn=hb["per_txn"]), profile)
    new = effective_rate(new_cost, st["monthly_volume"])
    annual = annual_savings(cur, new, st["monthly_volume"] * 12)
    offer = fixtures.load("mca_offer_fastfund")
    apr = mca_true_apr(offer["advance"], offer["factor_rate"], offer["holdback_pct"],
                       st["monthly_volume"] * 12 / 365, offer["origination_fee"]).apr

    s = _one(run, "summary")
    assert s["current_rate"] == pytest.approx(cur)
    assert s["new_rate"] == pytest.approx(new)
    assert s["annual_savings"] == annual == 9453.96
    assert s["monthly_savings"] == 787.83
    assert s["hidden_fees_monthly"] == 1203.75
    assert s["mca_apr"] == pytest.approx(apr)
    assert s["headline"] == "3.28% → 2.49% = $9,454/yr back"

    rc = _one(run, "rate_computed")
    assert rc["total_fees"] == total == 3277.40
    flagged = [e for e in run.events if e["event"] == "fee_flagged"]
    assert flagged[-1]["hidden_total"] == 1203.75
    assert any(f["tag"] == "PCI non-compliance" and f["amount"] == 39.95 for f in flagged)

    v = _one(run, "referee_verdict")
    assert v["winner"] == "hardball"
    sw = next(o for o in v["options"] if o["key"] == "switch")
    agreement = fixtures.load("merchant_agreement")
    exit_cost = early_termination_cost({**agreement["terms"], "avg_monthly_processor_fees": 1203.75},
                                       agreement["months_remaining"]).total
    assert sw["one_time_costs"] == exit_cost == 11089.70
    assert sw["net_first_year"] == net_switch_benefit(897.78, exit_cost).net_first_year

    a = _one(run, "apr_revealed")
    assert a["apr"] == pytest.approx(apr) and a["term_days"] == 274
    risk = {r["clause_key"]: r["dollars_at_risk"] for r in run.events if r["event"] == "redline"}
    assert risk["liquidated_damages"] == 8426.25 and risk["purchase_price"] == 15200.0

    # The SMS headline quotes exactly the calculator numbers.
    sms = [e["body"] for e in run.events if e["event"] == "owner_message" and e["direction"] == "out"]
    summary_sms = next(b for b in sms if "Reply YES" in b)
    assert "$1,204/mo" in summary_sms and "3.28%" in summary_sms and "~93% APR" in summary_sms
    assert "2.49%" in summary_sms and "$9,454/yr" in summary_sms and "($788)" in summary_sms

    led = _one(run, "ledger_update")
    assert led["back_in_pocket_annual"] == 9453.96


def test_mock_negotiation_scripts_agree_with_ladder() -> None:
    neg = fixtures.load("negotiation")
    for lane in ("hardball", "diplomat"):
        for step, text in zip(neg["ladder"][lane], neg["scripts"][f"rep_{lane}"]):
            assert f"{step['markup_pct'] * 100:.2f}%" in text
    run = _run()
    turns = [e for e in run.events if e["event"] == "negotiation_turn"]
    offers = [e["offer"] for e in turns if e.get("offer")]
    assert len(offers) == 6
    assert {e["lane"] for e in turns} == {"hardball", "diplomat"}
    assert {e["speaker"] for e in turns} == {"hardball", "diplomat", "rep"}


# ---------------------------------------------------------------- approval gate
def test_no_action_before_approval_and_none_on_no() -> None:
    run = _run("YES")
    seq = {e["event"]: e["seq"] for e in run.events}
    approved = _one(run, "approval_received")
    assert approved["approved"] is True
    for e in run.events:
        if e["event"] == "action_executed":
            assert e["seq"] > approved["seq"] and e["sandbox"] is True
    assert seq["approval_requested"] < seq["approval_received"]

    declined = _run("NO")
    assert _one(declined, "approval_received")["approved"] is False
    assert not [e for e in declined.events if e["event"] in ("action_executed", "ledger_update")]


def test_executor_refuses_without_approval() -> None:
    with pytest.raises(actions.ApprovalRequired):
        actions.savings_sweep(None, 10.0, "r", "m")
    with pytest.raises(actions.ApprovalRequired):
        actions.rep_email(actions.Approval("a", False, "NO"), {"to": "x", "subject": "y"})


def test_stripe_refuses_live_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    assert actions.stripe_mode() == "mock"
    r = actions.savings_sweep(actions.Approval("a", True, "YES"), 787.83, "run1", "Mario's")
    assert r["provider"] == "mock" and r["sandbox"] is True
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    assert actions.stripe_mode() == "live"


# ---------------------------------------------------------------- memory
def test_second_run_starts_smarter() -> None:
    _run()
    second = _run()
    neg_stage = next(e for e in second.events if e["event"] == "stage_start" and e["stage"] == "negotiator")
    assert "last time hardball won" in neg_stage["label"]


# ---------------------------------------------------------------- live routing
class _RecordingProvider:
    """Stands in for the Anthropic API: records which model each agent asked for,
    returns nothing so every agent must fall back to its fixture."""
    name = "anthropic"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def available(self) -> bool:
        return True

    def structured(self, cfg, system, messages, schema):
        self.calls.append((cfg.agent, cfg.model))
        assert system[-1]["type"] == "text"
        return None, llm_client.Usage(cfg.agent, cfg.model, True, 100, 10), ""

    def stream(self, cfg, system, messages, usage_out):
        self.calls.append((cfg.agent, cfg.model))
        usage_out.append(llm_client.Usage(cfg.agent, cfg.model, True, 50, 5))
        return iter(())


def test_live_mode_uses_models_file(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _RecordingProvider()
    monkeypatch.setitem(llm_client.PROVIDERS, "anthropic", fake)
    run = _run()
    called = dict(fake.calls)
    assert set(called) == set(AGENTS), f"agents not called live: {set(AGENTS) - set(called)}"
    for agent, model in called.items():
        assert model == model_for(agent).model == AGENTS[agent].model
    assert called["referee"] == "claude-opus-5-5" and called["contract_exposer"] == "claude-opus-5-5"
    assert called["fee_hunter"] == "claude-haiku-5-5" and called["processor_rep"] == "claude-haiku-5-5"
    assert called["statement_reader"] == "claude-sonnet-5-5" and called["hardball"] == "claude-sonnet-5-5"
    # Live failures still produce the exact mock numbers.
    assert _one(run, "summary")["annual_savings"] == 9453.96
    costs = [e for e in run.events if e["event"] == "cost_log"]
    assert costs and all(c["live"] for c in costs) and costs[-1]["run_total_usd"] > 0


def test_fable_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHADOWBUYER_USE_FABLE", "1")
    assert model_for("referee").model == "claude-fable-5-1"
    assert model_for("fee_hunter").model == "claude-haiku-5-5"


def test_number_guard() -> None:
    assert numbers_ok("Saves $9,454 a year at 2.49%", [9453.96], [2.49])
    assert numbers_ok("about $9.5K", [9453.96], [])
    assert not numbers_ok("Saves $12,000 a year", [9453.96], [])
    assert not numbers_ok("only 1.9%", [], [2.49])


# ---------------------------------------------------------------- API
def test_api_simulator_flow() -> None:
    from src.app import app
    c = TestClient(app)
    h = c.get("/healthz").json()
    assert h["ok"] and set(h["services"]) == {"claude", "stripe", "twilio"}
    r = c.post("/api/demo/start", params={"pace": "instant"}).json()
    run_id = r["run_id"]
    for _ in range(100):
        snap = c.get(f"/api/runs/{run_id}").json()
        if snap["awaiting"]:
            break
        time.sleep(0.05)
    assert snap["awaiting"], "run never reached the approval gate"
    assert not [e for e in snap["events"] if e["event"] == "action_executed"]
    rep = c.post("/api/sms/inbound", json={"from": "+1 (718) 555-0142", "body": "yes"}).json()
    assert rep["kind"] == "reply" and rep["run_id"] == run_id
    with c.stream("GET", f"/api/runs/{run_id}/events") as s:
        events = [json.loads(line[6:]) for line in s.iter_lines() if line.startswith("data: ")]
    assert events[-1]["event"] == "done"
    assert [e["seq"] for e in events] == list(range(len(events)))
    pdf = c.get(f"/api/runs/{run_id}/report.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_twilio_webhook_help_text() -> None:
    from src.app import app
    r = TestClient(app).post("/sms/twilio", data={"From": "+15551112222", "Body": "hi", "NumMedia": "0"})
    assert r.status_code == 200 and "<Message>" in r.text
