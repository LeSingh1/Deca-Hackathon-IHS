"""
RATE SCOUT (deterministic, no LLM). Benchmarks the current statement against
a fair interchange-plus price and the competitor quotes in fixtures/, and
prices the cost of leaving the current contract.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..finance import (
    FeeBreakdown,
    PricingPlan,
    StatementProfile,
    annual_savings,
    early_termination_cost,
    effective_rate,
    plan_monthly_cost,
)
from ..finance.contracts import TerminationCost
from . import fixtures


@dataclass
class Baseline:
    profile: StatementProfile
    breakdown: FeeBreakdown
    current_cost: float
    current_rate: float
    annual_volume: float
    exit_cost: TerminationCost


def plan_from(d: dict) -> PricingPlan:
    return PricingPlan(
        label=d["label"], model=d.get("model", "ic_plus"),
        markup_pct=d.get("markup_pct", 0.0), per_txn=d.get("per_txn", 0.0),
        flat_pct=d.get("flat_pct", 0.0), monthly_fees=dict(d.get("monthly_fees", {})),
        keeps_equipment_lease=d.get("keeps_equipment_lease", True),
    )


def baseline(statement: dict, breakdown: FeeBreakdown) -> Baseline:
    agreement = fixtures.load("merchant_agreement")
    profile = StatementProfile(
        monthly_volume=statement["monthly_volume"],
        transaction_count=statement["transaction_count"],
        interchange=breakdown.interchange,
        assessment=breakdown.assessment,
        equipment_lease=breakdown.equipment_lease,
    )
    exit_cost = early_termination_cost(
        {**agreement["terms"], "avg_monthly_processor_fees": breakdown.processor_controlled},
        agreement["months_remaining"],
    )
    return Baseline(
        profile=profile,
        breakdown=breakdown,
        current_cost=breakdown.total,
        current_rate=effective_rate(breakdown.total, statement["monthly_volume"]),
        annual_volume=round(statement["monthly_volume"] * 12, 2),
        exit_cost=exit_cost,
    )


def price(plan: PricingPlan, b: Baseline) -> dict:
    cost = plan_monthly_cost(plan, b.profile)
    rate = effective_rate(cost, b.profile.monthly_volume)
    return {
        "plan": plan.to_dict(),
        "monthly_cost": cost,
        "effective_rate": rate,
        "annual_savings": annual_savings(b.current_rate, rate, b.annual_volume),
    }


def quotes(statement: dict, b: Baseline) -> list[dict]:
    bench = fixtures.load("interchange_benchmarks")
    comps = fixtures.load("competitor_processors")
    out = [{
        "key": "current", "label": f"{statement['processor']} (today)", "kind": "current",
        "effective_rate": b.current_rate, "monthly_cost": b.current_cost, "annual_savings": 0.0,
        "source": f"Your {statement['period']['label']} statement", "as_of": statement["period"]["end"],
        "illustrative": bool(statement.get("illustrative", False)),
    }]
    fair = plan_from({"label": "Fair interchange-plus", **bench["fair_markup"]})
    p = price(fair, b)
    out.append({"key": "benchmark", "label": "Fair IC+ benchmark", "kind": "benchmark",
                "effective_rate": p["effective_rate"], "monthly_cost": p["monthly_cost"],
                "annual_savings": p["annual_savings"], "source": bench["source"], "as_of": bench["as_of"],
                "illustrative": bench["illustrative"]})
    for q in comps["quotes"]:
        p = price(plan_from(q["plan"]), b)
        out.append({"key": q["key"], "label": q["label"], "kind": "competitor",
                    "effective_rate": p["effective_rate"], "monthly_cost": p["monthly_cost"],
                    "annual_savings": p["annual_savings"], "source": q["source"], "as_of": q["as_of"],
                    "illustrative": comps["illustrative"]})
    return out


def best_competitor() -> dict:
    return fixtures.load("competitor_processors")["quotes"][0]
