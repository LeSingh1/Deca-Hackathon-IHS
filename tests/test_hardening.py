"""
Regressions found by driving the running app: path traversal, forged or
misrouted approvals, natural-language replies, malformed input, and never
showing fixture numbers as if they were a real owner's.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app import app, mount_ui
from src.runs import Run, RunManager

FIXTURE = "fixture:statement_marios_trattoria_oct"
PHONE = "+15550100"


def _await_gate(run: Run, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if run.awaiting:
            return
        time.sleep(0.01)
    raise AssertionError("run never reached the approval gate")


def _finish(run: Run, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if run.finished:
            return
        time.sleep(0.01)
    raise AssertionError("run never finished")


def _start(phone: str = PHONE, channel: str = "simulator", media: list[str] | None = None, mgr=None) -> Run:
    return (mgr or RunManager()).start(phone=phone, media=media or [FIXTURE], pace="instant", channel=channel)


def _actions(run: Run) -> list[str]:
    return [e["action"] for e in run.events if e["event"] == "action_executed"]


def _out_messages(run: Run) -> list[str]:
    return [e["body"] for e in run.events if e["event"] == "owner_message" and e["direction"] == "out"]


# ---------------------------------------------------------------- static files
@pytest.fixture
def ui_client(tmp_path: Path) -> TestClient:
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    dist = tmp_path / "public" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "favicon.svg").write_text("<svg/>")
    target = FastAPI()
    mount_ui(target, dist)
    return TestClient(target)


@pytest.mark.parametrize("path", ["/..%2f..%2fsecret.txt", "/%2e%2e/%2e%2e/secret.txt", "/assets/..%2f..%2f..%2fsecret.txt"])
def test_static_route_never_escapes_dist(ui_client: TestClient, path: str) -> None:
    assert "TOP-SECRET" not in ui_client.get(path).text


def test_static_route_still_serves_files_and_spa_fallback(ui_client: TestClient) -> None:
    assert ui_client.get("/favicon.svg").text == "<svg/>"
    assert "spa" in ui_client.get("/some/client/route").text


# ---------------------------------------------------------------- replies
@pytest.mark.parametrize("reply", ["YES", "yes!", "Yes please", "yep, do it", "ok go ahead", "lock it in", "sounds good, yes"])
def test_natural_yes_approves(reply: str) -> None:
    run = _start()
    _await_gate(run)
    assert run.receive_reply(reply)
    _finish(run)
    assert _actions(run) == ["rep_email", "fee_receipt", "savings_sweep"]


@pytest.mark.parametrize("reply", ["NO", "no thanks", "nope", "stop", "don't do it", "cancel"])
def test_natural_no_declines_and_moves_nothing(reply: str) -> None:
    run = _start()
    _await_gate(run)
    assert run.receive_reply(reply)
    _finish(run)
    assert _actions(run) == []
    assert _out_messages(run)[-1].startswith("No problem")


@pytest.mark.parametrize("reply", ["what does this mean?", "yes but not the email", "ok wait", "who is this", "not yes"])
def test_unclear_reply_keeps_gate_open_and_moves_nothing(reply: str) -> None:
    run = _start()
    _await_gate(run)
    assert run.receive_reply(reply)
    time.sleep(0.1)
    assert run.awaiting and not run.finished and _actions(run) == []
    assert "YES" in _out_messages(run)[-1] and "Nothing" in _out_messages(run)[-1]
    # the deal is still there: a clear YES afterwards goes through
    assert run.receive_reply("YES")
    _finish(run)
    assert _actions(run) == ["rep_email", "fee_receipt", "savings_sweep"]


def test_decision_is_final_once_made() -> None:
    run = Run(id="r1", phone=PHONE, pace="instant", channel="simulator", media=[])
    run.awaiting = "apv_r1"
    assert run.receive_reply("YES") is True
    assert run.receive_reply("NO") is False     # a late NO cannot flip a recorded YES
    assert run.approval is not None and run.approval.approved is True


# ---------------------------------------------------------------- approval routing
def _post_sim(c: TestClient, **body):
    return c.post("/api/sms/inbound", json=body)


def test_twilio_webhook_cannot_approve_a_simulator_run() -> None:
    c = TestClient(app)
    run_id = _post_sim(c, **{"from": "+15550111", "body": "statement", "pace": "instant"}).json()["run_id"]
    from src.app import runs
    run = runs.get(run_id)
    _await_gate(run)
    c.post("/sms/twilio", data={"From": "+15550111", "Body": "YES", "NumMedia": "0"})
    time.sleep(0.1)
    assert run.awaiting and _actions(run) == []
    run.receive_reply("NO")
    _finish(run)


def test_reply_goes_to_the_run_the_viewer_is_watching() -> None:
    """Two people on one public demo share the demo phone number."""
    c = TestClient(app)
    first = c.post("/api/demo/start", params={"pace": "instant"}).json()["run_id"]
    second = c.post("/api/demo/start", params={"pace": "instant"}).json()["run_id"]
    from src.app import runs
    a, b = runs.get(first), runs.get(second)
    _await_gate(a)
    _await_gate(b)
    r = _post_sim(c, **{"body": "YES", "run_id": first}).json()
    assert r["run_id"] == first
    _finish(a)
    assert _actions(a) and b.awaiting and not _actions(b)
    b.receive_reply("NO")
    _finish(b)


def test_simulator_reply_cannot_approve_a_run_on_another_channel() -> None:
    from src.app import runs
    run = runs.start(phone="+15550222", media=[FIXTURE], pace="instant", channel="twilio")
    _await_gate(run)
    c = TestClient(app)
    _post_sim(c, **{"from": "+15550222", "body": "YES"})
    r = _post_sim(c, **{"body": "YES", "run_id": run.id})
    assert r.status_code == 404
    time.sleep(0.1)
    assert run.awaiting and _actions(run) == []
    run.receive_reply("NO")
    _finish(run)


# ---------------------------------------------------------------- Twilio signature
def _sign(url: str, params: dict[str, str], token: str) -> str:
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()


@pytest.fixture
def twilio_live(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15550000")
    monkeypatch.delenv("SHADOWBUYER_PUBLIC_URL", raising=False)
    return "secret-token"


def test_live_twilio_webhook_rejects_unsigned_requests(twilio_live: str) -> None:
    r = TestClient(app).post("/sms/twilio", data={"From": "+15551", "Body": "hi", "NumMedia": "0"})
    assert r.status_code == 403


def test_live_twilio_webhook_rejects_wrong_signature(twilio_live: str) -> None:
    r = TestClient(app).post("/sms/twilio", data={"From": "+15551", "Body": "hi", "NumMedia": "0"},
                             headers={"X-Twilio-Signature": "AAAA"})
    assert r.status_code == 403


def test_live_twilio_webhook_accepts_valid_signature(twilio_live: str) -> None:
    params = {"From": "+15551", "Body": "hi", "NumMedia": "0"}
    sig = _sign("http://testserver/sms/twilio", params, twilio_live)
    r = TestClient(app).post("/sms/twilio", data=params, headers={"X-Twilio-Signature": sig})
    assert r.status_code == 200 and "<Message>" in r.text


def test_signature_uses_public_url_behind_a_proxy(twilio_live: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHADOWBUYER_PUBLIC_URL", "https://demo.example.com/")
    params = {"From": "+15551", "Body": "hi", "NumMedia": "0"}
    sig = _sign("https://demo.example.com/sms/twilio", params, twilio_live)
    assert TestClient(app).post("/sms/twilio", data=params, headers={"X-Twilio-Signature": sig}).status_code == 200


# ---------------------------------------------------------------- untrusted input
@pytest.mark.parametrize("media", ["file:/etc/hosts", "fixture:../../secrets", "https://evil.example/x.png"])
def test_simulator_rejects_media_other_than_the_demo_fixture(media: str) -> None:
    r = _post_sim(TestClient(app), **{"from": "+15550333", "body": "hi", "media": [media]})
    assert r.status_code == 400


def test_bad_event_cursor_is_not_a_server_error() -> None:
    c = TestClient(app, raise_server_exceptions=False)
    from src.app import runs
    r = runs.start(phone="+15550444", media=[FIXTURE], pace="instant", channel="simulator", auto_approve="NO", background=False)
    assert c.get(f"/api/runs/{r.id}/events", params={"from": "abc"}).status_code == 200


def test_bad_media_count_is_not_a_server_error() -> None:
    c = TestClient(app, raise_server_exceptions=False)
    assert c.post("/sms/twilio", data={"From": "+15552", "Body": "hi", "NumMedia": "abc"}).status_code == 200


# ---------------------------------------------------------------- honesty on real uploads
def test_unreadable_real_upload_never_shows_fixture_numbers(tmp_path: Path) -> None:
    photo = tmp_path / "statement.jpg"
    photo.write_bytes(b"\xff\xd8\xff not really a statement")
    run = RunManager().start(phone="+15550555", media=[f"file:{photo}"], pace="instant", channel="twilio",
                             auto_approve="YES", background=False)
    names = [e["event"] for e in run.events]
    assert "line_item" not in names and "approval_requested" not in names and "action_executed" not in names
    assert not any("3.28%" in b or "FastFund" in b for b in _out_messages(run))
    assert "couldn't read" in _out_messages(run)[-1]
    assert run.events[-1] == {**run.events[-1], "event": "done", "ok": False}


def test_run_started_does_not_name_the_fictional_owner_on_a_real_channel(tmp_path: Path) -> None:
    photo = tmp_path / "statement.jpg"
    photo.write_bytes(b"\xff\xd8\xff")
    run = RunManager().start(phone="+15550666", media=[f"file:{photo}"], pace="instant", channel="twilio",
                             auto_approve="NO", background=False)
    assert "Maria" not in str(run.events[0]["owner"])


# ---------------------------------------------------------------- memory
def test_second_run_negotiator_opens_from_what_won_last_time() -> None:
    def first_hardball_turn(run: Run) -> str:
        return "".join(e["delta"] for e in run.events if e["event"] == "negotiation_turn"
                       and e["lane"] == "hardball" and e["round"] == 1 and e["speaker"] == "hardball")

    mgr = RunManager()
    r1 = mgr.start(phone=PHONE, media=[FIXTURE], pace="instant", auto_approve="NO", background=False)
    assert "2.49%" not in first_hardball_turn(r1)
    r2 = mgr.start(phone=PHONE, media=[FIXTURE], pace="instant", auto_approve="NO", background=False)
    assert "2.49%" in first_hardball_turn(r2)
    # the money is unchanged: memory shapes the opening, never the calculators
    final = lambda r: [e for e in r.events if e["event"] == "summary"][0]["annual_savings"]  # noqa: E731
    assert final(r1) == final(r2)


# ---------------------------------------------------------------- sandbox labels
def test_mock_sweep_never_claims_to_be_stripe() -> None:
    run = RunManager().start(phone=PHONE, media=[FIXTURE], pace="instant", auto_approve="YES", background=False)
    request = [e for e in run.events if e["event"] == "approval_requested"][0]
    sweep = [e for e in run.events if e["event"] == "action_executed" and e["action"] == "savings_sweep"][0]
    assert sweep["provider"] == "mock"
    assert "Stripe" not in " ".join(_out_messages(run)) + str(request["actions"]) + str(sweep["detail"])


def test_sweep_rail_names_stripe_only_with_a_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.executor.actions import sweep_rail
    assert "Stripe" not in sweep_rail()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_nope")
    assert "Stripe" not in sweep_rail()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_ok")
    assert sweep_rail() == "Stripe test mode"


# ---------------------------------------------------------------- a real owner's statement
def _parsed_real_statement() -> dict:
    """A statement as the Statement Reader returns it for someone else's business."""
    import copy

    from src.agents import fixtures
    st = copy.deepcopy(fixtures.load("statement_marios_trattoria_oct"))
    st["merchant"]["name"] = "Bella's Bistro"
    st["processor"] = "Acme Payments"
    st["monthly_volume"] = 50000.0
    st["transaction_count"] = 1000
    for li in st["line_items"]:
        li["amount"] = round(li["amount"] / 2, 2)
    return st


