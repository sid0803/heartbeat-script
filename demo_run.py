"""
🎬 HEARTBEAT SYSTEM — Live Demo (with Founder Brain Intelligence Layer)
====================================================================
Demonstrates all 6 layers including the new Rule Engine.
No API keys needed — runs on rich realistic mock data.
"""
import time, sys

def bold(t): return f"\033[1m{t}\033[0m"
def green(t): return f"\033[92m{t}\033[0m"
def red(t):   return f"\033[91m{t}\033[0m"
def yellow(t):return f"\033[93m{t}\033[0m"
def cyan(t):  return f"\033[96m{t}\033[0m"
def magenta(t):return f"\033[95m{t}\033[0m"
def dim(t):   return f"\033[2m{t}\033[0m"
def hr(w=65): print(dim("─"*w))
def step(n, total, label): print(f"\n{cyan(bold(f'  STEP {n}/{total}'))} {bold(label)}"); hr()
def pause(s=0.35): time.sleep(s)

print("\n" + "═"*65)
print(bold("  💓  HEARTBEAT SYSTEM  —  Founder Intelligence System"))
print(bold("  Full Live Demo  |  2026-03-27  22:48 IST"))
print("═"*65)
print(dim("  Demonstrating all 6 layers including the new Founder Brain.\n"))
pause(0.6)

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
from signals import Severity
from summarizer import Summarizer
from heartbeat_app.delivery.unified_notifier import UnifiedNotifier

config    = Config()
repo_path = config.connectors.get("git", {}).get("repo_path", ".")

# ─── STEP 1 ───────────────────────────────────────────────────────────────────
step(1, 5, "Scanning All Data Sources (Connectors)")
sources = [
    ("💬 Slack",          SlackConnector(token="mock_token", channel_ids=["MOCK"])),
    ("📧 Gmail",          GmailConnector()),
    ("🐙 GitHub",         GitHubConnector()),
    ("📝 Notion",         NotionConnector()),
    ("🏥 Health Checks",  HealthCheckConnector(endpoints=config.connectors.get("health",{}).get("endpoints",[]))),
    ("📁 Git History",    GitConnector(repo_path=repo_path)),
    ("🗂️  Project Files", FileProjectConnector(project_path=repo_path)),
]
raw_data = []
for label, conn in sources:
    data = conn.fetch_data()
    raw_data.extend(data)
    print(f"  {green('✅')} {label:<22} {dim(str(len(data)) + ' signal(s)')}")
    pause(0.25)
print(f"\n  {bold(f'Total raw signals: {len(raw_data)}')}")
pause(0.5)

# ─── STEP 2 ───────────────────────────────────────────────────────────────────
step(2, 5, "Normalising Events (Event Processor)")
processor = EventProcessor()
events    = processor.process(raw_data)
print(f"  ✅ {len(events)} unique events with enriched schema (severity · type · age_hours)")
pause(0.5)

# ─── STEP 3 — THE NEW LAYER ──────────────────────────────────────────────────
step(3, 5, f"🧠 Founder Brain — Classifier")
print(dim("  Converting raw noise into structured BUSINESS DECISIONS...\n"))
pause(0.5)

classifier      = Classifier()
business_events = classifier.analyze(events)
pause(0.4)

# Display business signals by severity and confidence
critical = [e for e in business_events if e.severity == Severity.CRITICAL]
urgent   = [e for e in business_events if e.severity == Severity.URGENT]
info     = [e for e in business_events if e.severity == Severity.INFO]

print(f"\n  {red(bold('🔴 CRITICAL SIGNALS'))}: {len(critical)}")
for e in critical:
    conf_label = e.get_confidence_label()
    print(f"    {red('→')} [{e.signal_type.upper().replace('_',' ')}] {e.message} {magenta(f'({conf_label} Confidence)')}")
    print(f"       {dim('ACTION:')} {yellow(e.action)}")
    pause(0.2)

print(f"\n  {yellow(bold('🟡 URGENT SIGNALS'))}: {len(urgent)}")
for e in urgent:
    conf_label = e.get_confidence_label()
    print(f"    {yellow('→')} [{e.signal_type.upper().replace('_',' ')}] {e.message} {magenta(f'({conf_label} Confidence)')}")
    print(f"       {dim('ACTION:')} {e.action}")
    pause(0.2)

print(f"\n  {green(bold('🟢 INFO SIGNALS'))}: {len(info)}")
for e in info:
    print(f"    {green('→')} {e.message}")
    pause(0.1)

print(f"\n  {bold('💡 Master Layer Update')}: deduplicated across {len(sources)} sources + keyword scoring active.")
pause(0.6)

# ─── STEP 4 ───────────────────────────────────────────────────────────────────
step(4, 5, "Generating COO Decision Brief (Master Summarizer)")
print(dim("  AI acting as your startup COO — using robust 🔴/🟡/✅ 3-tier format.\n"))
pause(0.4)
summarizer = Summarizer(provider="auto")
# Simulate a mock source failure for the demo
mock_errors = ["Critical failure in legacy_crm: Connection timeout"]
digest = summarizer.summarize(business_events if business_events else events, source_errors=mock_errors)

print(f"\n  {bold('━━━  YOUR 60-SECOND MASTER BRIEF  ━━━')}\n")
for line in digest.split("\n"):
    stripped = line.strip()
    if stripped.startswith("🔴"):  print(f"  {red(bold(line))}")
    elif stripped.startswith("🟡"): print(f"  {yellow(bold(line))}")
    elif stripped.startswith("✅"): print(f"  {green(bold(line))}")
    elif stripped.startswith("📌"): print(f"  {cyan(bold(line))}")
    elif stripped.startswith("⚠️"): print(f"  {magenta(bold(line))}")
    elif stripped: print(f"  {line}")
print()
pause(0.5)

# ─── STEP 5 ───────────────────────────────────────────────────────────────────
step(5, 5, "Delivering Notification (Multi-channel Delivery)")
notifier = UnifiedNotifier(preferred="desktop")
notifier.send(digest)
pause(0.3)

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "═"*65)
print(bold("  💓  MASTER DEMO COMPLETE"))
print("═"*65)
print(f"\n  {bold('What just happened (Master Hardening):')}")
print(f"  1. Multi-source Ingestion with Source Failure tracking")
print(f"  2. Advanced Deduplication (cross-source consolidation)")
print(f"  3. Score-based Intelligence with Confidence Labeling")
print(f"  4. 3-Tier Executive Briefing (🔴/🟡/✅)")
print(f"  5. Persistence to SQLite and Multi-channel Delivery")
print(f"\n  {bold('Interview line:')}")
print(f"  {cyan('\"An event-driven intelligence system that transforms raw operational')}")
print(f"  {cyan(' signals into prioritized decision recommendations for founders.\"')}")
print(f"\n  {bold('Next:')}")
print(f"  • Add GEMINI_API_KEY to .env for real AI  →  {cyan('https://aistudio.google.com/')}")
print(f"  • Start the loop: {cyan('python heartbeat.py')}")
print(f"\n{dim('  github.com/sid0803/heartbeat-system')}\n")
