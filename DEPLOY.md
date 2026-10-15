# Deploy CareerBoost to Vercel

The project is deployable as-is: a Vite static frontend + a FastAPI serverless
function under `/api`, wired by [vercel.json](vercel.json) and [api/index.py](api/index.py).

## What's already set up

| Piece | File | What it does |
|---|---|---|
| ASGI entrypoint | `api/index.py` | Imports the FastAPI app so Vercel serves it as a Python function |
| Routing | `vercel.json` | `/api/*` → FastAPI function; everything else → React SPA |
| Build | `vercel.json` | Builds `frontend/`, serves `frontend/dist` |
| Python deps | `requirements.txt` | Root file pointing Vercel at `backend/requirements.txt` |
| SQLite on serverless | `backend/app/core/database.py` | Falls back to `/tmp` (read-only FS on Vercel) |
| Upload filter | `.vercelignore` | Skips venv, Vosk model, DB files, node_modules |

## Steps

1. **Push to GitHub** (done — repo: `sribalajikr/CAREERBOOST1`, branch `main`).
2. Go to [vercel.com/new](https://vercel.com/new) → **Import** `sribalajikr/CAREERBOOST1`.
   Vercel auto-detects the config from `vercel.json` — don't change the framework preset.
3. Under **Environment Variables**, set:
   ```
   SECRET_KEY            = <a long random string>        (REQUIRED — see below)
   ALLOWED_ORIGINS       = https://<your-app>.vercel.app
   DATABASE_URL          = <MySQL connection string>     (optional, see warning)
   SEED_DEMO             = true
   ```
4. Click **Deploy**. Done — the site lives at `https://<your-app>.vercel.app`.

## ⚠️ Read this before deploying

**Set `SECRET_KEY`.** The default in code is
`dev-insecure-secret-change-me`, and JWTs are signed with it — anyone who knows
it can forge a login token for any user id. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Data does NOT persist without a MySQL database.** Vercel's filesystem is
read-only and resets on every deploy/cold start, so the SQLite fallback means
every visitor gets an empty database that vanishes. That's fine for a demo,
but for real users you need a hosted MySQL (e.g. PlanetScale, Aiven, or any
MySQL 8 server) and its connection string in `DATABASE_URL`:

```
DATABASE_URL = mysql+pymysql://user:password@host:3306/career_assistant
```

The app auto-creates all tables on first boot (`Base.metadata.create_all`).

**Voice transcription degrades gracefully.** The Vosk model (~40 MB) is not
uploaded (`.vercelignore`); the app keeps the browser `SpeechRecognition` +
typed-answer paths, exactly as it already does when the model is missing.

**Password-reset emails** need the SMTP vars from `backend/.env.example`
copied into Vercel env vars too, or reset codes won't be sent.

## Updating the deployment

```bash
git add -A && git commit -m "Describe the change" && git push
```

Vercel redeploys automatically on every push to `main`.

## Local check before deploying (optional but fast)

```bash
cd backend && venv/Scripts/python -m uvicorn index:app --app-dir ../api --port 8010
curl http://127.0.0.1:8010/api/health
```

This runs the exact same entrypoint Vercel uses.
