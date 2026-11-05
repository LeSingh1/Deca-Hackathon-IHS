import { motion, useReducedMotion } from "motion/react";
import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Empty, Metric, ModeBadge } from "../components/ui";

const W = 1100;
const H = 380;
const PL = 52;
const PB = 28;
const PT = 12;
const PR = 12;

function PaydownChart({ schedule, payback, termDays }: { schedule: { day: number; balance: number; paid: number }[]; payback: number; termDays: number }) {
  const reduce = useReducedMotion();
  const x = (d: number) => PL + (d / termDays) * (W - PL - PR);
  const y = (v: number) => PT + (1 - v / payback) * (H - PT - PB);
  const line = (k: "balance" | "paid") => schedule.map((p, i) => `${i ? "L" : "M"}${x(p.day).toFixed(1)},${y(p[k]).toFixed(1)}`).join(" ");
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => payback * f);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Balance owed falls from ${money(payback)} to zero over ${termDays} days of daily debits`}>
      {ticks.map((t) => (
        <g key={t}>
          <line className="axis" x1={PL} x2={W - PR} y1={y(t)} y2={y(t)} strokeWidth={0.5} strokeDasharray="2 4" />
          <text x={PL - 8} y={y(t) + 4} textAnchor="end">{`$${Math.round(t / 1000)}k`}</text>
        </g>
      ))}
      {[0, 90, 180, 270].filter((d) => d <= termDays).map((d) => (
        <text key={d} x={x(d)} y={H - 8} textAnchor="middle">{`day ${d}`}</text>
      ))}
      <motion.path d={line("paid")} fill="none" stroke="#8b9197" strokeWidth={2} initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2, ease: "easeOut" }} />
      <motion.path d={line("balance")} fill="none" stroke="#f0b15a" strokeWidth={3} initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2, ease: "easeOut" }} />
      <text x={x(termDays * 0.62)} y={y(payback * 0.2)} style={{ fill: "#f0b15a", fontWeight: 600 }}>balance owed</text>
      <text x={x(termDays * 0.55)} y={y(payback * 0.86)} style={{ fontWeight: 600 }}>paid to funder</text>
    </svg>
  );
}

export function CashAdvance({ s }: { s: RunState }) {
  const a = s.apr;
  const st = s.stages.contract_exposer;
  return (
    <>
      <div className="metrics">
        <Metric label="Advance">{a ? money(a.advance) : "—"}</Metric>
        <Metric label="Cash you actually get">{a ? money(a.net_funded) : "—"}</Metric>
        <Metric label="You pay back">{a ? money(a.payback) : "—"}</Metric>
        <Metric label="Cost of the money" tone={a ? "red" : ""}>{a ? money(a.finance_charge) : "—"}</Metric>
      </div>
      {!a ? (
        <Empty>Waiting for the Contract Exposer…</Empty>
      ) : (
        <>
          <div className="apr-card">
            <div>
              <div className="apr-label">{a.lender}, really</div>
              <motion.div className="apr-big num" initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}>
                {(a.apr * 100).toFixed(1)}% APR
              </motion.div>
              <div className="apr-pitch">
                Sold as &ldquo;Get $40,000 in 24 hours. Simple {a.advertised}, no interest, no APR!&rdquo;
              </div>
              <div style={{ marginTop: 12 }}><ModeBadge live={st.live} label={st.live ? "Live" : "APR from the calculator"} /></div>
            </div>
            <PaydownChart schedule={a.schedule} payback={a.payback} termDays={a.term_days} />
          </div>
          <div className="summary-grid">
            <Metric label="Taken every day">{money(a.daily_remittance, true)}</Metric>
            <Metric label="Days to repay">{a.term_days}</Metric>
            <Metric label="Compounded yearly" tone="warn">{pct(a.effective_annual_rate, 0)}</Metric>
          </div>
        </>
      )}
    </>
  );
}
