"""
Provider-agnostic LLM client. Default provider: Anthropic Python SDK.

Mock-fallback contract
- No ANTHROPIC_API_KEY (or SHADOWBUYER_LLM=mock): every call returns None /
  yields nothing, and the calling agent uses its deterministic fixture.
- Any live failure (network, auth, refusal, schema mismatch after one retry)
  also returns None. The demo cannot crash because of the model.

Features used (per docs.claude.com, via the Claude API skill reference)
- Structured outputs: client.messages.stream(output_format=PydanticModel), read
  from get_final_message().parsed_output
- Streaming: client.messages.stream(...).text_stream for negotiator turns
- Prompt caching: the shared context (fee taxonomy, benchmarks, standard
  clauses) is the first system block with cache_control=ephemeral
- Adaptive thinking with display="summarized" for Referee/Contract Exposer;
  only the summary is surfaced in the UI, never raw reasoning
- Per-agent token + cost accounting via `usage`
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional, Protocol, TypeVar

from pydantic import BaseModel

from .models import AgentModel, cost_usd, model_for

T = TypeVar("T", bound=BaseModel)


@dataclass
class Usage:
    agent: str
    model: str
    live: bool
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def usd(self) -> float:
        if not self.live:
            return 0.0
        return cost_usd(self.model, self.input_tokens, self.output_tokens,
                        self.cache_read_tokens, self.cache_write_tokens)


@dataclass
class StructuredResult:
    value: Optional[BaseModel]
    usage: Usage
    thinking_summary: str = ""


class CostTracker:
    """Collects per-agent usage for one run; thread-safe."""

    def __init__(self, on_usage: Callable[[Usage, float], None] | None = None) -> None:
        self._lock = threading.Lock()
        self.entries: list[Usage] = []
        self.on_usage = on_usage

    def add(self, u: Usage) -> None:
        with self._lock:
            self.entries.append(u)
            total = self.total_usd
        if self.on_usage:
            self.on_usage(u, total)

    @property
    def total_usd(self) -> float:
        return round(sum(e.usd for e in self.entries), 6)


class Provider(Protocol):
    name: str

    def available(self) -> bool: ...

    def structured(self, cfg: AgentModel, system: list[dict], messages: list[dict],
                   schema: type[T]) -> tuple[Optional[T], Usage, str]: ...

    def stream(self, cfg: AgentModel, system: list[dict], messages: list[dict],
               usage_out: list[Usage]) -> Iterator[str]: ...


def _usage_from(resp_usage: Any, cfg: AgentModel) -> Usage:
    g = lambda k: int(getattr(resp_usage, k, 0) or 0)  # noqa: E731
    return Usage(
        agent=cfg.agent, model=cfg.model, live=True,
        input_tokens=g("input_tokens"), output_tokens=g("output_tokens"),
        cache_read_tokens=g("cache_read_input_tokens"),
        cache_write_tokens=g("cache_creation_input_tokens"),
    )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        self._client = None

    def available(self) -> bool:
        if os.getenv("SHADOWBUYER_LLM", "").lower() == "mock":
            return False
        if not os.getenv("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(timeout=90.0, max_retries=1)
        return self._client

    @staticmethod
    def _kwargs(cfg: AgentModel) -> dict[str, Any]:
        kw: dict[str, Any] = {"model": cfg.model, "max_tokens": cfg.max_tokens}
        if cfg.effort:
            kw["output_config"] = {"effort": cfg.effort}
        if cfg.show_thinking_summary:
            kw["thinking"] = {"type": "adaptive", "display": "summarized"}
        return kw

    def structured(self, cfg, system, messages, schema):
        # Streamed even though we only want the final message: a non-streamed call sends no
        # bytes until it finishes, so a long Opus answer would die at the client's read timeout.
        with self.client().messages.stream(
            system=system, messages=messages, output_format=schema, **self._kwargs(cfg)
        ) as s:
            resp = s.get_final_message()
        usage = _usage_from(resp.usage, cfg)
        if resp.stop_reason in ("refusal", "max_tokens"):
            return None, usage, ""
        summary = "\n".join(
            getattr(b, "thinking", "") for b in resp.content if getattr(b, "type", "") == "thinking"
        ).strip()
        return resp.parsed_output, usage, summary

    def stream(self, cfg, system, messages, usage_out):
        with self.client().messages.stream(system=system, messages=messages, **self._kwargs(cfg)) as s:
            for text in s.text_stream:
                yield text
            final = s.get_final_message()
            usage_out.append(_usage_from(final.usage, cfg))


PROVIDERS: dict[str, Provider] = {"anthropic": AnthropicProvider()}


def register_provider(provider: Provider) -> None:
    """Plug in another provider (e.g. a sponsor-required one) and point an
    agent at it via AgentModel.provider in src/llm/models.py."""
    PROVIDERS[provider.name] = provider


def _system_blocks(shared_context: str | None, instructions: str) -> list[dict]:
    blocks: list[dict] = []
    if shared_context:
        # Stable, shared prefix first so it can be cached across agents and runs.
        blocks.append({"type": "text", "text": shared_context, "cache_control": {"type": "ephemeral"}})
    blocks.append({"type": "text", "text": instructions})
    return blocks


@dataclass
class LLM:
    tracker: CostTracker = field(default_factory=CostTracker)

    def provider(self, agent: str) -> Provider | None:
        p = PROVIDERS.get(model_for(agent).provider)
        return p if p and p.available() else None

    def is_live(self, agent: str) -> bool:
        return self.provider(agent) is not None

    def mock_usage(self, agent: str) -> None:
        self.tracker.add(Usage(agent=agent, model=model_for(agent).model, live=False))

    def structured(self, agent: str, *, instructions: str, content: Any, schema: type[T],
                   shared_context: str | None = None,
                   validate: Callable[[T], bool] | None = None) -> StructuredResult:
        """Validated structured output, retried once, else value=None (caller falls back)."""
        cfg = model_for(agent)
        p = self.provider(agent)
        if p is None:
            u = Usage(agent=agent, model=cfg.model, live=False)
            self.tracker.add(u)
            return StructuredResult(None, u)
        messages = [{"role": "user", "content": content}]
        system = _system_blocks(shared_context, instructions)
        last = Usage(agent=agent, model=cfg.model, live=True)
        for _attempt in range(2):
            try:
                value, usage, summary = p.structured(cfg, system, messages, schema)
            except Exception:  # network/auth/schema — degrade to fixture
                continue
            last = usage
            self.tracker.add(usage)
            if value is not None and (validate is None or validate(value)):
                return StructuredResult(value, usage, summary)
        return StructuredResult(None, last)

    def stream(self, agent: str, *, instructions: str, messages: list[dict],
               shared_context: str | None = None) -> Iterator[str]:
        """Yield text deltas. Yields nothing in mock mode or if the call fails
        before the first token; the caller then streams its fixture text."""
        cfg = model_for(agent)
        p = self.provider(agent)
        if p is None:
            self.tracker.add(Usage(agent=agent, model=cfg.model, live=False))
            return
        usage_out: list[Usage] = []
        try:
            for chunk in p.stream(cfg, _system_blocks(shared_context, instructions), messages, usage_out):
                yield chunk
        except Exception:
            return
        finally:
            for u in usage_out:
                self.tracker.add(u)
