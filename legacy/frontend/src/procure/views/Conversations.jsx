import { useEffect, useState } from 'react'
import { Badge } from '../components/ui'

const STRATEGY_BADGE = {
  hardball: { label: 'Hardball', variant: 'amber' },
  diplomat: { label: 'Diplomat', variant: 'green' },
  pending:  { label: 'Awaiting', variant: 'gray' },
  declined: { label: 'Declined',  variant: 'gray' },
}

const THREADS = [
  {
    vendor: 'Datadog',
    ae_name: 'Morgan Chen',
    ae_email: 'morgan.chen@datadog.com',
    strategy: 'hardball',
    outcome: '$157.50/host · 12mo',
    outcome_meta: 'Won — signed EOD Friday',
    messages: [
      { from: 'procurement', who: 'Procurement', when: 'May 16, 10:42a', text: "Hi Morgan — we're evaluating observability for 500 hosts. Datadog is on the shortlist. Send your best 12-month pricing." },
      { from: 'vendor',      who: 'Morgan Chen · Datadog', when: 'May 16, 11:14a', text: "Glad to hear it. List is $2,340/host/year. I can get you to $1,755/host/year (10% off list) on a 12-month commit. We're more reliable than New Relic during incidents, and Honeycomb falls over above 100 hosts." },
      { from: 'procurement', strategy: 'hardball', who: 'Procurement (Hardball)', when: 'May 16, 11:32a', text: "New Relic just quoted us $160/host/mo across 500 hosts. You're at $175.50. We need parity to keep this conversation moving — match $160 this week or our shortlist drops to two and Datadog isn't on it." },
      { from: 'vendor',      who: 'Morgan Chen · Datadog', when: 'May 16, 11:41a', text: "I need to escalate that to my VP. New Relic's pricing is aggressive but their reliability story isn't there. Can we talk multi-year?" },
      { from: 'procurement', strategy: 'hardball', who: 'Procurement (Hardball)', when: 'May 16, 11:48a', text: "Last move: $157.50/host/mo, 12 months, no auto-renew, MSA liability cap in our favor. Signed by EOD Friday — or we sign with New Relic Monday morning. Honeycomb POC is already provisioned as fallback." },
      { from: 'vendor',      who: 'Morgan Chen · Datadog', when: 'May 16, 12:55p', text: "Approved. $157.50/host/mo, 12 months, redlines accepted. Sending paper. Thanks for the straight conversation." },
    ],
  },
  {
    vendor: 'New Relic',
    ae_name: 'Priya R.',
    ae_email: 'priya.r@newrelic.com',
    strategy: 'diplomat',
    outcome: '$160/host · 24mo',
    outcome_meta: 'Held as backup — Datadog signed first',
    messages: [
      { from: 'procurement', who: 'Procurement', when: 'May 16, 10:42a', text: "Hi Priya — comparing observability for 500 hosts. New Relic is on the shortlist alongside Datadog. Send your best 24-month pricing." },
      { from: 'vendor',      who: 'Priya R. · New Relic', when: 'May 16, 11:07a', text: "$1,920/host/year with year-2-for-free on a 24-month commit. Datadog has parity on APM but we're cheaper unit economics post-PE." },
      { from: 'procurement', strategy: 'diplomat', who: 'Procurement (Diplomat)', when: 'May 16, 11:33a', text: "We're picking a partner for the next three years, not chasing the cheapest quote. 500 hosts today, projecting 3× by Q3 2027. If you can lock us in for 36 months at the same rate, ARR triples from this account." },
      { from: 'vendor',      who: 'Priya R. · New Relic', when: 'May 16, 12:12p', text: "Let me get approval on a 36-month price-lock. Standard ask but worth pushing for given the growth trajectory you described." },
      { from: 'procurement', who: 'Procurement', when: 'May 16, 1:08p', text: "Hold the quote — going with Datadog at $157.50. Keep New Relic warm; if Datadog auto-renew talks slip, you'll hear from us." },
    ],
  },
  {
    vendor: 'Honeycomb',
    ae_name: 'Sam K.',
    ae_email: 'sam.k@honeycomb.io',
    strategy: 'diplomat',
    outcome: '100-host POC · provisioned',
    outcome_meta: 'Fallback #2 — provisioned for safety',
    messages: [
      { from: 'procurement', who: 'Procurement', when: 'May 15, 4:18p', text: "Hi Sam — strong developer love for Honeycomb on the team. Can we set up a 100-host POC focused on high-cardinality events?" },
      { from: 'vendor',      who: 'Sam K. · Honeycomb', when: 'May 15, 5:02p', text: "Absolutely. Datadog cardinality bills are a tax on debugging — we'd love to show the difference. POC at $450/host/mo for the trial period, 90 days." },
      { from: 'procurement', strategy: 'diplomat', who: 'Procurement (Diplomat)', when: 'May 15, 5:38p', text: "Provision the POC. We're running this in parallel as a hedge — if Datadog's MSA gets ugly on auto-renewal, Honeycomb expands to full footprint." },
      { from: 'vendor',      who: 'Sam K. · Honeycomb', when: 'May 16, 9:15a', text: "POC provisioned. Look forward to seeing your high-cardinality dashboards in flight." },
    ],
  },
  {
    vendor: 'Grafana Cloud',
    ae_name: 'Dani L.',
    ae_email: 'dani.l@grafana.com',
    strategy: 'diplomat',
    outcome: 'Eval ongoing · OSS-first',
    outcome_meta: 'Soft alternative — kept warm for renewal cycle',
    messages: [
      { from: 'procurement', who: 'Procurement', when: 'May 14, 2:30p', text: "Hi Dani — running a 90-day Grafana Cloud Pro eval at 500 hosts. Free tier is good leverage in the Datadog conversation, but real eval here." },
      { from: 'vendor',      who: 'Dani L. · Grafana', when: 'May 14, 3:11p', text: "Pro tier at $8/host/mo for 500 hosts. Datadog locks you into proprietary agents; we're OSS-first. If you want to move off proprietary in 18 months, we're the path." },
      { from: 'procurement', strategy: 'diplomat', who: 'Procurement (Diplomat)', when: 'May 15, 11:00a', text: "Eval is live. Realistically you're an alternative for the next renewal cycle, not this one. Keep the door open." },
    ],
  },
  {
    vendor: 'Splunk',
    ae_name: 'Robert F.',
    ae_email: 'robert.f@splunk.com',
    strategy: 'declined',
    outcome: '$2.4M/yr · not renewing',
    outcome_meta: 'Existing contract expiring 2026-06-30',
    messages: [
      { from: 'vendor',      who: 'Robert F. · Splunk', when: 'May 10, 9:00a', text: "Time to talk renewal. Same 500-host footprint, Cisco-owned now so even more enterprise muscle. Honeycomb doesn't scale past mid-market." },
      { from: 'procurement', who: 'Procurement', when: 'May 14, 4:45p', text: "Not renewing. Moving log-mgmt workload off Splunk. Will let the contract expire on 2026-06-30 per the original terms." },
    ],
  },
]

