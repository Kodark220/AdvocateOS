import { AlertTriangle } from 'lucide-react'
import { getNetwork, setNetwork } from '../api'

const NET_LABELS = {
  bradbury: 'Bradbury Testnet',
  studionet: 'Studionet',
}

export default function NetworkBanner({ message }) {
  if (!message) return null
  const net = getNetwork()
  const other = net === 'bradbury' ? 'studionet' : 'bradbury'

  const switchTo = () => {
    setNetwork(other)
    window.location.href = '/'
  }

  return (
    <div className="mx-6 mt-4 px-4 py-3 rounded-sm border border-burn/30 bg-burn/5 flex items-center gap-3">
      <AlertTriangle className="w-4 h-4 text-burn flex-shrink-0" />
      <span className="text-xs text-burn/90 flex-1">
        {message || `${NET_LABELS[net] || net} is currently unreachable.`}
      </span>
      <button
        onClick={switchTo}
        className="px-3 py-1 text-xs font-mono rounded-sm border border-acid/30 bg-acid/10 text-acid hover:bg-acid/20 transition-colors whitespace-nowrap"
      >
        Switch to {NET_LABELS[other]}
      </button>
    </div>
  )
}
