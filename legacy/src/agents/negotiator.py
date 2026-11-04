"""
ADVERSARIAL NEGOTIATOR. The demo highlight.

HARDBALL (Qwen3-Max via Qwen Cloud, routed through TokenRouter) — ruthless leverage.
DIPLOMAT (GLM-5.1 via Z.ai, routed through TokenRouter) — partnership angle.
REFEREE (Qwen via TokenRouter) — picks the winning strategy with reasoning.

Three rounds of HARDBALL ↔ DIPLOMAT, then a REFEREE verdict. Each turn carries
a price target, leverage cites, and round number so the dashboard can render
the price walking down round-by-round.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Iterator

from ..clients.tokenrouter import route

try:
    from agentfield import agent  # type: ignore
except ImportError:
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


@dataclass
class NegotiationTurn:
    round: int
    role: str                       # "hardball" | "diplomat" | "referee"
    headline: str                   # one-line for the card title
    text: str                       # the actual "spoken" message
    cites: list[str] = field(default_factory=list)
    price_target_per_host_mo: float | None = None
    deal_term_months: int | None = None
    mocked: bool = True


def _hb_round(round_no: int, target: dict[str, Any], competitor: dict[str, Any], current_price: float) -> NegotiationTurn:
    prompt = (
        f"You are HARDBALL, round {round_no} negotiating {target['vendor']}. "
        f"Current quote: ${current_price}/host/mo. Competitor {competitor['vendor']} at ${competitor['quoted_price_per_host_mo']}. "
        f"Quarter ends {target['quarter_end_iso']}. AE intel: {target['competitive_intel']}. "
        f"Escalate leverage. Be specific and ruthless."
    )
    c = route(prompt, model="qwen3-max", provider="qwen")
    if c.mocked:
        return _hb_mock(round_no, target, competitor, current_price)
    return NegotiationTurn(
        round=round_no, role="hardball",
        headline=f"Round {round_no}: hardball",
        text=c.text, cites=["live_completion"],
        price_target_per_host_mo=current_price * 0.85,
        mocked=False,
    )


def _hb_mock(round_no: int, target: dict[str, Any], competitor: dict[str, Any], current_price: float) -> NegotiationTurn:
    comp_price = competitor["quoted_price_per_host_mo"]
    if round_no == 1:
        return NegotiationTurn(
            round=1, role="hardball",
            headline="Open with competitor on the table",
            text=(
                f"{competitor['vendor']} just quoted us ${comp_price:.2f}/host across {target['hosts']} hosts. "
                f"You're at ${current_price:.2f}. We need parity to keep this conversation moving. "
                f"Match ${comp_price:.2f} this week and we keep talking; otherwise we shortlist drops to two and you're not on it."
            ),
            cites=[
                f"competitor:{competitor['vendor']}@${comp_price:.2f}/host",
                f"hosts:{target['hosts']}",
                f"shortlist_threat:cut_to_two_vendors",
            ],
            price_target_per_host_mo=comp_price,
        )
    if round_no == 2:
        target_price = round(comp_price - 1.50, 2)
        return NegotiationTurn(
            round=2, role="hardball",
            headline="Escalate: quarter-end + internal review",
            text=(
                f"Our CFO froze net-new SaaS spend pending Q-review. The only way this gets unstuck before {target['quarter_end_iso']} "
                f"is if you come in under {competitor['vendor']}, not at parity. ${target_price:.2f}/host, signed by Friday, or it slides to next quarter "
                f"and your AE eats the slip."
            ),
            cites=[
                f"quarter_end:{target['quarter_end_iso']}",
                "cfo_spend_freeze",
                "ae_quota_pressure:slip_risk",
            ],
            price_target_per_host_mo=target_price,
        )
    # round 3
    target_price = round(comp_price - 2.50, 2)
    return NegotiationTurn(
        round=3, role="hardball",
        headline="Close: deadline + walk-away",
        text=(
            f"Last move. ${target_price:.2f}/host, 12 months, no auto-renew clause, MSA redlines in our favor on liability cap. "
            f"Signed by EOD Friday or we sign with {competitor['vendor']} Monday morning. "
            f"Your AE knows this is real — Honeycomb POC is already provisioned as fallback #2."
        ),
        cites=[
            "deadline:friday_eod",
            "fallback_poc:honeycomb_provisioned",
            "msa_redlines:liability_cap",
        ],
        price_target_per_host_mo=target_price,
        deal_term_months=12,
    )


def _dp_round(round_no: int, target: dict[str, Any], current_price: float) -> NegotiationTurn:
    prompt = (
        f"You are DIPLOMAT, round {round_no} negotiating {target['vendor']}. "
        f"Quote: ${current_price}/host/mo. {target['hosts']} hosts. "
        f"Frame partnership, multi-year, expansion rights, co-marketing. Be warm and specific."
    )
    c = route(prompt, model="glm-5.1", provider="zai")
    if c.mocked:
        return _dp_mock(round_no, target, current_price)
    return NegotiationTurn(
        round=round_no, role="diplomat",
        headline=f"Round {round_no}: diplomat",
        text=c.text, cites=["live_completion"],
        price_target_per_host_mo=current_price * 0.90,
        mocked=False,
    )


def _dp_mock(round_no: int, target: dict[str, Any], current_price: float) -> NegotiationTurn:
    hosts = target["hosts"]
    if round_no == 1:
        target_price = round(current_price - 2.0, 2)
        return NegotiationTurn(
            round=1, role="diplomat",
            headline="Open: long-term partnership frame",
            text=(
                f"We're not shopping on price — we're picking an observability partner for the next three years. "
                f"{hosts} hosts today, projecting 3× by end of next year. Lock us in at ${target_price:.2f}/host for 36 months "
                f"and your ARR triples from this one account by Q3 2027."
            ),
            cites=[
                f"hosts_today:{hosts}",
                "expansion:3x_18mo",
                "arr_growth_argument",
            ],
            price_target_per_host_mo=target_price,
            deal_term_months=36,
        )
    if round_no == 2:
        target_price = round(current_price - 3.50, 2)
        return NegotiationTurn(
            round=2, role="diplomat",
            headline="Add value: case study + reference",
            text=(
                f"Sweetener: we'll be a public reference customer. Joint case study, quote from our CTO, logo on your homepage, "
                f"speaking slot at your conference. That's worth more than the ${target_price:.2f}/host delta over 36 months. "
                f"You get the marketing asset; we get the price that survives next year's budget cycle."
            ),
            cites=[
                "reference_customer",
                "joint_case_study",
                "conference_speaking_slot",
                "homepage_logo",
            ],
            price_target_per_host_mo=target_price,
            deal_term_months=36,
        )
    # round 3
    target_price = round(current_price - 4.50, 2)
    return NegotiationTurn(
        round=3, role="diplomat",
        headline="Close: expansion rights for price lock",
        text=(
            f"Final shape: ${target_price:.2f}/host, 36 months, 8% annual price-lock cap, expansion rights to APM + RUM at the same per-host rate. "
            f"Everyone's CFO can defend this. Your AE keeps the multi-year logo; we keep the unit economics. "
            f"Send paper today, we counter-sign Monday."
        ),
        cites=[
            "price_lock:8pct_annual_cap",
            "expansion_rights:apm_rum_same_rate",
            "term:36mo",
        ],
        price_target_per_host_mo=target_price,
        deal_term_months=36,
    )


def _referee(turns: list[NegotiationTurn], target: dict[str, Any]) -> NegotiationTurn:
    hb_final = [t for t in turns if t.role == "hardball"][-1]
    dp_final = [t for t in turns if t.role == "diplomat"][-1]
    transcript = "\n".join(f"[{t.round}/{t.role}] {t.text}" for t in turns)
    prompt = (
        f"You are REFEREE. Pick the winning strategy.\n{transcript}\n"
        f"Vendor: {target['vendor']}, quarter-end {target['quarter_end_iso']}, {target['hosts']} hosts."
    )
    c = route(prompt, model="qwen3-max", provider="qwen")

    hb_price = hb_final.price_target_per_host_mo or 0
    dp_price = dp_final.price_target_per_host_mo or 0
    list_price = target["list_price_per_host_mo"]
    hb_savings_annual = (list_price - hb_price) * target["hosts"] * 12
    dp_savings_annual = (list_price - dp_price) * target["hosts"] * 12 * 3  # 36mo

    if c.mocked:
        winner = "hardball"
        text = (
            f"HARDBALL takes round one. The quarter-end clock plus the {target.get('competing_vendor', 'competing')} quote on paper is "
            f"discrete, time-bounded leverage — Datadog's AE is forced to choose between signing at ${hb_price:.2f} or eating the slip. "
            f"DIPLOMAT's 36-month case-study sweetener is the right second move once price is anchored. "
            f"Recommended play: open HARDBALL through Friday EOD, close with DIPLOMAT's expansion-rights wrapper. "
            f"Projected annual savings vs list: ${hb_savings_annual:,.0f}."
        )
    else:
        text = c.text
        winner = "hardball" if "HARDBALL" in c.text.upper() else "diplomat"

    return NegotiationTurn(
        round=4, role="referee",
        headline=f"Verdict: {winner.upper()} opens, DIPLOMAT closes",
        text=text,
        cites=[
            f"winner:{winner}",
            f"hardball_savings_yr1:${hb_savings_annual:,.0f}",
            f"diplomat_savings_3yr:${dp_savings_annual:,.0f}",
            f"final_price:${hb_price:.2f}/host",
        ],
        price_target_per_host_mo=hb_price,
        mocked=c.mocked,
    )


@agent("negotiator")
def run(quotes: list[dict[str, Any]]) -> dict[str, Any]:
    turns = list(_play(quotes))
    if not turns:
        return {"agent": "negotiator", "error": "need >=2 quotes for adversarial round", "turns": []}
    target, competitor = quotes[0], quotes[1]
    return {
        "agent": "negotiator",
        "target_vendor": target["vendor"],
        "competing_vendor": competitor["vendor"],
        "turns": [asdict(t) for t in turns],
        "winner": next((t.cites[0].split(":")[1] for t in turns if t.role == "referee" and t.cites), "unknown"),
        "list_price_per_host_mo": target["list_price_per_host_mo"],
        "final_price_per_host_mo": next((t.price_target_per_host_mo for t in reversed(turns) if t.role == "referee"), None),
        "hosts": target["hosts"],
    }


def _play(quotes: list[dict[str, Any]]) -> Iterator[NegotiationTurn]:
    if len(quotes) < 2:
        return
    target, competitor = quotes[0], quotes[1]
    current = target["quoted_price_per_host_mo"]
    accumulated: list[NegotiationTurn] = []

    for round_no in (1, 2, 3):
        hb = _hb_round(round_no, target, competitor, current)
        accumulated.append(hb)
        yield hb
        if hb.price_target_per_host_mo:
            current = hb.price_target_per_host_mo

        dp = _dp_round(round_no, target, current)
        accumulated.append(dp)
        yield dp
        if dp.price_target_per_host_mo:
            current = dp.price_target_per_host_mo

    yield _referee(accumulated, target)


def stream(quotes: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Yield each turn for the live dashboard."""
    if len(quotes) < 2:
        yield {"role": "error", "text": "need >=2 quotes", "cites": [], "mocked": True, "round": 0}
        return
    for turn in _play(quotes):
        yield asdict(turn)
