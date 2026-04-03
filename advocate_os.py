# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json

# AdvocateOS — Autonomous Consumer Advocacy Agent (Multi-Jurisdiction)

VIOLATION_TYPES = [
    "overcharge", "missed_deadline", "sla_breach",
    "unauthorized_fee", "interest_calculation_error", "disclosure_failure",
    "unauthorized_transfer", "yield_misrepresentation", "withdrawal_restriction",
]

SUPPORTED_CHAINS = [
    "ethereum", "base", "solana", "polygon", "arbitrum",
    "optimism", "avalanche", "bsc", "genlayer", "stellar",
]

JURISDICTIONS: dict[str, dict] = {
    "US": {
        "clauses": {
            "overcharge": "TILA 15 USC §1601; CFPB Reg Z; FCBA §161",
            "missed_deadline": "FCBA 15 USC §1666; EFTA §908; Reg E §1005.11",
            "sla_breach": "Dodd-Frank §1031; FTC Act §5; UCC Art.4",
            "unauthorized_fee": "EFTA 15 USC §1693; Reg E §1005.11; TILA §161",
            "interest_calculation_error": "TILA §128; Reg Z §1026.18; FCBA §163",
            "disclosure_failure": "TILA §127; ECOA 15 USC §1691; Reg Z §1026.17",
            "unauthorized_transfer": "EFTA §1693g; Reg E §1005.6; State MTL",
            "yield_misrepresentation": "SEC Howey; Dodd-Frank §1031; FTC Act §5",
            "withdrawal_restriction": "EFTA §1693h; Reg E §1005.11; UCC Art.4A",
        },
        "tiers": [
            "Company Internal",
            "CFPB / State Attorney General",
            "OCC / FDIC / FRB",
            "Small Claims / Federal District Court",
        ],
        "deadlines": [1209600, 2592000, 2592000, 0],
    },
    "EU": {
        "clauses": {
            "overcharge": "PSD2 Art.73-74; CRD 2011/83/EU Art.6",
            "missed_deadline": "PSD2 Art.87-88; CRD 2011/83/EU Art.21",
            "sla_breach": "CRD 2011/83/EU Art.18-22; UCPD 2005/29/EC Art.5",
            "unauthorized_fee": "PSD2 Art.73; PAD 2014/92/EU Art.17-18",
            "interest_calculation_error": "CCD 2008/48/EC Art.10; MCD 2014/17/EU Art.13",
            "disclosure_failure": "CRD 2011/83/EU Art.5-6; PSD2 Art.44-48",
            "unauthorized_transfer": "PSD2 Art.73; MiCA Reg 2023/1114 Art.67-68",
            "yield_misrepresentation": "MiCA Art.53; UCPD 2005/29/EC Art.6-7",
            "withdrawal_restriction": "PSD2 Art.78; MiCA Art.67; PAD Art.17",
        },
        "tiers": [
            "Company Internal",
            "National ADR / EU ODR Platform",
            "National Consumer Authority",
            "National Court / CJEU",
        ],
        "deadlines": [1209600, 2592000, 2592000, 0],
    },
}


def _jur(j: str) -> dict:
    return JURISDICTIONS.get(j, JURISDICTIONS["US"])


