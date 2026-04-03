import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert, Plus, RefreshCw, ChevronRight, FileText } from 'lucide-react'
import { fetchAllCases, fetchAccounts, reportViolation } from '../api'
import { contractWrite } from '../glClient'
import { useWallet } from '../context/WalletContext'
import StatusBadge from '../components/StatusBadge'

const TABS = ['ALL', 'FILED', 'ACTIVE', 'ESCALATED', 'NEED APPROVAL', 'RESOLVED']

const VIOLATIONS = [
  'overcharge', 'missed_deadline', 'sla_breach',
  'unauthorized_fee', 'interest_calculation_error', 'disclosure_failure',
  'unauthorized_transfer', 'yield_misrepresentation', 'withdrawal_restriction',
]

export default function Incidents() {
  const [cases, setCases] = useState([])
  const [accounts, setAccounts] = useState([])
  const [tab, setTab] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [showReport, setShowReport] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [reportError, setReportError] = useState('')
  const [form, setForm] = useState({
    account_id: '', violation_type: VIOLATIONS[0], description: '', amount: '0', severity: '3',
  })
  const { wallet, provider } = useWallet()

  const load = async () => {
    setLoading(true)
    const [c, a] = await Promise.all([fetchAllCases(), fetchAccounts()])
    setCases(c)
    setAccounts(a)
    if (a.length > 0 && !form.account_id) setForm(f => ({...f, account_id: String(a[0].id)}))
    setLoading(false)
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    const h = () => load()
    window.addEventListener('networkChanged', h)
    return () => window.removeEventListener('networkChanged', h)
  }, [])

  const handleReport = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setReportError('')

    // Try wallet-signed write first
    if (provider && wallet) {
      try {
        await contractWrite(wallet, 'report_violation', [
          Number(form.account_id),
          form.violation_type,
          form.description,
          Number(form.amount),
          Number(form.severity),
        ], provider)
        setShowReport(false)
        setForm(f => ({...f, description: '', amount: '0', severity: '3'}))
        await load()
        setSubmitting(false)
        return
      } catch (err) {
        if (err.code === 4001) { setReportError('Transaction rejected.'); setSubmitting(false); return }
        console.error('Wallet write failed:', err.message)
        setReportError(`Report failed: ${err.message || 'Unknown error'}. Please try again.`)
        setSubmitting(false)
        return
      }
    } else {
      setReportError('Please connect your wallet first. A wallet signature is required.')
      setSubmitting(false)
    }
  }

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
          <h1 className="text-sm font-bold text-signal tracking-tight">Incidents</h1>
          <div className="flex items-center gap-2">
            <button onClick={load} className="btn-ghost text-xs flex items-center gap-1.5">
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={() => setShowReport(!showReport)} className="btn-primary text-xs flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              Report Violation
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 max-w-[1200px] mx-auto">
        {/* Report form */}
        {showReport && (
          <div className="card p-6 mb-6">
            <h2 className="text-sm font-bold text-signal mb-5">Report a Violation</h2>
            <form onSubmit={handleReport}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="label-field">Account</label>
                  <select className="input-field" value={form.account_id}
                    onChange={e => setForm({...form, account_id: e.target.value})} required>
                    {accounts.map(a => (
                      <option key={a.id} value={a.id}>#{a.id} — {a.name} @ {a.institution}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label-field">Violation Type</label>
                  <select className="input-field" value={form.violation_type}
                    onChange={e => setForm({...form, violation_type: e.target.value})}>
                    {VIOLATIONS.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
              </div>
              <div className="mb-4">
                <label className="label-field">Description</label>
                <textarea className="input-field min-h-[80px] resize-y" placeholder="Describe what happened..."
                  required value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="label-field">Amount Disputed</label>
                  <input type="number" className="input-field" min="0"
                    value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} />
                </div>
                <div>
                  <label className="label-field">Severity</label>
                  <select className="input-field" value={form.severity}
                    onChange={e => setForm({...form, severity: e.target.value})}>
                    <option value="1">1 — Low</option>
                    <option value="2">2 — Minor</option>
                    <option value="3">3 — Medium</option>
                    <option value="4">4 — High</option>
                    <option value="5">5 — Critical</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {reportError && (
                  <span className="font-mono text-xs text-burn">{reportError}</span>
                )}
                <button type="submit" className="btn-primary text-xs" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Submit Report'}
                </button>
                <button type="button" onClick={() => setShowReport(false)} className="btn-ghost text-xs">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Tabs + list */}
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
                {t}
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
                <FileText className="w-8 h-8 text-edge mx-auto mb-3" />
                <p className="text-sm text-ghost mb-1">No incidents in this category.</p>
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
                    <span className="font-mono text-xs text-ghost hidden sm:block">
                      {c.amount_disputed || 0}
                    </span>
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
