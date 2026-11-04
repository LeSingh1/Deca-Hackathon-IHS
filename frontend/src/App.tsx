import { MotionConfig, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ActionPanel } from "./components/ActionPanel";
import { AprPanel } from "./components/AprPanel";
import { Header, type Theme } from "./components/Header";
import { Hero } from "./components/Hero";
import { NegotiationPanel } from "./components/NegotiationPanel";
import { Phone } from "./components/Phone";
import { RatePanel } from "./components/RatePanel";
import { RedlinePanel } from "./components/RedlinePanel";
import { StageRail } from "./components/StageRail";
import { StatementPanel } from "./components/StatementPanel";
import { getServices, sendSms, startDemo, subscribe, type Pace } from "./lib/api";
import type { Stage } from "./lib/contract";
import { initialState, reducer } from "./lib/runState";

const PANEL_FOR: Partial<Record<Stage, string>> = {
  statement_reader: "statement_reader",
  fee_hunter: "fee_hunter",
  rate_scout: "rate_scout",
  negotiator: "negotiator",
  contract_exposer: "contract_exposer",
  action_drafter: "action_drafter",
  approval: "action_drafter",
  executor: "action_drafter",
};

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("sb-theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function Intro({ onStart }: { onStart: () => void }) {
  return (
    <section className="panel intro">
      <h1>Card fees are a restaurant&apos;s second-biggest bill after labor.</h1>
      <p>
        An independent restaurant doing $1.2M a year on cards runs on 3-4% margins and loses 2-3% of every swipe to
        processing. The worst of it hides in tier surcharges, junk fees and contracts nobody reads, and the
        &ldquo;simple&rdquo; cash advance in their inbox can cost 60-150% APR.
      </p>
      <p>
        ShadowBuyer is a swarm of agents that works over text. The owner sends a photo of the statement. The agents find the
        fees, translate the cash advance into a real APR, negotiate with the processor, and act only after the owner
        replies YES.
      </p>
      <div className="stats">
        <div><b>2-3%</b><span>of every card sale goes to fees</span></div>
        <div><b>3-4%</b><span>typical full-service margin</span></div>
        <div><b>60-150%</b><span>APR hidden in many cash advances</span></div>
      </div>
      <button className="btn money" onClick={onStart} style={{ fontSize: 18, padding: "14px 24px" }}>
        Run demo: Mario&apos;s Trattoria
      </button>
      <p className="hint" style={{ marginTop: 14 }}>
        Fictional restaurant, processor and lender. Benchmarks are labeled illustrative. All figures come from tested calculators.
      </p>
    </section>
  );
}

export default function App() {
  const [s, dispatch] = useReducer(reducer, undefined, () => initialState());
  const [pace, setPace] = useState<Pace>("presenter");
  const [theme, setThemeState] = useState<Theme>(readTheme);
  const unsub = useRef<(() => void) | null>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    getServices().then((services) => dispatch({ type: "services", services }));
    return () => unsub.current?.();
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("sb-theme", theme);
    } catch {
      /* storage unavailable: theme still applies for this session */
    }
  }, [theme]);

  // Keep the active agent's panel in view while presenting.
  useEffect(() => {
    if (!s.active) return;
    const id = PANEL_FOR[s.active];
    const el = id ? document.getElementById(`panel-${id}`) : null;
    el?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }, [s.active, reduce]);

  const start = useCallback(async () => {
    unsub.current?.();
    dispatch({ type: "starting" });
    const runId = await startDemo(pace);
    if (!runId) {
      dispatch({ type: "event", ev: { event: "error", run_id: "", seq: 0, message: "Could not reach the backend." } });
      return;
    }
    unsub.current = subscribe(runId, (ev) => dispatch({ type: "event", ev }));
  }, [pace]);

  const restart = useCallback(() => {
    unsub.current?.();
    dispatch({ type: "reset", services: s.services });
  }, [s.services]);

  const idle = s.status === "idle";

  return (
    <MotionConfig reducedMotion="user">
      <Header
        services={s.services}
        pace={pace}
        setPace={setPace}
        theme={theme}
        setTheme={setThemeState}
        cost={s.costTotal}
        costLive={s.costLive}
        canRestart={!idle}
        onRestart={restart}
      />
      <main className="stage">
        <div className="phone-col">
          <Phone state={s} onSend={(b) => void sendSms(b)} onStart={start} />
        </div>
        <div className="cc" aria-label="Swarm command center">
          {idle ? (
            <Intro onStart={start} />
          ) : (
            <>
              <Hero s={s} />
              <StageRail s={s} />
              {s.error && (
                <div className="panel" role="alert" style={{ borderColor: "var(--trap)" }}>
                  {s.error}
                </div>
              )}
              <StatementPanel s={s} />
              <RatePanel s={s} />
              <NegotiationPanel s={s} />
              <AprPanel s={s} />
              <RedlinePanel s={s} />
              <ActionPanel s={s} />
              <p className="foot">
                ShadowBuyer for Main Street · every dollar figure is computed by unit-tested calculators, never by a model ·
                sandbox actions are labeled · contract v1.0.0
              </p>
            </>
          )}
        </div>
      </main>
    </MotionConfig>
  );
}
