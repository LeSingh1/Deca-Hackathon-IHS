"""
Unit tests for src/finance — the only code allowed to produce headline numbers.
"""
from __future__ import annotations

import math

import pytest

from src.finance import (
    PricingPlan,
    StatementProfile,
    annual_savings,
    early_termination_cost,
    effective_rate,
    fee_breakdown,
    mca_true_apr,
    net_switch_benefit,
    per_ticket_fee,
    plan_monthly_cost,
)


# ---------------------------------------------------------------- effective_rate
def test_effective_rate_basic() -> None:
    assert effective_rate(3277.40, 100_000) == pytest.approx(0.032774)


def test_effective_rate_rejects_zero_volume() -> None:
    with pytest.raises(ValueError):
        effective_rate(10, 0)
    with pytest.raises(ValueError):
        effective_rate(-1, 100)


# ---------------------------------------------------------------- fee_breakdown
ITEMS = [
    {"id": "a", "amount": 1862.40, "category": "interchange"},
    {"id": "b", "amount": 141.30, "category": "assessment"},
    {"id": "c", "amount": 196.00, "category": "processor_markup"},
    {"id": "d", "amount": 890.20, "category": "processor_markup"},
    {"id": "e", "amount": 39.95, "category": "junk_fee"},
    {"id": "f", "amount": 77.60, "category": "junk_fee"},
    {"id": "g", "amount": 69.95, "category": "equipment_lease"},
]


def test_fee_breakdown_groups_and_totals() -> None:
    b = fee_breakdown(ITEMS)
    assert b.interchange == 1862.40
    assert b.assessment == 141.30
    assert b.processor_markup == 1086.20
    assert b.junk_fee == 117.55
    assert b.equipment_lease == 69.95
    assert b.total == 3277.40
    assert b.pass_through == 2003.70
    assert b.processor_controlled == 1203.75
    assert math.isclose(sum(b.by_category.values()), b.total)


def test_fee_breakdown_rejects_unknown_category() -> None:
    with pytest.raises(ValueError):
        fee_breakdown([{"amount": 1, "category": "mystery"}])
    with pytest.raises(ValueError):
        fee_breakdown([{"amount": -1, "category": "junk_fee"}])


# ---------------------------------------------------------------- annual_savings / plans
def test_annual_savings() -> None:
    assert annual_savings(0.032774, 0.0248957, 1_200_000) == 9453.96
    assert annual_savings(0.03, 0.03, 1_200_000) == 0.0
    assert annual_savings(0.02, 0.03, 100_000) == -1000.0


PROFILE = StatementProfile(
    monthly_volume=100_000.00,
    transaction_count=2074,
    interchange=1862.40,
    assessment=141.30,
    equipment_lease=69.95,
)


def test_plan_monthly_cost_ic_plus() -> None:
    plan = PricingPlan(label="IC+ 0.25% + $0.08", markup_pct=0.0025, per_txn=0.08)
    # 1862.40 + 141.30 + 250.00 + 165.92 + 69.95
    assert plan_monthly_cost(plan, PROFILE) == 2489.57


def test_plan_monthly_cost_switch_drops_lease_and_adds_fees() -> None:
    plan = PricingPlan(
        label="competitor", markup_pct=0.0020, per_txn=0.08,
        monthly_fees={"account": 10.0}, keeps_equipment_lease=False,
    )
    assert plan_monthly_cost(plan, PROFILE) == 2379.62


def test_plan_monthly_cost_flat() -> None:
    plan = PricingPlan(label="flat", model="flat", flat_pct=0.026, per_txn=0.15, keeps_equipment_lease=False)
    assert plan_monthly_cost(plan, PROFILE) == round(2600 + 0.15 * 2074, 2)


def test_plan_unknown_model() -> None:
    with pytest.raises(ValueError):
        plan_monthly_cost(PricingPlan(label="x", model="tiered"), PROFILE)


def test_per_ticket_fee() -> None:
    assert per_ticket_fee(0.032774, 48.20) == 1.58
    assert per_ticket_fee(0.0248957, 48.20) == 1.20


# ---------------------------------------------------------------- mca_true_apr
def test_mca_apr_matches_hand_checked_spreadsheet() -> None:
    """Hand-checked example.

    $10,000 advance, factor 1.20, 10% holdback, $1,000/day card sales
      -> $100/day for exactly 120 days, $12,000 repaid.
    Spreadsheet: =RATE(120, 100, -10000)        -> 0.0031141819 (daily)
                 =RATE(120, 100, -10000) * 365  -> 113.668% APR
                 =(1 + RATE(...))^365 - 1       -> 211.09% effective annual
    The daily rate was cross-checked with an independent Newton solve of the
    closed-form annuity 100 * (1 - (1+r)^-120) / r = 10000.
    """
    r = mca_true_apr(advance=10_000, factor_rate=1.20, holdback_pct=0.10, est_daily_card_sales=1_000)
    assert r.payback == 12_000
    assert r.daily_remittance == 100
    assert r.term_days == 120
    assert r.finance_charge == 2_000
    assert r.daily_irr == pytest.approx(0.0031141819, abs=1e-9)
    assert r.apr == pytest.approx(1.136676, abs=1e-5)
    assert r.effective_annual_rate == pytest.approx(2.110894, abs=1e-4)
    # Closed-form annuity check, independent of the solver.
    d = r.daily_irr
    assert 100 * (1 - (1 + d) ** -120) / d == pytest.approx(10_000, abs=0.01)


