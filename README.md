# AdvocateOS — Autonomous Consumer Advocacy Agent

> An AI-powered autonomous consumer protection system built on [GenLayer](https://genlayer.com). AdvocateOS monitors financial accounts, detects violations, drafts legally-grounded complaint letters, and autonomously escalates through regulatory bodies — all on-chain.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Dashboard                         │
│              (Flask @ localhost:5000)                     │
│    Accounts │ Cases │ Complaints │ Escalation Timeline   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
┌──────────────────────┴──────────────────────────────────┐
│                  Agent (agent.py)                         │
│  Autonomous watchdog loop:                               │
│    SCAN → DETECT → DRAFT → WATCH → ESCALATE → RESOLVE   │
│  CLI: status | add-account | report | scan | process     │
│  Notifications: webhook + email alerts                   │
└──────────────────────┬──────────────────────────────────┘
                       │ GenLayer CLI (genlayer write/call)
┌──────────────────────┴──────────────────────────────────┐
│           Intelligent Contract (advocate_os.py)           │
│              GenLayer Bradbury Testnet                    │
│                                                          │
│  On-chain:                                               │
│  • Account registry (wallet + chain + T&C URL)           │
│  • Violation detection (LLM + web fetch + T&C compare)   │
│  • Complaint drafting (LLM with jurisdiction-aware       │
│    legal citations)                                      │
│  • Escalation engine (4-tier per jurisdiction)           │
│  • Institution response analysis (LLM)                   │
│                                                          │
│  Consensus: Leader executes → Validators verify          │
│  (Equivalence Principle)                                 │
└─────────────────────────────────────────────────────────┘
```

## Features

- **Multi-jurisdiction** — US and EU regulatory frameworks with jurisdiction-specific legal clauses and escalation paths
- **On-chain neobank support** — Track accounts on ethereum, base, solana, polygon, arbitrum, optimism, avalanche, bsc, genlayer, stellar
- **T&C compliance** — Fetches institution's own terms, compares account activity against them
- **9 violation types** — overcharge, missed_deadline, sla_breach, unauthorized_fee, interest_calculation_error, disclosure_failure, unauthorized_transfer, yield_misrepresentation, withdrawal_restriction
- **AI-drafted complaints** — LLM generates formal letters citing exact legal clauses (PSD2, MiCA, PAD, EFTA, TILA, etc.)
- **4-tier escalation** — Company Internal → ADR/CFPB → National Authority → Court
- **Autonomous agent** — Scans, drafts, monitors deadlines, auto-escalates without human intervention
- **Web dashboard** — Real-time view of accounts, cases, complaints, and escalation timelines
- **Notifications** — Webhook and email alerts for new violations, escalations, and deadlines

## Violation Types

| Type | Description |
|------|-------------|
| `overcharge` | Excessive fees or charges |
| `missed_deadline` | Institution failed to act within required timeframe |
| `sla_breach` | Service level agreement violation |
| `unauthorized_fee` | Fee charged without disclosure or consent |
| `interest_calculation_error` | Incorrect interest applied |
| `disclosure_failure` | Required information not provided |
| `unauthorized_transfer` | Funds moved without authorization |
| `yield_misrepresentation` | Advertised yield doesn't match actual |
| `withdrawal_restriction` | Blocked access to funds without cause |

## Escalation Paths

### US
| Tier | Body | Deadline |
|------|------|----------|
| 0 | Company Internal | 14 days |
| 1 | CFPB / State Attorney General | 30 days |
| 2 | OCC / FDIC / FRB | 30 days |
| 3 | Small Claims / Federal District Court | — |

### EU
| Tier | Body | Deadline |
|------|------|----------|
| 0 | Company Internal | 14 days |
| 1 | National ADR / EU ODR Platform | 30 days |
| 2 | National Consumer Authority | 30 days |
| 3 | National Court / CJEU | — |

## Setup

### Prerequisites

- Python 3.12+
- [GenLayer CLI](https://docs.genlayer.com) (`npm install -g genlayer`)
- GenLayer account on Bradbury testnet
- Flask (`pip install flask`)

### Installation

```bash
git clone <repo-url>
cd "Consumer agent"
pip install flask
```

### Configure GenLayer

```bash
genlayer init
genlayer account import --name my-account --private-key <key>
genlayer config set --network testnet-bradbury
```

### Deploy the Contract

```bash
genlayer deploy --contract advocate_os.py
```

Update the `CONTRACT_ADDRESS` in both `agent.py` and `dashboard.py` with the deployed address.

## Usage

### Web Dashboard

```bash
py dashboard.py
# Open http://127.0.0.1:5000
```

The dashboard provides:
- **Overview** — Account count, open violations, escalations, resolved cases
- **Account Management** — Register accounts with wallet address and chain
- **Case Viewer** — Full complaint text, escalation timeline, legal citations
- **Actions** — Report violations, draft complaints, escalate, resolve

### CLI Agent

```bash
# Show current state
py agent.py status

# Register an account
py agent.py add-account "Marie Dupont" "N26" "N26-EU-789" "checking" "EU" "GBXYZ..." "stellar"

# Set T&C URL (stored on-chain)
py agent.py set-terms 1 "https://n26.com/en-eu/legal-documents"

# Report a violation
py agent.py report 1 withdrawal_restriction "Blocked 500 EUR withdrawal" 500 4

# Process open cases (draft complaints, auto-escalate)
py agent.py process

# Run autonomous loop (scans every hour, processes cases every 30 min)
py agent.py run
```

### Notifications

Configure webhook and email alerts in `notifications.py`:

```python
WEBHOOK_URL = "https://your-webhook-endpoint.com/alerts"
SMTP_SERVER = "smtp.gmail.com"
EMAIL_TO = "you@example.com"
```

Then start the notification-enabled agent:
```bash
py agent.py run  # Sends alerts on new violations, escalations, and approaching deadlines
```

## Project Structure

```
Consumer agent/
├── advocate_os.py      # GenLayer intelligent contract (~26 KB)
├── agent.py            # Autonomous CLI agent
├── dashboard.py        # Flask web dashboard
├── notifications.py    # Webhook + email notification layer
├── config.json         # Persistent URL configurations
├── agent.log           # Agent activity log
└── README.md           # This file
```

## Contract Details

- **Network**: GenLayer Bradbury Testnet
- **SDK**: py-genlayer v1
- **Size**: ~26 KB (under 28 KB limit)
- **Methods**: 10 write + 10 view
- **Storage**: TreeMap-based (accounts, cases, account_cases)
- **Consensus**: Equivalence Principle (leader proposes, validators verify)

## How It Works

1. **Register** an account with institution, jurisdiction, wallet, and chain
2. **Set terms URL** to enable T&C compliance checking
3. **Report violations** manually or let the agent **scan** automatically
4. The contract's LLM **drafts formal complaints** citing jurisdiction-specific laws
5. If the institution doesn't respond, the agent **auto-escalates** through regulatory tiers
6. **Check institution responses** — the LLM evaluates if the remedy is adequate
7. **Resolve** cases with recovery tracking

## License

MIT
