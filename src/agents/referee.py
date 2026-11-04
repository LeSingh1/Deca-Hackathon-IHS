"""
REFEREE (Opus 5.5, adaptive thinking). Judges the two negotiation lanes.

The *choice* is made on first-year net dollars from src/finance (stay as-is,
Hardball deal, Diplomat deal, switch processors after exit costs). Opus reads
the transcripts and writes the rationale; its thinking summary is shown
collapsed in the UI. The rationale must pass the number guard (every $ and %
it quotes must be a calculator output) or the template is used.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..finance import net_switch_benefit
from ..llm.client import LLM
from ..llm.guard import numbers_ok
from . import fixtures
from .rate_scout import Baseline, best_competitor, plan_from, price


class RefereeOut(BaseModel):
    rationale: str = Field(description="3-4 sentences for the owner: which deal wins and why, in plain words")


def options(b: Baseline, final: dict[str, dict]) -> list[dict]:
    comp = best_competitor()
    sw = price(plan_from(comp["plan"]), b)
    rows = [
        ("stay", "Do nothing", b.current_rate, b.current_cost, 0.0),
        ("hardball", f"Hardball: {final['hardball']['label'].removeprefix('Rep: ')}",
         final["hardball"]["effective_rate"], final["hardball"]["monthly_cost"], 0.0),
        ("diplomat", f"Diplomat: {final['diplomat']['label'].removeprefix('Rep: ')}",
         final["diplomat"]["effective_rate"], final["diplomat"]["monthly_cost"], 0.0),
        ("switch", f"Switch to {comp['name']} (after exit costs)", sw["effective_rate"], sw["monthly_cost"],
         b.exit_cost.total),
    ]
    out = []
    for key, label, rate, cost, one_time in rows:
        nb = net_switch_benefit(round(b.current_cost - cost, 2), one_time)
        out.append({"key": key, "label": label, "effective_rate": rate, "annual_savings": nb.annual_savings,
                    "one_time_costs": nb.one_time_costs, "net_first_year": nb.net_first_year,
                    "payback_months": nb.payback_months})
    return out


def pick(opts: list[dict]) -> dict:
    return max((o for o in opts if o["key"] != "stay"), key=lambda o: o["net_first_year"])


def _money(x: float) -> str:
    return f"${abs(x):,.0f}"


def template_rationale(opts: list[dict], winner: dict) -> str:
    neg = fixtures.load("negotiation")
    by = {o["key"]: o for o in opts}
    if winner["key"] != "hardball":
        return (f"{winner['label']} wins with {_money(winner['net_first_year'])} net in the first year, "
                "the best of the four options after exit costs.")
    sw = by["switch"]
    return neg["referee_rationale"].format(
        hardball_label=winner["label"].removeprefix("Hardball: ").split(",")[0],
        hardball_annual=_money(winner["annual_savings"]),
        switch_annual=_money(sw["annual_savings"]),
        switch_one_time=_money(sw["one_time_costs"]),
        switch_net_abs=_money(sw["net_first_year"]),
        switch_net_word="behind" if sw["net_first_year"] < 0 else "ahead",
        hb_minus_dp=_money(winner["annual_savings"] - by["diplomat"]["annual_savings"]),
    )


def allowed_numbers(opts: list[dict], b: Baseline) -> tuple[list[float], list[float]]:
    money: list[float] = [b.current_cost, b.exit_cost.total, b.exit_cost.flat_fee,
                          b.exit_cost.liquidated_damages, b.exit_cost.lease_buyout]
    pct: list[float] = []
    for o in opts:
        money += [o["annual_savings"], o["one_time_costs"], abs(o["net_first_year"]), o["annual_savings"] / 12]
        pct.append(round(o["effective_rate"] * 100, 2))
    for a in opts:
        for c in opts:
            money.append(abs(a["annual_savings"] - c["annual_savings"]))
    neg = fixtures.load("negotiation")
    for lane in neg["ladder"].values():
        for step in lane:
            pct.append(round(step["markup_pct"] * 100, 2))
            money.append(step["per_txn"])
    comp = best_competitor()["plan"]
    pct.append(round(comp["markup_pct"] * 100, 2))
    money += [comp["per_txn"], *comp.get("monthly_fees", {}).values()]
    return money, pct


def judge(b: Baseline, final: dict[str, dict], transcripts: dict, llm: LLM) -> dict:
    opts = options(b, final)
    winner = pick(opts)
    neg = fixtures.load("negotiation")
    rationale = template_rationale(opts, winner)
    summary = neg["referee_reasoning_summary"]
    live = False
    if llm.is_live("referee"):
        money, pct = allowed_numbers(opts, b)
        tx = "\n\n".join(
            f"## {lane.upper()} lane\n" + "\n".join(f"R{t['round']} {t['speaker']}: {t['text']}" for t in turns)
            for lane, turns in transcripts.items()
        )
        table = "\n".join(
            f"- {o['key']}: {o['label']} | rate {o['effective_rate'] * 100:.2f}% | annual savings ${o['annual_savings']:,.2f} "
            f"| one-time ${o['one_time_costs']:,.2f} | first-year net ${o['net_first_year']:,.2f}" for o in opts
        )
        res = llm.structured(
            "referee", shared_context=fixtures.shared_context(), schema=RefereeOut,
            instructions=("You are the REFEREE. The calculator has ranked the options by first-year net dollars; "
                          f"the winner is '{winner['key']}'. Read both negotiation transcripts and explain to the owner, "
                          "in 3-4 plain sentences, why this deal beats the others, including why switching does or "
                          "doesn't pay after exit costs. Quote only numbers from the table."),
            content=f"Options (calculator output):\n{table}\n\nTranscripts:\n{tx}",
            validate=lambda r: numbers_ok(r.rationale, money, pct),
        )
        if res.value is not None:
            rationale = res.value.rationale  # type: ignore[attr-defined]
            summary = res.thinking_summary or summary
            live = True
    return {"winner": winner["key"], "winner_option": winner, "options": opts,
            "rationale": rationale, "reasoning_summary": summary, "live": live}
