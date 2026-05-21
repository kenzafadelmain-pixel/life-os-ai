# LIFE OS AI

> **Your AI Operating System for a Better Life.**
> A futuristic, AI-powered life management workspace for students and knowledge workers.
> Built end-to-end in Python · Flask · SQLite · vanilla JavaScript.

Final-year graduation project — production-shaped architecture, ten integrated
modules, a distinctive *Aurora* design system, and an AI that learns *you*.

---

## ✨ What it does

LIFE OS AI is a single workspace that absorbs your day and gives it back to you
as insight. One database, one AI core, ten cooperating modules:

| # | Module | What it does |
|---|---|---|
| 01 | **Aurora Chat** | ChatGPT-grade assistant with persistent memory across sessions. Supports OpenAI, Gemini, *or* a deterministic local engine when no key is set. |
| 02 | **Smart Dashboard** | Live productivity score, mood pulse, 14-day trend, foresight tiles, activity stream. |
| 03 | **Productivity Analyzer** | Detects your peak window, sleep debt, procrastination drift, late-night drop-off. |
| 04 | **Study Planner** | Subjects, exam countdowns, AI-generated 7-day plan, real Pomodoro timer that logs every session. |
| 05 | **Mood & Emotion** | Free-write a journal entry — Aurora returns emotion, stress, motivation + a supportive reflection. |
| 06 | **Task Kanban** | Drag-and-drop board with priorities, deadlines, overdue detection, AI next-up. |
| 07 | **Foresight Engine** | The headline feature — burnout risk, 7-day productivity forecast, task-completion probability, emotional stability. |
| 08 | **Voice Assistant** | Web-Speech in, gTTS out. Talk to Aurora hands-free. |
| 09 | **Files & Notes** | Upload PDFs/DOCX — get an extractive summary and auto-generated flashcards. |
| 10 | **Automation Engine** | Pluggable jobs: organise uploads, snapshot DB, queue reminders, generate daily reports. |

---

## 🧱 Architecture at a glance

```
life_os_ai/
├── run.py                     # entry point — boots the app + initialises DB
├── config.py                  # Dev / Prod / Test config classes
├── requirements.txt
├── .env.example               # copy to `.env` to set API keys
│
├── app/
│   ├── __init__.py            # Flask application factory
│   │
│   ├── core/                  # ─── domain logic (OOP) ──────────────────
│   │   ├── database.py        # DatabaseManager — schema, connections
│   │   ├── chatbot.py         # AIChatbot + OpenAI/Gemini/local backends
│   │   ├── emotion.py         # EmotionDetector — sentiment + classification
│   │   ├── analyzer.py        # ProductivityAnalyzer — patterns & insights
│   │   ├── predictor.py       # PredictionEngine — burnout, forecast, etc.
│   │   ├── services.py        # VoiceAssistant, FileSummariser, AutomationEngine
│   │   └── auth.py            # @login_required + helpers
│   │
│   ├── models/                # ─── data-mapper repositories ────────────
│   │   ├── user.py            # User + UserRepository
│   │   ├── task.py            # Task + TaskManager
│   │   ├── study.py           # Subject + StudyPlanner
│   │   ├── chat.py            # ChatSession + ChatRepository
│   │   └── data.py            # MoodRepository, ProductivityLogRepository, FileRepository, MemoryRepository
│   │
│   ├── routes/                # ─── Flask blueprints ────────────────────
│   │   ├── main.py            # landing page + healthcheck
│   │   ├── auth.py            # /register, /login, /logout
│   │   ├── dashboard.py       # /app  — command center
│   │   ├── chat.py            # /app/chat — Aurora
│   │   ├── tasks.py           # /app/tasks — kanban
│   │   ├── study.py           # /app/study — pomodoro + planner
│   │   ├── mood.py            # /app/mood — journal + analytics
│   │   ├── productivity.py    # /app/productivity — logs + foresight
│   │   ├── files.py           # /app/files — upload, summarise, flashcards
│   │   ├── voice.py           # /app/voice — TTS endpoint
│   │   └── settings.py        # /app/settings — profile, memory, automations
│   │
│   ├── templates/             # Jinja2 templates
│   ├── static/css/            # base.css + app.css + landing.css + auth.css
│   └── static/js/             # app, landing, dashboard, chat, tasks, study, mood, files
│
├── instance/                  # SQLite DB lives here (auto-created)
└── uploads/                   # User files (auto-created, gitignored)
```

### Object-oriented core

Every domain concept is a class. The headline ones:

