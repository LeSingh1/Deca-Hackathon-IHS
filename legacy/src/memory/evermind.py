"""
Evermind persistent memory adapter.

Live path: POSTs to EVERMIND_BASE_URL using EVERMIND_API_KEY.
  PUT  /v1/namespaces/{namespace}/keys/{key}   body: {value, metadata}
  GET  /v1/namespaces/{namespace}/keys/{key}   returns: {value, metadata}
Override the path shape with EVERMIND_PATH_TEMPLATE if Person B's wiring differs.

Fallback path: JSON file at .evermind-fallback.json (gitignored) so the demo
runs deterministically with zero keys.

ANY live-path error (auth, network, shape) drops to local fallback silently.

Four record types the doc calls out:
  - vendor_profiles  · keyed by vendor name        (Scout output, "the moat" minus trash-talk)
  - ae_quotes        · keyed by vendor name        (Quote Hunter output)
  - trash_talk       · keyed by vendor name        (competitor digs — separate so they can be queried as intel)
  - decisions        · keyed by ISO timestamp      (Referee verdicts, full audit trail)
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx  # type: ignore
except ImportError:
    httpx = None  # type: ignore

_LOCAL_STORE = Path(__file__).parent.parent.parent / ".evermind-fallback.json"
_HTTP_TIMEOUT_S = 4.0


@dataclass
class WriteResult:
    ok: bool
    backend: str          # "evermind" | "local"
    namespace: str
    key: str


def write(namespace: str, key: str, value: Any, metadata: dict[str, Any] | None = None) -> WriteResult:
    """Try live Evermind first; on any failure, write to local JSON store."""
    if _live_available():
        try:
            _live_write(namespace, key, value, metadata or {})
            # Mirror to local as defense in depth — read() prefers live but local is a fallback.
            _local_write(namespace, key, value, metadata or {})
            return WriteResult(ok=True, backend="evermind", namespace=namespace, key=key)
        except Exception:
            pass
    _local_write(namespace, key, value, metadata or {})
    return WriteResult(ok=True, backend="local", namespace=namespace, key=key)


def read(namespace: str, key: str) -> Any | None:
    if _live_available():
        try:
            return _live_read(namespace, key)
        except Exception:
            pass
    return _local_read(namespace, key)


def write_vendor_profile(vendor: str, profile: dict[str, Any]) -> WriteResult:
    return write("vendor_profiles", vendor, profile, {"recorded_at": _now_iso()})


def write_ae_quote(vendor: str, quote: dict[str, Any]) -> WriteResult:
    return write("ae_quotes", vendor, quote, {"recorded_at": _now_iso()})


def write_trash_talk(vendor: str, dig: str, targets: list[str]) -> WriteResult:
    """Vendors who trash-talk competitors — the doc calls this 'the moat.'

    Each entry records the speaking vendor, the quote, and which competitors
    they named. Future Scout runs can query this to surface "vendors who
    consistently disparage their competitors" patterns.
    """
    record = {"vendor": vendor, "dig": dig, "targets": targets}
    return write("trash_talk", vendor, record, {"recorded_at": _now_iso()})


def write_decision(decision_id: str, decision: dict[str, Any]) -> WriteResult:
    return write("decisions", decision_id, decision, {"recorded_at": _now_iso()})


def _live_available() -> bool:
    return bool(os.getenv("EVERMIND_API_KEY")) and httpx is not None


def _live_write(namespace: str, key: str, value: Any, metadata: dict[str, Any]) -> None:
    base = os.getenv("EVERMIND_BASE_URL", "https://api.evermind.ai").rstrip("/")
    template = os.getenv("EVERMIND_PATH_TEMPLATE", "/v1/namespaces/{namespace}/keys/{key}")
    url = base + template.format(namespace=namespace, key=key)
    r = httpx.put(
        url,
        headers={"Authorization": f"Bearer {os.environ['EVERMIND_API_KEY']}", "Content-Type": "application/json"},
        json={"value": value, "metadata": metadata},
        timeout=_HTTP_TIMEOUT_S,
    )
    r.raise_for_status()


def _live_read(namespace: str, key: str) -> Any | None:
    base = os.getenv("EVERMIND_BASE_URL", "https://api.evermind.ai").rstrip("/")
    template = os.getenv("EVERMIND_PATH_TEMPLATE", "/v1/namespaces/{namespace}/keys/{key}")
    url = base + template.format(namespace=namespace, key=key)
    r = httpx.get(
        url,
        headers={"Authorization": f"Bearer {os.environ['EVERMIND_API_KEY']}"},
        timeout=_HTTP_TIMEOUT_S,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json().get("value")


def _load() -> dict:
    if not _LOCAL_STORE.exists():
        return {}
    try:
        return json.loads(_LOCAL_STORE.read_text())
    except json.JSONDecodeError:
        return {}


def _local_write(namespace: str, key: str, value: Any, metadata: dict[str, Any]) -> bool:
    data = _load()
    data.setdefault(namespace, {})[key] = {"value": value, "metadata": metadata, "ts": time.time()}
    _LOCAL_STORE.write_text(json.dumps(data, indent=2, default=str))
    return True


def _local_read(namespace: str, key: str) -> Any | None:
    entry = _load().get(namespace, {}).get(key)
    return entry["value"] if entry else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
