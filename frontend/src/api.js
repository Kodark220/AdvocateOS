import { contractRead } from './glClient'

const API = import.meta.env.VITE_API_URL || '/api';

// ── Network state ──
let currentNetwork = localStorage.getItem('aos_network') || 'studionet';

export function getNetwork() {
  return currentNetwork;
}

export function setNetwork(net) {
  currentNetwork = net;
  localStorage.setItem('aos_network', net);
  window.dispatchEvent(new CustomEvent('networkChanged', { detail: net }));
}

function withNetwork(url) {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}network=${currentNetwork}`;
}

// ── Backend-only helpers ──

export async function fetchNetworks() {
  try {
    const r = await fetch(`${API}/networks`);
    return r.ok ? r.json() : { networks: {}, default: 'studionet' };
  } catch {
    return { networks: {}, default: 'studionet' };
  }
}

export async function fetchNetworkStatus() {
  try {
    const r = await fetch(`${API}/networks/status`);
    return r.ok ? r.json() : {};
  } catch {
    return {};
  }
}

async function _get(url) {
  try {
    const r = await fetch(withNetwork(url));
    if (r.status === 503) {
      const err = await r.json().catch(() => ({}));
      return { _networkError: true, message: err.message || 'Network unreachable', network: err.network };
    }
    return r.ok ? r.json() : null;
  } catch {
    return null;
  }
}

export function isNetworkError(result) {
  return result && result._networkError === true;
}

// ── Read operations: contract-first, backend fallback ──

export async function fetchStats() {
  const direct = await contractRead('get_stats')
  if (direct) return direct
  const r = await _get(`${API}/stats`)
  return isNetworkError(r) ? r : (r || {})
}

export async function fetchAccounts() {
  const direct = await contractRead('get_all_accounts')
  if (Array.isArray(direct)) return direct
  const r = await _get(`${API}/accounts`)
  return isNetworkError(r) ? r : (r || [])
}

export async function fetchOpenCases() {
  const direct = await contractRead('get_open_cases')
  if (Array.isArray(direct)) return direct
  const r = await _get(`${API}/cases/open`)
  return isNetworkError(r) ? r : (r || [])
}

export async function fetchAllCases() {
  // No single get_all_cases on contract — get count then iterate
  try {
    const stats = await contractRead('get_stats')
    if (stats && stats.total_violations === 0) return []
    if (stats && typeof stats.total_violations === 'number') {
      const n = stats.total_violations
      const batch = Array.from({ length: n }, (_, i) =>
        contractRead('get_case', [i + 1])
      )
      const results = (await Promise.all(batch)).filter(Boolean)
      if (results.length > 0) return results
    }
  } catch { /* fall through */ }
  const r = await _get(`${API}/cases`)
  return isNetworkError(r) ? r : (r || [])
}

export async function fetchCase(id) {
  const direct = await contractRead('get_case', [Number(id)])
  if (direct) return direct
  const r = await _get(`${API}/case/${id}`)
  return isNetworkError(r) ? r : (r || null)
}

export async function fetchEscalationPath(id) {
  const direct = await contractRead('get_escalation_path', [Number(id)])
  if (direct) return direct
  const r = await _get(`${API}/case/${id}/path`)
  return isNetworkError(r) ? r : (r || null)
}

export async function fetchWalletAccounts(address) {
  try {
    const all = await contractRead('get_all_accounts')
    if (Array.isArray(all)) {
      const mine = all.filter(
        a => a.wallet_address && a.wallet_address.toLowerCase() === address.toLowerCase()
      )
      return { accounts: mine, registered: mine.length > 0 }
    }
  } catch { /* fall through */ }
  try {
    const r = await _get(`${API}/wallet/${address}`)
    return isNetworkError(r) ? r : (r || { accounts: [], registered: false })
  } catch {
    return { accounts: [], registered: false }
  }
}

// ── Write operations (backend fallback — pages prefer wallet signing) ──

export async function registerAccount(data) {
  const r = await fetch(`${API}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...data, network: currentNetwork }),
  });
  return r.json();
}

export async function reportViolation(data) {
  const r = await fetch(`${API}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...data, network: currentNetwork }),
  });
  return r.json();
}

export async function draftComplaint(caseId) {
  const r = await fetch(`${API}/draft/${caseId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ network: currentNetwork }),
  });
  return r.json();
}

export async function escalateCase(caseId) {
  const r = await fetch(`${API}/escalate/${caseId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ network: currentNetwork }),
  });
  return r.json();
}

export async function resolveCase(caseId, data) {
  const r = await fetch(`${API}/resolve/${caseId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...data, network: currentNetwork }),
  });
  return r.json();
}
