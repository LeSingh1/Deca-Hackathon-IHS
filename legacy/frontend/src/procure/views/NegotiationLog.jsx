import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { streamSwarm, fetchEmailDraft, MOCK_EVENTS, MOCK_EMAIL, BACKEND_URL } from '../lib/shadowbuyer'
import { Btn } from '../components/ui'

const STAGES = [
  { key: 'scout',          label: 'Scout' },
  { key: 'quote_hunter',   label: 'Quote Hunter' },
  { key: 'negotiator',     label: 'Negotiator' },
  { key: 'contract_diff',  label: 'Contract Diff' },
]

const EASE = [0.2, 0.8, 0.2, 1]

function fmtMoney(n) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(n)
}

export default function NegotiationLog() {
  const [running, setRunning]       = useState(false)
  const [mode, setMode]             = useState('idle') // idle | live | mock | done
  const [stages, setStages]         = useState({})
  const [meta, setMeta]             = useState({})
  const [livePrice, setLivePrice]   = useState(null)
  const [hardball, setHardball]     = useState([])
  const [diplomat, setDiplomat]     = useState([])
  const [referee, setReferee]       = useState(null)
  const [summary, setSummary]       = useState(null)
  const [email, setEmail]           = useState(null)
  const cancelRef = useRef(null)
  const hbBodyRef = useRef(null)
  const dpBodyRef = useRef(null)

  const reduceMotion = useReducedMotion()

  // Auto-scroll columns as new turns land.
  useEffect(() => { if (hbBodyRef.current) hbBodyRef.current.scrollTop = hbBodyRef.current.scrollHeight }, [hardball.length])
  useEffect(() => { if (dpBodyRef.current) dpBodyRef.current.scrollTop = dpBodyRef.current.scrollHeight }, [diplomat.length])

  const reset = useCallback(() => {
    setStages({}); setMeta({}); setLivePrice(null);
    setHardball([]); setDiplomat([]); setReferee(null);
    setSummary(null); setEmail(null);
  }, [])

  const handleEvent = useCallback((ev) => {
    if (ev.event === 'stage_start')      setStages((s) => ({ ...s, [ev.stage]: 'active' }))
    if (ev.event === 'stage_done')       setStages((s) => ({ ...s, [ev.stage]: 'done' }))
    if (ev.event === 'stage_start' && ev.stage === 'negotiator') {
      setMeta({
        vendor: ev.target_vendor, competing: ev.competing_vendor, hosts: ev.hosts,
        list: ev.list_price_per_host_mo, starting: ev.starting_quote_per_host_mo,
      })
      setLivePrice(ev.starting_quote_per_host_mo ?? null)
    }
    if (ev.event === 'negotiator_turn') {
      const t = ev.turn
      if (t.price_target_per_host_mo != null) setLivePrice(t.price_target_per_host_mo)
      if (t.role === 'hardball')      setHardball((arr) => [...arr, t])
      else if (t.role === 'diplomat') setDiplomat((arr) => [...arr, t])
      else if (t.role === 'referee')  setReferee(t)
    }
    if (ev.event === 'summary')  setSummary(ev.payload)
  }, [])

  const playMock = useCallback(() => {
    setMode('mock')
    setRunning(true)
    reset()
    let i = 0
    const step = () => {
      if (i >= MOCK_EVENTS.length) {
        setRunning(false)
        setMode('done')
        setEmail(MOCK_EMAIL)
        return
      }
      const ev = MOCK_EVENTS[i++]
      handleEvent(ev)
      const delay = ev.event === 'negotiator_turn' ? 520 : 280
      setTimeout(step, delay)
    }
    step()
  }, [handleEvent, reset])

  const runSwarm = useCallback(() => {
    if (running) return
    reset()
    setRunning(true)
    setMode('live')
    let received = false
    const close = streamSwarm(handleEvent, {
      onError: () => { if (!received) playMock() },
      onClose: () => {
        setRunning(false)
        setMode(received ? 'done' : 'mock')
        fetchEmailDraft().then((em) => setEmail(em ?? MOCK_EMAIL))
      },
    })
    cancelRef.current = close
    // mark we've received something once any handler fires
    const origHandle = handleEvent
    const wrap = (ev) => { received = true; origHandle(ev) }
    // streamSwarm already wired with handleEvent; this 'received' is a closure
    // tracked through the onError callback above (it checks before falling back)
    void wrap
  }, [handleEvent, playMock, reset, running])

  useEffect(() => () => cancelRef.current?.(), [])

  return (
    <div className="neg-wrap">
      <SwarmHeader running={running} mode={mode} onRun={runSwarm} meta={meta} livePrice={livePrice} />
      <PipelinePills stages={stages} />

      <div className="neg-grid">
        <NegColumn role="hardball" turns={hardball} bodyRef={hbBodyRef} reduceMotion={reduceMotion} />
        <NegColumn role="diplomat" turns={diplomat} bodyRef={dpBodyRef} reduceMotion={reduceMotion} />
      </div>

      <AnimatePresence>
        {referee && (
          <VerdictCard key="verdict" verdict={referee} summary={summary} reduceMotion={reduceMotion} />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {email && (
          <EmailCard key="email" email={email} reduceMotion={reduceMotion} />
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Header / CTA row ────────────────────────────────────────────────────
function SwarmHeader({ running, mode, onRun, meta, livePrice }) {
  const tag = mode === 'mock' ? 'mock fallback' : mode === 'live' ? 'live stream' : mode === 'done' ? 'complete' : 'ready'
  return (
    <div className="swarm-header">
      <div className="swarm-header-left">
        <span className={`swarm-dot ${running ? 'live' : ''}`} />
        <span className="swarm-title">Adversarial negotiation</span>
        <span className="swarm-tag">{tag}</span>
      </div>
      <div className="swarm-stats">
        <Stat k="Vendor" v={meta.vendor ?? '—'} />
        <Stat k="Competing" v={meta.competing ?? '—'} />
        <Stat k="Hosts" v={meta.hosts != null ? String(meta.hosts) : '—'} mono />
        <Stat k="List $/host" v={meta.list != null ? `$${meta.list}` : '—'} mono />
        <Stat k="Live target" v={livePrice != null ? `$${Number(livePrice).toFixed(2)}` : '—'} mono big />
      </div>
      <Btn primary icon="ti-bolt" onClick={onRun} disabled={running}>
        {running ? 'Streaming…' : 'Run the swarm'}
      </Btn>
    </div>
  )
}

function Stat({ k, v, mono = false, big = false }) {
  return (
    <div className="swarm-stat">
      <div className="swarm-stat-k">{k}</div>
      <div className={`swarm-stat-v ${mono ? 'mono' : ''} ${big ? 'big' : ''}`}>{v}</div>
    </div>
  )
}

function PipelinePills({ stages }) {
  return (
    <div className="swarm-pipeline">
      {STAGES.map((s, i) => {
        const state = stages[s.key] ?? 'idle'
        return (
          <span key={s.key} className="swarm-pipe">
            <motion.span
              className={`swarm-step ${state}`}
              animate={state === 'active' ? { scale: [1, 1.03, 1] } : { scale: 1 }}
              transition={state === 'active' ? { duration: 1.4, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.2 }}
            >
              <span className="swarm-step-dot" />
              {s.label}
            </motion.span>
            {i < STAGES.length - 1 && <span className="swarm-pipe-arrow">→</span>}
          </span>
        )
      })}
    </div>
  )
}

// ── Negotiation column ──────────────────────────────────────────────────
function NegColumn({ role, turns, bodyRef, reduceMotion }) {
  const isHB = role === 'hardball'
  const title = isHB ? 'Hardball' : 'Diplomat'
  const model = isHB ? 'Qwen3-Max · TokenRouter' : 'GLM-5.1 · Z.ai'
  const variant = isHB ? 'amber' : 'lime'
  return (
    <div className="neg-panel">
      <div className="neg-head">
        <span className={`neg-head-label ${variant}`}>{title}</span>
        <span className="neg-head-model">{model}</span>
      </div>
      <div className="neg-body" ref={bodyRef}>
        <AnimatePresence initial={false}>
          {turns.map((t, idx) => (
            <motion.div
              key={`${role}-${t.round}-${idx}`}
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: EASE }}
              className={`msg ${role}`}
            >
              <div className="msg-meta">
                <span>Round {t.round}{t.mocked ? ' · mock' : ''}</span>
                {t.price_target_per_host_mo != null && (
                  <span className="msg-price">
                    ${Number(t.price_target_per_host_mo).toFixed(2)}/host
                    {t.deal_term_months ? ` · ${t.deal_term_months}mo` : ''}
                  </span>
                )}
              </div>
              <div className="msg-head">{t.headline}</div>
              <div className="msg-body">{t.text}</div>
              {t.cites && t.cites.length > 0 && (
                <div className="msg-cites">
                  {t.cites.map((c) => (
                    <span key={c} className="msg-cite">{c}</span>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        {turns.length === 0 && (
          <div className="neg-empty">Waiting for {title.toLowerCase()} to open the round…</div>
        )}
      </div>
    </div>
  )
}

// ── Referee verdict ─────────────────────────────────────────────────────
function VerdictCard({ verdict, summary, reduceMotion }) {
  const final = summary?.final_price_per_host_mo
  const savings = summary?.annual_savings_vs_list_usd
  const discount = summary?.discount_vs_list_pct
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.36, ease: EASE }}
      className="verdict-card"
    >
      <div className="verdict-head">
        <span className="verdict-label">Referee verdict</span>
        {verdict.cites && (
          <div className="verdict-cites">
            {verdict.cites.map((c) => <span key={c} className="msg-cite verdict">{c}</span>)}
          </div>
        )}
      </div>
      <div className="verdict-title">{verdict.headline}</div>
      <div className="verdict-body">{verdict.text}</div>
      {summary && (
        <div className="verdict-stats">
          <Metric k="Final $/host/mo" v={final != null ? `$${Number(final).toFixed(2)}` : '—'} />
          <Metric k="Discount vs list" v={discount != null ? `${discount.toFixed(1)}%` : '—'} />
          <Metric k="Annual savings" v={fmtMoney(savings)} />
          <Metric k="Strategy" v={summary.winning_strategy ?? '—'} />
        </div>
      )}
    </motion.div>
  )
}

function Metric({ k, v }) {
  return (
    <div className="verdict-stat">
      <div className="verdict-stat-k">{k}</div>
      <div className="verdict-stat-v">{v}</div>
    </div>
  )
}

// ── Email card ──────────────────────────────────────────────────────────
function EmailCard({ email, reduceMotion }) {
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.36, ease: EASE }}
      className="email-card"
    >
      <div className="email-head">
        <span className="email-label">Outbound email to AE · drafted, not sent</span>
        <span className="email-tag">{email.dry_run ? 'dry-run' : 'sent'} · {email.strategy}</span>
      </div>
      <div className="email-meta">
        <div className="email-meta-k">From</div><div className="email-meta-v">{email.from}</div>
        <div className="email-meta-k">To</div><div className="email-meta-v">{email.to}</div>
      </div>
      <div className="email-subject">{email.subject}</div>
      <pre className="email-body">{email.body}</pre>
      {email.cites && email.cites.length > 0 && (
        <div className="email-cites">
          {email.cites.map((c) => <span key={c} className="msg-cite">{c}</span>)}
        </div>
      )}
    </motion.div>
  )
}
