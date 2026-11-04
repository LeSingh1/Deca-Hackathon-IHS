"""Fixture loading + the shared (prompt-cached) context every agent sees."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@lru_cache(maxsize=None)
def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def path(name: str) -> Path:
    return FIXTURES / name


@lru_cache(maxsize=1)
def shared_context() -> str:
    """Large, stable context placed first in every system prompt with
    cache_control so repeated agent calls read it from the prompt cache.
    Must be byte-identical across calls: sorted keys, no timestamps."""
    taxonomy = load("fee_taxonomy")
    bench = load("interchange_benchmarks")
    comps = load("competitor_processors")
    agreement = load("merchant_agreement")
    mca = load("mca_offer_fastfund")
    dump = lambda o: json.dumps(o, sort_keys=True, indent=1)  # noqa: E731
    return (
        "You are part of ShadowBuyer, a swarm of agents that fights hidden card-processing fees and "
        "predatory financing on behalf of independent restaurant owners. You work for the owner, "
        "never the processor or the funder. Speak plainly; the owner reads on a phone at 11pm.\n\n"
        "HARD RULE: you never compute or invent money figures. Every rate, dollar amount and APR is "
        "computed by deterministic calculators and given to you. Quote them exactly or not at all.\n\n"
        f"## Fee taxonomy\n{dump(taxonomy)}\n\n"
        f"## Interchange benchmark (illustrative)\n{dump(bench)}\n\n"
        f"## Competitor quotes (illustrative)\n{dump(comps)}\n\n"
        f"## Merchant processing agreement on file\n{dump(agreement)}\n\n"
        f"## Merchant cash advance offer on file\n{dump(mca)}\n"
    )
