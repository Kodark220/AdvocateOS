"""
AdvocateOS Agent — Autonomous Consumer Advocacy Watchdog

This agent continuously monitors registered accounts for violations
and autonomously handles the full lifecycle:

  1. SCAN   — Periodically fetch account data and detect violations
  2. DRAFT  — Auto-draft formal complaints citing legal clauses
  3. WATCH  — Monitor response deadlines per escalation tier
  4. ESCALATE — Auto-escalate when institutions miss deadlines
  5. REVIEW — Check institution responses, recommend resolve/escalate

Runs as a long-lived process against the deployed AdvocateOS contracts
on GenLayer Studionet and Bradbury testnet (dual-network).
"""

import subprocess
import shutil
import json
import time
import logging
import os
import sys
try:
    import fcntl
except ImportError:
    fcntl = None  # Windows — no file locking needed
from datetime import datetime, timedelta

import notifications

# ── CONFIGURATION ──

NETWORKS: dict[str, dict] = {
    "studionet": {
        "contract": os.environ.get("AOS_CONTRACT_STUDIONET", "0x5b1C73fb7F1df7081126bF473eB40FfE77F05DFb"),
        "rpc": "https://studio.genlayer.com/api",
        "cli_network": "studionet",
        "label": "Studionet",
    },
    "bradbury": {
        "contract": os.environ.get("AOS_CONTRACT_BRADBURY", "0x6E7694c3ffbB4b109b2A37D009cE29425039E9da"),
        "rpc": "https://rpc-bradbury.genlayer.com",
        "cli_network": "testnet-bradbury",
        "label": "Bradbury Testnet",
    },
}

# Current active network context (set per-cycle in the main loop)
_active_net: str = "studionet"

KEYSTORE_PASSWORD = os.environ.get("AOS_KEYSTORE_PASSWORD", "")
GL_PATH = os.environ.get("AOS_GL_PATH") or shutil.which("genlayer")

# How often the agent checks (seconds)
SCAN_INTERVAL = int(os.environ.get("AOS_SCAN_INTERVAL", "3600"))
CASE_CHECK_INTERVAL = int(os.environ.get("AOS_CASE_CHECK_INTERVAL", "1800"))
WRITE_TIMEOUT = int(os.environ.get("AOS_WRITE_TIMEOUT", "600"))
READ_TIMEOUT = int(os.environ.get("AOS_READ_TIMEOUT", "60"))

# Network health cache: skip offline networks for 120s
_net_health: dict[str, dict] = {}
PROBE_TIMEOUT = 15

# Jurisdiction-aware tier labels and deadlines (mirrors contract)
JURISDICTION_TIERS: dict[str, dict] = {
    "US": {
        "labels": ["Company Internal", "CFPB / State Attorney General", "OCC / FDIC / FRB", "Small Claims / Federal District Court"],
        "deadlines": [1_209_600, 2_592_000, 2_592_000, 0],
    },
    "EU": {
        "labels": ["Company Internal", "National ADR / EU ODR Platform", "National Consumer Authority", "National Court / CJEU"],
        "deadlines": [1_209_600, 2_592_000, 2_592_000, 0],
    },
}

SUPPORTED_CHAINS = [
    "ethereum", "base", "solana", "polygon", "arbitrum",
    "optimism", "avalanche", "bsc", "genlayer", "stellar",
]

def _get_tier_label(jur: str, tier: int) -> str:
    jdata = JURISDICTION_TIERS.get(jur, JURISDICTION_TIERS["US"])
    labels = jdata["labels"]
    return labels[tier] if tier < len(labels) else "?"

def _get_tier_deadline(jur: str, tier: int) -> int:
    jdata = JURISDICTION_TIERS.get(jur, JURISDICTION_TIERS["US"])
    dl = jdata["deadlines"]
    return dl[tier] if tier < len(dl) else 0

# Persistent config file path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Map account IDs to their data URLs for scanning
ACCOUNT_DATA_URLS: dict[int, str] = {}
# Map case IDs to institution response URLs
CASE_RESPONSE_URLS: dict[int, str] = {}


