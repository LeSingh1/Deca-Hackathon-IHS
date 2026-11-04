"""
Merchant-agreement exit math: what it costs to leave, and whether leaving pays.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Mapping


def _c(x: float) -> float:
    return round(x + 0.0, 2)


@dataclass(frozen=True)
class TerminationCost:
    flat_fee: float               # the advertised early-termination fee
    liquidated_damages: float     # "lost profits" clause: pct x avg monthly processor fees x months left
    lease_buyout: float           # non-cancellable terminal lease, accelerated on exit
    total: float
    months_remaining: int

    def to_dict(self) -> dict:
        return asdict(self)


def early_termination_cost(agreement_terms: Mapping, months_remaining: int) -> TerminationCost:
    """Cost to exit a merchant agreement with `months_remaining` left on the term.

    agreement_terms keys (all optional, default 0 / False):
      etf_flat                         flat early-termination fee, $
      liquidated_damages_pct           fraction of avg monthly processor fees owed per remaining month
      avg_monthly_processor_fees       the basis for liquidated damages, $ / month
      lease_monthly                    terminal lease payment, $ / month
      lease_months_remaining           months left on the lease
      lease_cancellable                if False, the full remaining lease is owed on exit
    """
    if months_remaining < 0:
        raise ValueError("months_remaining cannot be negative")
    if months_remaining == 0:
        flat = 0.0
        ld = 0.0
    else:
        flat = float(agreement_terms.get("etf_flat", 0.0))
        ld = (
            float(agreement_terms.get("liquidated_damages_pct", 0.0))
            * float(agreement_terms.get("avg_monthly_processor_fees", 0.0))
            * months_remaining
        )
    lease = 0.0
    if not agreement_terms.get("lease_cancellable", False):
        lease = float(agreement_terms.get("lease_monthly", 0.0)) * int(
            agreement_terms.get("lease_months_remaining", 0)
        )
    return TerminationCost(
        flat_fee=_c(flat),
        liquidated_damages=_c(ld),
        lease_buyout=_c(lease),
        total=_c(flat + ld + lease),
        months_remaining=months_remaining,
    )


@dataclass(frozen=True)
class SwitchBenefit:
    monthly_savings: float
    annual_savings: float
    one_time_costs: float
    net_first_year: float
    payback_months: float | None     # None when it never pays back

    def to_dict(self) -> dict:
        return asdict(self)


def net_switch_benefit(
    monthly_savings: float,
    one_time_costs: float = 0.0,
    horizon_months: int = 12,
) -> SwitchBenefit:
    """Savings minus exit costs (ETF + liquidated damages + equipment buyout) over a horizon.

    payback_months: months of savings needed to recover one_time_costs
    (0 when there is nothing to recover, None when savings are not positive).
    """
    if one_time_costs < 0:
        raise ValueError("one_time_costs cannot be negative")
    if horizon_months <= 0:
        raise ValueError("horizon_months must be positive")
    if one_time_costs == 0:
        payback: float | None = 0.0
    elif monthly_savings <= 0:
        payback = None
    else:
        payback = round(math.ceil(one_time_costs / monthly_savings * 10) / 10, 1)
    return SwitchBenefit(
        monthly_savings=_c(monthly_savings),
        annual_savings=_c(monthly_savings * 12),
        one_time_costs=_c(one_time_costs),
        net_first_year=_c(monthly_savings * horizon_months - one_time_costs),
        payback_months=payback,
    )
