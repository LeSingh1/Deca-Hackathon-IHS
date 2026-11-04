import { useState, useEffect } from 'react'
import { apiFetch, fmt$, fmtDate } from '../lib/api'
import { STATUS_DOT_CLASS, STATUS_LABEL } from '../lib/config'
import { Loading, ErrorBox, StatusDot, Btn } from '../components/ui'

export default function Quotes({ vendorMap, onCountChange }) {
  const [quotes, setQuotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/quotes?order=submitted_at.desc')
      .then((data) => {
        setQuotes(data)
        onCountChange?.(data.length)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading quotes…" />
  if (error)   return <ErrorBox message={error} />

  const total = quotes.reduce((s, q) => s + parseFloat(q.amount ?? 0), 0)

  return (
    <>
      <table className="list-table">
        <thead>
          <tr>
            <th>Vendor / description</th>
            <th>Submitted</th>
            <th>Amount</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {quotes.map((q) => (
            <tr key={q.id}>
              <td>
                <div className="td-primary">{vendorMap[q.vendor_id]?.name ?? '—'}</div>
                <div className="td-secondary">{q.description}</div>
              </td>
              <td className="td-dim">{fmtDate(q.submitted_at)}</td>
              <td className="td-amount">{fmt$(q.amount)}</td>
              <td>
                <StatusDot
                  variant={STATUS_DOT_CLASS[q.status] ?? 'gray'}
                  label={STATUS_LABEL[q.status] ?? q.status}
                />
              </td>
              <td>
                <Btn small>View</Btn>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="list-footer">
        <span>Showing {quotes.length} of {quotes.length} quotes</span>
        <strong>Total: {fmt$(total)}</strong>
      </div>
    </>
  )
}
