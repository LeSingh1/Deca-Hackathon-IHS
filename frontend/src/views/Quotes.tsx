import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Badge, Empty, Metric, StatusDot } from "../components/ui";

export function Quotes({ s }: { s: RunState }) {
  const quotes = s.rate?.quotes ?? [];
  const max = Math.max(0.035, ...quotes.map((q) => q.effective_rate));
  const fair = quotes.find((q) => q.kind === "benchmark");
  return (
    <>
      <div className="metrics">
        <Metric label="Monthly card volume">{s.rate ? money(s.rate.monthly_volume) : "—"}</Metric>
        <Metric label="Transactions">{s.rate ? s.rate.transaction_count.toLocaleString("en-US") : "—"}</Metric>
        <Metric label="All-in rate today" tone="warn">{s.rate ? pct(s.rate.effective_rate) : "—"}</Metric>
        <Metric label="Fair benchmark" tone="lime">{fair ? pct(fair.effective_rate) : "—"}</Metric>
      </div>
      {quotes.length === 0 ? (
        <Empty>Waiting for the Rate Scout…</Empty>
      ) : (
        <>
          <table className="list-table">
            <thead>
              <tr>
                <th>Processor / source</th>
                <th style={{ width: 110 }}>As of</th>
                <th style={{ width: 190 }}>Effective rate</th>
                <th style={{ width: 150 }}>Vs. today</th>
                <th style={{ width: 150 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => (
                <tr key={q.key}>
                  <td>
                    <div className="td-primary">{q.label}</div>
                    <div className="td-secondary">{q.source}</div>
                  </td>
                  <td className="td-dim">{q.as_of}</td>
                  <td>
                    <span className="td-amount num">{pct(q.effective_rate)}</span>
                    <div className="rate-track"><div className={`rate-fill ${q.kind}`} style={{ width: `${(q.effective_rate / max) * 100}%` }} /></div>
                  </td>
                  <td className="td-amount num">
                    {q.kind === "current" ? "—" : q.annual_savings >= 0 ? `${money(q.annual_savings)}/yr less` : `${money(-q.annual_savings)}/yr more`}
                  </td>
                  <td>
                    {q.kind === "current" ? <StatusDot variant="amber" label="Today" /> : q.kind === "benchmark" ? <StatusDot variant="green" label="Benchmark" /> : <StatusDot label="Competitor" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="list-footer">
            <span>Showing {quotes.length} of {quotes.length} rates {quotes.some((q) => q.illustrative) && <>&nbsp; <Badge>Illustrative quotes</Badge></>}</span>
            <strong>Switching has exit costs. The Referee weighs them.</strong>
          </div>
        </>
      )}
    </>
  );
}
