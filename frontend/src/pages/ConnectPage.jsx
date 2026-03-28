import { useState } from 'react'
import { Shield, Wallet, ArrowRight, Zap, ChevronDown, ExternalLink } from 'lucide-react'
import { useWallet } from '../context/WalletContext'

// Wallet provider icons as inline SVGs for zero-dependency rendering
function MetaMaskIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 35 33" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M32.96 1L19.7 10.82l2.45-5.9L32.96 1z" fill="#E17726" stroke="#E17726" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M2.66 1l13.11 9.92-2.33-5.99L2.66 1zM28.23 23.53l-3.52 5.4 7.53 2.08 2.16-7.34-6.17-.14zM.88 23.67l2.15 7.34 7.52-2.07-3.52-5.4-6.15.13z" fill="#E27625" stroke="#E27625" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M10.17 14.51L8.07 17.6l7.45.34-.26-8L10.17 14.5zM25.39 14.51l-5.16-4.66-.17 8.1 7.44-.33-2.11-3.1zM10.55 28.94l4.48-2.17-3.87-3.02-.61 5.19zM20.53 26.77l4.47 2.17-.6-5.2-3.87 3.03z" fill="#E27625" stroke="#E27625" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M25 28.94l-4.47-2.17.36 2.93-.04 1.23L25 28.94zM10.55 28.94l4.16 1.99-.03-1.23.35-2.93-4.48 2.17z" fill="#D5BFB2" stroke="#D5BFB2" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14.79 21.84l-3.73-1.1 2.63-1.21 1.1 2.31zM20.77 21.84l1.1-2.31 2.64 1.2-3.74 1.11z" fill="#233447" stroke="#233447" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M10.55 28.94l.64-5.4-4.16.13 3.52 5.27zM24.37 23.53l.63 5.4 3.53-5.27-4.16-.13zM27.5 17.6l-7.44.34.69 3.9 1.1-2.31 2.64 1.2 3.01-3.13zM11.06 20.74l2.64-1.21 1.1 2.31.69-3.9-7.45-.34 2.96 3.14z" fill="#CC6228" stroke="#CC6228" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M8.07 17.6l3.06 5.97-.1-2.83L8.07 17.6zM24.5 20.74l-.11 2.83 3.05-5.97-2.94 3.14zM15.53 17.94l-.7 3.9.87 4.48.2-5.91-.37-2.47zM20.06 17.94l-.36 2.46.18 5.92.87-4.49-.69-3.89z" fill="#E27525" stroke="#E27525" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M20.75 21.84l-.87 4.49.62.44 3.87-3.02.11-2.83-3.73 1.1v-.18zM11.06 20.74l.1 2.83 3.87 3.02.62-.44-.87-4.49-3.72-1.1v.18z" fill="#F5841F" stroke="#F5841F" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M20.8 30.93l.04-1.23-.34-.29h-5.37l-.33.3.03 1.22-4.16-1.99 1.46 1.19 2.95 2.04h5.46l2.96-2.04 1.45-1.19-4.15 1.99z" fill="#C0AC9D" stroke="#C0AC9D" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M20.53 26.77l-.62-.44h-3.58l-.62.44-.35 2.93.33-.29h5.37l.34.3-.35-2.94h-.52z" fill="#161616" stroke="#161616" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M33.52 11.35L34.62 6 32.96 1l-12.43 9.23 4.78 4.04 6.75 1.97 1.49-1.74-.65-.47 1.03-.94-.79-.61 1.03-.79-.68-.51zM1 6l1.1 5.35-.7.52 1.04.79-.79.6 1.03.95-.65.47 1.49 1.74 6.75-1.97 4.78-4.04L2.66 1 1 6z" fill="#763E1A" stroke="#763E1A" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M32.06 16.24l-6.75-1.97 2.05 3.1-3.06 5.97 4.04-.05h6.03l-2.31-7.05zM10.17 14.27l-6.75 1.97-2.25 7.05h6.02l4.04.05-3.06-5.97 2-3.1zM20.06 17.94l.43-7.48 1.96-5.3h-8.72l1.93 5.3.46 7.48.17 2.48.01 5.9h3.58l.02-5.9.16-2.48z" fill="#F5841F" stroke="#F5841F" strokeWidth=".25" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function CoinbaseIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <rect width="28" height="28" rx="5.6" fill="#0052FF"/>
      <path fillRule="evenodd" clipRule="evenodd" d="M14 23.8c5.41 0 9.8-4.39 9.8-9.8S19.41 4.2 14 4.2 4.2 8.59 4.2 14s4.39 9.8 9.8 9.8zm-3.15-12.25a1.05 1.05 0 011.05-1.05h4.2a1.05 1.05 0 011.05 1.05v4.9a1.05 1.05 0 01-1.05 1.05h-4.2a1.05 1.05 0 01-1.05-1.05v-4.9z" fill="#fff"/>
    </svg>
  )
}

function GenericWalletIcon() {
  return (
    <div className="w-7 h-7 rounded-full bg-surface border border-edge flex items-center justify-center">
      <Wallet className="w-3.5 h-3.5 text-ghost" />
    </div>
  )
}

export default function ConnectPage() {
  const { connectInjected, connectManual, connecting, error, setError, hasInjected } = useWallet()
  const [showManual, setShowManual] = useState(false)
  const [address, setAddress] = useState('')

  const handleManual = () => {
    connectManual(address)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleManual()
  }

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

          {/* Wallet providers */}
          <div className="space-y-2.5 mb-5">
            {/* MetaMask */}
            <button
              onClick={connectInjected}
              disabled={connecting}
              className="w-full flex items-center gap-4 px-4 py-3.5 rounded-sm border border-edge bg-core hover:bg-surface hover:border-muted transition-all group"
            >
              <MetaMaskIcon />
              <div className="flex-1 text-left">
                <div className="text-sm font-semibold text-signal group-hover:text-acid transition-colors">
                  MetaMask
                </div>
                <div className="font-mono text-[11px] text-muted">
                  {hasInjected ? 'Detected' : 'Not installed'}
                </div>
              </div>
              {connecting ? (
                <div className="w-4 h-4 border-2 border-acid/30 border-t-acid rounded-full animate-spin" />
              ) : (
                <ExternalLink className="w-4 h-4 text-edge group-hover:text-muted transition-colors" />
              )}
            </button>

            {/* Coinbase Wallet */}
            <button
              onClick={connectInjected}
              disabled={connecting}
              className="w-full flex items-center gap-4 px-4 py-3.5 rounded-sm border border-edge bg-core hover:bg-surface hover:border-muted transition-all group"
            >
              <CoinbaseIcon />
              <div className="flex-1 text-left">
                <div className="text-sm font-semibold text-signal group-hover:text-acid transition-colors">
                  Coinbase Wallet
                </div>
                <div className="font-mono text-[11px] text-muted">Browser extension</div>
              </div>
              <ExternalLink className="w-4 h-4 text-edge group-hover:text-muted transition-colors" />
            </button>

            {/* Browser wallet (generic injected) */}
            <button
              onClick={connectInjected}
              disabled={connecting}
              className="w-full flex items-center gap-4 px-4 py-3.5 rounded-sm border border-edge bg-core hover:bg-surface hover:border-muted transition-all group"
            >
              <GenericWalletIcon />
              <div className="flex-1 text-left">
                <div className="text-sm font-semibold text-signal group-hover:text-acid transition-colors">
                  Browser Wallet
                </div>
                <div className="font-mono text-[11px] text-muted">Any injected provider</div>
              </div>
              <ExternalLink className="w-4 h-4 text-edge group-hover:text-muted transition-colors" />
            </button>
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
