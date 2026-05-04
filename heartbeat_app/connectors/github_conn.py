import time
import requests
from typing import List, Dict, Any
from .base import BaseConnector

_MOCK_DATA = [
    {
        "type": "pr_stale",
        "content": "Delivery item 'Integrate payment gateway' is waiting for review and may affect a paid implementation",
        "priority": "high",
        "age_hours": 72.0,
    },
    {
        "type": "pr_stale",
        "content": "Delivery item 'Fix auth blocker' is waiting for approval before the customer rollout",
        "priority": "high",
        "age_hours": 26.0,
    },
    {
        "type": "issue_open",
        "content": "Customer rollout blocker 'rate limit during onboarding' is open with no owner",
        "priority": "high",
        "age_hours": 5.0,
    },
]


class GitHubConnector(BaseConnector):
    """
    Fetches customer-facing delivery blockers from a GitHub repository via REST API.
    Falls back to mock data when token is absent or repo not configured.
    """

    def __init__(self, token: str = None, repo: str = None):
        super().__init__()
        # token: personal access token from GITHUB_TOKEN env var
        # repo:  "owner/repo-name"
        self.token = token if token and "your-key" not in str(token) and "ghp_your" not in str(token) else None
        self.repo  = repo

    @property
    def name(self) -> str:
        return "github"

    def _headers(self):
        return {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}

    def _fetch_prs(self) -> List[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{self.repo}/pulls?state=open&per_page=10"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        events = []
        now = time.time()
        for pull in resp.json():
            created_at = pull.get("created_at", "")
            import datetime
            try:
                dt = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=datetime.timezone.utc)
                age_h = round((now - dt.timestamp()) / 3600, 1)
            except Exception:
                age_h = 0.0
            events.append({
                "source":    self.name,
                "type":      "pr_stale",
                "content":   f"Delivery item '{pull['title']}' has been waiting {age_h:.0f}h",
                "priority":  "high" if age_h > 24 else "low",
                "age_hours": age_h,
                "timestamp": now - age_h * 3600,
            })
        return events

    def _fetch_issues(self) -> List[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{self.repo}/issues?state=open&per_page=10"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        events = []
        now = time.time()
        for issue in resp.json():
            if "pull_request" in issue:
                continue  # PRs show up in issues endpoint too
            import datetime
            created_at = issue.get("created_at", "")
            try:
                dt = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=datetime.timezone.utc)
                age_h = round((now - dt.timestamp()) / 3600, 1)
            except Exception:
                age_h = 0.0
            events.append({
                "source":    self.name,
                "type":      "issue_open",
                "content":   f"Delivery issue '{issue['title']}' has been open {age_h:.0f}h",
                "priority":  "high" if issue.get("labels") else "low",
                "age_hours": age_h,
                "timestamp": now - age_h * 3600,
            })
        return events

    def fetch_data(self) -> List[Dict[str, Any]]:
        if self.token and self.repo:
            try:
                print(f"[GITHUB] Fetching GitHub data for {self.repo}...")
                return self._fetch_prs() + self._fetch_issues()
            except Exception as e:
                self.handle_error(e)
                print("   Falling back to mock GitHub data.")

        print("[GITHUB] GitHub token/repo not configured -- using mock data.")
        return [
            {
                "source":    self.name,
                "type":      m["type"],
                "content":   m["content"],
                "priority":  m["priority"],
                "age_hours": m["age_hours"],
                "timestamp": time.time() - m["age_hours"] * 3600,
            }
            for m in _MOCK_DATA
        ]
