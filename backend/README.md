# Backend — AI Interview Prep & Career Guidance

FastAPI + SQLAlchemy (MySQL-ready) + JWT auth + rule-based AI engine.

## Run locally

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
copy .env.example .env           # adjust if you like; defaults just work
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Demo account: **demo@career.ai / demo1234**

## Database

Uses `DATABASE_URL` from `.env`:

- MySQL: `mysql+pymysql://user:password@localhost:3306/career_assistant`
- If MySQL is unreachable, the app automatically falls back to a local
  SQLite file (`career_assistant.db`) so the demo always runs.

## AI service

`app/services/ai_service.py` defines the `AIService` interface:

- `analyze_resume(file_name, pdf_bytes, profile)`
- `recommend_careers(profile, resume_skills)`

`RuleBasedAIService` (default, free, offline) implements both with
explainable rules. To plug a real free-tier LLM later, implement the same
interface and register it in `get_ai_service()` — nothing else changes.

## Module map

| Module | File(s) |
|---|---|
| 1 Auth & Profile | `routes/auth.py`, `routes/users.py` |
| 2 Resume Analysis | `routes/resumes.py`, `services/resume_parser.py` |
| 3 Career Recommendation | `routes/careers.py`, `services/career_data.py` |
| 4 Roadmap | `routes/roadmap.py`, `services/roadmap_data.py` |
| 5 Planner | `routes/planner.py` |
| Dashboard | `routes/dashboard.py` |

Future modules: add `routes/<module>.py` + one `include_router()` in `app/main.py`.
