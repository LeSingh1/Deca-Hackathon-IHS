import { MotionConfig } from "motion/react";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { Btn } from "./components/ui";
import { getServices, sendSms, startDemo, subscribe, type Pace } from "./lib/api";
import type { Stage } from "./lib/contract";
import { initialState, reducer } from "./lib/runState";
import { CashAdvance } from "./views/CashAdvance";
import { Contracts } from "./views/Contracts";
import { Negotiation } from "./views/Negotiation";
import { Overview } from "./views/Overview";
import { OwnerTexts } from "./views/OwnerTexts";
import { Quotes } from "./views/Quotes";
import { Savings } from "./views/Savings";
import { ServiceHealth } from "./views/ServiceHealth";
import { Statement } from "./views/Statement";

type ViewId = "overview" | "texts" | "statement" | "quotes" | "negotiation" | "advance" | "contracts" | "savings" | "services";

const VIEWS: { id: ViewId; label: string; icon: string; stages?: Stage[] }[] = [
  { id: "overview", label: "Overview", icon: "ti-layout-dashboard" },
  { id: "texts", label: "Owner texts", icon: "ti-mail", stages: ["statement_reader", "approval"] },
  { id: "statement", label: "Statement", icon: "ti-file-invoice", stages: ["fee_hunter"] },
  { id: "quotes", label: "Quotes", icon: "ti-scale", stages: ["rate_scout"] },
  { id: "negotiation", label: "Negotiation log", icon: "ti-messages", stages: ["negotiator"] },
  { id: "advance", label: "Cash advance", icon: "ti-alert-triangle" },
  { id: "contracts", label: "Contracts", icon: "ti-file-check", stages: ["contract_exposer"] },
  { id: "savings", label: "Savings", icon: "ti-coin", stages: ["action_drafter", "executor"] },
  { id: "services", label: "Service health", icon: "ti-plug" },
];

// While a run is playing, the screen follows the swarm until the viewer picks a screen themselves.
const FOLLOW: Partial<Record<Stage, ViewId>> = {
  statement_reader: "texts",
  fee_hunter: "statement",
  rate_scout: "quotes",
  negotiator: "negotiation",
  contract_exposer: "advance",
  action_drafter: "savings",
  approval: "texts",
  executor: "savings",
};

