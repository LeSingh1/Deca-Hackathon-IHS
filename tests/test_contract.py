"""
The SSE contract is frozen: Python models and the TS mirror must agree.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src import contract

TS = (Path(__file__).parent.parent / "frontend" / "src" / "lib" / "contract.ts").read_text()


def _ts_event_types() -> list[str]:
    block = re.search(r"EVENT_TYPES = \[(.*?)\] as const", TS, re.S)
    assert block, "EVENT_TYPES missing from contract.ts"
    return re.findall(r'"(\w+)"', block.group(1))


def _ts_interfaces() -> dict[str, set[str]]:
    """event name -> field names, for every `interface X extends EventBase`."""
    out: dict[str, set[str]] = {}
    for body in re.findall(r"interface \w+ extends EventBase \{(.*?)\n\}", TS, re.S):
        fields = set(re.findall(r"^\s+(\w+)\??:", body, re.M))
        name = re.search(r'event: "(\w+)"', body)
        assert name
        out[name.group(1)] = fields | {"run_id", "seq"}
    return out


def test_event_names_match() -> None:
    assert list(contract.EVENT_TYPES) == _ts_event_types()


def test_event_fields_match() -> None:
    ts = _ts_interfaces()
    assert set(ts) == set(contract.EVENT_TYPES)
    for name, model in contract.EVENT_MODELS.items():
        assert set(model.model_fields) == ts[name], f"field drift in {name}"


def test_contract_versions_match() -> None:
    assert f'CONTRACT_VERSION = "{contract.CONTRACT_VERSION}"' in TS


def test_validate_rejects_unknown_and_extra() -> None:
    with pytest.raises(ValueError):
        contract.validate_event({"event": "nope", "run_id": "r"})
    with pytest.raises(Exception):
        contract.validate_event({"event": "done", "run_id": "r", "surprise": 1})
    ok = contract.validate_event({"event": "done", "run_id": "r"})
    assert ok.event == "done"
