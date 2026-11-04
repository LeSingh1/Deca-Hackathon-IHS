"""
Test-wide fixtures. Cleans the Evermind local fallback before every test so
write-count assertions are deterministic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_FALLBACK = Path(__file__).parent.parent / ".evermind-fallback.json"


@pytest.fixture(autouse=True)
def _clean_evermind_fallback() -> None:
    if _FALLBACK.exists():
        _FALLBACK.unlink()
    yield
    if _FALLBACK.exists():
        _FALLBACK.unlink()


@pytest.fixture(autouse=True)
def _strip_sponsor_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to the no-keys path. Tests that want fake keys set
    them explicitly via monkeypatch."""
    for var in [
        "TOKENROUTER_API_KEY",
        "TOKENROUTER_BASE_URL",
        "EVERMIND_API_KEY",
        "EVERMIND_BASE_URL",
        "NOSANA_ENDPOINT",
        "BRIGHTDATA_API_KEY",
        "QWEN_API_KEY",
        "ZAI_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)
