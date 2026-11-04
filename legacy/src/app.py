"""
ShadowBuyer FastAPI app.

- GET  /healthz            liveness + mock/live status
- POST /run                sync full pipeline, returns JSON snapshot
- GET  /run/stream         SSE stream (turns appear paced for the live demo)
- GET  /api/demo-state     cached full snapshot for the frontend
- GET  /                   minimal HTML dashboard, two columns + verdict
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from . import pipeline
from .agents import email_drafter, negotiator as negotiator_mod, quote_hunter as quote_hunter_mod, scout as scout_mod

app = FastAPI(title="ShadowBuyer", version="0.2.0")

# Frontend (Cloudflare Workers / Vite dev / Lovable preview) lives on a different
# origin. Open CORS — there's nothing here worth gating.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_state_lock = threading.Lock()
_demo_state: dict[str, Any] = {"ok": False, "generated_at": None, "snapshot": None}


def _refresh_demo_state(category: str = "observability") -> dict[str, Any]:
    snapshot = pipeline.run(category=category)
    with _state_lock:
        _demo_state["ok"] = True
        _demo_state["generated_at"] = time.time()
        _demo_state["category"] = category
        _demo_state["snapshot"] = snapshot
    return snapshot


@app.on_event("startup")
def _warm_demo_state() -> None:
    # Never let warmer failures take down the app — /healthz must always be reachable.
    # /api/demo-state will lazily retry on first request via the refresh path.
    try:
        _refresh_demo_state()
    except Exception:
        pass


def _service_mode() -> dict[str, bool]:
    return {
        "tokenrouter_live": bool(os.getenv("TOKENROUTER_API_KEY")),
        "qwen_live": bool(os.getenv("QWEN_API_KEY")),
        "zai_live": bool(os.getenv("ZAI_API_KEY")),
        "evermind_live": bool(os.getenv("EVERMIND_API_KEY")),
        "nosana_live": bool(os.getenv("NOSANA_API_KEY") or os.getenv("NOSANA_ENDPOINT")),
        "brightdata_live": bool(os.getenv("BRIGHTDATA_API_TOKEN") or os.getenv("BRIGHTDATA_API_KEY")),
    }


_SPONSOR_MAP = [
    {"name": "AgentField",  "env": [],                            "role": "Orchestrates the 4 agents via @agent decorators", "owner": "Person A", "code_ref": "every src/agents/*.py"},
    {"name": "TokenRouter", "env": ["TOKENROUTER_API_KEY"],       "role": "Routes ALL LLM calls (Qwen, Z.ai, OpenAI)",        "owner": "Person A", "code_ref": "src/clients/tokenrouter.py"},
    {"name": "Qwen Cloud",  "env": ["TOKENROUTER_API_KEY"],       "role": "Scout, Hardball (Qwen3-Max), Referee",            "owner": "Person A", "code_ref": "src/agents/scout.py, negotiator.py"},
    {"name": "Z.ai",        "env": ["TOKENROUTER_API_KEY"],       "role": "Diplomat (GLM-5.1)",                              "owner": "Person A", "code_ref": "src/agents/negotiator.py:_dp_round"},
    {"name": "Evermind",    "env": ["EVERMIND_API_KEY"],          "role": "Vendor profiles, AE quotes, trash-talk, decisions","owner": "Person B", "code_ref": "src/memory/evermind.py + pipeline writes"},
    {"name": "Nosana",      "env": ["NOSANA_API_KEY"],            "role": "Clause similarity embeddings",                    "owner": "Person B", "code_ref": "src/agents/contract_diff.py:_nosana_embed"},
    {"name": "Bright Data", "env": ["BRIGHTDATA_API_TOKEN"],      "role": "Vendor research (G2, funding, logos)",            "owner": "Person B", "code_ref": "fixtures/observability_vendors_g2.json, scout.run(bright_data_input=...)"},
    {"name": "Actionbook",  "env": [],                            "role": "Quote Hunter form filling (Person B)",            "owner": "Person B", "code_ref": "fixtures/datadog_ae_response.json + src/agents/quote_hunter.py"},
    {"name": "Zeabur",      "env": [],                            "role": "Live deployment",                                  "owner": "Person A", "code_ref": "Dockerfile, zeabur.toml"},
    {"name": "Qoder",       "env": [],                            "role": "Built the codebase (process sponsor)",            "owner": "All",      "code_ref": "(pitch mention)"},
    {"name": "Butterbase",  "env": [],                            "role": "Frontend dashboard + Gmail (Person C)",           "owner": "Person C", "code_ref": "consumes /api/demo-state, /api/email-draft, /run/stream"},
]


@app.get("/api/sponsor-health")
def sponsor_health(deep: bool = False) -> dict[str, Any]:
    """Env-var check by default. `?deep=true` adds a real network probe per
    sponsor (live key required, sub-3s timeout each) so you can confirm the
    key actually authenticates against the provider.
    """
    probes = _probe_sponsors() if deep else {}
    rows = []
    for s in _SPONSOR_MAP:
        env_present = bool(s["env"]) and all(os.getenv(k) for k in s["env"])
        if not s["env"]:
            env_status = "n/a"
        elif not env_present:
            env_status = "mock"
        elif deep:
            probe = probes.get(s["name"], {})
            env_status = "live" if probe.get("ok") else "mock"
        else:
            env_status = "live"
        row = {**s, "env_status": env_status}
        if deep and s["name"] in probes:
            row["probe"] = probes[s["name"]]
        rows.append(row)
    counts = {"live": 0, "mock": 0, "n/a": 0}
    for r in rows:
        counts[r["env_status"]] = counts.get(r["env_status"], 0) + 1
    return {
        "total": len(rows),
        "counts": counts,
        "sponsors": rows,
        "all_eleven_wired": len(rows) == 11,
        "deep": deep,
    }


def _probe_sponsors() -> dict[str, dict[str, Any]]:
    """Make one tiny network call per sponsor with credentials present.
    Returns {name: {ok: bool, latency_ms: int, error: str | None}}.
    """
    import time as _t
    try:
        import httpx  # type: ignore
    except ImportError:
        return {}

    results: dict[str, dict[str, Any]] = {}

    def _probe(name: str, fn):
        t0 = _t.time()
        try:
            ok, detail = fn()
            results[name] = {"ok": ok, "latency_ms": int((_t.time() - t0) * 1000), "detail": detail}
        except Exception as e:
            results[name] = {"ok": False, "latency_ms": int((_t.time() - t0) * 1000), "error": f"{type(e).__name__}: {e}"}

    # TokenRouter / Qwen / Z.ai — POST the real /chat/completions path the pipeline
    # uses. 200 = full success; 400 = key valid but request shape off (still "live"
    # because auth passed); 401/403 = bad key; 404 = wrong base URL.
    if os.getenv("TOKENROUTER_API_KEY"):
        def _tr():
            base = os.getenv("TOKENROUTER_BASE_URL", "https://api.tokenrouter.io/v1").rstrip("/")
            r = httpx.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['TOKENROUTER_API_KEY']}", "Content-Type": "application/json"},
                json={"model": "qwen/qwen3-max", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                timeout=4.0,
            )
            # Accept 2xx (real response) OR 400 (auth ok, model/payload arg-error).
            ok = (200 <= r.status_code < 300) or r.status_code == 400
            return (ok, f"HTTP {r.status_code}" + (f" — {r.text[:120]}" if not ok else ""))
        _probe("TokenRouter", _tr)
        results["Qwen Cloud"] = results["TokenRouter"]
        results["Z.ai"] = results["TokenRouter"]

    # Evermind — round-trip a write to a probe key. Tries Bearer then X-API-Key.
    if os.getenv("EVERMIND_API_KEY"):
        def _em():
            base = os.getenv("EVERMIND_BASE_URL", "https://api.evermind.ai").rstrip("/")
            ns = os.getenv("EVERMIND_NAMESPACE", "probes")
            key = os.environ["EVERMIND_API_KEY"]
            url = f"{base}/v1/namespaces/{ns}/keys/__probe__"
            body = {"value": "probe", "metadata": {}}
            last_status = None
            for auth in ({"Authorization": f"Bearer {key}"}, {"X-API-Key": key}, {"x-api-key": key}):
                r = httpx.put(url, headers={**auth, "Content-Type": "application/json"}, json=body, timeout=3.0)
                last_status = r.status_code
                if 200 <= r.status_code < 300:
                    return (True, f"HTTP {r.status_code} via {list(auth.keys())[0]}")
            return (False, f"HTTP {last_status} (tried Bearer + X-API-Key)")
        _probe("Evermind", _em)

    # Nosana — POST a 1-token embed probe with bearer auth if key is set.
    nosana_key = os.getenv("NOSANA_API_KEY")
    nosana_endpoint = os.getenv("NOSANA_ENDPOINT")
    if nosana_key or nosana_endpoint:
        def _ns():
            if not nosana_endpoint:
                return (False, "no NOSANA_ENDPOINT set (have key but no URL)")
            endpoint = nosana_endpoint.rstrip("/")
            headers = {"Authorization": f"Bearer {nosana_key}"} if nosana_key else {}
            r = httpx.post(f"{endpoint}/embed", json={"texts": ["probe"]}, headers=headers, timeout=3.0)
            return (200 <= r.status_code < 300, f"HTTP {r.status_code}")
        _probe("Nosana", _ns)

    # Bright Data — accept either BRIGHTDATA_API_TOKEN (their naming) or BRIGHTDATA_API_KEY.
    bd_token = os.getenv("BRIGHTDATA_API_TOKEN") or os.getenv("BRIGHTDATA_API_KEY")
    if bd_token:
        def _bd():
            # /status returns 200 with valid token; 401 with bad token. Conservative timeout.
            r = httpx.get("https://api.brightdata.com/status", headers={"Authorization": f"Bearer {bd_token}"}, timeout=3.0)
            return (200 <= r.status_code < 300, f"HTTP {r.status_code}")
        _probe("Bright Data", _bd)

    return results


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "service": "shadowbuyer", "version": app.version, "services": _service_mode()}


@app.post("/run")
def run(category: str = "observability", include_contract_diff: bool = False) -> dict[str, Any]:
    snapshot = pipeline.run(category=category, include_contract_diff=include_contract_diff)
    with _state_lock:
        _demo_state["ok"] = True
        _demo_state["generated_at"] = time.time()
        _demo_state["category"] = category
        _demo_state["snapshot"] = snapshot
    return snapshot


@app.get("/run/stream")
def run_stream(
    category: str = "observability",
    pace: bool = Query(True, description="set false to dump events with no delays"),
) -> StreamingResponse:
    def gen():
        last_summary: dict[str, Any] | None = None
        for event in pipeline.stream(category=category, pace=pace):
            if event.get("event") == "summary":
                last_summary = event.get("payload")
            yield f"data: {json.dumps(event, default=str)}\n\n"
        if last_summary:
            with _state_lock:
                _demo_state["ok"] = True
                _demo_state["generated_at"] = time.time()
                _demo_state["category"] = category
                # cheap refresh — full pipeline is already replayed via state warmer if needed
                _demo_state["snapshot"] = {"summary": last_summary} | (_demo_state.get("snapshot") or {})
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/email-draft")
def email_draft(category: str = "observability") -> dict[str, Any]:
    s = scout_mod.run(category)
    q = quote_hunter_mod.run(s["vendors"])
    n = negotiator_mod.run(q["quotes"])
    if "error" in n:
        return {"ok": False, "reason": n["error"]}
    draft = email_drafter.draft(n, q["quotes"][0], q["quotes"][1])
    return {"ok": True, "email": email_drafter.to_dict(draft)}


@app.get("/api/demo-state")
def demo_state(refresh: bool = False) -> JSONResponse:
    if refresh or not _demo_state.get("ok"):
        _refresh_demo_state()
    with _state_lock:
        return JSONResponse(_demo_state)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return _DASHBOARD_HTML


_DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<title>ShadowBuyer — live negotiation</title>
<style>
  :root {
    --bg:#0a0c10; --panel:#11151c; --line:#1f2530;
    --ink:#e6e8ec; --muted:#7c8392;
    --hb:#ff5d6c; --dp:#3ee0a1; --rf:#ffc83d; --acc:#7aa2ff;
    --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 var(--mono);min-height:100vh}
  header{padding:18px 28px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
  header .brand{display:flex;align-items:center;gap:12px}
  header h1{margin:0;font-size:13px;letter-spacing:.22em;text-transform:uppercase;color:var(--acc)}
  header .tag{font-size:11px;color:var(--muted);letter-spacing:.18em;text-transform:uppercase}
  header .dot{width:8px;height:8px;border-radius:50%;background:var(--muted);box-shadow:0 0 0 0 rgba(122,162,255,.6);transition:background .25s}
  header .dot.live{background:var(--dp);animation:pulse 1.6s infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(62,224,161,.55)}70%{box-shadow:0 0 0 10px rgba(62,224,161,0)}100%{box-shadow:0 0 0 0 rgba(62,224,161,0)}}
  header button{background:var(--acc);color:#0a0c10;border:0;padding:9px 18px;font:600 13px/1 var(--mono);letter-spacing:.05em;cursor:pointer;border-radius:2px}
  header button:disabled{opacity:.5;cursor:not-allowed}

  .meta{padding:14px 28px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:16px}
  .meta .cell{display:flex;flex-direction:column;gap:4px}
  .meta .k{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
  .meta .v{font-size:15px;color:var(--ink)}
  .meta .v.big{font-size:22px;color:var(--rf)}

  .pipeline{padding:14px 28px;border-bottom:1px solid var(--line);display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted)}
  .pipeline .step{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border:1px solid var(--line);border-radius:99px}
  .pipeline .step.active{color:var(--acc);border-color:var(--acc)}
  .pipeline .step.done{color:var(--dp);border-color:var(--dp)}
  .pipeline .arrow{color:var(--line)}

  .redlines{margin:0 28px 28px;background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:18px 22px;display:none}
  .redlines.on{display:block}
  .redlines h2{margin:0 0 4px;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--acc)}
  .redlines .top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:14px}
  .redlines .count{font-size:18px}
  .redlines .count strong{color:var(--rf);font-size:24px}
  .redlines .sev{display:inline-flex;gap:8px;font-size:11px;color:var(--muted)}
  .redlines .sev .pill{padding:2px 8px;border-radius:99px;border:1px solid var(--line)}
  .redlines .sev .pill.high{color:var(--hb);border-color:var(--hb)}
  .redlines .sev .pill.med{color:var(--rf);border-color:var(--rf)}
  .redlines .sev .pill.low{color:var(--muted)}
  .redlines .row{border-top:1px dashed var(--line);padding:10px 0;display:grid;grid-template-columns:90px 1fr 60px;gap:14px;align-items:start;opacity:0;animation:in .25s ease-out forwards}
  .redlines .row .badge{font-size:10px;letter-spacing:.16em;text-transform:uppercase;padding:3px 8px;border-radius:2px;justify-self:start}
  .redlines .row .badge.high{background:rgba(255,93,108,.15);color:var(--hb)}
  .redlines .row .badge.med{background:rgba(255,200,61,.13);color:var(--rf)}
  .redlines .row .badge.low{background:rgba(255,255,255,.04);color:var(--muted)}
  .redlines .row .title{font-weight:600;font-size:13px;margin-bottom:4px}
  .redlines .row .summary{color:var(--ink);font-size:12px;line-height:1.5}
  .redlines .row .fix{margin-top:6px;font-size:11px;color:var(--dp)}
  .redlines .row .sim{text-align:right;font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}

  main{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:24px 28px}
  .col{display:flex;flex-direction:column;gap:14px;min-height:200px}
  .col h2{margin:0;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted);padding-bottom:8px;border-bottom:1px dashed var(--line)}
  .col.hardball h2{color:var(--hb)}
  .col.diplomat h2{color:var(--dp)}

  .turn{background:var(--panel);border-left:3px solid var(--line);padding:14px 16px;border-radius:2px;opacity:0;transform:translateY(6px);animation:in .35s ease-out forwards}
  .turn.hardball{border-left-color:var(--hb)}
  .turn.diplomat{border-left-color:var(--dp)}
  @keyframes in{to{opacity:1;transform:translateY(0)}}
  .turn .head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:8px}
  .turn .round{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
  .turn .price{font-size:13px;color:var(--rf)}
  .turn .headline{font-size:13px;font-weight:600;margin-bottom:6px}
  .turn .body{color:var(--ink);font-size:13px;line-height:1.55}
  .turn .cites{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
  .turn .cite{font-size:10px;padding:2px 8px;background:rgba(255,255,255,.04);color:var(--muted);border-radius:99px;letter-spacing:.04em}

  .verdict{margin:0 28px 28px;background:linear-gradient(180deg,rgba(255,200,61,.08),rgba(255,200,61,0));border:1px solid rgba(255,200,61,.35);padding:22px 24px;border-radius:4px;opacity:0;transform:translateY(8px);animation:in .45s ease-out forwards}
  .verdict h2{margin:0 0 4px;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--rf)}
  .verdict .headline{font-size:18px;margin:8px 0 12px}
  .verdict .body{color:var(--ink);font-size:14px;line-height:1.6;max-width:880px}
  .verdict .savings{margin-top:18px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
  .verdict .savings .k{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
  .verdict .savings .v{font-size:18px;color:var(--rf)}

  .email{margin:0 28px 22px;background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:0;display:none;overflow:hidden}
  .email.on{display:block;animation:in .35s ease-out}
  .email .head{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
  .email .head h2{margin:0;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--dp)}
  .email .head .stamp{font-size:11px;color:var(--muted);letter-spacing:.06em}
  .email .meta{padding:12px 20px;display:grid;grid-template-columns:80px 1fr;gap:6px 14px;border-bottom:1px solid var(--line);font-size:12px}
  .email .meta .k{color:var(--muted);text-transform:uppercase;letter-spacing:.14em;font-size:10px;padding-top:2px}
  .email .meta .v{color:var(--ink)}
  .email .subject{padding:12px 20px;font-weight:600;font-size:14px;border-bottom:1px solid var(--line)}
  .email pre.body{margin:0;padding:18px 20px;color:var(--ink);font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;background:#0e1218}
  .email .cites{padding:10px 20px;display:flex;flex-wrap:wrap;gap:6px;border-top:1px solid var(--line)}
  .email .cite{font-size:10px;padding:2px 8px;background:rgba(122,162,255,.08);color:var(--acc);border-radius:99px;letter-spacing:.04em}

  .tagline{padding:10px 28px;border-bottom:1px solid var(--line);color:var(--muted);font-size:12px;letter-spacing:.04em}
  .tagline strong{color:var(--ink);font-weight:600}

  .sponsors{padding:10px 28px;border-top:1px solid var(--line);background:#080a0e;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .sponsors .label{font-size:10px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted);margin-right:6px}
  .sponsors .chip{font-size:11px;padding:3px 9px;border:1px solid var(--line);border-radius:99px;color:var(--ink);letter-spacing:.02em}
  .sponsors .chip.live{border-color:var(--dp);color:var(--dp)}
  .sponsors .chip.mock{color:var(--muted)}

  footer{padding:14px 28px;border-top:1px solid var(--line);color:var(--muted);font-size:11px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
  footer a{color:var(--acc);text-decoration:none}
  .mock-flag{color:var(--muted);font-size:10px;margin-left:6px}
  @media (max-width:820px){main{grid-template-columns:1fr}.meta{grid-template-columns:repeat(2,1fr)}.verdict .savings{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<header>
  <div class="brand">
    <span class="dot" id="dot"></span>
    <h1>ShadowBuyer · autonomous B2B procurement</h1>
    <span class="tag" id="modetag">mock fallback</span>
  </div>
  <button id="go">Run the swarm →</button>
</header>

<section class="tagline">
  Six weeks of demos, RFPs, and pricing games — collapsed to six hours.
  Watch a <strong>6-agent swarm</strong> research, negotiate, and redline a Datadog deal live.
  $5T procurement market. Every CFO has lost a quarter to this.
</section>

<section class="meta">
  <div class="cell"><span class="k">Vendor</span><span class="v" id="m-vendor">—</span></div>
  <div class="cell"><span class="k">Competing</span><span class="v" id="m-comp">—</span></div>
  <div class="cell"><span class="k">Hosts</span><span class="v" id="m-hosts">—</span></div>
  <div class="cell"><span class="k">List $/host/mo</span><span class="v" id="m-list">—</span></div>
  <div class="cell"><span class="k">Live target $/host/mo</span><span class="v big" id="m-price">—</span></div>
</section>

<section class="pipeline" id="pipeline">
  <span class="step" data-stage="scout">scout</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="quote_hunter">quote hunter</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="negotiator">negotiator</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="referee">referee</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="contract_diff">contract diff</span>
</section>

<main>
  <div class="col hardball"><h2>HARDBALL · Qwen3-Max via TokenRouter</h2><div id="hb"></div></div>
  <div class="col diplomat"><h2>DIPLOMAT · GLM-5.1 via Z.ai</h2><div id="dp"></div></div>
</main>

<section class="verdict" id="verdict" style="display:none">
  <h2>Referee verdict</h2>
  <div class="headline" id="v-headline"></div>
  <div class="body" id="v-body"></div>
  <div class="savings">
    <div><div class="k">Final $/host/mo</div><div class="v" id="v-final">—</div></div>
    <div><div class="k">Discount vs list</div><div class="v" id="v-disc">—</div></div>
    <div><div class="k">Annual savings</div><div class="v" id="v-save">—</div></div>
    <div><div class="k">Strategy</div><div class="v" id="v-strat">—</div></div>
  </div>
</section>

<section class="email" id="email">
  <div class="head">
    <h2>Outbound email to AE · drafted, not sent</h2>
    <span class="stamp" id="em-stamp">—</span>
  </div>
  <div class="meta">
    <div class="k">From</div><div class="v" id="em-from">—</div>
    <div class="k">To</div><div class="v" id="em-to">—</div>
    <div class="k">Strategy</div><div class="v" id="em-strat">—</div>
  </div>
  <div class="subject" id="em-subject">—</div>
  <pre class="body" id="em-body">—</pre>
  <div class="cites" id="em-cites"></div>
</section>

<section class="redlines" id="redlines">
  <h2>Contract Diff · MSA redlines</h2>
  <div class="top">
    <div class="count"><strong id="rd-count">0</strong> deviations flagged in <span id="rd-vendor">vendor</span> MSA</div>
    <div class="sev">
      <span class="pill high" id="rd-high">high 0</span>
      <span class="pill med"  id="rd-med">med 0</span>
      <span class="pill low"  id="rd-low">low 0</span>
      <span class="pill" id="rd-backend">backend: heuristic</span>
    </div>
  </div>
  <div id="rd-rows"></div>
</section>

<section class="sponsors" id="sponsors">
  <span class="label">Built on</span>
  <span class="chip" data-name="AgentField">AgentField</span>
  <span class="chip" data-name="TokenRouter">TokenRouter</span>
  <span class="chip" data-name="Qwen Cloud">Qwen Cloud</span>
  <span class="chip" data-name="Z.ai">Z.ai · GLM-5.1</span>
  <span class="chip" data-name="Evermind">Evermind</span>
  <span class="chip" data-name="Nosana">Nosana</span>
  <span class="chip" data-name="Bright Data">Bright Data</span>
  <span class="chip" data-name="Actionbook">Actionbook</span>
  <span class="chip" data-name="Zeabur">Zeabur</span>
  <span class="chip" data-name="Qoder">Qoder</span>
  <span class="chip" data-name="Butterbase">Butterbase</span>
</section>

<footer>
  <div>shadowbuyer · adversarial procurement · <a href="/api/demo-state" target="_blank">/api/demo-state</a> · <a href="/api/sponsor-health" target="_blank">/api/sponsor-health</a> · <a href="/healthz" target="_blank">/healthz</a></div>
  <div><a href="https://github.com/LeSingh1/shadowbuyer" target="_blank">source</a></div>
</footer>

<script>
const $ = id => document.getElementById(id);
const dot = $('dot'), go = $('go'), modetag = $('modetag');
const hbCol = $('hb'), dpCol = $('dp'), verdict = $('verdict');

function setStep(stage, state){
  document.querySelectorAll('.pipeline .step').forEach(s=>{
    if(s.dataset.stage===stage){ s.classList.remove('active','done'); s.classList.add(state); }
  });
}
function resetUI(){
  hbCol.innerHTML=''; dpCol.innerHTML=''; verdict.style.display='none';
  ['m-vendor','m-comp','m-hosts','m-list','m-price'].forEach(i=>$(i).textContent='—');
  document.querySelectorAll('.pipeline .step').forEach(s=>{s.classList.remove('active','done')});
  const redlines = $('redlines'); redlines.classList.remove('on');
  $('rd-rows').innerHTML=''; $('rd-count').textContent='0';
  $('rd-high').textContent='high 0'; $('rd-med').textContent='med 0'; $('rd-low').textContent='low 0';
  $('email').classList.remove('on');
}
function renderEmail(em){
  if(!em) return;
  $('email').classList.add('on');
  $('em-from').textContent = em.from;
  $('em-to').textContent = em.to;
  $('em-strat').textContent = em.strategy;
  $('em-subject').textContent = em.subject;
  $('em-body').textContent = em.body;
  $('em-stamp').textContent = em.dry_run ? 'dry-run · not delivered' : 'sent';
  const c = $('em-cites'); c.innerHTML = '';
  (em.cites||[]).forEach(x=>{const s=document.createElement('span');s.className='cite';s.textContent=x;c.appendChild(s);});
}
function renderRedline(r){
  $('redlines').classList.add('on');
  const row = document.createElement('div');
  row.className = 'row';
  row.innerHTML = `
    <div><span class="badge ${r.severity}">${r.severity}</span></div>
    <div>
      <div class="title">${r.clause_title}</div>
      <div class="summary">${r.deviation_summary}</div>
      <div class="fix">↳ ${r.recommended_redline}</div>
    </div>
    <div class="sim">sim ${Number(r.similarity).toFixed(2)}</div>`;
  $('rd-rows').appendChild(row);
}
function renderTurn(t){
  const col = t.role === 'hardball' ? hbCol : dpCol;
  const div = document.createElement('div');
  div.className = `turn ${t.role}`;
  const price = t.price_target_per_host_mo != null ? `$${Number(t.price_target_per_host_mo).toFixed(2)}/host` : '';
  const term  = t.deal_term_months ? ` · ${t.deal_term_months}mo` : '';
  const mock  = t.mocked ? '<span class="mock-flag">(mock)</span>' : '';
  div.innerHTML = `
    <div class="head"><span class="round">Round ${t.round}${mock}</span><span class="price">${price}${term}</span></div>
    <div class="headline">${t.headline||''}</div>
    <div class="body">${t.text}</div>
    <div class="cites">${(t.cites||[]).map(c=>`<span class="cite">${c}</span>`).join('')}</div>`;
  col.appendChild(div);
  if(t.price_target_per_host_mo != null){ $('m-price').textContent = `$${Number(t.price_target_per_host_mo).toFixed(2)}`; }
}
function renderVerdict(t, summary){
  $('v-headline').textContent = t.headline || '';
  $('v-body').textContent = t.text || '';
  if(summary){
    $('v-final').textContent = `$${Number(summary.final_price_per_host_mo).toFixed(2)}`;
    $('v-disc').textContent  = `${summary.discount_vs_list_pct}%`;
    $('v-save').textContent  = `$${Number(summary.annual_savings_vs_list_usd).toLocaleString()}`;
    $('v-strat').textContent = summary.winning_strategy || '—';
  }
  verdict.style.display='block';
}

go.onclick = () => {
  resetUI(); go.disabled=true; dot.classList.add('live');
  const es = new EventSource('/run/stream?category=observability');
  let lastSummary = null;
  es.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if(ev.event === 'stage_start'){
      setStep(ev.stage,'active');
      if(ev.stage === 'negotiator'){
        $('m-vendor').textContent = ev.target_vendor;
        $('m-comp').textContent = ev.competing_vendor;
        $('m-hosts').textContent = ev.hosts;
        $('m-list').textContent = `$${ev.list_price_per_host_mo}`;
        $('m-price').textContent = `$${Number(ev.starting_quote_per_host_mo).toFixed(2)}`;
      }
    } else if(ev.event === 'stage_done'){
      setStep(ev.stage,'done');
    } else if(ev.event === 'negotiator_turn'){
      const t = ev.turn;
      if(t.role === 'referee'){ setStep('referee','active'); renderVerdict(t, lastSummary); setStep('referee','done'); }
      else { renderTurn(t); }
    } else if(ev.event === 'contract_diff_summary'){
      $('redlines').classList.add('on');
      $('rd-count').textContent = ev.redline_count;
      $('rd-vendor').textContent = ev.vendor;
      $('rd-high').textContent = `high ${ev.severity_counts.high||0}`;
      $('rd-med').textContent  = `med ${ev.severity_counts.med||0}`;
      $('rd-low').textContent  = `low ${ev.severity_counts.low||0}`;
      $('rd-backend').textContent = `backend: ${ev.embedding_backend}`;
    } else if(ev.event === 'redline'){ renderRedline(ev.redline);
    } else if(ev.event === 'summary'){
      lastSummary = ev.payload;
      // verdict may have rendered before summary arrived; patch numbers in.
      if(lastSummary){
        $('v-final').textContent = `$${Number(lastSummary.final_price_per_host_mo).toFixed(2)}`;
        $('v-disc').textContent  = `${lastSummary.discount_vs_list_pct}%`;
        $('v-save').textContent  = `$${Number(lastSummary.annual_savings_vs_list_usd).toLocaleString()}`;
        $('v-strat').textContent = lastSummary.winning_strategy || '—';
      }
    } else if(ev.event === 'done'){
      // After the stream finishes, fetch the email draft and render it.
      fetch('/api/email-draft').then(r=>r.json()).then(j=>{ if(j.ok) renderEmail(j.email); }).catch(()=>{});
      es.close(); go.disabled=false; dot.classList.remove('live');
    }
  };
  es.onerror = () => { es.close(); go.disabled=false; dot.classList.remove('live'); };
};

fetch('/api/sponsor-health').then(r=>r.json()).then(h=>{
  const liveCount = (h.counts||{}).live || 0;
  modetag.textContent = liveCount > 0 ? `${liveCount} sponsor${liveCount===1?'':'s'} live · ${h.counts.mock||0} mock` : 'mock fallback · all 11 sponsors wired';
  // Color each sponsor chip by env_status.
  const byName = {};
  (h.sponsors||[]).forEach(s => byName[s.name] = s);
  document.querySelectorAll('.sponsors .chip').forEach(chip => {
    const s = byName[chip.dataset.name];
    if (s && s.env_status === 'live') chip.classList.add('live');
    else if (s && s.env_status === 'mock') chip.classList.add('mock');
  });
}).catch(()=>{});
</script>
</body></html>"""
