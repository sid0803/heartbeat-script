# Heartbeat System

This is a minimal prototype of a heartbeat system designed to provide non-technical founders with a concise, actionable digest every 30 minutes.

---

## 🧠 Architecture

**Pipeline:**
Ingestion → Classification → Summarization → Delivery

**Components:**
- `heartbeat.py` → orchestrator
- `classifier.py` → urgency detection
- `summarizer.py` → digest generation

---

## 📊 Sample Output

🔴 **ACTION REQUIRED:**
- [CLIENT] Client unhappy with delay (Slack — 2h ago)
- [TEAM BLOCKER] Auth bug staled (GitHub — 26h ago)

🟡 **FOR AWARENESS:**
- [PROJECT] Q2 Roadmap overdue (Notion)
- [OPPORTUNITY] New lead from demo (Gmail)

✅ **ALL CLEAR:**
- System infrastructure 100% UP
- Core database backups verified

---

---

## ✨ Key Features

- **30-Minute Check-in**: Runs automatically with cross-platform activity detection.
- **Master Hardening**: Structured source failure tracking (reports exactly which API failed).
- **Executive 3-Tier Reporting**: Standardized 🔴/🟡/✅ decision briefs.
- **Score-based Intelligence**: Every signal carries a numerical risk score and a `HIGH/MEDIUM/LOW` confidence label.
- **Advanced Deduplication**: Cross-source consolidation (matches Slack alerts with Gmail follow-ups).
- **7 Data Connectors**: Slack, Gmail, GitHub, Notion, Git history, health endpoints, and project file scan.
- **3 AI Providers**: Powered by **Gemini (free)**, **Claude (Anthropic)**, or **GPT-4o (OpenAI)**.
- **Daily Executive Summary**: A "Big Picture" report delivered every morning at 8:00 AM.

---

## 🏗️ System Architecture

Heartbeat System follows a **6-layer architecture** where each layer converts raw signals into cleaner, more actionable output.

```mermaid
graph TD
    subgraph Layer1 [Layer 1 — Data Connectors]
        S1[💬 Slack]
        S2[📧 Gmail]
        S3[🐙 GitHub]
        S4[📝 Notion]
        S5[🏥 Health Checks]
        S6[📁 Git History]
        S7[🗂️ Project Files]
    end

    subgraph Layer2 [Layer 2 — Event Engine]
        P1[EventProcessor — normalise + enrich]
    end

    subgraph Layer25 [Layer 3 — 🧠 Founder Brain - Rule Engine]
        R1[rule: client_risk]
        R2[rule: deadline_risk]
        R3[rule: system_failure]
        R4[rule: team_blocker]
        R5[rule: revenue_risk]
        R6[rule: opportunity_signal]
        R1 & R2 & R3 & R4 & R5 & R6 --> BE[BusinessEvent: message + action + severity]
    end

    subgraph Layer3 [Layer 4 — AI Summarizer - COO Brief]
        AI1[🔵 Gemini - free]
        AI2[🟣 Anthropic Claude]
        AI3[🟢 OpenAI GPT-4o]
        AI1 -->|fallback| AI2 -->|fallback| AI3
    end

    subgraph Layer4 [Layer 5 — Delivery]
        D1[🖥️ Desktop]
        D2[💬 Slack Webhook]
        D3[📬 HTML Email]
    end

    subgraph Layer0 [Layer 0 — Scheduler]
        SC[30-min loop + 8AM daily summary]
        DB[(SQLite — digest history)]
    end

    Layer1 -->|Raw signals| P1
    P1 -->|Structured events| Layer25
    BE -->|Business signals| Layer3
    Layer3 -->|COO decision brief| Layer4
    Layer3 -->|Save| DB
    SC -->|Triggers| Layer1
```

---

### Component Overview

