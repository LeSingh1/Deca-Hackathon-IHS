"""
FEE HUNTER (Haiku 5.5). Classify every statement line into the fee taxonomy.

Deterministic path: keyword rules from fixtures/fee_taxonomy.json (works on
any statement, so it also backs up a live parse). Live path: Haiku returns a
category per line; accepted only if every line id is covered with a valid
category. Totals are always computed by src/finance.fee_breakdown.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..finance.rates import CATEGORIES, EQUIPMENT, JUNK, MARKUP
from ..llm.client import LLM
from . import fixtures

Category = Literal["interchange", "assessment", "processor_markup", "junk_fee", "equipment_lease"]


class ClassifiedLine(BaseModel):
    id: str
    category: Category
    tag: str
    reason: str


class Classification(BaseModel):
    items: list[ClassifiedLine]


INSTRUCTIONS = (
    "You are the Fee Hunter. Classify each statement line into exactly one taxonomy category. "
    "`tag` is a 2-4 word stamp for the line (e.g. 'PCI non-compliance', 'Tier surcharge'). "
    "`reason` is one plain-English sentence an owner would understand: who gets this money and "
    "whether it can be removed. Do not mention dollar amounts."
)

_DEFAULT_TAGS = {
    "interchange": ("Interchange", "Goes to the card-issuing bank. Same at every processor."),
    "assessment": ("Network dues", "Goes to Visa/Mastercard. Same at every processor."),
    EQUIPMENT: ("Locked-in lease", "A non-cancellable terminal lease that costs far more than buying the terminal."),
    MARKUP: ("Unexplained markup", "Processor revenue with no clear purpose."),
}


def classify_rules(line_items: list[dict]) -> list[dict]:
    rules = fixtures.load("fee_taxonomy")["rules"]
    out = []
    for li in line_items:
        desc = li["description"].lower()
        hit = next((r for r in rules if any(m in desc for m in r["match"])), None)
        cat = hit["category"] if hit else MARKUP
        default_tag, default_reason = _DEFAULT_TAGS.get(cat, ("Fee", ""))
        out.append({
            **li,
            "category": cat,
            "tag": (hit or {}).get("tag", default_tag),
            "reason": (hit or {}).get("reason", default_reason),
        })
    return out


def classify(line_items: list[dict], llm: LLM) -> tuple[list[dict], bool]:
    base = classify_rules(line_items)
    if not llm.is_live("fee_hunter"):
        llm.mock_usage("fee_hunter")
        return base, False
    ids = {li["id"] for li in line_items}

    def ok(c: Classification) -> bool:
        return {i.id for i in c.items} == ids and all(i.category in CATEGORIES for i in c.items)

    listing = "\n".join(f"{li['id']}: {li['description']} ({li.get('detail') or ''})" for li in line_items)
    res = llm.structured("fee_hunter", instructions=INSTRUCTIONS, schema=Classification, validate=ok,
                         shared_context=fixtures.shared_context(), content=f"Statement lines:\n{listing}")
    if res.value is None:
        return base, False
    by_id = {i.id: i for i in res.value.items}  # type: ignore[attr-defined]
    return [{**li, "category": by_id[li["id"]].category, "tag": by_id[li["id"]].tag,
             "reason": by_id[li["id"]].reason} for li in line_items], True


def is_flagged(item: dict) -> bool:
    return item["category"] in (MARKUP, JUNK, EQUIPMENT)