class AdvocateOS(gl.Contract):
    case_counter: u32
    account_counter: u32

    accounts: TreeMap[u32, str]
    cases: TreeMap[u32, str]
    account_cases: TreeMap[u32, str]
    owner_accounts: TreeMap[Address, str]
    admin: Address
    total_violations: u32
    total_escalations: u32
    total_resolved: u32

    def __init__(self):
        self.case_counter = u32(0)
        self.account_counter = u32(0)
        self.total_violations = u32(0)
        self.total_escalations = u32(0)
        self.total_resolved = u32(0)
        self.admin = gl.message.sender_address

    # ── ACCOUNT MANAGEMENT ──

    @gl.public.write
    def register_account(
        self,
        name: str,
        institution: str,
        account_ref: str,
        account_type: str,
        jurisdiction: str,
        chain: str,
    ):
        if jurisdiction not in JURISDICTIONS:
            raise gl.UserError(
                f"Unsupported jurisdiction: {jurisdiction}. "
                f"Use: {', '.join(JURISDICTIONS.keys())}"
            )
        if chain and chain not in SUPPORTED_CHAINS:
            raise gl.UserError(
                f"Unsupported chain: {chain}. "
                f"Use: {', '.join(SUPPORTED_CHAINS)}"
            )
        sender = gl.message.sender_address
        self.account_counter = u32(self.account_counter + u32(1))
        aid = self.account_counter
        record = json.dumps({
            "id": int(aid),
            "name": name,
            "institution": institution,
            "account_ref": account_ref,
            "account_type": account_type,
            "jurisdiction": jurisdiction,
            "wallet_address": sender.as_hex,
            "chain": chain,
            "terms_url": "",
            "active": True,
        }, sort_keys=True)
        self.accounts[aid] = record

        existing = self.owner_accounts.get(sender, "")
        if existing:
            self.owner_accounts[sender] = existing + "," + str(int(aid))
        else:
            self.owner_accounts[sender] = str(int(aid))

    @gl.public.write
    def set_terms_url(self, account_id: u32, terms_url: str):
        self._require_owner_or_admin(account_id)
        acc = json.loads(self.accounts[account_id])
        acc["terms_url"] = terms_url[:500]
        self.accounts[account_id] = json.dumps(acc, sort_keys=True)

    @gl.public.write
    def deactivate_account(self, account_id: u32):
        self._require_owner_or_admin(account_id)
        raw = self.accounts[account_id]
        acc = json.loads(raw)
        acc["active"] = False
        self.accounts[account_id] = json.dumps(acc, sort_keys=True)

    @gl.public.view
    def get_account(self, account_id: u32) -> str:
        return self.accounts[account_id]

    @gl.public.view
    def get_all_accounts(self) -> str:
        results: list[dict] = []
        i = u32(1)
        while i <= self.account_counter:
            try:
                results.append(json.loads(self.accounts[i]))
            except Exception:
                pass
            i = u32(i + u32(1))
        return json.dumps(results)

    # ── VIOLATION DETECTION ──

    @gl.public.write
    def scan_for_violations(self, account_id: u32, data_url: str):
        self._require_owner_or_admin(account_id)
        acc = json.loads(self.accounts[account_id])
        if not acc.get("active"):
            raise gl.UserError("Account is deactivated")

        institution = acc["institution"]
        account_type = acc["account_type"]
        jur = acc.get("jurisdiction", "US")
        terms_url = acc.get("terms_url", "")
        all_types = ", ".join(VIOLATION_TYPES)

        def leader_fn():
            web_data = gl.nondet.web.get(data_url)
            body = web_data.body if isinstance(web_data.body, str) else web_data.body.decode("utf-8")
            tc_section = ""
            if terms_url:
                try:
                    tc_data = gl.nondet.web.get(terms_url)
                    tc_body = tc_data.body if isinstance(tc_data.body, str) else tc_data.body.decode("utf-8")
                    tc_section = f"\n\nTerms & Conditions:\n{tc_body[:3000]}\n\nCheck if any account activity violates these T&C."
                except Exception:
                    tc_section = ""
            prompt = (
                f"You are a consumer protection analyst for {jur}. "
                f"Analyze the following account data for potential violations.\n\n"
                f"Institution: {institution}\nAccount type: {account_type}\n"
                f"Jurisdiction: {jur}\nKnown violation types: {all_types}\n\n"
                f"Account data:\n{body[:4000]}"
                f"{tc_section}\n\n"
                f"Return a JSON object with key 'violations' containing an array. "
                f"Each violation must have: 'type' (one of the known types), "
                f"'description' (brief factual summary), 'amount_disputed' (numeric, "
                f"0 if unknown), 'severity' (1-5). "
                f"If no violations found, return empty array.\n"
                f"Return ONLY valid JSON."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            if isinstance(result, str):
                result = json.loads(result)
            violations = result.get("violations", [])
            cleaned: list[dict] = []
            for v in violations:
                vtype = str(v.get("type", "")).strip()
                if vtype not in VIOLATION_TYPES:
                    continue
                cleaned.append({
                    "type": vtype,
                    "description": str(v.get("description", ""))[:500],
                    "amount_disputed": max(0, int(v.get("amount_disputed", 0))),
                    "severity": max(1, min(5, int(v.get("severity", 3)))),
                })
            return json.dumps({"violations": cleaned}, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_result.calldata)
            except Exception:
                return False
            validator_raw = leader_fn()
            validator_data = json.loads(validator_raw)
            leader_types = sorted([v["type"] for v in leader_data.get("violations", [])])
            validator_types = sorted([v["type"] for v in validator_data.get("violations", [])])
            return leader_types == validator_types

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        parsed = json.loads(raw_result)
        for v in parsed.get("violations", []):
            self._create_case(
                account_id, v["type"], v["description"],
                v["amount_disputed"], v["severity"], jur,
            )

    # ── MANUAL VIOLATION REPORTING ──

    @gl.public.write
    def report_violation(
        self,
        account_id: u32,
        violation_type: str,
        description: str,
        amount_disputed: u32,
        severity: u32,
    ):
        self._require_owner_or_admin(account_id)
        if violation_type not in VIOLATION_TYPES:
            raise gl.UserError(f"Unknown violation type: {violation_type}")
        acc = json.loads(self.accounts[account_id])
        if not acc.get("active"):
            raise gl.UserError("Account is deactivated")
        jur = acc.get("jurisdiction", "US")
        self._create_case(
            account_id, violation_type, description,
            int(amount_disputed), int(severity), jur,
        )

    # ── COMPLAINT DRAFTING ──

    @gl.public.write
    def draft_complaint(self, case_id: u32):
        self._require_case_owner_or_admin(case_id)
        case = json.loads(self.cases[case_id])
        if case.get("status") == "resolved":
            raise gl.UserError("Case already resolved")

        acc = json.loads(self.accounts[u32(case["account_id"])])
        jur = case.get("jurisdiction", "US")
        jdata = _jur(jur)
        violation_type = case["violation_type"]
        legal_refs = jdata["clauses"].get(violation_type, "")
        tier = case.get("current_tier", 0)
        target_body = jdata["tiers"][tier] if tier < len(jdata["tiers"]) else ""

        def leader_fn():
            prompt = (
                f"You are a consumer rights solicitor practicing in {jur}. "
                f"Draft a formal complaint letter for the following case.\n\n"
                f"TO: {target_body}\n"
                f"RE: {acc['institution']} — Account {acc['account_ref']}\n"
                f"Jurisdiction: {jur}\nViolation type: {violation_type}\n"
                f"Description: {case['description']}\n"
                f"Amount disputed: {case['amount_disputed']}\n"
                f"Escalation tier: {target_body}\n\n"
                f"LEGAL REFERENCES (cite these plus any other relevant {jur} laws):\n"
                f"{legal_refs}\n\n"
                f"Requirements:\n"
                f"- Formal tone, addressed to the correct body for {jur}\n"
                f"- State the specific violation with dates/amounts\n"
                f"- Cite each applicable legal clause explicitly\n"
                f"- State the remedy sought\n"
                f"- Set a response deadline of 14 days\n"
                f"- Mention escalation to the next tier if unresolved\n\n"
                f"Return JSON with keys: 'subject' (string), 'body' (string), "
                f"'legal_clauses_cited' (array of strings), 'remedy_sought' "
                f"(string), 'deadline_days' (integer).\n"
                f"Return ONLY valid JSON."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            if isinstance(result, str):
                result = json.loads(result)
            return json.dumps({
                "subject": str(result.get("subject", ""))[:200],
                "body": str(result.get("body", ""))[:3000],
                "legal_clauses_cited": [str(c)[:100] for c in result.get("legal_clauses_cited", [])][:10],
                "remedy_sought": str(result.get("remedy_sought", ""))[:500],
                "deadline_days": max(7, min(30, int(result.get("deadline_days", 14)))),
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_result.calldata)
            except Exception:
                return False
            if not leader_data.get("body") or not leader_data.get("subject"):
                return False
            cited = leader_data.get("legal_clauses_cited", [])
            if len(cited) == 0:
                return False
            validator_raw = leader_fn()
            validator_data = json.loads(validator_raw)
            leader_set = set(c.lower()[:50] for c in cited)
            validator_set = set(
                c.lower()[:50] for c in validator_data.get("legal_clauses_cited", [])
            )
            return len(leader_set & validator_set) >= 1

        raw_complaint = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        complaint = json.loads(raw_complaint)

        case["complaints"] = case.get("complaints", [])
        case["complaints"].append({
            "tier": tier,
            "subject": complaint["subject"],
            "body": complaint["body"],
            "legal_clauses_cited": complaint["legal_clauses_cited"],
            "remedy_sought": complaint["remedy_sought"],
            "deadline_days": complaint["deadline_days"],
            "drafted_at": case.get("updated_at", case.get("created_at", "")),
        })
        case["status"] = "complaint_drafted"
        self.cases[case_id] = json.dumps(case, sort_keys=True)

    # ── ESCALATION ENGINE ──

    @gl.public.write
    def escalate(self, case_id: u32):
        self._require_case_owner_or_admin(case_id)
        case = json.loads(self.cases[case_id])
        if case.get("status") == "resolved":
            raise gl.UserError("Case already resolved")

        current_tier = case.get("current_tier", 0)
        if current_tier >= 3:
            raise gl.UserError("Already at maximum escalation tier")

        jur = case.get("jurisdiction", "US")
        tiers = _jur(jur)["tiers"]
        new_tier = current_tier + 1
        case["current_tier"] = new_tier
        case["status"] = "escalated"
        case["escalation_history"] = case.get("escalation_history", [])
        case["escalation_history"].append({
            "from_tier": current_tier,
            "to_tier": new_tier,
            "from_body": tiers[current_tier] if current_tier < len(tiers) else "",
            "to_body": tiers[new_tier] if new_tier < len(tiers) else "",
            "reason": "No satisfactory response within deadline",
        })
        self.cases[case_id] = json.dumps(case, sort_keys=True)
        self.total_escalations = u32(self.total_escalations + u32(1))

    @gl.public.write
    def check_and_auto_escalate(self, case_id: u32, current_timestamp: u32):
        self._require_case_owner_or_admin(case_id)
        case = json.loads(self.cases[case_id])

        if case.get("status") == "resolved":
            raise gl.UserError("Case already resolved")

        current_tier = case.get("current_tier", 0)
        if current_tier >= 3:
            raise gl.UserError("Cannot auto-escalate beyond final tier")

        jur = case.get("jurisdiction", "US")
        jdata = _jur(jur)
        deadlines = jdata["deadlines"]
        deadline_seconds = deadlines[current_tier] if current_tier < len(deadlines) else 0
        if deadline_seconds == 0:
            raise gl.UserError("No auto-escalation for this tier")

        complaints = case.get("complaints", [])
        tier_complaints = [c for c in complaints if c.get("tier") == current_tier]
        if not tier_complaints:
            raise gl.UserError("No complaint drafted for current tier yet")

        tiers = jdata["tiers"]
        new_tier = current_tier + 1
        case["current_tier"] = new_tier
        case["status"] = "auto_escalated"
        case["escalation_history"] = case.get("escalation_history", [])
        case["escalation_history"].append({
            "from_tier": current_tier,
            "to_tier": new_tier,
            "from_body": tiers[current_tier] if current_tier < len(tiers) else "",
            "to_body": tiers[new_tier] if new_tier < len(tiers) else "",
            "reason": f"Auto-escalated: no response within {deadline_seconds // 86400} days",
        })
        self.cases[case_id] = json.dumps(case, sort_keys=True)
        self.total_escalations = u32(self.total_escalations + u32(1))

    # ── RESOLUTION ──

    @gl.public.write
    def resolve_case(self, case_id: u32, resolution_note: str, amount_recovered: u32):
        self._require_case_owner_or_admin(case_id)
        case = json.loads(self.cases[case_id])
        if case.get("status") == "resolved":
            raise gl.UserError("Case already resolved")
        case["status"] = "resolved"
        case["resolution_note"] = resolution_note[:1000]
        case["amount_recovered"] = int(amount_recovered)
        self.cases[case_id] = json.dumps(case, sort_keys=True)
        self.total_resolved = u32(self.total_resolved + u32(1))

    # ── INSTITUTION RESPONSE CHECK ──

    @gl.public.write
    def check_institution_response(self, case_id: u32, response_url: str):
        self._require_case_owner_or_admin(case_id)
        case = json.loads(self.cases[case_id])
        if case.get("status") == "resolved":
            raise gl.UserError("Case already resolved")

        violation_type = case["violation_type"]
        acc = json.loads(self.accounts[u32(case["account_id"])])
        jur = case.get("jurisdiction", "US")

        def leader_fn():
            web_data = gl.nondet.web.get(response_url)
            body = web_data.body if isinstance(web_data.body, str) else web_data.body.decode("utf-8")
            prompt = (
                f"You are a consumer rights analyst for {jur}. Evaluate the "
                f"institution's response to a complaint.\n\n"
                f"Institution: {acc['institution']}\nJurisdiction: {jur}\n"
                f"Violation type: {violation_type}\n"
                f"Original complaint: {case['description'][:500]}\n"
                f"Amount disputed: {case['amount_disputed']}\n\n"
                f"Institution's response:\n{body[:4000]}\n\n"
                f"Determine:\n"
                f"1. Has the institution acknowledged the issue?\n"
                f"2. Have they offered adequate remedy?\n"
                f"3. Should this case be escalated or resolved?\n\n"
                f"Return JSON with keys: 'acknowledged' (bool), 'remedy_offered' "
                f"(bool), 'remedy_adequate' (bool), 'recommendation' ('resolve' "
                f"or 'escalate'), 'summary' (brief string).\n"
                f"Return ONLY valid JSON."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            if isinstance(result, str):
                result = json.loads(result)
            return json.dumps({
                "acknowledged": bool(result.get("acknowledged", False)),
                "remedy_offered": bool(result.get("remedy_offered", False)),
                "remedy_adequate": bool(result.get("remedy_adequate", False)),
                "recommendation": str(result.get("recommendation", "escalate"))[:20],
                "summary": str(result.get("summary", ""))[:500],
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_result.calldata)
            except Exception:
                return False
            validator_raw = leader_fn()
            validator_data = json.loads(validator_raw)
            return leader_data.get("recommendation") == validator_data.get("recommendation")

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        analysis = json.loads(raw_result)

        case["response_analyses"] = case.get("response_analyses", [])
        case["response_analyses"].append(analysis)

        if analysis.get("recommendation") == "resolve" and analysis.get("remedy_adequate"):
            case["status"] = "institution_resolved"
        else:
            case["status"] = "escalation_recommended"

        self.cases[case_id] = json.dumps(case, sort_keys=True)

    # ── VIEW METHODS ──

    @gl.public.view
    def get_case(self, case_id: u32) -> str:
        return self.cases[case_id]

    @gl.public.view
    def get_cases_for_account(self, account_id: u32) -> str:
        idx = self.account_cases.get(account_id, "")
        if not idx:
            return "[]"
        case_ids = [x.strip() for x in idx.split(",") if x.strip()]
        results: list[dict] = []
        for cid_str in case_ids:
            try:
                results.append(json.loads(self.cases[u32(int(cid_str))]))
            except Exception:
                pass
        return json.dumps(results)

    @gl.public.view
    def get_open_cases(self) -> str:
        results: list[dict] = []
        i = u32(1)
        while i <= self.case_counter:
            try:
                case = json.loads(self.cases[i])
                if case.get("status") != "resolved":
                    results.append(case)
            except Exception:
                pass
            i = u32(i + u32(1))
        return json.dumps(results)

    @gl.public.view
    def get_case_summary(self, case_id: u32) -> str:
        case = json.loads(self.cases[case_id])
        jur = case.get("jurisdiction", "US")
        tiers = _jur(jur)["tiers"]
        ct = case.get("current_tier", 0)
        return json.dumps({
            "id": case.get("id"),
            "violation_type": case.get("violation_type"),
            "status": case.get("status"),
            "jurisdiction": jur,
            "current_tier": ct,
            "current_body": tiers[ct] if ct < len(tiers) else "",
            "amount_disputed": case.get("amount_disputed"),
            "severity": case.get("severity"),
            "num_complaints": len(case.get("complaints", [])),
            "num_escalations": len(case.get("escalation_history", [])),
        })

    @gl.public.view
    def get_stats(self) -> str:
        return json.dumps({
            "total_accounts": int(self.account_counter),
            "total_violations": int(self.total_violations),
            "total_escalations": int(self.total_escalations),
            "total_resolved": int(self.total_resolved),
            "open_cases": int(self.case_counter) - int(self.total_resolved),
        })

    @gl.public.view
    def get_legal_clauses(self, jurisdiction: str, violation_type: str) -> str:
        if jurisdiction not in JURISDICTIONS:
            raise gl.UserError(f"Unsupported jurisdiction: {jurisdiction}")
        jdata = _jur(jurisdiction)
        if violation_type not in jdata["clauses"]:
            raise gl.UserError(f"Unknown violation type: {violation_type}")
        return json.dumps({
            "jurisdiction": jurisdiction,
            "violation_type": violation_type,
            "clauses": jdata["clauses"][violation_type],
            "escalation_tiers": {str(i): t for i, t in enumerate(jdata["tiers"])},
        })

    @gl.public.view
    def get_escalation_path(self, case_id: u32) -> str:
        case = json.loads(self.cases[case_id])
        jur = case.get("jurisdiction", "US")
        jdata = _jur(jur)
        current_tier = case.get("current_tier", 0)
        path: list[dict] = []
        for t in range(len(jdata["tiers"])):
            dl = jdata["deadlines"][t] if t < len(jdata["deadlines"]) else 0
            path.append({
                "tier": t,
                "body": jdata["tiers"][t],
                "deadline_days": dl // 86400,
                "status": "current" if t == current_tier else (
                    "completed" if t < current_tier else "pending"
                ),
            })
        return json.dumps({
            "case_id": int(case_id),
            "jurisdiction": jur,
            "current_tier": current_tier,
            "path": path,
            "history": case.get("escalation_history", []),
        })

    @gl.public.view
    def get_supported_jurisdictions(self) -> str:
        result: list[dict] = []
        for code, jdata in JURISDICTIONS.items():
            result.append({
                "code": code,
                "tiers": jdata["tiers"],
                "violation_types": list(jdata["clauses"].keys()),
            })
        return json.dumps(result)

    @gl.public.view
    def get_accounts_by_wallet(self, wallet_address: str) -> str:
        results: list[dict] = []
        i = u32(1)
        while i <= self.account_counter:
            try:
                acc = json.loads(self.accounts[i])
                if acc.get("wallet_address", "").lower() == wallet_address.lower():
                    results.append(acc)
            except Exception:
                pass
            i = u32(i + u32(1))
        return json.dumps(results)

    # ── INTERNAL HELPERS ──

    def _is_admin(self) -> bool:
        return gl.message.sender_address == self.admin

    def _is_owner(self, account_id: u32) -> bool:
        owner_list = self.owner_accounts.get(gl.message.sender_address, "")
        if not owner_list:
            return False
        return str(int(account_id)) in [x.strip() for x in owner_list.split(",")]

    def _require_owner_or_admin(self, account_id: u32):
        if self._is_admin():
            return
        if not self._is_owner(account_id):
            raise gl.UserError("Only account owner or admin can perform this action")

    def _require_case_owner_or_admin(self, case_id: u32):
        if self._is_admin():
            return
        case = json.loads(self.cases[case_id])
        aid = u32(case["account_id"])
        if not self._is_owner(aid):
            raise gl.UserError("Only case owner or admin can perform this action")

    def _create_case(
        self,
        account_id: u32,
        violation_type: str,
        description: str,
        amount_disputed: int,
        severity: int,
        jurisdiction: str,
    ):
        self.case_counter = u32(self.case_counter + u32(1))
        cid = self.case_counter

        case = {
            "id": int(cid),
            "account_id": int(account_id),
            "violation_type": violation_type,
            "description": description[:1000],
            "amount_disputed": amount_disputed,
            "severity": max(1, min(5, severity)),
            "jurisdiction": jurisdiction,
            "current_tier": 0,
            "status": "open",
            "complaints": [],
            "escalation_history": [],
            "response_analyses": [],
            "resolution_note": "",
            "amount_recovered": 0,
        }
        self.cases[cid] = json.dumps(case, sort_keys=True)
        self.total_violations = u32(self.total_violations + u32(1))

        existing = self.account_cases.get(account_id, "")
        if existing:
            self.account_cases[account_id] = existing + "," + str(int(cid))
        else:
            self.account_cases[account_id] = str(int(cid))
