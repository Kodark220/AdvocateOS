"""
AdvocateOS Dashboard — Professional B&W Web Frontend

Run:  py dashboard_new.py
Then open http://127.0.0.1:5000
"""

import subprocess
import shutil
import json
import os
import sys
import time
import logging
try:
    import fcntl
except ImportError:
    fcntl = None  # Windows — no file locking needed for single-process dev
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── CONFIG ──

NETWORKS = {
    "bradbury": {
        "contract": os.environ.get("AOS_CONTRACT_BRADBURY",
                                   os.environ.get("AOS_CONTRACT", "0x2e75bc5796791b20b645b17dcf2a9dfc052c83ab")),
        "rpc": "https://rpc-bradbury.genlayer.com",
        "cli_network": "testnet-bradbury",
        "label": "Bradbury Testnet",
    },
    "studionet": {
        "contract": os.environ.get("AOS_CONTRACT_STUDIONET", "0x5b1C73fb7F1df7081126bF473eB40FfE77F05DFb"),
        "rpc": "https://studio.genlayer.com/api",
        "cli_network": "studionet",
        "label": "Studionet",
    },
}

DEFAULT_NETWORK = os.environ.get("AOS_DEFAULT_NETWORK", "studionet")
CONTRACT_ADDRESS = NETWORKS[DEFAULT_NETWORK]["contract"]
GL_PATH = os.environ.get("AOS_GL_PATH") or shutil.which("genlayer")
WRITE_TIMEOUT = int(os.environ.get("AOS_WRITE_TIMEOUT", "600"))
READ_TIMEOUT = int(os.environ.get("AOS_READ_TIMEOUT", "60"))
PROBE_TIMEOUT = int(os.environ.get("AOS_PROBE_TIMEOUT", "15"))
KEYSTORE_PASSWORD = os.environ.get("AOS_KEYSTORE_PASSWORD", "")

# Network status cache: { "bradbury": {"online": True/False, "checked_at": timestamp} }
_network_status = {}

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
app.secret_key = os.environ.get("AOS_SECRET_KEY", os.urandom(24).hex())

# CORS — allow frontend origin in production
ALLOWED_ORIGINS = os.environ.get("AOS_CORS_ORIGINS", "*").split(",")
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})


# ── GENLAYER CLI HELPERS ──

def _resolve_network():
    """Get network key from ?network= query param, default to DEFAULT_NETWORK."""
    net = request.args.get("network", DEFAULT_NETWORK).lower()
    if net not in NETWORKS:
        net = DEFAULT_NETWORK
    return net


def _get_contract(network=None):
    """Return contract address for the given network."""
    net = network or DEFAULT_NETWORK
    return NETWORKS[net]["contract"]


def _get_rpc(network=None):
    """Return RPC URL for the given network."""
    net = network or DEFAULT_NETWORK
    return NETWORKS[net]["rpc"]


def _probe_network(net):
    """Quick probe: try a fast get_stats call with short timeout. Cache result for 60s."""
    now = time.time()
    cached = _network_status.get(net)
    if cached and now - cached["checked_at"] < 60:
        return cached["online"]
    contract = _get_contract(net)
    rpc = _get_rpc(net)
    if not contract:
        _network_status[net] = {"online": False, "checked_at": now}
        return False
    cmd = [GL_PATH, "call", "--rpc", rpc, contract, "get_stats"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=PROBE_TIMEOUT)
        # Check stdout first to avoid false negatives from stderr warnings like [genlayer-js]
        online = any(
            s.strip().startswith("{")
            for s in r.stdout.split("\n")
            if s.strip()
        )
        _network_status[net] = {"online": online, "checked_at": now}
        if online:
            logging.info("probe %s: online", net)
        else:
            logging.warning("probe %s: no JSON (exit %d)", net, r.returncode)
        return online
    except subprocess.TimeoutExpired:
        logging.warning("probe %s: timeout after %ds", net, PROBE_TIMEOUT)
        _network_status[net] = {"online": False, "checked_at": now}
        return False
    except Exception as e:
        logging.error("probe %s: %s", net, e)
        _network_status[net] = {"online": False, "checked_at": now}
        return False


def _is_network_online(net):
    """Check cached status without probing. Returns None if never probed."""
    cached = _network_status.get(net)
    if cached and time.time() - cached["checked_at"] < 120:
        return cached["online"]
    return None


def gl_call(method, *args, network=None):
    net = network or DEFAULT_NETWORK
    contract = _get_contract(net)
    rpc = _get_rpc(net)
    if not contract:
        return None
    # If we know the network is offline, skip the slow call
    status = _is_network_online(net)
    if status is False:
        logging.info("gl_call %s on %s: skipped (network offline)", method, net)
        return None
    cmd = [GL_PATH, "call", "--rpc", rpc, contract, method]
    for a in args:
        cmd += ["--args", str(a)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=READ_TIMEOUT)
        # Parse stdout first (stderr may contain deprecation warnings starting with '[')
        for source in (r.stdout, r.stderr):
            for line in source.split("\n"):
                s = line.strip()
                if not s or len(s) < 2:
                    continue
                if s.startswith("{") or s.startswith("["):
                    try:
                        parsed = json.loads(s)
                        _network_status[net] = {"online": True, "checked_at": time.time()}
                        return parsed
                    except json.JSONDecodeError:
                        continue
        logging.warning("gl_call %s on %s: no JSON in output", method, net)
        _network_status[net] = {"online": False, "checked_at": time.time()}
    except subprocess.TimeoutExpired:
        logging.error("gl_call %s on %s: timeout after %ds", method, net, READ_TIMEOUT)
        _network_status[net] = {"online": False, "checked_at": time.time()}
    except Exception as e:
        logging.error("gl_call %s on %s: %s", method, net, e)
    return None


