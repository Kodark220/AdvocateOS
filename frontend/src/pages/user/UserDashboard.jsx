import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert, FileText, AlertTriangle, Wallet, RefreshCw, ChevronRight, Activity, UserPlus } from 'lucide-react'
import { fetchStats, fetchAccounts, fetchAllCases, isNetworkError } from '../../api'
import { useWallet } from '../../context/WalletContext'
import StatusBadge from '../../components/StatusBadge'
import NetworkBanner from '../../components/NetworkBanner'

export default function UserDashboard() {
  const { wallet, username } = useWallet()
  const [accounts, setAccounts] = useState([])
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [networkError, setNetworkError] = useState(null)

  const load = async () => {
    setLoading(true)
    setNetworkError(null)
    const [a, c] = await Promise.all([fetchAccounts(), fetchAllCases()])
    if (isNetworkError(a)) {
      setNetworkError(a.message)
      setAccounts([]); setCases([])
    } else {
      setAccounts(Array.isArray(a) ? a : []); setCases(Array.isArray(c) ? c : [])
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  // Filter to user's accounts and cases
  const myAccounts = accounts.filter(
    a => a.wallet_address && a.wallet_address.toLowerCase() === wallet.toLowerCase()
  )
  const myAccountIds = new Set(myAccounts.map(a => a.id))
  const myCases = cases.filter(c => myAccountIds.has(c.account_id))
  const activeCases = myCases.filter(c => c.status !== 'resolved')
  const resolvedCases = myCases.filter(c => c.status === 'resolved')
  const totalRecovered = resolvedCases.reduce((sum, c) => sum + (c.amount_recovered || 0), 0)

  return (
    <div className="min-h-screen grid-bg">
      {/* Top bar */}
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-valid animate-pulse" />
              <span className="font-mono text-xs text-ghost">Connected</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Wallet className="w-3.5 h-3.5 text-ghost" />
            <span className="font-mono text-xs text-muted">{wallet.slice(0, 8)}...{wallet.slice(-6)}</span>
          </div>
        </div>
      </div>

      <NetworkBanner message={networkError} />

      <div className="px-6 py-6 max-w-[1200px] mx-auto">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-extrabold text-signal tracking-tight mb-1">Welcome back{username ? `, ${username}` : ''}</h1>
          <p className="font-mono text-xs text-muted">Your consumer protection overview</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <StatCard label="MY ACCOUNTS" value={myAccounts.length} icon={Wallet} />
          <StatCard label="ACTIVE CASES" value={activeCases.length} icon={ShieldAlert} />
          <StatCard label="RESOLVED" value={resolvedCases.length} icon={FileText} />
          <StatCard label="RECOVERED" value={totalRecovered} icon={Activity} />
        </div>

        {/* Quick actions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <Link to="/register" className="card-hover p-5 flex items-center gap-4 border-acid/30">
            <div className="w-10 h-10 rounded-sm bg-acid/10 border border-acid/20 flex items-center justify-center flex-shrink-0">
              <UserPlus className="w-5 h-5 text-acid" />
            </div>
            <div>
              <div className="text-sm font-bold text-signal">{myAccounts.length === 0 ? 'Register Account' : 'Add Another Account'}</div>
              <div className="font-mono text-[11px] text-muted mt-0.5">{myAccounts.length === 0 ? 'Link your wallet to an on-chain account' : 'Register another institution account'}</div>
            </div>
            <ChevronRight className="w-4 h-4 text-edge ml-auto" />
          </Link>
          <Link to="/report" className="card-hover p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-sm bg-burn/10 border border-burn/20 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-burn" />
            </div>
            <div>
              <div className="text-sm font-bold text-signal">Report a Violation</div>
              <div className="font-mono text-[11px] text-muted mt-0.5">File a complaint against an institution</div>
            </div>
            <ChevronRight className="w-4 h-4 text-edge ml-auto" />
          </Link>
          <Link to="/my-cases" className="card-hover p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-sm bg-pulse/10 border border-pulse/20 flex items-center justify-center flex-shrink-0">
              <FileText className="w-5 h-5 text-pulse" />
            </div>
            <div>
              <div className="text-sm font-bold text-signal">View My Cases</div>
              <div className="font-mono text-[11px] text-muted mt-0.5">Track progress on your active disputes</div>
            </div>
            <ChevronRight className="w-4 h-4 text-edge ml-auto" />
          </Link>
        </div>

        {/* My accounts */}
        <div className="card mb-6">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-edge">
            <h2 className="text-sm font-bold text-signal">My Accounts</h2>
            <button onClick={load} disabled={loading} className="btn-ghost text-xs flex items-center gap-1.5">
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="divide-y divide-edge">
            {loading ? (
              <div className="px-5 py-12 text-center">
                <RefreshCw className="w-5 h-5 text-muted animate-spin mx-auto mb-3" />
                <p className="font-mono text-xs text-muted">Loading...</p>
              </div>
            ) : myAccounts.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <Wallet className="w-6 h-6 text-edge mx-auto mb-3" />
                <p className="text-sm text-ghost mb-1">No accounts linked to your wallet</p>
                <p className="font-mono text-xs text-muted">
                  Ask an admin to register an account with your wallet address.
                </p>
              </div>
            ) : (
              myAccounts.map(a => (
                <div key={a.id} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-mono text-xs text-muted">#{a.id}</span>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-signal">{a.name} <span className="text-muted">@ {a.institution}</span></div>
                      <div className="font-mono text-[11px] text-muted mt-0.5">{a.account_type} · {a.jurisdiction}{a.chain ? ` · ${a.chain}` : ''}</div>
                    </div>
                  </div>
                  {a.active
                    ? <span className="tag-valid">active</span>
                    : <span className="badge-status bg-edge/50 text-muted">inactive</span>
                  }
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent cases */}
        <div className="card">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-edge">
            <h2 className="text-sm font-bold text-signal">Recent Cases</h2>
            {myCases.length > 0 && (
              <Link to="/my-cases" className="font-mono text-xs text-acid hover:underline">View all</Link>
            )}
          </div>
          <div className="divide-y divide-edge">
            {loading ? (
              <div className="px-5 py-12 text-center">
                <RefreshCw className="w-5 h-5 text-muted animate-spin mx-auto mb-3" />
              </div>
            ) : myCases.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <ShieldAlert className="w-6 h-6 text-edge mx-auto mb-3" />
                <p className="text-sm text-ghost mb-1">No cases yet</p>
                <p className="font-mono text-xs text-muted">
                  <Link to="/report" className="text-acid hover:underline">Report a violation</Link> to get started.
                </p>
              </div>
            ) : (
              myCases.slice(0, 5).map(c => (
                <Link
                  key={c.id}
                  to={`/case/${c.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-surface/50 transition-colors group"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <span className="font-mono text-xs text-muted w-8">#{c.id}</span>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-signal truncate">{c.violation_type?.replace(/_/g, ' ')}</div>
                      <div className="font-mono text-[11px] text-muted truncate mt-0.5">
                        {c.description?.slice(0, 60)}{c.description?.length > 60 ? '...' : ''}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0 ml-4">
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
