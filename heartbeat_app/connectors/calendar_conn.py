import os
import time
import datetime
from typing import List, Dict, Any
from .base import BaseConnector

_MOCK_MEETINGS = [
    {
        "summary": "Client kickoff with ABC Corp",
        "client": "ABC Corp",
        "description": "Prepare pricing deck and confirm agenda.",
        "start_offset_hours": 4,
        "priority": "high",
        "event_type": "meeting_soon",
    },
    {
        "summary": "Partner sync -- double-booked slot",
        "client": "PartnerFirm",
        "description": "Conflict between two investor calls; resolve now.",
        "start_offset_hours": 2,
        "priority": "high",
        "event_type": "meeting_conflict",
    },
    {
        "summary": "Weekly strategy review",
        "client": "Internal",
        "description": "Review board slide updates and top priorities.",
        "start_offset_hours": 28,
        "priority": "low",
        "event_type": "meeting_soon",
    },
]


class CalendarConnector(BaseConnector):
    """
    Reads upcoming calendar events that matter to the founder.

    If Google Calendar credentials are available, it can fetch live events.
    Otherwise it returns mock meetings so the pipeline still shows calendar signals.
    """

    def __init__(self, provider: str = "google", credentials_path: str = None,
                 calendar_id: str = "primary", lookahead_hours: int = 48):
        super().__init__()
        self.provider = provider.lower()
        self.calendar_id = calendar_id
        self.lookahead_hours = lookahead_hours
        self.credentials_path = credentials_path
        if self.credentials_path is None:
            PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.credentials_path = os.path.join(PROJECT_ROOT, "heartbeat_app", "config", "calendar_credentials.json")

    @property
    def name(self) -> str:
        return "calendar"

    def _parse_iso(self, value: str) -> float:
        if value is None:
            return time.time()
        try:
            dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return time.time()

    def _build_event(self, summary: str, client: str, description: str,
                     start_ts: float, end_ts: float, event_type: str,
                     priority: str, attendees: List[str], location: str,
                     status: str, reason: str) -> Dict[str, Any]:
        age_hours = round((time.time() - start_ts) / 3600, 1)
        event_time = datetime.datetime.utcfromtimestamp(start_ts).replace(tzinfo=datetime.timezone.utc).isoformat()
        return {
            "source": self.name,
            "type": event_type,
            "content": f"{summary} -- {description}",
            "client": client,
            "priority": priority,
            "age_hours": age_hours,
            "timestamp": start_ts,
            "start_timestamp": start_ts,
            "end_timestamp": end_ts,
            "event_time": event_time,
            "attendees": attendees,
            "location": location,
            "status": status,
            "reason": reason,
            "summary": summary,
            "description": description,
        }

    def _normalize_attendees(self, attendees_raw: List[Dict[str, Any]]) -> List[str]:
        attendees = []
        for attendee in attendees_raw or []:
            name = attendee.get("displayName") or attendee.get("email")
            if name:
                attendees.append(name)
        return attendees

    def _detect_conflicts(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for idx, event in enumerate(events):
            if event["type"] == "meeting_cancelled":
                continue
            overlaps = []
            for other in events:
                if other is event or other["type"] == "meeting_cancelled":
                    continue
                if event["start_timestamp"] < other["end_timestamp"] and other["start_timestamp"] < event["end_timestamp"]:
                    overlaps.append(other)
            if overlaps:
                event["type"] = "meeting_conflict"
                event["reason"] = f"Double-booked with: {', '.join([o['summary'] for o in overlaps])}"
                event["priority"] = "high"
        return events

    @property
    def is_configured(self) -> bool:
        if self.provider == "google":
            return bool(self.credentials_path and os.path.exists(self.credentials_path))
        return True

    def _fetch_live(self) -> List[Dict[str, Any]]:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle

        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        token_path = os.path.join(os.path.dirname(self.credentials_path), "calendar_token.pickle")
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

        service = build("calendar", "v3", credentials=creds)
        now = datetime.datetime.utcnow().isoformat() + "Z"
        window_end = (datetime.datetime.utcnow() + datetime.timedelta(hours=self.lookahead_hours)).isoformat() + "Z"
        events_result = service.events().list(
            calendarId=self.calendar_id,
            timeMin=now,
            timeMax=window_end,
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute()
        events = events_result.get("items", [])

        results = []
        for item in events:
            start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            start_ts = self._parse_iso(start)
            end_ts = self._parse_iso(end) if end else start_ts + 3600
            status = item.get("status", "confirmed")
            summary = item.get("summary", "No title")
            description = item.get("description", "No agenda provided.")
            client = item.get("organizer", {}).get("displayName") or item.get("organizer", {}).get("email", "Client")
            attendees = self._normalize_attendees(item.get("attendees", []))
            location = item.get("location", "")
            reason = "" if status == "confirmed" else item.get("status", "")

            # Detect cancelled and reschedule language in event metadata.
            if status == "cancelled" or "reschedule" in description.lower() or "reschedule" in summary.lower():
                event_type = "meeting_cancelled"
            else:
                event_type = "meeting_soon"

            priority = "high" if event_type == "meeting_cancelled" or start_ts - time.time() < 6 * 3600 else "low"
            results.append(self._build_event(
                summary, client, description, start_ts, end_ts,
                event_type, priority, attendees, location, status, reason
            ))

        return self._detect_conflicts(results)

    def _fetch_mock(self) -> List[Dict[str, Any]]:
        now = time.time()
        results = []
        for meeting in _MOCK_MEETINGS:
            start_ts = now + meeting["start_offset_hours"] * 3600
            end_ts = start_ts + 3600
            attendees = [meeting.get("client")]
            location = "Video call"
            status = "confirmed" if meeting["event_type"] != "meeting_cancelled" else "cancelled"
            reason = meeting.get("description", "")
            results.append(self._build_event(
                meeting["summary"], meeting["client"], meeting["description"],
                start_ts, end_ts, meeting["event_type"], meeting["priority"],
                attendees, location, status, reason
            ))
        return self._detect_conflicts(results)

    def fetch_data(self) -> List[Dict[str, Any]]:
        if self.provider == "google" and not self.is_configured:
            self.handle_error(Exception("Google Calendar credentials missing or invalid."))
            print("[CALENDAR] Calendar credentials not found or not configured -- using mock data.")
            return self._fetch_mock()

        if self.provider == "google":
            try:
                print("[CALENDAR] Fetching live Calendar events...")
                return self._fetch_live()
            except Exception as e:
                self.handle_error(e)
                print("   Falling back to mock Calendar data.")

        print("[CALENDAR] Using mock Calendar data.")
        return self._fetch_mock()
