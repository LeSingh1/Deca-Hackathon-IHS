export function Loading({ text = 'Loading…' }) {
  return (
    <div className="loading">
      <div className="spinner" />
      {text}
    </div>
  )
}

export function ErrorBox({ message }) {
  return <div className="error-box">⚠ {message}</div>
}

export function Badge({ variant = 'gray', children }) {
  return <span className={`badge badge-${variant}`}>{children}</span>
}

export function StatusDot({ variant = 'gray', label }) {
  return (
    <span className="status-cell">
      <span className={`dot dot-${variant}`} />
      <span className="td-dim">{label}</span>
    </span>
  )
}

export function Btn({ primary, icon, children, onClick, small, disabled }) {
  return (
    <button
      type="button"
      className={['btn', primary ? 'btn-primary' : '', small ? 'btn-icon' : ''].join(' ')}
      onClick={onClick}
      disabled={disabled}
    >
      {icon && <i className={`ti ${icon}`} aria-hidden="true" />}
      {children}
    </button>
  )
}
