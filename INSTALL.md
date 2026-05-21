# LIFE OS AI — Installation guide

This is the step-by-step setup guide. For the high-level overview see **README.md**.

---

## 1. Prerequisites

- **Python 3.10 or newer** — verify with `python --version`
- **pip** (ships with Python)
- A modern browser (Chrome, Edge, Firefox, Safari)

That's it. No Node, no Docker, no database server.

---

## 2. Get the code

If you have the zip:

```bash
unzip life_os_ai.zip
cd life_os_ai
```

If you cloned from a repo, just `cd` into it.

---

## 3. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Windows (cmd)

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Your prompt should now show `(.venv)` at the start.

---

## 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Expected output: Flask + a handful of supporting packages. If `gTTS` or
`pypdf` fail to install on your platform, that's fine — the app falls back
gracefully (you'll just lose voice and PDF summarisation).

---

## 5. (Optional) Configure AI keys

The app **runs without any keys** thanks to the local AI engine.
To enable OpenAI or Gemini, copy the env template and add your key:

```bash
cp .env.example .env       # macOS / Linux
copy .env.example .env     # Windows
```

Open `.env` and set **one** of:

```
OPENAI_API_KEY=sk-...
# or
GEMINI_API_KEY=AIza...
```

Then load the env file. The cleanest way is to use a tool like
[python-dotenv](https://pypi.org/project/python-dotenv/) — or just `export`
the variables in your shell before running.

---

## 6. (Optional) Seed sample data

This populates a demo user, tasks, study sessions, productivity logs, and
mood entries so your dashboard isn't empty on first boot:

```bash
python seed_data.py
```

Login credentials it creates:

```
email:    demo@lifeos.ai
password: aurora-demo-2026
```

---

## 7. Run the development server

```bash
python run.py
```

Visit **http://127.0.0.1:5000**.

You should see the landing page. Click **Boot LIFE OS** to register, or sign
in with the demo account.

---

## 8. Running in production

The dev server is fine for the demo and for your viva. For real deployment,
use a proper WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

Set these env vars:

```
FLASK_CONFIG=production
SECRET_KEY=<a long random string>
```

Put it behind a reverse proxy (nginx, Caddy) with HTTPS terminated there.

---

## Troubleshooting

**"ModuleNotFoundError: flask"**
→ You didn't activate the virtualenv. Re-run step 3.

**"sqlite3.OperationalError: no such table"**
→ Delete `instance/life_os.db` and restart. The schema is created on import.

**Voice button greyed out**
→ Web Speech API only works in Chromium-based browsers and Safari.
   gTTS for replies needs the optional `gTTS` package + network access.

**PDF summary says "No readable text"**
→ The PDF is a scanned image. The app doesn't ship OCR by default.

**Charts not rendering**
→ Check the browser console — Chart.js loads from a CDN, so you need network.
   For offline use, vendor `chart.js` locally and update the script tag.

---

## Resetting the demo data

```bash
rm instance/life_os.db          # macOS / Linux
del instance\life_os.db         # Windows
python seed_data.py             # re-seed
```

You're good.
