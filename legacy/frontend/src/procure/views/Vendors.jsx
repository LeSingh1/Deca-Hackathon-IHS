import { useState, useEffect } from 'react'
import { apiFetch } from '../lib/api'
import { VENDOR_CONFIG, DEFAULT_VENDOR_CONFIG, STATUS_BADGE_CLASS, STATUS_LABEL } from '../lib/config'
import { Loading, ErrorBox, Badge } from '../components/ui'

function VendorCard({ vendor }) {
  const cfg = VENDOR_CONFIG[vendor.name] ?? DEFAULT_VENDOR_CONFIG
  const badgeVariant = STATUS_BADGE_CLASS[vendor.status] ?? 'gray'
  const rating = vendor.rating ? parseFloat(vendor.rating).toFixed(1) : null

  return (
    <div className="vendor-card">
      <div className="v-avatar" style={{ background: cfg.bg }}>
        <i className={`ti ${cfg.icon}`} style={{ color: cfg.color }} aria-hidden="true" />
      </div>
      <div className="v-name">{vendor.name}</div>
      <div className="v-cat">{vendor.category}</div>
      <div className="v-meta">
        <Badge variant={badgeVariant.replace('badge-', '')}>
          {STATUS_LABEL[vendor.status] ?? vendor.status}
        </Badge>
        {rating && (
          <span className="v-score">
            <span className="star">★</span>
            {rating}
          </span>
        )}
      </div>
    </div>
  )
}

export default function Vendors({ onCountChange }) {
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/vendors?order=name.asc')
      .then((data) => {
        setVendors(data)
        onCountChange?.(data.length)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading vendors…" />
  if (error)   return <ErrorBox message={error} />

  const avgRating =
    vendors.filter((v) => v.rating).length
      ? (
          vendors.filter((v) => v.rating).reduce((s, v) => s + parseFloat(v.rating), 0) /
          vendors.filter((v) => v.rating).length
        ).toFixed(1)
      : '—'

  return (
    <>
      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Total vendors</div>
          <div className="metric-value">{vendors.length}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Avg rating</div>
          <div className="metric-value">{avgRating}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Preferred</div>
          <div className="metric-value">{vendors.filter((v) => v.status === 'preferred').length}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Under review</div>
          <div className="metric-value">{vendors.filter((v) => v.status === 'in_review').length}</div>
        </div>
      </div>

      <div className="vendor-grid">
        {vendors.map((v) => (
          <VendorCard key={v.id} vendor={v} />
        ))}
      </div>
    </>
  )
}
