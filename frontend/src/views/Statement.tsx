import { motion, useReducedMotion } from "motion/react";
import { CATEGORY_LABEL, money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Badge, Empty, Metric, ModeBadge, Num, StatusDot } from "../components/ui";

export function Statement({ s }: { s: RunState }) {
  const reduce = useReducedMotion();
  const flags = new Map(s.flagged.map((f) => [f.item_id, f]));
  const total = s.lineItems.reduce((n, li) => n + li.amount, 0);
  const fh = s.stages.fee_hunter;
  return (
    <>
      <div className="metrics">
        <Metric label="Lines read">{s.lineItems.length} of {s.totalItems}</Metric>
        <Metric label="Total fees this month"><Num value={total} format={(n) => money(n, true)} /></Metric>
        <Metric label="You pay today">{s.rate ? pct(s.rate.effective_rate) : "—"}</Metric>
        <Metric label="You can fight" tone="warn"><Num value={s.hiddenTotal} format={(n) => `${money(n, true)}/mo`} /></Metric>
      </div>
      {s.lineItems.length === 0 ? (
        <Empty>Waiting for the owner&apos;s statement photo…</Empty>
      ) : (
        <>
          <table className="list-table">
            <thead>
              <tr>
                <th style={{ width: 54 }}>Line</th>
                <th>Description</th>
                <th style={{ width: 180 }}>Category</th>
                <th style={{ width: 210 }}>Fee Hunter</th>
                <th className="r" style={{ width: 120 }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {s.lineItems.map((li) => {
                const f = flags.get(li.id);
                return (
                  <motion.tr key={li.id} className={f ? "flagged" : ""} initial={reduce ? false : { opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25 }}>
                    <td className="td-dim tag-mono">{li.id}</td>
                    <td>
                      <div className="td-primary">{li.description}</div>
                      <div className="td-secondary">{f?.reason ?? li.detail}</div>
                    </td>
                    <td>
                      {f ? (
                        <StatusDot variant="amber" label={CATEGORY_LABEL[f.category] ?? f.category} />
                      ) : (
                        <StatusDot label={fh.status === "pending" ? "Not reviewed yet" : fh.status === "active" ? "Reviewing" : "Pass-through"} />
                      )}
                    </td>
                    <td>{f && <Badge variant={f.category === "equipment_lease" ? "gray" : "red"}>{f.tag}</Badge>}</td>
                    <td className="td-amount r num">{money(li.amount, true)}</td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
          <div className="list-footer">
            <span>
              Showing {s.lineItems.length} of {s.totalItems} lines
              {fh.status !== "pending" && <> &nbsp; <ModeBadge live={fh.live} label={fh.note ?? undefined} /></>}
            </span>
            <strong className="num">Total: {money(total, true)}</strong>
          </div>
        </>
      )}
    </>
  );
}
