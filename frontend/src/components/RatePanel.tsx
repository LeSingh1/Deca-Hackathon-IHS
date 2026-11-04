import { motion, useReducedMotion } from "motion/react";
import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Panel, Skeleton } from "./Panel";

export function RatePanel({ s }: { s: RunState }) {
  const reduce = useReducedMotion();
  const quotes = s.rate?.quotes ?? [];
  const max = Math.max(0.035, ...quotes.map((q) => q.effective_rate));
  return (
    <Panel id="rate_scout" title="What a fair price looks like" who="Rate Scout · deterministic"
      tag={quotes.some((q) => q.illustrative) && <span className="tag muted">illustrative quotes</span>}>
      {!s.rate ? (
        <Skeleton rows={4} h={22} />
      ) : (
        <div className="bars">
          {quotes.map((q, i) => (
            <div key={q.key} className="barrow">
              <span className="lbl">
                {q.label}
                <small>{q.source.length > 70 ? q.source.slice(0, 68) + "…" : q.source} · {q.as_of}</small>
              </span>
              <div className="track" aria-hidden="true">
                <motion.div
                  className={`fill ${q.kind}`}
                  initial={reduce ? false : { width: 0 }}
                  animate={{ width: `${(q.effective_rate / max) * 100}%` }}
                  transition={{ duration: 0.4, delay: reduce ? 0 : i * 0.08, ease: "easeOut" }}
                />
              </div>
              <span className="val num">
                {pct(q.effective_rate)}
                {q.kind !== "current" && (
                  <small>{q.annual_savings >= 0 ? `${money(q.annual_savings)}/yr less` : `${money(-q.annual_savings)}/yr more`}</small>
                )}
              </span>
            </div>
          ))}
          <p className="hint" style={{ margin: "4px 0 0" }}>
            Switching processors has exit costs; the Referee weighs them below.
          </p>
        </div>
      )}
    </Panel>
  );
}
