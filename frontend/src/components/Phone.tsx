import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import type { RunState } from "../lib/runState";

// What the owner photographed (the fixture statement). Rows grey out as the
// Statement Reader peels them off into the command center.
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
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <b>Mario&apos;s Trattoria</b>
        <span>Oct 2026</span>
      </div>
      <div className="row"><span>Total card sales</span><span>$100,000.00</span></div>
      <div className="row" style={{ marginBottom: 4 }}><span>Total fees</span><span>$3,277.40</span></div>
      {PHOTO_ROWS.map(([d, a], i) => (
        <div key={d} className={`row ${i < peeled ? "peeled" : ""}`}>
          <span>{d}</span>
          <span>{a}</span>
        </div>
      ))}
      {scanning && !reduce && (
        <motion.div
          className="scanline"
          initial={{ top: "-10%" }}
          animate={{ top: ["-10%", "100%"] }}
          transition={{ duration: 1.6, repeat: 3, ease: "linear" }}
        />
      )}
    </div>
  );
}

export function Phone({
  state,
  onSend,
  onStart,
}: {
  state: RunState;
  onSend: (body: string) => void;
  onStart: () => void;
}) {
  const reduce = useReducedMotion();
  const [draft, setDraft] = useState("");
  const threadRef = useRef<HTMLDivElement>(null);
  const awaiting = state.status === "awaiting" && !!state.approval && !state.approvalReceived;
  const working =
    (state.status === "running" || state.status === "starting") &&
    state.active !== "approval" &&
    !state.summary;

  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.messages.length, working, awaiting]);

  const send = (body: string) => {
    const b = body.trim();
    if (!b) return;
    onSend(b);
    setDraft("");
  };

  return (
    <div className="phone" aria-label="Owner's phone">
      <div className="screen">
        <div className="statusbar" aria-hidden="true">
          <span className="num">11:04</span>
          <span>5G ▮▮▮</span>
        </div>
        <div className="thread-head">
          <div className="avatar" aria-hidden="true">S</div>
          <b>ShadowBuyer</b>
          <small>Text-only. Works for your restaurant.</small>
        </div>

        <div className="thread" ref={threadRef} role="log" aria-live="polite" aria-label="Text message thread">
          {state.messages.length === 0 && (
            <div className="hint" style={{ textAlign: "center", marginTop: 24, padding: "0 16px" }}>
              <p>Text a photo of your card-processing statement. I&apos;ll find the hidden fees and fight them.</p>
              <button className="btn money" onClick={onStart}>Send October statement photo</button>
            </div>
          )}
          <AnimatePresence initial={false}>
            {state.messages.map((m) => (
              <motion.div
                key={m.seq}
                layout={!reduce}
                initial={reduce ? false : { opacity: 0, y: 12, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                style={{ display: "flex", flexDirection: "column", alignItems: m.direction === "in" ? "flex-end" : "flex-start", gap: 6 }}
              >
                {m.media.length > 0 && (
                  <div className="bubble media in">
                    <StatementPhoto
                      scanning={state.stages.statement_reader.status === "active"}
                      peeled={state.lineItems.length}
                    />
                  </div>
                )}
                {m.body && (
                  <div className={`bubble ${m.direction}`}>
                    {m.body}
                    {m.body.includes("lender-ready report") && state.summary && (
                      <a
                        className="meta"
                        style={{ color: "inherit", fontWeight: 700, opacity: 1 }}
                        href={state.summary.report_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        shadowbuyer-report.pdf
                      </a>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          {working && state.messages.length > 0 && (
            <div className="typing" aria-label="ShadowBuyer is working">
              {[0, 1, 2].map((i) => (
                <motion.i
                  key={i}
                  animate={reduce ? undefined : { opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.1, repeat: 40, delay: i * 0.18 }}
                />
              ))}
            </div>
          )}
        </div>

        <div className="composer">
          {awaiting && (
            <div className="quick">
              <button className="yes" onClick={() => send("YES")}>YES</button>
              <button onClick={() => send("NO")}>NO</button>
            </div>
          )}
          <form
            className="compose-row"
            onSubmit={(e) => {
              e.preventDefault();
              send(draft);
            }}
          >
            <label className="sr-only" htmlFor="sms">Text message</label>
            <input
              id="sms"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={awaiting ? "Reply YES or NO" : "Text message"}
              disabled={!awaiting}
            />
            <button type="submit" disabled={!awaiting || !draft.trim()}>Send</button>
          </form>
        </div>
      </div>
    </div>
  );
}
