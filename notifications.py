"""
AdvocateOS Notification Layer — Webhook + Email Alerts

Sends alerts when:
  - New violation detected
  - Complaint drafted
  - Case escalated
  - Deadline approaching (within 3 days)
  - Case resolved

Configure WEBHOOK_URL and/or SMTP settings below.
"""

import json
import logging
import smtplib
import ssl
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

log = logging.getLogger("AdvocateOS-Notifications")

# ── WEBHOOK CONFIG ──

WEBHOOK_URL = ""  # Set your webhook endpoint (Slack, Discord, Zapier, etc.)
WEBHOOK_HEADERS = {"Content-Type": "application/json"}

# ── EMAIL CONFIG ──

SMTP_ENABLED = False
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = ""       # e.g. "alerts@yourdomain.com"
SMTP_PASSWORD = ""   # Use app password, not your real password
EMAIL_FROM = ""      # e.g. "AdvocateOS <alerts@yourdomain.com>"
EMAIL_TO = ""        # e.g. "you@example.com"

# ── ALERT TYPES ──

ALERT_VIOLATION = "violation"
ALERT_COMPLAINT = "complaint"
ALERT_ESCALATION = "escalation"
ALERT_DEADLINE = "deadline"
ALERT_RESOLVED = "resolved"
ALERT_RESPONSE = "response"

ALERT_COLORS = {
    ALERT_VIOLATION: "#ef4444",    # red
    ALERT_COMPLAINT: "#6366f1",    # indigo
    ALERT_ESCALATION: "#f97315",   # orange
    ALERT_DEADLINE: "#eab308",     # yellow
    ALERT_RESOLVED: "#22c55e",     # green
    ALERT_RESPONSE: "#3b82f6",     # blue
}

ALERT_ICONS = {
    ALERT_VIOLATION: "🚨",
    ALERT_COMPLAINT: "📝",
    ALERT_ESCALATION: "⬆️",
    ALERT_DEADLINE: "⏰",
    ALERT_RESOLVED: "✅",
    ALERT_RESPONSE: "📬",
}


# ── CORE SEND FUNCTIONS ──

def send_webhook(payload: dict) -> bool:
    """Send a JSON payload to the configured webhook URL."""
    if not WEBHOOK_URL:
        return False
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers=WEBHOOK_HEADERS,
            method="POST",
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            if resp.status < 300:
                log.debug("Webhook sent: %s", payload.get("alert_type", "?"))
                return True
            log.warning("Webhook returned %d", resp.status)
    except urllib.error.URLError as e:
        log.error("Webhook error: %s", e)
    except Exception as e:
        log.error("Webhook send failed: %s", e)
    return False


def send_email(subject: str, body_html: str) -> bool:
    """Send an email alert via SMTP."""
    if not SMTP_ENABLED or not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, EMAIL_TO]):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM or SMTP_USER
        msg["To"] = EMAIL_TO
        msg.attach(MIMEText(body_html, "html"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=ctx)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], [EMAIL_TO], msg.as_string())
        log.debug("Email sent: %s", subject)
        return True
    except Exception as e:
        log.error("Email send failed: %s", e)
    return False


# ── ALERT BUILDERS ──

def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _build_email_html(alert_type: str, title: str, details: dict) -> str:
    color = ALERT_COLORS.get(alert_type, "#6366f1")
    icon = ALERT_ICONS.get(alert_type, "🔔")
    rows = "".join(
        f'<tr><td style="padding:4px 8px;color:#94a3b8;font-size:13px">{k}</td>'
        f'<td style="padding:4px 8px;font-size:13px">{v}</td></tr>'
        for k, v in details.items()
    )
    return f"""
    <div style="font-family:Segoe UI,system-ui,sans-serif;max-width:600px;margin:0 auto;
    background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;overflow:hidden">
      <div style="background:{color};padding:16px 20px;color:#fff;font-size:16px;font-weight:700">
        {icon} {title}
      </div>
      <div style="padding:20px">
        <table style="width:100%;border-collapse:collapse;color:#e2e8f0">{rows}</table>
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid #2a2d3a;
        color:#94a3b8;font-size:11px">
          AdvocateOS • {_timestamp()}
        </div>
      </div>
    </div>
    """


def _build_webhook_payload(alert_type: str, title: str, details: dict) -> dict:
    """Build a generic webhook payload (works with Slack, Discord, generic endpoints)."""
    return {
        "alert_type": alert_type,
        "title": f"{ALERT_ICONS.get(alert_type, '')} {title}",
        "details": details,
        "timestamp": _timestamp(),
        "source": "AdvocateOS",
        # Slack-compatible format
        "text": f"{ALERT_ICONS.get(alert_type, '')} *{title}*\n"
                + "\n".join(f"• {k}: {v}" for k, v in details.items()),
    }