def _real_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, statement: dict) -> Run:
    from src import pipeline
    monkeypatch.setattr(pipeline.statement_reader, "read", lambda media, llm: (statement, True))
    photo = tmp_path / "statement.jpg"
    photo.write_bytes(b"\xff\xd8\xff")
    return RunManager().start(phone="+15550777", media=[f"file:{photo}"], pace="instant", channel="twilio",
                              auto_approve="YES", background=False)


def test_real_statement_gets_only_what_was_actually_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from src.finance import effective_rate
    st = _parsed_real_statement()
    run = _real_run(monkeypatch, tmp_path, st)
    names = {e["event"] for e in run.events}
    # The negotiation is simulated and the agreement and advance are fictional, so none of it may reach a real owner.
    assert not names & {"negotiation_turn", "referee_verdict", "apr_revealed", "redline", "approval_requested", "action_executed"}
    text = _out_messages(run)[-1]
    rate = effective_rate(sum(li["amount"] for li in st["line_items"]), st["monthly_volume"])
    assert f"{rate * 100:.2f}%" in text and "Acme Payments" in text
    for fictional in ("Keystone", "FastFund", "Harbor", "Maria", "Mario", "I got", "Reply YES"):
        assert fictional not in text
    assert "haven't contacted" in text
    assert run.events[-1]["event"] == "done" and run.events[-1]["ok"] is True


def test_real_statement_already_near_fair_is_told_so(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    st = _parsed_real_statement()
    keep = [li for li in st["line_items"] if li["id"] in ("L01", "L02")]     # pass-through costs only
    st["line_items"] = keep
    text = _out_messages(_real_run(monkeypatch, tmp_path, st))[-1]
    assert "close to" in text and "/yr less" not in text


def test_live_check_script_reports_mock_without_keys(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY")}
    env["SHADOWBUYER_MEMORY_PATH"] = str(tmp_path / "m.json")
    ok = subprocess.run([sys.executable, "scripts/live_check.py"], cwd=root, env=env, capture_output=True, text=True)
    assert ok.returncode == 0 and "claude: mock" in ok.stdout and "$9,454" in ok.stdout
    strict = subprocess.run([sys.executable, "scripts/live_check.py", "--require-live"], cwd=root, env=env, capture_output=True, text=True)
    assert strict.returncode == 1
