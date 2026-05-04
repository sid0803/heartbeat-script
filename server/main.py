import sys
import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

# Add project root to path to import from heartbeat_app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heartbeat_app.db.models import DatabaseManager
from heartbeat_app.core.config_manager import Config
from heartbeat_app.connectors.slack import SlackConnector
from heartbeat_app.connectors.git_conn import GitConnector
from heartbeat_app.connectors.file_project import FileProjectConnector
from heartbeat_app.connectors.gmail_conn import GmailConnector
from heartbeat_app.connectors.github_conn import GitHubConnector
from heartbeat_app.connectors.notion_conn import NotionConnector
from heartbeat_app.connectors.calendar_conn import CalendarConnector
from heartbeat_app.core.processor import EventProcessor
from heartbeat_app.intelligence.classifier import Classifier
from heartbeat_app.intelligence.summarizer import Summarizer
from heartbeat_app.delivery.unified_notifier import UnifiedNotifier
from server.auth import verify_password, get_password_hash, create_access_token, decode_access_token

app = FastAPI(title="Heartbeat Intelligence API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Schemas ---
class UserRegister(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class DigestOut(BaseModel):
    timestamp: str
    content: str
    source_type: str

class CalendarConfig(BaseModel):
    provider: str = "google"
    credentials_path: Optional[str] = None
    calendar_id: str = "primary"
    lookahead_hours: int = 48
    is_active: bool = True

class ConnectorState(BaseModel):
    is_active: bool

CONNECTOR_DEFINITIONS = {
    "slack": {
        "name": "Slack",
        "env": "SLACK_TOKEN",
        "config_keys": ["channel_ids"],
        "secret_keys": ["token"],
        "summary": "Client and team conversation signal.",
    },
    "gmail": {
        "name": "Gmail",
        "config_keys": ["credentials_path", "max_results"],
        "summary": "Customer email and revenue-risk signal.",
    },
    "github": {
        "name": "GitHub",
        "env": "GITHUB_TOKEN",
        "config_keys": ["repo"],
        "summary": "Customer-facing delivery commitment signal.",
    },
    "notion": {
        "name": "Notion",
        "env": "NOTION_TOKEN",
        "config_keys": ["database_id"],
        "secret_keys": ["token"],
        "summary": "Tasks, docs, and milestone context.",
    },
    "calendar": {
        "name": "Calendar",
        "config_keys": ["provider", "calendar_id", "credentials_path", "lookahead_hours"],
        "summary": "Schedule risk, cancellations, and meeting prep.",
    },
}

DEFAULT_CONNECTOR_CONFIGS = {
    "calendar": {
        "provider": "google",
        "calendar_id": "primary",
        "credentials_path": os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "heartbeat_app",
            "config",
            "calendar_credentials.json",
        ),
        "lookahead_hours": 48,
    },
    "gmail": {
        "credentials_path": os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "heartbeat_app",
            "config",
            "gmail_credentials.json",
        ),
        "max_results": 10,
    },
}

def _all_connector_configs(user_id: int) -> dict:
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT connector_type, config_json, is_active FROM connector_configs WHERE user_id = ?",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    configs = {}
    for connector_type, config_json, is_active in rows:
        try:
            config = json.loads(config_json or "{}")
        except json.JSONDecodeError:
            config = {}
        configs[connector_type] = {"config": config, "is_active": bool(is_active)}
    return configs

def _clean_value(value):
    if isinstance(value, list):
        return f"{len(value)} configured" if value else "Not set"
    if value is None or value == "":
        return "Not set"
    return value

def _credential_exists(path: Optional[str]) -> bool:
    return bool(path and os.path.exists(path))

