import { money } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Badge, Metric } from "../components/ui";

const ROWS: { key: string; name: string; role: string; code: string }[] = [
  { key: "claude", name: "Claude", role: "All agents: reading, classifying, negotiating, judging, drafting", code: "src/llm/models.py" },
  { key: "stripe", name: "Stripe", role: "Savings sweep, test mode only. Live keys are refused.", code: "src/executor/actions.py" },
  { key: "twilio", name: "Twilio", role: "Owner's text thread and signed webhook", code: "src/channels/twilio.py" },
];
const ALWAYS: { name: string; role: string; code: string }[] = [
  { name: "Calculators", role: "Every dollar figure, rate and APR. Unit-tested, never a model.", code: "src/finance/" },
  { name: "Memory", role: "Local JSON: owner profile, statements, decisions, winning tactics", code: "src/memory/store.py" },
];

export function ServiceHealth({ s }: { s: RunState }) {
  const modes = ROWS.map((r) => s.services[r.key]);
  const agents = Object.entries(s.agents);
  return (
    <>
      <div className="metrics">
        <Metric label="Services wired">{ROWS.length + ALWAYS.length}</Metric>
        <Metric label="Live" tone="lime">{modes.filter((m) => m === "live").length}</Metric>
        <Metric label="Fallback" tone="warn">{modes.filter((m) => m !== "live").length}</Metric>
        <Metric label="Always-on">{ALWAYS.length}</Metric>
      </div>
      <div className="sponsor-list">
        {ROWS.map((r) => (
          <div key={r.key} className="sponsor-row">
            <div className="sponsor-row-l">
              <div className="sponsor-name">{r.name}</div>
              <div className="sponsor-role">{r.role}</div>
              <div className="sponsor-code"><i className="ti ti-code" aria-hidden="true" />{r.code}</div>
            </div>
            <div className="sponsor-row-r">
              <Badge variant={s.services[r.key] === "live" ? "green" : "amber"}>{s.services[r.key] === "live" ? "Live" : "Fallback"}</Badge>
            </div>
          </div>
        ))}
        {ALWAYS.map((r) => (
          <div key={r.name} className="sponsor-row">
            <div className="sponsor-row-l">
              <div className="sponsor-name">{r.name}</div>
              <div className="sponsor-role">{r.role}</div>
              <div className="sponsor-code"><i className="ti ti-code" aria-hidden="true" />{r.code}</div>
            </div>
            <div className="sponsor-row-r"><Badge>Always-on</Badge></div>
          </div>
        ))}
      </div>
      {agents.length > 0 && (
        <>
          <div className="section-title">Agents this run</div>
          <table className="list-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Model</th>
                <th>Mode</th>
                <th className="r">Cost</th>
              </tr>
            </thead>
            <tbody>
              {agents.map(([name, a]) => (
                <tr key={name}>
                  <td className="td-primary">{name.replace(/_/g, " ")}</td>
                  <td className="td-dim tag-mono">{a.model}</td>
                  <td><Badge variant={a.live ? "green" : "amber"}>{a.live ? "Live" : "Mock"}</Badge></td>
                  <td className="td-amount r num">{a.usd ? `$${a.usd.toFixed(4)}` : money(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