def gl_write(method, *args, network=None):
    net = network or DEFAULT_NETWORK
    contract = _get_contract(net)
    rpc = _get_rpc(net)
    cli_network = NETWORKS[net]["cli_network"]
    if not contract:
        return False
    try:
        # File lock to prevent race conditions between Gunicorn workers
        lock_fd = None
        if fcntl:
            lock_fd = open("/tmp/genlayer_cli.lock", "w")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            # Switch to the correct network (needed for consensus contract resolution)
            subprocess.run([GL_PATH, "network", "set", cli_network],
                           capture_output=True, text=True, timeout=10)
            cmd = [GL_PATH, "write", "--rpc", rpc, contract, method]
            for a in args:
                cmd += ["--args", str(a)]
            r = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            if KEYSTORE_PASSWORD:
                r.stdin.write((KEYSTORE_PASSWORD + "\n").encode())
                r.stdin.flush()
        finally:
            if lock_fd and fcntl:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
        # Wait briefly for the tx to be submitted, then release
        # Don't wait for full consensus — just confirm submission
        try:
            stdout, stderr = r.communicate(timeout=30)
            output = (stdout + stderr).decode("utf-8", errors="replace")
            if "Transaction Hash" in output:
                logging.info("gl_write %s on %s: tx submitted", method, net)
                return True
            logging.error("gl_write %s on %s: %s", method, net, output[:500])
            return False
        except subprocess.TimeoutExpired:
            # TX submitted but consensus still pending — that's OK
            logging.info("gl_write %s on %s: timeout waiting for consensus (tx likely submitted)", method, net)
            r.kill()
            r.communicate()
            return True
        return True
    except Exception as e:
        logging.error("gl_write %s on %s: %s", method, net, e)
        return False


# ── LAYOUT ──

def page(title, content, active="dashboard"):
    return render_template_string(
        BASE_HTML,
        page_title=title,
        page_content=content,
        active=active,
        contract=CONTRACT_ADDRESS,
    )


# ── ROUTES ──

@app.route("/")
def index():
    stats = gl_call("get_stats") or {}
    accounts = gl_call("get_all_accounts") or []
    open_cases = gl_call("get_open_cases") or []

    # Build chart data
    total_v = stats.get("total_violations", 0)
    all_cases = []
    status_counts = {"open": 0, "complaint_drafted": 0, "escalated": 0, "resolved": 0}
    for i in range(1, total_v + 1):
        c = gl_call("get_case", str(i))
        if c and isinstance(c, dict):
            all_cases.append(c)
            st = c.get("status", "open")
            if st in status_counts:
                status_counts[st] += 1
            elif "escalat" in st:
                status_counts["escalated"] += 1
            elif "complaint" in st:
                status_counts["complaint_drafted"] += 1
            else:
                status_counts["open"] += 1

    # Violation type distribution
    vtype_counts = {}
    for c in all_cases:
        vt = c.get("violation_type", "unknown")
        vtype_counts[vt] = vtype_counts.get(vt, 0) + 1

    content = render_template_string(INDEX_CONTENT,
        stats=stats, accounts=accounts, cases=open_cases,
        all_cases=all_cases,
        status_counts=status_counts,
        vtype_counts=vtype_counts,
        chains=SUPPORTED_CHAINS, violations=VIOLATION_TYPES,
        jurisdictions=list(JURISDICTION_TIERS.keys()),
    )
    return page("Dashboard", content, "dashboard")


@app.route("/accounts")
def accounts_page():
    accounts = gl_call("get_all_accounts") or []
    content = render_template_string(ACCOUNTS_CONTENT,
        accounts=accounts,
        chains=SUPPORTED_CHAINS,
        jurisdictions=list(JURISDICTION_TIERS.keys()),
    )
    return page("Accounts", content, "accounts")


@app.route("/cases/all")
def all_cases():
    stats = gl_call("get_stats") or {}
    total = stats.get("total_violations", 0)
    cases = []
    for i in range(1, total + 1):
        c = gl_call("get_case", str(i))
        if c and isinstance(c, dict):
            cases.append(c)
    content = render_template_string(CASES_CONTENT, cases=cases)
    return page("All Cases", content, "cases")


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
    content = render_template_string(CASE_DETAIL_CONTENT,
        case=case, path=path, account=acc,
        tiers=JURISDICTION_TIERS,
    )
    return page(f"Case #{case_id}", content, "cases")


@app.route("/report-page")
def report_page():
    accounts = gl_call("get_all_accounts") or []
    content = render_template_string(REPORT_CONTENT,
        accounts=accounts,
        violations=VIOLATION_TYPES,
    )
    return page("Report Violation", content, "report")


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
        return redirect(url_for("accounts_page"))
    ok = gl_write("register_account", name, institution, ref, atype, jur, chain)
    flash("Account registered successfully." if ok else "Registration failed — consensus issue.", "success" if ok else "error")
    return redirect(url_for("accounts_page"))


@app.route("/report", methods=["POST"])
def report():
    aid = request.form.get("account_id", "")
    vtype = request.form.get("violation_type", "")
    desc = request.form.get("description", "").strip()
    amount = request.form.get("amount", "0")
    severity = request.form.get("severity", "3")
    if not all([aid, vtype, desc]):
        flash("All fields required", "error")
        return redirect(url_for("report_page"))
    ok = gl_write("report_violation", aid, vtype, desc, amount, severity)
    flash("Violation reported successfully." if ok else "Report failed.", "success" if ok else "error")
    return redirect(url_for("all_cases"))


@app.route("/draft/<int:case_id>", methods=["POST"])
def draft(case_id):
    ok = gl_write("draft_complaint", str(case_id))
    flash(f"Complaint drafted for case #{case_id}." if ok else "Drafting failed.", "success" if ok else "error")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/escalate/<int:case_id>", methods=["POST"])
def escalate(case_id):
    ok = gl_write("escalate", str(case_id))
    flash(f"Case #{case_id} escalated." if ok else "Escalation failed.", "success" if ok else "error")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/resolve/<int:case_id>", methods=["POST"])
def resolve(case_id):
    note = request.form.get("note", "").strip()
    amount = request.form.get("amount", "0")
    ok = gl_write("resolve_case", str(case_id), note, amount)
    flash(f"Case #{case_id} resolved." if ok else "Resolution failed.", "success" if ok else "error")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/api/health")
