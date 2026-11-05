"""
The real AnthropicProvider, driven through the Anthropic SDK against a mock
HTTP transport (no network): request shape (model from models.py, effort,
adaptive thinking with summarized display, cache_control on shared context,
structured-output schema), response parsing, streaming, and cost accounting.
"""
from __future__ import annotations

import json

import anthropic
import httpx2
import pytest

from src.agents.fee_hunter import Classification
from src.agents.referee import RefereeOut
from src.llm import client as C
from src.llm.models import model_for


def _sse(ev: str, data: dict) -> str:
    return f"event: {ev}\ndata: {json.dumps(data)}\n\n"


class _Mock:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def __call__(self, req: httpx2.Request) -> httpx2.Response:
        body = json.loads(req.content)
        self.requests.append(body)
        if body.get("output_config", {}).get("format"):
            return self._structured(body)
        if body.get("stream"):
            parts = [
                _sse("message_start", {"type": "message_start", "message": {
                    "id": "m", "type": "message", "role": "assistant", "model": body["model"], "content": [],
                    "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 300, "output_tokens": 1}}}),
                _sse("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}),
                *[_sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": w}})
                  for w in ("Harbor quoted ", "IC+ 0.20%.")],
                _sse("content_block_stop", {"type": "content_block_stop", "index": 0}),
                _sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                       "usage": {"output_tokens": 12}}),
                _sse("message_stop", {"type": "message_stop"}),
            ]
            return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content="".join(parts).encode())
        raise AssertionError(f"unexpected non-streamed request: {sorted(body)}")

    @staticmethod
    def _structured(body: dict) -> httpx2.Response:
        assert body.get("stream") is True, "structured calls must stream"
        props = body["output_config"]["format"]["schema"]["properties"]
        payload = ({"rationale": "Hardball wins."} if "rationale" in props else
                   {"items": [{"id": "L01", "category": "interchange", "tag": "Interchange", "reason": "bank"}]})
        parts = [_sse("message_start", {"type": "message_start", "message": {
            "id": "msg", "type": "message", "role": "assistant", "model": body["model"], "content": [],
            "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 1200, "output_tokens": 1, "cache_read_input_tokens": 900, "cache_creation_input_tokens": 0}}})]
        i = 0
        if body.get("thinking"):
            parts += [
                _sse("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}}),
                _sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "Compared the options."}}),
                _sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig"}}),
                _sse("content_block_stop", {"type": "content_block_stop", "index": 0}),
            ]
            i = 1
        parts += [
            _sse("content_block_start", {"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}}),
            _sse("content_block_delta", {"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": json.dumps(payload)}}),
            _sse("content_block_stop", {"type": "content_block_stop", "index": i}),
            _sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 80}}),
            _sse("message_stop", {"type": "message_stop"}),
        ]
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content="".join(parts).encode())


@pytest.fixture
def mock(monkeypatch: pytest.MonkeyPatch) -> _Mock:
    m = _Mock()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    p = C.AnthropicProvider()
    p._client = anthropic.Anthropic(api_key="test", base_url="http://mock",
                                    http_client=httpx2.Client(transport=httpx2.MockTransport(m)))
    monkeypatch.setitem(C.PROVIDERS, "anthropic", p)
    return m


def test_structured_opus_request_and_parse(mock: _Mock) -> None:
    llm = C.LLM()
    r = llm.structured("referee", instructions="judge", content="options", schema=RefereeOut, shared_context="CTX")
    assert r.value is not None and r.value.rationale == "Hardball wins."  # type: ignore[attr-defined]
    assert r.thinking_summary == "Compared the options."
    body = mock.requests[-1]
    assert body["model"] == model_for("referee").model == "claude-opus-5-5"
    assert body["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert body["output_config"]["effort"] == "high" and body["output_config"]["format"]["type"] == "json_schema"
    assert body["system"][0] == {"type": "text", "text": "CTX", "cache_control": {"type": "ephemeral"}}
    assert r.usage.cache_read_tokens == 900 and r.usage.usd > 0


def test_structured_haiku_no_thinking_param(mock: _Mock) -> None:
    r = C.LLM().structured("fee_hunter", instructions="x", content="y", schema=Classification)
    assert r.value is not None
    body = mock.requests[-1]
    assert body["model"] == "claude-haiku-5-5" and "thinking" not in body and body["output_config"]["effort"] == "low"


def test_streaming_turn(mock: _Mock) -> None:
    llm = C.LLM()
    chunks = list(llm.stream("hardball", instructions="x", messages=[{"role": "user", "content": "go"}]))
    assert chunks == ["Harbor quoted ", "IC+ 0.20%."]
    assert mock.requests[-1]["model"] == "claude-sonnet-5-5" and mock.requests[-1]["stream"] is True
    u = llm.tracker.entries[-1]
    assert (u.agent, u.live, u.input_tokens, u.output_tokens) == ("hardball", True, 300, 12)
