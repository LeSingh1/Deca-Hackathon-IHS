#!/usr/bin/env python3
"""
One command to confirm the live integrations once keys are set:

    set -a; . ./.env; set +a; .venv/bin/python scripts/live_check.py --require-live

Runs the full demo once and reports which services and agents really ran live and
which fell back to fixtures. With ANTHROPIC_API_KEY set this makes real, paid API
calls. With a Stripe test key it creates one test-mode PaymentIntent. No SMS is sent.
Exits 1 under --require-live if Claude is mock or any stage fell back to a fixture.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SHADOWBUYER_MEMORY_PATH", str(Path(tempfile.mkdtemp()) / "memory.json"))

from src.health import services  # noqa: E402
from src.runs import RunManager  # noqa: E402

FALLBACK_WORDS = ("mock", "fixture", "template", "taxonomy")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--require-live", action="store_true", help="fail unless Claude ran live with no fallbacks")
    args = parser.parse_args()

    chips = services()
    for name, mode in chips.items():
        print(f"{name}: {mode}")

    run = RunManager().start(phone="+15550100", media=["fixture:statement_marios_trattoria_oct"], pace="instant",
                             auto_approve="YES", background=False)
    errors = [e["message"] for e in run.events if e["event"] == "error"]

    print("\nagents:")
    seen: dict[str, dict] = {e["agent"]: e for e in run.events if e["event"] == "cost_log"}
    for agent, e in seen.items():
        print(f"  {agent:18s} {e['model']:20s} {'live' if e['live'] else 'mock'}")
    print(f"  run cost: ${run.events and max([e['run_total_usd'] for e in run.events if e['event'] == 'cost_log'] or [0]):.4f}")

    fallbacks = [f"{e['stage']}: {e['note']}" for e in run.events
                 if e["event"] == "stage_done" and e.get("note") and any(w in e["note"] for w in FALLBACK_WORDS)]
    print("\nfell back to fixtures:" if fallbacks else "\nno stage fell back to fixtures")
    for f in fallbacks:
        print(f"  {f}")

    for e in run.events:
        if e["event"] == "action_executed" and e["action"] == "savings_sweep":
            print(f"\nsavings sweep: {e['provider']} {e['ref']} ({e['detail'].get('status')})")
            if e["detail"].get("stripe_error"):
                print(f"  stripe error: {e['detail']['stripe_error']}")
    summary = [e for e in run.events if e["event"] == "summary"]
    print(f"headline: {summary[0]['headline'] if summary else 'none'}")
    for message in errors:
        print(f"ERROR: {message}")

    if errors or not summary:
        return 1
    if args.require_live and (chips["claude"] != "live" or fallbacks or not all(e["live"] for e in seen.values())):
        print("\nnot fully live", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
