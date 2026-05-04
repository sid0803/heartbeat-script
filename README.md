
# 💓 Heartbeat

### **From 100 Notifications → 1 Clear Decision**

> Your **Personal AI Chief of Staff** that turns scattered signals (Slack, Gmail, Calendar, Notion, GitHub) into a single, actionable executive brief.

---

## 🧠 What is Heartbeat?

**Heartbeat** is a **privacy-first, local founder intelligence system** that continuously scans your deal and delivery context and delivers:

* 🔴 Critical deal risks (missed client replies, renewal risk, meeting conflicts)
* 🟡 Important follow-ups (proposal delays, owner gaps, blocked commitments)
* ✅ Informational updates (low-priority account or roadmap changes)

👉 Every **30 minutes → 1 clear decision**

---

## ⚡ How It Works (10 Sec Overview)

```mermaid
flowchart LR
    A[Scanners] --> B[Event Engine]
    B --> C[Classifier]
    C --> D[AI Summarizer]
    D --> E[Storage]
    E --> F[Delivery]

    style C fill:#ff4d4d,color:#fff
```

👉 **Signals → Context → Priority → Decision → Delivery**

---

## 🤯 Before vs After

| Without Heartbeat ❌ | With Heartbeat ✅ |
| ------------------- | ---------------- |
| 50+ notifications   | 1 clear brief    |
| Context switching   | Deep focus       |
| Missed priorities   | Ranked actions   |
| Stress              | Control          |

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph Input Layer
        A1[Slack]
        A2[Gmail]
        A3[GitHub]
        A4[Notion]
        A5[Calendar]
    end

    Note[Calendar connector can be configured from the dashboard with provider, calendar ID, lookahead window, and active status]
    Note --> A5

    subgraph Processing Layer
        B1[Event Engine]
        B2[Normalization]
        B3[Deduplication]
    end

    subgraph Intelligence Layer
        C1[Classifier]
        C2[Priority Scoring]
        C3[LLM Summarizer]
    end

    subgraph Storage
        D1[SQLite Vault]
    end

    subgraph Delivery
        E1[Dashboard]
        E2[Chrome Extension]
        E3[Notifications]
        E4[Slack / Email]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    A4 --> B1
    A5 --> B1

    B1 --> B2 --> B3 --> C1 --> C2 --> C3 --> D1
    C3 --> E1
    C3 --> E2
    C3 --> E3
    C3 --> E4
```

---

## 🧠 Core Intelligence Layers

### 1. 🔍 Scanners (Input Layer)

* Slack → Urgent messages
* Gmail → Revenue-risk emails
* GitHub → Customer-facing delivery blockers
* Notion → Tasks & roadmap
* Calendar → Client meetings and prep risk

---

### 2. 🧹 Event Engine

* Normalizes data into unified format
* Removes duplicates across sources

---

### 3. 🧠 Classifier (The Brain)

* Assigns **Priority Score (0–10)**
* Detects:

  * 💰 Revenue risks
  * 📅 Meeting risks
  * ⏳ Delays
  * 🔗 Cross-source signals

---

### 4. 📝 AI Summarizer

* Converts raw signals → **human decisions**
* Powered by:

  * Gemini / Claude / GPT / Local LLM

---

### 5. 📂 Persistence Layer

* Local SQLite storage
* Enables:

  * Daily summaries
  * Historical insights

---

### 6. 🔔 Delivery Layer

* Chrome Extension
* Dashboard
* Notifications
* Slack / Email

---

## 🎯 Priority Scoring Logic

```mermaid
graph LR
    A[Client escalation] --> +3
    B[Meeting conflict / prep gap] --> +3
    C[Proposal or renewal delay] --> +2
    D[Multi-source deal signal] --> CRITICAL
    E[Older than 24h] --> +1
```

### Final Output:

* 🔴 Critical (Act Now)
* 🟡 Warning (Needs Attention)
* ✅ Normal (Informational)

---

## 📝 Example Output (What Users Actually Get)

```txt
🔴 CRITICAL:
- Client ABC asked for revised pricing in Slack, and the renewal call is tomorrow morning.
- Impact: Deal could stall if the founder joins without updated terms.

🟡 WARNING:
- Proposal owner is unclear in Notion, and Gmail has an unanswered follow-up from the buyer.

✅ INFO:
- Investor intro call was moved from 3:00 PM to 4:30 PM.

