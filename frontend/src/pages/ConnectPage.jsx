import { useState } from 'react'
import { Shield, Wallet, ArrowRight, Zap, ChevronDown, ExternalLink } from 'lucide-react'
import { useWallet } from '../context/WalletContext'

function FallbackWalletIcon() {
  return (
    <div className="w-7 h-7 rounded-full bg-surface border border-edge flex items-center justify-center">
      <Wallet className="w-3.5 h-3.5 text-ghost" />
    </div>
  )
}

export default function ConnectPage() {
  const { connectInjected, connectManual, connecting, error, setError, hasInjected, walletProviders } = useWallet()
  const [showManual, setShowManual] = useState(false)
  const [address, setAddress] = useState('')
  const [connectingId, setConnectingId] = useState(null)

  const handleManual = () => {
    connectManual(address)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleManual()
  }

  const handleProviderConnect = async (provider, uuid) => {
    setConnectingId(uuid)
    await connectInjected(provider)
    setConnectingId(null)
  }

  // Use EIP-6963 discovered wallets, fall back to legacy window.ethereum
  const hasDiscoveredWallets = walletProviders.length > 0

  return (
    <div className="min-h-screen grid-bg flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-sm bg-core border border-edge mb-5">
            <Shield className="w-8 h-8 text-acid" />
          </div>
          <h1 className="text-3xl font-extrabold text-signal tracking-tight mb-2">AdvocateOS</h1>
          <p className="text-sm text-ghost max-w-xs mx-auto leading-relaxed">
            Autonomous consumer advocacy agent powered by GenLayer Intelligent Contracts.
          </p>
        </div>

        {/* Connect card */}
        <div className="card p-8">
          <div className="flex items-center gap-2 mb-2">
            <Wallet className="w-4 h-4 text-acid" />
            <h2 className="text-sm font-bold text-signal">Connect Wallet</h2>
          </div>
          <p className="text-sm text-ghost mb-6 leading-relaxed">
            Connect your wallet to get started. You'll be asked to sign a message to verify ownership.
          </p>

          {/* Error */}
          {error && (
            <div className="mb-4 px-3 py-2.5 rounded-sm border border-burn/20 bg-burn/5">
              <p className="font-mono text-xs text-burn">{error}</p>
            </div>
          )}

          {/* Wallet providers — EIP-6963 discovered */}
          <div className="space-y-2.5 mb-5">
            {hasDiscoveredWallets ? (
              walletProviders.map(({ info, provider }) => (
                <button
                  key={info.uuid}
                  onClick={() => handleProviderConnect(provider, info.uuid)}
                  disabled={connecting}
                  className="w-full flex items-center gap-4 px-4 py-3.5 rounded-sm border border-edge bg-core hover:bg-surface hover:border-muted transition-all group"
                >
                  {info.icon ? (
                    <img src={info.icon} alt={info.name} className="w-7 h-7 rounded-sm" />
                  ) : (
                    <FallbackWalletIcon />
                  )}
                  <div className="flex-1 text-left">
                    <div className="text-sm font-semibold text-signal group-hover:text-acid transition-colors">
                      {info.name}
                    </div>
                    <div className="font-mono text-[11px] text-muted">{info.rdns || 'Detected'}</div>
                  </div>
                  {connectingId === info.uuid ? (
                    <div className="w-4 h-4 border-2 border-acid/30 border-t-acid rounded-full animate-spin" />
                  ) : (
                    <ExternalLink className="w-4 h-4 text-edge group-hover:text-muted transition-colors" />
                  )}
                </button>
              ))
            ) : hasInjected ? (
              /* Legacy fallback — single window.ethereum */
              <button
                onClick={() => connectInjected()}
                disabled={connecting}
                className="w-full flex items-center gap-4 px-4 py-3.5 rounded-sm border border-edge bg-core hover:bg-surface hover:border-muted transition-all group"
              >
                <FallbackWalletIcon />
                <div className="flex-1 text-left">
                  <div className="text-sm font-semibold text-signal group-hover:text-acid transition-colors">
                    Browser Wallet
                  </div>
                  <div className="font-mono text-[11px] text-muted">Detected</div>
                </div>
                {connecting ? (
                  <div className="w-4 h-4 border-2 border-acid/30 border-t-acid rounded-full animate-spin" />
                ) : (
                  <ExternalLink className="w-4 h-4 text-edge group-hover:text-muted transition-colors" />
                )}
              </button>
            ) : (
              <div className="px-4 py-3.5 rounded-sm border border-edge bg-core text-center">
                <p className="text-sm text-ghost">No wallet detected. Install a browser wallet to connect.</p>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="relative mb-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-edge" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-core px-3 font-mono text-[10px] uppercase tracking-widest text-muted">or</span>
            </div>
          </div>

          {/* Manual entry toggle */}
          <button
            onClick={() => { setShowManual(!showManual); setError('') }}
            className="w-full flex items-center justify-center gap-2 text-sm text-ghost hover:text-signal transition-colors mb-4"
          >
            <span className="font-mono text-xs">Enter address manually</span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showManual ? 'rotate-180' : ''}`} />
          </button>

          {showManual && (
            <div className="space-y-3">
              <div>
                <label className="label-field">Wallet Address</label>
                <input
                  className="input-field"
                  placeholder="0x..."
                  value={address}
                  onChange={e => { setAddress(e.target.value); setError('') }}
                  onKeyDown={handleKeyDown}
                  autoFocus
                />
              </div>
              <button
                onClick={handleManual}
                disabled={!address.trim()}
                className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
              >
                Connect
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Footer info */}
          <div className="mt-6 pt-5 border-t border-edge">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-acid" />
                <span className="font-mono text-[11px] text-ghost">AI-Native Enforcement</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-valid" />
                <span className="font-mono text-[11px] text-ghost">Bradbury Testnet</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <span className="font-mono text-[11px] text-muted">
            Built on{' '}
            <a href="https://genlayer.com/" target="_blank" rel="noreferrer" className="text-ghost hover:text-signal underline">
              GenLayer
            </a>
            {' '}· Optimistic Democracy Consensus
          </span>
        </div>
      </div>
    </div>
  )
}
