"""
ShadowBuyer pipeline: Scout → Quote Hunter → Negotiator → (Contract Diff) → Output.
- run() returns a full snapshot for batch demos and /api/demo-state
- stream() yields paced events for the live dashboard

Side effects per run: writes vendor profiles, AE quotes, trash-talk intel, and
the referee decision to Evermind. Live when EVERMIND_API_KEY is set; local
JSON fallback otherwise. See src/memory/evermind.py for the four record types.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

from .agents import scout, quote_hunter, negotiator, contract_diff
from .memory import evermind

# Pacing for the live demo. ~3.2s of negotiator turns total — tense but not boring.
PACE_STAGE_S = 0.35
PACE_TURN_S = 0.55


def run(
    category: str = "observability",
    bright_data_input: dict | None = None,
    include_contract_diff: bool = True,
) -> dict[str, Any]:
    s = scout.run(category, bright_data_input)
    q = quote_hunter.run(s["vendors"])
    n = negotiator.run(q["quotes"])
    writes = _evermind_writes(s, q, n)
    out: dict[str, Any] = {"scout": s, "quote_hunter": q, "negotiator": n, "evermind_writes": writes}
    if include_contract_diff:
        out["contract_diff"] = contract_diff.run()
    out["summary"] = _summary(s, q, n, out.get("contract_diff"), writes)
    return out


def _evermind_writes(s: dict, q: dict, n: dict) -> list[dict[str, Any]]:
    """Persist run artifacts to Evermind. Returns one descriptor per write so
    the dashboard / sponsor audit can show what landed where."""
    writes: list[dict[str, Any]] = []

    for v in s.get("vendors", []):
        r = evermind.write_vendor_profile(v["name"], v)
        writes.append({"namespace": r.namespace, "key": r.key, "backend": r.backend})

    for quote in q.get("quotes", []):
        r = evermind.write_ae_quote(quote["vendor"], quote)
        writes.append({"namespace": r.namespace, "key": r.key, "backend": r.backend})
        # Trash-talk intel — only when the AE actually disparaged a competitor.
        dig = (quote.get("ae_response") or {}).get("competitor_dig") or quote.get("competitive_intel") or ""
        if dig.strip():
            targets = _extract_competitor_targets(dig, exclude=quote["vendor"], all_vendors=[v["name"] for v in s.get("vendors", [])])
            r = evermind.write_trash_talk(quote["vendor"], dig, targets)
            writes.append({"namespace": r.namespace, "key": r.key, "backend": r.backend})

    if n and "error" not in n:
        decision_id = f"{n.get('target_vendor', 'unknown')}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        r = evermind.write_decision(decision_id, {
            "target_vendor": n.get("target_vendor"),
            "competing_vendor": n.get("competing_vendor"),
            "winner": n.get("winner"),
            "final_price_per_host_mo": n.get("final_price_per_host_mo"),
            "hosts": n.get("hosts"),
            "turn_count": len(n.get("turns", [])),
        })
        writes.append({"namespace": r.namespace, "key": r.key, "backend": r.backend})

    return writes


def _extract_competitor_targets(dig: str, exclude: str, all_vendors: list[str]) -> list[str]:
    """Find vendor names the AE name-dropped in their dig. Cheap substring match."""
    dig_lower = dig.lower()
    hits = []
    for v in all_vendors:
        if v.lower() == exclude.lower():
            continue
        if v.lower() in dig_lower:
            hits.append(v)
    return hits


def stream(
    category: str = "observability",
    bright_data_input: dict | None = None,
    pace: bool = True,
) -> Iterator[dict[str, Any]]:
    def _sleep(s: float) -> None:
        if pace:
            time.sleep(s)

    yield {"event": "stage_start", "stage": "scout", "label": "Researching observability vendors"}
    _sleep(PACE_STAGE_S)
    s = scout.run(category, bright_data_input)
    yield {"event": "stage_done", "stage": "scout", "payload": s}
    _sleep(PACE_STAGE_S)

    yield {"event": "stage_start", "stage": "quote_hunter", "label": "Pulling vendor quotes via Actionbook"}
    _sleep(PACE_STAGE_S)
    q = quote_hunter.run(s["vendors"])
    yield {"event": "stage_done", "stage": "quote_hunter", "payload": q}
    _sleep(PACE_STAGE_S)

    yield {
        "event": "stage_start",
        "stage": "negotiator",
        "label": f"Adversarial negotiation: {q['quotes'][0]['vendor']} vs {q['quotes'][1]['vendor']}",
        "target_vendor": q["quotes"][0]["vendor"],
        "competing_vendor": q["quotes"][1]["vendor"],
        "list_price_per_host_mo": q["quotes"][0]["list_price_per_host_mo"],
        "starting_quote_per_host_mo": q["quotes"][0]["quoted_price_per_host_mo"],
        "hosts": q["quotes"][0]["hosts"],
    }
    _sleep(PACE_STAGE_S)
    for turn in negotiator.stream(q["quotes"]):
        yield {"event": "negotiator_turn", "turn": turn}
        _sleep(PACE_TURN_S)
    yield {"event": "stage_done", "stage": "negotiator"}

    n = negotiator.run(q["quotes"])
    writes = _evermind_writes(s, q, n)
    if writes:
        yield {"event": "evermind_writes", "count": len(writes), "by_backend": _count_by_backend(writes), "writes": writes}
    _sleep(PACE_STAGE_S)

    yield {"event": "stage_start", "stage": "contract_diff", "label": "Comparing vendor MSA to standard template"}
    _sleep(PACE_STAGE_S)
    cd = contract_diff.run()
    yield {
        "event": "contract_diff_summary",
        "vendor": cd["vendor"],
        "redline_count": cd["redline_count"],
        "severity_counts": cd["severity_counts"],
        "embedding_backend": cd["embedding_backend"],
    }
    _sleep(PACE_STAGE_S)
    for r in cd["redlines"]:
        yield {"event": "redline", "redline": r}
        _sleep(0.18)
    yield {"event": "stage_done", "stage": "contract_diff", "payload": cd}

    yield {"event": "summary", "payload": _summary(s, q, n, cd, writes)}
    yield {"event": "done"}


def _count_by_backend(writes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for w in writes:
        counts[w["backend"]] = counts.get(w["backend"], 0) + 1
    return counts


def _summary(s: dict, q: dict, n: dict, cd: dict | None = None, writes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if "error" in n:
        return {"ok": False, "reason": n["error"]}
    target = q["quotes"][0]
    list_price = target["list_price_per_host_mo"]
    final_price = n.get("final_price_per_host_mo") or target["quoted_price_per_host_mo"]
    hosts = target["hosts"]
    yr1_list_cost = list_price * hosts * 12
    yr1_final_cost = final_price * hosts * 12
    return {
        "ok": True,
        "vendor": n["target_vendor"],
        "competing_vendor": n["competing_vendor"],
        "hosts": hosts,
        "list_price_per_host_mo": list_price,
        "starting_quote_per_host_mo": target["quoted_price_per_host_mo"],
        "final_price_per_host_mo": final_price,
        "annual_savings_vs_list_usd": round(yr1_list_cost - yr1_final_cost, 2),
        "discount_vs_list_pct": round((list_price - final_price) / list_price * 100, 1),
        "winning_strategy": n.get("winner"),
        "round_count": sum(1 for t in n["turns"] if t["role"] in ("hardball", "diplomat")),
        "contract_redline_count": cd["redline_count"] if cd else None,
        "contract_high_severity": cd["severity_counts"].get("high") if cd else None,
        "contract_backend": cd["embedding_backend"] if cd else None,
        "evermind_writes": len(writes) if writes else 0,
        "evermind_backend_counts": _count_by_backend(writes) if writes else {},
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
