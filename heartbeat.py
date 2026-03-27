from heartbeat_app.core.config_manager import Config
from heartbeat_app.connectors.slack import SlackConnector
from heartbeat_app.connectors.health import HealthCheckConnector
from heartbeat_app.connectors.git_conn import GitConnector
from heartbeat_app.connectors.file_project import FileProjectConnector
from heartbeat_app.connectors.gmail_conn import GmailConnector
from heartbeat_app.connectors.github_conn import GitHubConnector
from heartbeat_app.connectors.notion_conn import NotionConnector
from heartbeat_app.core.processor import EventProcessor
from classifier import Classifier
from summarizer import Summarizer
from heartbeat_app.delivery.unified_notifier import UnifiedNotifier
from heartbeat_app.core.scheduler import Scheduler
from heartbeat_app.db.models import DatabaseManager
import os


def _build_summarizer(config: Config) -> Summarizer:
    """Initialise Summarizer with all available AI keys and the configured provider."""
    ai_cfg   = config.ai
    provider = ai_cfg.get("provider", "auto")
    return Summarizer(
        gemini_key    = config.get_env("GEMINI_API_KEY"),
        anthropic_key = config.get_env("ANTHROPIC_API_KEY"),
        openai_key    = config.get_env("OPENAI_API_KEY"),
        provider      = provider,
    )


def _build_notifier(config: Config) -> UnifiedNotifier:
    """Initialise UnifiedNotifier from delivery section of settings.yaml."""
    delivery = config.delivery
    return UnifiedNotifier(
        preferred     = delivery.get("preferred", "desktop"),
        slack_webhook = delivery.get("slack_webhook", ""),
        smtp_user     = config.get_env("SMTP_USER", ""),
        smtp_pass     = config.get_env("SMTP_PASS", ""),
        smtp_to       = config.get_env("SMTP_TO", ""),
    )


def run_heartbeat():
    # 1. Load config
    config = Config()
    project_path = config.connectors.get("git", {}).get("repo_path", ".")

    # 2. Connectors
    connectors = [
        SlackConnector(
            token       = config.get_env("SLACK_TOKEN"),
            channel_ids = config.connectors.get("slack", {}).get("channel_ids", []),
        ),
        HealthCheckConnector(
            endpoints = config.connectors.get("health", {}).get("endpoints", []),
        ),
        GitConnector(repo_path=project_path),
        FileProjectConnector(project_path=project_path),
        GmailConnector(),
        GitHubConnector(
            token = config.get_env("GITHUB_TOKEN"),
            repo  = config.connectors.get("github", {}).get("repo", ""),
        ),
        NotionConnector(
            token       = config.get_env("NOTION_TOKEN"),
            database_id = config.connectors.get("notion", {}).get("database_id", ""),
        ),
    ]

    # 3. Pull raw data
    raw_data = []
    source_errors = []
    for conn in connectors:
        try:
            data = conn.fetch_data()
            raw_data.extend(data)
            # Collect any internal errors (e.g. from handle_error)
            if hasattr(conn, "errors"):
                source_errors.extend(conn.errors)
        except Exception as e:
            msg = f"Critical failure in {conn.name}: {e}"
            print(f"❌ {msg}")
            source_errors.append(msg)

    # 4. Normalise + enrich (Event Processor)
    processor        = EventProcessor()
    processed_events = processor.process(raw_data)

    # 5. ── FOUNDER BRAIN ── Convert to business signals
    classifier       = Classifier()
    business_events  = classifier.analyze(processed_events)

    # 6. Summarise with COO prompt (use business events if available, else raw)
    summarizer = _build_summarizer(config)
    digest     = summarizer.summarize(
        business_events if business_events else processed_events,
        source_errors = source_errors
    )

    # 7. Persist
    db = DatabaseManager()
    db.save_digest(digest)

    # 8. Deliver
    notifier = _build_notifier(config)
    notifier.send(digest)
    print("✅ Heartbeat cycle complete.")


def run_daily_summary():
    print("🌅 Triggering Daily Executive Summary...")
    config = Config()
    db     = DatabaseManager()

    summarizer   = _build_summarizer(config)
    past_digests = db.get_last_24h_digests()
    daily_digest = summarizer.summarize(past_digests, is_daily=True)

    notifier = _build_notifier(config)
    notifier.send(daily_digest)
    print("✅ Daily Executive Summary complete.")


if __name__ == "__main__":
    config    = Config()
    timing    = config._config.get("timing", {})
    interval  = timing.get("interval_minutes", 30)
    scheduler = Scheduler(interval_minutes=interval)
    scheduler.run(run_heartbeat, run_daily_summary)