export default function App() {
  const [s, dispatch] = useReducer(reducer, undefined, () => initialState());
  const [pace, setPace] = useState<Pace>("presenter");
  const [view, setView] = useState<ViewId>("overview");
  const follow = useRef(false);
  const unsub = useRef<(() => void) | null>(null);
  const content = useRef<HTMLElement>(null);

  useEffect(() => {
    getServices().then((services) => dispatch({ type: "services", services }));
    return () => unsub.current?.();
  }, []);

  useEffect(() => {
    const next = s.active && FOLLOW[s.active];
    if (follow.current && next) setView(next);
  }, [s.active]);

  useEffect(() => {
    if (follow.current && s.redlines.length === 1) setView("contracts");
  }, [s.redlines.length]);

  // Keep the newest thing on screen while following.
  useEffect(() => {
    const el = content.current;
    if (follow.current && el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [s.redlines.length, s.verdict, s.messages.length]);

  const start = useCallback(async () => {
    unsub.current?.();
    dispatch({ type: "starting" });
    follow.current = true;
    setView("texts");
    const runId = await startDemo(pace);
    if (!runId) {
      dispatch({ type: "event", ev: { event: "error", run_id: "", seq: 0, message: "Could not reach the backend." } });
      return;
    }
    unsub.current = subscribe(runId, (ev) => dispatch({ type: "event", ev }));
  }, [pace]);

  const restart = useCallback(() => {
    unsub.current?.();
    follow.current = false;
    dispatch({ type: "reset", services: s.services });
    setView("overview");
  }, [s.services]);

  const send = useCallback(
    (body: string) => {
      follow.current = true;
      dispatch({ type: "notice", message: null });
      void sendSms(body, s.runId).then((ok) => {
        if (!ok) dispatch({ type: "notice", message: "That text didn't send. Check the connection and try again." });
      });
    },
    [s.runId],
  );

  const pick = (id: ViewId) => {
    follow.current = false;
    setView(id);
  };

  const idle = s.status === "idle";
  const awaiting = s.status === "awaiting" && !!s.approval && !s.approvalReceived;
  const counts: Partial<Record<ViewId, number>> = {
    texts: s.messages.length || undefined,
    statement: s.lineItems.length || undefined,
    quotes: s.rate?.quotes.length,
    contracts: s.redlines.length || undefined,
    savings: s.actions.length || undefined,
    services: Object.keys(s.services).length || undefined,
  };
  const active = VIEWS.find((v) => v.id === view);

  return (
    <MotionConfig reducedMotion="user">
      <div className="procure-root">
        <div className="shell">
          <aside className="sidebar">
            <div className="logo">
              <i className="ti ti-building-store" aria-hidden="true" />
              ShadowBuyer
              <small>for Main Street</small>
            </div>
            <span className="nav-section">Workspace</span>
            {VIEWS.map((v) => {
              const isActiveStage = !!s.active && !!v.stages?.includes(s.active);
              return (
                <button key={v.id} className={`nav-item ${view === v.id ? "active" : ""}`} onClick={() => pick(v.id)}>
                  <i className={`ti ${v.icon}`} aria-hidden="true" />
                  {v.label}
                  {v.id === "texts" && awaiting ? (
                    <span className="nav-badge ask">Reply</span>
                  ) : isActiveStage ? (
                    <span className="swarm-dot live nav-pulse" aria-label="working" />
                  ) : counts[v.id] != null ? (
                    <span className="nav-badge">{counts[v.id]}</span>
                  ) : null}
                </button>
              );
            })}
            <div className="sidebar-bottom">
              <div className="side-status" aria-label="Service status">
                {Object.entries(s.services).map(([k, mode]) => (
                  <div key={k}>
                    <span className={`dot ${mode === "live" ? "dot-green" : "dot-amber"}`} />
                    {k.charAt(0).toUpperCase() + k.slice(1)} · {mode}
                  </div>
                ))}
              </div>
            </div>
          </aside>

          <div className="main">
            <header className="topbar">
              <div className="topbar-left">
                <span className="page-title">{active?.label}</span>
                {counts[view] != null && <span className="page-count">{counts[view]}</span>}
              </div>
              <div className="topbar-actions">
                <span className="run-cost">Run cost <b>${s.costTotal.toFixed(4)}</b> {s.costLive ? "" : "(mock)"}</span>
                <div className="pace" role="group" aria-label="Pacing">
                  <button aria-pressed={pace === "presenter"} onClick={() => setPace("presenter")}>Presenter{s.services.claude === "live" ? "" : " ~75s"}</button>
                  <button aria-pressed={pace === "fast"} onClick={() => setPace("fast")}>Fast{s.services.claude === "live" ? "" : " ~10s"}</button>
                </div>
                {idle ? (
                  <Btn primary icon="ti-bolt" onClick={start}>Run the swarm</Btn>
                ) : (
                  <Btn primary icon="ti-refresh" onClick={restart}>New run</Btn>
                )}
              </div>
            </header>

            <main className="content" ref={content} key={view}>
              {s.error && <div className="error-box" role="alert" style={{ marginBottom: 14 }}>{s.error}</div>}
              {view === "overview" && <Overview s={s} onStart={start} />}
              {view === "texts" && <OwnerTexts s={s} onSend={send} onStart={start} />}
              {view === "statement" && <Statement s={s} />}
              {view === "quotes" && <Quotes s={s} />}
              {view === "negotiation" && <Negotiation s={s} onRun={start} />}
              {view === "advance" && <CashAdvance s={s} />}
              {view === "contracts" && <Contracts s={s} />}
              {view === "savings" && <Savings s={s} />}
              {view === "services" && <ServiceHealth s={s} />}
            </main>
          </div>
        </div>
      </div>
    </MotionConfig>
  );
}
