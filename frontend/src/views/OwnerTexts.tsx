import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import { money, pct } from "../lib/format";
import type { RunState } from "../lib/runState";
import { Badge, Btn, Metric } from "../components/ui";

// What the owner photographed (the fixture statement). Rows grey out as the
// Statement Reader reads them.
const PHOTO_ROWS: [string, string][] = [
  ["Interchange charges", "1,862.40"],
  ["Card brand assessments", "141.30"],
  ["Discount fee - qualified", "196.00"],
  ["Mid-qualified surcharge", "326.40"],
  ["Non-qualified surcharge", "356.40"],
  ["Authorization fee", "207.40"],
  ["PCI non-compliance fee", "39.95"],
  ["Regulatory & compliance", "29.95"],
  ["Customer Insights Suite", "24.95"],
  ["Monthly statement fee", "14.95"],
  ["Batch settlement fee", "7.75"],
  ["Terminal lease", "69.95"],
];

function StatementPhoto({ scanning, peeled }: { scanning: boolean; peeled: number }) {
  const reduce = useReducedMotion();
  return (
    <div className="stmt" role="img" aria-label="Photo of an October card-processing statement">
      <div className="bar">KEYSTONE MERCHANT SERVICES</div>
      <div className="row"><b>Mario&apos;s Trattoria</b><span>Oct 2026</span></div>
      <div className="row"><span>Total card sales</span><span>$100,000.00</span></div>
      <div className="row" style={{ marginBottom: 5 }}><span>Total fees</span><span>$3,277.40</span></div>
      {PHOTO_ROWS.map(([d, a], i) => (
        <div key={d} className={`row ${i < peeled ? "peeled" : ""}`}><span>{d}</span><span>{a}</span></div>
      ))}
      {scanning && !reduce && (
        <motion.div className="scanline" initial={{ top: "-10%" }} animate={{ top: ["-10%", "100%"] }} transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }} />
      )}
    </div>
  );
}

export function OwnerTexts({ s, onSend, onStart }: { s: RunState; onSend: (body: string) => void; onStart: () => void }) {
  const reduce = useReducedMotion();
  const [draft, setDraft] = useState("");
  const awaiting = s.status === "awaiting" && !!s.approval && !s.approvalReceived;
  const win = s.verdict?.options.find((o) => o.key === s.verdict?.winner);
  const approved = s.approvalReceived?.approved;

  const send = (body: string) => {
    const b = body.trim();
    if (!b) return;
    onSend(b);
    setDraft("");
  };

  return (
    <>
      <div className="metrics">
        <Metric label="Messages">{s.messages.length}</Metric>
        <Metric label="Owner's interface">Text only</Metric>
        <Metric label="Waiting on" tone={awaiting ? "warn" : ""}>{awaiting ? "Owner's YES" : "—"}</Metric>
        <Metric label="Deal" tone={approved ? "lime" : ""}>
          {approved ? "Approved" : s.approvalReceived ? "Declined" : "Open"}
        </Metric>
      </div>

      <div className="thread-card expanded">
        <div className="thread-header thread-head-static">
          <div className="thread-l">
            <div className="thread-vendor">Maria Russo · Mario&apos;s Trattoria</div>
            <div className="thread-ae">+1 (718) 555-0142 · {s.services.twilio === "live" ? "Twilio SMS" : "SMS simulator"}</div>
          </div>
          <div className="thread-r">
            {awaiting && <Badge variant="amber">Awaiting YES</Badge>}
            {approved === true && <Badge variant="green">Approved</Badge>}
            {approved === false && <Badge>Declined</Badge>}
            {win && s.rate && (
              <div className="thread-outcome">{pct(s.rate.effective_rate)} → {pct(win.effective_rate)} · {money(win.annual_savings)}/yr</div>
            )}
          </div>
        </div>

        <div className="thread-body" role="log" aria-live="polite" aria-label="Text message thread">
          {s.messages.length === 0 && (
            <div className="chat-empty">
              <span>Text a photo of your card-processing statement. I&apos;ll find the hidden fees and fight them.</span>
              <Btn primary icon="ti-camera" onClick={onStart}>Send October statement photo</Btn>
            </div>
          )}
          <AnimatePresence initial={false}>
            {s.messages.map((m) => (
              <motion.div
                key={m.seq}
                className={`chat-row ${m.direction === "in" ? "owner" : "agent"}`}
                initial={reduce ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.28 }}
              >
                <div className="chat-bubble">
                  <div className="chat-meta">
                    <span className="chat-who">{m.direction === "in" ? "Maria Russo" : "ShadowBuyer"}</span>
                  </div>
                  {m.media.length > 0 && <StatementPhoto scanning={s.stages.statement_reader.status === "active"} peeled={s.lineItems.length} />}
                  {m.body && (
                    <div className="chat-text">
                      {m.body}
                      {m.body.includes("lender-ready report") && s.summary && (
                        <> <a href={s.summary.report_url} target="_blank" rel="noreferrer">shadowbuyer-report.pdf</a></>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        <div className="composer">
          {awaiting && (
            <>
              <Btn primary onClick={() => send("YES")}>YES</Btn>
              <Btn className="quick" onClick={() => send("NO")}>NO</Btn>
            </>
          )}
          <form onSubmit={(e) => { e.preventDefault(); send(draft); }}>
            <label className="sr-only" htmlFor="sms" style={{ display: "none" }}>Text message</label>
            <input id="sms" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={awaiting ? "Reply YES or NO" : "Text message"} disabled={!awaiting} />
            <Btn type="submit" icon="ti-send" disabled={!awaiting || !draft.trim()}>Send</Btn>
          </form>
        </div>
      </div>
      {awaiting && <p className="note">Nothing leaves the building until the owner texts YES.</p>}
    </>
  );
}
