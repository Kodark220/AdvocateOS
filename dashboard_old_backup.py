"""
AdvocateOS Dashboard — Web Frontend for the Consumer Advocacy Agent.

Provides a real-time view of:
  - Registered accounts with wallet/chain info
  - Open & resolved cases with full complaint text
  - Escalation timeline per case
  - Contract stats overview
  - Actions: register account, report violation, draft complaint, escalate, resolve

Run:  py dashboard.py
Then open http://127.0.0.1:5000
"""

import subprocess
import shutil
import json
import os
import sys
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify

# ── CONFIG ──

CONTRACT_ADDRESS = "0xAE693Bbb157FAf221bc6F6f12766f494Ae99aef3"
GL_PATH = shutil.which("genlayer")
WRITE_TIMEOUT = 600
READ_TIMEOUT = 60

SUPPORTED_CHAINS = [
    "ethereum", "base", "solana", "polygon", "arbitrum",
    "optimism", "avalanche", "bsc", "genlayer", "stellar",
]

JURISDICTION_TIERS = {
    "US": ["Company Internal", "CFPB / State AG", "OCC / FDIC / FRB", "Small Claims / Federal Court"],
    "EU": ["Company Internal", "National ADR / EU ODR", "National Consumer Authority", "National Court / CJEU"],
}

VIOLATION_TYPES = [
    "overcharge", "missed_deadline", "sla_breach",
    "unauthorized_fee", "interest_calculation_error", "disclosure_failure",
    "unauthorized_transfer", "yield_misrepresentation", "withdrawal_restriction",
]

app = Flask(__name__)
app.secret_key = os.urandom(24)


# ── GENLAYER CLI HELPERS ──

def gl_call(method, *args):
    cmd = [GL_PATH, "call", CONTRACT_ADDRESS, method]
    for a in args:
        cmd += ["--args", str(a)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=READ_TIMEOUT, shell=True)
        for line in (r.stdout + r.stderr).split("\n"):
            s = line.strip()
            if s.startswith("{") or s.startswith("["):
                return json.loads(s)
    except Exception:
        pass
    return None


def gl_write(method, *args):
    cmd = [GL_PATH, "write", CONTRACT_ADDRESS, method]
    for a in args:
        cmd += ["--args", str(a)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=WRITE_TIMEOUT, shell=True)
        return "successfully" in (r.stdout + r.stderr).lower()
    except Exception:
        return False


# ── ROUTES ──

@app.route("/")
def index():
    stats = gl_call("get_stats") or {}
    accounts = gl_call("get_all_accounts") or []
    open_cases = gl_call("get_open_cases") or []
    return render_template_string(INDEX_HTML,
        stats=stats, accounts=accounts, cases=open_cases,
        contract=CONTRACT_ADDRESS,
        chains=SUPPORTED_CHAINS, violations=VIOLATION_TYPES,
        jurisdictions=list(JURISDICTION_TIERS.keys()),
        tiers=JURISDICTION_TIERS,
    )


@app.route("/case/<int:case_id>")
def case_detail(case_id):
    case = gl_call("get_case", str(case_id))
    if not case or not isinstance(case, dict):
        flash("Case not found", "error")
        return redirect(url_for("index"))
    path = gl_call("get_escalation_path", str(case_id)) or {}
    acc = None
    try:
        acc = gl_call("get_account", str(case.get("account_id", 0)))
        if isinstance(acc, str):
            acc = json.loads(acc)
    except Exception:
        pass
    return render_template_string(CASE_HTML,
        case=case, path=path, account=acc,
        contract=CONTRACT_ADDRESS, tiers=JURISDICTION_TIERS,
    )


@app.route("/cases/all")
def all_cases():
    stats = gl_call("get_stats") or {}
    total = stats.get("total_violations", 0)
    cases = []
    for i in range(1, total + 1):
        c = gl_call("get_case", str(i))
        if c and isinstance(c, dict):
            cases.append(c)
    return render_template_string(ALL_CASES_HTML, cases=cases, contract=CONTRACT_ADDRESS)


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    institution = request.form.get("institution", "").strip()
    ref = request.form.get("ref", "").strip()
    atype = request.form.get("atype", "").strip()
    jur = request.form.get("jurisdiction", "US")
    wallet = request.form.get("wallet", "").strip()
    chain = request.form.get("chain", "")
    if not all([name, institution, ref, atype]):
        flash("All fields are required", "error")
        return redirect(url_for("index"))
    ok = gl_write("register_account", name, institution, ref, atype, jur, wallet, chain)
    flash("Account registered!" if ok else "Registration failed (consensus issue)", "success" if ok else "error")
    return redirect(url_for("index"))


