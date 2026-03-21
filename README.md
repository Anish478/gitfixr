<div align="center">

# ⚡ gitFixr

### Autonomous GitHub issue repair — right from your browser.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-FF6B35)](https://langchain-ai.github.io/langgraph)
[![Cost](https://img.shields.io/badge/API%20Cost-$0-brightgreen)](README.md)

**gitFixr** is a Chrome extension + multi-agent backend that reads a GitHub issue, writes a fix, tests it in an isolated sandbox, scores it with a critic agent, and opens a Pull Request — automatically. It learns from every failure so it gets better over time.

[**Install Extension**](#) · [**View Demo**](#) · [**Report Bug**](#) · [**Request Feature**](#)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Agent Pipeline](#-agent-pipeline)
- [How It Works](#-how-it-works)
- [Self-Healing Memory](#-self-healing-memory)
- [Retry System](#-retry-system)
- [The Sandbox](#-the-sandbox)
- [The Dashboard](#-the-dashboard)
- [Data Models](#-data-models)
- [API Reference](#-api-reference)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Benchmarks](#-benchmarks)
- [Roadmap](#-roadmap)

---

## 🔍 Overview

You're browsing GitHub. You see an open issue. You click one button.

gitFixr handles the rest:

| Step | What Happens |
|------|-------------|
| 🧠 **Memory Check** | Searches past failures for similar issues — adjusts strategy before starting |
| 📖 **Read** | Fetches issue details and scans the most relevant source files |
| 📝 **Plan** | Generates a step-by-step fix plan informed by memory lessons |
| ✍️ **Write** | Writes the actual code patch using Gemini Flash |
| 🐳 **Sandbox** | Runs the patch in an isolated E2B container — tests + security scan |
| ⭐ **Score** | Critic agent scores the patch; retries up to 5× with escalating strategies |
| 💾 **Learn** | Stores failures as embeddings in ChromaDB for future runs |
| 🚀 **Ship** | Opens a real Pull Request with full context attached |

> No CLI. No configuration. No leaving the page. Gets smarter every run.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  CHROME EXTENSION                    │
│                                                      │
│  manifest.json       → extension config              │
│  content_script.js   → reads GitHub issue page       │
│  sidebar.html/.js    → live pipeline progress UI     │
│  dashboard.html/.js  → reliability + learning stats  │
│  background.js       → communicates with backend     │
│  styles.css                                          │
└────────────────────────┬────────────────────────────┘
                         │
                    HTTP + WebSocket
                         │
┌────────────────────────▼────────────────────────────┐
│                   BACKEND (FastAPI)                  │
│                                                      │
│  POST /fix-issue       → starts the pipeline         │
│  WS   /stream/{run_id} → streams live progress       │
│  GET  /dashboard/stats → feeds the dashboard         │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                 LANGGRAPH PIPELINE                   │
│                                                      │
│  Memory Retrieval    [SELF-HEALING]                  │
│  Agent 1: Code Reader                                │
│  Agent 2: Planner                                    │
│  Agent 3: Code Writer                                │
│  Agent 4: Sandbox    [TWIST 3 — E2B]                 │
│  Agent 5: Critic     [TWIST 1 — retry loop]          │
│  Memory Storage      [SELF-HEALING]                  │
│  Agent 6: PR Opener                                  │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
┌──────────▼──────────┐  ┌────────▼──────────────────┐
│   SQLite Database   │  │   ChromaDB (local)         │
│   [TWIST 2]         │  │   [SELF-HEALING]           │
│   Reliability stats │  │   Failure embeddings       │
│   Learning curve    │  │   Lessons learned          │
└─────────────────────┘  └────────────────────────────┘
```

---

## 🤖 Agent Pipeline

| # | Agent | Model | Role |
|---|-------|-------|------|
| 0 | Memory Retrieval | sentence-transformers (local) | Retrieves lessons from similar past failures |
| 1 | Code Reader | Groq — Llama 3.3 70B | Fetches + ranks relevant source files |
| 2 | Planner | Groq — Llama 3.3 70B | Generates step-by-step fix plan |
| 3 | Code Writer | Gemini 1.5 Flash | Writes the unified diff patch |
| 4 | Sandbox | E2B (no LLM) | Runs tests + security scan in isolation |
| 5 | Critic | Groq — Llama 3.3 70B | Scores patch quality, triggers retries |
| 6 | Memory Storage | sentence-transformers (local) | Stores failure embeddings for future runs |
| 7 | PR Opener | GitHub API (no LLM) | Opens the real Pull Request |

> **Total LLM API cost per fix: $0**

---

## 🔀 How It Works

```
GitHub Issue URL
      │
      ▼
┌─────────────────────────────────────────┐
│  Memory Retrieval          [SELF-HEALING]│
│  • Embeds issue title + body             │
│  • Queries ChromaDB for similar failures │
│  • Returns top 3 lessons e.g:           │
│    "threading.Lock deadlocks with async  │
│     — use asyncio.Lock instead"          │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent 1: Code Reader                   │
│  • Fetches issue title + body           │
│  • Searches repo for referenced files   │
│  • Groq selects top 3 relevant files    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent 2: Planner                       │
│  • Reads issue + files + memory lessons │
│  • Outputs step-by-step fix plan:       │
│    ["1. Use asyncio.Lock (not threading)"│
│     "2. Add null check on line 84"      │
│     "3. Add async edge case test"]      │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent 3: Code Writer    (per attempt)  │
│  • Attempt 1: Standard patch            │
│  • Attempt 2: Match plan precisely      │
│  • Attempt 3: Minimal change only       │
│  • Attempt 4: Defensive + guard clauses │
│  • Attempt 5: Memory-guided strategy    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent 4: Sandbox (E2B)   [TWIST 3]     │
│  • Spins up isolated container          │
│  • Applies patch to codebase            │
│  • Runs: pytest     → pass / fail       │
│  • Runs: bandit     → security score    │
│  • Destroys container after use         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent 5: Critic          [TWIST 1]     │
│  • quality:  patch matches plan? (0–1)  │
│  • coverage: edge cases covered? (0–1)  │
│  • security: from bandit scan    (0–1)  │
│  • overall:  average of all three       │
│                                         │
│  overall > 0.8  ──────────────► proceed │
│  overall ≤ 0.8, retry < 4  ──► retry   │
│  retry = 4  ───────────────► give up   │
└──────┬───────────────────────┬──────────┘
       │ success               │ all failed
       ▼                       ▼
┌──────────────┐   ┌───────────────────────┐
│  PR Opener   │   │  Memory Storage       │
│  • Fork repo │   │  [SELF-HEALING]       │
│  • New branch│   │  • Embeds failure     │
│  • Commit    │   │  • Stores in ChromaDB │
│  • Open PR   │   │  • Flag for human     │
└──────────────┘   └───────────────────────┘
```

---

## 🧬 Self-Healing Memory

gitFixr doesn't just retry blindly — it **remembers why it failed** and applies those lessons to future issues.

### Memory Entry Schema

```python
{
    # Semantic representation (for similarity search)
    "issue_embedding":        [...512 floats...],

    # Context
    "issue_summary":          "async race condition in request handler",
    "repo":                   "fastapi/fastapi",
    "issue_number":           47,

    # What failed
    "approach_taken":         "Added threading.Lock around shared state",
    "failure_reason":         "threading.Lock causes deadlock with asyncio",
    "critic_scores": {
        "quality":            0.45,
        "coverage":           0.60,
        "security":           0.90
    },

    # What to try instead
    "suggested_alternative":  "Use asyncio.Lock or asyncio.Semaphore",

    # Metadata
    "retry_count_at_failure": 4,
    "times_retrieved":        3,
    "timestamp":              "2026-03-21T10:30:00Z"
}
```

### Retrieval Flow

```
New issue arrives: "Login crashes under concurrent requests"
        │
        ▼
Embed issue → query ChromaDB → top 3 matches:

  0.89 similarity → "async race condition"
                    Lesson: use asyncio.Lock

  0.71 similarity → "concurrent db writes"
                    Lesson: use connection pooling

  0.64 similarity → "timeout under load"
                    Lesson: add asyncio.Semaphore
        │
        ▼
Planner context includes lessons before planning
        │
        ▼
Better first-attempt patch
```

### Improvement Over Time

```
           Success rate on recurring bug types
  
  80% ┤                              ╭──────────
  70% ┤                   ╭──────────╯
  60% ┤        ╭──────────╯
  40% ┤────────╯
      └─────────────────────────────────────────
        Run 1–10       Run 11–20      Run 21–30
```

Every failure makes the system smarter for the next run.

---

## 🔁 Retry System

Three independent retry layers work together:

### Layer 1 — Critic Loop (max 5 attempts)

| Attempt | Strategy |
|---------|----------|
| 1 | Standard patch — normal approach |
| 2 | Precision mode — match plan exactly |
| 3 | Minimal mode — smallest possible change |
| 4 | Defensive mode — null checks + guard clauses |
| 5 | Memory mode — apply ChromaDB lessons directly |

### Layer 2 — Sandbox Retry (max 3 attempts)

```
E2B container crashes?
  → Retry spin-up (×2)
  → Still failing? Mark tests_passed=False, continue
```

### Layer 3 — Memory (runs at start + end)

```
Before pipeline  → retrieve lessons → better attempt 1
After all fail   → store failure   → better future runs
```

### Timing

| Scenario | Attempts | Time |
|----------|----------|------|
| Best case | 1 | ~55 seconds |
| Average | 2–3 | ~2 minutes |
| Worst case | 5 | ~4.5 minutes |

---

## 🛡️ The Sandbox

Every patch is executed in an isolated E2B container before touching any real repository.

```
E2B Container Lifecycle:
  1. Spin up fresh python:3.11 container
  2. Upload relevant source files
  3. Apply the patch
  4. pip install pytest bandit
  5. Run pytest  ──► pass / fail + output
  6. Run bandit  ──► security issues list
  7. Destroy container

Security score = max(0.0,  1.0 − (issue_count × 0.1))
```

**Guarantees:** Isolated execution · No host machine access · 60s timeout · Auto-destroyed

---

## 📊 The Dashboard

All runs are logged to SQLite and surfaced in the extension's dashboard tab.

```
gitFixr Dashboard
════════════════════════════════════════════════════

  47 issues tried    31 PRs opened    66% success rate

────────────────────────────────────────────────────
  Per-Agent Reliability

  Code Reader   ████████░░  89%
  Planner       ███████░░░  76%
  Code Writer   ████████░░  84%
  Sandbox       █████████░  94%
  Critic        ██████████  98%

────────────────────────────────────────────────────
  Failure Hotspot
  Code Writer → Critic retry accounts for 34% of retries

────────────────────────────────────────────────────
  Self-Healing Memory

  Lessons stored          23
  Memory-assisted wins     6   ← only succeeded via memory
  Most reused lesson       asyncio.Lock over threading.Lock

────────────────────────────────────────────────────
  Learning Curve

  100% │                              ╭────
   80% │                   ╭──────────╯
   60% │        ╭──────────╯
   40% │────────╯
       └──────────────────────────────────
       Run 1-10    Run 11-20    Run 21-30

────────────────────────────────────────────────────
  Avg critic score    0.84
  Avg cost per fix    $0.00
  PRs merged           8 ⭐
```

---

## 💾 Data Models

### AgentState

```python
class AgentState(TypedDict):
    # Issue context
    issue_url:              str
    issue_title:            str
    issue_body:             str
    repo_owner:             str
    repo_name:              str

    # Code Reader output
    relevant_files:         list[dict]      # [{path, content}]

    # Memory output
    memory_lessons:         list[str]       # lessons from ChromaDB
    memory_matches:         int             # number of similar failures found

    # Planner output
    plan:                   list[str]

    # Code Writer output
    patch:                  str             # unified diff
    retry_strategy:         str             # strategy used this attempt

    # Sandbox output
    sandbox_result:         dict            # {tests_passed, test_output,
                                            #  security_issues, security_score}

    # Critic output
    critic_scores:          dict            # {quality, coverage, security, overall}

    # Retry tracking
    retry_count:            int             # 0–4 (attempt 5 is memory-guided)
    memory_attempt_used:    bool

    # Final output
    pr_url:                 str
    status:                 str
    error:                  str
```

### WebSocket Event Format

```jsonc
{
  "step":      "memory_retrieval | code_reader | planner | code_writer | sandbox | critic | memory_storage | pr_opener",
  "status":    "running | success | failed | retrying",
  "data": {
    // step-specific payload
  },
  "timestamp": "2026-03-21T10:30:00Z"
}
```

### Database Schema

```sql
-- One row per pipeline run
CREATE TABLE runs (
    id                   TEXT PRIMARY KEY,
    issue_url            TEXT NOT NULL,
    repo                 TEXT NOT NULL,
    status               TEXT NOT NULL,        -- success | failed | human_review
    created_at           DATETIME NOT NULL,
    completed_at         DATETIME,
    pr_url               TEXT,
    memory_lessons_used  INTEGER DEFAULT 0
);

-- One row per agent execution within a run
CREATE TABLE agent_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT REFERENCES runs(id),
    agent_name   TEXT NOT NULL,
    status       TEXT NOT NULL,
    duration_ms  INTEGER,
    tokens_used  INTEGER
);

-- One row per critic scoring attempt
CREATE TABLE critic_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT REFERENCES runs(id),
    attempt_number  INTEGER NOT NULL,
    quality         REAL,
    coverage        REAL,
    security        REAL,
    overall         REAL,
    retry_strategy  TEXT
);

-- One row per stored failure lesson
CREATE TABLE memory_entries (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_summary         TEXT NOT NULL,
    repo                  TEXT NOT NULL,
    approach_taken        TEXT,
    failure_reason        TEXT,
    suggested_alternative TEXT,
    quality_score         REAL,
    coverage_score        REAL,
    security_score        REAL,
    times_retrieved       INTEGER DEFAULT 0,
    created_at            DATETIME NOT NULL
);
```

---

## 🌐 API Reference

### `POST /fix-issue`

Start a new pipeline run.

```jsonc
// Request
{
  "issue_url":     "https://github.com/owner/repo/issues/47",
  "github_token":  "ghp_xxxxxxxxxxxx"
}

// Response
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### `WS /stream/{run_id}`

Connect to receive live pipeline events.

```jsonc
// Example stream events
{ "step": "memory_retrieval", "status": "success",  "data": { "lessons_found": 2 } }
{ "step": "code_reader",      "status": "success",  "data": { "files_found": 3 } }
{ "step": "planner",          "status": "success",  "data": { "plan_steps": 4 } }
{ "step": "code_writer",      "status": "running",  "data": { "attempt": 1 } }
{ "step": "sandbox",          "status": "success",  "data": { "tests_passed": true, "security_score": 0.9 } }
{ "step": "critic",           "status": "retrying", "data": { "overall": 0.71, "attempt": 1 } }
{ "step": "critic",           "status": "success",  "data": { "overall": 0.87, "attempt": 2 } }
{ "step": "pr_opener",        "status": "success",  "data": { "pr_url": "https://github.com/..." } }
```

### `GET /dashboard/stats`

Fetch aggregated statistics for the dashboard.

```jsonc
// Response
{
  "total_runs":       47,
  "success_rate":     0.66,
  "prs_merged":       8,
  "per_agent_stats":  { "code_reader": 0.89, "planner": 0.76, "..." },
  "memory_stats":     { "lessons_stored": 23, "assisted_wins": 6 },
  "learning_curve":   [
    { "bucket": "1-10",   "success_rate": 0.40 },
    { "bucket": "11-20",  "success_rate": 0.62 },
    { "bucket": "21-30",  "success_rate": 0.74 }
  ],
  "recent_runs":      [ "..." ]
}
```

---

## 📦 Tech Stack

| Layer | Technology | Cost |
|-------|-----------|------|
| Chrome Extension | Vanilla JS | Free |
| Backend framework | FastAPI + Python 3.11 | Free |
| Agent orchestration | LangGraph | Free |
| LLM — Reader / Planner / Critic | Groq API — Llama 3.3 70B | Free tier |
| LLM — Code Writer | Google Gemini 1.5 Flash | Free tier |
| Code sandbox | E2B | Free tier (100 hr/mo) |
| Self-healing memory | ChromaDB (local) | Free |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Free |
| Relational database | SQLite | Free |
| GitHub integration | PyGithub | Free |
| Local development | Uvicorn | Free |
| Demo hosting | Render.com | Free tier |
| Chrome Web Store | One-time developer fee | $5 |

> **Total cost to build and ship: $5**

---

## 📁 Project Structure

```
gitfixr/
│
├── extension/                         # Chrome extension
│   ├── manifest.json
│   ├── content_script.js              # reads GitHub issue page
│   ├── sidebar.html
│   ├── sidebar.js                     # live pipeline progress UI
│   ├── dashboard.html
│   ├── dashboard.js                   # reliability + memory stats
│   ├── background.js                  # service worker / backend comms
│   └── styles.css
│
├── backend/                           # FastAPI application
│   ├── main.py                        # app entrypoint + routes
│   ├── pipeline/
│   │   ├── graph.py                   # LangGraph StateGraph definition
│   │   ├── state.py                   # AgentState TypedDict
│   │   ├── memory/
│   │   │   ├── retrieval.py           # ChromaDB query before pipeline
│   │   │   └── storage.py            # ChromaDB insert after failure
│   │   └── agents/
│   │       ├── code_reader.py         # Groq — file relevance ranking
│   │       ├── planner.py             # Groq — fix plan generation
│   │       ├── code_writer.py         # Gemini Flash — patch writing
│   │       ├── sandbox.py             # E2B — test + security execution
│   │       ├── critic.py              # Groq — quality scoring + retry
│   │       └── pr_opener.py          # GitHub API — PR creation
│   ├── database/
│   │   ├── models.py                  # SQLAlchemy table definitions
│   │   └── db.py                     # connection + session management
│   └── requirements.txt
│
├── data/
│   └── chromadb/                      # local vector store (gitignored)
│
├── ARCHITECTURE.md                    # shared reference for both devs
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Chrome or Chromium browser
- Git

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/gitfixr.git
cd gitfixr
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

```bash
# .env

# LLMs
GROQ_API_KEY=            # groq.com — free tier
GEMINI_API_KEY=          # aistudio.google.com — free tier

# Sandbox
E2B_API_KEY=             # e2b.dev — free tier (100hr/mo)

# GitHub
GITHUB_TOKEN=            # github.com/settings/tokens

# Memory (no key needed — runs locally)
CHROMADB_PATH=./data/chromadb
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# App
BACKEND_URL=http://localhost:8000
ENV=development
```

### 4. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

### 5. Load the Chrome extension

```
1. Open Chrome → chrome://extensions
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the /extension folder
```

### 6. Use gitFixr

```
1. Navigate to any GitHub issue
   e.g. github.com/fastapi/fastapi/issues/47
2. Click the gitFixr button in the toolbar
3. Watch the pipeline run in the sidebar
4. Click "Open PR" when the critic passes
```

---

## 🎯 Recommended Test Repositories

These repositories have clear issue descriptions, good test coverage, and active maintainers — ideal for benchmarking:

| Repository | Why |
|-----------|-----|
| `fastapi/fastapi` | Clean codebase, well-scoped bug reports |
| `psf/requests` | Simple isolated bugs, minimal dependencies |
| `pallets/flask` | Well documented, good test suite |
| `pydantic/pydantic` | Structured reproducible issues |
| `tiangolo/sqlmodel` | Small codebase, manageable scope |

Filter by labels: `good first issue` · `bug` · `easy`

---

## 📊 Benchmarks

*Results will be populated after testing on 25+ real issues.*

| Repository | Tested | PRs Opened | Success Rate |
|-----------|--------|------------|-------------|
| fastapi/fastapi | — | — | — |
| psf/requests | — | — | — |
| pallets/flask | — | — | — |
| **Total** | **—** | **—** | **—** |

| Metric | Result |
|--------|--------|
| Memory-assisted wins | — |
| Avg critic score | — |
| Avg time per fix | — |
| PRs merged by maintainers | — |

---

## 🗺️ Roadmap

```
Week 1  ─── Base pipeline (Issue → Code → PR) working end-to-end
Week 2  ─── E2B sandbox integration + Bandit security scan
Week 3  ─── Critic scoring loop + escalating retry strategies
Week 4  ─── ChromaDB self-healing memory layer
Week 5  ─── SQLite dashboard + learning curve logging
Week 6  ─── Test on 25+ real open-source issues, fix failures
Week 7  ─── Polish, fill benchmark table, ship to Chrome Web Store
```

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Built with [Groq](https://groq.com) · [Gemini](https://aistudio.google.com) · [LangGraph](https://langchain-ai.github.io/langgraph) · [ChromaDB](https://www.trychroma.com) · [E2B](https://e2b.dev) · [FastAPI](https://fastapi.tiangolo.com)

**If this project helped you, please consider giving it a ⭐**

</div>
