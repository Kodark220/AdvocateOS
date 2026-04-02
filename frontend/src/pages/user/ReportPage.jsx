import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { fetchAccounts, reportViolation } from '../../api'
import { contractWrite } from '../../glClient'
import { useWallet } from '../../context/WalletContext'

const VIOLATIONS = [
  'overcharge', 'missed_deadline', 'sla_breach',
  'unauthorized_fee', 'interest_calculation_error', 'disclosure_failure',
  'unauthorized_transfer', 'yield_misrepresentation', 'withdrawal_restriction',
]

export default function ReportPage() {
  const { wallet } = useWallet()
  const navigate = useNavigate()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    account_id: '', violation_type: VIOLATIONS[0], description: '', amount: '0', severity: '3',
  })

  const loadAccounts = async () => {
    setLoading(true)
    const all = await fetchAccounts()
    const mine = all.filter(a => a.wallet_address && a.wallet_address.toLowerCase() === wallet.toLowerCase())
    setAccounts(mine)
    if (mine.length > 0) setForm(f => ({ ...f, account_id: String(mine[0].id) }))
    setLoading(false)
  }

  useEffect(() => { loadAccounts() }, [wallet])
  useEffect(() => {
    const h = () => loadAccounts()
    window.addEventListener('networkChanged', h)
    return () => window.removeEventListener('networkChanged', h)
  }, [wallet])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    setStatus('')

    // Try wallet-signed direct contract write
    if (window.ethereum && wallet) {
      try {
        setStatus('Please confirm the transaction in your wallet...')
        await contractWrite(wallet, 'report_violation', [
          Number(form.account_id),
          form.violation_type,
          form.description,
          Number(form.amount),
          Number(form.severity),
        ])
        setSubmitting(false)
        navigate('/my-cases')
        return
      } catch (err) {
        if (err.code === 4001) {
          setError('Transaction rejected. Please approve in your wallet.')
          setSubmitting(false)
          return
        }
        console.warn('Direct write failed, falling back:', err.message)
      }
    }

    // Fallback: backend API
    setStatus('Submitting via backend...')
    try {
      const res = await reportViolation(form)
      if (res.ok) {
        navigate('/my-cases')
      } else {
        setError(res.error || 'Report failed. Please try again.')
      }
    } catch {
      setError('Report failed. Server may be unreachable.')
    }
    setSubmitting(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen grid-bg flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-muted animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen grid-bg">
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <h1 className="text-sm font-bold text-signal tracking-tight">Report Violation</h1>
        </div>
      </div>

      <div className="px-6 py-6 max-w-[700px] mx-auto">
        {accounts.length === 0 ? (
          <div className="card p-12 text-center">
            <AlertTriangle className="w-8 h-8 text-edge mx-auto mb-3" />
            <p className="text-sm text-ghost mb-1">No accounts linked to your wallet</p>
            <p className="font-mono text-xs text-muted">
              Ask an admin to register an account with your wallet address before reporting.
            </p>
          </div>
        ) : (
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-6">
              <AlertTriangle className="w-4 h-4 text-burn" />
              <h2 className="text-sm font-bold text-signal">File a Complaint</h2>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="label-field">Account</label>
                  <select
                    className="input-field"
                    value={form.account_id}
                    onChange={e => setForm({ ...form, account_id: e.target.value })}
                    required
                  >
                    {accounts.map(a => (
                      <option key={a.id} value={a.id}>#{a.id} — {a.name} @ {a.institution}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label-field">Violation Type</label>
                  <select
                    className="input-field"
                    value={form.violation_type}
                    onChange={e => setForm({ ...form, violation_type: e.target.value })}
                  >
                    {VIOLATIONS.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
              </div>

              <div className="mb-4">
                <label className="label-field">Description</label>
                <textarea
                  className="input-field min-h-[100px] resize-y"
                  placeholder="Describe what happened in detail..."
                  required
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="label-field">Amount Disputed</label>
                  <input
                    type="number"
                    className="input-field"
                    min="0"
                    value={form.amount}
                    onChange={e => setForm({ ...form, amount: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label-field">Severity</label>
                  <select
                    className="input-field"
                    value={form.severity}
                    onChange={e => setForm({ ...form, severity: e.target.value })}
                  >
                    <option value="1">1 — Low</option>
                    <option value="2">2 — Minor</option>
                    <option value="3">3 — Medium</option>
                    <option value="4">4 — High</option>
                    <option value="5">5 — Critical</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="mb-4 px-3 py-2.5 rounded-sm border border-burn/20 bg-burn/5">
                  <p className="font-mono text-xs text-burn">{error}</p>
                </div>
              )}

              {status && submitting && (
                <div className="mb-4 px-3 py-2 rounded-sm border border-signal/20 bg-signal/5">
                  <p className="font-mono text-xs text-signal">{status}</p>
                </div>
              )}

              <button type="submit" className="btn-primary w-full text-sm" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Submit Report'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
