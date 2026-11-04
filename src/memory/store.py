"""
Persistent memory, same interface as the original Evermind adapter.

Live: EVERMIND_API_KEY set -> PUT/GET {EVERMIND_BASE_URL}/v1/namespaces/{ns}/keys/{key}
Fallback: local JSON file (SHADOWBUYER_MEMORY_PATH, default .shadowbuyer-memory.json).
Any live error falls back to local silently.

Namespaces
  owner_profiles  keyed by owner phone   name, business, card volume
  statements      keyed by phone:period  parsed line items + effective rate
  decisions       keyed by run_id        referee verdict + approval outcome
  tactics         keyed by processor     which strategy won and at what rate
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request as _rq

_LOCK = threading.Lock()


def _path() -> Path:
    return Path(os.getenv("SHADOWBUYER_MEMORY_PATH", Path(__file__).resolve().parents[2] / ".shadowbuyer-memory.json"))


@dataclass
class WriteResult:
    ok: bool
    backend: str      # "evermind" | "local"
    namespace: str
    key: str


def backend_mode() -> str:
    return "live" if os.getenv("EVERMIND_API_KEY") else "mock"


def _url(ns: str, key: str) -> str:
    base = os.getenv("EVERMIND_BASE_URL", "https://api.evermind.ai").rstrip("/")
    return f"{base}/v1/namespaces/{ns}/keys/{key}"


def _live_put(ns: str, key: str, value: Any) -> None:
    req = _rq.Request(_url(ns, key), method="PUT", data=json.dumps({"value": value}, default=str).encode(),
                      headers={"Authorization": f"Bearer {os.environ['EVERMIND_API_KEY']}",
                               "Content-Type": "application/json"})
    _rq.urlopen(req, timeout=4).read()


def _live_get(ns: str, key: str) -> Any:
    req = _rq.Request(_url(ns, key), headers={"Authorization": f"Bearer {os.environ['EVERMIND_API_KEY']}"})
    return json.loads(_rq.urlopen(req, timeout=4).read()).get("value")


def _load() -> dict:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def write(ns: str, key: str, value: Any) -> WriteResult:
    backend = "local"
    if backend_mode() == "live":
        try:
            _live_put(ns, key, value)
            backend = "evermind"
        except Exception:
            pass
    with _LOCK:
        data = _load()
        data.setdefault(ns, {})[key] = {"value": value, "ts": time.time()}
        _path().write_text(json.dumps(data, indent=2, default=str))
    return WriteResult(True, backend, ns, key)


def read(ns: str, key: str) -> Any | None:
    if backend_mode() == "live":
        try:
            v = _live_get(ns, key)
            if v is not None:
                return v
        except Exception:
            pass
    with _LOCK:
        entry = _load().get(ns, {}).get(key)
    return entry["value"] if entry else None
