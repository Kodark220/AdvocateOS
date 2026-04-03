import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UserPlus, Building, Globe } from 'lucide-react'
import { useWallet } from '../../context/WalletContext'
import { registerAccount } from '../../api'
import { createWriteClient, getContractAddress, getChainName } from '../../glClient'
import { TransactionStatus } from 'genlayer-js/types'

const CHAINS = [
  'ethereum', 'base', 'solana', 'polygon', 'arbitrum',
  'optimism', 'avalanche', 'bsc', 'genlayer', 'stellar',
]

export default function RegisterPage() {
  const { wallet, username, markRegistered, provider } = useWallet()
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [form, setForm] = useState({
    name: username || '', institution: '', ref: '', atype: 'checking',
    jurisdiction: 'US', chain: '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    setStatus('')

    // Try wallet-signed direct contract write first
    if (provider && wallet) {
      try {
        setStatus('Switching wallet to GenLayer network...')
        const client = createWriteClient(wallet, provider)
        await client.connect(getChainName())

        setStatus('Please confirm the transaction in your wallet...')
        const txHash = await client.writeContract({
          address: getContractAddress(),
          functionName: 'register_account',
          args: [
            form.name,
            form.institution,
            form.ref,
            form.atype,
            form.jurisdiction,
            form.chain || '',
          ],
          value: BigInt(0),
        })

        setStatus('Transaction submitted! Waiting for confirmation...')
        await client.waitForTransactionReceipt({
          hash: txHash,
          status: TransactionStatus.ACCEPTED,
        })

        markRegistered(form.name)
        setSuccess(true)
        setTimeout(() => navigate('/'), 1500)
        setSubmitting(false)
        return
      } catch (err) {
        if (err.code === 4001) {
          setError('Transaction rejected. Please approve in your wallet to register.')
          setSubmitting(false)
          return
        }
        console.warn('Direct wallet write failed, falling back to backend:', err.message)
      }
    }

    // Fallback: use backend API
    setStatus('Registering via backend...')
    try {
      const res = await registerAccount({ ...form, wallet })
      if (res.ok) {
        markRegistered(form.name)
        setSuccess(true)
        setTimeout(() => navigate('/'), 1500)
      } else {
        setError(res.error || 'Registration failed. Please try again.')
      }
    } catch {
      setError('Registration failed. Server may be unreachable.')
    }
    setSubmitting(false)
  }

  if (success) {
    return (
      <div className="px-6 py-12 max-w-lg mx-auto text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-valid/10 border border-valid/20 mb-5">
          <UserPlus className="w-7 h-7 text-valid" />
        </div>
        <h2 className="text-lg font-bold text-signal mb-2">Account Registered!</h2>
        <p className="text-sm text-ghost">Redirecting to your dashboard...</p>
      </div>
    )
  }

  return (
    <div className="px-6 py-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-extrabold text-signal tracking-tight mb-1">Register Account</h1>
        <p className="font-mono text-xs text-muted">Link your wallet to an on-chain account</p>
      </div>

      <div className="card p-6">
        {error && (
          <div className="mb-4 px-3 py-2.5 rounded-sm border border-burn/20 bg-burn/5">
            <p className="font-mono text-xs text-burn">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 mb-6">
            <div>
              <label className="label-field">Full Name</label>
              <input
                className="input-field"
                placeholder="Jane Doe"
                required
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-field">
                  <Building className="w-3 h-3 inline mr-1" />
                  Institution
                </label>
                <input
                  className="input-field"
                  placeholder="N26, Revolut, Coinbase..."
                  required
                  value={form.institution}
                  onChange={e => setForm({ ...form, institution: e.target.value })}
                />
              </div>
              <div>
                <label className="label-field">Account Reference</label>
                <input
                  className="input-field"
                  placeholder="ACC-12345"
                  required
                  value={form.ref}
                  onChange={e => setForm({ ...form, ref: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-field">Account Type</label>
                <select
                  className="input-field"
                  value={form.atype}
                  onChange={e => setForm({ ...form, atype: e.target.value })}
                >
                  <option value="checking">Checking</option>
                  <option value="savings">Savings</option>
                  <option value="crypto_wallet">Crypto Wallet</option>
                  <option value="investment">Investment</option>
                </select>
              </div>
              <div>
                <label className="label-field">
                  <Globe className="w-3 h-3 inline mr-1" />
                  Jurisdiction
                </label>
                <select
                  className="input-field"
                  value={form.jurisdiction}
                  onChange={e => setForm({ ...form, jurisdiction: e.target.value })}
                >
                  <option value="US">US</option>
                  <option value="EU">EU</option>
                </select>
              </div>
            </div>

            <div>
              <label className="label-field">Chain (optional)</label>
              <select
                className="input-field"
                value={form.chain}
                onChange={e => setForm({ ...form, chain: e.target.value })}
              >
                <option value="">None</option>
                {CHAINS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="p-3 rounded-sm bg-void border border-edge mb-5">
            <div className="font-mono text-[10px] uppercase tracking-widest text-muted mb-1">Linked Wallet</div>
            <div className="font-mono text-xs text-ghost break-all">{wallet}</div>
          </div>

          {status && submitting && (
            <div className="mb-3 px-3 py-2 rounded-sm border border-signal/20 bg-signal/5">
              <p className="font-mono text-xs text-signal">{status}</p>
            </div>
          )}

          <button type="submit" className="btn-primary w-full text-sm" disabled={submitting}>
            {submitting ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-void/30 border-t-void rounded-full animate-spin" />
                Registering on-chain...
              </span>
            ) : (
              'Register Account'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
