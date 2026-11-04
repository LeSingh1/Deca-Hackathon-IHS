"""
FROZEN SSE event contract — v1.0.0.

Every event the pipeline streams to the UI is one of the models below,
serialised as `data: {json}\\n\\n` with `event` as the discriminator.
Mirrored by hand in frontend/src/lib/contract.ts; tests/test_contract.py
fails if the two drift (event names or field names).

Rules
- Add new optional fields freely; never rename or remove one.
- Every dollar/rate field is produced by src/finance, never by an LLM.
"""
from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"

Stage = Literal[
    "statement_reader",
    "fee_hunter",
    "rate_scout",
    "negotiator",
    "contract_exposer",
    "action_drafter",
    "approval",
    "executor",
]
Lane = Literal["hardball", "diplomat"]
Speaker = Literal["hardball", "diplomat", "rep"]
Severity = Literal["high", "medium", "low"]


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    seq: int = 0


# ---------------------------------------------------------------- shared shapes
class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    description: str
    amount: float
    category: Optional[str] = None       # set by Fee Hunter
    detail: Optional[str] = None          # e.g. "0.85% x $38,400.00"


class Offer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    plan: dict[str, Any]
    monthly_cost: float
    effective_rate: float
    annual_savings: float


class RateQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    label: str
    kind: Literal["current", "benchmark", "competitor"]
    effective_rate: float
    monthly_cost: float
    annual_savings: float
    source: str
    as_of: str
    illustrative: bool = True


class VerdictOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    label: str
    effective_rate: float
    annual_savings: float
    one_time_costs: float
    net_first_year: float
    payback_months: Optional[float] = None


class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    from_bucket: str
    to_bucket: str
    amount: float


# ---------------------------------------------------------------- events
class RunStarted(_Event):
    event: Literal["run_started"] = "run_started"
    pace: Literal["presenter", "fast", "instant"]
    owner: dict[str, Any]
    services: dict[str, str]              # service -> "live" | "mock"
    contract_version: str = CONTRACT_VERSION


class StageStart(_Event):
    event: Literal["stage_start"] = "stage_start"
    stage: Stage
    label: str
    agent: str
    model: Optional[str] = None
    live: bool = False


class StageDone(_Event):
    event: Literal["stage_done"] = "stage_done"
    stage: Stage
    ms: int = 0
    note: Optional[str] = None


class LineItemEvent(_Event):
    event: Literal["line_item"] = "line_item"
    item: LineItem
    index: int
    total_items: int


class FeeFlagged(_Event):
    event: Literal["fee_flagged"] = "fee_flagged"
    item_id: str
    category: str
    tag: str                              # stamped label, e.g. "PCI non-compliance"
    amount: float
    reason: str
    hidden_total: float                   # running total of processor-controlled fees


class RateComputed(_Event):
    event: Literal["rate_computed"] = "rate_computed"
    monthly_volume: float
    annual_volume: float
    transaction_count: int
    total_fees: float
    effective_rate: float
    breakdown: dict[str, float]
    quotes: list[RateQuote] = Field(default_factory=list)


class NegotiationTurn(_Event):
    event: Literal["negotiation_turn"] = "negotiation_turn"
    lane: Lane
    round: int
    speaker: Speaker
    delta: str = ""                       # streamed text chunk
    done: bool = False                    # last chunk of this turn
    offer: Optional[Offer] = None         # present on the rep's final chunk of a turn


class RefereeVerdict(_Event):
    event: Literal["referee_verdict"] = "referee_verdict"
    winner: str
    options: list[VerdictOption]
    rationale: str
    reasoning_summary: str = ""


class AprRevealed(_Event):
    event: Literal["apr_revealed"] = "apr_revealed"
    lender: str
    advertised: str                       # e.g. "1.35 factor"
    advance: float
    net_funded: float
    payback: float
    finance_charge: float
    daily_remittance: float
    term_days: int
    apr: float
    effective_annual_rate: float
    schedule: list[dict[str, float]]      # sampled [{day, balance, paid}]


class Redline(_Event):
    event: Literal["redline"] = "redline"
    doc: Literal["mca_offer", "merchant_agreement"]
    clause_key: str
    title: str
    original: str
    revised: str
    severity: Severity
    why: str
    dollars_at_risk: Optional[float] = None


class OwnerMessage(_Event):
    event: Literal["owner_message"] = "owner_message"
    direction: Literal["in", "out"]
    body: str
    media: list[str] = Field(default_factory=list)
    channel: Literal["simulator", "twilio"] = "simulator"


class Draft(_Event):
    event: Literal["draft"] = "draft"
    kind: Literal["rep_email", "switch_checklist"]
    to: str
    subject: str
    body: str
    dry_run: bool = True


class ApprovalRequested(_Event):
    event: Literal["approval_requested"] = "approval_requested"
    approval_id: str
    actions: list[str]
    prompt: str


class ApprovalReceived(_Event):
    event: Literal["approval_received"] = "approval_received"
    approval_id: str
    approved: bool
    body: str


class ActionExecuted(_Event):
    event: Literal["action_executed"] = "action_executed"
    action: str
    provider: str                         # "stripe" | "mock" | "email-dry-run"
    sandbox: bool = True
    ref: str
    amount: Optional[float] = None
    detail: dict[str, Any] = Field(default_factory=dict)


class LedgerUpdate(_Event):
    event: Literal["ledger_update"] = "ledger_update"
    entries: list[LedgerEntry]
    back_in_pocket_monthly: float
    back_in_pocket_annual: float


class CostLog(_Event):
    event: Literal["cost_log"] = "cost_log"
    agent: str
    model: str
    live: bool
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    usd: float = 0.0
    run_total_usd: float = 0.0


class Summary(_Event):
    event: Literal["summary"] = "summary"
    headline: str
    current_rate: float
    new_rate: float
    annual_savings: float
    monthly_savings: float
    hidden_fees_monthly: float
    mca_apr: Optional[float] = None
    report_url: str


class Done(_Event):
    event: Literal["done"] = "done"
    ok: bool = True


class ErrorEvent(_Event):
    event: Literal["error"] = "error"
    message: str


Event = Union[
    RunStarted, StageStart, StageDone, LineItemEvent, FeeFlagged, RateComputed,
    NegotiationTurn, RefereeVerdict, AprRevealed, Redline, OwnerMessage, Draft,
    ApprovalRequested, ApprovalReceived, ActionExecuted, LedgerUpdate, CostLog,
    Summary, Done, ErrorEvent,
]

EVENT_MODELS: dict[str, type[_Event]] = {
    m.model_fields["event"].default: m  # type: ignore[misc]
    for m in Event.__args__  # type: ignore[attr-defined]
}
EVENT_TYPES = tuple(EVENT_MODELS)


def validate_event(payload: dict[str, Any]) -> _Event:
    """Validate a raw event dict against the frozen contract."""
    model = EVENT_MODELS.get(payload.get("event", ""))
    if model is None:
        raise ValueError(f"unknown event type: {payload.get('event')!r}")
    return model.model_validate(payload)
