export default function StatusBadge({ status }) {
  const s = (status || '').toLowerCase()

  if (s === 'resolved')
    return <span className="tag-valid">resolved</span>
  if (s.includes('escalat'))
    return <span className="tag-burn">escalated</span>
  if (s.includes('complaint'))
    return <span className="tag-pulse">drafted</span>
  if (s === 'open')
    return <span className="tag-warn">open</span>

  return <span className="tag-acid">{status}</span>
}
