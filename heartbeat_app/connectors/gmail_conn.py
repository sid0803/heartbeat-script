import time
import os
from typing import List, Dict, Any
from .base import BaseConnector

# ── Mock data ---------------------------------------------------------------──
_MOCK_EMAILS = [
    {
        "subject": "Re: Project Timeline Update",
        "sender": "client.abc@example.com",
        "snippet": "Hi, just checking in on the delivery date. We need this by end of month.",
        "client": "ABC Corp",
        "age_hours": 3.5,
        "priority": "high",
    },
    {
        "subject": "Invoice #1042 follow-up",
        "sender": "billing@partnerfirm.com",
        "snippet": "The invoice is still outstanding. Please confirm payment date.",
        "client": "PartnerFirm",
        "age_hours": 14.0,
        "priority": "high",
    },
    {
        "subject": "Quick question about the API",
        "sender": "dev@startup.io",
        "snippet": "We're integrating your API and hit a rate limit issue. Any guidance?",
        "client": "Startup.io",
        "age_hours": 1.0,
        "priority": "low",
    },
]


class GmailConnector(BaseConnector):
    """
    Reads unread client emails via Gmail API.

    When GMAIL credentials are available (`credentials.json` file present), uses
    the Google API client. Otherwise returns rich mock data so the system works
    end-to-end without any Google setup.
    """

    def __init__(self, credentials_path: str = None,
                 max_results: int = 10):
        super().__init__()
        if credentials_path is None:
            # Project root is two levels up from this file
            PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.credentials_path = os.path.join(PROJECT_ROOT, "heartbeat_app", "config", "gmail_credentials.json")
        else:
            self.credentials_path = credentials_path
        self.max_results = max_results

    @property
    def name(self) -> str:
        return "gmail"

    def _fetch_live(self) -> List[Dict[str, Any]]:
        """Fetch unread emails using Gmail API."""
        import os
        import pickle
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        token_path = "heartbeat/config/gmail_token.pickle"
        creds = None

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(
            userId="me", q="is:unread", maxResults=self.max_results
        ).execute()

        messages = results.get("messages", [])
        events = []
        for msg in messages:
            detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata",
                                                     metadataHeaders=["From", "Subject"]).execute()
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            snippet = detail.get("snippet", "")
            ts_ms   = int(detail.get("internalDate", time.time() * 1000))
            age_hrs = round((time.time() - ts_ms / 1000) / 3600, 1)
            events.append({
                "source":    self.name,
                "type":      "client_email",
                "content":   f"Email from {headers.get('From','Unknown')}: {headers.get('Subject','(no subject)')} -- {snippet[:120]}",
                "client":    headers.get("From", ""),
                "priority":  "high" if age_hrs > 4 else "low",
                "age_hours": age_hrs,
                "timestamp": ts_ms / 1000,
            })
        return events

    def fetch_data(self) -> List[Dict[str, Any]]:
        import os
        if os.path.exists(self.credentials_path):
            try:
                print("[GMAIL] Fetching live Gmail data...")
                return self._fetch_live()
            except Exception as e:
                self.handle_error(e)
                print("   Falling back to mock Gmail data.")

        print("[GMAIL] Gmail credentials not found -- using mock data.")
        return [
            {
                "source":    self.name,
                "type":      "client_email",
                "content":   f"Email from {e['sender']}: {e['subject']} -- {e['snippet']}",
                "client":    e["client"],
                "priority":  e["priority"],
                "age_hours": e["age_hours"],
                "timestamp": time.time() - e["age_hours"] * 3600,
            }
            for e in _MOCK_EMAILS
        ]
