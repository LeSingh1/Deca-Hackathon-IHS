import { useState, useEffect } from 'react'
import { apiFetch, fmt$, fmtDate } from '../lib/api'
import { STATUS_DOT_CLASS, STATUS_LABEL } from '../lib/config'
import { Loading, ErrorBox, StatusDot, Btn } from '../components/ui'

export default function Contracts({ vendorMap, onCountChange }) {
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/contracts?order=created_at.asc')
      .then((data) => {
        setContracts(data)
        onCountChange?.(data.length)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading contracts…" />
  if (error)   return <ErrorBox message={error} />

  const totalValue = contracts
    .filter((c) => c.value)
    .reduce((s, c) => s + parseFloat(c.value), 0)

  const active = contracts.filter((c) => c.status === 'active' && c.expiry_date)
  const earliest = active.sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date))[0]

  const soonExpiring = active.filter(
    (c) => new Date(c.expiry_date) - new Date() < 90 * 86_400_000
  ).length

  return (
    <>
      <table className="list-table">
        <thead>
          <tr>
            <th>Contract / vendor</th>
            <th>Start date</th>
            <th>Expiry</th>
            <th>Value</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {contracts.map((c) => (
            <tr key={c.id}>
              <td>
                <div className="td-primary">{c.title}</div>
                <div className="td-secondary">{c.description}</div>
              </td>
              <td className="td-dim">{fmtDate(c.start_date)}</td>
              <td className="td-dim">{fmtDate(c.expiry_date)}</td>
              <td className="td-amount">{fmt$(c.value)}</td>
              <td>
                <StatusDot
                  variant={STATUS_DOT_CLASS[c.status] ?? 'gray'}
                  label={STATUS_LABEL[c.status] ?? c.status}
                />
              </td>
              <td>
                <Btn small icon="ti-file" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="summary-grid">
        <div className="metric">
          <div className="metric-label">Total committed value</div>
          <div className="metric-value">{fmt$(totalValue)}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Earliest renewal</div>
          <div className="metric-value" style={{ fontSize: 15 }}>
            {earliest ? fmtDate(earliest.expiry_date) : '—'}
          </div>
        </div>
        <div className="metric">
          <div className="metric-label">Expiring &lt;90 days</div>
          <div className={`metric-value ${soonExpiring > 0 ? 'warn' : ''}`}>
            {soonExpiring}
          </div>
        </div>
      </div>
    </>
  )
}