def load_config():
    """Load persisted URLs from config.json."""
    global ACCOUNT_DATA_URLS, CASE_RESPONSE_URLS
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        ACCOUNT_DATA_URLS = {int(k): v for k, v in data.get("account_urls", {}).items()}
        CASE_RESPONSE_URLS = {int(k): v for k, v in data.get("response_urls", {}).items()}


def save_config():
    """Persist URLs to config.json."""
    data = {
        "account_urls": {str(k): v for k, v in ACCOUNT_DATA_URLS.items()},
        "response_urls": {str(k): v for k, v in CASE_RESPONSE_URLS.items()},
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# Load on import
load_config()

# ── LOGGING ──

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "agent.log"),
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("AdvocateOS-Agent")


# ── GENLAYER CLI INTERFACE ──

def _net() -> dict:
    """Return the current active network config."""
    return NETWORKS[_active_net]


def probe_network(net: str) -> bool:
    """Quick health check — try get_stats with short timeout. Cache for 120s."""
    now = time.time()
    cached = _net_health.get(net)
    if cached and now - cached["at"] < 120:
        return cached["ok"]
    cfg = NETWORKS[net]
    cmd = [GL_PATH, "call", "--rpc", cfg["rpc"], cfg["contract"], "get_stats"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=PROBE_TIMEOUT)
        output = r.stdout + r.stderr
        ok = any(s.strip().startswith("{") for s in output.split("\n"))
        _net_health[net] = {"ok": ok, "at": now}
        if ok:
            log.info("probe %s: online", net)
        else:
            log.warning("probe %s: no JSON (exit %d)", net, r.returncode)
        return ok
    except subprocess.TimeoutExpired:
        log.warning("probe %s: timeout after %ds", net, PROBE_TIMEOUT)
        _net_health[net] = {"ok": False, "at": now}
        return False
    except Exception as e:
        log.error("probe %s: %s", net, e)
        _net_health[net] = {"ok": False, "at": now}
        return False


def gl_call(method: str, *args: str) -> dict | list | str | None:
    """Call a view method on the active network's contract via CLI with --rpc."""
    cfg = _net()
    cmd = [GL_PATH, "call", "--rpc", cfg["rpc"], cfg["contract"], method]
    for a in args:
        cmd += ["--args", str(a)]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=READ_TIMEOUT,
        )
        for line in (r.stdout + r.stderr).split("\n"):
            s = line.strip()
            if s.startswith("{") or s.startswith("["):
                return json.loads(s)
    except subprocess.TimeoutExpired:
        log.error("[%s] gl_call %s timed out after %ds", _active_net, method, READ_TIMEOUT)
    except Exception as e:
        log.error("[%s] gl_call %s failed: %s", _active_net, method, e)
    return None


def gl_write(method: str, *args: str) -> bool:
    """Send a write transaction on the active network with keystore password and file locking."""
    cfg = _net()
    cmd = [GL_PATH, "write", "--rpc", cfg["rpc"], cfg["contract"], method]
    for a in args:
        cmd += ["--args", str(a)]
    try:
        lock_fd = None
        if fcntl:
            lock_fd = open("/tmp/genlayer_cli.lock", "w")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            # Switch to correct network for consensus
            subprocess.run(
                [GL_PATH, "network", "set", cfg["cli_network"]],
                capture_output=True, text=True, timeout=10,
            )
            r = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            if KEYSTORE_PASSWORD:
                r.stdin.write((KEYSTORE_PASSWORD + "\n").encode())
                r.stdin.flush()
        finally:
            if lock_fd and fcntl:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
        try:
            stdout, stderr = r.communicate(timeout=WRITE_TIMEOUT)
            combined = (stdout + stderr).decode("utf-8", errors="replace")
            if "Transaction Hash" in combined or "successfully" in combined.lower():
                log.info("[%s] gl_write %s: tx submitted", _active_net, method)
                return True
            if "DISAGREE" in combined:
                log.warning("[%s] Validators DISAGREE on %s", _active_net, method)
            elif "not processed" in combined.lower():
                log.warning("[%s] Transaction not processed: %s", _active_net, method)
            else:
                log.warning("[%s] Write %s exit=%d: %s", _active_net, method, r.returncode, combined[-300:])
        except subprocess.TimeoutExpired:
            log.info("[%s] Write %s: timeout waiting for consensus (tx likely submitted)", _active_net, method)
            r.kill()
            r.communicate()
            return True
    except Exception as e:
        log.error("[%s] Write %s error: %s", _active_net, method, e)
    return False