def _connector_status(connector_type: str, config: dict, is_active: bool) -> str:
    if not is_active:
        return "Disabled"

    if connector_type == "slack":
        token = os.getenv("SLACK_TOKEN") or config.get("token")
        channels = config.get("channel_ids", [])
        if not token or "mock" in str(token).lower():
            return "Missing token"
        if not channels:
            return "Missing config"
        return "Active"

    if connector_type == "gmail":
        return "OK" if _credential_exists(config.get("credentials_path")) else "Missing credentials"

    if connector_type == "github":
        if not os.getenv("GITHUB_TOKEN") and not config.get("token"):
            return "Missing token"
        if not config.get("repo"):
            return "Missing config"
        return "Active"

    if connector_type == "notion":
        token = os.getenv("NOTION_TOKEN") or config.get("token")
        database_id = config.get("database_id")
        if not token or "mock" in str(token).lower():
            return "Missing token"
        if not database_id or database_id == "abc-123" or "mock" in str(database_id).lower():
            return "Missing config"
        return "Active"

    if connector_type == "calendar":
        if config.get("provider", "google") == "mock":
            return "Active"
        return "Active" if _credential_exists(config.get("credentials_path")) else "Missing credentials"

    return "Unknown"

def _connector_last_sync_status(status_value: str) -> str:
    if status_value in {"Active", "OK"}:
        return "Ready for next scan"
    if status_value == "Disabled":
        return "Paused by user"
    return "Needs setup before live sync"

# --- Auth Helpers ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    email = payload.get("sub")
    # Fetch user from DB
    conn = db._get_conn() # Assuming we add _get_conn or just query
    cursor = conn.cursor()
    cursor.execute("SELECT id, email FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": user[0], "email": user[1]}

# --- Routes ---

@app.post("/register", response_model=Token)
def register(user: UserRegister):
    print(f"Registering user: {user.email}")
    try:
        hashed = get_password_hash(user.password)
        print("Password hashed")
        conn = db._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (user.email, hashed))
            conn.commit()
            print("User inserted into DB")
        except Exception as e:
            conn.close()
            print(f"DB Insert Error: {e}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user_id = cursor.lastrowid
        print(f"User ID: {user_id}")
        db.seed_mock_connectors(user_id) # ⚡ Seed mocks for MVP
        print("Mock connectors seeded")
        conn.close()
        access_token = create_access_token(data={"sub": user.email})
        print("Access token created")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Registration Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE email = ?", (form_data.username,))
    row = cursor.fetchone()
    conn.close()
    if not row or not verify_password(form_data.password, row[0]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/digests", response_model=List[DigestOut])
def get_digests(current_user: dict = Depends(get_current_user)):
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, content, source_type FROM digests WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50", (current_user["id"],))
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "content": r[1], "source_type": r[2]} for r in rows]

@app.get("/connectors/status")
def get_connectors_status(current_user: dict = Depends(get_current_user)):
    stored_configs = _all_connector_configs(current_user["id"])
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp FROM digests WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
        (current_user["id"],),
    )
    last_digest = cursor.fetchone()
    conn.close()

    connectors = []
    for connector_type, definition in CONNECTOR_DEFINITIONS.items():
        stored = stored_configs.get(connector_type, {})
        config = {
            **DEFAULT_CONNECTOR_CONFIGS.get(connector_type, {}),
            **stored.get("config", {}),
        }
        is_active = stored.get("is_active", True)
        status_value = _connector_status(connector_type, config, is_active)
        config_values = {
            key: _clean_value(config.get(key))
            for key in definition.get("config_keys", [])
        }
        for secret_key in definition.get("secret_keys", []):
            if config.get(secret_key) or os.getenv(definition.get("env", "")):
                config_values[secret_key] = "Configured"

        connectors.append({
            "type": connector_type,
            "name": definition["name"],
            "status": status_value,
            "is_active": is_active,
            "last_sync_status": _connector_last_sync_status(status_value),
            "last_sync_at": last_digest[0] if last_digest else None,
            "summary": definition["summary"],
            "config": config_values,
        })
    return {"connectors": connectors}

@app.post("/connectors/{connector_type}/state")
def update_connector_state(connector_type: str, state: ConnectorState, current_user: dict = Depends(get_current_user)):
    if connector_type not in CONNECTOR_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Unknown connector")
    existing = db.get_connector_config(current_user["id"], connector_type)
    config = existing["config"] if existing else DEFAULT_CONNECTOR_CONFIGS.get(connector_type, {})
    db.upsert_connector_config(
        current_user["id"],
        connector_type,
        config,
        is_active=1 if state.is_active else 0,
    )
    return {"type": connector_type, "is_active": state.is_active}

