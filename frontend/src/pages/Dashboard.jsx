import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert, CheckCircle, DollarSign, TrendingUp, RefreshCw, ChevronRight, Activity, Wallet, Users } from 'lucide-react'
import { fetchStats, fetchAccounts, fetchAllCases } from '../api'
import { useWallet } from '../context/WalletContext'
import StatusBadge from '../components/StatusBadge'

const TABS = ['ALL', 'FILED', 'ACTIVE', 'ESCALATED', 'NEED APPROVAL', 'RESOLVED']

export default function Dashboard() {
  const [stats, setStats] = useState({})
  const [accounts, setAccounts] = useState([])
  const [cases, setCases] = useState([])
  const [tab, setTab] = useState('ALL')
  const [loading, setLoading] = useState(true)

  const { wallet } = useWallet()

  const load = async () => {
    setLoading(true)
    const [s, a, c] = await Promise.all([fetchStats(), fetchAccounts(), fetchAllCases()])
    setStats(s)
    setAccounts(a)
    setCases(c)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const total = stats.total_violations || 0
  const resolved = stats.total_resolved || 0
  const rate = total > 0 ? Math.round((resolved / total) * 100) : 0

  // Compute total recovered from resolved cases
  const totalRecovered = cases
    .filter(c => c.status === 'resolved')
    .reduce((sum, c) => sum + (c.amount_recovered || 0), 0)

  const filtered = cases.filter(c => {
    if (tab === 'ALL') return true
    if (tab === 'FILED') return c.status === 'open'
    if (tab === 'ACTIVE') return c.status === 'complaint_drafted'
    if (tab === 'ESCALATED') return c.status?.includes('escalat')
    if (tab === 'NEED APPROVAL') return c.status === 'escalation_recommended'
    if (tab === 'RESOLVED') return c.status === 'resolved'
    return true
  })

  return (
    <div className="min-h-screen grid-bg">
      {/* Top bar */}
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-valid animate-pulse" />
              <span className="font-mono text-xs text-ghost">Agent Active</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Wallet className="w-3.5 h-3.5 text-valid" />
            <span className="font-mono text-xs text-ghost">{wallet.slice(0, 8)}...{wallet.slice(-6)}</span>
            <span className="tag-burn text-[9px]">ADMIN</span>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 max-w-[1400px] mx-auto">
        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-8">
          <StatCard label="USERS" value={stats.total_accounts || accounts.length} icon={Users} />
          <StatCard label="CASES OPENED" value={total} icon={ShieldAlert} />
          <StatCard label="RESOLVED" value={resolved} icon={CheckCircle} />
          <StatCard label="TOTAL RECOVERED" value={`${totalRecovered}`} icon={DollarSign} prefix="" suffix="" />
          <StatCard label="RESOLUTION RATE" value={`${rate}%`} icon={TrendingUp} />
        </div>

        {/* Agent status */}
        <div className="card p-5 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="w-4 h-4 text-acid" />
            <span className="text-sm font-semibold text-signal">
              Agent is monitoring {accounts.length} accounts
            </span>
          </div>
          <div className="font-mono text-xs text-muted">
            {cases.filter(c => c.status !== 'resolved').length} active cases · {stats.total_escalations || 0} escalations pending
          </div>
        </div>

        {/* Cases section */}
        <div className="card">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-edge">
            <div className="flex items-center gap-5 overflow-x-auto">
              {TABS.map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`font-mono text-xs uppercase tracking-widest whitespace-nowrap pb-0.5 transition-colors ${
                    tab === t
                      ? 'text-acid border-b border-acid'
                      : 'text-muted hover:text-ghost'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            <button
              onClick={load}
              disabled={loading}
              className="btn-ghost text-xs flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Cases list */}
          <div className="divide-y divide-edge">
            {loading ? (
              <div className="px-5 py-16 text-center">
                <RefreshCw className="w-5 h-5 text-muted animate-spin mx-auto mb-3" />
                <p className="font-mono text-xs text-muted">Loading cases...</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="px-5 py-16 text-center">
                <ShieldAlert className="w-8 h-8 text-edge mx-auto mb-3" />
                <p className="text-sm text-ghost mb-1">No incidents detected yet.</p>
                <p className="font-mono text-xs text-muted">
                  Add accounts in the <Link to="/accounts" className="text-acid hover:underline">Accounts</Link> tab for the agent to watch.
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

      {/* Footer */}
      <div className="border-t border-edge px-6 py-4 mt-12">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <span className="font-mono text-[11px] text-muted">
            AdvocateOS — Built on <a href="https://genlayer.com/" target="_blank" rel="noreferrer" className="text-ghost hover:text-signal underline">GenLayer</a>
          </span>
          <span className="font-mono text-[11px] text-muted">
            Optimistic Democracy consensus · AI-native enforcement
          </span>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted">{label}</span>
        <Icon className="w-4 h-4 text-edge" />
      </div>
      <div className="text-3xl font-extrabold text-signal tracking-tight">{value}</div>
    </div>
  )
}
