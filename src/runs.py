"""
Run manager: one background thread per run produces contract events into an
append-only log; any number of SSE subscribers replay + tail it. Owner
replies (simulator or Twilio) resolve the approval gate.

Pacing (seconds slept AFTER each event):
  presenter ~75s end to end (excluding time waiting for YES), fast ~10s,
  instant 0 (tests, batch).
"""
from __future__ import annotations

import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

from . import contract, pipeline
from .channels import twilio
from .executor.actions import Approval

PRESENTER_DELAY = {
    "run_started": 0.4, "owner_message": 1.6, "stage_start": 0.9, "stage_done": 0.5,
    "line_item": 0.32, "fee_flagged": 0.75, "rate_computed": 2.6, "negotiation_turn": 0.085,
    "referee_verdict": 4.0, "apr_revealed": 4.5, "redline": 0.85, "draft": 1.5,
    "approval_requested": 0.4, "approval_received": 0.6, "action_executed": 1.4,
    "ledger_update": 2.0, "summary": 0.5, "cost_log": 0.0, "done": 0.0, "error": 0.0,
}
TURN_DONE_DELAY = 0.9          # extra pause when a negotiation turn completes
PACE_FACTOR = {"presenter": 0.9, "fast": 0.12, "instant": 0.0}
YES_WORDS = {"YES", "Y", "YEP", "YEAH", "YUP", "OK", "OKAY", "SI", "SURE", "APPROVE", "APPROVED", "CONFIRM", "ACCEPT"}
YES_PHRASES = ("DO IT", "LOCK IT IN", "GO AHEAD", "SOUNDS GOOD")
NO_WORDS = {"NO", "N", "NOPE", "NAH", "STOP", "CANCEL", "DECLINE", "REJECT"}
REFUSALS = ("DONT", "DO NOT")
HEDGES = {"BUT", "WAIT", "NOT", "HOLD", "UNLESS", "MAYBE", "IF", "LATER", "WHAT", "WHY", "HOW", "WHO", "WHEN"}
UNCLEAR_REPLY = "Nothing has moved yet. Reply YES to lock it in, or NO to stop."


def parse_reply(body: str) -> bool | None:
    """True = approved, False = declined, None = unclear (ask again).

    Money moves on this answer, so approval needs a reply that opens with a clear
    yes and hedges nothing. Anything doubtful keeps the gate closed and asks again.
    """
    if "?" in body:
        return None
    text = " ".join(re.sub(r"[^A-Z ]", " ", re.sub(r"['’]", "", body.upper())).split())
    words = text.split()
    if not words:
        return None
    if text.startswith(REFUSALS):
        return False
    if HEDGES & set(words):
        return None
    says_no = bool(NO_WORDS & set(words))
    says_yes = words[0] in YES_WORDS or text.startswith(YES_PHRASES)
    if says_yes == says_no:
        return None
    return says_yes


def delay_for(ev: dict, pace: str) -> float:
    f = PACE_FACTOR.get(pace, 1.0)
    d = PRESENTER_DELAY.get(ev["event"], 0.3)
    if ev["event"] == "negotiation_turn" and ev.get("done"):
        d += TURN_DONE_DELAY
    return d * f


