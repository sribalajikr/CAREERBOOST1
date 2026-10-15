"""AI Interview Preparation & Career Guidance System — FastAPI backend.

Currently active modules (v1):
    1. Auth & Profile          /api/auth, /api/users
    2. Resume Analysis         /api/resumes
    3. Career Recommendation   /api/careers
    4. Career Roadmap          /api/roadmap
    5. Preparation Planner     /api/planner
    -  Dashboard (aggregates)  /api/dashboard

Architecture is modular: future modules (mock interviews, job tracker,
community, admin analytics, notifications) plug in as new files in
app/routes/ and one include_router() line here.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, SessionLocal, get_engine, is_fallback
from app.core.errors import register_exception_handlers
from app.routes import (analytics, auth, careers, dashboard, interview,
                        placement, planner, resumes, roadmap, speech, users)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()
    Base.metadata.create_all(bind=get_engine())
    _ensure_columns()
    if is_fallback():
        logger.warning("Running on SQLite fallback — set DATABASE_URL to a MySQL server for production.")
    if settings.SEED_DEMO:
        _seed_demo()
    yield


# Columns added after v1 — create_all() does not ALTER existing tables, so add
# them explicitly. Idempotent: duplicate-column errors are expected and ignored.
_LATE_COLUMNS = {
    "interview_sessions": [("pending_question", "JSON")],
    "placement_tasks": [("category", "VARCHAR(60)")],
}


def _ensure_columns() -> None:
    from sqlalchemy import text

    with get_engine().begin() as conn:
        for table, cols in _LATE_COLUMNS.items():
            for name, coltype in cols:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}"))
                    logger.info("Migrated: added %s.%s", table, name)
                except Exception:
                    pass  # column already exists (or DB-specific no-op)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Free, student-friendly AI career platform (rule-based AI core, modular by design).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resumes.router)
app.include_router(careers.router)
app.include_router(roadmap.router)
app.include_router(planner.router)
app.include_router(dashboard.router)

# Modules 6-10
app.include_router(interview.router)
app.include_router(speech.router)
app.include_router(analytics.router)
app.include_router(placement.router)


def _seed_demo() -> None:
    """Create a ready-to-explore demo account on first run."""
    from app.core.security import hash_password
    from app.models import Profile, User

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@career.ai").first():
            return
        user = User(email="demo@career.ai", name="Demo Student", hashed_password=hash_password("demo1234"), onboarded=True)
        user.profile = Profile(
            phone="9876543210",
            college="Sunrise Institute of Technology",
            degree="B.Tech",
            department="Computer Science",
            year_of_study="3rd Year",
            cgpa=8.4,
            skills=["Python", "Java", "C", "SQL", "HTML", "CSS", "JavaScript", "Git", "DSA", "OOP"],
            preferred_career="Software Developer",
            experience_level="Beginner",
            interests=["web development", "problem solving", "data"],
            daily_study_minutes=120,
        )
        db.add(user)
        db.commit()
        logger.info("Seeded demo account: demo@career.ai / demo1234")
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "ok",
        "modules": ["auth-profile", "resume-analysis", "career-recommendation", "roadmap", "planner", "dashboard",
                    "interview-prep", "mock-interview", "speech-analysis", "analytics", "placement"],
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "database": "sqlite-fallback" if is_fallback() else "primary"}
