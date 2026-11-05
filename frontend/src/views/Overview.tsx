import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import type { Stage } from "../lib/contract";
import { Pipeline } from "../components/Pipeline";
import { Badge, Btn, Metric, Num } from "../components/ui";

const AGENTS: { name: string; role: string; icon: string; stage: Stage; agent: string }[] = [
  { name: "Statement Reader", role: "Photo to line items", icon: "ti-scan", stage: "statement_reader", agent: "statement_reader" },
  { name: "Fee Hunter", role: "Finds fees she can fight", icon: "ti-search", stage: "fee_hunter", agent: "fee_hunter" },
  { name: "Rate Scout", role: "Fair price + competitor quotes", icon: "ti-scale", stage: "rate_scout", agent: "" },
  { name: "Hardball", role: "Competitor quote, switch threat", icon: "ti-swords", stage: "negotiator", agent: "hardball" },
  { name: "Diplomat", role: "Loyalty and growth", icon: "ti-heart-handshake", stage: "negotiator", agent: "diplomat" },
  { name: "Referee", role: "Best first-year dollars", icon: "ti-gavel", stage: "negotiator", agent: "referee" },
  { name: "Contract Exposer", role: "True APR + contract traps", icon: "ti-file-alert", stage: "contract_exposer", agent: "contract_exposer" },
  { name: "Action Drafter", role: "Rep email + owner text", icon: "ti-pencil", stage: "action_drafter", agent: "action_drafter" },
  { name: "Executor", role: "Acts only after YES", icon: "ti-cash", stage: "executor", agent: "" },
];

const FIXED: Record<string, string> = { "Rate Scout": "deterministic", Executor: "sandbox" };

export function Overview({ s, onStart }: { s: RunState; onStart: () => void }) {
  const idle = s.status === "idle";
  const win = s.verdict?.options.find((o) => o.key === s.verdict?.winner);
  return (
    <>
      {idle ? (
        <>
          <section className="lede">
            <div>
              <h1>Card fees can cost a restaurant as much as it keeps in profit.</h1>
              <p>
                ShadowBuyer is a swarm of agents that works over text. The owner sends a photo of the statement. The agents find the
                fees, translate the cash advance into a real APR, negotiate with the processor, and act only after the owner replies YES.
              </p>
            </div>
            <Btn primary icon="ti-bolt" onClick={onStart}>Run demo: Mario&apos;s Trattoria</Btn>
          </section>
          <div className="metrics three">
            <Metric label="Of every card sale goes to fees">2-3%</Metric>
            <Metric label="Typical full-service margin">3-4%</Metric>
            <Metric label="APR hidden in many cash advances" tone="warn">60-150%</Metric>
          </div>
        </>
      ) : (
        <div className="metrics">
          <Metric label="You pay today" sub={s.rate ? `${money(s.rate.total_fees, true)} on ${money(s.rate.monthly_volume)} of sales` : "all-in effective rate"}>
            {s.rate ? <Num value={s.rate.effective_rate} format={(n) => pct(n)} /> : "—"}
          </Metric>
          <Metric label="Fees you can fight" tone="warn" sub="markup + junk fees, every month">
            <Num value={s.hiddenTotal} format={(n) => `${money(n)}/mo`} />
          </Metric>
          <Metric label="Back in your pocket" tone="lime" sub={win && s.rate ? `${pct(s.rate.effective_rate)} → ${pct(win.effective_rate)}` : "after negotiation"}>
            <Num value={win?.annual_savings ?? 0} format={(n) => `${money(n)}/yr`} />
          </Metric>
          <Metric label="That cash advance" tone={s.apr ? "red" : ""} sub={s.apr ? `sold as a ${s.apr.advertised}` : "advertised as a simple factor"}>
            {s.apr ? `${(s.apr.apr * 100).toFixed(0)}% APR` : "1.35x"}
          </Metric>
        </div>
      )}

      <Pipeline s={s} className="overview-pipe" />

      <div className="vendor-grid">
        {AGENTS.map((a) => {
          const status = s.stages[a.stage].status;
          const label = status === "active" ? "Working" : status === "done" ? "Done" : "Idle";
          const model = s.agents[a.agent]?.model ?? s.stages[a.stage].model?.split(" / ").at(-1);
          return (
            <div key={a.name} className={`vendor-card agent ${status}`}>
              <div className="v-avatar agent"><i className={`ti ${a.icon}`} aria-hidden="true" /></div>
              <div className="v-name">{a.name}</div>
              <div className="v-cat">{a.role}</div>
              <div className="v-meta">
                <Badge variant={status === "done" ? "green" : status === "active" ? "amber" : "gray"}>{label}</Badge>
                <span className="v-model">{FIXED[a.name] ?? model?.replace("claude-", "")}</span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="note">Fictional restaurant, processor and lender. Benchmarks are labeled illustrative. All figures come from tested calculators.</p>
    </>
  );
}
