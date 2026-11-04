"""
QUOTE HUNTER agent. Owned by Person B (Actionbook). We consume the output.

Reads from fixtures/datadog_ae_response.json when present so Person B can drop
real Actionbook captures in without code changes. Emits both the doc-spec
`ae_response` shape (display strings — for Person C's dashboard) and numeric
fields the Negotiator needs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from agentfield import agent  # type: ignore
except ImportError:
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load_ae_response(vendor: str) -> dict[str, Any] | None:
    candidates = [
        FIXTURES / f"{vendor.lower().replace(' ', '_')}_ae_response.json",
    ]
    for p in candidates:
        if p.exists():
            data = json.loads(p.read_text())
            data.pop("_source", None)
            return data
    return None


_NEW_RELIC_FALLBACK = {
    "vendor": "New Relic",
    "ae_email": "priya.r@newrelic.com",
    "ae_name": "Priya R.",
    "first_quote": "$1,920/host/year",
    "discount_offered": "Year-2-for-free on 24mo commit",
    "competitor_dig": "Datadog parity on APM. We're cheaper unit economics post-PE.",
    "quarter_end_iso": "2026-06-30",
    "hosts_quoted": 500,
}


def _to_negotiator_shape(ae: dict[str, Any]) -> dict[str, Any]:
    """Build the per-month numeric record the Negotiator works on.

    AE responses speak in $/host/year ("$2,340/host/year"); the Negotiator
    works in $/host/month. Parse the string, divide by 12, and keep the
    discount offered as a hint for the diplomat's opening price target.
    """
    annual = _parse_annual_dollars(ae.get("first_quote", "$0/host/year"))
    monthly = round(annual / 12, 2) if annual else 0.0
    # Apply the headline discount to the "first_quote" for a realistic post-offer price.
    discount_pct = _parse_discount_pct(ae.get("discount_offered", ""))
    quoted_monthly = round(monthly * (1 - discount_pct / 100), 2) if monthly else 0.0
    list_monthly = monthly  # treat first_quote as list anchor for demo math
    return {
        "vendor": ae["vendor"],
        "ae_email": ae.get("ae_email", "ae@example.com"),
        "ae_name": ae.get("ae_name", "AE"),
        "list_price_per_host_mo": list_monthly or 23,
        "quoted_price_per_host_mo": quoted_monthly or list_monthly or 23,
        "hosts": ae.get("hosts_quoted", 500),
        "annual_quote_usd": round((quoted_monthly or list_monthly) * (ae.get("hosts_quoted", 500)) * 12, 2),
        "competitive_intel": ae.get("competitor_dig", ""),
        "quarter_end_iso": ae.get("quarter_end_iso", "2026-06-30"),
        "ae_response": ae,
    }


def _parse_annual_dollars(s: str) -> float:
    digits = "".join(c for c in s.split("/")[0] if c.isdigit() or c == ".")
    try:
        return float(digits)
    except ValueError:
        return 0.0


def _parse_discount_pct(s: str) -> float:
    for tok in s.replace("%", " ").split():
        try:
            return float(tok)
        except ValueError:
            continue
    return 0.0


@agent("quote_hunter")
def run(vendors: list[dict[str, Any]]) -> dict[str, Any]:
    quotes = []
    sources = []
    for v in vendors:
        ae = _load_ae_response(v["name"])
        if ae is None and v["name"] == "New Relic":
            ae = _NEW_RELIC_FALLBACK
        if ae is None:
            continue
        quotes.append(_to_negotiator_shape(ae))
        sources.append("fixture" if v["name"] != "New Relic" or _load_ae_response("New Relic") else "inline_mock")
    return {
        "agent": "quote_hunter",
        "quotes": quotes,
        "source": "actionbook" if all(_load_ae_response(v["name"]) for v in vendors[:2]) else "mixed",
        "per_vendor_sources": sources,
    }
