import { motion, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import type { Lane } from "../lib/contract";
import { money, pct } from "../lib/format";
import { laneOffer, type RunState, type Turn } from "../lib/runState";
import { ModeTag, Panel } from "./Panel";

const LANE_META: Record<Lane, { name: string; who: string }> = {
  hardball: { name: "Hardball", who: "competitor quote + switch threat" },
  diplomat: { name: "Diplomat", who: "loyalty + growth" },
};

function Convo({ turns }: { turns: Turn[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const len = turns.reduce((n, t) => n + t.text.length + (t.offer ? 1 : 0), 0);
  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [len, turns.length]);
  return (
    <div className="convo" ref={ref} aria-live="off">
      {turns.length === 0 && <p className="hint">Waiting for the opening move…</p>}
      {turns.map((t, i) => (
        <div key={i} className={`say ${t.speaker === "rep" ? "rep" : "agent"}`}>
          <span className="who">{t.speaker === "rep" ? "Processor rep" : `${t.speaker} · round ${t.round}`}</span>
          {t.text}
          {t.offer && (
            <div>
              <span className="offer">
                offer → {pct(t.offer.effective_rate)} · {money(t.offer.annual_savings)}/yr
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Tug({ current, target, offer }: { current: number; target: number; offer: number | null }) {
  const reduce = useReducedMotion();
  const pos = offer == null ? 0 : Math.min(1, Math.max(0, (current - offer) / (current - target)));
  return (
    <div className="tug" aria-label={`Rate tug-of-war: ${offer == null ? "no offer yet" : pct(offer)}`}>
      <div className="tug-track">
        <motion.div
          className="tug-knot"
          initial={false}
          animate={{ left: `${pos * 100}%` }}
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 120, damping: 16 }}
        />
      </div>
      <div className="tug-ends">
        <span>they keep <span className="num">{pct(current)}</span></span>
        <span className="num" style={{ fontWeight: 700 }}>{offer == null ? "—" : pct(offer)}</span>
        <span>fair <span className="num">{pct(target)}</span></span>
      </div>
    </div>
  );
}

export function NegotiationPanel({ s }: { s: RunState }) {
  const current = s.rate?.effective_rate ?? 0.0328;
  const target = s.rate?.quotes.find((q) => q.kind === "benchmark")?.effective_rate ?? 0.0242;
  const st = s.stages.negotiator;
  const v = s.verdict;
  return (
    <Panel id="negotiator" title="The negotiation" who="Hardball & Diplomat vs. the processor's retention rep"
      tag={st.status !== "pending" && <ModeTag live={st.live} />}>
      <div className="duel">
        {(["hardball", "diplomat"] as Lane[]).map((lane) => (
          <div key={lane} className="lane">
            <div className="lane-h">
              <b>{LANE_META[lane].name}</b>
              <small>{LANE_META[lane].who}</small>
            </div>
            <Convo turns={s.lanes[lane]} />
            <Tug current={current} target={target} offer={laneOffer(s.lanes[lane])?.effective_rate ?? null} />
          </div>
        ))}
      </div>

      {v && (
        <motion.div
          className="verdict"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          <h3>Referee: {v.winner === "hardball" ? "Hardball" : v.winner === "diplomat" ? "Diplomat" : v.winner} wins</h3>
          <p>{v.rationale}</p>
          <table className="opts">
            <thead>
              <tr>
                <th>Option</th>
                <th className="r">Rate</th>
                <th className="r">Saves / yr</th>
                <th className="r">Exit costs</th>
                <th className="r">Year-1 net</th>
              </tr>
            </thead>
            <tbody>
              {v.options.map((o) => (
                <tr key={o.key} className={o.key === v.winner ? "win" : ""}>
                  <td>{o.label}</td>
                  <td className="r num">{pct(o.effective_rate)}</td>
                  <td className="r num">{money(o.annual_savings)}</td>
                  <td className="r num">{money(o.one_time_costs)}</td>
                  <td className={`r num ${o.net_first_year < 0 ? "neg" : ""}`}>{money(o.net_first_year)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {v.reasoning_summary && (
            <details className="reasoning">
              <summary>Referee&apos;s reasoning summary</summary>
              <p>{v.reasoning_summary}</p>
            </details>
          )}
        </motion.div>
      )}
    </Panel>
  );
}