👉 Recommended Action:
Send the pricing update today, assign proposal ownership, and prep the renewal call agenda before tomorrow morning.
```

---

## 💻 Developer View (Pipeline)

```python
def heartbeat_pipeline():
    events = scan_sources()
    normalized = normalize(events)
    scored = classify(normalized)
    summary = generate_summary(scored)
    store(summary)
    deliver(summary)
```

---

## 🗄️ Database Schema (SQLite)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT,
    password_hash TEXT
);

CREATE TABLE connector_configs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    connector_type TEXT,
    config_json TEXT
);

CREATE TABLE digests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🚀 Quick Start

### 1. Clone Repo

```bash
git clone https://github.com/sid0803/heartbeat-system
cd heartbeat-system
```

### 2. Backend Setup

```bash
pip install -r requirements.txt
python server/main.py
```

### 3. Frontend Setup

```bash
cd dashboard
npm install
npm run build
```

### 4. Load Extension

* Go to `chrome://extensions`
* Enable Developer Mode
* Load `/dashboard/dist`

---

## 🔒 Privacy-First Architecture

* ✅ 100% Local Processing
* ✅ SQLite (no external DB)
* ✅ No raw data leaves device
* ✅ Optional LLM usage

👉 **Your data never becomes someone else's model**

---

## 🧠 Why Heartbeat Wins

| Feature                | Traditional Tools | Heartbeat |
| ---------------------- | ----------------- | --------- |
| Multi-source reasoning | ❌                 | ✅         |
| Local-first AI         | ❌                 | ✅         |
| Executive summaries    | ❌                 | ✅         |
| Noise filtering        | ⚠️                | ✅         |
| Decision engine        | ❌                 | ✅         |

---

## 🧩 Supported Connectors

| Tool     | Purpose                                           |
| -------- | ------------------------------------------------- |
| Slack    | Team communication and urgent customer signals    |
| Gmail    | Client inbox, billing, and contract follow-ups    |
| GitHub   | Delivery blockers tied to customer commitments    |
| Notion   | Delivery status, overdue tasks, and timeline risk |
| Calendar | Upcoming client meetings and deal timing          |

## 🧠 Dashboard UI

- Adds a dedicated **Today’s client schedule risk** panel in the dashboard.
- Shows meeting conflicts, cancelled client calls, and prep risk separately from the digest.
- Uses a new `/calendar` API route to keep schedule risk visible immediately.

## 🔍 Why we scan each source

- Slack: catches deal pressure early because customers and partners often ask urgent questions there before a formal email exists.
- Gmail: protects revenue conversations such as renewals, invoices, contracts, pricing requests, and procurement follow-ups.
- Calendar: shows whether the founder is prepared for the next revenue moment: client calls, renewal meetings, investor intros, and partner check-ins.
- Notion: checks whether promised follow-ups have an owner and whether sales commitments are slipping after the meeting.
- GitHub: only matters when product delivery affects a customer promise, launch date, pilot, or paid implementation.

## ⚖️ Founder-first tradeoffs

- Slack and Gmail are checked first because deal risk usually appears in customer messages before it appears in project tools. A buyer asking "Can we get this by Friday?" is more urgent to a BD founder than an internal task label.
- Calendar is elevated because meetings create hard deadlines. A renewal call tomorrow, a double-booked investor intro, or a client meeting without an agenda should change what the founder does today.
- Notion is useful for accountability, but only after the customer signal is known. It answers "who owns the follow-up?" and "is the promised deck/proposal/launch task slipping?"
- GitHub is intentionally secondary for this audience. It is included only when delivery work maps to a customer-facing commitment such as a pilot launch, integration deadline, or paid implementation.
- Technical noise is not part of the primary founder brief. Operational details are only useful when they are translated into a customer or revenue consequence.
- Mock data keeps the demo understandable without every credential, but live Slack, Gmail, Calendar, Notion, and GitHub setup is required for accurate deal intelligence.

---

## 🗺️ Roadmap

* [ ] Discord Integration
* [ ] Telegram Alerts
* [ ] Jira / Linear Support
* [ ] Voice Briefing (AI audio)
* [ ] Mobile App

---

## ❓ FAQ

**Q: Why is nothing showing?**
→ Trigger the first scan manually.

**Q: Is it free?**
→ Yes (use Gemini free tier or local LLM).

**Q: Can I build my own connector?**
→ Yes, extend `BaseConnector`.

---

## ⭐ Final Thought

> Most tools give you **more data**
> Heartbeat gives you **clear decisions**

---
