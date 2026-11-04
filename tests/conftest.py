"""Every test starts on the zero-env-var path with an isolated memory file."""
from __future__ import annotations

import pytest

LIVE_VARS = [
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "SHADOWBUYER_LLM", "SHADOWBUYER_USE_FABLE",
    "STRIPE_SECRET_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER",
    "EVERMIND_API_KEY", "EVERMIND_BASE_URL",
]


@pytest.fixture(autouse=True)
def _zero_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for v in LIVE_VARS:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("SHADOWBUYER_MEMORY_PATH", str(tmp_path / "memory.json"))
    monkeypatch.setenv("SHADOWBUYER_APPROVAL_TIMEOUT_S", "5")