def api_health():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "cli": bool(GL_PATH), "networks": list(NETWORKS.keys())})


@app.route("/api/networks")
def api_networks():
    """Return available networks with online status."""
    nets = {}
    for k, v in NETWORKS.items():
        cached = _network_status.get(k)
        online = cached["online"] if cached and time.time() - cached["checked_at"] < 120 else None
        nets[k] = {
            "label": v["label"],
            "hasContract": bool(v["contract"]),
            "online": online,  # True, False, or null (unknown)
        }
    return jsonify({"networks": nets, "default": DEFAULT_NETWORK})


@app.route("/api/networks/status")
def api_networks_status():
    """Probe all networks and return live status. May take a few seconds."""
    results = {}
    for k in NETWORKS:
        online = _probe_network(k)
        results[k] = {"online": online, "label": NETWORKS[k]["label"]}
    return jsonify(results)


@app.route("/api/stats")
def api_stats():
    net = _resolve_network()
    result = gl_call("get_stats", network=net)
    if result is None:
        return jsonify({"error": "network_unavailable", "network": net, "message": f"{NETWORKS[net]['label']} is currently unreachable"}), 503
    return jsonify(result)


@app.route("/api/accounts")
def api_accounts():
    net = _resolve_network()
    result = gl_call("get_all_accounts", network=net)
    if result is None:
        return jsonify({"error": "network_unavailable", "network": net, "message": f"{NETWORKS[net]['label']} is currently unreachable"}), 503
    return jsonify(result)


@app.route("/api/wallet/<address>")
def api_wallet_accounts(address):
    """Check if a wallet address has any registered accounts."""
    net = _resolve_network()
    all_accounts = gl_call("get_all_accounts", network=net)
    if all_accounts is None:
        return jsonify({"accounts": [], "registered": False, "error": "network_unavailable", "network": net})
    matched = [
        a for a in all_accounts
        if isinstance(a, dict) and a.get("wallet_address", "").lower() == address.lower()
    ]
    return jsonify({"accounts": matched, "registered": len(matched) > 0})


@app.route("/api/cases/open")
def api_open_cases():
    net = _resolve_network()
    result = gl_call("get_open_cases", network=net)
    if result is None:
        return jsonify({"error": "network_unavailable", "network": net, "message": f"{NETWORKS[net]['label']} is currently unreachable"}), 503
    return jsonify(result)


@app.route("/api/cases")
def api_all_cases():
    net = _resolve_network()
    stats = gl_call("get_stats", network=net)
    if stats is None:
        return jsonify({"error": "network_unavailable", "network": net, "message": f"{NETWORKS[net]['label']} is currently unreachable"}), 503
    total = stats.get("total_violations", 0)
    cases = []
    for i in range(1, total + 1):
        c = gl_call("get_case", str(i), network=net)
        if c and isinstance(c, dict):
            cases.append(c)
    return jsonify(cases)


@app.route("/api/case/<int:case_id>")
def api_case(case_id):
    net = _resolve_network()
    case = gl_call("get_case", str(case_id), network=net)
    if not case or not isinstance(case, dict):
        return jsonify({"error": "not found"}), 404
    return jsonify(case)


@app.route("/api/case/<int:case_id>/path")
def api_case_path(case_id):
    net = _resolve_network()
    return jsonify(gl_call("get_escalation_path", str(case_id), network=net) or {})


@app.route("/api/register", methods=["POST"])
def api_register():
    d = request.get_json(force=True) or {}
    net = d.get("network", DEFAULT_NETWORK)
    name = d.get("name", "").strip()
    institution = d.get("institution", "").strip()
    ref = d.get("ref", "").strip()
    atype = d.get("atype", "").strip()
    jur = d.get("jurisdiction", "US")
    wallet = d.get("wallet", "").strip()
    chain = d.get("chain", "")
    if not all([name, institution, ref, atype]):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    ok = gl_write("register_account", name, institution, ref, atype, jur, chain, network=net)
    return jsonify({"ok": ok})


@app.route("/api/report", methods=["POST"])
def api_report():
    d = request.get_json(force=True) or {}
    net = d.get("network", DEFAULT_NETWORK)
    aid = d.get("account_id", "")
    vtype = d.get("violation_type", "")
    desc = d.get("description", "").strip()
    amount = d.get("amount", "0")
    severity = d.get("severity", "3")
    if not all([aid, vtype, desc]):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    ok = gl_write("report_violation", str(aid), vtype, desc, str(amount), str(severity), network=net)
    return jsonify({"ok": ok})


@app.route("/api/draft/<int:case_id>", methods=["POST"])
def api_draft(case_id):
    d = request.get_json(force=True) or {}
    net = d.get("network", DEFAULT_NETWORK)
    ok = gl_write("draft_complaint", str(case_id), network=net)
    return jsonify({"ok": ok})


@app.route("/api/escalate/<int:case_id>", methods=["POST"])
def api_escalate(case_id):
    d = request.get_json(force=True) or {}
    net = d.get("network", DEFAULT_NETWORK)
    ok = gl_write("escalate", str(case_id), network=net)
    return jsonify({"ok": ok})


@app.route("/api/resolve/<int:case_id>", methods=["POST"])
def api_resolve(case_id):
    d = request.get_json(force=True) or {}
    net = d.get("network", DEFAULT_NETWORK)
    note = d.get("note", "").strip()
    amount = d.get("amount", "0")
    ok = gl_write("resolve_case", str(case_id), note, str(amount), network=net)
    return jsonify({"ok": ok})


# ═══════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════

BASE_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ page_title }} — AdvocateOS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
/* ── RESET & BASE ── */
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html{font-size:14px}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#fafafa;color:#111827;
min-height:100vh;display:flex;-webkit-font-smoothing:antialiased}

