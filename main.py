from heartbeat.core.config_manager import Config
from heartbeat.connectors.slack import SlackConnector
from heartbeat.connectors.health import HealthCheckConnector
from heartbeat.connectors.git_conn import GitConnector
from heartbeat.connectors.file_project import FileProjectConnector
from heartbeat.connectors.gmail_conn import GmailConnector
from heartbeat.connectors.github_conn import GitHubConnector
from heartbeat.connectors.notion_conn import NotionConnector
from heartbeat.core.processor import EventProcessor
from heartbeat.intelligence.rule_engine import RuleEngine
from heartbeat.core.summarizer import Summarizer
from heartbeat.delivery.unified_notifier import UnifiedNotifier
from heartbeat.core.scheduler import Scheduler
from heartbeat.db.models import DatabaseManager
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
    for conn in connectors:
        raw_data.extend(conn.fetch_data())

    # 4. Normalise + enrich (Event Processor)
    processor        = EventProcessor()
    processed_events = processor.process(raw_data)

    # 5. ── FOUNDER BRAIN ── Convert to business signals
    rule_engine      = RuleEngine()
    business_events  = rule_engine.analyze(processed_events)

    # 6. Summarise with COO prompt (use business events if available, else raw)
    summarizer = _build_summarizer(config)
    digest     = summarizer.summarize(business_events if business_events else processed_events)

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
