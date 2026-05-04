import sys
import os
import json
from heartbeat_app.db.models import DatabaseManager
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

def run_heartbeat_for_user(user_id: int, config) -> str:
    # 1. Initialize DB
    db = DatabaseManager()

    # 2. Connectors
    # We load connector settings from config_dict passed in main.py
    connectors = [
        SlackConnector(
            token       = config.get_env("SLACK_TOKEN"),
            channel_ids = config.connectors.get("slack", {}).get("channel_ids", []),
        ),
        # Note: Local file/git connectors might not work in a hosted SaaS,
        # but for this MVP on user's device, we keep them.
        GitConnector(repo_path=config.connectors.get("git", {}).get("repo_path", ".")),
        FileProjectConnector(project_path=config.connectors.get("git", {}).get("repo_path", ".")),
        GmailConnector(), # Uses local OAuth credentials
        GitHubConnector(
            token = config.get_env("GITHUB_TOKEN"),
            repo  = config.connectors.get("github", {}).get("repo", ""),
        ),
        NotionConnector(
            token       = config.get_env("NOTION_TOKEN"),
            database_id = config.connectors.get("notion", {}).get("database_id", ""),
        ),
        CalendarConnector(
            provider         = config.connectors.get("calendar", {}).get("provider", "google"),
            credentials_path = config.connectors.get("calendar", {}).get("credentials_path"),
            calendar_id      = config.connectors.get("calendar", {}).get("calendar_id", "primary"),
            lookahead_hours  = config.connectors.get("calendar", {}).get("lookahead_hours", 48),
        ),
    ]

    # 3. Pull raw data
    raw_data = []
    source_errors = []
    for conn in connectors:
        try:
            # Check if connector is configured
            if hasattr(conn, "is_configured") and not conn.is_configured: continue
            # Basic sanity check (if token is missing, skip)
            if hasattr(conn, "token") and not conn.token: continue
            
            data = conn.fetch_data()
            raw_data.extend(data)
            if hasattr(conn, "errors"): source_errors.extend(conn.errors)
        except Exception as e:
            source_errors.append(f"{conn.name} data unavailable: {e}")

    # 4. Process + Brain
    processor        = EventProcessor()
    processed_events = processor.process(raw_data)
    classifier       = Classifier()
    business_events  = classifier.analyze(processed_events)

    # 5. Summarize
    # Extract AI provider from config
    ai_cfg   = config.ai
    provider = ai_cfg.get("provider", "auto")
    summarizer = Summarizer(
        gemini_key    = config.get_env("GEMINI_API_KEY"),
        anthropic_key = config.get_env("ANTHROPIC_API_KEY"),
        openai_key    = config.get_env("OPENAI_API_KEY"),
        provider      = provider,
    )
    
    digest = summarizer.summarize(
        business_events if business_events else processed_events,
        source_errors = source_errors
    )

    # 6. Save (Multi-tenant)
    db.save_digest(user_id, digest)

    # 7. Notify (Optional in SaaS, as dashboard is primary)
    try:
        delivery = config.delivery
        notifier = UnifiedNotifier(
            preferred     = delivery.get("preferred", "desktop"),
            slack_webhook = delivery.get("slack_webhook", ""),
            smtp_user     = config.get_env("SMTP_USER", ""),
            smtp_pass     = config.get_env("SMTP_PASS", ""),
            smtp_to       = config.get_env("SMTP_TO", ""),
        )
        notifier.send(digest)
    except: pass # Don't fail if notification fails
    
    return digest
