const API_URL = import.meta.env.VITE_BUTTERBASE_API_URL
const ANON_KEY = import.meta.env.VITE_BUTTERBASE_ANON_KEY ?? 'anon'

// --- Fixture data — observability vendors for the ShadowBuyer demo ---
// Realigned from generic procurement to match the ShadowBuyer narrative:
// 5 observability vendors (Bright Data scrape shape), Datadog AE quote
// (Actionbook capture shape), Datadog MSA (Contract Diff redlines), and a
// negotiation log driven by the Hardball vs Diplomat agents.
const FIXTURES = {
  vendors: [
    { id: 'v1', name: 'Datadog',       category: 'Observability — APM + Infra', status: 'preferred',  rating: '4.3', notes: '500 hosts quoted; Q-end pressure 2026-06-30' },
    { id: 'v2', name: 'New Relic',     category: 'Observability — APM',         status: 'active',     rating: '4.3', notes: 'PE-backed (Francisco Partners); cheaper unit economics' },
    { id: 'v3', name: 'Honeycomb',     category: 'Observability — events',      status: 'in_review',  rating: '4.5', notes: 'Strong developer love; weaker enterprise sales' },
    { id: 'v4', name: 'Grafana Cloud', category: 'Observability — metrics',     status: 'active',     rating: '4.5', notes: 'OSS halo; free tier is real negotiation leverage' },
    { id: 'v5', name: 'Splunk',        category: 'Observability — log mgmt',    status: 'inactive',   rating: '4.3', notes: 'Cisco-owned; legacy enterprise lock-in plays' },
  ],
  quotes: [
    { id: 'q1', vendor_id: 'v1', description: 'Datadog — 500 hosts, APM+Infra+RUM',     submitted_at: '2026-05-16', amount: '1170000', status: 'negotiating', dig: "More reliable than New Relic during incidents; Honeycomb falls over above 100 hosts." },
    { id: 'q2', vendor_id: 'v2', description: 'New Relic — 500 hosts, 24mo commit',     submitted_at: '2026-05-16', amount: '960000',  status: 'under_review', dig: "Datadog parity on APM. Cheaper unit economics post-PE." },
    { id: 'q3', vendor_id: 'v3', description: 'Honeycomb — events tier, 100 hosts POC', submitted_at: '2026-05-15', amount: '54000',   status: 'draft',        dig: "Datadog cardinality bills are a tax on debugging." },
    { id: 'q4', vendor_id: 'v4', description: 'Grafana Cloud — Pro, 500 hosts',         submitted_at: '2026-05-15', amount: '48000',   status: 'draft',        dig: "Datadog locks you into proprietary agents; we are OSS-first." },
    { id: 'q5', vendor_id: 'v5', description: 'Splunk Observability — 500 hosts',       submitted_at: '2026-05-14', amount: '2400000', status: 'inactive',     dig: "Honeycomb does not scale past mid-market." },
  ],
  contracts: [
    { id: 'c1', title: 'Datadog MSA — under negotiation',  description: '500 hosts; 15 redlines flagged (7 high)',  start_date: '2026-07-01', expiry_date: '2027-06-30', value: '945000', status: 'negotiating' },
    { id: 'c2', title: 'New Relic Order Form — pending',   description: 'Backup if Datadog talks slip',             start_date: '2026-07-01', expiry_date: '2028-06-30', value: '960000', status: 'draft' },
    { id: 'c3', title: 'Honeycomb POC — provisioned',      description: 'Fallback #2 provisioned at 100 hosts',     start_date: '2026-05-15', expiry_date: '2026-08-15', value: '54000',  status: 'active' },
    { id: 'c4', title: 'Grafana Cloud Pro — evaluation',   description: '90-day eval, OSS-first',                   start_date: '2026-05-01', expiry_date: '2026-07-30', value: '12000',  status: 'active' },
    { id: 'c5', title: 'Splunk renewal — declined',        description: 'Existing contract not renewing',            start_date: '2024-07-01', expiry_date: '2026-06-30', value: '2400000', status: 'expiring' },
  ],
  negotiation_logs: [
    { id: 'n1', author: 'Scout (Qwen)',        author_type: 'user',   created_at: '2026-05-16T10:42:00Z', message: 'Ranked 5 observability vendors. Datadog #1, New Relic #2 (cheapest by unit economics).' },
    { id: 'n2', author: 'Datadog · Morgan Chen', author_type: 'vendor', created_at: '2026-05-16T11:14:00Z', message: '$2,340/host/year quoted with 10% annual discount. We are more reliable than New Relic during incidents.' },
    { id: 'n3', author: 'Hardball (Qwen3-Max)', author_type: 'user',   created_at: '2026-05-16T11:32:00Z', message: 'New Relic at $1,920/host/year on the table. Match $160/host/mo this week or shortlist drops to two and you are off it.' },
    { id: 'n4', author: 'Diplomat (Z.ai GLM-5.1)', author_type: 'user', created_at: '2026-05-16T11:34:00Z', message: 'We are picking an observability partner for the next three years. 500 hosts today, projecting 3x by Q3 2027. Lock us in at $158 for 36 months.' },
    { id: 'n5', author: 'Hardball (Qwen3-Max)', author_type: 'user',   created_at: '2026-05-16T11:48:00Z', message: 'Last move: $157.50/host, 12 months, no auto-renew, MSA liability cap in our favor. Signed by EOD Friday or we sign with New Relic Monday.' },
    { id: 'n6', author: 'Referee (Qwen)',       author_type: 'user',   created_at: '2026-05-16T11:55:00Z', message: 'HARDBALL wins this round. Quarter-end clock + competing quote = discrete time-bounded leverage. Open hardball, close diplomat. Projected annual savings: $225,000.' },
    { id: 'n7', author: 'Contract Diff (Qwen + Nosana)', author_type: 'user', created_at: '2026-05-16T12:02:00Z', message: '15 deviations flagged in the Datadog MSA. 7 high severity, including a 90-day auto-renewal trap and a missing data-deletion clause.' },
  ],
}

function mockResponse(path) {
  const key = path.replace(/^\//, '').split('?')[0]
  return FIXTURES[key] ?? []
}

export async function apiFetch(path) {
  try {
    const ctrl = new AbortController()
    const t = setTimeout(() => ctrl.abort(), 1500)
    const res = await fetch(`${API_URL}${path}`, {
      headers: { 'x-api-key': ANON_KEY },
      signal: ctrl.signal,
    })
    clearTimeout(t)
    if (!res.ok) throw new Error(`API error ${res.status}`)
    return await res.json()
  } catch {
    return mockResponse(path)
  }
}

export const fmt$ = (n) =>
  n != null ? '$' + Number(n).toLocaleString() : '—'

export const fmtDate = (d) =>
  d
    ? new Date(d).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : '—'

export const fmtShortDate = (d) =>
  d
    ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : '—'