@app.route("/report", methods=["POST"])
def report():
    aid = request.form.get("account_id", "")
    vtype = request.form.get("violation_type", "")
    desc = request.form.get("description", "").strip()
    amount = request.form.get("amount", "0")
    severity = request.form.get("severity", "3")
    if not all([aid, vtype, desc]):
        flash("All fields required", "error")
        return redirect(url_for("index"))
    ok = gl_write("report_violation", aid, vtype, desc, amount, severity)
    flash("Violation reported!" if ok else "Report failed", "success" if ok else "error")
    return redirect(url_for("index"))


@app.route("/draft/<int:case_id>", methods=["POST"])
def draft(case_id):
    ok = gl_write("draft_complaint", str(case_id))
    flash(f"Complaint drafted for case #{case_id}!" if ok else "Drafting failed", "success" if ok else "error")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/escalate/<int:case_id>", methods=["POST"])
def escalate(case_id):
    ok = gl_write("escalate", str(case_id))
    flash(f"Case #{case_id} escalated!" if ok else "Escalation failed", "success" if ok else "error")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/resolve/<int:case_id>", methods=["POST"])
def resolve(case_id):
    note = request.form.get("note", "").strip()
    amount = request.form.get("amount", "0")
    ok = gl_write("resolve_case", str(case_id), note, amount)
    flash(f"Case #{case_id} resolved!" if ok else "Resolution failed", "success" if ok else "error")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/api/stats")
def api_stats():
    return jsonify(gl_call("get_stats") or {})


# ── HTML TEMPLATES ──

INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AdvocateOS Dashboard</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2a2d3a;--accent:#6366f1;--accent2:#818cf8;
--green:#22c55e;--red:#ef4444;--yellow:#eab308;--text:#e2e8f0;--muted:#94a3b8;--font:'Segoe UI',system-ui,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh}
a{color:var(--accent2);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:1200px;margin:0 auto;padding:1rem}
header{background:linear-gradient(135deg,#1e1b4b,#312e81);padding:1.5rem 0;border-bottom:1px solid var(--border);margin-bottom:1.5rem}
header .container{display:flex;justify-content:space-between;align-items:center}
h1{font-size:1.5rem;font-weight:700}h1 span{color:var(--accent2)}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:.75rem;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge-active{background:#22c55e22;color:var(--green)}.badge-inactive{background:#ef444422;color:var(--red)}
.badge-open{background:#eab30822;color:var(--yellow)}.badge-resolved{background:#22c55e22;color:var(--green)}
.badge-escalated{background:#f9731533;color:#f97315}.badge-drafted{background:#6366f122;color:var(--accent2)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.75rem;margin-bottom:1.5rem}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:.75rem;padding:1rem;text-align:center}
.stat-card .num{font-size:2rem;font-weight:700;color:var(--accent2)}.stat-card .label{color:var(--muted);font-size:.8rem;margin-top:.25rem}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}
@media(max-width:768px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:.75rem;padding:1.25rem;margin-bottom:1rem}
.card h2{font-size:1.1rem;margin-bottom:.75rem;display:flex;align-items:center;gap:.5rem}
.card h2 .icon{font-size:1.3rem}
table{width:100%;border-collapse:collapse;font-size:.85rem}th,td{padding:.5rem .6rem;text-align:left;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
.form-row{display:flex;gap:.5rem;margin-bottom:.5rem;flex-wrap:wrap}
.form-row input,.form-row select,.form-row textarea{flex:1;min-width:120px;padding:.5rem;border-radius:.5rem;border:1px solid var(--border);
background:var(--bg);color:var(--text);font-size:.85rem}
.form-row textarea{min-height:60px}
button,.btn{padding:.5rem 1rem;border-radius:.5rem;font-size:.85rem;font-weight:600;cursor:pointer;border:none;transition:all .2s}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{background:var(--accent2)}
.btn-danger{background:var(--red);color:#fff}.btn-success{background:var(--green);color:#fff}
.btn-sm{padding:.3rem .6rem;font-size:.75rem}
.flash{padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;font-size:.85rem}
.flash-success{background:#22c55e22;border:1px solid #22c55e44;color:var(--green)}
.flash-error{background:#ef444422;border:1px solid #ef444444;color:var(--red)}
.mono{font-family:'Cascadia Code',monospace;font-size:.75rem;color:var(--muted)}
.wallet-info{font-size:.75rem;color:var(--muted)}
.nav-links{display:flex;gap:1rem;font-size:.85rem}
</style>
</head>
<body>
<header><div class="container">
<h1>&#x1F6E1; Advocate<span>OS</span></h1>
<div class="nav-links">
<a href="/">Dashboard</a>
<a href="/cases/all">All Cases</a>
<span class="mono">{{ contract[:10] }}...{{ contract[-6:] }}</span>
</div>
</div></header>

<div class="container">
{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}
<div class="flash flash-{{ cat }}">{{ msg }}</div>
{% endfor %}{% endwith %}

<div class="stats">
<div class="stat-card"><div class="num">{{ stats.get('total_accounts',0) }}</div><div class="label">Accounts</div></div>
<div class="stat-card"><div class="num">{{ stats.get('total_violations',0) }}</div><div class="label">Violations</div></div>
<div class="stat-card"><div class="num">{{ stats.get('total_escalations',0) }}</div><div class="label">Escalations</div></div>
<div class="stat-card"><div class="num">{{ stats.get('total_resolved',0) }}</div><div class="label">Resolved</div></div>
<div class="stat-card"><div class="num">{{ stats.get('open_cases',0) }}</div><div class="label">Open Cases</div></div>
</div>

<div class="grid">
<div>
<!-- ACCOUNTS -->
<div class="card">
<h2><span class="icon">&#x1F4B3;</span> Registered Accounts</h2>
{% if accounts %}
<table><thead><tr><th>#</th><th>Name</th><th>Institution</th><th>Jurisdiction</th><th>Chain</th><th>Status</th></tr></thead>
<tbody>
{% for a in accounts %}
<tr>
<td>{{ a.id }}</td>
<td>{{ a.name }}</td>
<td>{{ a.institution }}</td>
<td><span class="badge badge-active">{{ a.get('jurisdiction','?') }}</span></td>
<td>
{% if a.get('chain') %}<span class="wallet-info">{{ a.chain }}</span>{% else %}-{% endif %}
</td>
<td>{% if a.get('active') %}<span class="badge badge-active">Active</span>{% else %}<span class="badge badge-inactive">Inactive</span>{% endif %}</td>
</tr>
{% if a.get('wallet_address') %}
<tr><td colspan="6" class="wallet-info">&nbsp;&nbsp;&#x1F4CE; {{ a.wallet_address }}</td></tr>
{% endif %}
{% endfor %}
</tbody></table>
{% else %}<p style="color:var(--muted);font-size:.85rem">No accounts registered yet.</p>{% endif %}
</div>

<!-- REGISTER FORM -->
<div class="card">
<h2><span class="icon">&#x2795;</span> Register Account</h2>
<form method="POST" action="/register">
<div class="form-row">
<input name="name" placeholder="Full name" required>
<input name="institution" placeholder="Institution (e.g. N26)" required>
</div>
<div class="form-row">
<input name="ref" placeholder="Account reference" required>
<select name="atype"><option value="checking">Checking</option><option value="savings">Savings</option><option value="crypto_wallet">Crypto Wallet</option><option value="investment">Investment</option></select>
</div>
<div class="form-row">
<select name="jurisdiction">{% for j in jurisdictions %}<option value="{{ j }}">{{ j }}</option>{% endfor %}</select>
<select name="chain"><option value="">No chain</option>{% for c in chains %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
</div>
<div class="form-row">
<input name="wallet" placeholder="Wallet address (optional)">
</div>
<button type="submit" class="btn btn-primary">Register</button>
</form>
</div>
</div>

<div>
<!-- OPEN CASES -->
<div class="card">
<h2><span class="icon">&#x26A0;&#xFE0F;</span> Open Cases ({{ cases|length }})</h2>
{% if cases %}
<table><thead><tr><th>#</th><th>Type</th><th>Jur</th><th>Tier</th><th>Amount</th><th>Status</th></tr></thead>
<tbody>
{% for c in cases %}
<tr>
<td><a href="/case/{{ c.id }}">{{ c.id }}</a></td>
<td>{{ c.violation_type }}</td>
<td>{{ c.get('jurisdiction','?') }}</td>
<td>{{ c.current_tier }}</td>
<td>{{ c.get('amount_disputed',0) }}</td>
<td>
{% if c.status == 'escalated' or c.status == 'auto_escalated' %}<span class="badge badge-escalated">{{ c.status }}</span>
{% elif 'complaint' in c.status %}<span class="badge badge-drafted">{{ c.status }}</span>
{% else %}<span class="badge badge-open">{{ c.status }}</span>{% endif %}
</td>
</tr>
{% endfor %}
</tbody></table>
{% else %}<p style="color:var(--muted);font-size:.85rem">All quiet — no open cases.</p>{% endif %}
</div>

<!-- REPORT VIOLATION -->
<div class="card">
<h2><span class="icon">&#x1F6A8;</span> Report Violation</h2>
<form method="POST" action="/report">
<div class="form-row">
<select name="account_id">{% for a in accounts %}<option value="{{ a.id }}">#{{ a.id }} {{ a.name }}</option>{% endfor %}</select>
<select name="violation_type">{% for v in violations %}<option value="{{ v }}">{{ v }}</option>{% endfor %}</select>
</div>
<div class="form-row">
<textarea name="description" placeholder="Describe the violation..." required></textarea>
</div>
<div class="form-row">
<input type="number" name="amount" placeholder="Amount disputed" value="0" min="0">
<select name="severity"><option value="1">1 — Low</option><option value="2">2</option><option value="3" selected>3 — Medium</option><option value="4">4</option><option value="5">5 — Critical</option></select>
</div>
<button type="submit" class="btn btn-danger">Report</button>
</form>
</div>
</div>
</div>
</div>
</body></html>
"""

CASE_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Case #{{ case.id }} — AdvocateOS</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2a2d3a;--accent:#6366f1;--accent2:#818cf8;
--green:#22c55e;--red:#ef4444;--yellow:#eab308;--text:#e2e8f0;--muted:#94a3b8;--font:'Segoe UI',system-ui,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh}
a{color:var(--accent2);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:1000px;margin:0 auto;padding:1rem}
header{background:linear-gradient(135deg,#1e1b4b,#312e81);padding:1.5rem 0;border-bottom:1px solid var(--border);margin-bottom:1.5rem}
header .container{display:flex;justify-content:space-between;align-items:center}
h1{font-size:1.5rem;font-weight:700}h1 span{color:var(--accent2)}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:.75rem;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge-open{background:#eab30822;color:var(--yellow)}.badge-resolved{background:#22c55e22;color:var(--green)}
.badge-escalated{background:#f9731533;color:#f97315}.badge-drafted{background:#6366f122;color:var(--accent2)}
.card{background:var(--card);border:1px solid var(--border);border-radius:.75rem;padding:1.25rem;margin-bottom:1rem}
.card h2{font-size:1.05rem;margin-bottom:.75rem}.meta{color:var(--muted);font-size:.8rem}
.mono{font-family:'Cascadia Code',monospace;font-size:.8rem;color:var(--muted)}
button,.btn{padding:.5rem 1rem;border-radius:.5rem;font-size:.85rem;font-weight:600;cursor:pointer;border:none;transition:all .2s}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{background:var(--accent2)}
.btn-danger{background:var(--red);color:#fff}.btn-success{background:var(--green);color:#fff}
.btn-sm{padding:.3rem .6rem;font-size:.75rem}
.form-row{display:flex;gap:.5rem;margin-bottom:.5rem;flex-wrap:wrap}
.form-row input,.form-row textarea{flex:1;padding:.5rem;border-radius:.5rem;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:.85rem}
.form-row textarea{min-height:60px}
.flash{padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;font-size:.85rem}
.flash-success{background:#22c55e22;border:1px solid #22c55e44;color:var(--green)}
.flash-error{background:#ef444422;border:1px solid #ef444444;color:var(--red)}
.timeline{position:relative;padding-left:2rem;margin:1rem 0}
.timeline::before{content:'';position:absolute;left:.6rem;top:0;bottom:0;width:2px;background:var(--border)}
.tl-item{position:relative;margin-bottom:1.25rem;padding-left:.5rem}
.tl-item::before{content:'';position:absolute;left:-1.65rem;top:.4rem;width:10px;height:10px;border-radius:50%;border:2px solid var(--accent)}
.tl-item.current::before{background:var(--accent)}
.tl-item.completed::before{background:var(--green);border-color:var(--green)}
.tl-item .tl-label{font-size:.85rem;font-weight:600}.tl-item .tl-meta{font-size:.75rem;color:var(--muted)}
.complaint-box{background:var(--bg);border:1px solid var(--border);border-radius:.5rem;padding:1rem;margin:.75rem 0;font-size:.85rem;white-space:pre-wrap;max-height:400px;overflow-y:auto}
.actions{display:flex;gap:.5rem;margin-top:1rem;flex-wrap:wrap}
.nav-links{display:flex;gap:1rem;font-size:.85rem}
</style>
</head>
<body>
<header><div class="container">
<h1>&#x1F6E1; Advocate<span>OS</span></h1>
<div class="nav-links">
<a href="/">Dashboard</a>
<a href="/cases/all">All Cases</a>
</div>
</div></header>

<div class="container">
{% with messages = get_flashed_messages(with_categories=true) %}{% for cat,msg in messages %}
<div class="flash flash-{{ cat }}">{{ msg }}</div>
{% endfor %}{% endwith %}

<div class="card">
<h2>Case #{{ case.id }} — {{ case.violation_type }}
{% set st = case.status %}
{% if st == 'resolved' %}<span class="badge badge-resolved">{{ st }}</span>
{% elif 'escalat' in st %}<span class="badge badge-escalated">{{ st }}</span>
{% elif 'complaint' in st %}<span class="badge badge-drafted">{{ st }}</span>
{% else %}<span class="badge badge-open">{{ st }}</span>{% endif %}
</h2>
<p>{{ case.description }}</p>
<div class="meta" style="margin-top:.5rem">
Jurisdiction: <strong>{{ case.get('jurisdiction','?') }}</strong> |
Amount: <strong>{{ case.get('amount_disputed',0) }}</strong> |
Severity: <strong>{{ case.get('severity','?') }}/5</strong> |
Tier: <strong>{{ case.current_tier }}</strong>
{% if account %} | Account: <strong>{{ account.get('name','?') }} @ {{ account.get('institution','?') }}</strong>{% endif %}
</div>

{% if case.status != 'resolved' %}
<div class="actions">
<form method="POST" action="/draft/{{ case.id }}"><button class="btn btn-primary btn-sm">Draft Complaint</button></form>
<form method="POST" action="/escalate/{{ case.id }}"><button class="btn btn-danger btn-sm">Escalate</button></form>
</div>
{% endif %}
</div>

<!-- ESCALATION TIMELINE -->
{% if path and path.get('path') %}
<div class="card">
<h2>&#x1F4C8; Escalation Timeline</h2>
<div class="timeline">
{% for step in path.path %}
<div class="tl-item {{ step.status }}">
<div class="tl-label">Tier {{ step.tier }}: {{ step.body }}</div>
<div class="tl-meta">Deadline: {{ step.deadline_days }} days | {{ step.status|upper }}</div>
</div>
{% endfor %}
</div>
{% if path.get('history') %}
<div class="meta" style="margin-top:.5rem">
{% for h in path.history %}
<div>&#x27A1;&#xFE0F; {{ h.get('from_body','?') }} &rarr; {{ h.get('to_body','?') }}: {{ h.get('reason','') }}</div>
{% endfor %}
</div>
{% endif %}
</div>
{% endif %}

<!-- COMPLAINTS -->
{% set complaints = case.get('complaints', []) %}
{% if complaints %}
<div class="card">
<h2>&#x1F4DD; Complaints ({{ complaints|length }})</h2>
{% for comp in complaints %}
<div style="margin-bottom:1rem">
<div class="meta">Tier {{ comp.get('tier','?') }} | {{ comp.get('subject','No subject') }}</div>
<div class="complaint-box">{{ comp.get('body','') }}</div>
{% if comp.get('legal_clauses_cited') %}
<div class="meta">Legal clauses: {{ comp.legal_clauses_cited|join(', ') }}</div>
{% endif %}
{% if comp.get('remedy_sought') %}
<div class="meta">Remedy: {{ comp.remedy_sought }}</div>
{% endif %}
</div>
{% endfor %}
</div>
{% endif %}

<!-- RESPONSE ANALYSES -->
{% set analyses = case.get('response_analyses', []) %}
{% if analyses %}
<div class="card">
<h2>&#x1F50D; Institution Response Analyses</h2>
{% for ra in analyses %}
<div style="margin-bottom:.75rem">
<p><strong>Recommendation:</strong> {{ ra.get('recommendation','?') }}</p>
<p class="meta">Acknowledged: {{ ra.get('acknowledged','?') }} | Remedy offered: {{ ra.get('remedy_offered','?') }} | Adequate: {{ ra.get('remedy_adequate','?') }}</p>
<p class="meta">{{ ra.get('summary','') }}</p>
</div>
{% endfor %}
</div>
{% endif %}

<!-- RESOLVE FORM (if not resolved) -->
{% if case.status != 'resolved' %}
<div class="card">
<h2>&#x2705; Resolve Case</h2>
<form method="POST" action="/resolve/{{ case.id }}">
<div class="form-row">
<textarea name="note" placeholder="Resolution note..." required></textarea>
</div>
<div class="form-row">
<input type="number" name="amount" placeholder="Amount recovered" value="0" min="0">
<button type="submit" class="btn btn-success">Resolve</button>
</div>
</form>
</div>
{% endif %}

<!-- RESOLUTION INFO (if resolved) -->
{% if case.status == 'resolved' %}
<div class="card">
<h2>&#x2705; Resolution</h2>
<p>{{ case.get('resolution_note', 'No note') }}</p>
<div class="meta">Amount recovered: {{ case.get('amount_recovered', 0) }}</div>
</div>
{% endif %}

</div>
</body></html>
"""

ALL_CASES_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>All Cases — AdvocateOS</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--border:#2a2d3a;--accent:#6366f1;--accent2:#818cf8;
--green:#22c55e;--red:#ef4444;--yellow:#eab308;--text:#e2e8f0;--muted:#94a3b8;--font:'Segoe UI',system-ui,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh}
a{color:var(--accent2);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:1000px;margin:0 auto;padding:1rem}
header{background:linear-gradient(135deg,#1e1b4b,#312e81);padding:1.5rem 0;border-bottom:1px solid var(--border);margin-bottom:1.5rem}
header .container{display:flex;justify-content:space-between;align-items:center}
h1{font-size:1.5rem;font-weight:700}h1 span{color:var(--accent2)}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:.75rem;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge-open{background:#eab30822;color:var(--yellow)}.badge-resolved{background:#22c55e22;color:var(--green)}
.badge-escalated{background:#f9731533;color:#f97315}.badge-drafted{background:#6366f122;color:var(--accent2)}
.card{background:var(--card);border:1px solid var(--border);border-radius:.75rem;padding:1.25rem;margin-bottom:1rem}
table{width:100%;border-collapse:collapse;font-size:.85rem}th,td{padding:.5rem .6rem;text-align:left;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
.nav-links{display:flex;gap:1rem;font-size:.85rem}
</style>
</head>
<body>
<header><div class="container">
<h1>&#x1F6E1; Advocate<span>OS</span></h1>
<div class="nav-links"><a href="/">Dashboard</a><a href="/cases/all">All Cases</a></div>
</div></header>
<div class="container">
<div class="card">
<h2>All Cases ({{ cases|length }})</h2>
{% if cases %}
<table><thead><tr><th>#</th><th>Type</th><th>Jurisdiction</th><th>Tier</th><th>Amount</th><th>Severity</th><th>Status</th></tr></thead>
<tbody>
{% for c in cases %}
<tr>
<td><a href="/case/{{ c.id }}">{{ c.id }}</a></td>
<td>{{ c.violation_type }}</td>
<td>{{ c.get('jurisdiction','?') }}</td>
<td>{{ c.current_tier }}</td>
<td>{{ c.get('amount_disputed',0) }}</td>
<td>{{ c.get('severity','?') }}</td>
<td>
{% set st = c.status %}
{% if st == 'resolved' %}<span class="badge badge-resolved">{{ st }}</span>
{% elif 'escalat' in st %}<span class="badge badge-escalated">{{ st }}</span>
{% elif 'complaint' in st %}<span class="badge badge-drafted">{{ st }}</span>
{% else %}<span class="badge badge-open">{{ st }}</span>{% endif %}
</td>
</tr>
{% endfor %}
</tbody></table>
{% else %}<p style="color:var(--muted)">No cases recorded yet.</p>{% endif %}
</div>
</div>
</body></html>
"""


if __name__ == "__main__":
    if not GL_PATH:
        print("ERROR: genlayer CLI not found. Install it first.")
        sys.exit(1)
    print(f"\n  AdvocateOS Dashboard")
    print(f"  Contract: {CONTRACT_ADDRESS}")
    print(f"  Open http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