@app.get("/calendar")
def get_calendar_signals(current_user: dict = Depends(get_current_user)):
    calendar_config = db.get_connector_config(current_user["id"], "calendar") or {}
    config_data = calendar_config.get("config", {})
    is_active = calendar_config.get("is_active", True)

    if not is_active:
        return {
            "meetings": [],
            "source_errors": [],
            "calendar_config": {
                "provider": config_data.get("provider", "google"),
                "credentials_path": config_data.get("credentials_path"),
                "calendar_id": config_data.get("calendar_id", "primary"),
                "lookahead_hours": config_data.get("lookahead_hours", 48),
                "is_active": False,
            }
        }

    calendar = CalendarConnector(
        provider         = config_data.get("provider", "google"),
        credentials_path = config_data.get("credentials_path"),
        calendar_id      = config_data.get("calendar_id", "primary"),
        lookahead_hours  = config_data.get("lookahead_hours", 48),
    )

    raw_data = []
    source_errors = []
    try:
        raw_data = calendar.fetch_data()
        if hasattr(calendar, "errors"):
            source_errors.extend(calendar.errors)
    except Exception as e:
        source_errors.append(f"Calendar data unavailable: {e}")

    processor = EventProcessor()
    processed_events = processor.process(raw_data)
    classifier = Classifier()
    business_events = classifier.analyze(processed_events)
    meeting_signals = [event.to_dict() for event in business_events if event.signal_type == "meeting_risk"]
    return {
        "meetings": meeting_signals,
        "source_errors": source_errors,
        "calendar_config": {
            "provider": config_data.get("provider", "google"),
            "credentials_path": config_data.get("credentials_path"),
            "calendar_id": config_data.get("calendar_id", "primary"),
            "lookahead_hours": config_data.get("lookahead_hours", 48),
            "is_active": calendar_config.get("is_active", True),
        }
    }

@app.get("/calendar/config", response_model=CalendarConfig)
def get_calendar_config(current_user: dict = Depends(get_current_user)):
    calendar_config = db.get_connector_config(current_user["id"], "calendar")
    if not calendar_config:
        return CalendarConfig()

    cfg = calendar_config["config"]
    return CalendarConfig(
        provider=cfg.get("provider", "google"),
        credentials_path=cfg.get("credentials_path"),
        calendar_id=cfg.get("calendar_id", "primary"),
        lookahead_hours=cfg.get("lookahead_hours", 48),
        is_active=calendar_config.get("is_active", True),
    )

@app.post("/calendar/config", response_model=CalendarConfig)
def update_calendar_config(config_in: CalendarConfig, current_user: dict = Depends(get_current_user)):
    db.upsert_connector_config(
        current_user["id"],
        "calendar",
        {
            "provider": config_in.provider,
            "credentials_path": config_in.credentials_path,
            "calendar_id": config_in.calendar_id,
            "lookahead_hours": config_in.lookahead_hours,
        },
        is_active=1 if config_in.is_active else 0,
    )
    return config_in

@app.post("/heartbeat/trigger")
def trigger_heartbeat(current_user: dict = Depends(get_current_user)):
    # 1. Load user config from DB
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT connector_type, config_json FROM connector_configs WHERE user_id = ? AND is_active = 1", (current_user["id"],))
    configs = cursor.fetchall()
    conn.close()

    # Convert configs to dict for Config class
    user_settings = {"connectors": {}}
    for c_type, c_json in configs:
        user_settings["connectors"][c_type] = json.loads(c_json)
    
    # We also need AI keys and delivery settings. For MVP, we might use system defaults or user-provided keys.
    # For now, let's assume we use shared environment variables if not in user_settings.
    config = Config(config_dict=user_settings)

    # 2. Re-use Heartbeat Logic (Simplified version of heartbeat.py)
    # Note: We should refactor run_heartbeat to be a reusable function in a service layer.
    try:
        from server.api_logic import run_heartbeat_for_user
        digest = run_heartbeat_for_user(current_user["id"], config)
        return {"status": "success", "digest": digest}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add a helper to get DB connection
def _get_conn():
    import sqlite3
    return sqlite3.connect(db.db_path)

db._get_conn = _get_conn

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
