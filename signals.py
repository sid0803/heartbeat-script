"""
Business Signal Definitions for Heartbeat System.

This module defines the core data model for the Intelligence Layer.
An `Event` is a structured business signal — not a raw data point,
but a meaningful interpretation that directly tells the founder WHAT TO DO.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# ── Signal type taxonomy ──────────────────────────────────────────────────────
# These map to real founder concerns, not technical terms.

CLIENT_RISK          = "client_risk"         # Client waiting, unhappy, or about to churn
DEADLINE_RISK        = "deadline_risk"       # Task/milestone overdue or at risk
SYSTEM_FAILURE       = "system_failure"      # Service down or degraded
TEAM_BLOCKER         = "team_blocker"        # PR/task blocking team progress
REVENUE_RISK         = "revenue_risk"        # Invoice, payment, or billing issue
COMMUNICATION_GAP    = "communication_gap"   # No reply from founder/team in critical window
OPPORTUNITY_SIGNAL   = "opportunity_signal"  # Positive signal — milestone, good news


# ── Severity levels ───────────────────────────────────────────────────────────
class Severity:
    CRITICAL = "CRITICAL"   # Needs action RIGHT NOW — revenue or client at stake
    URGENT   = "URGENT"     # Needs action TODAY
    INFO     = "INFO"       # Informational — no action needed


# ── Recommended action templates ─────────────────────────────────────────────
ACTION_TEMPLATES = {
    CLIENT_RISK:       "Reply to {client} immediately — {age_hours}h without response risks churn.",
    DEADLINE_RISK:     "Review and unblock '{title}' — it's {age_hours}h overdue.",
    SYSTEM_FAILURE:    "Alert engineering: {service} is DOWN. Check status page.",
    TEAM_BLOCKER:      "Review '{title}' to unblock the team — it's been stale {age_hours}h.",
    REVENUE_RISK:      "Handle '{title}' urgently — there is a revenue implication.",
    COMMUNICATION_GAP: "Respond to '{client}' — {age_hours}h gap in communication.",
    OPPORTUNITY_SIGNAL:"Acknowledge milestone: '{title}'. Consider sharing with stakeholders.",
}


@dataclass
class BusinessEvent:
    """
    A structured business signal produced by the Intelligence Layer.

    Every BusinessEvent answers three founder questions:
      1. WHAT is happening?       → message
      2. HOW URGENT is it?        → severity
      3. WHAT should I do?        → action

    Unlike raw connector data or processor events, a BusinessEvent is
    already interpreted in business language — no technical jargon.
    """
    signal_type:  str               # One of the signal type constants above
    severity:     str               # Severity.CRITICAL | URGENT | INFO
    message:      str               # Human-readable, plain-English description
    action:       str               # Specific, actionable recommendation
    source:       str               # Which connector this came from
    client:       str = ""          # Affected client/partner name (if any)
    age_hours:    float = 0.0       # How long this signal has been active
    confidence:   float = 1.0       # 0.0–1.0 — how certain the rule is
    raw_content:  str = ""          # Original raw content for traceability
    metadata:     Dict[str, Any] = field(default_factory=dict)

    def to_prompt_line(self) -> str:
        """Render a concise line for the LLM prompt."""
        age_tag  = f" [{self.age_hours}h old]" if self.age_hours else ""
        client_tag = f" (re: {self.client})" if self.client else ""
        return (
            f"[{self.severity}] {self.signal_type.upper().replace('_',' ')}"
            f"{client_tag}{age_tag}: {self.message} → ACTION: {self.action}"
        )

    def get_confidence_label(self) -> str:
        """Return human-readable confidence level."""
        if self.confidence >= 0.9:  return "HIGH"
        if self.confidence >= 0.75: return "MEDIUM"
        return "LOW"

    def to_dict(self) -> dict:
        return {
            "signal_type":      self.signal_type,
            "severity":         self.severity,
            "message":          self.message,
            "action":           self.action,
            "source":           self.source,
            "client":           self.client,
            "age_hours":        self.age_hours,
            "confidence":       self.confidence,
            "confidence_label": self.get_confidence_label(),
        }
