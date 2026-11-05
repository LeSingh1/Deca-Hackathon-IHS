"""
NEGOTIATOR SWARM. Two lanes run side by side against a simulated Processor Rep:

  HARDBALL (Sonnet 5.5)  competitor quote + switch threat
  DIPLOMAT (Sonnet 5.5)  loyalty + growth, relationship-preserving
  PROCESSOR REP (Haiku 5.5) pushes back realistically

3 rounds per lane. Text streams token-by-token (live) or word-by-word from
the fixture script (mock). The rep's *offers* come from a deterministic
concession ladder (fixtures/negotiation.json) and are priced by src/finance,
so the money is never whatever the model happened to say. Live, the rep is
told the exact terms it is authorised to offer and must state them.
"""
from __future__ import annotations

from itertools import zip_longest
from typing import Any, Iterator

from ..llm.client import LLM
from . import fixtures
from .rate_scout import Baseline, plan_from, price

LANES = ("hardball", "diplomat")

_AGENT_BRIEF = {
    "hardball": ("You are HARDBALL, negotiating for the restaurant owner with their card processor's "
                 "retention rep. Be firm and specific. Use the competitor quote as leverage and make "
                 "clear the owner will switch. Push for interchange-plus, removal of every junk fee, "
                 "and waiver of exit clauses."),
    "diplomat": ("You are DIPLOMAT, negotiating for the restaurant owner with their card processor's "
                 "retention rep. Be warm and specific. The owner would like to stay; appeal to loyalty, "
                 "clean history and upcoming growth. Ask for interchange-plus and fee removal."),
}


def _words(text: str, n: int = 3) -> Iterator[str]:
    w = text.split(" ")
    for i in range(0, len(w), n):
        yield " ".join(w[i:i + n]) + (" " if i + n < len(w) else "")


def _offer_terms(step: dict) -> str:
    fees = step.get("monthly_fees") or {}
    fee_txt = ("keeping monthly fees: " + ", ".join(fees)) if fees else "no monthly fees"
    extra = step.get("concessions") or []
    ex = f"; also concede: {', '.join(extra)}" if extra else ""
    return f"interchange plus {step['markup_pct'] * 100:.2f}% and ${step['per_txn']:.2f} per transaction, {fee_txt}{ex}"


def _facts(statement: dict, b: Baseline) -> str:
    comp = fixtures.load("competitor_processors")["quotes"][0]
    surch = sum(li["amount"] for li in statement["line_items"] if "surcharge" in li["description"].lower())
    return (
        f"Owner: {statement['merchant']['owner']}, {statement['merchant']['name']}. "
        f"Processor: {statement['processor']}. Monthly card volume ${statement['monthly_volume']:,.2f}, "
        f"{statement['transaction_count']:,} transactions. All-in effective rate {b.current_rate * 100:.2f}%. "
        f"Tier surcharges this month ${surch:,.2f}. Competitor: {comp['label']} ({comp['terms']})."
    )


def _memory_line(prior: dict) -> str:
    return f"Last time we settled with you at {prior['final_rate'] * 100:.2f}% all-in, so let's start from there."


def stream(statement: dict, b: Baseline, llm: LLM, result: dict[str, Any],
           prior: dict | None = None) -> Iterator[dict]:
    """Yield negotiation_turn event dicts. Fills result['final'][lane] with the
    priced final offer and result['transcripts'][lane] with the full text.

    `prior` is what won last run (from memory). It shapes how the winning lane
    opens; the offers still come from the ladder, so the money can't change."""
    neg = fixtures.load("negotiation")
    facts = _facts(statement, b)
    if prior:
        facts += f" Memory: the {prior['winner']} approach won the last run at {prior['final_rate'] * 100:.2f}% all-in."
    ctx = fixtures.shared_context()
    transcripts: dict[str, list[dict]] = {lane: [] for lane in LANES}
    final: dict[str, dict] = {}

    def agent_turn(lane: str, rnd: int) -> Iterator[str]:
        history = "\n".join(f"{t['speaker'].upper()}: {t['text']}" for t in transcripts[lane]) or "(opening)"
        live = llm.stream(
            lane, shared_context=ctx,
            instructions=_AGENT_BRIEF[lane] + " Under 70 words. No greeting, no sign-off. Quote numbers only from the facts given.",
            messages=[{"role": "user", "content": f"Facts: {facts}\n\nSo far:\n{history}\n\nWrite your round {rnd} of 3 message to the rep."}],
        )
        got = False
        for chunk in live:
            got = True
            yield chunk
        if not got:
            script = neg["scripts"][lane][rnd - 1]
            if prior and rnd == 1 and prior["winner"] == lane:
                script = f"{_memory_line(prior)} {script}"
            yield from _words(script)

    def rep_turn(lane: str, rnd: int, step: dict) -> Iterator[str]:
        last = transcripts[lane][-1]["text"] if transcripts[lane] else ""
        live = llm.stream(
            "processor_rep", shared_context=ctx,
            instructions=(f"You are {neg['rep']['name']}, {neg['rep']['title']}. You protect your company's margin "
                          "and push back realistically, but you are authorised to offer EXACTLY these terms this "
                          f"round and nothing better: {_offer_terms(step)}. State the offer clearly. Under 50 words."),
            messages=[{"role": "user", "content": f"The owner's negotiator said: {last}"}],
        )
        got = False
        for chunk in live:
            got = True
            yield chunk
        if not got:
            yield from _words(neg["scripts"][f"rep_{lane}"][rnd - 1])

    def run_turns(make: dict[str, Iterator[str]], speaker_of: dict[str, str], rnd: int,
                  offers: dict[str, dict] | None = None) -> Iterator[dict]:
        bufs = {lane: [] for lane in make}
        lanes = list(make)
        for chunks in zip_longest(*(make[l] for l in lanes)):
            for lane, chunk in zip(lanes, chunks):
                if chunk is None:
                    continue
                bufs[lane].append(chunk)
                yield {"event": "negotiation_turn", "lane": lane, "round": rnd,
                       "speaker": speaker_of[lane], "delta": chunk, "done": False}
        for lane in lanes:
            text = "".join(bufs[lane]).strip()
            transcripts[lane].append({"round": rnd, "speaker": speaker_of[lane], "text": text})
            ev = {"event": "negotiation_turn", "lane": lane, "round": rnd,
                  "speaker": speaker_of[lane], "delta": "", "done": True}
            if offers:
                ev["offer"] = offers[lane]
            yield ev

    for rnd in (1, 2, 3):
        yield from run_turns({l: agent_turn(l, rnd) for l in LANES}, {l: l for l in LANES}, rnd)
        offers = {}
        steps = {}
        for lane in LANES:
            step = neg["ladder"][lane][rnd - 1]
            steps[lane] = step
            priced = price(plan_from({**step, "keeps_equipment_lease": True}), b)
            offers[lane] = {"label": step["label"], **priced}
            if rnd == 3:
                final[lane] = {**offers[lane], "concessions": step.get("concessions", [])}
        yield from run_turns({l: rep_turn(l, rnd, steps[l]) for l in LANES}, {l: "rep" for l in LANES}, rnd, offers)

    result["final"] = final
    result["transcripts"] = transcripts
