# Submission package

Paste-ready copy for `tinyurl.com/agentforgesubmit`. **Deadline: 4:25 PM. Submit by 4:25 PM.**

Live URL is confirmed: https://shadowbuyer.zeabur.app

---

## Project name

**ShadowBuyer**

## One-liner

Autonomous B2B procurement agent swarm that collapses 6 weeks of SaaS buying into 6 hours.

## Description (short — 280 chars)

ShadowBuyer is a 6-agent swarm that automates B2B software procurement. Scout researches, Quote Hunter pulls AE quotes, Hardball (Qwen) and Diplomat (Z.ai) negotiate adversarially, Referee picks the winner, and Contract Diff redlines the MSA. Live demo: $225K saved on one Datadog deal.

## Description (long)

ShadowBuyer automates the painful B2B software procurement process with a six-agent workflow. **Scout** ranks observability vendors using Bright Data scrapes and Qwen reasoning. **Quote Hunter** fills Contact Sales forms via Actionbook and captures AE replies (including competitor trash-talk, which becomes the moat in Evermind). **Hardball** (Qwen3-Max) and **Diplomat** (Z.ai GLM-5.1) run an adversarial negotiation across three rounds, routed entirely through TokenRouter. **Referee** (Qwen) picks the winning play. The drafted AE email is generated automatically. Finally, **Contract Diff** (Qwen + Nosana embeddings) compares the vendor MSA to a standard template and flags 15 deviations — including an auto-renewal trap and a missing data-deletion clause.

The demo runs the full pipeline live on stage, end-to-end, on Datadog with a competing New Relic quote. List price $195/host/mo walks down to $157.50/host/mo through visible disagreement between two LLMs, ending with $225,000 in annual savings at 500 hosts. Every external API has a deterministic mock fallback — the demo cannot crash even if a sponsor service is unavailable mid-pitch.

## Live URL

**Backend (live demo, SSE stream, sponsor health):** https://shadowbuyer.zeabur.app

Try it:
- https://shadowbuyer.zeabur.app/ — embedded dashboard
- https://shadowbuyer.zeabur.app/healthz — service health
- https://shadowbuyer.zeabur.app/api/sponsor-health — all 11 sponsors with live/fallback status
- https://shadowbuyer.zeabur.app/run/stream?category=observability — full 34-event SSE pipeline

**Frontend (Procure workspace with Vendors / Quotes / Negotiation log / Contracts / Sponsor health):**
Lives at `frontend/` in the same repo. Run locally — `cd frontend && npm install && npm run build:spa && npm run preview:spa`. Deploys to Zeabur as a second service via `frontend/Dockerfile` + `frontend/zeabur.toml`. Production env: `VITE_SHADOWBUYER_URL=https://shadowbuyer.zeabur.app`.

## GitHub

Single repo: https://github.com/LeSingh1/shadowbuyer

- `src/` — FastAPI backend, 6 agents, pipeline
- `frontend/` — React 19 + Vite SPA, Procure CRM with 5 views

## Sponsors used (all 11)

AgentField, Bright Data, Actionbook, Evermind, Qwen Cloud, Z.ai, TokenRouter, Nosana, Qoder, Zeabur, Butterbase.

Audit endpoint live at: https://shadowbuyer.zeabur.app/api/sponsor-health

## Key demo stats

- 6-week procurement process collapsed to 6 hours
- Datadog list price: **$195/host/month** (≈ $2,340/host/year, matches doc-spec AE response)
- Negotiated price: **$157.50/host/month** after 3 rounds of adversarial negotiation
- **$225,000 annual savings** at 500 hosts (19.2% off list)
- **15 contract deviations** flagged in 4 seconds
- **Auto-renewal trap** flagged high severity (90-day non-renewal notice vs our 30)
- **Missing data-deletion clause** flagged high severity (entirely absent from vendor MSA)
- 11/11 sponsors wired with real code references
- All sponsor APIs have mock fallbacks — demo cannot crash
- Backend: 6/6 pytest smoke tests green, sub-second pipeline runs

## Technical stack

- **Backend:** Python 3.12, FastAPI, uvicorn, httpx. Server-sent events for live streaming. Deterministic mock fallback on every external client. 6-test pytest smoke suite. Docker + Zeabur deploy.
- **Frontend:** React 19, TanStack Start, TanStack Router, TanStack Query, shadcn/ui, Tailwind 4, framer-motion 12, JetBrains Mono for numerics. Cloudflare Workers via wrangler.
- **Agents:** AgentField orchestration, every LLM call routed through TokenRouter (OpenAI-compatible). Qwen3-Max via Qwen Cloud (Scout, Hardball, Referee). GLM-5.1 via Z.ai (Diplomat). Sentence-transformer embeddings via Nosana for Contract Diff.
- **Memory:** Evermind for vendor profiles, AE quotes, competitor trash-talk, and Referee decisions — with local JSON fallback as defense in depth.
- **Data:** Bright Data scrapes (G2, funding, outages, logos). Actionbook captures (Contact Sales form fills, AE replies).
- **Built with:** Qoder.
- **Workspace:** Butterbase-compatible JSON endpoints (`/api/demo-state`, `/api/email-draft`, `/api/sponsor-health`).

## Why this hits the rubric

| Criterion | Score target | How |
|---|---|---|
| Completeness (25%) | 5/5 | MVP shipped: 4 core agents + 1 stretch agent (Contract Diff) + 1 polish agent (Email Drafter). Pipeline runs end-to-end with deterministic numbers. Deployed live on Zeabur. |
| Innovation (25%) | 5/5 | Adversarial dual-LLM negotiation (Qwen vs Z.ai) with a Referee verdict is genuinely novel. Two models visibly disagree on stage. |
| Real Pain (25%) | 5/5 | $5T procurement market. Every CFO has lost a quarter to this. Pitch closes with a direct ask to the room. |
| Sponsor Coverage (25%) | 5/5 | All 11 sponsors wired with real code references. Mock fallback so the demo cannot crash. Audit endpoint at `/api/sponsor-health`. |

## Team

- **Person A** ("The Forge") — backend, AgentField orchestration, Qwen / Z.ai / TokenRouter, Evermind memory, Zeabur deploy
- **Person B** ("The Hunter") — Bright Data scrapers, Actionbook integrations, Evermind wiring, Nosana endpoint, mock fixtures
- **Person C** ("The Voice") — Butterbase dashboard, TanStack + framer-motion frontend, pitch deck, demo script, backup video

## Repo collaborators

- LeSingh1 (Person A, owner of backend)
- Yba1 (Person B)
- RohithBStar (Person C, owner of frontend at rhthbandaru-star/visual-procurement-studio)