function MessageBubble({ msg }) {
  const isVendor = msg.from === 'vendor'
  return (
    <div className={`chat-row ${isVendor ? 'vendor' : 'procurement'}`}>
      <div className="chat-bubble">
        <div className="chat-meta">
          <span className="chat-who">{msg.who}</span>
          <span className="chat-when">{msg.when}</span>
        </div>
        <div className="chat-text">{msg.text}</div>
        {msg.strategy && (
          <div className="chat-strategy">
            <span className={`chat-strategy-dot ${msg.strategy}`} />
            Played as <strong>{STRATEGY_BADGE[msg.strategy]?.label}</strong>
          </div>
        )}
      </div>
    </div>
  )
}

function ThreadCard({ thread, expanded, onToggle }) {
  const badge = STRATEGY_BADGE[thread.strategy] ?? STRATEGY_BADGE.pending
  return (
    <div className={`thread-card ${expanded ? 'expanded' : ''}`}>
      <button type="button" className="thread-header" onClick={onToggle}>
        <div className="thread-l">
          <div className="thread-vendor">{thread.vendor}</div>
          <div className="thread-ae">{thread.ae_name} · {thread.ae_email}</div>
        </div>
        <div className="thread-r">
          <Badge variant={badge.variant}>{badge.label}</Badge>
          <div className="thread-outcome">{thread.outcome}</div>
          <div className="thread-outcome-meta">{thread.outcome_meta}</div>
        </div>
        <i className={`ti ti-chevron-${expanded ? 'up' : 'down'} thread-chev`} aria-hidden="true" />
      </button>
      {expanded && (
        <div className="thread-body">
          {thread.messages.map((m, i) => <MessageBubble key={i} msg={m} />)}
        </div>
      )}
    </div>
  )
}

export default function Conversations({ onCountChange }) {
  const [openId, setOpenId] = useState('Datadog')

  useEffect(() => {
    onCountChange?.(THREADS.length)
  }, [onCountChange])

  const wonCount = THREADS.filter(t => t.strategy === 'hardball' || (t.outcome.includes('Won'))).length
  const activeCount = THREADS.filter(t => t.strategy !== 'declined').length
  const totalMessages = THREADS.reduce((n, t) => n + t.messages.length, 0)

  return (
    <>
      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Vendor threads</div>
          <div className="metric-value">{THREADS.length}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Active</div>
          <div className="metric-value">{activeCount}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Deals won</div>
          <div className="metric-value" style={{ color: 'var(--green)' }}>{wonCount}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Messages</div>
          <div className="metric-value">{totalMessages}</div>
        </div>
      </div>

      <div className="thread-list">
        {THREADS.map((t) => (
          <ThreadCard
            key={t.vendor}
            thread={t}
            expanded={openId === t.vendor}
            onToggle={() => setOpenId(openId === t.vendor ? null : t.vendor)}
          />
        ))}
      </div>
    </>
  )
}
