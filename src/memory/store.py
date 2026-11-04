"""
Persistent memory: a local JSON file (SHADOWBUYER_MEMORY_PATH, default
.shadowbuyer-memory.json). No external service.

Namespaces
  owner_profiles  keyed by owner phone   name, business, card volume
  statements      keyed by phone:period  effective rate + total fees
  decisions       keyed by run_id        referee verdict + approval outcome
  tactics         keyed by processor     which strategy won and at what rate

Next month's run reads `tactics` so the negotiator starts from what worked.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


def _path() -> Path:
    return Path(os.getenv("SHADOWBUYER_MEMORY_PATH", Path(__file__).resolve().parents[2] / ".shadowbuyer-memory.json"))


def _load() -> dict:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def write(ns: str, key: str, value: Any) -> None:
    with _LOCK:
        data = _load()
        data.setdefault(ns, {})[key] = {"value": value, "ts": time.time()}
        _path().write_text(json.dumps(data, indent=2, default=str))


def read(ns: str, key: str) -> Any | None:
    with _LOCK:
        entry = _load().get(ns, {}).get(key)
    return entry["value"] if entry else None
