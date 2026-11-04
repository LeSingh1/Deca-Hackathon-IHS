"""
Email Drafter. Pitch line: "The hardball wins this round. Email goes to the AE."

Consumes negotiator output + AE quote and emits the actual email ShadowBuyer
would send. Dry-run only — never delivers. Person C's dashboard renders this
as the final card after the referee verdict.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from ..clients.tokenrouter import route


@dataclass
class EmailDraft:
    to: str
    from_addr: str
    cc: list[str]
    subject: str
    body: str
    strategy: str
    cites: list[str]
    dry_run: bool
    drafted_at: str
    mocked: bool


def _hardball_body(target: dict[str, Any], comp: dict[str, Any], final_price: float, term_months: int) -> str:
    return (
        f"Hi {target.get('ae_name', 'Morgan')},\n\n"
        f"Thanks for the quote on {target['vendor']} at ${target['quoted_price_per_host_mo']}/host/mo "
        f"across {target['hosts']} hosts.\n\n"
        f"We've finalized our shortlist for observability and need to close this week. "
        f"{comp['vendor']} has a competing offer on the table at ${comp['quoted_price_per_host_mo']}/host. "
        f"Given the quarter close on {target['quarter_end_iso']}, we'd like to move forward with the following terms:\n\n"
        f"  • Price: ${final_price:.2f}/host/month\n"
        f"  • Term: {term_months} months\n"
        f"  • Auto-renewal: 30-day notice window (not 90)\n"
        f"  • Liability cap: 12 months of fees (not 3)\n"
        f"  • Annual price escalation: capped at 5%\n\n"
        f"Our Honeycomb POC is provisioned as backup if we can't align by Friday EOD. "
        f"I'd rather sign with you — your team's been responsive and the platform fit is right. "
        f"Can we close on the above today?\n\n"
        f"Best,\nProcurement, ShadowBuyer\n"
    )


def _diplomat_body(target: dict[str, Any], final_price: float, term_months: int) -> str:
    return (
        f"Hi {target.get('ae_name', 'Morgan')},\n\n"
        f"Appreciate the {target['vendor']} proposal. We're not optimizing for the lowest sticker price — "
        f"we're picking an observability partner for the next three years.\n\n"
        f"Here's the shape that works for both sides:\n\n"
        f"  • Price: ${final_price:.2f}/host/month\n"
        f"  • Term: {term_months} months\n"
        f"  • Annual price-lock cap: 8%\n"
        f"  • Expansion rights to APM and RUM at the same per-host rate\n"
        f"  • ShadowBuyer commits to: public reference customer, joint case study, conference speaking slot, homepage logo\n\n"
        f"At {target['hosts']} hosts today and a 3× projection by Q3 2027, this is a meaningful logo for {target['vendor']} "
        f"and a price that survives our budget cycle. Marketing assets you can use immediately on your end.\n\n"
        f"Happy to get paper Monday and counter-sign by EOW. Let me know.\n\n"
        f"Best,\nProcurement, ShadowBuyer\n"
    )


def draft(negotiator_output: dict[str, Any], target_quote: dict[str, Any], competing_quote: dict[str, Any]) -> EmailDraft:
    strategy = negotiator_output.get("winner") or "hardball"
    final_price = negotiator_output.get("final_price_per_host_mo") or target_quote["quoted_price_per_host_mo"]

    # Term comes from the winning strategy's own turns — hardball turns specify 12mo,
    # diplomat turns specify 36mo. Default if the winning role didn't set one.
    default_term = 12 if strategy == "hardball" else 36
    term_months = default_term
    for t in reversed(negotiator_output.get("turns", [])):
        if t.get("role") == strategy and t.get("deal_term_months"):
            term_months = t["deal_term_months"]
            break

    if strategy == "hardball":
        subject = f"{target_quote['vendor']} — closing by Friday at ${final_price:.2f}/host"
        body = _hardball_body(target_quote, competing_quote, final_price, term_months)
        cites = [
            f"competing_offer:{competing_quote['vendor']}@${competing_quote['quoted_price_per_host_mo']}",
            f"quarter_end:{target_quote['quarter_end_iso']}",
            "fallback_poc:honeycomb",
            f"final_price:${final_price:.2f}/host",
        ]
    else:
        subject = f"{target_quote['vendor']} — 36-month partnership at ${final_price:.2f}/host"
        body = _diplomat_body(target_quote, final_price, term_months)
        cites = [
            f"term:{term_months}mo",
            "reference_customer",
            "joint_case_study",
            "expansion_rights:apm_rum",
            f"final_price:${final_price:.2f}/host",
        ]

    # Optional LLM polish — route through TokenRouter so the sponsor box stays checked.
    # In mock mode this is a no-op; in live mode it lightly rewrites the body.
    polish = route(
        prompt=f"Lightly polish this procurement email for tone. Preserve all numbers and bullet points verbatim:\n\n{body}",
        model="qwen3-max",
        provider="qwen",
        max_tokens=600,
    )
    final_body = body if polish.mocked else polish.text

    return EmailDraft(
        to=target_quote.get("ae_email", "ae@datadog.com"),
        from_addr="procurement@shadowbuyer.ai",
        cc=["procurement-cc@shadowbuyer.ai"],
        subject=subject,
        body=final_body,
        strategy=strategy,
        cites=cites,
        dry_run=True,
        drafted_at=datetime.now(timezone.utc).isoformat(),
        mocked=polish.mocked,
    )


def to_dict(d: EmailDraft) -> dict[str, Any]:
    out = asdict(d)
    out["from"] = out.pop("from_addr")
    return out
