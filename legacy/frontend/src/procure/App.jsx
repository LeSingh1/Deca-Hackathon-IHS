import { useState, useEffect, useRef } from 'react'
import { apiFetch } from './lib/api'
import Vendors       from './views/Vendors'
import Quotes        from './views/Quotes'
import NegotiationLog from './views/NegotiationLog'
import Contracts     from './views/Contracts'
import SponsorHealth from './views/SponsorHealth'
import Conversations from './views/Conversations'
import { Btn }       from './components/ui'

const VIEWS = [
  { id: 'vendors',       label: 'Vendors',         icon: 'ti-briefcase',    addLabel: 'Add vendor'   },
  { id: 'quotes',        label: 'Quotes',           icon: 'ti-file-invoice', addLabel: 'Add quote'    },
  { id: 'conversations', label: 'Conversations',    icon: 'ti-mail',         addLabel: 'New thread'   },
  { id: 'negotiation',   label: 'Negotiation log',  icon: 'ti-messages',     addLabel: 'Add note'     },
  { id: 'contracts',     label: 'Contracts',        icon: 'ti-file-check',   addLabel: 'Add contract' },
  { id: 'sponsors',      label: 'Sponsor health',   icon: 'ti-plug',         addLabel: 'Refresh'      },
]

export default function App() {
  const [activeId, setActiveId]   = useState('vendors')
  const [vendorMap, setVendorMap] = useState({})
  const [counts, setCounts]       = useState({})

  // Load vendor map once — needed by Quotes + Contracts to resolve names
  useEffect(() => {
    apiFetch('/vendors?order=name.asc')
      .then((data) => {
        const map = {}
        data.forEach((v) => { map[v.id] = v })
        setVendorMap(map)
        setCounts((c) => ({ ...c, vendors: data.length }))
      })
      .catch(() => {})
  }, [])

  const active = VIEWS.find((v) => v.id === activeId)

  function handleCountChange(viewId) {
    return (n) => setCounts((c) => ({ ...c, [viewId]: n }))
  }

  return (
    <div className="shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="logo">
          <i className="ti ti-building-store" aria-hidden="true" />
          Procure
        </div>

        <span className="nav-section">Workspace</span>

        {VIEWS.map((v) => (
          <button
            key={v.id}
            className={`nav-item ${activeId === v.id ? 'active' : ''}`}
            onClick={() => setActiveId(v.id)}
          >
            <i className={`ti ${v.icon}`} aria-hidden="true" />
            {v.label}
            {counts[v.id] != null && v.id !== 'negotiation' && (
              <span className="nav-badge">{counts[v.id]}</span>
            )}
          </button>
        ))}

        <div className="sidebar-bottom">
          <button className="nav-item">
            <i className="ti ti-chart-bar" aria-hidden="true" />
            Analytics
          </button>
          <button className="nav-item">
            <i className="ti ti-settings" aria-hidden="true" />
            Settings
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <span className="page-title">{active?.label}</span>
            {counts[activeId] != null && activeId !== 'negotiation' && (
              <span className="page-count">{counts[activeId]}</span>
            )}
          </div>
          <div className="topbar-actions">
            <Btn icon="ti-search">Search</Btn>
            <Btn icon="ti-adjustments-horizontal">Filter</Btn>
            <Btn primary icon="ti-plus">
              {active?.addLabel}
            </Btn>
          </div>
        </header>

        <main className="content">
          {activeId === 'vendors' && (
            <Vendors onCountChange={handleCountChange('vendors')} />
          )}
          {activeId === 'quotes' && (
            <Quotes vendorMap={vendorMap} onCountChange={handleCountChange('quotes')} />
          )}
          {activeId === 'negotiation' && <NegotiationLog />}
          {activeId === 'contracts' && (
            <Contracts vendorMap={vendorMap} onCountChange={handleCountChange('contracts')} />
          )}
          {activeId === 'sponsors' && (
            <SponsorHealth onCountChange={handleCountChange('sponsors')} />
          )}
          {activeId === 'conversations' && (
            <Conversations onCountChange={handleCountChange('conversations')} />
          )}
        </main>
      </div>
    </div>
  )
}