# ── AGENT TASKS ──

def fetch_stats() -> dict | None:
    """Get current contract statistics."""
    return gl_call("get_stats")


def fetch_all_accounts() -> list[dict]:
    """Get all registered accounts."""
    result = gl_call("get_all_accounts")
    return result if isinstance(result, list) else []


def fetch_open_cases() -> list[dict]:
    """Get all open (unresolved) cases."""
    result = gl_call("get_open_cases")
    return result if isinstance(result, list) else []


def fetch_case(case_id: int) -> dict | None:
    """Get full case details."""
    result = gl_call("get_case", str(case_id))
    return result if isinstance(result, dict) else None


def scan_account(account_id: int, data_url: str) -> bool:
    """Trigger on-chain violation scan for an account."""
    log.info(
        "SCANNING account #%d via %s",
        account_id, data_url[:80],
    )
    ok = gl_write("scan_for_violations", str(account_id), data_url)
    if ok:
        log.info("Scan complete for account #%d — violations filed on-chain", account_id)
    else:
        log.error("Scan failed for account #%d", account_id)
    return ok


def draft_complaint_for_case(case_id: int) -> bool:
    """Trigger on-chain complaint drafting for a case."""
    log.info("DRAFTING complaint for case #%d", case_id)
    ok = gl_write("draft_complaint", str(case_id))
    if ok:
        log.info("Complaint drafted for case #%d", case_id)
        c = fetch_case(case_id)
        if c:
            jur = c.get("jurisdiction", "US")
            tier = c.get("current_tier", 0)
            notifications.notify_complaint_drafted(
                case_id, c.get("violation_type", "?"), tier,
                _get_tier_label(jur, tier),
            )
    else:
        log.error("Complaint drafting failed for case #%d", case_id)
    return ok


def escalate_case(case_id: int, prev_tier: int = 0, jur: str = "US") -> bool:
    """Escalate a case to the next tier."""
    log.info("ESCALATING case #%d", case_id)
    ok = gl_write("escalate", str(case_id))
    if ok:
        log.info("Case #%d escalated", case_id)
        new_tier = prev_tier + 1
        notifications.notify_escalation(
            case_id, prev_tier, new_tier,
            _get_tier_label(jur, prev_tier),
            _get_tier_label(jur, new_tier),
            "Deadline passed without adequate response",
        )
    else:
        log.error("Escalation failed for case #%d", case_id)
    return ok


def check_response(case_id: int, response_url: str) -> bool:
    """Check institution's response to a complaint."""
    log.info("CHECKING institution response for case #%d", case_id)
    ok = gl_write("check_institution_response", str(case_id), response_url)
    if ok:
        log.info("Response checked for case #%d", case_id)
    else:
        log.error("Response check failed for case #%d", case_id)
    return ok


# ── AGENT DECISION ENGINE ──

