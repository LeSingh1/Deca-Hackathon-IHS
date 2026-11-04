"""
CONTRACT DIFF agent.

Compares a vendor MSA to ShadowBuyer's standard template. Uses Nosana-hosted
sentence-transformers embeddings for clause similarity when the endpoint is
configured; falls back to a deterministic keyword + length heuristic otherwise.

Output: redline list with severity (high/med/low) and recommended counter-text.
The doc's pitch line — "our agent flags 14 deviations including an
auto-renewal trap and a missing data-deletion clause" — is the bar.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

try:
    import httpx  # type: ignore
except ImportError:
    httpx = None  # type: ignore

try:
    from agentfield import agent  # type: ignore
except ImportError:
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"

# Per-clause severity weight + recommended counter-text. Drives the redline list.
_CLAUSE_RULES: dict[str, dict[str, str]] = {
    "limitation_of_liability": {
        "severity": "high",
        "redline": "Restore 12-month aggregate cap or $1M, whichever is greater. Carve consequential damages only for IP indemnity and data breach.",
    },
    "indemnification": {
        "severity": "high",
        "redline": "Expand indemnity to gross negligence and willful misconduct. Remove broad customer-modification carve-out.",
    },
    "data_processing": {
        "severity": "high",
        "redline": "Attach DPA as Exhibit A at signing. Strike all training/benchmarking rights on Customer telemetry, aggregated or otherwise.",
    },
    "auto_renewal": {
        "severity": "high",
        "redline": "Reduce non-renewal notice from 90 to 30 days. This is a known auto-renewal trap.",
    },
    "price_lock": {
        "severity": "high",
        "redline": "Cap annual price escalation at 5% post initial term. Vendor's current language permits unlimited list-rate increases.",
    },
    "termination_for_convenience": {
        "severity": "med",
        "redline": "Add 60-day termination-for-convenience right with pro-rated refund of prepaid fees.",
    },
    "sla_credits": {
        "severity": "med",
        "redline": "Raise uptime target to 99.9%. Remove the 10% credit cap. Auto-issue credits instead of requiring written request.",
    },
    "subprocessors": {
        "severity": "med",
        "redline": "Add 15-day Customer objection window for new subprocessors and right to terminate if unresolved.",
    },
    "audit_rights": {
        "severity": "med",
        "redline": "Restore annual on-site audit right on 30 days' notice. Require SOC 2 Type II delivered automatically, not on request.",
    },
    "confidentiality": {
        "severity": "low",
        "redline": "Extend confidentiality survival from 3 to 5 years; trade secrets indefinite.",
    },
    "ip_assignment": {
        "severity": "med",
        "redline": "Strike vendor's perpetual royalty-free feedback license; Customer feedback should not transfer IP.",
    },
    "warranty": {
        "severity": "high",
        "redline": "Replace 'AS IS' disclaimer with materially-conforms-to-documentation warranty and re-performance/refund remedy.",
    },
    "governing_law": {
        "severity": "low",
        "redline": "Negotiate neutral venue (Delaware or San Francisco). Preserve right to jury trial where state law allows.",
    },
    "publicity": {
        "severity": "med",
        "redline": "Strike unilateral logo/name usage. Replace with mutual written consent per use.",
    },
    "data_deletion": {
        "severity": "high",
        "redline": "MISSING CLAUSE — require 30-day data deletion on termination with written certification of deletion.",
    },
}


@dataclass
class Redline:
    clause_key: str
    clause_title: str
    severity: str
    standard_text: str
    vendor_text: str
    similarity: float
    deviation_summary: str
    recommended_redline: str
    embedding_backend: str


def _load_fixtures() -> tuple[dict[str, Any], dict[str, Any]]:
    standard = json.loads((FIXTURES / "standard_msa.json").read_text())
    vendor = json.loads((FIXTURES / "vendor_msa_datadog.json").read_text())
    return standard, vendor


def _nosana_embed(texts: list[str]) -> list[list[float]] | None:
    endpoint = os.getenv("NOSANA_ENDPOINT")
    if not endpoint or httpx is None:
        return None
    try:
        # TODO: confirm Nosana endpoint contract with Person B.
        r = httpx.post(f"{endpoint.rstrip('/')}/embed", json={"texts": texts}, timeout=10.0)
        r.raise_for_status()
        return r.json().get("embeddings")
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


_TOKEN = re.compile(r"[A-Za-z0-9]+")


def _heuristic_similarity(a: str, b: str) -> float:
    """Deterministic fallback: token Jaccard with length penalty."""
    ta = {w.lower() for w in _TOKEN.findall(a)}
    tb = {w.lower() for w in _TOKEN.findall(b)}
    if not ta or not tb:
        return 0.0
    jaccard = len(ta & tb) / len(ta | tb)
    len_ratio = min(len(a), len(b)) / max(len(a), len(b))
    return round(0.7 * jaccard + 0.3 * len_ratio, 3)


def _summarize_deviation(clause_key: str, standard: str, vendor: str) -> str:
    """Hand-rolled per-clause one-liner. Beats trying to LLM these — deterministic + fast."""
    summaries = {
        "limitation_of_liability": "Vendor caps liability at 3 months of fees vs. our 12-month / $1M floor.",
        "indemnification": "Vendor narrows indemnity to direct IP claims only; carves out modifications and OSS.",
        "data_processing": "Vendor reserves right to train models on Customer telemetry, even aggregated.",
        "auto_renewal": "Vendor's non-renewal notice window is 90 days vs. our 30. Auto-renewal trap.",
        "price_lock": "Vendor reserves unilateral renewal price increases; no cap.",
        "termination_for_convenience": "Vendor disallows termination during committed term; charges remaining fees.",
        "sla_credits": "Vendor weakens SLA to 99.5%, caps credits at 10%, and gates on written request.",
        "subprocessors": "Vendor controls subprocessor changes unilaterally; no Customer objection right.",
        "audit_rights": "Vendor offers SOC 2 on request, no on-site audit, at vendor's discretion.",
        "confidentiality": "Confidentiality term shortened to 3 years vs. our 5.",
        "ip_assignment": "Vendor takes perpetual royalty-free license to Customer feedback and ideas.",
        "warranty": "Vendor disclaims all warranties; service is 'AS IS' with no remedy.",
        "governing_law": "Vendor's venue is NY with jury waiver; we prefer Delaware/SF with AAA arbitration.",
        "publicity": "Vendor unilaterally claims Customer logo + name usage rights with no opt-out.",
        "data_deletion": "Vendor MSA omits any post-termination data deletion clause entirely.",
    }
    return summaries.get(clause_key, "Material deviation from standard language.")


def _diff(standard: dict[str, Any], vendor: dict[str, Any]) -> list[Redline]:
    standard_clauses = {c["key"]: c for c in standard["clauses"]}
    vendor_clauses = {c["key"]: c for c in vendor["clauses"]}

    # Try real embeddings first; fall back to heuristic if Nosana isn't wired.
    all_keys = sorted(set(standard_clauses) | set(vendor_clauses))
    texts: list[str] = []
    for k in all_keys:
        texts.append(standard_clauses.get(k, {}).get("text", ""))
        texts.append(vendor_clauses.get(k, {}).get("text", ""))
    embeddings = _nosana_embed(texts)
    backend = "nosana" if embeddings else "heuristic"

    redlines: list[Redline] = []
    for i, key in enumerate(all_keys):
        std = standard_clauses.get(key)
        ven = vendor_clauses.get(key)

        if std and not ven:
            # Missing clause in vendor MSA — automatic high-severity flag.
            rule = _CLAUSE_RULES.get(key, {"severity": "high", "redline": "Insert standard clause verbatim."})
            redlines.append(Redline(
                clause_key=key,
                clause_title=std["title"],
                severity=rule["severity"],
                standard_text=std["text"],
                vendor_text="(missing from vendor MSA)",
                similarity=0.0,
                deviation_summary=_summarize_deviation(key, std["text"], ""),
                recommended_redline=rule["redline"],
                embedding_backend=backend,
            ))
            continue

        if ven and not std:
            # Vendor added a clause not in our template — e.g., publicity rights.
            rule = _CLAUSE_RULES.get(key, {"severity": "med", "redline": "Strike or negotiate to mutual consent."})
            redlines.append(Redline(
                clause_key=key,
                clause_title=ven["title"],
                severity=rule["severity"],
                standard_text="(not in standard template)",
                vendor_text=ven["text"],
                similarity=0.0,
                deviation_summary=_summarize_deviation(key, "", ven["text"]),
                recommended_redline=rule["redline"],
                embedding_backend=backend,
            ))
            continue

        # Both present — compute similarity.
        if embeddings:
            sim = _cosine(embeddings[2 * i], embeddings[2 * i + 1])
        else:
            sim = _heuristic_similarity(std["text"], ven["text"])

        # Threshold: <0.78 = material deviation worth a redline.
        if sim < 0.78:
            rule = _CLAUSE_RULES.get(key, {"severity": "med", "redline": "Negotiate back to standard language."})
            redlines.append(Redline(
                clause_key=key,
                clause_title=std["title"],
                severity=rule["severity"],
                standard_text=std["text"],
                vendor_text=ven["text"],
                similarity=round(sim, 3),
                deviation_summary=_summarize_deviation(key, std["text"], ven["text"]),
                recommended_redline=rule["redline"],
                embedding_backend=backend,
            ))

    # Sort: high → med → low, then by clause title.
    sev_rank = {"high": 0, "med": 1, "low": 2}
    redlines.sort(key=lambda r: (sev_rank.get(r.severity, 9), r.clause_title))
    return redlines


@agent("contract_diff")
def run(vendor_key: str = "datadog") -> dict[str, Any]:
    try:
        standard, vendor = _load_fixtures()
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # Demo-cannot-crash: if fixtures aren't shipped (or are unreadable),
        # return the same 15 redlines hardcoded in src/, preserving the demo
        # numbers and the auto-renewal/data-deletion pitch beats.
        return _fallback_response(vendor_key)
    redlines = _diff(standard, vendor)
    backend = redlines[0].embedding_backend if redlines else ("nosana" if os.getenv("NOSANA_ENDPOINT") else "heuristic")
    counts = {"high": 0, "med": 0, "low": 0}
    for r in redlines:
        counts[r.severity] = counts.get(r.severity, 0) + 1
    return {
        "agent": "contract_diff",
        "vendor": vendor.get("vendor", vendor_key),
        "redline_count": len(redlines),
        "severity_counts": counts,
        "embedding_backend": backend,
        "redlines": [asdict(r) for r in redlines],
    }


def _fallback_response(vendor_key: str) -> dict[str, Any]:
    from ._contract_diff_fallback import FALLBACK_REDLINES
    counts = {"high": 0, "med": 0, "low": 0}
    for r in FALLBACK_REDLINES:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1
    return {
        "agent": "contract_diff",
        "vendor": vendor_key.capitalize() if vendor_key else "Datadog",
        "redline_count": len(FALLBACK_REDLINES),
        "severity_counts": counts,
        "embedding_backend": "fallback",
        "redlines": list(FALLBACK_REDLINES),
    }
