"""
ACTION DRAFTER (Sonnet 5.5). Writes the owner's SMS summary and the email to
the processor rep.

- The SMS is a deterministic template: it is the headline, so every number in
  it is a calculator output.
- The rep email is model-written when live, then checked by the number guard;
  the template is used if the model quotes any number it wasn't given.
Nothing here is sent. Sending happens only in the Executor after approval.
"""
from __future__ import annotations

from pydantic import BaseModel

from ..llm.client import LLM
from ..llm.guard import numbers_ok
from . import fixtures

_CONCESSION_TEXT = {
    "liquidated_damages": "remove the liquidated-damages clause",
    "auto_renew": "replace the 3-year auto-renewal with month-to-month after the current term",
    "pci_fee": "stop the PCI non-compliance fee while we complete the SAQ",
    "etf": "waive the early termination fee",
    "price_lock_12mo": "lock this pricing for 12 months",
}


class EmailOut(BaseModel):
    subject: str
    body: str


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def money(x: float, cents: bool = False) -> str:
    return f"${x:,.2f}" if cents else f"${x:,.0f}"


def sms_summary(*, hidden_monthly: float, current_rate: float, new_rate: float, annual: float,
                monthly: float, apr: float | None, lender: str, processor: str) -> str:
    lines = [f"Found {money(hidden_monthly)}/mo in markup + junk fees on your statement. You pay {pct(current_rate)} all-in."]
    if apr is not None:
        lines.append(f"That {lender} offer is really ~{apr * 100:.0f}% APR. Don't sign it.")
    lines.append(f"I got {processor} down to {pct(new_rate)} = {money(annual)}/yr back. "
                 f"Reply YES to lock it in + move month 1 ({money(monthly)}) to your rainy-day fund.")
    return "\n".join(lines)


def real_statement_sms(*, hidden_monthly: float, current_rate: float, fair_rate: float, annual: float,
                       processor: str) -> str:
    """For a real owner: only what the statement shows. Negotiating for them isn't live, so never imply it."""
    lines = [f"Found {money(hidden_monthly)}/mo in markup + junk fees on your {processor} statement. "
             f"You pay {pct(current_rate)} all-in."]
    if annual > 0:
        lines.append(f"A fair interchange-plus price would be about {pct(fair_rate)}, or {money(annual)}/yr less "
                     "(illustrative benchmark).")
    else:
        lines.append("That's already close to a fair interchange-plus price (illustrative benchmark).")
    lines.append(f"I haven't contacted {processor} or moved any money. Negotiating for you isn't live yet, "
                 "so ask them for interchange-plus pricing and to drop those fees.")
    return "\n".join(lines)


def _template_email(statement: dict, winner_final: dict, owner: str) -> dict:
    rep = fixtures.load("negotiation")["rep"]
    plan = winner_final["plan"]
    asks = [_CONCESSION_TEXT[c] for c in winner_final.get("concessions", []) if c in _CONCESSION_TEXT]
    terms = f"interchange plus {plan['markup_pct'] * 100:.2f}% and ${plan['per_txn']:.2f} per transaction, with no monthly fees"
    body = (
        f"Hi {rep['name'].split()[0]},\n\n"
        f"Thank you for working with us on {statement['merchant']['name']} (MID {statement['merchant']['mid']}). "
        f"We accept your offer of {terms}.\n\n"
        "Please send a written amendment that:\n"
        + "".join(f"  - {a[0].upper() + a[1:]}\n" for a in [f"moves the account to {terms}"] + asks)
        + "\nOnce we have the signed amendment, pricing should take effect from the next statement cycle. "
        "Please confirm by Friday.\n\n"
        f"Thanks,\n{owner}\n{statement['merchant']['name']}"
    )
    return {"to": rep["email"], "subject": f"{statement['merchant']['name']}: accepting interchange-plus offer, amendment request",
            "body": body}


def rep_email(statement: dict, winner_final: dict, llm: LLM) -> tuple[dict, bool]:
    owner = statement["merchant"]["owner"]
    tpl = _template_email(statement, winner_final, owner)
    if not llm.is_live("action_drafter"):
        llm.mock_usage("action_drafter")
        return tpl, False
    plan = winner_final["plan"]
    allowed_money = [plan["per_txn"]]
    allowed_pct = [round(plan["markup_pct"] * 100, 2)]
    res = llm.structured(
        "action_drafter", schema=EmailOut,
        instructions=("You are the Action Drafter. Rewrite this email to the processor rep so it is short, polite and "
                      "firm, from the owner's voice. Keep every term and request exactly as given. Quote no numbers "
                      "other than the ones in the draft."),
        content=f"Draft:\nSubject: {tpl['subject']}\n\n{tpl['body']}",
        validate=lambda e: numbers_ok(e.subject + " " + e.body, allowed_money, allowed_pct)
        and statement["merchant"]["mid"] in e.body,
    )
    if res.value is None:
        return tpl, False
    return {"to": tpl["to"], "subject": res.value.subject, "body": res.value.body}, True  # type: ignore[attr-defined]
