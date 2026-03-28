const API = import.meta.env.VITE_API_URL || '/api';

export async function fetchStats() {
  const r = await fetch(`${API}/stats`);
  return r.ok ? r.json() : {};
}

export async function fetchAccounts() {
  const r = await fetch(`${API}/accounts`);
  return r.ok ? r.json() : [];
}

export async function fetchOpenCases() {
  const r = await fetch(`${API}/cases/open`);
  return r.ok ? r.json() : [];
}

export async function fetchAllCases() {
  const r = await fetch(`${API}/cases`);
  return r.ok ? r.json() : [];
}

export async function fetchCase(id) {
  const r = await fetch(`${API}/case/${id}`);
  return r.ok ? r.json() : null;
}

export async function fetchEscalationPath(id) {
  const r = await fetch(`${API}/case/${id}/path`);
  return r.ok ? r.json() : null;
}

export async function registerAccount(data) {
  const r = await fetch(`${API}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function reportViolation(data) {
  const r = await fetch(`${API}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function draftComplaint(caseId) {
  const r = await fetch(`${API}/draft/${caseId}`, { method: 'POST' });
  return r.json();
}

export async function escalateCase(caseId) {
  const r = await fetch(`${API}/escalate/${caseId}`, { method: 'POST' });
  return r.json();
}

export async function resolveCase(caseId, data) {
  const r = await fetch(`${API}/resolve/${caseId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}
