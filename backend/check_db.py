"""Quick database viewer — run anytime to see what's stored.

Usage (from the backend folder):
    venv\\Scripts\\python check_db.py            -> overview of all tables
    venv\\Scripts\\python check_db.py users      -> just the accounts
    venv\\Scripts\\python check_db.py resumes    -> just the resumes
"""
import sys

from app.core.database import SessionLocal
from app.models import (
    InterviewAnswer,
    InterviewSession,
    PlanTask,
    PlacementTask,
    Profile,
    Resume,
    RoadmapProgress,
    SpeechAnalysis,
    User,
)

TABLES = {
    "users": (User, ["id", "email", "name", "onboarded", "created_at"]),
    "profiles": (Profile, ["user_id", "college", "degree", "year_of_study", "cgpa", "preferred_career", "experience_level", "daily_study_minutes"]),
    "resumes": (Resume, ["id", "user_id", "file_name", "score", "is_latest", "created_at"]),
    "roadmap_progress": (RoadmapProgress, ["id", "user_id", "career", "task_id", "completed"]),
    "plan_tasks": (PlanTask, ["id", "user_id", "task_date", "title", "status", "duration_minutes"]),
    "interview_sessions": (InterviewSession, ["id", "user_id", "session_type", "mode", "status", "overall_score", "created_at"]),
    "interview_answers": (InterviewAnswer, ["id", "session_id", "topic", "overall", "created_at"]),
    "speech_analyses": (SpeechAnalysis, ["id", "user_id", "communication_score", "created_at"]),
    "placement_tasks": (PlacementTask, ["id", "user_id", "week_number", "focus", "title", "status"]),
}


def overview(db):
    print("=" * 62)
    print("CAREERBOOST DATABASE — TABLE OVERVIEW")
    print("=" * 62)
    total = 0
    for name, (model, _) in TABLES.items():
        n = db.query(model).count()
        total += n
        print(f"  {name:22s} {n:5d} rows")
    print(f"  {'-' * 34}")
    print(f"  {'TOTAL':22s} {total:5d} rows")
    print("\nUsers in the system:")
    for u in db.query(User).all():
        n_res = db.query(Resume).filter(Resume.user_id == u.id).count()
        n_ses = db.query(InterviewSession).filter(InterviewSession.user_id == u.id).count()
        print(f"  #{u.id:<3} {u.email:32s} onboarded={u.onboarded}  resumes={n_res}  interviews={n_ses}")


def show(db, name):
    model, cols = TABLES[name]
    rows = db.query(model).all()
    print(f"\n=== {name} ({len(rows)} rows) ===")
    if not rows:
        return
    # column widths
    data = [[("" if getattr(r, c) is None else str(getattr(r, c)))[:28] for c in cols] for r in rows]
    widths = [max(len(c), max((len(row[i]) for row in data), default=0)) for i, c in enumerate(cols)]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("-" * (sum(widths) + 2 * len(widths)))
    for row in data:
        print("  ".join(v.ljust(w) for v, w in zip(row, widths)))


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "overview"
    db = SessionLocal()
    if which == "overview":
        overview(db)
    elif which in TABLES:
        show(db, which)
    else:
        print(f"Unknown table '{which}'. Options: overview or {', '.join(TABLES)}")
    db.close()


if __name__ == "__main__":
    main()
