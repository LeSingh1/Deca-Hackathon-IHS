"""
CONTRACT EXPOSER (Opus 5.5, adaptive thinking).

1. MCA offer -> true APR via src/finance.mca_true_apr (daily IRR on the
   estimated remittance schedule). The model never computes the APR.
2. MCA offer + merchant agreement -> redlines (traps + rewritten clauses).
   Live, Opus writes the redlines; `original`/`title` always come from the
   document and `dollars_at_risk` always comes from the calculators.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..finance import McaResult, mca_true_apr
from ..llm.client import LLM
from ..llm.guard import numbers_ok
from . import fixtures
from .rate_scout import Baseline


class RedlineOut(BaseModel):
    doc: Literal["mca_offer", "merchant_agreement"]
    clause_key: str
    severity: Literal["high", "medium", "low"]
    revised: str
    why: str


class RedlineSet(BaseModel):
    redlines: list[RedlineOut]


def mca(b: Baseline) -> McaResult:
    offer = fixtures.load("mca_offer_fastfund")
    return mca_true_apr(
        advance=offer["advance"],
        factor_rate=offer["factor_rate"],
        holdback_pct=offer["holdback_pct"],
        est_daily_card_sales=b.annual_volume / 365,
        upfront_fees=offer.get("origination_fee", 0.0),
    )


def sampled_schedule(m: McaResult, points: int = 40) -> list[dict]:
    sched = m.schedule
    step = max(1, len(sched) // points)
    picked = [{"day": 0, "balance": m.payback, "paid": 0.0}]
    paid = 0.0
    for i, row in enumerate(sched):
        paid += row["payment"]
        if (i + 1) % step == 0 or i == len(sched) - 1:
            picked.append({"day": row["day"], "balance": row["balance"], "paid": round(paid, 2)})
    return picked


def dollars_at_risk(b: Baseline, m: McaResult, statement: dict) -> dict[tuple[str, str], float]:
    pci = next((li["amount"] for li in statement["line_items"] if "pci" in li["description"].lower()), 0.0)
    return {
        ("merchant_agreement", "liquidated_damages"): b.exit_cost.liquidated_damages,
        ("merchant_agreement", "etf"): b.exit_cost.flat_fee,
        ("merchant_agreement", "equipment_lease"): b.exit_cost.lease_buyout,
        ("merchant_agreement", "pci_fee"): round(pci * 12, 2),
        ("mca_offer", "purchase_price"): m.finance_charge,
        ("mca_offer", "origination"): m.upfront_fees,
    }


def _clauses() -> dict[tuple[str, str], dict]:
    out = {}
    for doc, fx in (("mca_offer", "mca_offer_fastfund"), ("merchant_agreement", "merchant_agreement")):
        for c in fixtures.load(fx)["clauses"]:
            out[(doc, c["key"])] = c
    return out


def _allowed(b: Baseline, m: McaResult, risk: dict) -> tuple[list[float], list[float]]:
    offer = fixtures.load("mca_offer_fastfund")
    terms = fixtures.load("merchant_agreement")["terms"]
    money = [m.advance, m.net_funded, m.payback, m.finance_charge, m.daily_remittance, m.upfront_fees,
             b.exit_cost.total, *risk.values(), terms["lease_monthly"], terms["lease_monthly"] * terms["lease_term_months"],
             99.0, 300.0]
    apr = m.apr * 100
    pct = [round(apr, 1), round(apr), round(m.effective_annual_rate * 100), offer["holdback_pct"] * 100,
           round((offer["factor_rate"] - 1) * 100), 50.0, 25.0]
    return money, pct


def expose(b: Baseline, statement: dict, llm: LLM) -> dict:
    m = mca(b)
    risk = dollars_at_risk(b, m, statement)
    clauses = _clauses()
    fx = fixtures.load("redlines")
    raw = [{"doc": doc, **r} for doc in ("merchant_agreement", "mca_offer") for r in fx[doc]]
    summary = ""
    live = False
    if llm.is_live("contract_exposer"):
        money, pct = _allowed(b, m, risk)
        keys = set(clauses)

        def ok(rs: RedlineSet) -> bool:
            return bool(rs.redlines) and all((r.doc, r.clause_key) in keys for r in rs.redlines) and all(
                numbers_ok(r.why + " " + r.revised, money, pct) for r in rs.redlines)

        res = llm.structured(
            "contract_exposer", shared_context=fixtures.shared_context(), schema=RedlineSet, validate=ok,
            instructions=(
                "You are the CONTRACT EXPOSER. Review the merchant processing agreement and the MCA offer on file. "
                "For each clause that harms the owner, return a redline: `clause_key` must be one of the clause keys "
                "in the documents, `revised` is the replacement clause language the owner should ask for, and `why` "
                "is one or two plain sentences. Calculator facts you may quote: "
                f"MCA estimated APR {m.apr * 100:.1f}%, total cost of financing ${m.finance_charge:,.2f}, "
                f"daily debit ${m.daily_remittance:,.2f}, about {m.term_days} days to repay; "
                f"cost to exit the processing agreement today ${b.exit_cost.total:,.2f} "
                f"(liquidated damages ${b.exit_cost.liquidated_damages:,.2f}, ETF ${b.exit_cost.flat_fee:,.2f}, "
                f"lease buyout ${b.exit_cost.lease_buyout:,.2f}). Quote no other numbers."),
            content="Review both documents in the context and return the redlines, most harmful first.",
        )
        if res.value is not None:
            raw = [r.model_dump() for r in res.value.redlines]  # type: ignore[attr-defined]
            summary = res.thinking_summary
            live = True
    redlines = []
    for r in raw:
        c = clauses[(r["doc"], r["clause_key"])]
        redlines.append({
            "doc": r["doc"], "clause_key": r["clause_key"], "title": c["title"], "original": c["text"],
            "revised": r["revised"], "severity": r["severity"], "why": r["why"],
            "dollars_at_risk": risk.get((r["doc"], r["clause_key"])),
        })
    return {"mca": m, "schedule": sampled_schedule(m), "redlines": redlines,
            "reasoning_summary": summary, "live": live}
