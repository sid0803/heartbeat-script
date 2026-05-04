import time
import requests
from typing import List, Dict, Any
from .base import BaseConnector

_MOCK_TASKS = [
    {
        "title":     "Q2 Roadmap Review",
        "status":    "Not started",
        "due":       "2026-03-25",
        "assignee":  "Unassigned",
        "age_hours": 48.0,
        "priority":  "high",
    },
    {
        "title":     "Send proposal to Client XYZ",
        "status":    "In progress",
        "due":       "2026-03-26",
        "assignee":  "Alice",
        "age_hours": 30.0,
        "priority":  "high",
    },
    {
        "title":     "Update investor deck",
        "status":    "Not started",
        "due":       "2026-03-28",
        "assignee":  "Unassigned",
        "age_hours": 6.0,
        "priority":  "low",
    },
]


class NotionConnector(BaseConnector):
    """
    Queries a Notion database for overdue/incomplete tasks via the Notion API.
    Falls back to mock data when NOTION_TOKEN or database_id is absent.
    """

    def __init__(self, token: str = None, database_id: str = None):
        super().__init__()
        self.token       = token if token and "secret_your" not in str(token) else None
        self.database_id = database_id if database_id and "abc-123" not in str(database_id) else None

    @property
    def name(self) -> str:
        return "notion"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def _fetch_live(self) -> List[Dict[str, Any]]:
        url  = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        body = {
            "filter": {
                "or": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Status", "status": {"equals": "Not started"}},
                ]
            }
        }
        resp = requests.post(url, headers=self._headers(), json=body, timeout=10)
        resp.raise_for_status()

        events = []
        now    = time.time()
        for page in resp.json().get("results", []):
            props     = page.get("properties", {})
            title_obj = props.get("Name", props.get("Title", {}))
            title     = ""
            for t in title_obj.get("title", []):
                title += t.get("plain_text", "")

            status_obj = props.get("Status", {})
            status     = status_obj.get("status", {}).get("name", "Unknown")

            due_obj = props.get("Due", props.get("Due Date", {}))
            due     = due_obj.get("date", {}).get("start", "N/A") if due_obj else "N/A"

            age_h = 0.0
            if due != "N/A":
                try:
                    import datetime
                    due_dt = datetime.datetime.fromisoformat(due).replace(tzinfo=datetime.timezone.utc)
                    age_h  = max(round((now - due_dt.timestamp()) / 3600, 1), 0.0)
                except Exception:
                    pass

            events.append({
                "source":    self.name,
                "type":      "task_overdue",
                "content":   f"Notion task '{title}' -- Status: {status}, Due: {due}",
                "priority":  "high" if age_h > 0 else "low",
                "age_hours": age_h,
                "timestamp": now - age_h * 3600,
            })
        return events

    def fetch_data(self) -> List[Dict[str, Any]]:
        if self.token and self.database_id:
            try:
                print("[NOTION] Fetching Notion tasks...")
                return self._fetch_live()
            except Exception as e:
                self.handle_error(e)
                print("   Falling back to mock Notion data.")

        print("[NOTION] Notion token/database not configured -- using mock data.")
        return [
            {
                "source":    self.name,
                "type":      "task_overdue",
                "content":   f"Notion task '{t['title']}' -- Status: {t['status']}, Assignee: {t['assignee']}, Due: {t['due']}",
                "priority":  t["priority"],
                "age_hours": t["age_hours"],
                "timestamp": time.time() - t["age_hours"] * 3600,
            }
            for t in _MOCK_TASKS
        ]
