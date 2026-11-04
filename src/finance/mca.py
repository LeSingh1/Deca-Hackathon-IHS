"""
Merchant cash advance (MCA) true-cost math.

An MCA is sold as a "factor rate" (e.g. 1.35: borrow $40k, repay $54k) with
repayment taken as a fixed percentage ("holdback") of daily card sales. Because
the money comes back fast, the annualised cost is far higher than the factor
suggests. We estimate the daily remittance from expected card sales, build the
cash-flow schedule, and solve for the internal rate of return.

APR here is the nominal annual rate: daily IRR x 365. That is the same
convention as a spreadsheet's =RATE(n, pmt, -pv) * 365 and the "estimated APR"
used by state commercial-financing disclosure laws (e.g. California SB 1235).
We also return the effective annual rate, (1 + daily IRR)^365 - 1.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class McaResult:
    advance: float               # gross advance amount on the offer
    upfront_fees: float          # origination/underwriting deducted at funding
    net_funded: float            # cash actually received = advance - upfront_fees
    factor_rate: float
    payback: float               # advance x factor
    finance_charge: float        # payback - net_funded (total cost of the money)
    holdback_pct: float
    est_daily_card_sales: float
    daily_remittance: float
    term_days: int               # days until paid off at the estimated remittance
    daily_irr: float
    apr: float                   # nominal: daily_irr * 365
    effective_annual_rate: float
    schedule: list[dict] = field(default_factory=list)   # [{day, payment, balance}]

    def to_dict(self) -> dict:
        return asdict(self)


def _npv(rate: float, cash_flows: list[float]) -> float:
    """Net present value at a periodic rate. cash_flows[0] is at t=0.

    We use the funder's view: -net_funded at t=0, then each remittance as a
    positive inflow, so NPV(0) > 0 and NPV falls as the rate rises."""
    return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cash_flows))


def _irr(cash_flows: list[float], lo: float = 0.0, hi: float = 1.0, tol: float = 1e-12) -> float:
    """Periodic IRR by bisection. Requires NPV(lo) > 0 > NPV(hi)."""
    f_lo, f_hi = _npv(lo, cash_flows), _npv(hi, cash_flows)
    if f_lo == 0:
        return lo
    if f_lo * f_hi > 0:
        raise ValueError("IRR not bracketed: cash flows never repay principal")
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = _npv(mid, cash_flows)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def mca_true_apr(
    advance: float,
    factor_rate: float,
    holdback_pct: float,
    est_daily_card_sales: float,
    upfront_fees: float = 0.0,
) -> McaResult:
    """Estimate the true APR of an MCA offer.

    Assumes one remittance per calendar day (restaurants trade 7 days a week)
    equal to holdback_pct x est_daily_card_sales, with a final partial
    payment. Upfront fees reduce the cash the merchant actually receives.
    """
    if advance <= 0:
        raise ValueError("advance must be positive")
    if factor_rate < 1:
        raise ValueError("factor_rate below 1.0 would mean repaying less than borrowed")
    if not 0 < holdback_pct <= 1:
        raise ValueError("holdback_pct must be in (0, 1]")
    if est_daily_card_sales <= 0:
        raise ValueError("est_daily_card_sales must be positive")
    if not 0 <= upfront_fees < advance:
        raise ValueError("upfront_fees must be in [0, advance)")

    payback = round(advance * factor_rate, 2)
    net_funded = round(advance - upfront_fees, 2)
    daily = round(holdback_pct * est_daily_card_sales, 2)

    full_days = int(payback // daily)
    remainder = round(payback - full_days * daily, 2)
    payments = [daily] * full_days + ([remainder] if remainder > 0 else [])
    term_days = len(payments)

    schedule = []
    balance = payback
    for day, p in enumerate(payments, start=1):
        balance = round(balance - p, 2)
        schedule.append({"day": day, "payment": p, "balance": max(balance, 0.0)})

    flows = [-net_funded] + payments
    if math.isclose(sum(payments), net_funded) or sum(payments) <= net_funded:
        r = 0.0
    else:
        r = _irr(flows)
    return McaResult(
        advance=round(advance, 2),
        upfront_fees=round(upfront_fees, 2),
        net_funded=net_funded,
        factor_rate=factor_rate,
        payback=payback,
        finance_charge=round(payback - net_funded, 2),
        holdback_pct=holdback_pct,
        est_daily_card_sales=round(est_daily_card_sales, 2),
        daily_remittance=daily,
        term_days=term_days,
        daily_irr=r,
        apr=r * 365.0,
        effective_annual_rate=(1.0 + r) ** 365 - 1.0,
        schedule=schedule,
    )