def process_open_cases():
    """
    Core agent logic — decide what to do with each open case:

    Case status flow:
      open → (draft complaint) → complaint_drafted → (wait for deadline)
        → (escalate if no response) → escalated → (draft new complaint)
        → ... repeat up to tier 3
      At any point: check_institution_response → institution_resolved / escalation_recommended
    """
    cases = fetch_open_cases()
    if not cases:
        log.info("No open cases — all quiet")
        return

    log.info("Processing %d open case(s)...", len(cases))
    now_ts = int(time.time())

    for case in cases:
        cid = case["id"]
        status = case.get("status", "")
        tier = case.get("current_tier", 0)
        complaints = case.get("complaints", [])
        tier_complaints = [c for c in complaints if c.get("tier") == tier]

        jur = case.get("jurisdiction", "UK")
        log.info(
            "  Case #%d: %s | %s | status=%s | tier=%d (%s) | complaints=%d",
            cid, case.get("violation_type"), jur, status, tier,
            _get_tier_label(jur, tier), len(complaints),
        )

        # Step 1: If case has a response URL configured, check it
        if cid in CASE_RESPONSE_URLS:
            url = CASE_RESPONSE_URLS[cid]
            log.info("  → Response URL found, checking institution response...")
            if check_response(cid, url):
                # Re-fetch to see updated status
                updated = fetch_case(cid)
                if updated:
                    new_status = updated.get("status", "")
                    if new_status == "institution_resolved":
                        log.info("  → Institution adequately resolved case #%d!", cid)
                        notifications.notify_institution_response(cid, "resolved", "Institution resolved the case")
                        del CASE_RESPONSE_URLS[cid]
                        save_config()
                        continue
                    elif new_status == "escalation_recommended":
                        log.info("  → Institution response inadequate, will escalate")
                        notifications.notify_institution_response(cid, "escalate", "Institution response inadequate")
                        escalate_case(cid, tier, jur)
                        continue
            continue

        # Step 2: If no complaint drafted for current tier, draft one
        if status in ("open", "escalated", "auto_escalated") and not tier_complaints:
            log.info("  → No complaint for tier %d, drafting...", tier)
            draft_complaint_for_case(cid)
            continue

        # Step 3: If complaint was drafted, check if deadline passed
        if status == "complaint_drafted" or (tier_complaints and status not in ("resolved",)):
            deadline_secs = _get_tier_deadline(jur, tier)
            if deadline_secs > 0 and tier < 3:
                # Use a simple heuristic: if complaint exists and we've waited
                # long enough, escalate. In production you'd track exact timestamps.
                log.info(
                    "  → Complaint exists for tier %d, deadline=%dd. "
                    "Attempting auto-escalation check...",
                    tier, deadline_secs // 86400,
                )
                # Try auto-escalate (contract checks internally)
                ok = gl_write(
                    "check_and_auto_escalate", str(cid), str(now_ts)
                )
                if ok:
                    log.info("  → Auto-escalated case #%d past tier %d", cid, tier)
                    new_tier = tier + 1
                    notifications.notify_escalation(
                        cid, tier, new_tier,
                        _get_tier_label(jur, tier),
                        _get_tier_label(jur, new_tier),
                        "Deadline passed — auto-escalated",
                    )
                else:
                    # Check deadline proximity for warning
                    if tier_complaints:
                        days_left = max(0, deadline_secs // 86400 - 1)
                        if 0 < days_left <= 3:
                            notifications.notify_deadline_approaching(
                                cid, case.get("violation_type", "?"), tier,
                                _get_tier_label(jur, tier), days_left,
                            )
                    log.info("  → Not yet time to escalate (deadline not passed)")

        # Step 4: If escalation_recommended from response check, escalate
        if status == "escalation_recommended":
            log.info("  → Escalation recommended, escalating...")
            escalate_case(cid, tier, jur)


def scan_all_accounts():
    """Scan every active account that has a data URL configured."""
    accounts = fetch_all_accounts()
    if not accounts:
        log.info("No accounts registered yet")
        return

    for acc in accounts:
        aid = acc["id"]
        if not acc.get("active"):
            continue
        if aid not in ACCOUNT_DATA_URLS:
            log.debug("Account #%d has no data URL configured, skipping", aid)
            continue
        scan_account(aid, ACCOUNT_DATA_URLS[aid])


# ── AGENT MAIN LOOP ──

def print_banner():
    log.info("=" * 60)
    log.info("  AdvocateOS Agent — Autonomous Consumer Watchdog")
    log.info("  Mode: Dual-Network (Studionet + Bradbury)")
    for net_key, cfg in NETWORKS.items():
        global _active_net
        _active_net = net_key
        stats = fetch_stats()
        if stats:
            log.info(
                "  [%s] %s | Accounts: %d | Violations: %d | Escalations: %d | Resolved: %d",
                net_key, cfg["contract"][:12] + "...",
                stats.get("total_accounts", 0),
                stats.get("total_violations", 0),
                stats.get("total_escalations", 0),
                stats.get("total_resolved", 0),
            )
        else:
            log.warning("  [%s] %s — offline or unreachable", net_key, cfg["contract"][:12] + "...")
    log.info("=" * 60)


def run_agent():
    """Main agent loop — runs forever, monitoring both networks."""
    global _active_net
    if not GL_PATH:
        log.error("genlayer CLI not found in PATH. Install it first.")
        sys.exit(1)

    print_banner()

    log.info("Agent started. Scan interval: %ds, Case check: %ds",
             SCAN_INTERVAL, CASE_CHECK_INTERVAL)
    log.info("Monitored networks: %s", ", ".join(NETWORKS.keys()))
    log.info("Supported jurisdictions: %s", ", ".join(JURISDICTION_TIERS.keys()))

    last_scan = 0
    last_case_check = 0

    while True:
        now = time.time()

        # Periodic violation scanning — both networks
        if now - last_scan >= SCAN_INTERVAL:
            for net_key in NETWORKS:
                _active_net = net_key
                if not probe_network(net_key):
                    log.warning("─── SCAN SKIP [%s] — network offline ───", net_key)
                    continue
                log.info("─── VIOLATION SCAN [%s] ───", net_key)
                scan_all_accounts()
            last_scan = now

        # Periodic case lifecycle processing — both networks
        if now - last_case_check >= CASE_CHECK_INTERVAL:
            for net_key in NETWORKS:
                _active_net = net_key
                if not probe_network(net_key):
                    log.warning("─── CASE CHECK SKIP [%s] — network offline ───", net_key)
                    continue
                log.info("─── CASE LIFECYCLE [%s] ───", net_key)
                process_open_cases()
            last_case_check = now

        # Sleep before next tick
        time.sleep(60)


# ── CLI COMMANDS ──

def cmd_status():
    """Show current contract state across both networks."""
    global _active_net
    print_banner()
    for net_key in NETWORKS:
        _active_net = net_key
        if not probe_network(net_key):
            print(f"\n[{net_key}] — OFFLINE")
            continue
        print(f"\n[{net_key}] {NETWORKS[net_key]['label']}:")
        accounts = fetch_all_accounts()
        if accounts:
            print("  Accounts:")
            for a in accounts:
                status = "ACTIVE" if a.get("active") else "INACTIVE"
                jur = a.get("jurisdiction", "?")
                url = ACCOUNT_DATA_URLS.get(a["id"], "not configured")
                print(f"    #{a['id']} {a['name']} @ {a['institution']} [{status}] ({jur})")
                wallet = a.get("wallet_address", "")
                ch = a.get("chain", "")
                if wallet:
                    print(f"        Wallet: {wallet} on {ch}")
                tc = a.get("terms_url", "")
                print(f"        Data URL: {url}")
                if tc:
                    print(f"        Terms URL: {tc}")

        cases = fetch_open_cases()
        if cases:
            print(f"  Open Cases ({len(cases)}):")
            for c in cases:
                cjur = c.get("jurisdiction", "US")
                print(
                    f"    #{c['id']}: {c['violation_type']} [{cjur}] | "
                    f"status={c['status']} | tier={c['current_tier']} "
                    f"({_get_tier_label(cjur, c['current_tier'])}) | "
                    f"amount={c.get('amount_disputed', 0)}"
                )
        else:
            print("  No open cases.")


def cmd_add_account(name: str, institution: str, account_ref: str,
                    account_type: str, jurisdiction: str = "US",
                    wallet_address: str = "", chain: str = "",
                    data_url: str = ""):
    """Register a new account and optionally set its data URL."""
    if jurisdiction not in JURISDICTION_TIERS:
        log.error("Unsupported jurisdiction: %s. Use: %s", jurisdiction, ", ".join(JURISDICTION_TIERS.keys()))
        return
    if chain and chain not in SUPPORTED_CHAINS:
        log.error("Unsupported chain: %s. Use: %s", chain, ", ".join(SUPPORTED_CHAINS))
        return
    log.info("Registering account: %s @ %s [%s] wallet=%s chain=%s", name, institution, jurisdiction, wallet_address, chain)
    ok = gl_write("register_account", name, institution, account_ref, account_type, jurisdiction, wallet_address, chain)
    if ok:
        stats = fetch_stats()
        aid = stats["total_accounts"] if stats else "?"
        log.info("Account registered as #%s", aid)
        if data_url:
            ACCOUNT_DATA_URLS[int(aid)] = data_url
            save_config()
            log.info("Data URL set for account #%s: %s", aid, data_url)
    else:
        log.error("Failed to register account")


def cmd_set_data_url(account_id: int, data_url: str):
    """Set the data URL for periodic scanning of an account."""
    ACCOUNT_DATA_URLS[account_id] = data_url
    save_config()
    log.info("Data URL set for account #%d: %s", account_id, data_url)


def cmd_set_response_url(case_id: int, response_url: str):
    """Set an institution response URL for a case."""
    CASE_RESPONSE_URLS[case_id] = response_url
    save_config()
    log.info("Response URL set for case #%d: %s", case_id, response_url)


def cmd_set_terms_url(account_id: int, terms_url: str):
    """Set the T&C URL for an account (stored on-chain)."""
    log.info("Setting terms URL for account #%d: %s", account_id, terms_url)
    ok = gl_write("set_terms_url", str(account_id), terms_url)
    if ok:
        log.info("Terms URL set on-chain for account #%d", account_id)
    else:
        log.error("Failed to set terms URL for account #%d", account_id)


def cmd_scan_now(account_id: int = 0):
    """Manually trigger a scan. If account_id=0, scan all."""
    if account_id == 0:
        scan_all_accounts()
    else:
        url = ACCOUNT_DATA_URLS.get(account_id)
        if not url:
            log.error("No data URL for account #%d. Set one with: set-url %d <url>", account_id, account_id)
            return
        scan_account(account_id, url)


def cmd_process_now():
    """Manually trigger case processing."""
    process_open_cases()


def print_usage():
    print("""
AdvocateOS Agent — Usage:
  py agent.py run                                    Start the autonomous agent loop
  py agent.py status                                 Show contract state & cases
  py agent.py add-account <name> <institution> <ref> <type> <jurisdiction> <wallet> <chain> [data_url]
                                                     Register a new account
                                                     Jurisdictions: US, EU
                                                     Chains: ethereum, base, solana, polygon, arbitrum, optimism, avalanche, bsc, genlayer, stellar
  py agent.py set-url <account_id> <data_url>        Set scan URL for an account
  py agent.py set-terms <account_id> <terms_url>     Set T&C URL for an account
  py agent.py set-response <case_id> <response_url>  Set institution response URL
  py agent.py scan [account_id]                      Trigger violation scan now
  py agent.py process                                Process open cases now
  py agent.py report <account_id> <type> <desc> <amount> <severity>
                                                     Manually report a violation
""")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print_usage()
    elif args[0] == "run":
        run_agent()
    elif args[0] == "status":
        cmd_status()
    elif args[0] == "add-account" and len(args) >= 8:
        data_url = args[8] if len(args) > 8 else ""
        cmd_add_account(args[1], args[2], args[3], args[4], args[5], args[6], args[7], data_url)
    elif args[0] == "set-url" and len(args) == 3:
        cmd_set_data_url(int(args[1]), args[2])
    elif args[0] == "set-terms" and len(args) == 3:
        cmd_set_terms_url(int(args[1]), args[2])
    elif args[0] == "set-response" and len(args) == 3:
        cmd_set_response_url(int(args[1]), args[2])
    elif args[0] == "scan":
        aid = int(args[1]) if len(args) > 1 else 0
        cmd_scan_now(aid)
    elif args[0] == "process":
        cmd_process_now()
    elif args[0] == "report" and len(args) >= 6:
        log.info("Reporting violation: %s on account #%s", args[2], args[1])
        ok = gl_write("report_violation", args[1], args[2], args[3], args[4], args[5])
        if ok:
            log.info("Violation reported successfully")
            # Send notification for new violation
            acc = gl_call("get_account", args[1])
            stats = fetch_stats()
            cid = stats.get("total_violations", 0) if stats else 0
            notifications.notify_violation(
                cid, args[2],
                acc.get("name", "?") if acc else "?",
                acc.get("institution", "?") if acc else "?",
                acc.get("jurisdiction", "US") if acc else "US",
                int(args[4]), int(args[5]),
            )
        else:
            log.error("Failed to report violation")
    else:
        print_usage()
