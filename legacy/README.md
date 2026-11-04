# ShadowBuyer

ShadowBuyer is an autonomous B2B procurement swarm that compresses six weeks of SaaS buying into a six-hour agent workflow.

**Live demo:** https://shadowbuyer.zeabur.app
**Frontend repo:** https://github.com/rhthbandaru-star/visual-procurement-studio

Demo category: observability tools. Live vendor: Datadog. Demo arc: 6 agents → $195/host list → $157.50/host negotiated → $225K/yr savings at 500 hosts → 15 contract redlines flagged.

## Status

- ✅ 6 agents wired: Scout, Quote Hunter, Hardball + Diplomat + Referee (adversarial negotiation), Contract Diff, Email Drafter
- ✅ Sequential pipeline with paced SSE stream (34 events end-to-end)
- ✅ Integrated dashboard: vendor comparison, live swarm, verdict, drafted AE email, 15-redline MSA review, sponsor health
- ✅ Mock-fallback contract: every external client returns deterministic stub data when keys are missing — demo cannot crash
- ✅ CORS open so the frontend (Cloudflare Workers / Vite) can hit the SSE stream cross-origin
- ✅ Deployed live on Zeabur at https://shadowbuyer.zeabur.app
- ✅ All 11 sponsors wired with real code references; audit at `/api/sponsor-health`

## Repo layout

```
shadowbuyer/
├── src/                  ← FastAPI backend + 6 agents (Python 3.12)
├── fixtures/             ← deterministic mock data
├── tests/                ← 6 pytest smoke tests (sub-second)
├── Dockerfile            ← backend image, deploys as `shadowbuyer` on Zeabur
├── zeabur.toml           ← backend service config
└── frontend/             ← Procure CRM (React 19 + Vite SPA)
    ├── src/procure/      ← Vendors / Quotes / NegotiationLog / Contracts / SponsorHealth views
    ├── src/spa-main.tsx  ← React mount point
    ├── Dockerfile        ← multi-stage build → nginx serve
    └── zeabur.toml       ← frontend service config (deploy as 2nd Zeabur service)
```

## Run locally

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.app:app --reload --port 8000
open http://localhost:8000   # embedded HTML dashboard

# Frontend (in a second terminal)
cd frontend
npm install
npm run build:spa && npm run preview:spa
open http://localhost:4173   # full Procure CRM with sidebar + 5 views
```

## Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET`  | `/`                  | live dashboard (HTML) |
| `GET`  | `/healthz`           | `{ok, version, services: {tokenrouter_live, ...}}` |
| `POST` | `/run`               | full pipeline snapshot (sync) — `{scout, quote_hunter, negotiator, contract_diff, evermind_writes, summary}` |
| `GET`  | `/run/stream`        | SSE stream of stage + turn + redline + evermind_writes events |
| `GET`  | `/api/demo-state`    | cached snapshot, warmed on startup; pass `?refresh=true` to regenerate |
| `GET`  | `/api/email-draft`   | drafted AE email derived from the winning negotiation strategy |
| `GET`  | `/api/sponsor-health`| all 11 sponsors with env_status (live / mock / n/a) and code_ref |

## SSE stream contract (`/run/stream`)

Events arrive as `data: {json}\n\n`. Paced so the dashboard animates over ~7–8 seconds total.

| Event | Payload shape | Notes |
|---|---|---|
| `stage_start`           | `{stage, label, ...}`                                                        | One per pipeline stage |
| `stage_done`            | `{stage, payload?}`                                                          | Payload present for scout, quote_hunter, contract_diff |
| `negotiator_turn`       | `{turn: {round, role, headline, text, cites[], price_target_per_host_mo, deal_term_months, mocked}}` | role ∈ {hardball, diplomat, referee} |
| `contract_diff_summary` | `{vendor, redline_count, severity_counts: {high, med, low}, embedding_backend}` | Once, before redlines stream |
| `redline`               | `{redline: {clause_key, clause_title, severity, standard_text, vendor_text, similarity, deviation_summary, recommended_redline}}` | One per flagged clause |
| `summary`               | `{payload: {vendor, hosts, list_price_per_host_mo, final_price_per_host_mo, annual_savings_vs_list_usd, discount_vs_list_pct, winning_strategy, contract_redline_count, contract_high_severity, ...}}` | Once near end |
| `done`                  | `{}`                                                                          | Close the EventSource |

## Demo numbers (current mock)

- Vendor: Datadog · Competing: New Relic · Hosts: 500
- List: **$195/host/mo** ($2,340/host/yr, matches doc-spec AE response)
- Starting quote: $175.50 (10% AE discount)
- Final after 3-round adversarial negotiation: **$157.50/host/mo**
- **Annual savings vs list: $225,000** · **Discount: 19.2%**
- Winning strategy: HARDBALL · Email drafted to morgan.chen@datadog.com
- Contract Diff: **15 redlines** flagged · 7 high / 6 med / 2 low
  - High includes the auto-renewal trap and the missing data-deletion clause (doc pitch beats)

## Sponsor coverage (Person A's 5 + integration points for the rest)

