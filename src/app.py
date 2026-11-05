"""
FastAPI app: owner channel webhooks, SSE run stream, report PDF, static UI.

  GET  /healthz
  GET  /api/services                     live/mock per service (header chips)
  POST /api/sms/inbound                  phone simulator (JSON) -> same handler as Twilio
  POST /sms/twilio                       Twilio webhook (form) -> TwiML
  POST /api/demo/start                   "Run demo": the owner texts the fixture statement photo
  GET  /api/runs/{id}/events             SSE stream (replay + tail), ?from=<seq>
  GET  /api/runs/{id}                    snapshot of events so far
  GET  /api/runs/{id}/report.pdf         lender/accountant-ready PDF
  GET  /                                 built frontend (frontend/dist) if present
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .channels import twilio
from .contract import CONTRACT_VERSION
from .health import services
from .runs import RunManager

FIXTURE_MEDIA = "fixture:statement_marios_trattoria_oct"
DEMO_PHONE = "+1 (718) 555-0142"
PACES = {"presenter", "fast", "instant"}

app = FastAPI(title="ShadowBuyer for Main Street", version=CONTRACT_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
runs = RunManager()


class Inbound(BaseModel):
    from_: str = Field(default=DEMO_PHONE, alias="from")
    body: str = ""
    media: list[str] = Field(default_factory=list)
    pace: str = "presenter"
    run_id: str | None = None     # the run this simulator is watching; shared demos share one phone number


def _non_negative_int(value: object) -> int:
    """Untrusted numeric input: anything that isn't a plain non-negative integer counts as 0."""
    text = str(value) if value is not None else ""
    return int(text) if text.isdigit() else 0


def handle_inbound(phone: str, body: str, media: list[str], pace: str, channel: str) -> dict[str, Any]:
    """One handler for both the simulator and Twilio."""
    pending = runs.latest_awaiting(phone, channel)
    if pending and not media:
        pending.receive_reply(body)
        return {"run_id": pending.id, "kind": "reply", "replies": []}
    if media or body.strip().lower() in {"statement", "demo", "run", "start"}:
        run = runs.start(phone=phone, media=media or [FIXTURE_MEDIA], body=body, channel=channel,
                         pace=pace if pace in PACES else "presenter")
        return {"run_id": run.id, "kind": "new_run",
                "replies": ["Got it. Reading your statement now. Give me about a minute."]}
    return {"run_id": None, "kind": "help",
            "replies": ["Text me a photo of your card-processing statement and I'll find the hidden fees."]}


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "service": "shadowbuyer-main-street", "contract": CONTRACT_VERSION, "services": services()}


@app.get("/api/services")
def api_services() -> dict[str, str]:
    return services()


@app.post("/api/sms/inbound")
def sms_inbound(msg: Inbound) -> dict[str, Any]:
    # The simulator is unauthenticated: it may only use the demo fixture (never a server
    # path) and may only answer simulator runs (never a real owner's approval).
    if any(m != FIXTURE_MEDIA for m in msg.media):
        raise HTTPException(400, "the simulator only accepts the demo statement")
    if msg.run_id is not None:
        run = runs.get(msg.run_id)
        if not run or run.channel != "simulator":
            raise HTTPException(404, "unknown run")
        run.receive_reply(msg.body)
        return {"run_id": run.id, "kind": "reply", "replies": []}
    return handle_inbound(msg.from_, msg.body, msg.media, msg.pace, "simulator")


@app.post("/api/demo/start")
def demo_start(pace: str = "presenter") -> dict[str, Any]:
    return handle_inbound(DEMO_PHONE, "Here's my October statement. Am I getting ripped off?",
                          [FIXTURE_MEDIA], pace, "simulator")


@app.post("/sms/twilio")
async def sms_twilio(request: Request) -> Response:
    form = await request.form()
    # A valid signature proves Twilio sent this, so a forged "YES" can't approve anything.
    if twilio.mode() == "live":
        params = {k: str(v) for k, v in form.items()}
        if not twilio.valid_signature(twilio.webhook_url(str(request.url)), params,
                                      request.headers.get("x-twilio-signature", "")):
            raise HTTPException(403, "invalid Twilio signature")
    phone, body = str(form.get("From", "")), str(form.get("Body", ""))
    media = []
    for i in range(_non_negative_int(form.get("NumMedia"))):
        m = twilio.download_media(str(form.get(f"MediaUrl{i}")), str(form.get(f"MediaContentType{i}") or ""))
        if m:
            media.append(m)
    res = handle_inbound(phone, body, media, "fast", "twilio")
    # New-run acks are sent by the run itself; TwiML only carries help text.
    return Response(twilio.twiml(res["replies"] if res["kind"] == "help" else []), media_type="application/xml")


@app.get("/api/runs/{run_id}")
def run_snapshot(run_id: str) -> JSONResponse:
    run = runs.get(run_id)
    if not run:
        raise HTTPException(404, "unknown run")
    return JSONResponse({"run_id": run.id, "finished": run.finished, "awaiting": run.awaiting, "events": run.events})


@app.get("/api/runs/{run_id}/events")
def run_events(run_id: str, request: Request) -> StreamingResponse:
    run = runs.get(run_id)
    if not run:
        raise HTTPException(404, "unknown run")
    # EventSource reconnects send Last-Event-ID; resume right after it (no duplicates).
    last = request.headers.get("last-event-id")
    start = int(last) + 1 if last and last.isdigit() else _non_negative_int(request.query_params.get("from"))

    def gen():
        for ev in run.subscribe(start):
            if ev is None:
                yield ": keep-alive\n\n"
                continue
            yield f"id: {ev['seq']}\nevent: {ev['event']}\ndata: {json.dumps(ev, default=str)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/runs/{run_id}/report.pdf")
def run_report(run_id: str) -> Response:
    run = runs.get(run_id)
    if not run or "verdict" not in run.state:
        raise HTTPException(404, "report not ready")
    from .report.pdf import build_report
    pdf = build_report(run.state, run_id=run.id)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="shadowbuyer-{run.id}.pdf"'})


_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def mount_ui(target: FastAPI, dist: Path) -> None:
    """Serve the built frontend from `dist`, falling back to index.html for SPA routes."""
    target.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @target.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        root = dist.resolve()
        f = (root / path).resolve()     # the route decodes %2f, so `path` may contain ../
        return FileResponse(f if path and f.is_relative_to(root) and f.is_file() else root / "index.html")


if _DIST.exists():
    mount_ui(app, _DIST)