/* ── SIDEBAR ── */
.sidebar{position:fixed;top:0;left:0;bottom:0;width:260px;background:#000;color:#fff;
display:flex;flex-direction:column;z-index:100;transition:transform .3s}
.sidebar-header{padding:28px 24px 20px;border-bottom:1px solid #1a1a1a}
.sidebar-logo{font-size:20px;font-weight:700;letter-spacing:-.5px;display:flex;align-items:center;gap:10px}
.sidebar-logo svg{flex-shrink:0}
.sidebar-sub{font-size:11px;color:#666;margin-top:4px;letter-spacing:.5px;text-transform:uppercase}
.sidebar-nav{flex:1;padding:16px 0;overflow-y:auto}
.nav-section{padding:0 24px;margin-bottom:4px;margin-top:16px;font-size:10px;font-weight:600;
color:#555;text-transform:uppercase;letter-spacing:1px}
.nav-section:first-child{margin-top:8px}
.nav-item{display:flex;align-items:center;gap:12px;padding:10px 24px;font-size:13px;font-weight:500;
color:#999;text-decoration:none;transition:all .15s;border-left:3px solid transparent;cursor:pointer}
.nav-item:hover{color:#fff;background:#111;border-left-color:#333}
.nav-item.active{color:#fff;background:#111;border-left-color:#fff}
.nav-item svg{width:18px;height:18px;flex-shrink:0;opacity:.6}
.nav-item.active svg,.nav-item:hover svg{opacity:1}
.sidebar-footer{padding:16px 24px;border-top:1px solid #1a1a1a;font-size:11px;color:#444}
.sidebar-footer .addr{font-family:'SF Mono',SFMono-Regular,Consolas,monospace;font-size:10px;
color:#555;word-break:break-all;margin-top:4px}
.sidebar-footer .net{display:inline-block;padding:2px 8px;background:#1a1a1a;border-radius:10px;
font-size:10px;color:#666;margin-top:8px}

/* ── MAIN ── */
.main{margin-left:260px;flex:1;min-height:100vh}
.topbar{position:sticky;top:0;z-index:50;background:rgba(250,250,250,.85);
backdrop-filter:blur(12px);border-bottom:1px solid #e5e7eb;padding:0 32px;height:56px;
display:flex;align-items:center;justify-content:space-between}
.topbar h1{font-size:16px;font-weight:600;color:#111827}
.topbar-right{display:flex;align-items:center;gap:16px;font-size:12px;color:#9ca3af}
.content{padding:28px 32px}

/* ── FLASH ── */
.flash{padding:12px 16px;border-radius:8px;margin-bottom:20px;font-size:13px;font-weight:500;
display:flex;align-items:center;gap:8px}
.flash-success{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534}
.flash-error{background:#fef2f2;border:1px solid #fecaca;color:#991b1b}

/* ── STATS GRID ── */
.stats-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-bottom:28px}
@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:700px){.stats-grid{grid-template-columns:repeat(2,1fr)}}
.stat-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px 22px;transition:box-shadow .2s}
.stat-card:hover{box-shadow:0 4px 24px rgba(0,0,0,.06)}
.stat-label{font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.stat-num{font-size:32px;font-weight:700;color:#111827;line-height:1}
.stat-sub{font-size:11px;color:#9ca3af;margin-top:6px}

/* ── CARDS ── */
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;margin-bottom:20px;overflow:hidden}
.card-header{padding:18px 22px;border-bottom:1px solid #f3f4f6;display:flex;
align-items:center;justify-content:space-between}
.card-header h2{font-size:14px;font-weight:600;color:#111827;display:flex;align-items:center;gap:8px}
.card-header .count{display:inline-flex;align-items:center;justify-content:center;
min-width:22px;height:22px;background:#f3f4f6;border-radius:11px;font-size:11px;
font-weight:600;color:#6b7280;padding:0 7px}
.card-body{padding:22px}
.card-body.no-pad{padding:0}

/* ── TABLES ── */
table{width:100%;border-collapse:collapse}
thead th{padding:10px 16px;font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;
letter-spacing:.5px;text-align:left;background:#fafafa;border-bottom:1px solid #e5e7eb}
tbody td{padding:12px 16px;font-size:13px;color:#374151;border-bottom:1px solid #f3f4f6;vertical-align:middle}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:#fafafa}
.cell-mono{font-family:'SF Mono',SFMono-Regular,Consolas,monospace;font-size:12px;color:#6b7280}

/* ── BADGES ── */
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:100px;
font-size:11px;font-weight:600;text-transform:capitalize}
.badge::before{content:'';width:6px;height:6px;border-radius:50%}
.badge-open{background:#fef3c7;color:#92400e}.badge-open::before{background:#f59e0b}
.badge-drafted{background:#f3f4f6;color:#374151}.badge-drafted::before{background:#6b7280}
.badge-escalated{background:#fef2f2;color:#991b1b}.badge-escalated::before{background:#ef4444}
.badge-resolved{background:#f0fdf4;color:#166534}.badge-resolved::before{background:#22c55e}
.badge-active{background:#f0fdf4;color:#166534}.badge-active::before{background:#22c55e}
.badge-inactive{background:#f3f4f6;color:#6b7280}.badge-inactive::before{background:#9ca3af}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;
font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all .15s;text-decoration:none}
.btn-primary{background:#111827;color:#fff}.btn-primary:hover{background:#000}
.btn-outline{background:#fff;color:#374151;border:1px solid #d1d5db}.btn-outline:hover{background:#f9fafb;border-color:#9ca3af}
.btn-danger{background:#111827;color:#fff}.btn-danger:hover{background:#000}
.btn-sm{padding:6px 12px;font-size:12px}
.btn-ghost{background:transparent;color:#6b7280;padding:6px 10px}.btn-ghost:hover{color:#111827;background:#f3f4f6}

/* ── FORMS ── */
.form-group{margin-bottom:16px}
.form-label{display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:6px}
.form-input,.form-select,.form-textarea{width:100%;padding:9px 12px;border:1px solid #d1d5db;
border-radius:8px;font-size:13px;font-family:inherit;color:#111827;background:#fff;transition:border-color .15s}
.form-input:focus,.form-select:focus,.form-textarea:focus{outline:none;border-color:#111827;box-shadow:0 0 0 3px rgba(0,0,0,.08)}
.form-textarea{min-height:80px;resize:vertical}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:600px){.form-row{grid-template-columns:1fr}}
.form-hint{font-size:11px;color:#9ca3af;margin-top:4px}

/* ── GRID ── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid-3{display:grid;grid-template-columns:2fr 1fr;gap:20px}
@media(max-width:900px){.grid-2,.grid-3{grid-template-columns:1fr}}

/* ── TIMELINE ── */
.timeline{position:relative;padding-left:28px}
.timeline::before{content:'';position:absolute;left:8px;top:4px;bottom:4px;width:1px;background:#e5e7eb}
.tl-step{position:relative;padding-bottom:24px}
.tl-step:last-child{padding-bottom:0}
.tl-dot{position:absolute;left:-24px;top:4px;width:12px;height:12px;border-radius:50%;
border:2px solid #d1d5db;background:#fff}
.tl-step.current .tl-dot{border-color:#111827;background:#111827}
.tl-step.completed .tl-dot{border-color:#22c55e;background:#22c55e}
.tl-step.pending .tl-dot{border-color:#e5e7eb;background:#f9fafb}
.tl-title{font-size:13px;font-weight:600;color:#111827}
.tl-meta{font-size:12px;color:#9ca3af;margin-top:2px}

/* ── COMPLAINT BOX ── */
.complaint{background:#fafafa;border:1px solid #e5e7eb;border-radius:8px;padding:16px 18px;
margin:12px 0;font-size:13px;line-height:1.7;color:#374151;white-space:pre-wrap;
max-height:320px;overflow-y:auto}
.complaint-tier{display:inline-flex;align-items:center;justify-content:center;
width:24px;height:24px;background:#111827;color:#fff;border-radius:6px;font-size:11px;font-weight:700}

/* ── CHART CONTAINER ── */
.chart-wrap{position:relative;height:220px}

/* ── META ── */
.meta{font-size:12px;color:#6b7280}
.meta strong{color:#374151}
.mono{font-family:'SF Mono',SFMono-Regular,Consolas,monospace}
.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;display:inline-block}
.divider{height:1px;background:#e5e7eb;margin:20px 0}
a{color:#111827;text-decoration:none}
a:hover{text-decoration:underline}
.link{color:#111827;font-weight:600}
.empty-state{text-align:center;padding:40px 20px;color:#9ca3af}
.empty-state .empty-icon{font-size:32px;margin-bottom:12px;opacity:.4}
.empty-state p{font-size:13px}

/* ── MOBILE TOGGLE ── */
.mobile-toggle{display:none;background:none;border:none;cursor:pointer;padding:8px}
@media(max-width:768px){
  .sidebar{transform:translateX(-100%)}
  .sidebar.open{transform:translateX(0)}
  .main{margin-left:0}
  .mobile-toggle{display:block}
}
</style>
</head>
<body>

<!-- SIDEBAR -->
<aside class="sidebar" id="sidebar">
<div class="sidebar-header">
  <div class="sidebar-logo">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
    AdvocateOS
  </div>
  <div class="sidebar-sub">Consumer Protection Agent</div>
</div>

<nav class="sidebar-nav">
  <div class="nav-section">Overview</div>
  <a href="/" class="nav-item {{ 'active' if active=='dashboard' }}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
    Dashboard
  </a>

  <div class="nav-section">Management</div>
  <a href="/accounts" class="nav-item {{ 'active' if active=='accounts' }}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
    Accounts
  </a>
  <a href="/cases/all" class="nav-item {{ 'active' if active=='cases' }}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
    Cases
  </a>

  <div class="nav-section">Actions</div>
  <a href="/report-page" class="nav-item {{ 'active' if active=='report' }}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    Report Violation
  </a>
</nav>

<div class="sidebar-footer">
  <div style="color:#666;font-weight:600">Contract</div>
  <div class="addr">{{ contract }}</div>
  <div class="net">Bradbury Testnet</div>
</div>
</aside>

<!-- MAIN -->
<main class="main">
<div class="topbar">
  <div style="display:flex;align-items:center;gap:12px">
    <button class="mobile-toggle" onclick="document.getElementById('sidebar').classList.toggle('open')">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#111827" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
    <h1>{{ page_title }}</h1>
  </div>
  <div class="topbar-right">
    <span class="mono" style="font-size:11px">GenLayer Protocol</span>
  </div>
</div>

<div class="content">
  {% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat, msg in messages %}
  <div class="flash flash-{{ cat }}">
    {% if cat == 'success' %}
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
    {% else %}
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
    {% endif %}
    {{ msg }}
  </div>
  {% endfor %}
  {% endwith %}

  {{ page_content | safe }}
</div>
</main>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════
# INDEX / DASHBOARD
# ═══════════════════════════════════════════════════════

INDEX_CONTENT = r"""
<!-- STATS -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-label">Accounts</div>
    <div class="stat-num">{{ stats.get('total_accounts', 0) }}</div>
    <div class="stat-sub">Registered</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Violations</div>
    <div class="stat-num">{{ stats.get('total_violations', 0) }}</div>
    <div class="stat-sub">Total filed</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Escalations</div>
    <div class="stat-num">{{ stats.get('total_escalations', 0) }}</div>
    <div class="stat-sub">Tier advances</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Resolved</div>
    <div class="stat-num">{{ stats.get('total_resolved', 0) }}</div>
    <div class="stat-sub">Cases closed</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Open</div>
    <div class="stat-num">{{ stats.get('open_cases', 0) }}</div>
    <div class="stat-sub">Active cases</div>
  </div>
</div>

<!-- CHARTS ROW -->
<div class="grid-2" style="margin-bottom:20px">
  <div class="card">
    <div class="card-header"><h2>Case Status Distribution</h2></div>
    <div class="card-body">
      {% if stats.get('total_violations', 0) > 0 %}
      <div class="chart-wrap"><canvas id="statusChart"></canvas></div>
      {% else %}
      <div class="empty-state"><div class="empty-icon">&#9675;</div><p>No cases yet</p></div>
      {% endif %}
    </div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Violation Types</h2></div>
    <div class="card-body">
      {% if vtype_counts %}
      <div class="chart-wrap"><canvas id="vtypeChart"></canvas></div>
      {% else %}
      <div class="empty-state"><div class="empty-icon">&#9675;</div><p>No violations yet</p></div>
      {% endif %}
    </div>
  </div>
</div>

<!-- OPEN CASES TABLE -->
<div class="card">
  <div class="card-header">
    <h2>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      Open Cases
      <span class="count">{{ cases|length }}</span>
    </h2>
    <a href="/cases/all" class="btn btn-ghost btn-sm">View All</a>
  </div>
  <div class="card-body no-pad">
    {% if cases %}
    <table>
      <thead><tr>
        <th>ID</th><th>Violation</th><th>Jurisdiction</th><th>Tier</th><th>Amount</th><th>Severity</th><th>Status</th>
      </tr></thead>
      <tbody>
      {% for c in cases %}
      <tr>
        <td><a href="/case/{{ c.id }}" class="link">#{{ c.id }}</a></td>
        <td>{{ c.violation_type }}</td>
        <td>{{ c.get('jurisdiction', '?') }}</td>
        <td>{{ c.current_tier }}</td>
        <td class="cell-mono">{{ c.get('amount_disputed', 0) }}</td>
        <td>{{ c.get('severity', '?') }}/5</td>
        <td>
          {% set st = c.status %}
          {% if st == 'resolved' %}<span class="badge badge-resolved">resolved</span>
          {% elif 'escalat' in st %}<span class="badge badge-escalated">escalated</span>
          {% elif 'complaint' in st %}<span class="badge badge-drafted">drafted</span>
          {% else %}<span class="badge badge-open">open</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty-state" style="padding:32px">
      <div class="empty-icon">&#10003;</div>
      <p>All clear — no open cases.</p>
    </div>
    {% endif %}
  </div>
</div>

<!-- RECENT ACCOUNTS -->
<div class="card">
  <div class="card-header">
    <h2>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
      Accounts
      <span class="count">{{ accounts|length }}</span>
    </h2>
    <a href="/accounts" class="btn btn-ghost btn-sm">Manage</a>
  </div>
  <div class="card-body no-pad">
    {% if accounts %}
    <table>
      <thead><tr><th>ID</th><th>Name</th><th>Institution</th><th>Jurisdiction</th><th>Chain</th><th>Status</th></tr></thead>
      <tbody>
      {% for a in accounts %}
      <tr>
        <td class="cell-mono">#{{ a.id }}</td>
        <td style="font-weight:500">{{ a.name }}</td>
        <td>{{ a.institution }}</td>
        <td>{{ a.get('jurisdiction', '?') }}</td>
        <td>{% if a.get('chain') %}<span class="cell-mono">{{ a.chain }}</span>{% else %}—{% endif %}</td>
        <td>{% if a.get('active') %}<span class="badge badge-active">Active</span>{% else %}<span class="badge badge-inactive">Inactive</span>{% endif %}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty-state" style="padding:32px"><p>No accounts registered yet.</p></div>
    {% endif %}
  </div>
</div>

<!-- CHARTS JS -->
{% if stats.get('total_violations', 0) > 0 %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  // Status donut chart
  var statusCtx = document.getElementById('statusChart');
  if (statusCtx) {
    new Chart(statusCtx, {
      type: 'doughnut',
      data: {
        labels: ['Open', 'Complaint Drafted', 'Escalated', 'Resolved'],
        datasets: [{
          data: [{{ status_counts.get('open',0) }}, {{ status_counts.get('complaint_drafted',0) }},
                 {{ status_counts.get('escalated',0) }}, {{ status_counts.get('resolved',0) }}],
          backgroundColor: ['#e5e7eb','#9ca3af','#374151','#111827'],
          borderColor: '#fff',
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, padding: 14, font: { size: 12, family: 'Inter' }, color: '#6b7280' } }
        }
      }
    });
  }

  // Violation type bar chart
  var vtypeCtx = document.getElementById('vtypeChart');
  if (vtypeCtx) {
    var vtypeData = {{ vtype_counts | tojson }};
    var labels = Object.keys(vtypeData);
    var values = Object.values(vtypeData);
    new Chart(vtypeCtx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: '#111827',
          borderRadius: 4,
          barThickness: 28
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11, family: 'Inter' }, color: '#9ca3af' } },
          y: { grid: { display: false }, ticks: { font: { size: 11, family: 'Inter' }, color: '#374151' } }
        }
      }
    });
  }
});
</script>
{% endif %}
"""

# ═══════════════════════════════════════════════════════
# ACCOUNTS PAGE
# ═══════════════════════════════════════════════════════

ACCOUNTS_CONTENT = r"""
<div class="grid-3">
<!-- ACCOUNTS TABLE -->
<div>
  <div class="card">
    <div class="card-header">
      <h2>All Accounts <span class="count">{{ accounts|length }}</span></h2>
    </div>
    <div class="card-body no-pad">
      {% if accounts %}
      <table>
        <thead><tr><th>ID</th><th>Name</th><th>Institution</th><th>Type</th><th>Jurisdiction</th><th>Chain</th><th>Wallet</th><th>Status</th></tr></thead>
        <tbody>
        {% for a in accounts %}
        <tr>
          <td class="cell-mono">#{{ a.id }}</td>
          <td style="font-weight:600">{{ a.name }}</td>
          <td>{{ a.institution }}</td>
          <td>{{ a.get('account_type', '?') }}</td>
          <td>{{ a.get('jurisdiction', '?') }}</td>
          <td>{% if a.get('chain') %}<span class="cell-mono">{{ a.chain }}</span>{% else %}—{% endif %}</td>
          <td>{% if a.get('wallet_address') %}<span class="cell-mono truncate" title="{{ a.wallet_address }}">{{ a.wallet_address[:8] }}...{{ a.wallet_address[-6:] }}</span>{% else %}—{% endif %}</td>
          <td>{% if a.get('active') %}<span class="badge badge-active">Active</span>{% else %}<span class="badge badge-inactive">Inactive</span>{% endif %}</td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
      {% else %}
      <div class="empty-state" style="padding:32px"><p>No accounts registered. Use the form to add one.</p></div>
      {% endif %}
    </div>
  </div>
</div>

<!-- REGISTER FORM -->
<div>
  <div class="card">
    <div class="card-header"><h2>Register Account</h2></div>
    <div class="card-body">
      <form method="POST" action="/register">
        <div class="form-group">
          <label class="form-label">Full Name</label>
          <input class="form-input" name="name" placeholder="Jane Doe" required>
        </div>
        <div class="form-group">
          <label class="form-label">Institution</label>
          <input class="form-input" name="institution" placeholder="N26, Revolut, Coinbase..." required>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Account Reference</label>
            <input class="form-input" name="ref" placeholder="ACC-12345" required>
          </div>
          <div class="form-group">
            <label class="form-label">Account Type</label>
            <select class="form-select" name="atype">
              <option value="checking">Checking</option>
              <option value="savings">Savings</option>
              <option value="crypto_wallet">Crypto Wallet</option>
              <option value="investment">Investment</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Jurisdiction</label>
            <select class="form-select" name="jurisdiction">
              {% for j in jurisdictions %}<option value="{{ j }}">{{ j }}</option>{% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Chain</label>
            <select class="form-select" name="chain">
              <option value="">None</option>
              {% for c in chains %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Wallet Address</label>
          <input class="form-input" name="wallet" placeholder="0x... (optional)">
          <div class="form-hint">Optional — for on-chain neobank accounts</div>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">
          Register Account
        </button>
      </form>
    </div>
  </div>
</div>
</div>
"""

# ═══════════════════════════════════════════════════════
# ALL CASES PAGE
# ═══════════════════════════════════════════════════════

CASES_CONTENT = r"""
<div class="card">
  <div class="card-header">
    <h2>All Cases <span class="count">{{ cases|length }}</span></h2>
    <a href="/report-page" class="btn btn-primary btn-sm">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      Report Violation
    </a>
  </div>
  <div class="card-body no-pad">
    {% if cases %}
    <table>
      <thead><tr>
        <th>ID</th><th>Violation</th><th>Jurisdiction</th><th>Tier</th><th>Amount</th><th>Severity</th><th>Complaints</th><th>Status</th>
      </tr></thead>
      <tbody>
      {% for c in cases %}
      <tr>
        <td><a href="/case/{{ c.id }}" class="link">#{{ c.id }}</a></td>
        <td>{{ c.violation_type }}</td>
        <td>{{ c.get('jurisdiction', '?') }}</td>
        <td>{{ c.current_tier }}</td>
        <td class="cell-mono">{{ c.get('amount_disputed', 0) }}</td>
        <td>{{ c.get('severity', '?') }}/5</td>
        <td>{{ c.get('complaints', [])|length }}</td>
        <td>
          {% set st = c.status %}
          {% if st == 'resolved' %}<span class="badge badge-resolved">resolved</span>
          {% elif 'escalat' in st %}<span class="badge badge-escalated">escalated</span>
          {% elif 'complaint' in st %}<span class="badge badge-drafted">drafted</span>
          {% else %}<span class="badge badge-open">open</span>{% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty-state" style="padding:48px">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      </div>
      <p style="margin-top:8px">No cases recorded yet.</p>
    </div>
    {% endif %}
  </div>
</div>
"""

# ═══════════════════════════════════════════════════════
# CASE DETAIL PAGE
# ═══════════════════════════════════════════════════════

CASE_DETAIL_CONTENT = r"""
<!-- BREADCRUMB -->
<div style="margin-bottom:20px">
  <a href="/cases/all" class="meta" style="text-decoration:none">&larr; Back to Cases</a>
</div>

<!-- CASE HEADER -->
<div class="card">
  <div class="card-body">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
      <div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
          <h2 style="font-size:18px;font-weight:700;margin:0">{{ case.violation_type }}</h2>
          {% set st = case.status %}
          {% if st == 'resolved' %}<span class="badge badge-resolved">resolved</span>
          {% elif 'escalat' in st %}<span class="badge badge-escalated">escalated</span>
          {% elif 'complaint' in st %}<span class="badge badge-drafted">drafted</span>
          {% else %}<span class="badge badge-open">open</span>{% endif %}
        </div>
        <p style="color:#6b7280;font-size:13px;max-width:600px">{{ case.description }}</p>
      </div>
      {% if case.status != 'resolved' %}
      <div style="display:flex;gap:8px">
        <form method="POST" action="/draft/{{ case.id }}"><button class="btn btn-outline btn-sm">Draft Complaint</button></form>
        <form method="POST" action="/escalate/{{ case.id }}"><button class="btn btn-primary btn-sm">Escalate</button></form>
      </div>
      {% endif %}
    </div>

    <div class="divider"></div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:20px">
      <div>
        <div class="meta">Case ID</div>
        <div style="font-weight:600;margin-top:2px">#{{ case.id }}</div>
      </div>
      <div>
        <div class="meta">Jurisdiction</div>
        <div style="font-weight:600;margin-top:2px">{{ case.get('jurisdiction', '?') }}</div>
      </div>
      <div>
        <div class="meta">Current Tier</div>
        <div style="font-weight:600;margin-top:2px">{{ case.current_tier }}</div>
      </div>
      <div>
        <div class="meta">Amount Disputed</div>
        <div style="font-weight:600;margin-top:2px">{{ case.get('amount_disputed', 0) }}</div>
      </div>
      <div>
        <div class="meta">Severity</div>
        <div style="font-weight:600;margin-top:2px">{{ case.get('severity', '?') }} / 5</div>
      </div>
      {% if account %}
      <div>
        <div class="meta">Account</div>
        <div style="font-weight:600;margin-top:2px">{{ account.get('name', '?') }} @ {{ account.get('institution','?') }}</div>
      </div>
      {% endif %}
    </div>
  </div>
</div>

<div class="grid-2">
<!-- ESCALATION TIMELINE -->
<div>
  {% if path and path.get('path') %}
  <div class="card">
    <div class="card-header"><h2>Escalation Path</h2></div>
    <div class="card-body">
      <div class="timeline">
      {% for step in path.path %}
        <div class="tl-step {{ step.status }}">
          <div class="tl-dot"></div>
          <div class="tl-title">Tier {{ step.tier }}: {{ step.body }}</div>
          <div class="tl-meta">Deadline: {{ step.deadline_days }} days &middot; {{ step.status }}</div>
        </div>
      {% endfor %}
      </div>

      {% if path.get('history') %}
      <div class="divider"></div>
      <div class="meta" style="margin-bottom:6px;font-weight:600">Escalation History</div>
      {% for h in path.history %}
      <div class="meta" style="padding:4px 0">{{ h.get('from_body','?') }} &rarr; {{ h.get('to_body','?') }}{% if h.get('reason') %}: {{ h.reason }}{% endif %}</div>
      {% endfor %}
      {% endif %}
    </div>
  </div>
  {% endif %}

  <!-- RESOLVE / RESOLUTION -->
  {% if case.status != 'resolved' %}
  <div class="card">
    <div class="card-header"><h2>Resolve Case</h2></div>
    <div class="card-body">
      <form method="POST" action="/resolve/{{ case.id }}">
        <div class="form-group">
          <label class="form-label">Resolution Note</label>
          <textarea class="form-textarea" name="note" placeholder="Describe how the case was resolved..." required></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Amount Recovered</label>
          <input class="form-input" type="number" name="amount" placeholder="0" value="0" min="0">
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">Mark as Resolved</button>
      </form>
    </div>
  </div>
  {% else %}
  <div class="card">
    <div class="card-header"><h2>Resolution</h2></div>
    <div class="card-body">
      <p style="font-size:13px;color:#374151">{{ case.get('resolution_note', 'No note') }}</p>
      <div class="meta" style="margin-top:8px">Amount recovered: <strong>{{ case.get('amount_recovered', 0) }}</strong></div>
    </div>
  </div>
  {% endif %}
</div>

<!-- COMPLAINTS -->
<div>
  {% set complaints = case.get('complaints', []) %}
  <div class="card">
    <div class="card-header">
      <h2>Complaints <span class="count">{{ complaints|length }}</span></h2>
    </div>
    <div class="card-body">
      {% if complaints %}
        {% for comp in complaints %}
        <div style="{% if not loop.last %}margin-bottom:20px;padding-bottom:20px;border-bottom:1px solid #f3f4f6{% endif %}">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span class="complaint-tier">{{ comp.get('tier', '?') }}</span>
            <span style="font-weight:600;font-size:13px">{{ comp.get('subject', 'Untitled') }}</span>
          </div>
          <div class="complaint">{{ comp.get('body', '') }}</div>
          {% if comp.get('legal_clauses_cited') %}
          <div class="meta" style="margin-top:6px">
            <strong>Legal clauses:</strong> {{ comp.legal_clauses_cited | join(', ') }}
          </div>
          {% endif %}
          {% if comp.get('remedy_sought') %}
          <div class="meta" style="margin-top:4px">
            <strong>Remedy sought:</strong> {{ comp.remedy_sought }}
          </div>
          {% endif %}
        </div>
        {% endfor %}
      {% else %}
        <div class="empty-state">
          <p>No complaints drafted yet.</p>
          {% if case.status != 'resolved' %}
          <form method="POST" action="/draft/{{ case.id }}" style="margin-top:12px">
            <button class="btn btn-outline btn-sm">Draft First Complaint</button>
          </form>
          {% endif %}
        </div>
      {% endif %}
    </div>
  </div>

  <!-- RESPONSE ANALYSES -->
  {% set analyses = case.get('response_analyses', []) %}
  {% if analyses %}
  <div class="card">
    <div class="card-header"><h2>Response Analyses</h2></div>
    <div class="card-body">
      {% for ra in analyses %}
      <div style="{% if not loop.last %}margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #f3f4f6{% endif %}">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px">Recommendation: {{ ra.get('recommendation', '?') }}</div>
        <div class="meta">
          Acknowledged: {{ ra.get('acknowledged', '?') }} &middot;
          Remedy offered: {{ ra.get('remedy_offered', '?') }} &middot;
          Adequate: {{ ra.get('remedy_adequate', '?') }}
        </div>
        <div class="meta" style="margin-top:4px">{{ ra.get('summary', '') }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}
</div>
</div>
"""

# ═══════════════════════════════════════════════════════
# REPORT VIOLATION PAGE
# ═══════════════════════════════════════════════════════

REPORT_CONTENT = r"""
<div style="max-width:600px">
  <div class="card">
    <div class="card-header"><h2>Report a Violation</h2></div>
    <div class="card-body">
      <form method="POST" action="/report">
        <div class="form-group">
          <label class="form-label">Account</label>
          <select class="form-select" name="account_id" required>
            <option value="">Select account...</option>
            {% for a in accounts %}
            <option value="{{ a.id }}">#{{ a.id }} — {{ a.name }} @ {{ a.institution }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Violation Type</label>
          <select class="form-select" name="violation_type" required>
            {% for v in violations %}<option value="{{ v }}">{{ v }}</option>{% endfor %}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Description</label>
          <textarea class="form-textarea" name="description" placeholder="Describe what happened in detail..." required></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Amount Disputed</label>
            <input class="form-input" type="number" name="amount" value="0" min="0">
          </div>
          <div class="form-group">
            <label class="form-label">Severity</label>
            <select class="form-select" name="severity">
              <option value="1">1 — Low</option>
              <option value="2">2 — Minor</option>
              <option value="3" selected>3 — Medium</option>
              <option value="4">4 — High</option>
              <option value="5">5 — Critical</option>
            </select>
          </div>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;margin-top:8px">
          Submit Report
        </button>
      </form>
    </div>
  </div>
</div>
"""


if __name__ == "__main__":
    if not GL_PATH:
        print("ERROR: genlayer CLI not found. Install it first.")
        sys.exit(1)
    print(f"\n  AdvocateOS Dashboard (Professional B&W)")
    print(f"  Contract: {CONTRACT_ADDRESS}")
    print(f"  Open http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
