"""
STATEMENT READER (Sonnet 5.5, vision). Photo/PDF of a processing statement -> line items.

Live: sends the image/PDF to the model with a Pydantic schema; the parse is
accepted only if the line items add up to the statement's stated total
(within 5 cents). Otherwise: one retry, then the fixture.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from ..llm.client import LLM
from . import fixtures

FIXTURE = "statement_marios_trattoria_oct"


class ParsedLine(BaseModel):
    id: str = Field(description="L01, L02, ... in statement order")
    description: str
    amount: float = Field(description="dollars charged this period for this line")
    detail: Optional[str] = Field(default=None, description="rate x basis, count, etc. as printed")


class StatementParse(BaseModel):
    merchant_name: str
    processor: str
    period_label: str
    monthly_volume: float = Field(description="total card sales volume for the period, $")
    transaction_count: int
    stated_total_fees: float = Field(description="total fees as printed on the statement")
    line_items: list[ParsedLine]


INSTRUCTIONS = (
    "You are the Statement Reader. Extract every fee line from this card-processing statement exactly "
    "as printed. Do not classify, total, or round anything; copy amounts to the cent. If the statement "
    "prints a total fees figure, report it as stated_total_fees."
)


def _media_block(media: str) -> list[dict] | None:
    """fixture:<name> -> the fixture PDF; file:<path> -> an uploaded photo/PDF."""
    if media.startswith("fixture:"):
        p = fixtures.path(media.split(":", 1)[1] + ".pdf")
    elif media.startswith("file:"):
        p = Path(media.split(":", 1)[1])
    else:
        return None
    if not p.exists():
        return None
    data = base64.standard_b64encode(p.read_bytes()).decode()
    mt = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    if mt == "application/pdf":
        return [{"type": "document", "source": {"type": "base64", "media_type": mt, "data": data}}]
    if mt in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        return [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}]
    return None


def _valid(p: StatementParse) -> bool:
    total = sum(li.amount for li in p.line_items)
    return p.monthly_volume > 0 and p.transaction_count > 0 and bool(p.line_items) \
        and abs(total - p.stated_total_fees) <= 0.05


def read(media: list[str], llm: LLM) -> tuple[dict, bool]:
    """Returns (statement dict in fixture shape, live_parsed)."""
    fx = fixtures.load(FIXTURE)
    block = _media_block(media[0]) if media else None
    if block is not None and llm.is_live("statement_reader"):
        res = llm.structured(
            "statement_reader", instructions=INSTRUCTIONS, schema=StatementParse, validate=_valid,
            content=block + [{"type": "text", "text": "Extract this statement."}],
        )
        if res.value is not None:
            p: StatementParse = res.value  # type: ignore[assignment]
            out = {
                **fx,
                "merchant": {**fx["merchant"], "name": p.merchant_name},
                "processor": p.processor,
                "period": {**fx["period"], "label": p.period_label},
                "monthly_volume": p.monthly_volume,
                "transaction_count": p.transaction_count,
                "annual_volume_estimate": round(p.monthly_volume * 12, 2),
                "stated_total_fees": p.stated_total_fees,
                "line_items": [li.model_dump() for li in p.line_items],
            }
            return out, True
    elif not llm.is_live("statement_reader"):
        llm.mock_usage("statement_reader")
    return fx, False
