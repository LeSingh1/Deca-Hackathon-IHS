"""
Deterministic money math. Every number that appears in a headline, the SMS
summary, or the PDF comes from a function in this package — never from a model.

All functions are pure (no I/O, no clock, no randomness) and unit-tested in
tests/test_finance.py.
"""
from .rates import (
    FeeBreakdown,
    PricingPlan,
    StatementProfile,
    annual_savings,
    effective_rate,
    fee_breakdown,
    per_ticket_fee,
    plan_monthly_cost,
)
from .mca import McaResult, mca_true_apr
from .contracts import (
    TerminationCost,
    SwitchBenefit,
    early_termination_cost,
    net_switch_benefit,
)

__all__ = [
    "FeeBreakdown",
    "PricingPlan",
    "StatementProfile",
    "annual_savings",
    "effective_rate",
    "fee_breakdown",
    "per_ticket_fee",
    "plan_monthly_cost",
    "McaResult",
    "mca_true_apr",
    "TerminationCost",
    "SwitchBenefit",
    "early_termination_cost",
    "net_switch_benefit",
]
