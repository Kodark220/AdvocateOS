import { useEffect, useState } from 'react'
import { Plus, Trash2, Wallet, Globe, RefreshCw, Search, CheckCircle, XCircle } from 'lucide-react'
import { fetchAccounts, registerAccount, fetchWalletAccounts } from '../api'

const CHAINS = [
  'ethereum', 'base', 'solana', 'polygon', 'arbitrum',
  'optimism', 'avalanche', 'bsc', 'genlayer', 'stellar',
]

export default function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    name: '', institution: '', ref: '', atype: 'checking',
    jurisdiction: 'US', wallet: '', chain: '',
  })

  // Wallet lookup state
  const [lookupAddr, setLookupAddr] = useState('')
  const [lookupResult, setLookupResult] = useState(null) // { registered, accounts }
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupError, setLookupError] = useState('')

  const handleLookup = async (e) => {
    e.preventDefault()
    const addr = lookupAddr.trim()
    if (!addr) return
    if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) {
      setLookupError('Invalid wallet address')
      setLookupResult(null)
      return
    }
    setLookupLoading(true)
    setLookupError('')
    setLookupResult(null)
    try {
      const data = await fetchWalletAccounts(addr)
      setLookupResult(data)
    } catch {
      setLookupError('Network error')
    }
    setLookupLoading(false)
  }

  const load = async () => {
    setLoading(true)
    setAccounts(await fetchAccounts())
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    const res = await registerAccount(form)
    if (res.ok) {
      setForm({ name: '', institution: '', ref: '', atype: 'checking', jurisdiction: 'US', wallet: '', chain: '' })
      setShowForm(false)
      await load()
    }
    setSubmitting(false)
  }

  return (
    <div className="min-h-screen grid-bg">
      {/* Top bar */}
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <h1 className="text-sm font-bold text-signal tracking-tight">Accounts</h1>
          <div className="flex items-center gap-2">
            <button onClick={load} className="btn-ghost text-xs flex items-center gap-1.5">
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={() => setShowForm(!showForm)} className="btn-primary text-xs flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              Add Account
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 max-w-[1200px] mx-auto">
        {/* Wallet Lookup */}
        <div className="card p-5 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Search className="w-4 h-4 text-acid" />
            <h2 className="text-sm font-bold text-signal">Wallet Lookup</h2>
            <span className="font-mono text-[10px] text-muted ml-1">Check if a wallet is registered on the contract</span>
          </div>
          <form onSubmit={handleLookup} className="flex items-center gap-3">
            <input
              className="input-field flex-1"
              placeholder="Enter wallet address (0x...)"
              value={lookupAddr}
              onChange={e => { setLookupAddr(e.target.value); setLookupError(''); setLookupResult(null) }}
            />
            <button type="submit" className="btn-primary text-xs flex items-center gap-1.5 flex-shrink-0" disabled={lookupLoading}>
              {lookupLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Search className="w-3.5 h-3.5" />
              )}
              Check
            </button>
          </form>

          {lookupError && (
            <div className="mt-3 px-3 py-2 rounded-sm border border-burn/20 bg-burn/5">
              <p className="font-mono text-xs text-burn">{lookupError}</p>
            </div>
          )}

          {lookupResult && (
            <div className="mt-4">
              {lookupResult.registered ? (
                <div className="rounded-sm border border-valid/20 bg-valid/5 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-4 h-4 text-valid" />
                    <span className="text-sm font-bold text-valid">Registered</span>
                    <span className="font-mono text-[11px] text-ghost">
                      — {lookupResult.accounts.length} account{lookupResult.accounts.length !== 1 ? 's' : ''} found
                    </span>
                  </div>
                  <div className="space-y-2">
                    {lookupResult.accounts.map((a, i) => (
                      <div key={i} className="flex items-center justify-between bg-void/50 rounded-sm border border-edge px-3 py-2">
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="font-mono text-xs text-muted">#{a.id}</span>
                          <span className="text-sm text-signal font-medium">{a.name}</span>
                          <span className="font-mono text-xs text-muted">@ {a.institution}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="font-mono text-[11px] text-muted">{a.account_type} · {a.jurisdiction}</span>
                          {a.active
                            ? <span className="tag-valid">active</span>
                            : <span className="badge-status bg-edge/50 text-muted">inactive</span>
                          }
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-sm border border-burn/20 bg-burn/5 p-4 flex items-center gap-3">
                  <XCircle className="w-5 h-5 text-burn flex-shrink-0" />
                  <div>
                    <p className="text-sm font-bold text-burn">Not Registered</p>
                    <p className="font-mono text-[11px] text-ghost mt-0.5">
                      This wallet has no accounts on the contract.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Register form */}
        {showForm && (
          <div className="card p-6 mb-6">
            <h2 className="text-sm font-bold text-signal mb-5">Register New Account</h2>
            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="label-field">Full Name</label>
                  <input className="input-field" placeholder="Jane Doe" required
                    value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
                </div>
                <div>
                  <label className="label-field">Institution</label>
                  <input className="input-field" placeholder="N26, Revolut, Coinbase..." required
                    value={form.institution} onChange={e => setForm({...form, institution: e.target.value})} />
                </div>
                <div>
                  <label className="label-field">Account Reference</label>
                  <input className="input-field" placeholder="ACC-12345" required
                    value={form.ref} onChange={e => setForm({...form, ref: e.target.value})} />
                </div>
                <div>
                  <label className="label-field">Account Type</label>
                  <select className="input-field" value={form.atype}
                    onChange={e => setForm({...form, atype: e.target.value})}>
                    <option value="checking">Checking</option>
                    <option value="savings">Savings</option>
                    <option value="crypto_wallet">Crypto Wallet</option>
                    <option value="investment">Investment</option>
                  </select>
                </div>
                <div>
                  <label className="label-field">Jurisdiction</label>
                  <select className="input-field" value={form.jurisdiction}
                    onChange={e => setForm({...form, jurisdiction: e.target.value})}>
                    <option value="US">US</option>
                    <option value="EU">EU</option>
                  </select>
                </div>
                <div>
                  <label className="label-field">Chain</label>
                  <select className="input-field" value={form.chain}
                    onChange={e => setForm({...form, chain: e.target.value})}>
                    <option value="">None</option>
                    {CHAINS.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="mb-4">
                <label className="label-field">Wallet Address</label>
                <input className="input-field" placeholder="0x... (optional)"
                  value={form.wallet} onChange={e => setForm({...form, wallet: e.target.value})} />
              </div>
              <div className="flex items-center gap-3">
                <button type="submit" className="btn-primary text-xs" disabled={submitting}>
                  {submitting ? 'Registering...' : 'Register Account'}
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="btn-ghost text-xs">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Accounts list */}
        {loading ? (
          <div className="text-center py-16">
            <RefreshCw className="w-5 h-5 text-muted animate-spin mx-auto mb-3" />
            <p className="font-mono text-xs text-muted">Loading accounts...</p>
          </div>
        ) : accounts.length === 0 ? (
          <div className="card p-12 text-center">
            <Wallet className="w-8 h-8 text-edge mx-auto mb-3" />
            <p className="text-sm text-ghost mb-1">No accounts registered</p>
            <p className="font-mono text-xs text-muted">Click "Add Account" to get started.</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {accounts.map(a => (
              <div key={a.id} className="card-hover p-5 group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-9 h-9 rounded-sm bg-surface border border-edge flex items-center justify-center flex-shrink-0">
                      <span className="font-mono text-xs text-ghost">#{a.id}</span>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-signal">{a.name}</span>
                        <span className="font-mono text-xs text-muted">@ {a.institution}</span>
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="font-mono text-[11px] text-muted">{a.account_type || 'checking'}</span>
                        <span className="text-edge">·</span>
                        <span className="font-mono text-[11px] text-muted">{a.jurisdiction}</span>
                        {a.chain && (
                          <>
                            <span className="text-edge">·</span>
                            <span className="font-mono text-[11px] text-muted flex items-center gap-1">
                              <Globe className="w-3 h-3" />{a.chain}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {a.wallet_address && (
                      <span className="font-mono text-[11px] text-muted hidden lg:inline" title={a.wallet_address}>
                        {a.wallet_address.slice(0, 8)}...{a.wallet_address.slice(-6)}
                      </span>
                    )}
                    {a.active
                      ? <span className="tag-valid">active</span>
                      : <span className="badge-status bg-edge/50 text-muted">inactive</span>
                    }
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
