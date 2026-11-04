# Prior work disclosure

This repository contains work that existed before the hackathon and work built during it. This file says plainly which is which.

## What existed before the hackathon

**ShadowBuyer (procurement edition)**: `LeSingh1/shadowbuyer`, last commit `9a05364` (2026-05-16). It is kept **verbatim and unchanged in [`legacy/`](legacy/)**.

It was a 6-agent B2B SaaS procurement swarm: Scout → Quote Hunter → adversarial Negotiator (Hardball / Diplomat / Referee) → Contract Diff → Email Drafter. It negotiated a fixture Datadog contract from $195 to $157.50/host. It had:

- a FastAPI backend with a paced SSE stream (`/run/stream`)
- a "mock-fallback contract": every external client returned deterministic stub data when keys were missing
- LLM calls routed through TokenRouter to Qwen and GLM
- an Evermind key-value memory adapter with a local JSON fallback
- a TanStack Start + shadcn "Procure CRM" dashboard
- 6 pytest smoke tests

## What was built during the hackathon (everything outside `legacy/`)

The product, customer, money math, agents, UI and integrations are new:

| Area | Built during the hackathon |
|---|---|
| Product | ShadowBuyer **for Main Street**: independent restaurant owners, card-processing statements, merchant cash advances, approve-by-text |
| Money math | `src/finance/`: effective rate, fee breakdown, plan pricing, annual savings, MCA true APR (daily IRR), early-termination cost, net switch benefit; 27 unit tests including a hand-checked `=RATE()` example |
| Contract | `src/contract.py` + `frontend/src/lib/contract.ts`: frozen SSE event contract v1.0.0 with a drift test |
| Agents | Statement Reader (vision), Fee Hunter, Rate Scout, Hardball / Diplomat vs. a simulated Processor Rep, Referee, Contract Exposer, Action Drafter: all new code |
| LLM layer | `src/llm/`: provider-agnostic client on the Anthropic SDK (structured outputs, streaming, prompt caching, adaptive thinking summaries, per-agent cost), the models file, and the number guard. TokenRouter/Qwen/GLM removed. |
| Execution | Approval gate, run manager, Stripe test-mode savings sweep, dry-run rep email, fee receipt, savings ledger |
| Owner channel | Twilio SMS webhook and phone-frame simulator driving the same handler |
| Report | Server-side lender/accountant-ready PDF (reportlab) with the MCA paydown chart |
| Fixtures | Fictional statement (JSON + PDF), fee taxonomy, benchmarks, competitor quotes, MCA offer, merchant agreement, redlines, negotiation ladder |
| Frontend | New Vite + React 19 + Motion app: two-screen layout, new visual design, all animations |
| Tests | 45 tests: calculators, contract drift, end-to-end mock run, approval gate, live-model routing, API |

## What carried over as ideas (not code)

- The **swarm shape**: a Hardball and a Diplomat negotiator compete and a Referee picks.
- The **mock-fallback contract**: zero keys = deterministic demo; any live failure degrades to fixtures.
- The **paced SSE generator** pattern and live/mock status chips (formerly `/api/sponsor-health`).
- The idea of **persisting run outcomes** so the next run starts smarter. `src/memory/store.py` is new: a plain local JSON store (no Evermind) with namespaces for owner profiles, statements, decisions and tactics.
