const API = import.meta.env.VITE_API_URL || '/api';

// ── Network state ──
let currentNetwork = localStorage.getItem('aos_network') || 'studionet';

export function getNetwork() {
  return currentNetwork;
}

export function setNetwork(net) {
  currentNetwork = net;
  localStorage.setItem('aos_network', net);
}

function withNetwork(url) {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}network=${currentNetwork}`;
}

export async function fetchNetworks() {
  const r = await fetch(`${API}/networks`);
  return r.ok ? r.json() : { networks: {}, default: 'studionet' };
}

export async function fetchNetworkStatus() {
  const r = await fetch(`${API}/networks/status`);
  return r.ok ? r.json() : {};
}

async function _get(url) {
  const r = await fetch(withNetwork(url));
  if (r.status === 503) {
    const err = await r.json().catch(() => ({}));
    return { _networkError: true, message: err.message || 'Network unreachable', network: err.network };
  }
  return r.ok ? r.json() : null;
}

export function isNetworkError(result) {
  return result && result._networkError === true;
}

export async function fetchStats() {
  const r = await _get(`${API}/stats`);
  return isNetworkError(r) ? r : (r || {});
}

export async function fetchAccounts() {
  const r = await _get(`${API}/accounts`);
  return isNetworkError(r) ? r : (r || []);
}

export async function fetchOpenCases() {
  const r = await _get(`${API}/cases/open`);
  return isNetworkError(r) ? r : (r || []);
}

export async function fetchAllCases() {
  const r = await _get(`${API}/cases`);
  return isNetworkError(r) ? r : (r || []);
}

export async function fetchCase(id) {
  const r = await _get(`${API}/case/${id}`);
  return isNetworkError(r) ? r : (r || null);
}

export async function fetchEscalationPath(id) {
  const r = await _get(`${API}/case/${id}/path`);
  return isNetworkError(r) ? r : (r || null);
}

export async function fetchWalletAccounts(address) {
  const r = await _get(`${API}/wallet/${address}`);
  return isNetworkError(r) ? r : (r || { accounts: [], registered: false });
}

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
