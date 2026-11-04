import { motion, useReducedMotion } from "motion/react";
import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { ModeTag, Panel, Skeleton } from "./Panel";
import { SplitFlap } from "./SplitFlap";

const W = 560;
const H = 220;
const PL = 52;
const PB = 28;
const PT = 12;
const PR = 12;

function PaydownChart({
  schedule,
  payback,
  termDays,
}: {
  schedule: { day: number; balance: number; paid: number }[];
  payback: number;
  termDays: number;
}) {
  const reduce = useReducedMotion();
  const x = (d: number) => PL + (d / termDays) * (W - PL - PR);
  const y = (v: number) => PT + (1 - v / payback) * (H - PT - PB);
  const line = (k: "balance" | "paid") =>
    schedule.map((p, i) => `${i ? "L" : "M"}${x(p.day).toFixed(1)},${y(p[k]).toFixed(1)}`).join(" ");
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => payback * f);
  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Balance owed falls from ${money(payback)} to zero over ${termDays} days of daily debits`}
    >
      {ticks.map((t) => (
        <g key={t}>
          <line className="axis" x1={PL} x2={W - PR} y1={y(t)} y2={y(t)} strokeWidth={0.5} strokeDasharray="2 4" />
          <text x={PL - 8} y={y(t) + 4} textAnchor="end">{`$${Math.round(t / 1000)}k`}</text>
        </g>
      ))}
      {[0, 90, 180, 270]
        .filter((d) => d <= termDays)
        .map((d) => (
          <text key={d} x={x(d)} y={H - 8} textAnchor="middle">{`day ${d}`}</text>
        ))}
      <motion.path
        d={line("paid")}
        fill="none"
        stroke="var(--muted)"
        strokeWidth={2}
        initial={reduce ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: "easeOut" }}
      />
      <motion.path
        d={line("balance")}
        fill="none"
        stroke="var(--trap)"
        strokeWidth={3}
        initial={reduce ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: "easeOut" }}
      />
      <text x={x(termDays * 0.62)} y={y(payback * 0.2)} style={{ fill: "var(--trap)", fontWeight: 700 }}>
        balance owed
      </text>
      <text x={x(termDays * 0.55)} y={y(payback * 0.86)} style={{ fontWeight: 700 }}>
        paid to funder
      </text>
    </svg>
  );
}

export function AprPanel({ s }: { s: RunState }) {
  const a = s.apr;
  const st = s.stages.contract_exposer;
  return (
    <Panel
      id="contract_exposer"
      title="The cash advance, translated"
      who="Contract Exposer · APR from the calculator"
      tag={st.status !== "pending" && <ModeTag live={st.live} label={st.note ?? undefined} />}
    >
      <div className="apr">
        <div>
          <div className="hint" style={{ marginBottom: 6 }}>
            {a ? `${a.lender}, really:` : "The offer says"}
          </div>
          <SplitFlap
            text={a ? `${(a.apr * 100).toFixed(1)}% APR` : "1.35 FACTOR"}
            width={11}
            tone={a ? "trap" : undefined}
          />
          {a ? (
            <dl className="facts">
              <dt>Advance</dt>
              <dd className="num">{money(a.advance)}</dd>
              <dt>Cash you actually get</dt>
              <dd className="num">{money(a.net_funded)}</dd>
              <dt>You pay back</dt>
              <dd className="num">{money(a.payback)}</dd>
              <dt>Cost of the money</dt>
              <dd className="num" style={{ color: "var(--trap)", fontWeight: 700 }}>
                {money(a.finance_charge)}
              </dd>
              <dt>Taken every day</dt>
              <dd className="num">{money(a.daily_remittance, true)}</dd>
              <dt>Days to repay</dt>
              <dd className="num">{a.term_days}</dd>
              <dt>Compounded yearly</dt>
              <dd className="num">{pct(a.effective_annual_rate, 0)}</dd>
            </dl>
          ) : (
            <p className="hint" style={{ marginTop: 12 }}>
              &ldquo;Get $40,000 in 24 hours. Simple 1.35 factor, no interest, no APR!&rdquo;
            </p>
          )}
        </div>
        <div>
          {a ? (
            <PaydownChart schedule={a.schedule} payback={a.payback} termDays={a.term_days} />
          ) : (
            <Skeleton rows={5} h={30} />
          )}
        </div>
      </div>
    </Panel>
  );
}
