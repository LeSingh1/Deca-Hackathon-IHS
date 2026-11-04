"""
Card-processing rate math: effective rate, fee breakdown, plan pricing, savings.

Conventions
- Money is in US dollars as floats, rounded to cents at function boundaries.
- Rates are fractions (0.0328 == 3.28%), never percentages.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Mapping

# Fee categories (see fixtures/fee_taxonomy.json for the human-readable taxonomy).
INTERCHANGE = "interchange"          # paid to the card-issuing bank; pass-through, not negotiable
ASSESSMENT = "assessment"            # card-network dues; pass-through, not negotiable
MARKUP = "processor_markup"          # the processor's margin; negotiable
JUNK = "junk_fee"                    # fixed monthly add-ons that buy the merchant nothing; negotiable
EQUIPMENT = "equipment_lease"        # terminal lease; contractually separate, often non-cancellable

PASS_THROUGH = frozenset({INTERCHANGE, ASSESSMENT})
PROCESSOR_CONTROLLED = frozenset({MARKUP, JUNK})
CATEGORIES = (INTERCHANGE, ASSESSMENT, MARKUP, JUNK, EQUIPMENT)


def _c(x: float) -> float:
    """Round to cents. Adding 0.0 normalises -0.0."""
    return round(x + 0.0, 2)


def effective_rate(total_fees: float, card_volume: float) -> float:
    """All-in fees as a fraction of card volume. 3,277.40 / 100,000 -> 0.032774."""
    if card_volume <= 0:
        raise ValueError("card_volume must be positive")
    if total_fees < 0:
        raise ValueError("total_fees cannot be negative")
    return total_fees / card_volume


@dataclass(frozen=True)
class FeeBreakdown:
    interchange: float
    assessment: float
    processor_markup: float
    junk_fee: float
    equipment_lease: float
    total: float
    pass_through: float            # interchange + assessments
    processor_controlled: float    # markup + junk — the negotiable part
    by_category: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def fee_breakdown(line_items: Iterable[Mapping]) -> FeeBreakdown:
    """Group classified statement line items by category.

    Each item needs `amount` and `category` (one of CATEGORIES). Unknown
    categories raise — an unclassified fee must never silently vanish from
    the total.
    """
    sums = {c: 0.0 for c in CATEGORIES}
    for item in line_items:
        cat = item["category"]
        if cat not in sums:
            raise ValueError(f"unknown fee category: {cat!r}")
        amt = float(item["amount"])
        if amt < 0:
            raise ValueError(f"negative fee amount on {item.get('id', '?')}")
        sums[cat] += amt
    sums = {k: _c(v) for k, v in sums.items()}
    total = _c(sum(sums.values()))
    return FeeBreakdown(
        interchange=sums[INTERCHANGE],
        assessment=sums[ASSESSMENT],
        processor_markup=sums[MARKUP],
        junk_fee=sums[JUNK],
        equipment_lease=sums[EQUIPMENT],
        total=total,
        pass_through=_c(sums[INTERCHANGE] + sums[ASSESSMENT]),
        processor_controlled=_c(sums[MARKUP] + sums[JUNK]),
        by_category=sums,
    )


def annual_savings(current_rate: float, new_rate: float, annual_volume: float) -> float:
    """Dollars per year saved by moving from current_rate to new_rate on annual_volume."""
    if annual_volume < 0:
        raise ValueError("annual_volume cannot be negative")
    return _c((current_rate - new_rate) * annual_volume)


@dataclass(frozen=True)
class StatementProfile:
    """What a statement tells us about the business, independent of pricing."""
    monthly_volume: float
    transaction_count: int
    interchange: float          # monthly pass-through interchange, $
    assessment: float           # monthly pass-through network dues, $
    equipment_lease: float      # monthly lease payment, $

    @property
    def avg_ticket(self) -> float:
        return self.monthly_volume / self.transaction_count if self.transaction_count else 0.0


@dataclass(frozen=True)
class PricingPlan:
    """An interchange-plus or flat-rate offer, expressed as terms (never as a dollar total).

    model = "ic_plus": interchange + assessments pass through at cost, plus
        markup_pct of volume, plus per_txn per transaction, plus monthly_fees.
    model = "flat":    flat_pct of volume + per_txn per transaction + monthly_fees
        (interchange is bundled — Square/Stripe style).
    keeps_equipment_lease: the existing lease payment continues under this plan
        (true when staying, and also true when switching if the lease is
        non-cancellable — see contracts.early_termination_cost).
    """
    label: str
    model: str = "ic_plus"
    markup_pct: float = 0.0
    per_txn: float = 0.0
    flat_pct: float = 0.0
    monthly_fees: Mapping[str, float] = field(default_factory=dict)
    keeps_equipment_lease: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["monthly_fees"] = dict(self.monthly_fees)
        return d


def plan_monthly_cost(plan: PricingPlan, profile: StatementProfile) -> float:
    """Total monthly processing cost of `plan` for the business in `profile`."""
    fixed = sum(float(v) for v in plan.monthly_fees.values())
    per_txn = plan.per_txn * profile.transaction_count
    lease = profile.equipment_lease if plan.keeps_equipment_lease else 0.0
    if plan.model == "ic_plus":
        variable = profile.interchange + profile.assessment + plan.markup_pct * profile.monthly_volume
    elif plan.model == "flat":
        variable = plan.flat_pct * profile.monthly_volume
    else:
        raise ValueError(f"unknown pricing model: {plan.model!r}")
    return _c(variable + per_txn + fixed + lease)


def per_ticket_fee(rate: float, ticket: float) -> float:
    """Fee on a single ticket at an all-in effective rate. Used for the receipt comparison."""
    return _c(rate * ticket)