def test_mca_apr_year_long_daily_repayment() -> None:
    # Borrow 1,000, repay 1,095 at $3/day for 365 days. NPV at the solved rate must be ~0.
    r = mca_true_apr(advance=1_000, factor_rate=1.095, holdback_pct=0.003, est_daily_card_sales=1_000)
    assert r.term_days == 365
    npv = -1000 + sum(3 / (1 + r.daily_irr) ** t for t in range(1, 366))
    assert npv == pytest.approx(0, abs=1e-6)
    # A 9.5% flat charge repaid daily is ~18.4% APR: the balance falls all year, so
    # the average amount borrowed is ~half the advance. This is the trap factor rates hide.
    assert r.apr == pytest.approx(0.18387, abs=1e-4)


def test_mca_schedule_and_partial_last_payment() -> None:
    r = mca_true_apr(advance=40_000, factor_rate=1.35, holdback_pct=0.06,
                     est_daily_card_sales=1_200_000 / 365, upfront_fees=1_200)
    assert r.payback == 54_000
    assert r.net_funded == 38_800
    assert r.finance_charge == 15_200
    assert r.daily_remittance == 197.26
    assert r.term_days == 274
    assert sum(p["payment"] for p in r.schedule) == pytest.approx(54_000, abs=0.01)
    assert r.schedule[-1]["balance"] == 0
    assert r.schedule[-1]["payment"] < r.daily_remittance
    assert r.apr == pytest.approx(0.9334, abs=5e-4)


def test_mca_upfront_fees_raise_apr() -> None:
    a = mca_true_apr(40_000, 1.35, 0.06, 3_287.67)
    b = mca_true_apr(40_000, 1.35, 0.06, 3_287.67, upfront_fees=1_200)
    assert b.apr > a.apr


def test_mca_faster_holdback_raises_apr() -> None:
    slow = mca_true_apr(40_000, 1.35, 0.06, 3_287.67)
    fast = mca_true_apr(40_000, 1.35, 0.12, 3_287.67)
    assert fast.term_days < slow.term_days
    assert fast.apr > slow.apr


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(advance=0, factor_rate=1.3, holdback_pct=0.1, est_daily_card_sales=100),
        dict(advance=100, factor_rate=0.9, holdback_pct=0.1, est_daily_card_sales=100),
        dict(advance=100, factor_rate=1.3, holdback_pct=0, est_daily_card_sales=100),
        dict(advance=100, factor_rate=1.3, holdback_pct=0.1, est_daily_card_sales=0),
        dict(advance=100, factor_rate=1.3, holdback_pct=0.1, est_daily_card_sales=100, upfront_fees=100),
    ],
)
def test_mca_rejects_bad_inputs(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        mca_true_apr(**kwargs)


def test_mca_factor_one_is_zero_apr() -> None:
    r = mca_true_apr(1_000, 1.0, 0.1, 1_000)
    assert r.apr == 0.0


# ---------------------------------------------------------------- early_termination_cost
TERMS = {
    "etf_flat": 495.0,
    "liquidated_damages_pct": 0.5,
    "avg_monthly_processor_fees": 1203.75,
    "lease_monthly": 69.95,
    "lease_months_remaining": 31,
    "lease_cancellable": False,
}


def test_early_termination_cost_components() -> None:
    t = early_termination_cost(TERMS, months_remaining=14)
    assert t.flat_fee == 495.00
    assert t.liquidated_damages == 8426.25
    assert t.lease_buyout == 2168.45
    assert t.total == 11089.70


def test_early_termination_cost_at_term_end_only_lease() -> None:
    t = early_termination_cost(TERMS, months_remaining=0)
    assert t.flat_fee == 0 and t.liquidated_damages == 0
    assert t.lease_buyout == 2168.45


def test_early_termination_cost_cancellable_lease() -> None:
    t = early_termination_cost({**TERMS, "lease_cancellable": True}, months_remaining=14)
    assert t.lease_buyout == 0
    with pytest.raises(ValueError):
        early_termination_cost(TERMS, -1)


# ---------------------------------------------------------------- net_switch_benefit
def test_net_switch_benefit_trap_eats_savings() -> None:
    b = net_switch_benefit(monthly_savings=897.78, one_time_costs=11089.70)
    assert b.annual_savings == 10773.36
    assert b.net_first_year == -316.34
    assert b.payback_months == 12.4


def test_net_switch_benefit_no_costs() -> None:
    b = net_switch_benefit(787.83)
    assert b.net_first_year == 9453.96
    assert b.payback_months == 0.0


def test_net_switch_benefit_never_pays_back() -> None:
    assert net_switch_benefit(-5, 100).payback_months is None
    with pytest.raises(ValueError):
        net_switch_benefit(10, -1)
