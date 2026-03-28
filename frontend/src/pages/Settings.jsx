import { Link2 } from 'lucide-react'

const CONTRACT = '0x6E7694c3ffbB4b109b2A37D009cE29425039E9da'

export default function Settings() {
  return (
    <div className="min-h-screen grid-bg">
      {/* Top bar */}
      <div className="sticky top-0 z-40 border-b border-edge bg-void/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-6 h-14">
          <h1 className="text-sm font-bold text-signal tracking-tight">Settings</h1>
        </div>
      </div>

      <div className="px-6 py-6 max-w-[700px] mx-auto">
        {/* Contract info */}
        <div className="card p-6 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <Link2 className="w-4 h-4 text-acid" />
            <h2 className="text-sm font-bold text-signal">Contract</h2>
          </div>
          <div className="space-y-3">
            <div>
              <div className="label-field">Contract Address</div>
              <div className="font-mono text-xs text-ghost break-all">{CONTRACT}</div>
            </div>
            <div>
              <div className="label-field">Network</div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-valid" />
                <span className="font-mono text-xs text-ghost">GenLayer Bradbury Testnet</span>
              </div>
            </div>
            <div>
              <div className="label-field">Protocol</div>
              <span className="font-mono text-xs text-ghost">Optimistic Democracy Consensus</span>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="card p-6">
          <h2 className="text-sm font-bold text-signal mb-3">About AdvocateOS</h2>
          <p className="text-sm text-ghost leading-relaxed mb-3">
            Autonomous consumer protection agent powered by GenLayer's Intelligent Contracts.
            AI-drafted legal complaints, multi-jurisdiction escalation paths, and on-chain enforcement
            with Optimistic Democracy consensus.
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="tag-acid">GenLayer</span>
            <span className="tag-pulse">AI-Native</span>
            <span className="tag-valid">US + EU</span>
          </div>
        </div>
      </div>
    </div>
  )
}
