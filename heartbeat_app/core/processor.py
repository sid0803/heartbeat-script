import time
import hashlib
from typing import List, Dict, Any, Set

# ── Keyword maps ────────────────────────────────────────────────────────────
CRITICAL_KEYWORDS = {"critical", "emergency", "missed", "blocked", "stalled", "lost"}
URGENT_KEYWORDS   = {"urgent", "deadline", "money", "immediate", "overdue", "waiting", "blocker", "renewal", "proposal"}
CLIENT_SIGNALS    = {"client", "customer", "partner", "investor", "stakeholder"}

# ── Event-type inference ─────────────────────────────────────────────────────
def _infer_type(source: str, content: str) -> str:
    c = content.lower()
    if source == "slack":
        return "client_message" if any(s in c for s in CLIENT_SIGNALS) else "team_update"
    if source == "gmail":
        return "client_email"
    if source == "github":
        return "pr_stale" if "delivery item" in c or "pull" in c else "issue_open"
    if source == "notion":
        return "task_overdue"
    if source == "calendar":
        if "cancelled" in content.lower() or "canceled" in content.lower():
            return "meeting_cancelled"
        if "conflict" in content.lower() or "double-book" in content.lower():
            return "meeting_conflict"
        return "meeting_soon"
    if source in ("git_project", "full_project_analysis"):
        return "code_activity"
    return "general"

# ── Client name extraction (best-effort) ─────────────────────────────────────
def _extract_client(content: str) -> str:
    import re
    # Patterns like "Client X", "from: Name", "re: Company"
    m = re.search(r"(client|customer|from)[:\s]+([A-Z][a-zA-Z]+)", content)
    return m.group(2) if m else ""

# ── Suggested action map ─────────────────────────────────────────────────────
_ACTION_MAP = {
    "client_message": "Reply to client message within 2 hours",
    "client_email":   "Review and respond to client email",
    "pr_stale":       "Confirm whether this blocks a customer promise",
    "task_overdue":   "Assign or reschedule the overdue task",
    "issue_open":     "Assign an owner if this affects a customer commitment",
    "code_activity":  "Review recent commits for quality",
    "team_update":    "Acknowledge team update",
    "meeting_soon":   "Prepare for the meeting and confirm agenda, attendees, and follow-up",
    "meeting_conflict": "Resolve the schedule conflict before the meeting start",
    "meeting_cancelled": "Confirm the meeting cancellation or reschedule with stakeholders",
    "general":        None,
}


class EventProcessor:
    def __init__(self):
        self._seen_hashes: Set[str] = set()  # For deduplication within a session

    def _event_hash(self, source: str, content: str) -> str:
        # Cross-source deduplication: ignore source and focus on normalized content
        # Strip common prefixes like "Email from...", "Slack message from..."
        import re
        normalized = re.sub(r"^(email from|slack message from|notion task|delivery item|delivery issue|issue #\d+:)\s*", "", content.lower(), flags=re.IGNORECASE)
        # Use first 100 chars of normalized content for fuzzy-ish match
        return hashlib.md5(normalized[:100].encode()).hexdigest()

    def process(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalise, enrich and prioritise raw connector data."""
        processed_events = []
        now = time.time()
        seen_hashes = set()

        for item in raw_data:
            raw_content = item.get("content", "") or f"Status report for {item.get('url','unknown')}"
            source      = item.get("source", "unknown")
            content_lc  = raw_content.lower()

            # ── Advanced Deduplication ─────────────────────────────────────
            h = self._event_hash(source, raw_content)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            # ── Severity ───────────────────────────────────────────────────
            severity = "INFO"
            if item.get("priority") == "high" or item.get("status") == "DOWN":
                severity = "CRITICAL"
            if any(kw in content_lc for kw in CRITICAL_KEYWORDS):
                severity = "CRITICAL"
            elif any(kw in content_lc for kw in URGENT_KEYWORDS) and severity != "CRITICAL":
                severity = "URGENT"

            # ── Age & urgency decay ────────────────────────────────────────
            ts        = item.get("timestamp") or now
            age_hours = round((now - float(ts)) / 3600, 1)
            if age_hours >= 4 and severity == "INFO":
                severity = "URGENT"  # Stale items deserve attention

            # ── Semantic enrichment ────────────────────────────────────────
            event_type       = item.get("type") or _infer_type(source, raw_content)
            client           = item.get("client") or _extract_client(raw_content)
            suggested_action = _ACTION_MAP.get(event_type)

            processed_events.append({
                "source":           source,
                "content":          raw_content,
                "severity":         severity,
                "type":             event_type,
                "client":           client,
                "age_hours":        age_hours,
                "suggested_action": suggested_action,
                "timestamp":        ts,
                "event_time":       item.get("event_time", ""),
                "attendees":        item.get("attendees", []),
                "location":         item.get("location", ""),
                "status":           item.get("status", ""),
                "reason":           item.get("reason", ""),
                "summary":          item.get("summary", ""),
            })

        # Sort: CRITICAL → URGENT → INFO
        _order = {"CRITICAL": 0, "URGENT": 1, "INFO": 2}
        processed_events.sort(key=lambda x: _order.get(x["severity"], 3))
        return processed_events
