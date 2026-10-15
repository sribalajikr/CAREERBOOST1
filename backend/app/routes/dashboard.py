"""Dashboard route — one call that feeds the whole home page."""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import PlanTask, Resume, RoadmapProgress, User
from app.routes.users import completion_info
from app.schemas import DashboardResponse, PlanTaskOut
from app.services.ai_service import get_ai_service
from app.services.roadmap_data import ROADMAPS, roadmap_task_totals

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    comp = completion_info(user)
    profile = user.profile

    # --- resume ---
    latest_resume: Optional[Resume] = (
        db.query(Resume)
        .filter(Resume.user_id == user.id, Resume.is_latest == True)  # noqa: E712
        .order_by(Resume.created_at.desc())
        .first()
    )
    resume_score = latest_resume.score if latest_resume and latest_resume.score > 0 else None

    # --- careers ---
    career_match = None
    recommended_career = None
    if profile and (profile.skills or profile.preferred_career):
        recs = get_ai_service().recommend_careers(
            {
                "skills": profile.skills or [],
                "interests": profile.interests or [],
                "degree": profile.degree or "",
                "department": profile.department or "",
                "preferred_career": profile.preferred_career or "",
                "experience_level": profile.experience_level or "Beginner",
                "cgpa": profile.cgpa,
            },
            (latest_resume.analysis.get("skills") if latest_resume and isinstance(latest_resume.analysis, dict) else None),
        )
        if recs:
            recommended_career = recs[0]["career"]
            career_match = recs[0]["match_percent"]

    # --- roadmap ---
    # same career choice as Analytics: the career the user actually has progress
    # in wins, otherwise fall back to the profile's preferred career — so the two
    # pages always show the same percentage.
    roadmap_progress = None
    roadmap_career = None
    roadmap_completed = roadmap_total = 0
    prog_row = db.query(RoadmapProgress).filter(RoadmapProgress.user_id == user.id).first()
    if prog_row and prog_row.career in ROADMAPS:
        roadmap_career = prog_row.career
    elif profile and profile.preferred_career in ROADMAPS:
        roadmap_career = profile.preferred_career
    if roadmap_career:
        template = ROADMAPS[roadmap_career]
        done_rows = (
            db.query(RoadmapProgress)
            .filter(RoadmapProgress.user_id == user.id, RoadmapProgress.career == roadmap_career, RoadmapProgress.completed == True)  # noqa: E712
            .all()
        )
        roadmap_completed = len(done_rows)
        # same totals as the Planner levels UI and Analytics (phases + finale levels)
        roadmap_total = roadmap_task_totals(roadmap_career, profile.skills if profile else None)
        roadmap_progress = round(roadmap_completed / roadmap_total * 100) if roadmap_total else 0

    # --- today's plan ---
    today = dt.date.today().isoformat()
    today_rows = (
        db.query(PlanTask)
        .filter(PlanTask.user_id == user.id, PlanTask.task_date == today)
        .all()
    )
    today_done = sum(1 for r in today_rows if r.status == "done")
    today_total = len(today_rows)
    today_progress = round(today_done / today_total * 100) if today_total else 0

    # --- upcoming ---
    upcoming_rows = (
        db.query(PlanTask)
        .filter(
            PlanTask.user_id == user.id,
            PlanTask.status == "pending",
            PlanTask.task_date >= today,
        )
        .order_by(PlanTask.task_date.asc(), PlanTask.id.asc())
        .limit(5)
        .all()
    )
    if not upcoming_rows:
        upcoming_rows = (
            db.query(PlanTask)
            .filter(PlanTask.user_id == user.id, PlanTask.status == "pending")
            .order_by(PlanTask.task_date.asc())
            .limit(5)
            .all()
        )

    hour = dt.datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
    if not user.onboarded:
        message = f"{greeting}, {user.name.split(' ')[0] if user.name else 'there'}! Finish your profile to unlock personalized guidance."
    elif resume_score is None:
        message = f"Welcome back, {user.name.split(' ')[0] if user.name else 'there'}! Upload your resume to get your first analysis."
    elif roadmap_progress is None:
        message = "Your resume is looking good — explore careers to find your best fit next."
    else:
        message = f"{greeting}! You're {roadmap_progress}% through your {roadmap_career} roadmap. Here's what to focus on today."

    return DashboardResponse(
        name=user.name or "Student",
        completion=comp.completion,
        resume_score=resume_score,
        resume_file=latest_resume.file_name if latest_resume else None,
        career_match=career_match,
        recommended_career=recommended_career,
        roadmap_progress=roadmap_progress,
        roadmap_career=roadmap_career,
        roadmap_completed=roadmap_completed,
        roadmap_total=roadmap_total,
        today_progress=today_progress,
        today_done=today_done,
        today_total=today_total,
        upcoming=[
            PlanTaskOut(
                id=r.id, title=r.title, category=r.category,
                duration_minutes=r.duration_minutes, status=r.status, task_date=r.task_date,
            )
            for r in upcoming_rows
        ],
        message=message,
    )
