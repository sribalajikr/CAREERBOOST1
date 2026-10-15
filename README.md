# CareerBoost — AI Interview Preparation & Career Guidance System

A modern, student-friendly web platform that helps college students and fresh graduates
**analyze their resume, discover fitting careers, follow a guided roadmap, and stay on a
personalized daily study plan**.

Built with **FastAPI + MySQL-ready SQLAlchemy + JWT** on the backend and
**React + Vite + Tailwind CSS + Recharts + Lucide** on the frontend.
Everything runs on free/open-source tech — **no paid AI APIs required** (a rule-based AI
engine is included, and a real free-tier LLM can be plugged in later via one interface).

## Modules (v1)

| Module | What it does |
|---|---|
| 1. Auth & Profile | Sign up, login, logout, forgot/reset password, 4-step onboarding wizard, profile editing with completion % |
| 2. Resume Analysis | Drag-&-drop PDF upload, rule-based AI scoring, strengths/improvements, section & keyword checks, history |
| 3. Career Recommendations | Ranked career cards with match %, skill gaps, "why this fits you" reasoning, learning paths |
| 4. Career Roadmaps | 7-phase visual roadmaps per career, per-task checklists, resources, mini projects, overall readiness % |
| 5. Study Planner | Daily plan sized to your available time, mark-done/skip/reschedule, weekly themed dashboard, auto-adjustment |

Plus a live **student dashboard** aggregating resume score, career match, roadmap progress
and today's plan.

## Quick start

### Backend
```bash
cd backend
python -m venv venv
venv/Scripts/pip install -r requirements.txt      # Windows
cp .env.example .env                              # works as-is (SQLite fallback)
venv/Scripts/python -m uvicorn app.main:app --port 8000
```
To use MySQL instead of SQLite, set in `backend/.env`:
```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/career_assistant
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api -> :8000)
```

**Demo login:** `demo@career.ai` / `demo1234` (seeded automatically on first backend start).

## Architecture notes

- **AI service abstraction** (`backend/app/services/ai_service.py`): the app never talks to a
  vendor directly. The default `mock` provider is a fully rule-based engine; implement
  `AIService` + register it to swap in a real free-tier LLM later without touching routes.
- **Database**: SQLAlchemy models with automatic MySQL → SQLite fallback for zero-config demos.
- **API layer** (`frontend/src/services/api.js`): single place for JWT headers, error
  unwrapping and 401 handling.
- **Modular routes**: `auth`, `users`, `resumes`, `careers`, `roadmap`, `planner`, `dashboard`
  — future modules (interview Q&A, job listings, etc.) drop in as new routers.

## Tests

```bash
cd backend && venv/Scripts/python e2e_test.py run1   # 35 end-to-end API checks
cd frontend && npx vite build                        # production build check
```

See `.freebuff/run.md` for the detached-server run procedure used by the live preview.
