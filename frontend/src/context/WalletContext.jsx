import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { contractRead } from '../glClient'

const ADMIN_WALLET = (import.meta.env.VITE_ADMIN_WALLET || '0xf9346827f713eb953a2e22465b9ee91901726bdc').toLowerCase()
const API_BASE = import.meta.env.VITE_API_URL || '/api'

const WalletContext = createContext(null)

export function WalletProvider({ children }) {
  const [wallet, setWallet] = useState(() => localStorage.getItem('aos_wallet') || '')
  const [signed, setSigned] = useState(() => localStorage.getItem('aos_signed') === 'true')
  const [registered, setRegistered] = useState(() => localStorage.getItem('aos_registered') === 'true')
  const [username, setUsername] = useState(() => localStorage.getItem('aos_username') || '')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')
  const [walletProviders, setWalletProviders] = useState([])
  const activeProvider = useRef(null)

  const connected = !!wallet
  const role = connected && wallet.toLowerCase() === ADMIN_WALLET ? 'admin' : 'user'
  const hasInjected = typeof window !== 'undefined' && !!window.ethereum

  // EIP-6963: Discover all installed wallet providers
  useEffect(() => {
    const discovered = new Map()

    const handleAnnounce = async (event) => {
      const { info, provider } = event.detail
      if (info && provider && !discovered.has(info.uuid)) {
        discovered.set(info.uuid, { info, provider })
        setWalletProviders(Array.from(discovered.values()))

        // Reconnect: if we have a stored wallet, check if this provider owns it
        const storedWallet = localStorage.getItem('aos_wallet')
        if (storedWallet && !activeProvider.current) {
          try {
            const accounts = await provider.request({ method: 'eth_accounts' })
            if (accounts?.some(a => a.toLowerCase() === storedWallet.toLowerCase())) {
              activeProvider.current = provider
            }
          } catch { /* provider doesn't support eth_accounts silently */ }
        }
      }
    }

    window.addEventListener('eip6963:announceProvider', handleAnnounce)
    // Request all wallets to announce themselves
    window.dispatchEvent(new Event('eip6963:requestProvider'))

    // Also try window.ethereum as fallback for reconnection
    const storedWallet = localStorage.getItem('aos_wallet')
    if (storedWallet && !activeProvider.current && window.ethereum) {
      window.ethereum.request({ method: 'eth_accounts' }).then(accounts => {
        if (accounts?.some(a => a.toLowerCase() === storedWallet.toLowerCase())) {
          if (!activeProvider.current) activeProvider.current = window.ethereum
        }
      }).catch(() => {})
    }

    return () => window.removeEventListener('eip6963:announceProvider', handleAnnounce)
  }, [])

  // Admin is always considered registered
  const isRegistered = role === 'admin' || registered
  const needsOnboarding = connected && signed && !isRegistered

  const persist = (addr) => {
    setWallet(addr)
    localStorage.setItem('aos_wallet', addr)
    setError('')
  }

  // Check if wallet has accounts on the contract
  const checkRegistration = useCallback(async (addr) => {
    // Try direct contract read first
    try {
      const all = await contractRead('get_all_accounts')
      if (Array.isArray(all)) {
        const has = all.some(a => a.wallet_address && a.wallet_address.toLowerCase() === addr.toLowerCase())
        setRegistered(has)
        localStorage.setItem('aos_registered', has ? 'true' : 'false')
        return has
      }
    } catch { /* fall through to backend */ }
    // Fallback: backend API
    try {
      const r = await fetch(`${API_BASE}/wallet/${addr}`)
      if (r.ok) {
        const data = await r.json()
        const has = data.accounts && data.accounts.length > 0
        setRegistered(has)
        localStorage.setItem('aos_registered', has ? 'true' : 'false')
        return has
      }
    } catch {}
    // Both checks failed (network error) — preserve existing state instead of forcing unregistered
    const existing = localStorage.getItem('aos_registered') === 'true'
    setRegistered(existing)
    return existing
  }, [])

  // Sign a message to verify wallet ownership
  const signMessage = useCallback(async (addr, provider) => {
    const p = provider || activeProvider.current || window.ethereum
    if (!p) return false
    try {
      const message = `Welcome to AdvocateOS!\n\nSign this message to verify your wallet ownership.\n\nWallet: ${addr}\nTimestamp: ${Date.now()}`
      await p.request({
        method: 'personal_sign',
        params: [message, addr],
      })
      setSigned(true)
      localStorage.setItem('aos_signed', 'true')
      return true
    } catch (err) {
      if (err.code === 4001) {
        setError('Signature rejected. You must sign to verify your wallet.')
      } else {
        setError(err.message || 'Signature failed.')
      }
      return false
    }
  }, [])

  // Full connect flow: request accounts → sign message → check registration
  const connectInjected = useCallback(async (provider) => {
    const p = provider || window.ethereum
    if (!p) {
      setError('No wallet detected. Install MetaMask or another browser wallet.')
      return
    }
    activeProvider.current = p
    setConnecting(true)
    setError('')
    try {
      const accounts = await p.request({ method: 'eth_requestAccounts' })
      if (!accounts || accounts.length === 0) {
        setError('No accounts returned.')
        return
      }
      const addr = accounts[0]
      persist(addr)

      // Sign message to verify ownership
      const didSign = await signMessage(addr, p)
      if (!didSign) {
        // Revert connection if they won't sign
        setWallet('')
        localStorage.removeItem('aos_wallet')
        return
      }

      // Check if already registered on contract
      await checkRegistration(addr)
    } catch (err) {
      if (err.code === 4001) {
        setError('Connection rejected. Please approve the request in your wallet.')
      } else {
        setError(err.message || 'Wallet connection failed.')
      }
    } finally {
      setConnecting(false)
    }
  }, [signMessage, checkRegistration])

  // Manual connect (no signing possible)
  const connectManual = useCallback(async (address) => {
    const addr = (address || '').trim()
    if (!addr) { setError('Please enter a wallet address'); return }
    if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) { setError('Invalid wallet address'); return }
    persist(addr)
    setSigned(true) // Manual entry trusts the user
    localStorage.setItem('aos_signed', 'true')
    await checkRegistration(addr)
  }, [checkRegistration])

  const markRegistered = useCallback((name) => {
    if (name) {
      setUsername(name)
      localStorage.setItem('aos_username', name)
    }
    setRegistered(true)
    localStorage.setItem('aos_registered', 'true')
  }, [])

  const disconnect = useCallback(() => {
    setWallet('')
    setSigned(false)
    setRegistered(false)
    setUsername('')
    localStorage.removeItem('aos_wallet')
    localStorage.removeItem('aos_signed')
    localStorage.removeItem('aos_registered')
    localStorage.removeItem('aos_username')
    setError('')
  }, [])

  // Listen for account changes
  useEffect(() => {
    const p = activeProvider.current || window.ethereum
    if (!p) return
    const handleChange = (accounts) => {
      if (accounts.length === 0) {
        disconnect()
      } else {
        persist(accounts[0])
        setSigned(false)
        setRegistered(false)
        localStorage.setItem('aos_signed', 'false')
        localStorage.setItem('aos_registered', 'false')
      }
    }
    p.on('accountsChanged', handleChange)
    return () => p.removeListener('accountsChanged', handleChange)
  }, [disconnect])

  // Re-check registration on load if wallet is already connected
  useEffect(() => {
    if (wallet && signed && role !== 'admin') {
      checkRegistration(wallet)
    }
  }, [])

  return (
    <WalletContext.Provider value={{
      wallet, connected, role, connecting, error, hasInjected,
      signed, isRegistered, needsOnboarding, username, walletProviders,
      connectInjected, connectManual, disconnect, setError,
      markRegistered, checkRegistration,
      get provider() { return activeProvider.current || window.ethereum },
    }}>
      {children}
    </WalletContext.Provider>
  )
}

export function useWallet() {
  const ctx = useContext(WalletContext)
  if (!ctx) throw new Error('useWallet must be used within WalletProvider')
  return ctx
}
