import { useState, useRef, useEffect } from 'react'
import { Wallet, LogOut, Copy, Check, ChevronDown } from 'lucide-react'
import { useWallet } from '../context/WalletContext'
import { getNetwork, setNetwork, fetchNetworks } from '../api'

const NET_LABELS = {
  bradbury: 'Bradbury Testnet',
  studionet: 'Studionet',
}

export default function WalletBar() {
  const { wallet, role, disconnect } = useWallet()
  const [open, setOpen] = useState(false)
  const [netOpen, setNetOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [network, setNet] = useState(getNetwork())
  const [networks, setNetworks] = useState({})
  const ref = useRef(null)
  const netRef = useRef(null)

  useEffect(() => {
    fetchNetworks().then((d) => setNetworks(d.networks || {}))
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
      if (netRef.current && !netRef.current.contains(e.target)) setNetOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleCopy = () => {
    navigator.clipboard.writeText(wallet)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const switchNetwork = (key) => {
    setNetwork(key)
    setNet(key)
    setNetOpen(false)
    window.location.reload()
  }

  return (
    <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
      <div className="flex items-center justify-end gap-3 px-6 h-12">

        {/* Network selector */}
        <div className="relative" ref={netRef}>
          <button
            onClick={() => setNetOpen(!netOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm border border-edge bg-core hover:border-muted transition-colors"
          >
            <div className={`w-1.5 h-1.5 rounded-full ${network === 'bradbury' ? 'bg-signal' : 'bg-acid'}`} />
            <span className="font-mono text-xs text-ghost">
              {NET_LABELS[network] || network}
            </span>
            <ChevronDown className="w-3 h-3 text-muted" />
          </button>
          {netOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-48 card p-2 shadow-xl shadow-black/40">
              {Object.keys(networks).length > 0
                ? Object.entries(networks).map(([key, cfg]) => (
                    <button
                      key={key}
                      onClick={() => switchNetwork(key)}
                      className={`w-full text-left px-3 py-2 rounded-sm font-mono text-xs transition-colors flex items-center gap-2
                        ${key === network ? 'bg-surface text-valid' : 'text-ghost hover:bg-surface/50'}`}
                    >
                      <div className={`w-1.5 h-1.5 rounded-full ${key === 'bradbury' ? 'bg-signal' : 'bg-acid'}`} />
                      {NET_LABELS[key] || key}
                      {key === network && <Check className="w-3 h-3 ml-auto" />}
                    </button>
                  ))
                : ['bradbury', 'studionet'].map((key) => (
                    <button
                      key={key}
                      onClick={() => switchNetwork(key)}
                      className={`w-full text-left px-3 py-2 rounded-sm font-mono text-xs transition-colors flex items-center gap-2
                        ${key === network ? 'bg-surface text-valid' : 'text-ghost hover:bg-surface/50'}`}
                    >
                      <div className={`w-1.5 h-1.5 rounded-full ${key === 'bradbury' ? 'bg-signal' : 'bg-acid'}`} />
                      {NET_LABELS[key]}
                      {key === network && <Check className="w-3 h-3 ml-auto" />}
                    </button>
                  ))}
            </div>
          )}
        </div>

        {/* Wallet dropdown */}
        <div className="relative" ref={ref}>
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-sm border border-edge bg-core hover:border-muted transition-colors"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-valid" />
            <Wallet className="w-3.5 h-3.5 text-ghost" />
            <span className="font-mono text-xs text-ghost">
              {wallet.slice(0, 6)}...{wallet.slice(-4)}
            </span>
            {role === 'admin' && <span className="tag-burn text-[9px] py-0">ADMIN</span>}
          </button>

          {open && (
            <div className="absolute right-0 top-full mt-1.5 w-64 card p-4 shadow-xl shadow-black/40">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-valid" />
                <span className="font-mono text-xs text-valid">Connected</span>
                {role === 'admin' && <span className="tag-burn text-[9px]">ADMIN</span>}
              </div>
              <div className="font-mono text-[11px] text-ghost break-all mb-3 leading-relaxed">
                {wallet}
              </div>
              <div className="flex items-center gap-2">
                <button onClick={handleCopy} className="btn-ghost text-xs flex items-center gap-1.5 flex-1">
                  {copied ? <Check className="w-3 h-3 text-valid" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <button onClick={disconnect} className="flex-1 rounded-sm border border-burn/20 bg-burn/5 px-3 py-2 font-mono text-xs text-burn hover:bg-burn/10 transition-colors flex items-center justify-center gap-1.5">
                  <LogOut className="w-3 h-3" />
                  Disconnect
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