| Sponsor       | Code reference                                                              | State                  |
|---            |---                                                                          |---                     |
| AgentField    | `@agent("…")` on every agent run()                                          | stub-import w/ fallback |
| TokenRouter   | `src/clients/tokenrouter.py` — every LLM call routes through it             | mock until key set     |
| Qwen Cloud    | Scout, Hardball (Qwen3-Max), Referee                                        | mock until key set     |
| Z.ai          | Diplomat (GLM-5.1)                                                          | mock until key set     |
| Evermind      | `src/memory/evermind.py` — scout cache, decisions; JSON file fallback        | local fallback         |
| Nosana        | `src/agents/contract_diff.py:_nosana_embed`                                 | mock until endpoint set |
| Bright Data   | `scout.run(bright_data_input=...)` parameter, `fixtures/observability_vendors_g2.json` | fixture; Person B replaces |
| Actionbook    | `src/agents/quote_hunter.py` reads `fixtures/<vendor>_ae_response.json`     | fixture; Person B drops in |
| Zeabur        | `Dockerfile`, `zeabur.toml`                                                 | config ready           |
| Qoder         | mentioned in pitch (process sponsor)                                        | n/a                    |
| Butterbase    | Person C consumes `/api/demo-state` + `/api/email-draft`                    | external               |

## Person B handoff — what to drop into `fixtures/`

The pipeline reads these files when present. Drop in real captures, no code change needed.

```
fixtures/
├── observability_vendors_g2.json     ← Bright Data scrape, shape: {vendors: [{name, g2_rating, ...}]}
├── datadog_ae_response.json          ← Actionbook capture, shape:
│                                        {vendor, ae_email, ae_name, first_quote, discount_offered,
│                                         competitor_dig, quarter_end_iso, hosts_quoted}
├── new_relic_ae_response.json        ← same shape, second vendor (currently inline-mocked)
├── standard_msa.json                 ← our standard MSA clauses (already populated)
└── vendor_msa_datadog.json           ← captured Datadog MSA (currently mocked, replace if you get one)
```

If `NOSANA_ENDPOINT` env var is set, `contract_diff` POSTs `{texts: [...]}` to `${endpoint}/embed` and expects `{embeddings: [[...], ...]}` back. Falls back to deterministic Jaccard+length similarity if endpoint absent/errors.

## Person C handoff — frontend contract

Render two things:
1. **Live negotiation column view** — consume `/run/stream`, render hardball + diplomat turns side-by-side as they arrive. Verdict card at the end. The built-in HTML dashboard at `/` shows the target aesthetic.
2. **Vendor snapshot view** — `GET /api/demo-state` returns the cached full snapshot. `summary` field has every number you need for the headline:
   - `summary.final_price_per_host_mo` (final)
   - `summary.annual_savings_vs_list_usd` (the CFO number)
   - `summary.discount_vs_list_pct`
   - `summary.contract_redline_count`, `summary.contract_high_severity`
   - `summary.winning_strategy` ∈ {hardball, diplomat}
3. **Email card** — `GET /api/email-draft` returns `{ok, email: {to, from, subject, body, strategy, cites, dry_run}}`. Render after the verdict.

## Mock-fallback contract

Every external dependency degrades to a deterministic mock so the demo cannot crash:
- TokenRouter → tagged stub completions, no API call
- Qwen / Z.ai → routed through TokenRouter, mock-passthrough
- Evermind → `.evermind-fallback.json` (gitignored)
- Nosana → Jaccard + length similarity heuristic
- Bright Data → `fixtures/observability_vendors_g2.json`
- Actionbook → `fixtures/<vendor>_ae_response.json` or inline fallback

Flipping any service to live = drop one env var. See `.env.example`.

## Environment variables

Every variable is **optional**. With all of them empty, the pipeline runs end-to-end on deterministic mocks. Flipping a service to live = drop one env var. See `.env.example` for the canonical list.

| Variable                       | Powers                  | Default               | Live behavior |
|---                             |---                      |---                    |---            |
| `TOKENROUTER_API_KEY`          | Scout, Hardball, Diplomat, Referee, Email polish | (mock) | POSTs OpenAI-compatible chat/completions; any error → mock |
| `TOKENROUTER_BASE_URL`         | TokenRouter base URL    | `https://api.tokenrouter.io/v1` | Override if the sponsor's URL differs |
| `TOKENROUTER_QWEN_PREFIX`      | Qwen model id prefix    | `qwen`                | Override if TokenRouter uses e.g. `alibaba/...` |
| `TOKENROUTER_ZAI_PREFIX`       | Z.ai model id prefix    | `zai`                 | Override if TokenRouter uses e.g. `glm/...` |
| `EVERMIND_API_KEY`             | Vendor profiles, AE quotes, trash-talk, decisions | (local JSON fallback) | PUTs to Evermind; mirrors locally; any error → local only |
| `EVERMIND_BASE_URL`            | Evermind base URL       | `https://api.evermind.ai` | Override per sponsor docs |
| `EVERMIND_PATH_TEMPLATE`       | Key path template       | `/v1/namespaces/{namespace}/keys/{key}` | Override if path shape differs |
| `NOSANA_ENDPOINT`              | Contract Diff embeddings | (heuristic fallback) | POSTs `{texts}` to `{endpoint}/embed`; expects `{embeddings}` |
| `BRIGHTDATA_API_KEY`           | Scout (via Person B)    | (fixture)             | Person B's pipeline; we just plumb it through |
| `QWEN_API_KEY`, `ZAI_API_KEY`  | (currently unused — TokenRouter handles routing) | — | Reserved for direct-call fallback |

## Deploy to Zeabur

```bash
# one-time (in your shell, not the agent's)
zeabur auth login

# from projects/shadowbuyer/
zeabur deploy
```

Alternative: connect the GitHub repo in the Zeabur dashboard and every push to `main` redeploys.

The `Dockerfile` exposes port 8000 and runs `uvicorn src.app:app`. `zeabur.toml` declares a `/healthz` healthcheck and lists the env-var slots — set them in the Zeabur project settings, not in the committed file. Per the doc, redeploy hourly during the build; freeze redeploys at 4:00 PM.
