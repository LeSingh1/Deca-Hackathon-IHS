import { LayoutGroup, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Badge, Empty, Metric, Num, StatusDot } from "../components/ui";

const BUCKETS = ["Processor fees", "Back in your pocket", "Tax & Rainy-Day reserve"] as const;
const SUBS = ["per month, before", "per year", "moved, month 1"] as const;
const ACTION_LABEL: Record<string, string> = { savings_sweep: "Savings sweep", rep_email: "Rep email", fee_receipt: "Fee receipt" };

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
    const t = setTimeout(() => setPhase(2), 1100);
    return () => clearTimeout(t);
  }, [s.ledger, reduce]);
  const monthly = s.ledger?.back_in_pocket_monthly ?? 0;
  const amounts = [s.hiddenTotal, phase >= 1 ? s.ledger?.back_in_pocket_annual ?? 0 : 0, phase >= 2 ? monthly : 0];
  return (
    <LayoutGroup>
      <div className="ledger ledger-row" aria-label="Savings ledger">
        {BUCKETS.map((b, i) => (
          <div key={b} style={{ display: "contents" }}>
            <Metric label={b} tone={i === 0 ? "warn" : i === 1 ? "lime" : ""} sub={SUBS[i]} className={phase === i && s.ledger ? "lit" : ""}>
              <Num value={amounts[i] ?? 0} format={(n) => money(n, i === 2)} />
              {phase === i && s.ledger && (
                <motion.div layoutId="coin" className="coin" transition={{ type: "spring", stiffness: 140, damping: 20 }}>$</motion.div>
              )}
            </Metric>
            {i < 2 && <span className="to" aria-hidden="true">→</span>}
          </div>
        ))}
      </div>
    </LayoutGroup>
  );
}

export function Savings({ s }: { s: RunState }) {
  const awaiting = !!s.draft && !s.approvalReceived;
  const declined = s.approvalReceived && !s.approvalReceived.approved;
  const receipt = s.actions.find((a) => a.action === "fee_receipt");
  const d = receipt?.detail as { ticket: number; old_fee: number; new_fee: number; old_rate: number; new_rate: number } | undefined;
  return (
    <>
      {awaiting && (
        <div className="fallback-note block">
          <i className="ti ti-shield-check" aria-hidden="true" />
          Nothing leaves the building until the owner texts YES.
        </div>
      )}
      {declined && (
        <div className="fallback-note block">
          <i className="ti ti-shield-check" aria-hidden="true" />
          Owner said no. Nothing was sent and no money moved.
        </div>
      )}

      <Ledger s={s} />

      {d && (
        <>
          <div className="section-title">Fee on a sample ticket</div>
          <div className="receipts" aria-label="Fee on a sample ticket">
            <Metric label={`Before · ${pct(d.old_rate)}`} tone="warn" sub={`on a ${money(d.ticket, true)} ticket`}>{money(d.old_fee, true)}</Metric>
            <Metric label={`After · ${pct(d.new_rate)}`} tone="lime" sub={`on a ${money(d.ticket, true)} ticket`}>{money(d.new_fee, true)}</Metric>
          </div>
        </>
      )}

      <div className="section-title">Actions after YES</div>
      {s.actions.length === 0 ? (
        <Empty>The savings sweep, fee receipt, and dry-run email run only after the approval event.</Empty>
      ) : (
        <table className="list-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>Provider</th>
              <th>Reference</th>
              <th className="r">Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {s.actions.map((a) => (
              <motion.tr key={a.ref} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
                <td className="td-primary">{ACTION_LABEL[a.action] ?? a.action}</td>
                <td className="td-dim">{a.provider}{a.sandbox ? " · sandbox" : ""}</td>
                <td className="td-dim tag-mono">{a.ref}</td>
                <td className="td-amount r num">
                  {a.amount == null ? "—" : a.action === "fee_receipt" ? `${money(a.amount, true)} less per ticket` : money(a.amount, true)}
                </td>
                <td><StatusDot variant="green" label={a.action === "rep_email" ? "Drafted, not sent" : "Done"} /></td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="save-foot">
        <a
          className={`btn ${s.summary ? "btn-primary" : ""}`}
          href={s.summary?.report_url ?? undefined}
          target="_blank"
          rel="noreferrer"
          aria-disabled={!s.summary}
          style={s.summary ? undefined : { opacity: 0.45, pointerEvents: "none" }}
          onClick={(e) => { if (!s.summary) e.preventDefault(); }}
        >
          <i className="ti ti-download" aria-hidden="true" />
          Download lender-ready PDF
        </a>
        <p className="note">Sandbox, no real money: Stripe test mode with a key, a labeled mock without one. In production the sweep rides FedNow instant payments.</p>
      </div>

      {s.draft && (
        <>
          <div className="section-title">Email to the processor rep</div>
          <div className="email-card">
            <div className="email-head">
              <span className="email-label">Outbound email to rep · drafted, not sent</span>
              <span className="email-tag"><Badge variant="amber">Dry run</Badge></span>
            </div>
            <div className="email-meta">
              <div className="email-meta-k">To</div>
              <div className="email-meta-v">{s.draft.to}</div>
            </div>
            <div className="email-subject">{s.draft.subject}</div>
            <pre className="email-body">{s.draft.body}</pre>
          </div>
        </>
      )}
    </>
  );
}