| Class | Purpose |
|---|---|
| `DatabaseManager` | SQLite wrapper — connections, schema, query helpers, transactions. |
| `AIChatbot` | Provider-agnostic chat with **OpenAIBackend / GeminiBackend / LocalIntelligenceEngine** fallback. |
| `EmotionDetector` | Lexicon-based sentiment + emotion classifier. Zero deps. |
| `ProductivityAnalyzer` | Composite score + natural-language recommendations from observed patterns. |
| `PredictionEngine` | Burnout risk, 7-day OLS forecast, task-completion probability, emotional stability. |
| `TaskManager` | Kanban CRUD + priority queues + statistics. |
| `StudyPlanner` | Subjects, sessions, AI-generated weekly plan. |
| `VoiceAssistant` | gTTS wrapper that degrades gracefully if the library is missing. |
| `FileSummariser` | PDF/DOCX/TXT text extraction + extractive summarisation + flashcards. |
| `AutomationEngine` | Pluggable named jobs registry. |

---

## 🚀 Getting started — in 3 minutes

```bash
# 1. clone or unzip
cd life_os_ai

# 2. create a virtualenv
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate            # Windows

# 3. install
pip install -r requirements.txt

# 4. (optional) configure AI keys — works fine without them
cp .env.example .env
#   then edit .env to add OPENAI_API_KEY or GEMINI_API_KEY

# 5. (optional) seed sample data so the dashboard isn't empty
python seed_data.py

# 6. run
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

### Demo credentials (only if you ran `seed_data.py`)

```
email:    demo@lifeos.ai
password: aurora-demo-2026
```

---

## 🤖 AI configuration

The chat system uses **three** interchangeable backends. The first available wins:

1. **OpenAI** — set `OPENAI_API_KEY` (uses `gpt-4o-mini` by default; override with `AI_MODEL_OPENAI`).
2. **Google Gemini** — set `GEMINI_API_KEY` (uses `gemini-1.5-flash` by default).
3. **Local engine** — always available. Deterministic, no network. So the demo always *works*.

Get keys:

- OpenAI: https://platform.openai.com/api-keys
- Gemini: https://aistudio.google.com/app/apikey

You can switch providers from `/app/settings` at any time.

---

## 🎨 Design system — "Aurora"

A specific, named aesthetic — not generic dark mode:

- **Typography**: Fraunces (display, italic ligatures) + Inter (body) + JetBrains Mono (data)
- **Palette**: void black, glass surfaces, neon cyan + violet + pink accents
- **Motion**: drifting aurora blobs, scroll-reveals, orbital hero visual, ring-progress indicators
- **Layout**: asymmetric grids, generous whitespace, mono-eyebrow labels (`// signal`)
- **Surfaces**: real glassmorphism — `backdrop-filter: blur(20px)` + 1px borders + grain overlay

---

## 🧪 Testing

A small sanity test suite ships in `tests/`:

```bash
python -m unittest discover tests
```

The tests use an in-memory SQLite database (`":memory:"`) so they don't touch your real data.

---

## 📂 Sample data

Run `python seed_data.py` to populate:

- a demo user (`demo@lifeos.ai` / `aurora-demo-2026`)
- 6 tasks across all statuses
- 4 subjects with realistic exam dates
- 14 days of productivity logs + study sessions
- 8 mood journal entries
- 3 long-term memories for Aurora

This gives you a fully populated dashboard from the first click.

---

## 🔐 Security notes

- Passwords are stored with `werkzeug.security` (PBKDF2-SHA256 by default).
- Sessions use HttpOnly + SameSite=Lax cookies.
- File uploads are restricted to a safe extension whitelist and 32 MB.
- SQLite foreign keys + cascading deletes are enforced.

This is a **demo / academic project** — for any real deployment you'd want HTTPS,
proper secret management, rate-limiting, and a stronger session backend.

---

## 🛠️ Tech stack

- **Backend**: Python 3.10+, Flask 3, Werkzeug, Jinja2
- **Database**: SQLite (zero-install, single file)
- **Frontend**: vanilla HTML/CSS/JS — no build step, no framework lock-in
- **Charts**: Chart.js (CDN)
- **AI**: OpenAI, Gemini, or local fallback
- **Optional**: pypdf, python-docx, gTTS

---

## 📜 License

MIT — built as a graduation project. Use it, fork it, learn from it.

---

## 🎓 Built as a final-year project

The goal was a system that looks and feels like a real AI startup product
while being completely buildable in a semester. Every line of code is here in
the repo — nothing is hidden behind paywalled cloud services. Have fun.

**Aurora is awake. ✦**
