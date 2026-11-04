import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { money } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Num } from "./Num";
import { ModeTag, Panel, Skeleton } from "./Panel";

export function StatementPanel({ s }: { s: RunState }) {
  const reduce = useReducedMotion();
  const flaggedIds = new Set(s.flagged.map((f) => f.item_id));
  const st = s.stages.statement_reader;
  const fh = s.stages.fee_hunter;
  return (
    <div className="grid2">
      <Panel id="statement_reader" title="The statement, line by line" who="Statement Reader"
        tag={st.status !== "pending" && <ModeTag live={st.live} label={st.note ?? undefined} />}>
        {s.lineItems.length === 0 ? (
          <Skeleton rows={8} />
        ) : (
          <ul className="items">
            <AnimatePresence initial={false}>
              {s.lineItems.map((li) => (
                <motion.li
                  key={li.id}
                  className={flaggedIds.has(li.id) ? "flag" : ""}
                  initial={reduce ? false : { opacity: 0, x: -48, rotate: -2 }}
                  animate={{ opacity: 1, x: 0, rotate: 0 }}
                  transition={{ type: "spring", stiffness: 260, damping: 24 }}
                >
                  <span className="id mono">{li.id}</span>
                  <span className="d">
                    <span className="desc">{li.description}</span>
                    {li.detail && <small>{li.detail}</small>}
                  </span>
                  <span className="num">{money(li.amount, true)}</span>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </Panel>

      <Panel id="fee_hunter" title="Hidden fees" who="Fee Hunter"
        tag={fh.status !== "pending" && <ModeTag live={fh.live} label={fh.note ?? undefined} />}>
        <div className="fees-total" aria-live="polite">
          <span>You can fight</span>
          <span className="v">
            <Num value={s.hiddenTotal} format={(n) => money(n, true)} />
            <span style={{ fontSize: 16, fontWeight: 600 }}> /mo</span>
          </span>
        </div>
        {s.flagged.length === 0 ? (
          <Skeleton rows={6} h={30} />
        ) : (
          <div>
            <AnimatePresence initial={false}>
              {s.flagged.map((f) => (
                <motion.div
                  key={f.item_id}
                  className="fee"
                  initial={reduce ? false : { opacity: 0, x: 40 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <motion.span
                    className={`stamp ${f.category === "equipment_lease" ? "lease" : ""}`}
                    initial={reduce ? false : { scale: 1.8, opacity: 0, rotate: -12 }}
                    animate={{ scale: 1, opacity: 1, rotate: -2.5 }}
                    transition={{ type: "spring", stiffness: 420, damping: 18, delay: reduce ? 0 : 0.12 }}
                  >
                    {f.tag}
                  </motion.span>
                  <span className="num" style={{ fontWeight: 600 }}>{money(f.amount, true)}</span>
                  <span className="reason">{f.reason}</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </Panel>
    </div>
  );
}
