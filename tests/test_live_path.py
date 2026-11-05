"""
The live path with valid answers, through the real SDKs over HTTP (no network):
Anthropic and Stripe talk to stand-ins, and Twilio's calls are captured. This
covers what mock mode can't: every agent actually using a model's answer, what
happens when the model invents numbers, and the owner's full text conversation.
It doesn't prove the real services accept these requests; scripts/live_check.py
does that once real keys are set.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import anthropic
import httpx2
import pytest
import stripe
from fastapi.testclient import TestClient

from src import runs as runs_module
from src.agents import fixtures
from src.agents.fee_hunter import classify_rules
from src.app import app, runs
from src.channels import twilio
from src.executor import actions
from src.finance import effective_rate
from src.llm import client as C
from src.llm.models import AGENTS, model_for
from src.runs import RunManager

FIXTURE = "fixture:statement_marios_trattoria_oct"
STATEMENT = fixtures.load("statement_marios_trattoria_oct")
THINKING = "Compared first-year dollars across the options."
GOOD_RATIONALE = "Hardball wins at 2.49%, worth $9,454 a year. Switching costs $11,090 up front and leaves her $316 behind."


def _sse(ev: str, data: dict) -> str:
    return f"event: {ev}\ndata: {json.dumps(data)}\n\n"


def _reply(body: dict, text: str, thinking: str | None = None, stop: str = "end_turn") -> httpx2.Response:
    """Answer in the shape the request asked for: a streamed event sequence or one JSON message."""
    usage = {"input_tokens": 1000, "output_tokens": 50, "cache_read_input_tokens": 400, "cache_creation_input_tokens": 0}
    if not body.get("stream"):
        content = ([{"type": "thinking", "thinking": thinking, "signature": "sig"}] if thinking else []) + [{"type": "text", "text": text}]
        return httpx2.Response(200, json={"id": "msg", "type": "message", "role": "assistant", "model": body["model"],
                                          "content": content, "stop_reason": stop, "stop_sequence": None, "usage": usage})
    parts = [_sse("message_start", {"type": "message_start", "message": {
        "id": "m", "type": "message", "role": "assistant", "model": body["model"], "content": [],
        "stop_reason": None, "stop_sequence": None, "usage": {**usage, "output_tokens": 1}}})]
    i = 0
    if thinking:
        parts += [
            _sse("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}}),
            _sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": thinking}}),
            _sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig"}}),
            _sse("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ]
        i = 1
    if text:
        parts += [
            _sse("content_block_start", {"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}}),
            *[_sse("content_block_delta", {"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": text[n:n + 40]}})
              for n in range(0, len(text), 40)],
            _sse("content_block_stop", {"type": "content_block_stop", "index": i}),
        ]
    parts += [_sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None}, "usage": {"output_tokens": 50}}),
              _sse("message_stop", {"type": "message_stop"})]
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content="".join(parts).encode())


def _parse_answer(statement: dict) -> dict:
    return {"merchant_name": statement["merchant"]["name"], "processor": statement["processor"],
            "period_label": statement["period"]["label"], "monthly_volume": statement["monthly_volume"],
            "transaction_count": statement["transaction_count"],
            "stated_total_fees": round(sum(li["amount"] for li in statement["line_items"]), 2),
            "line_items": [{k: li.get(k) for k in ("id", "description", "amount", "detail")} for li in statement["line_items"]]}


class FakeClaude:
    """Answers each agent the way a well-behaved model would. Tests override `answers` to misbehave."""

    def __init__(self, statement: dict | None = None) -> None:
        self.requests: list[dict] = []
        self.statement = statement or STATEMENT
        self.answers: dict[str, object] = {}

    def __call__(self, req: httpx2.Request) -> httpx2.Response:
        body = json.loads(req.content)
        self.requests.append(body)
        fmt = (body.get("output_config") or {}).get("format")
        if not fmt:
            return _reply(body, "LIVE-TURN Keystone already offered 2.49% last time. Interchange plus, please, and drop the junk fees.")
        props = fmt["schema"]["properties"]
        if "merchant_name" in props:
            return self._answer(body, "statement", _parse_answer(self.statement))
        if "items" in props:
            return self._answer(body, "fees", {"items": [
                {"id": li["id"], "category": li["category"], "tag": f"LIVE {li['tag']}", "reason": li["reason"]}
                for li in classify_rules(self.statement["line_items"])]})
        if "rationale" in props:
            return self._answer(body, "referee", {"rationale": GOOD_RATIONALE}, THINKING)
        if "redlines" in props:
            fx = fixtures.load("redlines")
            return self._answer(body, "redlines", {"redlines": [
                {"doc": doc, **r, "why": f"LIVE {r['why']}"} for doc in ("merchant_agreement", "mca_offer") for r in fx[doc]]}, THINKING)
        return self._answer(body, "email", {"subject": "LIVE accepting your offer", "body":
                            f"We accept interchange plus 0.25% and $0.08 per transaction. MID {STATEMENT['merchant']['mid']}."})

    def _answer(self, body: dict, key: str, default: dict, thinking: str | None = None) -> httpx2.Response:
        answer = self.answers.get(key, default)
        if answer == "refuse":
            return _reply(body, "", stop="refusal")
        return _reply(body, json.dumps(answer), thinking)

    def models_used(self) -> set[str]:
        return {r["model"] for r in self.requests}


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> FakeClaude:
    fake = FakeClaude()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    provider = C.AnthropicProvider()
    provider._client = anthropic.Anthropic(api_key="test", base_url="http://stand-in", max_retries=0,
                                           http_client=httpx2.Client(transport=httpx2.MockTransport(fake)))
    monkeypatch.setitem(C.PROVIDERS, "anthropic", provider)
    return fake


def _full_run(reply: str = "YES"):
    return RunManager().start(phone="+15550100", media=[FIXTURE], pace="instant", auto_approve=reply, background=False)


def _events(run, name: str) -> list[dict]:
    return [e for e in run.events if e["event"] == name]


def _notes(run) -> dict[str, str | None]:
    return {e["stage"]: e.get("note") for e in _events(run, "stage_done")}


def _owner_texts(run) -> list[str]:
    return [e["body"] for e in _events(run, "owner_message") if e["direction"] == "out"]


# ---------------------------------------------------------------- live requests
def test_slow_structured_calls_stream_so_they_cannot_hit_the_read_timeout(claude: FakeClaude) -> None:
    """A non-streamed Opus call sends no bytes until it finishes, so a long answer dies at the 90 s read timeout."""
    _full_run()
    structured = [r for r in claude.requests if (r.get("output_config") or {}).get("format")]
    assert structured and all(r.get("stream") is True for r in structured)


@pytest.mark.parametrize("agent", ["hardball", "diplomat", "processor_rep"])
def test_negotiators_leave_room_for_default_thinking(agent: str) -> None:
    """Sonnet and Haiku 5.5 think by default and thinking counts against max_tokens: a low cap cuts turns off mid-sentence."""
    assert model_for(agent).max_tokens >= 4000


# ---------------------------------------------------------------- a fully live run
def test_every_agent_uses_the_models_answer_and_the_money_stays_computed(claude: FakeClaude) -> None:
    run = _full_run()
    assert not _events(run, "error") and run.events[-1]["ok"] is True
    notes = _notes(run)
    assert notes["statement_reader"] == "live vision parse"
    assert notes["fee_hunter"] == "live classification"
    assert notes["negotiator"] == "live referee"
    assert notes["contract_exposer"] == "live redlines"
    assert notes["action_drafter"] == "live draft"

    # Each answer reached what the owner sees.
    assert all(f["tag"].startswith("LIVE ") for f in _events(run, "fee_flagged"))
    turns = "".join(e["delta"] for e in _events(run, "negotiation_turn"))
    assert "LIVE-TURN" in turns
    verdict = _events(run, "referee_verdict")[0]
    assert verdict["rationale"] == GOOD_RATIONALE and verdict["reasoning_summary"] == THINKING
    assert all(r["why"].startswith("LIVE ") for r in _events(run, "redline"))
    assert _events(run, "draft")[0]["subject"] == "LIVE accepting your offer"

    # The headline money still comes from the calculators.
    summary = _events(run, "summary")[0]
    assert summary["current_rate"] == pytest.approx(0.0328, abs=0.0001)
    assert summary["new_rate"] == pytest.approx(0.0249, abs=0.0001)
    assert summary["annual_savings"] == 9453.96
    assert summary["mca_apr"] == pytest.approx(0.9334, abs=0.001)

    # Requests use the models file and the statement goes as a document before the text.
    assert claude.models_used() == {a.model for a in AGENTS.values()}
    first = claude.requests[0]["messages"][0]["content"]
    assert first[0]["type"] == "document" and first[-1]["type"] == "text"
    assert first[0]["source"]["media_type"] == "application/pdf"

    costs = _events(run, "cost_log")
    assert {c["agent"] for c in costs} == set(AGENTS) and all(c["live"] for c in costs)
    assert costs[-1]["run_total_usd"] > 0


def test_invented_numbers_never_reach_the_owner(claude: FakeClaude) -> None:
    claude.answers["referee"] = {"rationale": "Hardball saves $99,999 a year at 0.10%."}
    claude.answers["email"] = {"subject": "Deal", "body": f"We accept 0.01% and $5.00 per transaction. MID {STATEMENT['merchant']['mid']}."}
    claude.answers["redlines"] = {"redlines": [{"doc": "mca_offer", "clause_key": "origination", "severity": "high", "revised": "No fee.", "why": "Costs you $123,456."}]}
    run = _full_run()
    everything = json.dumps(run.events)
    for invented in ("99,999", "0.10%", "$5.00", "123,456"):
        assert invented not in everything
    assert _events(run, "summary")[0]["annual_savings"] == 9453.96
    assert "live" not in (_notes(run)["negotiator"] or "")


def test_a_clause_the_documents_dont_contain_is_rejected(claude: FakeClaude) -> None:
    claude.answers["redlines"] = {"redlines": [{"doc": "mca_offer", "clause_key": "made_up_clause", "severity": "high", "revised": "x", "why": "y"}]}
    run = _full_run()
    assert not _events(run, "error")
    assert "made_up_clause" not in json.dumps(run.events) and len(_events(run, "redline")) == 12


@pytest.mark.parametrize("key,stage", [("statement", "statement_reader"), ("fees", "fee_hunter"), ("referee", "negotiator"),
                                       ("redlines", "contract_exposer"), ("email", "action_drafter")])
def test_a_refusal_degrades_to_the_fixture_and_the_run_finishes(claude: FakeClaude, key: str, stage: str) -> None:
    claude.answers[key] = "refuse"
    run = _full_run()
    assert not _events(run, "error") and run.events[-1]["ok"] is True
    assert not (_notes(run)[stage] or "").startswith("live")
    assert _events(run, "summary")[0]["annual_savings"] == 9453.96


def test_a_parse_that_doesnt_add_up_is_rejected(claude: FakeClaude) -> None:
    claude.answers["statement"] = {**_parse_answer(STATEMENT), "stated_total_fees": 1.00}
    assert _notes(_full_run())["statement_reader"] == "fixture parse (mock)"


# ---------------------------------------------------------------- a real owner, live
def _other_business() -> dict:
    st = copy.deepcopy(STATEMENT)
    st["merchant"]["name"], st["processor"] = "Bella's Bistro", "Acme Payments"
    st["monthly_volume"], st["transaction_count"] = 50000.0, 1000
    for li in st["line_items"]:
        li["amount"] = round(li["amount"] / 2, 2)
    return st


def test_a_real_owners_photo_gets_their_own_numbers_and_no_simulated_deal(claude: FakeClaude, tmp_path: Path) -> None:
    other = _other_business()
    claude.statement = other
    photo = tmp_path / "statement.jpg"
    photo.write_bytes(b"\xff\xd8\xff real photo bytes")
    run = RunManager().start(phone="+15550777", media=[f"file:{photo}"], pace="instant", channel="twilio", background=False)
    image = claude.requests[0]["messages"][0]["content"][0]
    assert image["type"] == "image" and image["source"]["media_type"] == "image/jpeg"
    assert base64.b64decode(image["source"]["data"]) == photo.read_bytes()
    assert len(claude.requests) == 2      # the reader and the fee hunter; nothing simulated after that
    text = _owner_texts(run)[-1]
    rate = effective_rate(sum(li["amount"] for li in other["line_items"]), other["monthly_volume"])
    assert f"{rate * 100:.2f}%" in text and "Acme Payments" in text and "haven't contacted" in text
    for fictional in ("Keystone", "FastFund", "Harbor", "Maria", "I got", "Reply YES"):
        assert fictional not in text


# ---------------------------------------------------------------- Stripe, through the real SDK
class _StripeStandIn(BaseHTTPRequestHandler):
    seen: list[dict] = []
    status = 200
    answer: dict = {}

    def do_POST(self) -> None:  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("content-length", 0))).decode()
        type(self).seen.append({"path": self.path, "form": parse_qs(raw), "headers": dict(self.headers)})
        data = json.dumps(type(self).answer).encode()
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def stripe_standin(monkeypatch: pytest.MonkeyPatch):
    handler = type("Handler", (_StripeStandIn,), {"seen": [], "status": 200, "answer":
                   {"id": "pi_test_123", "object": "payment_intent", "status": "succeeded", "livemode": False}})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    real = stripe.StripeClient
    monkeypatch.setattr(stripe, "StripeClient", lambda key: real(key, base_addresses={"api": f"http://127.0.0.1:{server.server_port}"}, max_network_retries=0))
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_standin")
    yield handler
    server.shutdown()


APPROVED = actions.Approval("apv_1", True, "YES")


def test_savings_sweep_makes_a_well_formed_test_mode_payment(stripe_standin) -> None:
    out = actions.savings_sweep(APPROVED, 787.83, "run1", "Mario's Trattoria")
    assert (out["provider"], out["ref"], out["sandbox"]) == ("stripe", "pi_test_123", True)
    assert out["detail"]["livemode"] is False and "Stripe test mode" in out["detail"]["note"]
    req = stripe_standin.seen[0]
    assert req["path"] == "/v1/payment_intents"
    assert req["form"]["amount"] == ["78783"] and req["form"]["currency"] == ["usd"] and req["form"]["confirm"] == ["true"]
    assert req["form"]["payment_method"] == ["pm_card_visa"]
    assert req["form"]["metadata[bucket]"] == [actions.RESERVE_LABEL]
    assert req["form"]["metadata[run_id]"] == ["run1"]
    headers = {k.lower(): v for k, v in req["headers"].items()}
    assert headers["authorization"] == "Bearer sk_test_standin" and headers["idempotency-key"] == "sweep-run1"


def test_a_failed_stripe_call_is_reported_as_what_actually_happened(stripe_standin) -> None:
    stripe_standin.status = 402
    stripe_standin.answer = {"error": {"type": "card_error", "code": "card_declined", "message": "Declined"}}
    out = actions.savings_sweep(APPROVED, 787.83, "run2", "Mario's Trattoria")
    assert out["provider"] == "mock" and out["detail"]["stripe_error"]
    assert "Stripe" not in out["detail"]["note"]


def test_owner_is_not_told_stripe_ran_when_it_failed(stripe_standin) -> None:
    stripe_standin.status = 402
    stripe_standin.answer = {"error": {"type": "card_error", "code": "card_declined", "message": "Declined"}}
    final = next(t for t in reversed(_owner_texts(_full_run())) if t.startswith("Done."))
    assert "Stripe" not in final


def test_owner_is_told_stripe_ran_when_it_did(stripe_standin) -> None:
    final = next(t for t in reversed(_owner_texts(_full_run())) if t.startswith("Done."))
    assert "Stripe test mode" in final


# ---------------------------------------------------------------- the owner's whole text conversation
def _sign(url: str, params: dict[str, str], token: str) -> str:
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()


class _Network:
    """Captures Twilio traffic. Nothing leaves the machine."""

    def __init__(self) -> None:
        self.calls: list = []

    def __call__(self, req, timeout=None):
        self.calls.append(req)

        class _Resp:
            @staticmethod
            def read() -> bytes:
                return b"\xff\xd8\xff photo bytes"
        return _Resp()

    def sms(self) -> list[dict]:
        out = []
        for r in self.calls:
            if r.full_url.endswith("/Messages.json"):
                out.append({k: v[0] for k, v in parse_qs(r.data.decode()).items()})
        return out


@pytest.fixture
def texting(monkeypatch: pytest.MonkeyPatch) -> _Network:
    net = _Network()
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACstandin")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15550000")
    monkeypatch.delenv("SHADOWBUYER_PUBLIC_URL", raising=False)
    monkeypatch.setattr(twilio.request, "urlopen", net)
    monkeypatch.setitem(runs_module.PACE_FACTOR, "fast", 0.0)
    return net


def _text(client: TestClient, **params: str):
    params = {"NumMedia": "0", **params}
    return client.post("/sms/twilio", data=params, headers={"X-Twilio-Signature": _sign("http://testserver/sms/twilio", params, "secret-token")})


def _wait(check, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return
        time.sleep(0.01)
    raise AssertionError("timed out")


def test_full_sms_conversation_demo_question_then_yes(texting: _Network) -> None:
    c, phone = TestClient(app), "+15550888"
    assert _text(c, From=phone, Body="DEMO").status_code == 200
    _wait(lambda: runs.latest_awaiting(phone, "twilio"))
    run = runs.latest_awaiting(phone, "twilio")
    assert any("Found $1,204" in s["Body"] for s in texting.sms())
    assert all(s["To"] == phone and s["From"] == "+15550000" for s in texting.sms())
    auth = texting.calls[0].get_header("Authorization")
    assert auth == "Basic " + base64.b64encode(b"ACstandin:secret-token").decode()
    assert texting.calls[0].full_url == "https://api.twilio.com/2010-04-01/Accounts/ACstandin/Messages.json"

    _text(c, From=phone, Body="what does this mean?")
    _wait(lambda: any("Nothing has moved yet" in s["Body"] for s in texting.sms()))
    assert run.awaiting and not _events(run, "action_executed")

    _text(c, From=phone, Body="yes please")
    _wait(lambda: run.finished)
    assert [e["action"] for e in _events(run, "action_executed")] == ["rep_email", "fee_receipt", "savings_sweep"]
    assert texting.sms()[-1]["Body"].startswith("Done.")


def test_photo_by_mms_is_fetched_with_auth_and_answered_honestly_without_claude(texting: _Network) -> None:
    c, phone = TestClient(app), "+15550999"
    _text(c, From=phone, Body="", NumMedia="1", MediaUrl0="https://api.twilio.com/media/abc", MediaContentType0="image/jpeg")
    _wait(lambda: any("couldn't read" in s["Body"] for s in texting.sms() if s["To"] == phone))
    media = next(r for r in texting.calls if r.full_url.endswith("/media/abc"))
    assert media.get_header("Authorization", "").startswith("Basic ")
    sent = [s["Body"] for s in texting.sms() if s["To"] == phone]
    assert not any("3.28%" in b or "FastFund" in b for b in sent)


# ---------------------------------------------------------------- memory, live
def test_second_live_run_tells_only_the_winning_negotiator_to_open_from_last_time(claude: FakeClaude) -> None:
    mgr = RunManager()
    mgr.start(phone="+15550100", media=[FIXTURE], pace="instant", auto_approve="NO", background=False)
    claude.requests.clear()
    mgr.start(phone="+15550100", media=[FIXTURE], pace="instant", auto_approve="NO", background=False)
    openers = {}
    for r in claude.requests:
        text = r["system"][-1]["text"]
        for lane in ("HARDBALL", "DIPLOMAT"):
            if f"You are {lane}" in text and "round 1 of 3" in r["messages"][0]["content"]:
                openers[lane] = text
    assert "already offered 2.49% all-in last time" in openers["HARDBALL"]
    assert "already offered" not in openers["DIPLOMAT"]
    # "settled" could be false: the owner may have said NO. An offer is what the records actually show.
    assert not any("settled" in json.dumps(r["messages"]) + r["system"][-1]["text"] for r in claude.requests)


def test_memory_says_which_processor_it_came_from(claude: FakeClaude) -> None:
    mgr = RunManager()
    mgr.start(phone="+15550100", media=[FIXTURE], pace="instant", auto_approve="NO", background=False)
    claude.requests.clear()
    mgr.start(phone="+15550100", media=[FIXTURE], pace="instant", auto_approve="NO", background=False)
    turn = next(r for r in claude.requests if "You are HARDBALL" in r["system"][-1]["text"])
    assert "your records for Keystone Merchant Services" in turn["messages"][0]["content"]


def test_negotiators_are_told_to_write_only_the_message(claude: FakeClaude) -> None:
    _full_run()
    streamed = [r for r in claude.requests if not (r.get("output_config") or {}).get("format")]
    assert streamed and all("no commentary" in r["system"][-1]["text"] for r in streamed)


def test_referee_sees_negative_money_written_normally(claude: FakeClaude) -> None:
    _full_run()
    table = next(r for r in claude.requests if "rationale" in json.dumps((r.get("output_config") or {}).get("format") or {}))
    text = table["messages"][0]["content"]
    assert "-$316.34" in text and "$-316" not in text
