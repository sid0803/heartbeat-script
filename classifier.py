import re
import time
from typing import List, Dict, Any
from signals import BusinessEvent, Severity, CLIENT_RISK, DEADLINE_RISK, SYSTEM_FAILURE, TEAM_BLOCKER, REVENUE_RISK, COMMUNICATION_GAP, OPPORTUNITY_SIGNAL

# ── Tunable thresholds ──────────────────────────────────────────────────────
CLIENT_WAIT_URGENT_HOURS   = 4    
CLIENT_WAIT_CRITICAL_HOURS = 12   
PR_STALE_HOURS             = 24   
TASK_OVERDUE_HOURS         = 0    
INVOICE_KEYWORDS = {"invoice", "payment", "refund", "billing", "overdue", "outstanding", "owe"}
OPPORTUNITY_KEYWORDS = {"shipped", "launched", "closed", "signed", "approved", "milestone", "congrats"}


def rule_client_risk(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        if e.get("type") not in ("client_message", "client_email"): continue
        age   = e.get("age_hours", 0.0)
        client = e.get("client") or _extract_name(e.get("content", ""))
        if age < CLIENT_WAIT_URGENT_HOURS: continue
        sev = Severity.CRITICAL if age >= CLIENT_WAIT_CRITICAL_HOURS else Severity.URGENT
        results.append(BusinessEvent(
            signal_type = CLIENT_RISK,
            severity    = sev,
            message     = f"{client or 'A client'} has been waiting {age:.0f} hours for a response.",
            action      = f"Reply to {client or 'client'} now.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.9,
            raw_content = e.get("content", ""),
        ))
    return results

def rule_deadline_risk(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        if e.get("type") != "task_overdue": continue
        age    = e.get("age_hours", 0.0)
        title  = _extract_title(e.get("content", "")) or "Unknown task"
        client = e.get("client", "")
        sev    = Severity.CRITICAL if age > 48 else Severity.URGENT
        results.append(BusinessEvent(
            signal_type = DEADLINE_RISK,
            severity    = sev,
            message     = f"'{title}' is overdue by {age:.0f} hours.",
            action      = f"Immediately assign or reschedule '{title}'.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.95,
            raw_content = e.get("content", ""),
        ))
    return results

def rule_system_failure(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        if e.get("source") != "health_check": continue
        status = e.get("status", "") or ""
        content = e.get("content", "")
        if "DOWN" not in status.upper() and "DOWN" not in content.upper(): continue
        service = e.get("url") or e.get("content", "Unknown service")
        results.append(BusinessEvent(
            signal_type = SYSTEM_FAILURE,
            severity    = Severity.CRITICAL,
            message     = f"Service is DOWN: {service}",
            action      = "Alert engineering leading immediately.",
            source      = "health_check",
            age_hours   = e.get("age_hours", 0.0),
            confidence  = 1.0,
            raw_content = content,
        ))
    return results

def rule_team_blocker(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        if e.get("type") not in ("pr_stale", "issue_open"): continue
        age   = e.get("age_hours", 0.0)
        if age < PR_STALE_HOURS: continue
        title = _extract_title(e.get("content", "")) or "untitled PR/issue"
        sev   = Severity.CRITICAL if age > 72 else Severity.URGENT
        results.append(BusinessEvent(
            signal_type = TEAM_BLOCKER,
            severity    = sev,
            message     = f"'{title}' has been stale for {age:.0f} hours.",
            action      = f"Review '{title}' today.",
            source      = e.get("source", ""),
            age_hours   = age,
            confidence  = 0.85,
            raw_content = e.get("content", ""),
        ))
    return results

def rule_revenue_risk(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        content_lc = e.get("content", "").lower()
        if not any(kw in content_lc for kw in INVOICE_KEYWORDS): continue
        client = e.get("client") or _extract_name(content_lc)
        age    = e.get("age_hours", 0.0)
        title  = _extract_title(e.get("content", "")) or "Payment issue"
        results.append(BusinessEvent(
            signal_type = REVENUE_RISK,
            severity    = Severity.CRITICAL,
            message     = f"Revenue signal: '{title}'",
            action      = "Handle this immediately.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.80,
            raw_content = e.get("content", ""),
        ))
    return results

def rule_communication_gap(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        if e.get("type") not in ("team_update", "general"): continue
        age    = e.get("age_hours", 0.0)
        if age < CLIENT_WAIT_URGENT_HOURS * 2: continue
        content_lc = e.get("content", "").lower()
        if not any(s in content_lc for s in {"waiting", "follow up", "update", "reply"}): continue
        results.append(BusinessEvent(
            signal_type = COMMUNICATION_GAP,
            severity    = Severity.URGENT,
            message     = f"Communication gap in {e.get('source','source')}.",
            action      = "Send a quick status update.",
            source      = e.get("source", ""),
            age_hours   = age,
            confidence  = 0.70,
            raw_content = e.get("content", ""),
        ))
    return results

def rule_opportunity_signal(events: List[Dict]) -> List[BusinessEvent]:
    results = []
    for e in events:
        content_lc = e.get("content", "").lower()
        if not any(kw in content_lc for kw in OPPORTUNITY_KEYWORDS): continue
        title = _extract_title(e.get("content", "")) or "Milestone"
        results.append(BusinessEvent(
            signal_type = OPPORTUNITY_SIGNAL,
            severity    = Severity.INFO,
            message     = f"Positive signal: {title}",
            action      = "Acknowledge win.",
            source      = e.get("source", ""),
            age_hours   = e.get("age_hours", 0.0),
            confidence  = 0.75,
            raw_content = e.get("content", ""),
        ))
    return results

def _extract_name(text: str) -> str:
    m = re.search(r"(client|customer|from)[:\s]+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)", text)
    return m.group(2) if m else ""

def _extract_title(text: str) -> str:
    m = re.search(r"'([^']{3,60})'|\"([^\"]{3,60})\"", text)
    if m: return m.group(1) or m.group(2)
    cleaned = re.sub(r"^(Email from|Notion task|PR #\d+:|Issue #\d+:)\s*", "", text, flags=re.IGNORECASE)
    return cleaned[:60].strip()


class Classifier:
    RULES = [rule_system_failure, rule_revenue_risk, rule_client_risk, rule_deadline_risk, rule_team_blocker, rule_communication_gap, rule_opportunity_signal]
    def __init__(self, min_confidence: float = 0.65): self.min_confidence = min_confidence

    def _calculate_score(self, event: Dict[str, Any]) -> float:
        score = 0.0
        content = event.get("content", "").lower()
        if any(kw in content for kw in ["delay", "overdue", "late", "missed"]): score += 2.0
        if any(kw in content for kw in ["error", "failure", "crash", "down"]): score += 3.0
        if any(kw in content for kw in ["unhappy", "angry", "complaint", "lost"]): score += 3.0
        if any(kw in content for kw in ["invoice", "payment", "billing"]): score += 2.0
        if event.get("age_hours", 0.0) > 24: score += 1.0
        return min(score, 10.0)

    def analyze(self, processed_events: List[Dict[str, Any]]) -> List[BusinessEvent]:
        all_events = []
        for rule in self.RULES:
            try:
                detected = rule(processed_events)
                all_events.extend([e for e in detected if e.confidence >= self.min_confidence])
            except Exception as ex: print(f"⚠️ rule error: {ex}")
        for e in processed_events:
            if not any(ev.raw_content == e.get("content") for ev in all_events):
                score = self._calculate_score(e)
                if score >= 2.0:
                    sev = Severity.CRITICAL if score >= 5.0 else Severity.URGENT
                    all_events.append(BusinessEvent(signal_type="scored_signal", severity=sev, message=f"Risk detected: {e.get('content')[:60]}...", action="Review signal.", source=e.get("source", ""), age_hours=e.get("age_hours", 0.0), confidence=score/10.0, raw_content=e.get("content", "")))
        seen = set()
        unique_events = []
        for ev in all_events:
            key = (ev.signal_type, ev.source, ev.message[:30])
            if key not in seen: seen.add(key); unique_events.append(ev)
        _order = {Severity.CRITICAL: 0, Severity.URGENT: 1, Severity.INFO: 2}
        unique_events.sort(key=lambda x: _order.get(x.severity, 3))
        print(f"🧠 Intelligence Layer: {len(unique_events)} signals detected.")
        return unique_events
