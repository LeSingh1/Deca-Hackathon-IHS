import { motion, useReducedMotion } from "motion/react";
import { money } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Panel, Skeleton } from "./Panel";

export function RedlinePanel({ s }: { s: RunState }) {
  const reduce = useReducedMotion();
  const total = s.redlines.reduce((n, r) => n + (r.dollars_at_risk ?? 0), 0);
  return (
    <Panel
      id="redlines"
      title="Contract traps, marked up"
      who="Contract Exposer"
      tag={s.redlines.length > 0 && <span className="tag trap num">{money(total)} at risk</span>}
    >
      {s.redlines.length === 0 ? (
        <Skeleton rows={6} h={26} />
      ) : (
        <div className="redlines">
          {s.redlines.map((r) => (
            <motion.div
              key={`${r.doc}-${r.clause_key}`}
              className={`rl ${r.severity}`}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
            >
              <div className="rl-h">
                <span className={`tag ${r.severity === "high" ? "trap" : "muted"}`}>{r.severity}</span>
                <b>{r.title}</b>
                <span className="hint" style={{ fontSize: 12 }}>
                  {r.doc === "mca_offer" ? "cash advance" : "processing agreement"}
                </span>
                {r.dollars_at_risk ? <span className="num">{money(r.dollars_at_risk)}</span> : null}
              </div>
              <p className="orig">
                <motion.span
                  className="strike"
                  initial={reduce ? false : { backgroundSize: "0% 2px" }}
                  animate={{ backgroundSize: "100% 2px" }}
                  transition={{ duration: 0.4, delay: reduce ? 0 : 0.15, ease: "easeInOut" }}
                >
                  {r.original}
                </motion.span>
              </p>
              <motion.p
                className="revised"
                initial={reduce ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3, delay: reduce ? 0 : 0.5 }}
              >
                {r.revised}
              </motion.p>
              <p className="why">{r.why}</p>
            </motion.div>
          ))}
        </div>
      )}
    </Panel>
  );
}
