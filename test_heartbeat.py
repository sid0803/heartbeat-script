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


def test_run():
    print("🚀 Starting Founder Heartbeat — FULL SYSTEM TEST\n")

    # ── Config ────────────────────────────────────────────────────────────────
    config = Config()
    repo_path = config.connectors.get("git", {}).get("repo_path", ".")

    # ── All Connectors (all run in mock mode without real keys) ───────────────
    connectors = [
        SlackConnector(token="mock_token",   channel_ids=["MOCK"]),
        HealthCheckConnector(endpoints=config.connectors.get("health", {}).get("endpoints", [])),
        GitConnector(repo_path=repo_path),
        FileProjectConnector(project_path=repo_path),
        GmailConnector(),          # mock: no credentials.json present
        GitHubConnector(),         # mock: no token
        NotionConnector(),         # mock: no token
    ]

    # ── Pull Data ─────────────────────────────────────────────────────────────
    print("─── 📥 Layer 2: Pulling Data from Connectors ───")
    raw_data = []
    for conn in connectors:
        data = conn.fetch_data()
        assert len(data) >= 1, f"❌ {conn.name} returned 0 items!"
        print(f"  ✅ [{conn.name}] → {len(data)} item(s)")
        raw_data.extend(data)

    # ── Process Events ────────────────────────────────────────────────────────
    processor = EventProcessor()
    processed_events = processor.process(raw_data)
    print(f"  ✅ Normalised to {len(processed_events)} unique events")

    # ── Classifier (Founder Brain) ────────────────────────────────────────────
    print(f"\n─── 🧠 Layer 4: Founder Brain ───")
    classifier = Classifier()
    business_events = classifier.analyze(processed_events)
    print(f"  ✅ Detected {len(business_events)} business signals")

    # Validate enriched schema
    for e in processed_events:
        assert "severity"  in e, f"Missing 'severity' in: {e}"
        assert "type"      in e, f"Missing 'type' in: {e}"
        assert "age_hours" in e, f"Missing 'age_hours' in: {e}"
    print("  ✅ All events have required fields (severity, type, age_hours)")

    # Print top 3 events
    print("\n  Top 3 events by severity:")
    for ev in processed_events[:3]:
        print(f"    [{ev['severity']}] ({ev['type']}) {ev['content'][:80]}")

    # ── Summarize ─────────────────────────────────────────────────────────────
    print(f"\n─── 📝 Layer 5: Generating Digest (multi-provider AI) ───")
    summarizer = Summarizer(provider="auto")  # no keys → mock fallback
    input_events = business_events if business_events else processed_events
    digest = summarizer.summarize(input_events)
    print(f"\n  DIGEST OUTPUT:\n{'─'*60}\n{digest}\n{'─'*60}")

    # ── Deliver ───────────────────────────────────────────────────────────────
    print(f"\n─── 🔔 Layer 6: Delivering Notification ───")
    notifier = UnifiedNotifier(preferred="desktop")
    notifier.send(digest)

    print("\n✅ FULL SYSTEM TEST PASSED — all 6 layers operational!")


if __name__ == "__main__":
    test_run()

