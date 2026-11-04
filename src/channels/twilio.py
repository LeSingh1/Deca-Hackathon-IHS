"""
Twilio SMS channel (sandbox / trial number).

Inbound:  POST /sms/twilio (form-encoded From, Body, NumMedia, MediaUrl0...)
Outbound: replies to the owner on their own thread via the Messages REST API.
          These are the conversation itself; the third-party actions
          (rep email, money movement) are gated by the approval event.

Live when TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER are
set; otherwise send_sms is a no-op and the phone simulator in the UI shows
the same messages from the same event stream.
"""
from __future__ import annotations

import base64
import mimetypes
import os
import tempfile
from urllib import parse, request


def mode() -> str:
    return "live" if all(os.getenv(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER")) else "mock"


def _auth() -> str:
    raw = f"{os.environ['TWILIO_ACCOUNT_SID']}:{os.environ['TWILIO_AUTH_TOKEN']}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def send_sms(to: str, body: str) -> bool:
    if mode() != "live":
        return False
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    data = parse.urlencode({"To": to, "From": os.environ["TWILIO_FROM_NUMBER"], "Body": body[:1500]}).encode()
    req = request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data,
                          headers={"Authorization": _auth()})
    try:
        request.urlopen(req, timeout=8).read()
        return True
    except Exception:
        return False


def download_media(url: str, content_type: str | None = None) -> str | None:
    """Fetch an MMS attachment to a temp file; returns 'file:<path>' for the Statement Reader."""
    if mode() != "live":
        return None
    try:
        req = request.Request(url, headers={"Authorization": _auth()})
        data = request.urlopen(req, timeout=15).read()
    except Exception:
        return None
    ext = mimetypes.guess_extension(content_type or "") or ".jpg"
    fd, path = tempfile.mkstemp(prefix="statement-", suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return f"file:{path}"


def twiml(messages: list[str]) -> str:
    from xml.sax.saxutils import escape
    body = "".join(f"<Message>{escape(m)}</Message>" for m in messages)
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'
