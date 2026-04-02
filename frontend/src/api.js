const API = import.meta.env.VITE_API_URL || '/api';

// ── Network state ──
let currentNetwork = localStorage.getItem('aos_network') || 'bradbury';

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
  return r.ok ? r.json() : { networks: {}, default: 'bradbury' };
}

export async function fetchStats() {
  const r = await fetch(withNetwork(`${API}/stats`));
  return r.ok ? r.json() : {};
}

export async function fetchAccounts() {
  const r = await fetch(withNetwork(`${API}/accounts`));
  return r.ok ? r.json() : [];
}

export async function fetchOpenCases() {
  const r = await fetch(withNetwork(`${API}/cases/open`));
  return r.ok ? r.json() : [];
}

export async function fetchAllCases() {
  const r = await fetch(withNetwork(`${API}/cases`));
  return r.ok ? r.json() : [];
}

export async function fetchCase(id) {
  const r = await fetch(withNetwork(`${API}/case/${id}`));
  return r.ok ? r.json() : null;
}

export async function fetchEscalationPath(id) {
  const r = await fetch(withNetwork(`${API}/case/${id}/path`));
  return r.ok ? r.json() : null;
}

export async function fetchWalletAccounts(address) {
  const r = await fetch(withNetwork(`${API}/wallet/${address}`));
  return r.ok ? r.json() : { accounts: [], registered: false };
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
