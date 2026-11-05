import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import type { Lane } from "../lib/contract";
import { money, pct } from "../lib/format";
import { laneOffer, type RunState, type Turn } from "../lib/runState";
import { Pipeline } from "../components/Pipeline";
import { Btn } from "../components/ui";

const EASE = [0.2, 0.8, 0.2, 1] as const;

function Stat({ k, v, mono, big, done }: { k: string; v: string; mono?: boolean; big?: boolean; done?: boolean }) {
  return (
    <div className="swarm-stat">
      <div className="swarm-stat-k">{k}</div>
      <div className={`swarm-stat-v ${mono ? "mono" : ""} ${big ? "big" : ""} ${done ? "done" : ""}`}>{v}</div>
    </div>
  );
}

function NegColumn({ lane, s }: { lane: Lane; s: RunState }) {
  const reduce = useReducedMotion();
  const turns: Turn[] = s.lanes[lane];
  const body = useRef<HTMLDivElement>(null);
  const size = turns.reduce((n, t) => n + t.text.length + (t.offer ? 1 : 0), 0);
  useEffect(() => {
    if (body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [size]);
  const isHB = lane === "hardball";
  const title = isHB ? "Hardball" : "Diplomat";
  const a = s.agents[lane];
  return (
    <div className="neg-panel">
      <div className="neg-head">
        <span className={`neg-head-label ${isHB ? "amber" : "lime"}`}>{title}</span>
        <span className="neg-head-model">{isHB ? "competitor quote + switch threat" : "loyalty + growth"}{a ? ` · ${a.model.replace("claude-", "")}` : ""}</span>
      </div>
      <div className="neg-body" ref={body} aria-live="off">
        {turns.length === 0 && <div className="neg-empty">Waiting for {title.toLowerCase()} to open the round…</div>}
        <AnimatePresence initial={false}>
          {turns.map((t, i) => (
            <motion.div
              key={`${lane}-${t.round}-${t.speaker}-${i}`}
              className={`msg ${t.speaker === "rep" ? "rep" : lane}`}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: EASE }}
            >
              <div className="msg-meta">
                <span className="msg-who">{t.speaker === "rep" ? "Processor rep" : title}</span>
                <span>Round {t.round}</span>
              </div>
              <div className="msg-body">{t.text}</div>
              {t.offer && <div className="offer num">offer → {pct(t.offer.effective_rate)} · {money(t.offer.annual_savings)}/yr</div>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function Negotiation({ s, onRun }: { s: RunState; onRun: () => void }) {
  const reduce = useReducedMotion();
  const quotes = s.rate?.quotes ?? [];
  const processor = quotes.find((q) => q.kind === "current")?.label.replace(" (today)", "");
  const competing = quotes.find((q) => q.kind === "competitor")?.label.split(" - ")[0];
  const offers = (["hardball", "diplomat"] as Lane[]).map((l) => laneOffer(s.lanes[l])?.effective_rate).filter((r): r is number => r != null);
  const target = offers.length ? Math.min(...offers) : s.rate?.effective_rate ?? null;
  const st = s.stages.negotiator;
  const v = s.verdict;
  const win = v?.options.find((o) => o.key === v.winner);
  const winnerName = v ? v.winner.charAt(0).toUpperCase() + v.winner.slice(1) : "";
  const tag = st.status === "done" ? "complete" : st.status === "active" ? (st.live ? "live stream" : "mock stream") : "ready";
  return (
    <div className="neg-wrap">
      <div className="swarm-header">
        <div className="swarm-header-left">
          <span className={`swarm-dot ${st.status === "active" ? "live" : ""}`} />
          <span className="swarm-title">Adversarial negotiation</span>
          <span className="swarm-tag">{tag}</span>
        </div>
        <div className="swarm-stats">
          <Stat k="Processor" v={processor ?? "—"} />
          <Stat k="Competing" v={competing ?? "—"} />
          <Stat k="Volume / mo" v={s.rate ? money(s.rate.monthly_volume) : "—"} mono />
          <Stat k="Rate today" v={s.rate ? pct(s.rate.effective_rate) : "—"} mono />
          <Stat k="Live target" v={target != null ? pct(target) : "—"} mono big done={st.status === "done"} />
        </div>
        <Btn primary icon="ti-bolt" onClick={onRun} disabled={s.status !== "idle"}>
          {s.status === "idle" ? "Run the swarm" : st.status === "done" ? "Round complete" : st.status === "active" ? "Streaming…" : "Swarm running"}
        </Btn>
      </div>

      <Pipeline s={s} />

      <div className="neg-grid">
        <NegColumn lane="hardball" s={s} />
        <NegColumn lane="diplomat" s={s} />
      </div>

      <AnimatePresence>
        {v && (
          <motion.div
            className="verdict-card"
            initial={reduce ? false : { opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.36, ease: EASE }}
          >
            <div className="verdict-head"><span className="verdict-label">Referee verdict</span></div>
            <div className="verdict-title">{winnerName} wins</div>
            <div className="verdict-body">{v.rationale}</div>
            {win && (
              <div className="verdict-stats">
                <div><div className="verdict-stat-k">Final rate</div><div className="verdict-stat-v">{pct(win.effective_rate)}</div></div>
                <div><div className="verdict-stat-k">Saves / yr</div><div className="verdict-stat-v">{money(win.annual_savings)}</div></div>
                <div><div className="verdict-stat-k">Exit costs</div><div className="verdict-stat-v">{money(win.one_time_costs)}</div></div>
                <div><div className="verdict-stat-k">Strategy</div><div className="verdict-stat-v">{winnerName}</div></div>
              </div>
            )}
            <table className="list-table opts">
              <thead>
                <tr>
                  <th>Option</th>
                  <th className="r">Rate</th>
                  <th className="r">Saves / yr</th>
                  <th className="r">Exit costs</th>
                  <th className="r">Year-1 net</th>
                </tr>
              </thead>
              <tbody>
                {v.options.map((o) => (
                  <tr key={o.key} className={o.key === v.winner ? "win" : ""}>
                    <td>{o.label}</td>
                    <td className="r num">{pct(o.effective_rate)}</td>
                    <td className="r num">{money(o.annual_savings)}</td>
                    <td className="r num">{money(o.one_time_costs)}</td>
                    <td className={`r num ${o.net_first_year < 0 ? "neg" : ""}`}>{money(o.net_first_year)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {v.reasoning_summary && (
              <details className="reasoning">
                <summary>Referee&apos;s reasoning summary</summary>
                <p>{v.reasoning_summary}</p>
              </details>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