# ── PUBLIC ALERT FUNCTIONS ──

def notify_violation(case_id: int, violation_type: str, account_name: str,
                     institution: str, jurisdiction: str, amount: int, severity: int):
    """Send alert for a new violation detected."""
    title = f"New Violation: {violation_type}"
    details = {
        "Case": f"#{case_id}",
        "Type": violation_type,
        "Account": f"{account_name} @ {institution}",
        "Jurisdiction": jurisdiction,
        "Amount Disputed": str(amount),
        "Severity": f"{severity}/5",
    }
    send_webhook(_build_webhook_payload(ALERT_VIOLATION, title, details))
    send_email(
        f"[AdvocateOS] {title} — Case #{case_id}",
        _build_email_html(ALERT_VIOLATION, title, details),
    )
    log.info("NOTIFY: %s (case #%d)", title, case_id)


def notify_complaint_drafted(case_id: int, violation_type: str, tier: int, tier_body: str):
    """Send alert when a complaint is drafted."""
    title = f"Complaint Drafted: Case #{case_id}"
    details = {
        "Case": f"#{case_id}",
        "Violation": violation_type,
        "Tier": f"{tier} — {tier_body}",
    }
    send_webhook(_build_webhook_payload(ALERT_COMPLAINT, title, details))
    send_email(
        f"[AdvocateOS] {title}",
        _build_email_html(ALERT_COMPLAINT, title, details),
    )
    log.info("NOTIFY: %s", title)


def notify_escalation(case_id: int, from_tier: int, to_tier: int,
                       from_body: str, to_body: str, reason: str):
    """Send alert when a case is escalated."""
    title = f"Case #{case_id} Escalated to Tier {to_tier}"
    details = {
        "Case": f"#{case_id}",
        "From": f"Tier {from_tier} — {from_body}",
        "To": f"Tier {to_tier} — {to_body}",
        "Reason": reason,
    }
    send_webhook(_build_webhook_payload(ALERT_ESCALATION, title, details))
    send_email(
        f"[AdvocateOS] ⬆️ {title}",
        _build_email_html(ALERT_ESCALATION, title, details),
    )
    log.info("NOTIFY: %s", title)


def notify_deadline_approaching(case_id: int, violation_type: str, tier: int,
                                 tier_body: str, days_left: int):
    """Send alert when a deadline is approaching (within 3 days)."""
    title = f"Deadline Approaching: Case #{case_id}"
    details = {
        "Case": f"#{case_id}",
        "Violation": violation_type,
        "Tier": f"{tier} — {tier_body}",
        "Days Remaining": str(days_left),
        "Action": "Response needed or case will auto-escalate",
    }
    send_webhook(_build_webhook_payload(ALERT_DEADLINE, title, details))
    send_email(
        f"[AdvocateOS] ⏰ {title} — {days_left} days left",
        _build_email_html(ALERT_DEADLINE, title, details),
    )
    log.info("NOTIFY: %s (%d days left)", title, days_left)


def notify_resolved(case_id: int, violation_type: str, amount_recovered: int,
                     resolution_note: str):
    """Send alert when a case is resolved."""
    title = f"Case #{case_id} Resolved"
    details = {
        "Case": f"#{case_id}",
        "Violation": violation_type,
        "Amount Recovered": str(amount_recovered),
        "Resolution": resolution_note[:200],
    }
    send_webhook(_build_webhook_payload(ALERT_RESOLVED, title, details))
    send_email(
        f"[AdvocateOS] ✅ {title}",
        _build_email_html(ALERT_RESOLVED, title, details),
    )
    log.info("NOTIFY: %s (recovered %d)", title, amount_recovered)


def notify_institution_response(case_id: int, recommendation: str, summary: str):
    """Send alert when an institution response is analyzed."""
    title = f"Institution Response: Case #{case_id}"
    details = {
        "Case": f"#{case_id}",
        "Recommendation": recommendation,
        "Summary": summary[:200],
    }
    send_webhook(_build_webhook_payload(ALERT_RESPONSE, title, details))
    send_email(
        f"[AdvocateOS] 📬 {title} — {recommendation}",
        _build_email_html(ALERT_RESPONSE, title, details),
    )
    log.info("NOTIFY: %s (%s)", title, recommendation)
