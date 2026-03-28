import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import WalletBar from './WalletBar'

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[220px]">
        <WalletBar />
        <Outlet />
      </main>
    </div>
  )
}