1. **Layer 0 — Scheduler**: Activity-aware loop (skips cycles when you're away). Triggers the 8AM daily summary automatically.
2. **Layer 1 — Connectors**: 7 pluggable data sources. Each includes **Source Failure Monitoring** — if an API fails, it's reported in the digest rather than crashing.
3. **Layer 2 — Event Engine**: Normalises raw signals into a structured schema. Features **Advanced Deduplication** to consolidate similar messages from different sources.
4. **Layer 3 — 🧠 Founder Brain (Rule & Scoring Engine)**: The core USP. Combines 6 independent business rules with a **Keyword-Scoring Engine** to calculate risk and assign confidence labels (HIGH/MEDIUM/LOW).
5. **Layer 4 — AI Summarizer (Master COO Brief)**: Sends business signals to the LLM with a startup COO prompt. Output format: 🔴 Action Required / 🟡 For Awareness / ✅ All Clear / 📌 Bottom Line.
6. **Layer 5 — Delivery Engine**: Routes the digest to desktop, Slack, email, or all three.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- At least one AI API key *(optional — system works in mock mode without any key)*:
  - **Gemini** (free): [aistudio.google.com](https://aistudio.google.com/) — no credit card needed
  - **Anthropic**: [console.anthropic.com](https://console.anthropic.com/)
  - **OpenAI**: [platform.openai.com](https://platform.openai.com/)

### Installation

```bash
# Clone the repo
git clone https://github.com/sid0803/heartbeat-system.git
cd heartbeat-system

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy the example env file
cp .env.example .env
```

Edit `.env` and add your keys (you only need one):

```env
GEMINI_API_KEY=your-free-gemini-key    # recommended — free tier
ANTHROPIC_API_KEY=sk-ant-...           # optional
OPENAI_API_KEY=sk-...                  # optional
```

---

## 🛠️ Usage

### Quick Test (no API key needed)

Runs the full system in mock mode — see exactly what a founder receives:

```bash
python demo_run.py
```

### Test Suite

Validates all 7 connectors and the event schema:

```bash
python test_heartbeat.py
```

### Production Run

Starts the background monitoring loop (every 30 minutes + 8AM daily summary):

```bash
python heartbeat.py
```

---

## 🔌 Connector Setup

| Connector | Env Var / File | How to get it |
|---|---|---|
| **Slack** | `SLACK_TOKEN` | [api.slack.com/apps](https://api.slack.com/apps) → OAuth & Permissions → `channels:history` scope |
| **Gmail** | `heartbeat_app/config/gmail_credentials.json` | Google Cloud Console → Gmail API → Download credentials.json |
| **GitHub** | `GITHUB_TOKEN` | Settings → Developer Settings → Personal Access Tokens |
| **Notion** | `NOTION_TOKEN` + `database_id` in settings.yaml | [notion.so/my-integrations](https://www.notion.so/my-integrations) + share DB with integration |
| **Health** | Endpoint URLs in settings.yaml | Add your API/dashboard URLs |
| **Git / Files** | `repo_path` in settings.yaml | Local folder path |

---

## 🛡️ Reliability & Security

- **Local First**: All scanning runs on your machine. No data leaves without your keys.
- **Activity-Aware**: Skips heartbeat cycles when system is idle for 30+ minutes — saves API costs.
- **Graceful Degradation**: Every layer has a fallback. The system never crashes silently.
- **No Vendor Lock-in**: Switch AI providers in one line of config.

---

## 🗺️ Roadmap

- [x] Cross-platform activity detection (Mac / Windows / Linux)
- [x] Full codebase mapping
- [x] Daily 8AM executive summaries
- [x] Multi-provider AI — Gemini · Claude · GPT-4o
- [x] Gmail, GitHub, Notion connectors
- [x] HTML email delivery
- [x] Semantic event engine (type, age, suggested action)
- [x] Urgency classification (Rule Engine)
- [x] Multi-source ingestion (7 connectors)
- [x] Founder-friendly COO output
- [ ] Voice command status queries
- [ ] Weekly "CEO Performance" report
- [ ] Mobile push notification

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

> 🔗 [github.com/sid0803/heartbeat-system](https://github.com/sid0803/heartbeat-system) · **Made for Founders. Built by humans. Powered by AI.**
