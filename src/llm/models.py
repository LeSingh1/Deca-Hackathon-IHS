"""
THE one place that decides which model each agent uses.

Model IDs and prices: Anthropic model table (Claude API skill reference,
cached 2026-10-06; verify at https://docs.claude.com/en/docs/about-claude/models).
Change an agent's model here and nothing else needs to move. To swap in a
different provider for one agent (e.g. a sponsor requirement), set its
`provider` field; see src/llm/client.py for the provider registry.

Env overrides:
  SHADOWBUYER_USE_FABLE=1      -> Referee + Contract Exposer use claude-fable-5-1
  SHADOWBUYER_MODEL_<AGENT>=id -> override any single agent, e.g.
                                  SHADOWBUYER_MODEL_FEE_HUNTER=claude-sonnet-5-5
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace

OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-5-5"
FABLE = "claude-fable-5-1"


@dataclass(frozen=True)
class AgentModel:
    agent: str
    model: str
    job: str
    provider: str = "anthropic"
    effort: str | None = None          # output_config.effort; None = model default
    show_thinking_summary: bool = False  # adaptive thinking, display="summarized"
    max_tokens: int = 4000             # includes thinking, which is on by default on these models


AGENTS: dict[str, AgentModel] = {
    a.agent: a
    for a in [
        AgentModel("statement_reader", SONNET, "Vision-parse statement photo/PDF into line items", effort="medium", max_tokens=8000),
        AgentModel("fee_hunter", HAIKU, "Classify every line (interchange, markup, junk, PCI...)", effort="low", max_tokens=4000),
        AgentModel("hardball", SONNET, "Aggressive rate-cut ask citing competitor quotes", effort="low", max_tokens=4000),
        AgentModel("diplomat", SONNET, "Relationship-preserving retention ask", effort="low", max_tokens=4000),
        AgentModel("processor_rep", HAIKU, "Simulated processor sales rep who pushes back", effort="low", max_tokens=4000),
        AgentModel("referee", OPUS, "Judge transcripts, explain the winning strategy", effort="high", show_thinking_summary=True, max_tokens=8000),
        AgentModel("contract_exposer", OPUS, "Find traps in MCA offer + merchant agreement; write redlines", effort="high", show_thinking_summary=True, max_tokens=16000),
        AgentModel("action_drafter", SONNET, "Write the rep email and switch checklist", effort="low", max_tokens=2000),
    ]
}

# $ per 1M tokens: (input, output, cache_read). Cache writes bill at 1.25x input.
PRICING: dict[str, tuple[float, float, float]] = {
    FABLE: (10.00, 50.00, 0.25),
    OPUS: (4.00, 20.00, 0.20),
    SONNET: (2.00, 10.00, 0.20),
    HAIKU: (0.10, 0.50, 0.01),
}


def model_for(agent: str) -> AgentModel:
    cfg = AGENTS[agent]
    if os.getenv("SHADOWBUYER_USE_FABLE") == "1" and agent in ("referee", "contract_exposer"):
        cfg = replace(cfg, model=FABLE)
    override = os.getenv(f"SHADOWBUYER_MODEL_{agent.upper()}")
    if override:
        cfg = replace(cfg, model=override)
    return cfg


def cost_usd(model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> float:
    inp, out, cr = PRICING.get(model, PRICING[OPUS])
    return round(
        (input_tokens * inp + output_tokens * out + cache_read * cr + cache_write * inp * 1.25) / 1_000_000, 6
    )
