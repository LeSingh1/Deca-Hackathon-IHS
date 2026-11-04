"""
TokenRouter client. ALL LLM calls route through this per sponsor requirement.

Live path: POSTs OpenAI-compatible chat/completions to TOKENROUTER_BASE_URL using
TOKENROUTER_API_KEY. Provider hint maps to a model id understood by TokenRouter
(default mapping below; override per-call via the explicit `model` argument).

Fallback path: returns a deterministic stub tagged with the provider so the
pipeline runs end-to-end with zero keys. ANY error in the live path (network,
auth, JSON shape, timeout) silently drops back to mock so the demo cannot crash.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal

try:
    import httpx  # type: ignore
except ImportError:
    httpx = None  # type: ignore

Provider = Literal["qwen", "zai", "openai"]

_DEFAULT_BASE_URL = "https://api.tokenrouter.io/v1"
_HTTP_TIMEOUT_S = 6.0  # tight: demo time budget is more important than a perfect response


@dataclass
class Completion:
    text: str
    provider: Provider
    model: str
    mocked: bool


def route(prompt: str, model: str, provider: Provider, max_tokens: int = 1024, system: str | None = None) -> Completion:
    api_key = os.getenv("TOKENROUTER_API_KEY")
    if not api_key or httpx is None:
        return _mock(prompt, model, provider)

    base = os.getenv("TOKENROUTER_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
    routed_model = _route_model(provider, model)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": routed_model, "messages": messages, "max_tokens": max_tokens},
            timeout=_HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip():
            return _mock(prompt, model, provider)
        return Completion(text=text, provider=provider, model=routed_model, mocked=False)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError):
        # Demo-cannot-crash contract: any live-path failure degrades to mock.
        return _mock(prompt, model, provider)


def _route_model(provider: Provider, model: str) -> str:
    """Map a provider hint + model name to TokenRouter's model id.

    Override the prefixes with env vars if TokenRouter's actual id convention
    differs from "{provider}/{model}" — common patterns:
      qwen/qwen3-max     ·  alibaba/qwen3-max
      zai/glm-5.1        ·  glm/glm-5.1
    """
    overrides = {
        "qwen": os.getenv("TOKENROUTER_QWEN_PREFIX", "qwen"),
        "zai": os.getenv("TOKENROUTER_ZAI_PREFIX", "zai"),
        "openai": os.getenv("TOKENROUTER_OPENAI_PREFIX", "openai"),
    }
    prefix = overrides.get(provider, provider)
    return f"{prefix}/{model}" if "/" not in model else model


def _mock(prompt: str, model: str, provider: Provider) -> Completion:
    snippet = prompt.strip().split("\n", 1)[0][:120]
    return Completion(
        text=f"[MOCK {provider}/{model}] would respond to: {snippet}",
        provider=provider,
        model=model,
        mocked=True,
    )
