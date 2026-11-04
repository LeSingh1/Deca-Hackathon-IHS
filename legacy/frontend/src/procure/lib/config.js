// Maps vendor names to their icon and palette.
// Slate + Lime theme: muted tiles, single lime accent for the marquee vendor.
export const VENDOR_CONFIG = {
  'Axion Systems':  { icon: 'ti-cloud-computing', bg: 'rgba(255,255,255,0.04)', color: '#cfd4d8' },
  'NovaTech Ltd.':  { icon: 'ti-cpu',             bg: 'rgba(163,230,53,0.10)',  color: '#a3e635' },
  'CoreRoute Inc.': { icon: 'ti-router',          bg: 'rgba(255,255,255,0.04)', color: '#cfd4d8' },
  'Proxima SaaS':   { icon: 'ti-puzzle',          bg: 'rgba(255,255,255,0.04)', color: '#cfd4d8' },
  'Deltalink Co.':  { icon: 'ti-truck-delivery',  bg: 'rgba(255,255,255,0.04)', color: '#cfd4d8' },
}

export const DEFAULT_VENDOR_CONFIG = {
  icon: 'ti-building',
  bg: 'rgba(255,255,255,0.04)',
  color: '#8b9197',
}

export const STATUS_BADGE_CLASS = {
  preferred:    'badge-green',
  active:       'badge-blue',
  in_review:    'badge-amber',
  inactive:     'badge-gray',
}

export const STATUS_DOT_CLASS = {
  under_review: 'dot-amber',
  negotiating:  'dot-blue',
  approved:     'dot-green',
  active:       'dot-green',
  draft:        'dot-gray',
}

export const STATUS_LABEL = {
  under_review: 'Under review',
  negotiating:  'Negotiating',
  approved:     'Approved',
  active:       'Active',
  draft:        'Draft',
  preferred:    'Preferred',
  in_review:    'In review',
  inactive:     'Inactive',
}
