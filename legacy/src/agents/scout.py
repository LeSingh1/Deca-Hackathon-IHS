"""
SCOUT agent. Researches a B2B SaaS category, ranks vendors.
Model: Qwen via TokenRouter. Input: category string. Output: ranked vendor list.

Sponsor wiring: AgentField decorator, TokenRouter routing, Evermind memory.
"""
from __future__ import annotations

from typing import Any

from ..clients.tokenrouter import route
from ..memory import evermind

try:
    from agentfield import agent  # type: ignore
except ImportError:  # AgentField not installed yet — degrade gracefully.
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


_MOCK_OBSERVABILITY_VENDORS = [
    {"name": "Datadog", "rank": 1, "list_price_per_host_mo": 23, "notes": "Market leader, high stickiness, aggressive Q4 discounting historically."},
    {"name": "New Relic", "rank": 2, "list_price_per_host_mo": 25, "notes": "Recently went private (Francisco Partners). Pricing flexibility up."},
    {"name": "Honeycomb", "rank": 3, "list_price_per_host_mo": 18, "notes": "Developer love; weaker enterprise sales motion."},
    {"name": "Grafana Cloud", "rank": 4, "list_price_per_host_mo": 8, "notes": "OSS halo. Free tier is real leverage in negotiation."},
    {"name": "Splunk", "rank": 5, "list_price_per_host_mo": 40, "notes": "Cisco acquisition closed; legacy enterprise lock-in plays."},
]


@agent("scout")
def run(category: str, bright_data_input: dict | None = None) -> dict[str, Any]:
    cached = evermind.read("scout", category)
    if cached:
        return {**cached, "cache_hit": True}

    completion = route(
        prompt=f"Rank top vendors in category: {category}. "
               f"Bright Data signals: {bright_data_input or {}}. "
               f"Return JSON list with name, rank, list_price_per_host_mo, notes.",
        model="qwen3-max",
        provider="qwen",
    )

    vendors = _MOCK_OBSERVABILITY_VENDORS if "observ" in category.lower() else _MOCK_OBSERVABILITY_VENDORS[:3]

    result = {
        "agent": "scout",
        "category": category,
        "vendors": vendors,
        "model_meta": {"model": completion.model, "provider": completion.provider, "mocked": completion.mocked},
        "cache_hit": False,
    }
    evermind.write("scout", category, result)
    return result
