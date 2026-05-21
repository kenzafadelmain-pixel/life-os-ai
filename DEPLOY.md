# Deploying LIFE OS AI to Render (free tier)

This guide gets your project live on the internet in **~15 minutes**, for
**free**, with a public URL like `https://life-os-ai.onrender.com` that you
can put in your viva slides, your CV, or your portfolio.

---

## Why Render?

- **Free tier** — no credit card required
- **Auto-deploy from GitHub** — every `git push` becomes a new deploy
- **HTTPS included** — Render gives you a real SSL certificate automatically
- **Zero config** — the `render.yaml` in this repo handles everything

### The one catch

Free instances **spin down after 15 minutes of inactivity**. The first request
after that takes ~30 seconds to wake up (the "cold start"). For your viva:

> **Open the site 1 minute before the demo starts.** That wakes it up.

That's the whole gotcha.

---

## Step 1 — Push your code to GitHub

You need your project in a GitHub repository. If it's not there yet:

### 1a. Create a GitHub account

Sign up at https://github.com if you don't have one. Free.

### 1b. Create a new repository

Go to https://github.com/new and create a repo named `life-os-ai`. **Don't**
initialise it with a README — your project already has one.

### 1c. Push your code

Open a terminal in your project folder:

```bash
cd life_os_ai

# Initialise git
git init
git add .
git commit -m "Initial commit: LIFE OS AI graduation project"

# Connect to your GitHub repo (replace YOUR-USERNAME)
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/life-os-ai.git
git push -u origin main
```

If git asks for credentials, use a **Personal Access Token** instead of your
password: https://github.com/settings/tokens (Generate new token → "classic"
→ tick `repo` → copy → paste as password).

Refresh your GitHub repo page — all your files should be there.

---

## Step 2 — Sign up for Render

1. Go to https://render.com
2. Click **Get Started**
3. Choose **Sign up with GitHub** (easiest — it auto-links your repos)

---

## Step 3 — Deploy

### 3a. Create a new Blueprint

1. In the Render dashboard, click **New +** → **Blueprint**
2. Click **Connect a repository**
3. Find `life-os-ai` in the list and click **Connect**

Render will detect the `render.yaml` file you already have and show you:

> **Service: life-os-ai** (web service, free plan)

### 3b. Click **Apply**

That's it. Render now:

1. Clones your repo
2. Installs `requirements.txt`
3. Runs `seed_data.py` (so reviewers can sign in instantly)
4. Starts gunicorn

The first build takes **3–5 minutes**. Watch the logs roll past — you'll see
the same `python seed_data.py` output you saw locally, then `gunicorn` boot.

### 3c. Open your live site

When the deploy finishes, Render shows you a URL at the top:

> `https://life-os-ai.onrender.com` (or similar)

Click it. You should see the LIFE OS AI landing page.

**Sign in with the demo account:**
- Email: `demo@lifeos.ai`
- Password: `aurora-demo-2026`

---

## Step 4 — (Optional) Add real AI

The local AI engine works fine for the viva, but if you want OpenAI or
Gemini-quality replies:

1. In the Render dashboard, click your service
2. **Environment** tab on the left
3. **Add Environment Variable**
4. Add either:
   - Key `OPENAI_API_KEY`, value `sk-...`  (from https://platform.openai.com/api-keys)
   - Key `GEMINI_API_KEY`, value `AIza...` (from https://aistudio.google.com/app/apikey)
5. Click **Save Changes** — Render auto-redeploys with the new key

---

## Step 5 — Update the live site

Whenever you want to deploy a change, just push to GitHub:

```bash
git add .
git commit -m "Improved the dashboard"
git push
```

Render watches your repo and **auto-redeploys** within 1–2 minutes. No
manual upload, no FTP, no clicking around.

---

## For your viva — final checklist

- [ ] Live URL works (open it 1 minute before the demo to wake it up)
- [ ] Demo account credentials handy (`demo@lifeos.ai` / `aurora-demo-2026`)
- [ ] At least one real chat message sent (so the dashboard activity feed looks alive)
- [ ] (Optional) `OPENAI_API_KEY` or `GEMINI_API_KEY` set in Render env vars
      → the chat reply will look more impressive
- [ ] Tell reviewers the URL or paste it in the chat — it works on any device

---

## Things you should know

### Where's my database?

On the free Render plan, the SQLite file lives at
`instance/life_os.db` inside the container. **It gets wiped on every deploy
and on every cold start.** For your viva that's fine — `seed_data.py` runs
on every start, so the demo data is always there.

If you want **persistent data** between deploys:
- Upgrade to Render's "Starter" plan ($7/mo) and uncomment the `disk:`
  block in `render.yaml`, **or**
- Migrate to PostgreSQL (Render offers a free Postgres database — ask me
  and I'll show you the ~30-line change to `database.py`).

### Why does the first visit take so long?

Free instances sleep after 15 min idle. The first request wakes them up.
This isn't a bug — it's how Render keeps the free tier sustainable.

### Can I use a custom domain?

Yes — Render supports custom domains on free instances. In your service
settings → **Custom Domains** → **Add Custom Domain**. You'll need to own
the domain ($10–15/year from Namecheap or Cloudflare).

For a viva you don't need this — `*.onrender.com` URLs work fine.

---

## Troubleshooting

**Build fails with "ModuleNotFoundError: gunicorn"**
→ Make sure `gunicorn>=21.2` is uncommented in `requirements.txt`. Push and redeploy.

**Site loads but shows "Internal Server Error"**
→ Check the **Logs** tab in Render. Most common cause: a missing env var.
  Try setting `SECRET_KEY` manually if `generateValue: true` didn't work.

**Demo login fails**
→ The seed didn't run. Check the build logs — you should see "✓ DEMO ACCOUNT READY".
  If not, the build crashed before reaching it. The logs will tell you why.

**"Application failed to respond" — but Render says it's running**
→ Cold start. Wait 30 seconds and refresh.

**Chat replies are slow / cut off**
→ Free instances have limited CPU. If you set an OpenAI/Gemini key, replies
  also depend on the AI provider. Increase `--timeout 120` in the Procfile
  if you keep hitting timeouts.

---

## Alternative: Railway

Render is the easiest, but **Railway** (https://railway.app) is a great
alternative — it has the same auto-deploy-from-GitHub flow and gives you
$5 of free credit each month, which is enough to run a small Flask app
24/7 without spin-downs.

Setup is almost identical to Render — just create a new project, connect
your GitHub repo, and Railway picks up the `Procfile`. The `render.yaml`
will be ignored (Railway doesn't read it), but everything else works.

---

That's it. Push to GitHub, click connect, get a URL. Good luck with your viva. ✦
