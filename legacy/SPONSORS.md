# Sponsor name-drops — all 11

One sentence each. Memorize. If a judge asks "how did you use X," recite the matching line and point at the code reference.

| # | Sponsor | Stage line | Code reference |
|---|---|---|---|
| 1 | **AgentField** | "AgentField orchestrates the six agents — one decorator per agent — so we can wire the swarm in minutes instead of weeks." | `@agent("…")` on every agent in [src/agents/](https://github.com/LeSingh1/shadowbuyer/tree/main/src/agents) |
| 2 | **Bright Data** | "Bright Data pulls G2 reviews, funding signals, and outage history on every observability vendor before Scout even starts ranking." | [fixtures/observability_vendors_g2.json](https://github.com/LeSingh1/shadowbuyer/blob/main/fixtures/observability_vendors_g2.json), `scout.run(bright_data_input=...)` |
| 3 | **Actionbook** | "Actionbook fills Datadog's Contact Sales form for us and captures the AE reply — no humans in the loop." | [fixtures/datadog_ae_response.json](https://github.com/LeSingh1/shadowbuyer/blob/main/fixtures/datadog_ae_response.json), [src/agents/quote_hunter.py](https://github.com/LeSingh1/shadowbuyer/blob/main/src/agents/quote_hunter.py) |
| 4 | **Evermind** | "Evermind is our memory layer — vendor profiles, AE quotes, every trash-talk dig, every referee decision. The moat: AEs who consistently disparage their competitors become queryable intel." | [src/memory/evermind.py](https://github.com/LeSingh1/shadowbuyer/blob/main/src/memory/evermind.py), pipeline writes 10 records per run |
| 5 | **Qwen Cloud** | "Qwen3-Max powers Scout's vendor ranking, Hardball's leverage reasoning, and the Referee's final verdict — three of our six agents." | [negotiator.py:_hb_round](https://github.com/LeSingh1/shadowbuyer/blob/main/src/agents/negotiator.py), `provider="qwen"` |
| 6 | **Z.ai** | "Z.ai's GLM-5.1 plays Diplomat — the partnership voice in our adversarial negotiation. A different model produces a genuinely different strategy." | [negotiator.py:_dp_round](https://github.com/LeSingh1/shadowbuyer/blob/main/src/agents/negotiator.py), `provider="zai"` |
| 7 | **TokenRouter** | "Every LLM call in the entire codebase routes through TokenRouter — single auth, single billing, single audit point for Qwen and Z.ai." | [src/clients/tokenrouter.py](https://github.com/LeSingh1/shadowbuyer/blob/main/src/clients/tokenrouter.py), OpenAI-compatible adapter |
| 8 | **Nosana** | "Nosana hosts our sentence-transformer model for clause-similarity embeddings — that's how Contract Diff knows the auto-renewal clause was 90 days instead of 30." | [contract_diff.py:_nosana_embed](https://github.com/LeSingh1/shadowbuyer/blob/main/src/agents/contract_diff.py), `NOSANA_ENDPOINT` env var |
| 9 | **Qoder** | "Qoder is what we built ShadowBuyer in — pair-programmed with the agents that became Hardball and Diplomat." | (process sponsor — pitch mention) |
| 10 | **Zeabur** | "Zeabur runs the FastAPI backend that streams the live negotiation you just watched. Deployed at hour zero, redeployed hourly, frozen at four." | [Dockerfile](https://github.com/LeSingh1/shadowbuyer/blob/main/Dockerfile), [zeabur.toml](https://github.com/LeSingh1/shadowbuyer/blob/main/zeabur.toml) |
| 11 | **Butterbase** | "Butterbase powers the procurement workspace — Vendors, Quotes, Contracts — that ShadowBuyer's agents write into. It's where the procurement lead lives after the swarm is done." | [visual-procurement-studio](https://github.com/rhthbandaru-star/visual-procurement-studio), Butterbase API integration |

## Compact stage version (if you only get one breath)

> "All eleven sponsors are wired with real code. AgentField orchestrates. Bright Data scrapes. Actionbook fills the form. Quote Hunter parses. Evermind remembers. Qwen and Z.ai disagree on stage through TokenRouter. Nosana embeds the contract clauses. Built with Qoder. Deployed on Zeabur. Workspace on Butterbase. Every call has a mock fallback so the demo cannot crash. Check `/api/sponsor-health` if you want to audit."

## Sponsor audit URL (if asked)

`https://<LIVE_URL>/api/sponsor-health`

Returns `{total: 11, counts: {live, mock, n/a}, sponsors: [{name, env, role, owner, code_ref, env_status}, ...], all_eleven_wired: true}`.

Pull it up in a side tab. Scroll down the list. The chips on the swarm dashboard light up green as keys flip live — what you see on the page IS the audit.
