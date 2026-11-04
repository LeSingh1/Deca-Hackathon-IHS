# API keys checklist

Every sponsor key is **optional** — the pipeline runs end-to-end with all of them empty (sponsors show as `mock`). Set the ones you have to flip them to `live`.

## Where to set them

Zeabur dashboard → `shadowbuyer` service → **Environment** tab → add each key.

## Required env vars per sponsor

| Sponsor       | Env var(s)                | Where to get the key                                |
|---------------|---------------------------|-----------------------------------------------------|
| TokenRouter   | `TOKENROUTER_API_KEY`     | tokenrouter.io dashboard                             |
| Qwen Cloud    | (same as TokenRouter)     | One key covers Scout + Hardball + Referee            |
| Z.ai          | (same as TokenRouter)     | One key covers Diplomat                              |
| Evermind      | `EVERMIND_API_KEY`        | evermind.ai dashboard                                |
| Nosana        | `NOSANA_ENDPOINT`         | Person B's deployed Nosana endpoint URL              |
| Bright Data   | `BRIGHTDATA_API_KEY`      | brightdata.com console                               |

Sponsors with no env var (`AgentField`, `Actionbook`, `Zeabur`, `Qoder`, `Butterbase`) show as `n/a` — they're code-referenced, not key-gated.

## Optional overrides

| Var                          | Default                                 | When to set                                          |
|------------------------------|-----------------------------------------|------------------------------------------------------|
| `TOKENROUTER_BASE_URL`       | `https://api.tokenrouter.io/v1`         | If TokenRouter changes their endpoint                |
| `TOKENROUTER_QWEN_PREFIX`    | `qwen`                                  | If model ID convention is e.g. `alibaba/qwen3-max`   |
| `TOKENROUTER_ZAI_PREFIX`     | `zai`                                   | If model ID convention is e.g. `glm/glm-5.1`         |
| `EVERMIND_BASE_URL`          | `https://api.evermind.ai`               | If Person A wires a different Evermind base          |
| `EVERMIND_PATH_TEMPLATE`     | `/v1/namespaces/{namespace}/keys/{key}` | If Evermind's path shape differs                     |

## Verify the keys actually work

After setting keys, hit the **deep probe** endpoint:

```bash
curl https://shadowbuyer.zeabur.app/api/sponsor-health?deep=true
```

This makes a real (sub-3s, sub-cost) network call per sponsor with credentials and returns:

```json
{
  "total": 11,
  "counts": {"live": 4, "mock": 2, "n/a": 5},
  "deep": true,
  "sponsors": [
    {
      "name": "TokenRouter",
      "env_status": "live",
      "probe": {"ok": true, "latency_ms": 142, "detail": "HTTP 200"}
    },
    {
      "name": "Evermind",
      "env_status": "mock",
      "probe": {"ok": false, "latency_ms": 230, "detail": "HTTP 401"}
    }
  ]
}
```

- `env_status: "live"` ↔ key present AND probe succeeded
- `env_status: "mock"` ↔ key missing OR probe failed
- `probe.detail` tells you the HTTP status code so you can debug

## Demo guarantee

**The demo cannot crash regardless of key status.** Every adapter (`src/clients/tokenrouter.py`, `src/memory/evermind.py`, `src/agents/contract_diff.py:_nosana_embed`) catches every exception and falls back to deterministic mock data. Setting keys only flips sponsors from `mock` to `live` — it never breaks anything.
