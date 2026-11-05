"""
EXECUTOR. Runs outbound actions, and only after an approval event.

Actions
  rep_email      -> always a labeled dry run (we show exactly what would be sent)
  savings_sweep  -> Stripe TEST MODE PaymentIntent moving month-1 recovered
                    savings into a labeled "Tax & Rainy-Day reserve".
                    STRIPE_SECRET_KEY must be a test key (sk_test_/rk_test_);
                    live keys are refused. No key -> deterministic mock.
                    Production rail would be FedNow instant settlement to the
                    owner's own reserve account.
  fee_receipt    -> side-by-side fee on a sample $48.20 ticket, old vs new
                    rate (pure calculator output, no external call)
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from ..finance import per_ticket_fee

SAMPLE_TICKET = 48.20
RESERVE_LABEL = "Tax & Rainy-Day reserve"


class ApprovalRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class Approval:
    approval_id: str
    approved: bool
    body: str


def stripe_mode() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "")
    return "live" if key.startswith(("sk_test_", "rk_test_")) else "mock"


def sweep_rail() -> str:
    """How the sweep actually runs right now, for anything shown to the owner."""
    return "Stripe test mode" if stripe_mode() == "live" else "sandbox, no real money"


def _require(approval: Approval | None, action: str) -> None:
    if approval is None or not approval.approved:
        raise ApprovalRequired(f"refusing to run {action!r} without an owner approval event")


def _mock_ref(prefix: str, *parts: object) -> str:
    return f"{prefix}_mock_" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:14]


def rep_email(approval: Approval | None, email: dict) -> dict:
    _require(approval, "rep_email")
    return {"action": "rep_email", "provider": "email-dry-run", "sandbox": True,
            "ref": _mock_ref("msg", email["to"], email["subject"]), "amount": None,
            "detail": {"to": email["to"], "subject": email["subject"], "status": "drafted, not sent (dry run)"}}


def savings_sweep(approval: Approval | None, amount: float, run_id: str, merchant: str) -> dict:
    _require(approval, "savings_sweep")
    cents = int(round(amount * 100))
    detail = {"to": RESERVE_LABEL, "merchant": merchant, "rail_in_production": "FedNow instant payment",
              "note": f"{sweep_rail()}: no real money moved"}
    if stripe_mode() == "live":
        try:
            import stripe
            client = stripe.StripeClient(os.environ["STRIPE_SECRET_KEY"])
            pi = client.v1.payment_intents.create(params={
                "amount": cents, "currency": "usd",
                "payment_method": "pm_card_visa", "payment_method_types": ["card"], "confirm": True,
                "description": f"ShadowBuyer savings sweep -> {RESERVE_LABEL} (TEST MODE)",
                "metadata": {"run_id": run_id, "merchant": merchant, "bucket": RESERVE_LABEL,
                             "approval_id": approval.approval_id if approval else ""},
            }, options={"idempotency_key": f"sweep-{run_id}"})
            return {"action": "savings_sweep", "provider": "stripe", "sandbox": True, "ref": pi.id,
                    "amount": amount, "detail": {**detail, "status": pi.status, "livemode": bool(pi.livemode)}}
        except Exception as e:  # demo cannot crash: fall back, but say so
            detail["stripe_error"] = type(e).__name__
    return {"action": "savings_sweep", "provider": "mock", "sandbox": True,
            "ref": _mock_ref("pi", run_id, cents), "amount": amount, "detail": {**detail, "status": "succeeded"}}


def fee_receipt(approval: Approval | None, old_rate: float, new_rate: float) -> dict:
    _require(approval, "fee_receipt")
    old, new = per_ticket_fee(old_rate, SAMPLE_TICKET), per_ticket_fee(new_rate, SAMPLE_TICKET)
    return {"action": "fee_receipt", "provider": "calculator", "sandbox": True,
            "ref": _mock_ref("rcpt", old_rate, new_rate), "amount": round(old - new, 2),
            "detail": {"ticket": SAMPLE_TICKET, "old_fee": old, "new_fee": new,
                       "old_rate": old_rate, "new_rate": new_rate}}
