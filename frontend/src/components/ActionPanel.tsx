import { LayoutGroup, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Num } from "./Num";
import { ModeTag, Panel, Skeleton } from "./Panel";

const BUCKETS = ["Processor fees", "Back in your pocket", "Tax & Rainy-Day reserve"] as const;

function Ledger({ s }: { s: RunState }) {
  const reduce = useReducedMotion();
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (!s.ledger) {
      setPhase(0);
      return;
    }
    if (reduce) {
      setPhase(2);
      return;
    }
    setPhase(1);
    const t = setTimeout(() => setPhase(2), 900);
    return () => clearTimeout(t);
  }, [s.ledger, reduce]);
  const monthly = s.ledger?.back_in_pocket_monthly ?? s.summary?.monthly_savings ?? 0;
  const amounts = [
    s.hiddenTotal,
    phase >= 1 ? s.ledger?.back_in_pocket_annual ?? 0 : 0,
    phase >= 2 ? monthly : 0,
  ];
  return (
    <LayoutGroup>
      <div className="ledger" aria-label="Savings ledger">
        {BUCKETS.map((b, i) => (
          <div key={b} style={{ display: "contents" }}>
            <div className={`bucket ${i === 0 ? "trap" : i === 1 ? "money" : ""}`}>
              <b>{b}</b>
              <Num value={amounts[i] ?? 0} format={(n) => money(n, i === 2)} />
              <span className="hint" style={{ fontSize: 11, display: "block" }}>
                {i === 0 ? "per month, before" : i === 1 ? "per year" : "moved, month 1"}
              </span>
              {phase === i && s.ledger && (
                <motion.div layoutId="coin" className="coin" transition={{ type: "spring", stiffness: 160, damping: 20 }}>$</motion.div>
              )}
            </div>
            {i < 2 && <span className="to" aria-hidden="true">→</span>}
          </div>
        ))}
      </div>
    </LayoutGroup>
  );
}

export function ActionPanel({ s }: { s: RunState }) {
  const awaiting = !!s.approval && !s.approvalReceived;
  const receipt = s.actions.find((a) => a.action === "fee_receipt");
  const d = receipt?.detail as { ticket: number; old_fee: number; new_fee: number; old_rate: number; new_rate: number } | undefined;
  const ex = s.stages.executor;
  return (
    <Panel id="action_drafter" title="Your YES, and the money moves" who="Action Drafter · Executor"
      tag={ex.status !== "pending" && <span className="tag money">sandbox</span>}>
      <div className="actions">
        <div>
          <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>
            Email to the processor rep <ModeTag label="dry run" />
          </h3>
          {s.draft ? (
            <div className="email">
              <div className="subj">{s.draft.subject}</div>
              <div className="hint" style={{ fontSize: 12, marginBottom: 6 }}>to {s.draft.to}</div>
              {s.draft.body}
            </div>
          ) : (
            <Skeleton rows={5} />
          )}
          {awaiting && (
            <div className="waiting" role="status">
              Nothing leaves the building until the owner texts YES.
            </div>
          )}
          {s.approvalReceived && !s.approvalReceived.approved && (
            <div className="waiting" role="status">Owner said no. Nothing was sent and no money moved.</div>
          )}
        </div>

        <div>
          <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>After YES</h3>
          {s.actions.length === 0 ? (
            <p className="hint">The savings sweep, fee receipt, and dry-run email run only after the approval event.</p>
          ) : (
            <div>
              {s.actions.map((a) => (
                <motion.div key={a.ref} className="act" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
                  <b>{a.action === "savings_sweep" ? "Savings sweep" : a.action === "rep_email" ? "Rep email" : "Fee receipt"}</b>
                  <span className="num">
                    {a.amount == null ? "—" : a.action === "fee_receipt" ? `${money(a.amount, true)} less per ticket` : money(a.amount, true)}
                  </span>
                  <small>{a.provider}{a.sandbox ? " · sandbox" : ""} · {a.ref}</small>
                </motion.div>
              ))}
            </div>
          )}
          {d && (
            <div className="receipts" aria-label="Fee on a sample ticket">
              <div className="receipt old">
                <b>Before · {pct(d.old_rate)}</b>
                <div className="fee-line"><span>Ticket</span><span>{money(d.ticket, true)}</span></div>
                <div className="fee-line"><span>Card fee</span><span>{money(d.old_fee, true)}</span></div>
              </div>
              <div className="receipt new">
                <b>After · {pct(d.new_rate)}</b>
                <div className="fee-line"><span>Ticket</span><span>{money(d.ticket, true)}</span></div>
                <div className="fee-line"><span>Card fee</span><span>{money(d.new_fee, true)}</span></div>
              </div>
            </div>
          )}
        </div>
      </div>

      <Ledger s={s} />
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 16, flexWrap: "wrap" }}>
        <a
          className={`btn ${s.summary ? "money" : "ghost"}`}
          href={s.summary?.report_url ?? undefined}
          target="_blank"
          rel="noreferrer"
          aria-disabled={!s.summary}
          onClick={(e) => { if (!s.summary) e.preventDefault(); }}
        >
          Download lender-ready PDF
        </a>
        <span className="hint">Sandbox, no real money: Stripe test mode with a key, a labeled mock without one. In production the sweep rides FedNow instant payments.</span>
      </div>
    </Panel>
  );
}
