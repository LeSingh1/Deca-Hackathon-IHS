import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Num } from "./Num";
import { SplitFlap } from "./SplitFlap";

export function Hero({ s }: { s: RunState }) {
  const win = s.verdict?.options.find((o) => o.key === s.verdict?.winner);
  return (
    <section className="hero" aria-label="Headline numbers">
      <div className="tile">
        <div className="k">You pay today</div>
        <div className="v">{s.rate ? <Num value={s.rate.effective_rate} format={(n) => pct(n)} /> : <span className="hint">—</span>}</div>
        <div className="s">{s.rate ? `${money(s.rate.total_fees, true)} on ${money(s.rate.monthly_volume)} of sales` : "all-in effective rate"}</div>
      </div>
      <div className="tile trap">
        <div className="k">Fees you can fight</div>
        <div className="v">
          <Num value={s.hiddenTotal} format={(n) => money(n)} />
          <span className="arrow" style={{ fontSize: "0.45em" }}>/mo</span>
        </div>
        <div className="s">markup + junk fees, every month</div>
      </div>
      <div className="tile money">
        <div className="k">Back in your pocket</div>
        <div className="v">
          <Num value={win?.annual_savings ?? 0} format={(n) => money(n)} />
          <span className="arrow" style={{ fontSize: "0.45em" }}>/yr</span>
        </div>
        <div className="s">
          {win && s.rate ? (
            <>
              <span className="num">{pct(s.rate.effective_rate)}</span> → <b className="num">{pct(win.effective_rate)}</b>
              {s.ledger ? " · month 1 moved to reserve" : ""}
            </>
          ) : (
            "after negotiation"
          )}
        </div>
      </div>
      <div className="tile trap">
        <div className="k">That cash advance</div>
        <div className="v" style={{ fontSize: "unset" }}>
          <SplitFlap
            text={s.apr ? `${(s.apr.apr * 100).toFixed(0)}% APR` : "1.35x"}
            width={7}
            tone={s.apr ? "trap" : undefined}
          />
        </div>
        <div className="s">{s.apr ? `sold as a ${s.apr.advertised}` : "advertised as a simple factor"}</div>
      </div>
    </section>
  );
}
