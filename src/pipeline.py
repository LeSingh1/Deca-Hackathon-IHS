"""
ShadowBuyer for Main Street: the pipeline.

Statement Reader -> Fee Hunter -> Rate Scout -> Negotiator swarm (+ Referee)
-> Contract Exposer -> Action Drafter -> owner approval -> Executor -> ledger

`run(ctx)` is a generator of contract event dicts (without run_id/seq; the
run manager stamps those). It blocks at the approval stage on
ctx.wait_for_approval(), so nothing leaves the building without a YES.
Every number in a headline comes from src/finance via the agents.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from .agents import action_drafter, contract_exposer, fee_hunter, fixtures, negotiator, rate_scout, referee, statement_reader
from .executor import actions
from .executor.actions import Approval
from .finance import fee_breakdown
from .llm.client import LLM, CostTracker, Usage
from .llm.models import model_for
from .memory import store


@dataclass
class RunContext:
    run_id: str
    phone: str
    media: list[str]
    wait_for_approval: Callable[[str], Approval | None]
    channel: str = "simulator"
    state: dict[str, Any] = field(default_factory=dict)   # filled in for the PDF + snapshot
    _pending_costs: list[dict] = field(default_factory=list)
    llm: LLM = field(init=False)

    def __post_init__(self) -> None:
        def on_usage(u: Usage, total: float) -> None:
            self._pending_costs.append({
                "event": "cost_log", "agent": u.agent, "model": u.model, "live": u.live,
                "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                "cache_read_tokens": u.cache_read_tokens, "usd": u.usd, "run_total_usd": total,
            })
        self.llm = LLM(CostTracker(on_usage))

    def drain_costs(self) -> Iterator[dict]:
        while self._pending_costs:
            yield self._pending_costs.pop(0)


def _stage(stage: str, label: str, agent: str, llm: LLM, agents: tuple[str, ...] = ()) -> dict:
    names = agents or ((agent,) if agent in _AGENT_KEYS else ())
    models = " / ".join(dict.fromkeys(model_for(a).model for a in names)) or None
    return {"event": "stage_start", "stage": stage, "label": label, "agent": agent, "model": models,
            "live": any(llm.is_live(a) for a in names)}


_AGENT_KEYS = {"statement_reader", "fee_hunter", "hardball", "diplomat", "processor_rep", "referee",
               "contract_exposer", "action_drafter"}


def _done(stage: str, t0: float, note: str | None = None) -> dict:
    return {"event": "stage_done", "stage": stage, "ms": int((time.monotonic() - t0) * 1000), "note": note}


def owner_say(body: str, ctx: RunContext, direction: str = "out", media: list[str] | None = None) -> dict:
    return {"event": "owner_message", "direction": direction, "body": body, "media": media or [],
            "channel": ctx.channel}


def run(ctx: RunContext) -> Iterator[dict]:
    llm, st = ctx.llm, ctx.state
    yield owner_say("Got it. Reading your statement now. Give me about a minute.", ctx)

    # 1 ── Statement Reader ───────────────────────────────────────────
    t0 = time.monotonic()
    yield _stage("statement_reader", "Reading the statement photo", "statement_reader", llm)
    statement, parsed_live = statement_reader.read(ctx.media, llm)
    if not parsed_live and any(m.startswith("file:") for m in ctx.media):
        # A real owner sent this. Never answer with the fictional fixture's numbers.
        yield from ctx.drain_costs()
        yield _done("statement_reader", t0, "could not read the upload")
        yield owner_say("Sorry, I couldn't read that statement, so I haven't changed anything. Try a clear, flat "
                        "photo of the whole page, or text DEMO to see a sample run.", ctx)
        yield {"event": "done", "ok": False}
        return
    st["statement"] = statement
    items = statement["line_items"]
    for i, li in enumerate(items):
        yield {"event": "line_item", "item": {k: li.get(k) for k in ("id", "description", "amount", "detail")},
               "index": i, "total_items": len(items)}
    yield from ctx.drain_costs()
    yield _done("statement_reader", t0, "live vision parse" if parsed_live else "fixture parse (mock)")

    # 2 ── Fee Hunter ─────────────────────────────────────────────────
    t0 = time.monotonic()
    yield _stage("fee_hunter", "Hunting hidden fees", "fee_hunter", llm)
    classified, cls_live = fee_hunter.classify(items, llm)
    breakdown = fee_breakdown(classified)
    st["classified"], st["breakdown"] = classified, breakdown.to_dict()
    hidden = 0.0
    for li in classified:
        if not fee_hunter.is_flagged(li):
            continue
        if li["category"] in ("processor_markup", "junk_fee"):
            hidden = round(hidden + li["amount"], 2)
        yield {"event": "fee_flagged", "item_id": li["id"], "category": li["category"], "tag": li["tag"],
               "amount": li["amount"], "reason": li["reason"], "hidden_total": hidden}
    yield from ctx.drain_costs()
    yield _done("fee_hunter", t0, "live classification" if cls_live else "taxonomy rules (mock)")

    # 3 ── Rate Scout ─────────────────────────────────────────────────
    t0 = time.monotonic()
    yield _stage("rate_scout", "Benchmarking against fair interchange-plus and competitor quotes", "rate_scout", llm)
    b = rate_scout.baseline(statement, breakdown)
    quotes = rate_scout.quotes(statement, b)
    st["baseline"], st["quotes"] = b, quotes
    yield {"event": "rate_computed", "monthly_volume": statement["monthly_volume"], "annual_volume": b.annual_volume,
           "transaction_count": statement["transaction_count"], "total_fees": breakdown.total,
           "effective_rate": b.current_rate, "breakdown": breakdown.by_category, "quotes": quotes}
    yield _done("rate_scout", t0)

    if any(m.startswith("file:") for m in ctx.media):
        # A real owner: the steps below use a simulated rep and the fictional agreement and
        # cash advance, so they stop here with only what their own statement shows.
        fair = next(q for q in quotes if q["kind"] == "benchmark")
        store.write("statements", f"{ctx.phone}:{statement['period']['label']}",
                    {"effective_rate": b.current_rate, "total_fees": breakdown.total})
        yield owner_say(action_drafter.real_statement_sms(
            hidden_monthly=breakdown.processor_controlled, current_rate=b.current_rate,
            fair_rate=fair["effective_rate"], annual=fair["annual_savings"], processor=statement["processor"]), ctx)
        yield {"event": "done", "ok": True}
        return

    # 4 ── Negotiator swarm + Referee ─────────────────────────────────
    t0 = time.monotonic()
    prior = store.read("tactics", statement["processor"])
    label = f"Hardball and Diplomat vs. {statement['processor']} retention rep"
    if prior:
        label += f" (last time {prior['winner']} won)"
    yield _stage("negotiator", label, "negotiator_swarm", llm,
                 agents=("hardball", "diplomat", "processor_rep", "referee"))
    neg: dict[str, Any] = {}
    yield from negotiator.stream(statement, b, llm, neg, prior)
    yield from ctx.drain_costs()
    verdict = referee.judge(b, neg["final"], neg["transcripts"], llm)
    st["negotiation"], st["verdict"] = neg, verdict
    yield {"event": "referee_verdict", "winner": verdict["winner"], "options": verdict["options"],
           "rationale": verdict["rationale"], "reasoning_summary": verdict["reasoning_summary"]}
    yield from ctx.drain_costs()
    yield _done("negotiator", t0, "live referee" if verdict["live"] else "template rationale (mock)")

    # 5 ── Contract Exposer ───────────────────────────────────────────
    t0 = time.monotonic()
    yield _stage("contract_exposer", "Exposing the MCA's true APR and contract traps", "contract_exposer", llm)
    ce = contract_exposer.expose(b, statement, llm)
    m = ce["mca"]
    offer = fixtures.load("mca_offer_fastfund")
    st["mca"], st["mca_schedule"], st["redlines"] = m, ce["schedule"], ce["redlines"]
    yield {"event": "apr_revealed", "lender": offer["lender"], "advertised": f"{offer['factor_rate']:.2f} factor",
           "advance": m.advance, "net_funded": m.net_funded, "payback": m.payback, "finance_charge": m.finance_charge,
           "daily_remittance": m.daily_remittance, "term_days": m.term_days, "apr": m.apr,
           "effective_annual_rate": m.effective_annual_rate, "schedule": ce["schedule"]}
    for r in ce["redlines"]:
        yield {"event": "redline", **r}
    yield from ctx.drain_costs()
    yield _done("contract_exposer", t0, "live redlines" if ce["live"] else "fixture redlines (mock)")

    # 6 ── Action Drafter ─────────────────────────────────────────────
    t0 = time.monotonic()
    yield _stage("action_drafter", "Drafting the rep email and your text", "action_drafter", llm)
    win = verdict["winner_option"]
    win_final = neg["final"].get(verdict["winner"]) or neg["final"]["hardball"]
    email, email_live = action_drafter.rep_email(statement, win_final, llm)
    monthly = round(win["annual_savings"] / 12, 2)
    sms = action_drafter.sms_summary(
        hidden_monthly=breakdown.processor_controlled, current_rate=b.current_rate,
        new_rate=win["effective_rate"], annual=win["annual_savings"], monthly=monthly,
        apr=m.apr, lender=offer["lender"], processor=statement["processor"].split()[0],
    )
    st["email"], st["sms"], st["monthly_savings"] = email, sms, monthly
    yield {"event": "draft", "kind": "rep_email", "to": email["to"], "subject": email["subject"],
           "body": email["body"], "dry_run": True}
    yield from ctx.drain_costs()
    yield _done("action_drafter", t0, "live draft" if email_live else "template draft (mock)")
    yield owner_say(sms, ctx)

    # 7 ── Approval gate ──────────────────────────────────────────────
    t0 = time.monotonic()
    approval_id = f"apv_{ctx.run_id}"
    yield _stage("approval", "Waiting for the owner's YES", "owner", llm)
    yield {"event": "approval_requested", "approval_id": approval_id,
           "actions": ["Email the accepted offer to the processor rep (dry run)",
                       f"Move {action_drafter.money(monthly, True)} to {actions.RESERVE_LABEL} ({actions.sweep_rail()})"],
           "prompt": "Reply YES to lock it in, or NO to stop."}
    approval = ctx.wait_for_approval(approval_id)
    approved = bool(approval and approval.approved)
    st["approval"] = approval
    yield {"event": "approval_received", "approval_id": approval_id, "approved": approved,
           "body": approval.body if approval else "(no reply)"}
    yield _done("approval", t0, "approved" if approved else "declined")

    # 8 ── Executor ───────────────────────────────────────────────────
    executed: list[dict] = []
    if approved:
        t0 = time.monotonic()
        yield _stage("executor", "Executing the approved actions (sandbox)", "executor", llm)
        executed = [
            actions.rep_email(approval, email),
            actions.fee_receipt(approval, b.current_rate, win["effective_rate"]),
            actions.savings_sweep(approval, monthly, ctx.run_id, statement["merchant"]["name"]),
        ]
        for a in executed:
            yield {"event": "action_executed", **a}
        yield {"event": "ledger_update", "entries": [
            {"label": "Recovered processing fees", "from_bucket": "Processor fees", "to_bucket": "Back in your pocket",
             "amount": monthly},
            {"label": "Month-1 savings sweep", "from_bucket": "Back in your pocket", "to_bucket": actions.RESERVE_LABEL,
             "amount": monthly},
        ], "back_in_pocket_monthly": monthly, "back_in_pocket_annual": win["annual_savings"]}
        yield _done("executor", t0)
        yield owner_say(
            f"Done. Rep email drafted (dry run) and {action_drafter.money(monthly, True)} moved to your "
            f"{actions.RESERVE_LABEL} ({actions.sweep_rail()}). Your lender-ready report: tap to download.", ctx)
    else:
        yield owner_say("No problem. Nothing was sent and no money moved.", ctx)
    st["executed"] = executed

    # memory: next month's run starts smarter
    store.write("owner_profiles", ctx.phone, {"owner": statement["merchant"]["owner"],
                                              "business": statement["merchant"]["name"],
                                              "annual_volume": b.annual_volume})
    store.write("statements", f"{ctx.phone}:{statement['period']['label']}",
                {"effective_rate": b.current_rate, "total_fees": breakdown.total})
    store.write("decisions", ctx.run_id, {"winner": verdict["winner"], "approved": approved,
                                          "annual_savings": win["annual_savings"]})
    store.write("tactics", statement["processor"], {"winner": verdict["winner"],
                                                    "final_rate": win["effective_rate"]})

    yield {"event": "summary",
           "headline": f"{b.current_rate * 100:.2f}% → {win['effective_rate'] * 100:.2f}% = "
                       f"{action_drafter.money(win['annual_savings'])}/yr back",
           "current_rate": b.current_rate, "new_rate": win["effective_rate"],
           "annual_savings": win["annual_savings"], "monthly_savings": monthly,
           "hidden_fees_monthly": breakdown.processor_controlled, "mca_apr": m.apr,
           "report_url": f"/api/runs/{ctx.run_id}/report.pdf"}
    yield {"event": "done", "ok": True}
