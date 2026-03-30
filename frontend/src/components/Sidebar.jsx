import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, ShieldAlert, Settings, FileText, AlertTriangle, UserPlus, LogOut } from 'lucide-react'
import { useWallet } from '../context/WalletContext'

const adminLinks = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/accounts', icon: Users, label: 'Accounts' },
  { to: '/incidents', icon: ShieldAlert, label: 'Incidents' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const userLinks = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/register', icon: UserPlus, label: 'Add Account' },
  { to: '/my-cases', icon: FileText, label: 'My Cases' },
  { to: '/report', icon: AlertTriangle, label: 'Report' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { wallet, role, disconnect } = useWallet()
  const links = role === 'admin' ? adminLinks : userLinks

  return (
    <aside className="fixed top-0 left-0 bottom-0 w-[220px] bg-core border-r border-edge flex flex-col z-50">
      {/* Logo */}
      <div className="px-5 pt-6 pb-5 border-b border-edge">
        <div className="flex items-center gap-2.5">
          <img src="/logo_png.jpg" alt="AdvocateOS" className="w-6 h-6 rounded-full" />
          <span className="text-lg font-bold tracking-tight text-signal">AdvocateOS</span>
        </div>
        {role === 'admin' && (
          <div className="mt-2">
            <span className="tag-burn text-[9px]">ADMIN</span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm font-medium transition-colors mb-0.5 ${
                isActive
                  ? 'bg-surface text-signal border-l-2 border-acid'
                  : 'text-ghost hover:text-signal hover:bg-surface/50'
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Wallet + Footer */}
      <div className="px-5 py-4 border-t border-edge">
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-1.5 h-1.5 rounded-full bg-valid animate-pulse" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-ghost">
            {role === 'admin' ? 'Agent Active' : 'Connected'}
          </span>
        </div>
        <div className="font-mono text-[10px] text-muted leading-relaxed truncate" title={wallet}>
          {wallet.slice(0, 10)}...{wallet.slice(-6)}
        </div>
        <button
          onClick={disconnect}
          className="flex items-center gap-1.5 mt-2 font-mono text-[10px] text-burn/70 hover:text-burn transition-colors"
        >
          <LogOut className="w-3 h-3" />
          Disconnect
        </button>
        <div className="mt-3 font-mono text-[10px] text-muted leading-relaxed">
          Built on GenLayer
        </div>
        <div className="mt-1 inline-block px-2 py-0.5 bg-surface rounded-sm font-mono text-[9px] text-muted">
          Bradbury Testnet
        </div>
      </div>
    </aside>
  )
}
