import time
from typing import List, Dict, Any
from .base import BaseConnector

_MOCK_MESSAGES = [
    {"text": "Client ABC: The deadline is this Friday -- are we on track?",  "client": "ABC Corp",    "age_hours": 3.2,  "priority": "high"},
    {"text": "Client XYZ: Can we schedule a call to discuss the proposal?",  "client": "XYZ Ltd",     "age_hours": 8.0,  "priority": "high"},
    {"text": "Team: Weekly sync is moved to 4pm today.",                     "client": "",            "age_hours": 1.0,  "priority": "low"},
    {"text": "Client Beta: Invoice #1038 -- when can we expect the refund?",  "client": "Beta Inc",    "age_hours": 26.0, "priority": "high"},
    {"text": "Delivery Team: Customer auth fix is ready for review.",        "client": "",            "age_hours": 0.5,  "priority": "low"},
]


class SlackConnector(BaseConnector):
    """
    Fetches recent channel messages via Slack SDK.
    Falls back to rich mock data when token is absent or invalid.
    """

    def __init__(self, token: str, channel_ids: List[str], lookback_hours: int = 2):
        super().__init__()
        self.token        = token if token and "xoxb-your" not in str(token) and token != "mock_token" else None
        self.channel_ids  = channel_ids
        self.lookback_hours = lookback_hours

    @property
    def name(self) -> str:
        return "slack"

    def _fetch_live(self) -> List[Dict[str, Any]]:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError

        client  = WebClient(token=self.token)
        since   = time.time() - self.lookback_hours * 3600
        events  = []

        for channel_id in self.channel_ids:
            try:
                result = client.conversations_history(
                    channel=channel_id,
                    oldest=str(since),
                    limit=20,
                )
                for msg in result.get("messages", []):
                    text = msg.get("text", "").strip()
                    if not text:
                        continue
                    ts    = float(msg.get("ts", time.time()))
                    age_h = round((time.time() - ts) / 3600, 1)
                    events.append({
                        "source":    self.name,
                        "type":      "team_update",
                        "content":   text[:200],
                        "priority":  "high" if age_h > 4 else "low",
                        "age_hours": age_h,
                        "timestamp": ts,
                    })
            except SlackApiError as e:
                self.handle_error(e)
        return events

    def fetch_data(self) -> List[Dict[str, Any]]:
        if self.token and self.channel_ids:
            try:
                print(f"[SLACK] Fetching live Slack messages from {len(self.channel_ids)} channels...")
                return self._fetch_live()
            except Exception as e:
                self.handle_error(e)
                print("   Falling back to mock Slack data.")

        print(f"[SLACK] Slack not configured (channels: {self.channel_ids}) -- using mock data.")
        return [
            {
                "source":    self.name,
                "type":      "client_message" if m["client"] else "team_update",
                "content":   m["text"],
                "client":    m["client"],
                "priority":  m["priority"],
                "age_hours": m["age_hours"],
                "timestamp": time.time() - m["age_hours"] * 3600,
            }
            for m in _MOCK_MESSAGES
        ]
