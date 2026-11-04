"""
Number guard: LLM prose may *quote* calculator numbers, never invent them.

`numbers_ok(text, allowed)` extracts every dollar amount and percentage in the
text and checks each against the allowed set (calculator outputs). Used on
model-written rationale and emails; on failure the agent uses its template.
"""
from __future__ import annotations

import re
from typing import Iterable

_MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?([kK])?")
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s?%")


def _money_values(text: str) -> list[float]:
    out = []
    for num, k in _MONEY.findall(text):
        v = float(num.replace(",", ""))
        out.append(v * 1000 if k else v)
    return out


def numbers_ok(text: str, allowed_money: Iterable[float], allowed_pct: Iterable[float],
               money_tol: float = 0.51, pct_tol: float = 0.051) -> bool:
    money = list(allowed_money)
    pct = list(allowed_pct)
    for v in _money_values(text):
        # allow exact cents, whole-dollar rounding, and "$9.5K"-style rounding
        if not any(abs(v - a) <= max(money_tol, a * 0.006 if v >= 1000 and v % 100 == 0 else money_tol) for a in money):
            return False
    for v in (float(x) for x in _PCT.findall(text)):
        if not any(abs(v - a) <= pct_tol for a in pct):
            return False
    return True
