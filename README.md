# AdvocateOS — Onchain Consumer Justice Agent

> **GenLayer Bradbury Hackathon — Onchain Justice Track**
>
> An AI-powered autonomous consumer protection system built on [GenLayer](https://genlayer.com). AdvocateOS monitors financial accounts, detects violations using AI consensus, drafts legally-grounded complaint letters, and autonomously escalates through regulatory bodies — all on-chain with the Equivalence Principle.

**Live Demo**: [advocate-os.vercel.app](https://advocate-os.vercel.app/)
**Contract**: [`0x2e75bc5796791b20b645b17dcf2a9dfc052c83ab`](https://explorer.genlayer.com/contracts/0x2e75bc5796791b20b645b17dcf2a9dfc052c83ab) on Bradbury Testnet

---

## Why AdvocateOS?

Every year consumers lose billions to overcharges, hidden fees, and SLA breaches. Filing complaints is slow, confusing, and most people give up. AdvocateOS automates the entire process — from detection to legal escalation — using GenLayer's Intelligent Contract with AI-in-the-loop consensus.

**The Equivalence Principle in action:**
- **Leader node** scans account data and uses an LLM to identify violations
- **Validator nodes** independently run the same analysis and confirm the violation types match
- Same pattern for complaint drafting (validators verify legal clauses cited) and institution response analysis (validators verify recommendation)

This means **no single AI can fabricate a violation** — the decentralized consensus ensures fair, verifiable justice.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  React Frontend (Vercel)                   │
│         EIP-6963 Wallet Connect • Role-Based UI           │
│    User: Register, Report, Track   Admin: Manage, Resolve │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTPS (Vercel rewrite proxy)
┌──────────────────────┴───────────────────────────────────┐
│            Flask API + Autonomous Agent (Oracle Cloud)     │
│  REST endpoints ↔ GenLayer CLI ↔ Bradbury Testnet         │
│  Agent loop: SCAN → DETECT → DRAFT → WATCH → ESCALATE    │
└──────────────────────┬───────────────────────────────────┘
                       │ GenLayer CLI (genlayer call/write)
┌──────────────────────┴───────────────────────────────────┐
│        Intelligent Contract (advocate_os.py)               │
│            GenLayer Bradbury Testnet                       │
│                                                           │
│  Equivalence Principle (run_nondet_unsafe):                │
│  ┌─────────────┐   ┌──────────────────┐                  │
│  │   Leader     │──▶│   Validators     │                  │
│  │  LLM scan    │   │  Independent LLM │                  │
│  │  proposes    │   │  verify result   │                  │
│  └─────────────┘   └──────────────────┘                  │
│                                                           │
│  On-chain state:                                          │
│  • Account registry (wallet + chain + T&C URL)            │
│  • AI violation detection (web fetch + LLM analysis)      │
│  • AI complaint drafting (jurisdiction-aware legal refs)   │
│  • 4-tier escalation engine per jurisdiction              │
│  • AI institution response analysis                       │
└───────────────────────────────────────────────────────────┘
```

---

## How It Uses GenLayer

### Equivalence Principle — 3 Core AI Functions

| Function | Leader Does | Validator Checks |
|---|---|---|
| `scan_for_violations` | Fetches account data via `gl.nondet.web.get`, runs LLM to identify violations | Re-runs same analysis, confirms violation **types** match |
| `draft_complaint` | LLM drafts formal complaint with legal citations | Re-drafts independently, confirms at least 1 legal clause overlaps |
| `check_institution_response` | Fetches institution's reply, LLM evaluates remedy | Re-evaluates, confirms recommendation (resolve/escalate) matches |

All three use `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` — the core Equivalence Principle pattern.

### Non-Deterministic Operations
- `gl.nondet.web.get()` — Fetches real-world account data and institution responses
- `gl.nondet.exec_prompt()` — LLM-powered analysis with JSON structured output

---

## Features

- **Multi-jurisdiction** — US (TILA, CFPB, EFTA, Dodd-Frank) and EU (PSD2, MiCA, PAD, CRD) legal frameworks
- **10-chain support** — Ethereum, Base, Solana, Polygon, Arbitrum, Optimism, Avalanche, BSC, GenLayer, Stellar
- **9 violation types** — overcharge, missed_deadline, sla_breach, unauthorized_fee, interest_calculation_error, disclosure_failure, unauthorized_transfer, yield_misrepresentation, withdrawal_restriction
- **AI-drafted complaints** — Formal letters citing exact legal clauses per jurisdiction and escalation tier
- **4-tier escalation** — Company Internal → Regulator (CFPB/ADR) → Authority (OCC/NCA) → Court
- **T&C compliance** — Compares account activity against institution's own terms
- **Autonomous agent** — Background service scans, drafts, monitors deadlines, auto-escalates
- **EIP-6963 wallet connect** — Dynamic multi-wallet discovery (MetaMask, Rabby, etc.)
- **personal_sign verification** — Cryptographic wallet ownership proof
- **Role-based UI** — Admin dashboard for oversight, User dashboard for self-service

---

## Violation Types

| Type | Description | US Law | EU Law |
|------|-------------|--------|--------|
| `overcharge` | Excessive fees or charges | TILA §1601; CFPB Reg Z | PSD2 Art.73-74 |
| `missed_deadline` | Institution failed to act in time | FCBA §1666; EFTA §908 | PSD2 Art.87-88 |
| `sla_breach` | Service level violation | Dodd-Frank §1031; FTC Act §5 | CRD Art.18-22 |
| `unauthorized_fee` | Fee without consent | EFTA §1693; Reg E | PSD2 Art.73; PAD Art.17-18 |
| `interest_calculation_error` | Incorrect interest | TILA §128; Reg Z | CCD Art.10; MCD Art.13 |
| `disclosure_failure` | Required info not provided | TILA §127; ECOA §1691 | CRD Art.5-6; PSD2 Art.44-48 |
| `unauthorized_transfer` | Funds moved without auth | EFTA §1693g; State MTL | PSD2 Art.73; MiCA Art.67-68 |
| `yield_misrepresentation` | Advertised yield ≠ actual | SEC Howey; Dodd-Frank | MiCA Art.53; UCPD Art.6-7 |
| `withdrawal_restriction` | Blocked fund access | EFTA §1693h; UCC Art.4A | PSD2 Art.78; MiCA Art.67 |

---

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

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [GenLayer CLI](https://docs.genlayer.com) (`npm install -g genlayer`)

### Backend

```bash
git clone https://github.com/Kodark220/AdvocateOS.git
cd AdvocateOS
pip install -r requirements.txt

# Configure GenLayer
genlayer init
genlayer account import --name my-account --private-key <key>
genlayer config set --network testnet-bradbury

# Deploy contract
genlayer deploy --contract advocate_os.py
# Copy the contract address

# Set environment variables
export AOS_CONTRACT=<your-contract-address>
export AOS_SECRET_KEY=<random-secret>
export AOS_KEYSTORE_PASSWORD=<your-keystore-password>

# Run
gunicorn dashboard:app --bind 0.0.0.0:5000 --timeout 660
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env  # Set VITE_API_URL and VITE_ADMIN_WALLET
npm run dev
```

### Autonomous Agent

```bash
python agent.py run  # Scans every hour, processes cases every 30 min
```

---

## Project Structure

```
AdvocateOS/
├── advocate_os.py      # GenLayer Intelligent Contract (~26 KB)
│                       #   3 Equivalence Principle functions
│                       #   10 write + 10 view methods
├── dashboard.py        # Flask API (REST → GenLayer CLI bridge)
├── agent.py            # Autonomous watchdog agent
├── notifications.py    # Webhook + email alert layer
├── config.json         # Runtime configuration
├── requirements.txt    # Python dependencies
└── frontend/
    ├── src/
    │   ├── context/WalletContext.jsx   # EIP-6963 + personal_sign
    │   ├── pages/ConnectPage.jsx       # Multi-wallet connect
    │   ├── pages/Dashboard.jsx         # Admin overview
    │   ├── pages/user/UserDashboard.jsx # User self-service
    │   ├── pages/user/ReportPage.jsx   # Violation reporting
    │   ├── pages/user/RegisterPage.jsx # Account registration
    │   ├── pages/Incidents.jsx         # Case management
    │   └── pages/CaseDetail.jsx        # Full case + complaint view
    └── vercel.json                     # Rewrite proxy config
```

## Contract Details

- **Network**: GenLayer Bradbury Testnet
- **Address**: `0x2e75bc5796791b20b645b17dcf2a9dfc052c83ab`
- **SDK**: py-genlayer v1
- **Size**: ~26 KB (under 28 KB limit)
- **Methods**: 10 write + 10 view
- **Storage**: TreeMap-based (accounts, cases, account_cases)
- **Consensus**: Equivalence Principle via `run_nondet_unsafe`

---

## How It Works

1. **Connect Wallet** — EIP-6963 discovers installed wallets, user signs with `personal_sign`
2. **Register Account** — Link your bank/neobank/DeFi account with institution, jurisdiction, and chain
3. **Set Terms URL** — Point to institution's T&C for compliance checking
4. **Detect Violations** — AI scans account data, consensus validates findings
5. **Draft Complaint** — AI generates formal complaint citing jurisdiction-specific laws
6. **Monitor Response** — AI evaluates institution's reply for adequacy
7. **Auto-Escalate** — If no response within deadline, escalate to next regulatory tier
8. **Resolve** — Track recovery amount and close case

---

## Tech Stack

| Layer | Technology |
|---|---|
| Smart Contract | GenLayer Intelligent Contract (Python) |
| Consensus | Optimistic Democracy + Equivalence Principle |
| Backend | Flask + Gunicorn + GenLayer CLI |
| Frontend | React + Vite + TailwindCSS |
| Wallet | EIP-6963 / EIP-1193 + personal_sign |
| Hosting | Vercel (frontend) + Oracle Cloud (backend) |
| Agent | Python autonomous loop with systemd |

---

## Roadmap

- **Internet Court Integration** — Escalate unresolved cases directly to [Internet Court](https://internetcourt.org/) for on-chain arbitration. AdvocateOS builds the legal case; Internet Court's AI jury delivers the verdict. *The lawyer meets the judge — a composable justice stack on GenLayer.*
- **More Jurisdictions** — UK (FCA), India (RBI), Brazil (BACEN) regulatory frameworks
- **DeFi Protocol Scanning** — Direct on-chain monitoring of lending rates, yield promises, and fee structures via `gl.nondet.web.get`
- **Multi-language Complaints** — AI-drafted complaints in the consumer's native language
- **DAO Governance** — Community voting on escalation policies and supported violation types

---

## Team

Built for the GenLayer Bradbury Hackathon — Onchain Justice Track

## License

MIT
