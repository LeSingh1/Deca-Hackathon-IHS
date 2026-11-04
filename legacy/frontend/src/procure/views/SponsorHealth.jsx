import { useState, useEffect } from 'react'
import { Loading, ErrorBox, Badge } from '../components/ui'
import { BACKEND_URL } from '../lib/shadowbuyer'

const STATUS_VARIANT = { live: 'green', mock: 'amber', 'n/a': 'gray' }
const STATUS_LABEL = { live: 'Live', mock: 'Fallback', 'n/a': 'Always-on' }

function SponsorRow({ sponsor }) {
  const variant = STATUS_VARIANT[sponsor.env_status] ?? 'gray'
  const label = STATUS_LABEL[sponsor.env_status] ?? sponsor.env_status
  return (
    <div className="sponsor-row">
      <div className="sponsor-row-l">
        <div className="sponsor-name">{sponsor.name}</div>
        <div className="sponsor-role">{sponsor.role}</div>
        <div className="sponsor-code" title={sponsor.code_ref}>
          <i className="ti ti-code" aria-hidden="true" />
          {sponsor.code_ref}
        </div>
      </div>
      <div className="sponsor-row-r">
        <Badge variant={variant}>{label}</Badge>
        <div className="sponsor-owner">{sponsor.owner}</div>
      </div>
    </div>
  )
}

export default function SponsorHealth({ onCountChange }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch(`${BACKEND_URL}/api/sponsor-health`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((j) => {
        if (cancelled) return
        setData(j)
        onCountChange?.(j.total ?? 0)
      })
      .catch((e) => {
        if (cancelled) return
        setError(e.message)
        setData({
          total: 11,
          counts: { live: 0, mock: 6, 'n/a': 5 },
          sponsors: FALLBACK_SPONSORS,
          fallback: true,
        })
        onCountChange?.(11)
      })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  if (loading) return <Loading text="Checking sponsor health…" />
  if (!data) return <ErrorBox message={error || 'Unavailable'} />

  const { counts = {}, sponsors = [] } = data

  return (
    <>
      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Sponsors wired</div>
          <div className="metric-value">{data.total ?? sponsors.length}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Live</div>
          <div className="metric-value" style={{ color: 'var(--green)' }}>{counts.live ?? 0}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Fallback</div>
          <div className="metric-value" style={{ color: 'var(--amber)' }}>{counts.mock ?? 0}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Always-on</div>
          <div className="metric-value">{counts['n/a'] ?? 0}</div>
        </div>
      </div>

      {data.fallback && (
        <div className="fallback-note">
          <i className="ti ti-shield-check" aria-hidden="true" />
          Backend unreachable — showing verified static snapshot for demo reliability.
        </div>
      )}

      <div className="sponsor-list">
        {sponsors.map((s) => <SponsorRow key={s.name} sponsor={s} />)}
      </div>
    </>
  )
}

const FALLBACK_SPONSORS = [
  { name: 'AgentField', role: 'Orchestrates the 6 agents via @agent decorators', owner: 'Person A', code_ref: 'every src/agents/*.py', env_status: 'n/a' },
  { name: 'TokenRouter', role: 'Routes ALL LLM calls (Qwen, Z.ai, OpenAI)', owner: 'Person A', code_ref: 'src/clients/tokenrouter.py', env_status: 'mock' },
  { name: 'Qwen Cloud', role: 'Scout, Hardball (Qwen3-Max), Referee', owner: 'Person A', code_ref: 'src/agents/scout.py, negotiator.py', env_status: 'mock' },
  { name: 'Z.ai', role: 'Diplomat (GLM-5.1)', owner: 'Person A', code_ref: 'src/agents/negotiator.py:_dp_round', env_status: 'mock' },
  { name: 'Evermind', role: 'Vendor profiles, AE quotes, trash-talk, decisions', owner: 'Person B', code_ref: 'src/memory/evermind.py', env_status: 'mock' },
  { name: 'Nosana', role: 'Clause similarity embeddings', owner: 'Person B', code_ref: 'src/agents/contract_diff.py:_nosana_embed', env_status: 'mock' },
  { name: 'Bright Data', role: 'Vendor research (G2, funding, logos)', owner: 'Person B', code_ref: 'fixtures/observability_vendors_g2.json', env_status: 'mock' },
  { name: 'Actionbook', role: 'Quote Hunter form filling', owner: 'Person B', code_ref: 'src/agents/quote_hunter.py', env_status: 'n/a' },
  { name: 'Qoder', role: 'Coding workflow / build notes', owner: 'Team', code_ref: 'README.md', env_status: 'n/a' },
  { name: 'Zeabur', role: 'Live deployment', owner: 'Person A', code_ref: 'zeabur.toml + Dockerfile', env_status: 'n/a' },
  { name: 'Butterbase', role: 'Dashboard JSON endpoints', owner: 'Person C', code_ref: '/api/demo-state, /api/email-draft, /api/sponsor-health', env_status: 'n/a' },
]
