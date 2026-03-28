import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, RefreshCw, ChevronRight, ShieldAlert } from 'lucide-react'
import { fetchAccounts, fetchAllCases } from '../../api'
import { useWallet } from '../../context/WalletContext'
import StatusBadge from '../../components/StatusBadge'

const TABS = ['ALL', 'OPEN', 'ACTIVE', 'ESCALATED', 'RESOLVED']

export default function MyCases() {
  const { wallet } = useWallet()
  const [accounts, setAccounts] = useState([])
  const [cases, setCases] = useState([])
  const [tab, setTab] = useState('ALL')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    const [a, c] = await Promise.all([fetchAccounts(), fetchAllCases()])
    setAccounts(a)
    setCases(c)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const myAccountIds = new Set(
    accounts
      .filter(a => a.wallet_address && a.wallet_address.toLowerCase() === wallet.toLowerCase())
      .map(a => a.id)
  )
  const myCases = cases.filter(c => myAccountIds.has(c.account_id))

  const filtered = myCases.filter(c => {
    if (tab === 'ALL') return true
    if (tab === 'OPEN') return c.status === 'open'
    if (tab === 'ACTIVE') return c.status === 'complaint_drafted'
    if (tab === 'ESCALATED') return c.status?.includes('escalat')
    if (tab === 'RESOLVED') return c.status === 'resolved'
    return true
  })

  return (
    <div className="min-h-screen grid-bg">
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <h1 className="text-sm font-bold text-signal tracking-tight">My Cases</h1>
          <div className="flex items-center gap-2">
            <button onClick={load} disabled={loading} className="btn-ghost text-xs flex items-center gap-1.5">
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <Link to="/report" className="btn-primary text-xs">Report Violation</Link>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 max-w-[1200px] mx-auto">
        <div className="card">
          <div className="flex items-center gap-5 px-5 py-3.5 border-b border-edge overflow-x-auto">
            {TABS.map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`font-mono text-xs uppercase tracking-widest whitespace-nowrap pb-0.5 transition-colors ${
                  tab === t ? 'text-acid border-b border-acid' : 'text-muted hover:text-ghost'
                }`}
              >
                {t} {t === 'ALL' ? `(${myCases.length})` : ''}
              </button>
            ))}
          </div>

          <div className="divide-y divide-edge">
            {loading ? (
              <div className="px-5 py-16 text-center">
                <RefreshCw className="w-5 h-5 text-muted animate-spin mx-auto mb-3" />
                <p className="font-mono text-xs text-muted">Loading cases...</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="px-5 py-16 text-center">
                <ShieldAlert className="w-8 h-8 text-edge mx-auto mb-3" />
                <p className="text-sm text-ghost mb-1">No cases in this category.</p>
                <p className="font-mono text-xs text-muted">
                  <Link to="/report" className="text-acid hover:underline">Report a violation</Link> to start a case.
                </p>
              </div>
            ) : (
              filtered.map(c => (
                <Link
                  key={c.id}
                  to={`/case/${c.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-surface/50 transition-colors group"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <span className="font-mono text-xs text-muted w-8">#{c.id}</span>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-signal truncate">
                        {c.violation_type?.replace(/_/g, ' ')}
                      </div>
                      <div className="font-mono text-[11px] text-muted truncate mt-0.5">
                        {c.description?.slice(0, 80)}{c.description?.length > 80 ? '...' : ''}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0 ml-4">
                    <span className="font-mono text-xs text-muted hidden sm:block">{c.jurisdiction}</span>
                    <span className="font-mono text-xs text-muted hidden sm:block">T{c.current_tier}</span>
                    <StatusBadge status={c.status} />
                    <ChevronRight className="w-4 h-4 text-edge group-hover:text-muted transition-colors" />
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
