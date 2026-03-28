import { Routes, Route, Navigate } from 'react-router-dom'
import { useWallet } from './context/WalletContext'
import Layout from './components/Layout'
import ConnectPage from './pages/ConnectPage'
import OnboardingPage from './pages/OnboardingPage'
// Admin pages
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Incidents from './pages/Incidents'
import CaseDetail from './pages/CaseDetail'
import Settings from './pages/Settings'
// User pages
import UserDashboard from './pages/user/UserDashboard'
import MyCases from './pages/user/MyCases'
import ReportPage from './pages/user/ReportPage'
import RegisterPage from './pages/user/RegisterPage'

export default function App() {
  const { connected, signed, role, needsOnboarding } = useWallet()

  // Step 1: Not connected → show wallet connect
  if (!connected || !signed) {
    return <Routes><Route path="*" element={<ConnectPage />} /></Routes>
  }

  // Step 2: Connected but not registered → show onboarding (users only)
  if (needsOnboarding) {
    return <Routes><Route path="*" element={<OnboardingPage />} /></Routes>
  }

  // Step 3: Admin dashboard
  if (role === 'admin') {
    return (
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/case/:id" element={<CaseDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Route>
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<UserDashboard />} />
        <Route path="/my-cases" element={<MyCases />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/case/:id" element={<CaseDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  )
}
