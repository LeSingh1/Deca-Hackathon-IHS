/**
 * ShadowBuyer SSE client — used by NegotiationLog to stream the live
 * adversarial negotiation from the FastAPI backend (/run/stream).
 *
 * Backend URL is VITE_SHADOWBUYER_URL (defaults to localhost:8000).
 * If the backend is unreachable we fall back to deterministic MOCK_EVENTS
 * so the demo cannot crash.
 */

const SHADOWBUYER_URL =
  (import.meta.env.VITE_SHADOWBUYER_URL || 'http://localhost:8000').replace(/\/$/, '')

export const BACKEND_URL = SHADOWBUYER_URL

export function streamSwarm(onEvent, { category = 'observability', onError, onClose } = {}) {
  const url = `${SHADOWBUYER_URL}/run/stream?category=${encodeURIComponent(category)}`
  let es
  let closed = false
  try {
    es = new EventSource(url)
  } catch (err) {
    onError?.(err)
    return () => {}
  }
  es.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data)
      onEvent(parsed)
      if (parsed?.event === 'done' && !closed) {
        closed = true
        es?.close()
        onClose?.()
      }
    } catch (err) {
      onError?.(err)
    }
  }
  es.onerror = (err) => {
    if (!closed) {
      closed = true
      es?.close()
      onError?.(err)
      onClose?.()
    }
  }
  return () => {
    if (!closed) {
      closed = true
      es?.close()
      onClose?.()
    }
  }
}

export async function fetchEmailDraft(category = 'observability') {
  try {
    const r = await fetch(`${SHADOWBUYER_URL}/api/email-draft?category=${encodeURIComponent(category)}`)
    if (!r.ok) return null
    const json = await r.json()
    return json.ok ? json.email : null
  } catch {
    return null
  }
}

// Deterministic fallback events — replayed when the backend is unreachable.
// Numbers match the locked backend output: $195 list → $157.50 final, $225K/yr.
export const MOCK_EVENTS = [
  { event: 'stage_start', stage: 'scout', label: 'Researching observability vendors' },
  { event: 'stage_done', stage: 'scout' },
  { event: 'stage_start', stage: 'quote_hunter', label: 'Pulling vendor quotes' },
  { event: 'stage_done', stage: 'quote_hunter' },
  {
    event: 'stage_start',
    stage: 'negotiator',
    label: 'Adversarial negotiation: Datadog vs New Relic',
    target_vendor: 'Datadog',
    competing_vendor: 'New Relic',
    list_price_per_host_mo: 195,
    starting_quote_per_host_mo: 175.5,
    hosts: 500,
  },
  { event: 'negotiator_turn', turn: { round: 1, role: 'hardball', headline: 'Open with competitor on the table', text: "New Relic just quoted us $160.00/host across 500 hosts. You're at $175.50. We need parity to keep this conversation moving. Match $160.00 this week and we keep talking; otherwise we shortlist drops to two and you're not on it.", cites: ['competitor:New Relic@$160.00/host', 'hosts:500'], price_target_per_host_mo: 160, mocked: true } },
  { event: 'negotiator_turn', turn: { round: 1, role: 'diplomat', headline: 'Long-term partnership frame', text: "We're not shopping on price — we're picking an observability partner for the next three years. 500 hosts today, projecting 3× by end of next year. Lock us in at $158.00/host for 36 months and your ARR triples from this one account by Q3 2027.", cites: ['hosts_today:500', 'expansion:3x_18mo'], price_target_per_host_mo: 158, deal_term_months: 36, mocked: true } },
  { event: 'negotiator_turn', turn: { round: 2, role: 'hardball', headline: 'Quarter-end + internal review', text: 'Our CFO froze net-new SaaS spend pending Q-review. The only way this gets unstuck before 2026-06-30 is if you come in under New Relic, not at parity. $158.50/host, signed by Friday, or it slides to next quarter and your AE eats the slip.', cites: ['quarter_end:2026-06-30', 'cfo_spend_freeze'], price_target_per_host_mo: 158.5, mocked: true } },
  { event: 'negotiator_turn', turn: { round: 2, role: 'diplomat', headline: 'Case study + reference customer', text: "Sweetener: we'll be a public reference customer. Joint case study, quote from our CTO, logo on your homepage, speaking slot at your conference. That's worth more than the $155.00/host delta over 36 months.", cites: ['reference_customer', 'joint_case_study'], price_target_per_host_mo: 155, deal_term_months: 36, mocked: true } },
  { event: 'negotiator_turn', turn: { round: 3, role: 'hardball', headline: 'Deadline + walk-away', text: 'Last move. $157.50/host, 12 months, no auto-renew clause, MSA redlines in our favor on liability cap. Signed by EOD Friday or we sign with New Relic Monday morning. Honeycomb POC is already provisioned as fallback #2.', cites: ['deadline:friday_eod', 'fallback_poc:honeycomb'], price_target_per_host_mo: 157.5, deal_term_months: 12, mocked: true } },
  { event: 'negotiator_turn', turn: { round: 3, role: 'diplomat', headline: 'Expansion rights for price lock', text: 'Final shape: $153.00/host, 36 months, 8% annual price-lock cap, expansion rights to APM + RUM at the same per-host rate. Everyone\'s CFO can defend this. Send paper today, we counter-sign Monday.', cites: ['price_lock:8pct_annual_cap', 'expansion_rights:apm_rum'], price_target_per_host_mo: 153, deal_term_months: 36, mocked: true } },
  { event: 'negotiator_turn', turn: { round: 4, role: 'referee', headline: 'HARDBALL opens, DIPLOMAT closes', text: "HARDBALL takes round one. The quarter-end clock plus the New Relic quote on paper is discrete, time-bounded leverage. DIPLOMAT's 36-month case-study sweetener is the right second move once price is anchored. Recommended play: open HARDBALL through Friday EOD, close with DIPLOMAT's expansion-rights wrapper.", cites: ['winner:hardball', 'final_price:$157.50/host'], price_target_per_host_mo: 157.5, mocked: true } },
  { event: 'stage_done', stage: 'negotiator' },
  { event: 'summary', payload: { ok: true, vendor: 'Datadog', competing_vendor: 'New Relic', hosts: 500, list_price_per_host_mo: 195, starting_quote_per_host_mo: 175.5, final_price_per_host_mo: 157.5, annual_savings_vs_list_usd: 225000, discount_vs_list_pct: 19.2, winning_strategy: 'hardball', contract_redline_count: 15, contract_high_severity: 7 } },
  { event: 'done' },
]

export const MOCK_EMAIL = {
  to: 'morgan.chen@datadog.com',
  from: 'procurement@shadowbuyer.ai',
  subject: 'Datadog — closing by Friday at $157.50/host',
  body: "Hi Morgan,\n\nThanks for the quote on Datadog at $175.50/host/mo across 500 hosts.\n\nWe've finalized our shortlist for observability and need to close this week. New Relic has a competing offer on the table at $160.00/host. Given the quarter close on 2026-06-30, we'd like to move forward with the following terms:\n\n  • Price: $157.50/host/month\n  • Term: 12 months\n  • Auto-renewal: 30-day notice window (not 90)\n  • Liability cap: 12 months of fees (not 3)\n  • Annual price escalation: capped at 5%\n\nOur Honeycomb POC is provisioned as backup if we can't align by Friday EOD.\n\nBest,\nProcurement, ShadowBuyer",
  strategy: 'hardball',
  cites: ['competing_offer:New Relic@$160.00', 'quarter_end:2026-06-30', 'final_price:$157.50/host'],
  dry_run: true,
}
