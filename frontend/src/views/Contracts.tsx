import { motion, useReducedMotion } from "motion/react";
import { money } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Badge, Empty, Metric } from "../components/ui";

export function Contracts({ s }: { s: RunState }) {
  const reduce = useReducedMotion();
  const atRisk = s.redlines.reduce((n, r) => n + (r.dollars_at_risk ?? 0), 0);
  const high = s.redlines.filter((r) => r.severity === "high").length;
  return (
    <>
      <div className="metrics">
        <Metric label="Traps found">{s.redlines.length}</Metric>
        <Metric label="High severity" tone={high ? "warn" : ""}>{high}</Metric>
        <Metric label="Dollars at risk" tone={atRisk ? "red" : ""}>{money(atRisk)}</Metric>
        <Metric label="Documents reviewed">{s.redlines.length ? 2 : 0}</Metric>
      </div>
      {s.redlines.length === 0 ? (
        <Empty>Waiting for the Contract Exposer…</Empty>
      ) : (
        <table className="list-table top">
          <thead>
            <tr>
              <th>Clause / what to ask for</th>
              <th style={{ width: 170 }}>Document</th>
              <th style={{ width: 96 }}>Severity</th>
              <th className="r" style={{ width: 100 }}>At risk</th>
            </tr>
          </thead>
          <tbody>
            {s.redlines.map((r) => (
              <motion.tr key={`${r.doc}-${r.clause_key}`} initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
                <td>
                  <div className="td-primary">{r.title}</div>
                  <div className="td-secondary">{r.why}</div>
                  <div className="rl-orig">{r.original}</div>
                  <div className="rl-new">→ {r.revised}</div>
                </td>
                <td className="td-dim">{r.doc === "mca_offer" ? "Cash advance" : "Processing agreement"}</td>
                <td><Badge variant={r.severity === "high" ? "red" : "amber"}>{r.severity === "high" ? "High" : "Medium"}</Badge></td>
                <td className="td-amount r num">{r.dollars_at_risk ? money(r.dollars_at_risk) : "—"}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