@dataclass
class Run:
    id: str
    phone: str
    pace: str
    channel: str
    media: list[str]
    events: list[dict] = field(default_factory=list)
    cond: threading.Condition = field(default_factory=threading.Condition)
    awaiting: str | None = None
    approval: Approval | None = None
    approval_flag: threading.Event = field(default_factory=threading.Event)
    finished: bool = False
    state: dict[str, Any] = field(default_factory=dict)
    auto_approve: str | None = None      # "YES"/"NO" for tests and batch runs
    _reply_lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, ev: dict) -> dict:
        with self.cond:
            ev = {**ev, "run_id": self.id, "seq": len(self.events)}
            contract.validate_event(ev)      # the frozen contract is enforced at runtime too
            self.events.append(ev)
            self.cond.notify_all()
        if ev["event"] == "owner_message" and ev["direction"] == "out" and self.channel == "twilio":
            twilio.send_sms(self.phone, ev["body"])
        return ev

    def wait_for_approval(self, approval_id: str) -> Approval | None:
        self.awaiting = approval_id
        if self.auto_approve is not None:
            self.receive_reply(self.auto_approve, emit_message=True)
        timeout = float(os.getenv("SHADOWBUYER_APPROVAL_TIMEOUT_S", "900"))
        self.approval_flag.wait(timeout)
        self.awaiting = None
        return self.approval

    def receive_reply(self, body: str, emit_message: bool = True) -> bool:
        """Answer the approval gate. Returns False if nothing is awaiting.

        A clear yes or no is final; an unclear reply is answered and the gate stays open.
        """
        with self._reply_lock:
            if self.awaiting is None:
                return False
            if emit_message:
                self.emit({"event": "owner_message", "direction": "in", "body": body, "media": [],
                           "channel": self.channel})
            decision = parse_reply(body)
            if decision is None:
                self.emit({"event": "owner_message", "direction": "out", "body": UNCLEAR_REPLY, "media": [],
                           "channel": self.channel})
                return True
            self.approval = Approval(self.awaiting, decision, body)
            self.awaiting = None
            self.approval_flag.set()
            return True

    def subscribe(self, from_seq: int = 0, heartbeat_s: float = 15.0) -> Iterator[dict | None]:
        """Replay then tail. Yields None as a heartbeat when idle."""
        i = from_seq
        while True:
            with self.cond:
                if i >= len(self.events) and not self.finished:
                    self.cond.wait(heartbeat_s)
                batch = self.events[i:]
                finished = self.finished
            if not batch:
                if finished:
                    return
                yield None
                continue
            for ev in batch:
                yield ev
            i += len(batch)


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def latest_awaiting(self, phone: str, channel: str) -> Run | None:
        with self._lock:
            runs = [r for r in self._runs.values() if r.phone == phone and r.channel == channel and r.awaiting]
        return runs[-1] if runs else None

    def start(self, *, phone: str, media: list[str], body: str = "", pace: str = "presenter",
              channel: str = "simulator", auto_approve: str | None = None, background: bool = True) -> Run:
        run = Run(id=uuid.uuid4().hex[:12], phone=phone, pace=pace, channel=channel, media=media,
                  auto_approve=auto_approve)
        with self._lock:
            self._runs[run.id] = run
        if background:
            threading.Thread(target=self._produce, args=(run, body), daemon=True, name=f"run-{run.id}").start()
        else:
            self._produce(run, body)
        return run

    def _produce(self, run: Run, body: str) -> None:
        from .health import services
        ctx = pipeline.RunContext(run_id=run.id, phone=run.phone, media=run.media,
                                  wait_for_approval=run.wait_for_approval, channel=run.channel, state=run.state)
        demo = all(m.startswith("fixture:") for m in run.media)
        owner = {"phone": run.phone, "name": "Maria Russo" if demo else "",
                 "business": "Mario's Trattoria" if demo else ""}
        try:
            first = [
                {"event": "run_started", "pace": run.pace, "services": services(), "owner": owner},
                {"event": "owner_message", "direction": "in", "body": body or "Here's my card statement",
                 "media": run.media, "channel": run.channel},
            ]
            for ev in first:
                run.emit(ev)
                time.sleep(delay_for(ev, run.pace))
            for ev in pipeline.run(ctx):
                run.emit(ev)
                time.sleep(delay_for(ev, run.pace))
        except Exception as e:  # never leave a subscriber hanging
            run.emit({"event": "error", "message": f"{type(e).__name__}: {e}"})
            run.emit({"event": "done", "ok": False})
        finally:
            with run.cond:
                run.finished = True
                run.cond.notify_all()
