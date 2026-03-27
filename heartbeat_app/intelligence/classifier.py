"""
Founder Brain — Rule Engine for Heartbeat System.

This is the MOST IMPORTANT module in the system.

It converts raw, enriched processor events into structured BusinessEvents
that answer the founder's real question: "What should I DO right now?"

Each rule is a small, independently testable function.
Rules are registered in `RuleEngine.rules` and run against every batch of events.

Design principles:
  • Simple rules > complex ML (explainable, debuggable, fast)
  • Every rule produces zero or more BusinessEvents
  • Rules compose — they see the full event list, not just one at a time
  • Confidence scoring allows filtering noise
"""
import re
from typing import List, Dict, Any

from .signals import (
    BusinessEvent, Severity,
    CLIENT_RISK, DEADLINE_RISK, SYSTEM_FAILURE,
    TEAM_BLOCKER, REVENUE_RISK, COMMUNICATION_GAP, OPPORTUNITY_SIGNAL,
)

# ── Tunable thresholds ──────────────────────────────────────────────────────
CLIENT_WAIT_URGENT_HOURS   = 4    # Hours without reply → URGENT
CLIENT_WAIT_CRITICAL_HOURS = 12   # Hours without reply → CRITICAL
PR_STALE_HOURS             = 24   # Hours for a PR to be "stale"
TASK_OVERDUE_HOURS         = 0    # Any overdue = immediate URGENT
INVOICE_KEYWORDS = {"invoice", "payment", "refund", "billing", "overdue", "outstanding", "owe"}
OPPORTUNITY_KEYWORDS = {"shipped", "launched", "closed", "signed", "approved", "milestone", "congrats"}


# ── Individual rule functions ─────────────────────────────────────────────────

