"""
🎬 USER-COPILOT — Live Demo (with Founder Brain Intelligence Layer)
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
print(bold("  💓  USER-COPILOT  —  Founder Intelligence System"))
print(bold("  Full Live Demo  |  2026-03-27  22:48 IST"))
print("═"*65)
print(dim("  Demonstrating all 6 layers including the new Founder Brain.\n"))
pause(0.6)

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
from heartbeat.intelligence.signals import Severity
from heartbeat.core.summarizer import Summarizer
from heartbeat.delivery.unified_notifier import UnifiedNotifier

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
step(3, 5, f"🧠 Founder Brain — Rule Engine")
print(dim("  Converting raw noise into structured BUSINESS DECISIONS...\n"))
pause(0.5)

rule_engine     = RuleEngine()
business_events = rule_engine.analyze(events)
pause(0.4)

# Display business signals by severity
critical = [e for e in business_events if e.severity == Severity.CRITICAL]
urgent   = [e for e in business_events if e.severity == Severity.URGENT]
info     = [e for e in business_events if e.severity == Severity.INFO]

print(f"\n  {red(bold('🔴 CRITICAL SIGNALS'))}: {len(critical)}")
for e in critical:
    print(f"    {red('→')} [{e.signal_type.upper().replace('_',' ')}] {e.message}")
    print(f"       {dim('ACTION:')} {yellow(e.action)}")
    pause(0.2)

print(f"\n  {yellow(bold('🟡 URGENT SIGNALS'))}: {len(urgent)}")
for e in urgent:
    print(f"    {yellow('→')} [{e.signal_type.upper().replace('_',' ')}] {e.message}")
    print(f"       {dim('ACTION:')} {e.action}")
    pause(0.2)

print(f"\n  {green(bold('🟢 INFO SIGNALS'))}: {len(info)}")
for e in info:
    print(f"    {green('→')} {e.message}")
    pause(0.1)

print(f"\n  {bold('💡 This layer is your USP')}: raw data → structured business decisions.")
print(f"  {dim('Each signal answers: WHAT happened · HOW URGENT · WHAT TO DO')}")
pause(0.6)

# ─── STEP 4 ───────────────────────────────────────────────────────────────────
step(4, 5, "Generating COO Decision Brief (AI Summarizer)")
print(dim("  AI acting as your startup COO — not a generic summariser.\n"))
pause(0.4)
print(f"  {yellow('○')} No AI key in .env → using MOCK digest (same format as real AI)")
pause(0.4)
summarizer = Summarizer(provider="auto")
input_events = business_events if business_events else events
digest = summarizer.summarize(input_events)

print(f"\n  {bold('━━━  YOUR 60-SECOND DECISION BRIEF  ━━━')}\n")
for line in digest.split("\n"):
    stripped = line.strip()
    if stripped.startswith("🚨"):  print(f"  {red(bold(line))}")
    elif stripped.startswith("👀"): print(f"  {yellow(bold(line))}")
    elif stripped.startswith("✅"): print(f"  {green(bold(line))}")
    elif stripped.startswith("📌"): print(f"  {cyan(bold(line))}")
    elif stripped: print(f"  {line}")
print()
pause(0.5)

# ─── STEP 5 ───────────────────────────────────────────────────────────────────
step(5, 5, "Delivering Notification (Delivery Layer)")
notifier = UnifiedNotifier(preferred="desktop")
notifier.send(digest)
pause(0.3)

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "═"*65)
print(bold("  💓  DEMO COMPLETE"))
print("═"*65)
print(f"\n  {bold('What just happened:')}")
print(f"  1. Scanned {len(raw_data)} signals from 7 sources in the background")
print(f"  2. Normalised → {len(events)} structured events")
print(f"  3. Founder Brain detected {len(business_events)} business signals")
print(f"     ({len(critical)} critical, {len(urgent)} urgent, {len(info)} informational)")
print(f"  4. Generated a COO-style decision brief (not just a summary)")
print(f"  5. Delivered to your preferred channel")
print(f"\n  {bold('Interview line:')}")
print(f"  {cyan('\"An event-driven intelligence system that transforms raw operational')}")
print(f"  {cyan(' signals into prioritized decision recommendations for founders.\"')}")
print(f"\n  {bold('Next:')}")
print(f"  • Add GEMINI_API_KEY to .env for real AI  →  {cyan('https://aistudio.google.com/')}")
print(f"  • Start the loop: {cyan('python main.py')}")
print(f"\n{dim('  github.com/sid0803/user-copilot')}\n")
