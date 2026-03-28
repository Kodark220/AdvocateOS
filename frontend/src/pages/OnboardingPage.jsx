import { useState } from 'react'
import { Shield, User, ArrowRight } from 'lucide-react'
import { useWallet } from '../context/WalletContext'

export default function OnboardingPage() {
  const { wallet, markRegistered, disconnect } = useWallet()
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const handleContinue = (e) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Please enter a username')
      return
    }
    if (trimmed.length < 2) {
      setError('Username must be at least 2 characters')
      return
    }
    markRegistered(trimmed)
  }

  return (
    <div className="min-h-screen grid-bg flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-sm bg-core border border-edge mb-4">
            <Shield className="w-7 h-7 text-acid" />
          </div>
          <h1 className="text-2xl font-extrabold text-signal tracking-tight">AdvocateOS</h1>
        </div>

        <div className="card p-8">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-acid/10 border border-acid/20 mb-4">
              <User className="w-6 h-6 text-acid" />
            </div>
            <h2 className="text-lg font-bold text-signal mb-1">Choose a username</h2>
            <p className="text-sm text-ghost leading-relaxed">
              Pick a display name to get started. You can complete full account registration from your dashboard.
            </p>
          </div>

          <div className="font-mono text-[11px] text-muted bg-void rounded-sm border border-edge px-3 py-2 mb-5 break-all text-center">
            {wallet}
          </div>

          {error && (
            <div className="mb-4 px-3 py-2.5 rounded-sm border border-burn/20 bg-burn/5">
              <p className="font-mono text-xs text-burn">{error}</p>
            </div>
          )}

          <form onSubmit={handleContinue}>
            <div className="mb-5">
              <label className="label-field">Username</label>
              <input
                className="input-field"
                placeholder="Enter your username"
                autoFocus
                value={name}
                onChange={e => { setName(e.target.value); setError('') }}
              />
            </div>

            <button type="submit" className="btn-primary w-full text-sm flex items-center justify-center gap-2">
              Continue to Dashboard
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <button onClick={disconnect} className="w-full mt-4 font-mono text-xs text-muted hover:text-ghost transition-colors">
            Use a different wallet
          </button>
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="font-mono text-[10px] text-muted">AI-Native Consumer Protection · Bradbury Testnet</p>
        </div>
      </div>
    </div>
  )
}