def rule_client_risk(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects client messages that have gone unanswered too long.
    Source: Slack (client_message), Gmail (client_email)
    """
    results = []
    for e in events:
        if e.get("type") not in ("client_message", "client_email"):
            continue
        age   = e.get("age_hours", 0.0)
        client = e.get("client") or _extract_name(e.get("content", ""))
        if age < CLIENT_WAIT_URGENT_HOURS:
            continue

        sev = Severity.CRITICAL if age >= CLIENT_WAIT_CRITICAL_HOURS else Severity.URGENT
        results.append(BusinessEvent(
            signal_type = CLIENT_RISK,
            severity    = sev,
            message     = f"{client or 'A client'} has been waiting {age:.0f} hours for a response.",
            action      = f"Reply to {client or 'client'} now — risk of losing trust increases with every hour.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.9,
            raw_content = e.get("content", ""),
        ))
    return results


def rule_deadline_risk(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects overdue tasks from Notion or any connector with type=task_overdue.
    """
    results = []
    for e in events:
        if e.get("type") != "task_overdue":
            continue
        age    = e.get("age_hours", 0.0)
        title  = _extract_title(e.get("content", "")) or "Unknown task"
        client = e.get("client", "")
        sev    = Severity.CRITICAL if age > 48 else Severity.URGENT
        results.append(BusinessEvent(
            signal_type = DEADLINE_RISK,
            severity    = sev,
            message     = f"'{title}' is overdue by {age:.0f} hours.",
            action      = f"Immediately assign or reschedule '{title}'. If client-facing, communicate delay proactively.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.95,
            raw_content = e.get("content", ""),
        ))
    return results


def rule_system_failure(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects services that are DOWN from the health check connector.
    """
    results = []
    for e in events:
        if e.get("source") != "health_check":
            continue
        status = e.get("status", "") or ""
        content = e.get("content", "")
        if "DOWN" not in status.upper() and "DOWN" not in content.upper():
            continue
        service = e.get("url") or e.get("content", "Unknown service")
        results.append(BusinessEvent(
            signal_type = SYSTEM_FAILURE,
            severity    = Severity.CRITICAL,
            message     = f"Service is DOWN: {service}",
            action      = "Alert your engineering lead immediately. Check status page and notify affected clients.",
            source      = "health_check",
            age_hours   = e.get("age_hours", 0.0),
            confidence  = 1.0,
            raw_content = content,
        ))
    return results


def rule_team_blocker(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects stale GitHub PRs that are blocking team velocity.
    """
    results = []
    for e in events:
        if e.get("type") not in ("pr_stale", "issue_open"):
            continue
        age   = e.get("age_hours", 0.0)
        if age < PR_STALE_HOURS:
            continue
        title = _extract_title(e.get("content", "")) or "untitled PR/issue"
        sev   = Severity.CRITICAL if age > 72 else Severity.URGENT
        results.append(BusinessEvent(
            signal_type = TEAM_BLOCKER,
            severity    = sev,
            message     = f"'{title}' has been stale for {age:.0f} hours — blocking team progress.",
            action      = f"Review '{title}' today: merge, close, or assign a reviewer.",
            source      = e.get("source", ""),
            age_hours   = age,
            confidence  = 0.85,
            raw_content = e.get("content", ""),
        ))
    return results


def rule_revenue_risk(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects invoice, payment, and billing signals across all sources.
    """
    results = []
    for e in events:
        content_lc = e.get("content", "").lower()
        if not any(kw in content_lc for kw in INVOICE_KEYWORDS):
            continue
        client = e.get("client") or _extract_name(content_lc)
        age    = e.get("age_hours", 0.0)
        title  = _extract_title(e.get("content", "")) or "Payment issue"
        results.append(BusinessEvent(
            signal_type = REVENUE_RISK,
            severity    = Severity.CRITICAL,
            message     = f"Revenue signal detected: '{title}'" + (f" from {client}" if client else ""),
            action      = "Handle this immediately — payment issues left unaddressed become lost revenue.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.80,
            raw_content = e.get("content", ""),
        ))
    return results


def rule_communication_gap(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects any communication from external stakeholders that is ≥CLIENT_WAIT_URGENT_HOURS
    old and not already flagged as client_risk.
    """
    results = []
    already_flagged_clients = set()
    # First pass — collect clients already caught by client_risk rule
    for e in events:
        if e.get("type") in ("client_message", "client_email") and e.get("age_hours", 0) >= CLIENT_WAIT_URGENT_HOURS:
            already_flagged_clients.add(e.get("client", ""))

    for e in events:
        if e.get("type") not in ("team_update", "general"):
            continue
        age    = e.get("age_hours", 0.0)
        client = e.get("client", "")
        if age < CLIENT_WAIT_URGENT_HOURS * 2:   # Only flag severe gaps
            continue
        if client in already_flagged_clients:
            continue
        content_lc = e.get("content", "").lower()
        if not any(s in content_lc for s in {"waiting", "follow up", "update", "reply", "response"}):
            continue
        results.append(BusinessEvent(
            signal_type = COMMUNICATION_GAP,
            severity    = Severity.URGENT,
            message     = f"Communication gap detected: {age:.0f}h since last update in {e.get('source','unknown')}.",
            action      = "Send a quick status update to keep stakeholders informed and trust intact.",
            source      = e.get("source", ""),
            client      = client,
            age_hours   = age,
            confidence  = 0.70,
            raw_content = e.get("content", ""),
        ))
    return results


def rule_opportunity_signal(events: List[Dict]) -> List[BusinessEvent]:
    """
    Detects positive signals — shipped features, signed deals, milestones.
    These inform the daily summary and help founders celebrate wins.
    """
    results = []
    for e in events:
        content_lc = e.get("content", "").lower()
        if not any(kw in content_lc for kw in OPPORTUNITY_KEYWORDS):
            continue
        title = _extract_title(e.get("content", "")) or "Milestone"
        results.append(BusinessEvent(
            signal_type = OPPORTUNITY_SIGNAL,
            severity    = Severity.INFO,
            message     = f"Positive signal: {title}",
            action      = "Acknowledge and share this win with stakeholders when appropriate.",
            source      = e.get("source", ""),
            age_hours   = e.get("age_hours", 0.0),
            confidence  = 0.75,
            raw_content = e.get("content", ""),
        ))
    return results


# ── Helper extractors ─────────────────────────────────────────────────────────

def _extract_name(text: str) -> str:
    m = re.search(r"(client|customer|from)[:\s]+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)", text)
    return m.group(2) if m else ""

def _extract_title(text: str) -> str:
    """Pull quoted strings or PR/task names from content."""
    m = re.search(r"'([^']{3,60})'|\"([^\"]{3,60})\"", text)
    if m:
        return m.group(1) or m.group(2)
    # Fall back: first 60 chars stripped of leading labels
    cleaned = re.sub(r"^(Email from|Notion task|PR #\d+:|Issue #\d+:)\s*", "", text, flags=re.IGNORECASE)
    return cleaned[:60].strip()


# ── Rule Engine ────────────────────────────────────────────────────────────────

class Classifier:
    """
    The Founder Brain.

    Runs a registry of business rules over processed events and returns
    a prioritised list of BusinessEvents — structured decisions, not raw data.

    Usage:
        classifier = Classifier()
        business_events = classifier.analyze(processed_events)
    """

    # Rule registry — add new rules here
    RULES = [
        rule_system_failure,       # Highest priority (infrastructure)
        rule_revenue_risk,         # Revenue always critical
        rule_client_risk,          # Client relationship risk
        rule_deadline_risk,        # Deadline & task risk
        rule_team_blocker,         # Team velocity
        rule_communication_gap,    # Softer communication signals
        rule_opportunity_signal,   # Positive wins (for daily summary)
    ]

    def __init__(self, min_confidence: float = 0.65):
        self.min_confidence = min_confidence

    def _calculate_score(self, event: Dict[str, Any]) -> float:
        """Calculate a numerical risk score for an event."""
        score = 0.0
        content = event.get("content", "").lower()

        # Keywords from blueprint
        if any(kw in content for kw in ["delay", "overdue", "late", "missed"]): score += 2.0
        if any(kw in content for kw in ["error", "failure", "crash", "down"]): score += 3.0
        if any(kw in content for kw in ["unhappy", "angry", "complaint", "lost"]): score += 3.0
        if any(kw in content for kw in ["invoice", "payment", "billing"]): score += 2.0

        # Adjust by age
        age = event.get("age_hours", 0.0)
        if age > 24: score += 1.0  # Escalation
        
        # Max out at 10.0 for normalization
        return min(score, 10.0)

    def analyze(self, processed_events: List[Dict[str, Any]]) -> List[BusinessEvent]:
        """
        Run all rules and scoring against the event list.
        """
        all_events: List[BusinessEvent] = []

        # 1. Run traditional rules
        for rule in self.RULES:
            try:
                detected = rule(processed_events)
                filtered = [e for e in detected if e.confidence >= self.min_confidence]
                all_events.extend(filtered)
            except Exception as ex:
                print(f"⚠️  Rule '{rule.__name__}' failed: {ex}")

        # 2. Run scoring for "general" events that might have been missed
        for e in processed_events:
            if e.get("type") == "general" or not any(ev.raw_content == e.get("content") for ev in all_events):
                score = self._calculate_score(e)
                if score >= 2.0:
                    sev = Severity.CRITICAL if score >= 5.0 else Severity.URGENT
                    all_events.append(BusinessEvent(
                        signal_type = "scored_signal",
                        severity    = sev,
                        message     = f"Scored signal: {e.get('content')[:60]}...",
                        action      = "Review this signal — reached risk threshold of " + str(score),
                        source      = e.get("source", "unknown"),
                        age_hours   = e.get("age_hours", 0.0),
                        confidence  = score / 10.0,
                        raw_content = e.get("content", ""),
                    ))

        # Deduplicate and Sort
        seen = set()
        unique_events = []
        for ev in all_events:
            key = (ev.signal_type, ev.source, ev.message[:30])
            if key not in seen:
                seen.add(key)
                unique_events.append(ev)

        _order = {Severity.CRITICAL: 0, Severity.URGENT: 1, Severity.INFO: 2}
        unique_events.sort(key=lambda x: _order.get(x.severity, 3))

        print(f"🧠 Intelligence Layer: {len(unique_events)} business signals detected "
              f"(Confidence Breakdown: {sum(1 for e in unique_events if e.confidence >= 0.9)} HIGH, "
              f"{sum(1 for e in unique_events if e.confidence >= 0.75)} MEDIUM)")

        return unique_events
