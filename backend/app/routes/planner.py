"""Planner routes — personalized daily & weekly preparation plans.

Generation logic (rule-based, adjusts automatically):
  1. Reads the student's roadmap position (first phase with pending tasks).
  2. Builds a "content stream" of study topics, practice and coding tasks.
  3. Splits the student's available daily time into friendly 30-45 min blocks.
  4. Carries pending tasks from previous days forward so nothing gets lost.
"""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import PlanTask, RoadmapProgress, User
from app.schemas import PlanResponse, PlanTaskOut, StudyTimeIn, WeeklyPlanResponse
from app.services.roadmap_data import ROADMAPS

router = APIRouter(prefix="/api/planner", tags=["planner"])

STUDY_TIME_OPTIONS = [
    {"minutes": 30, "label": "30 minutes", "blocks": [30]},
    {"minutes": 60, "label": "1 hour", "blocks": [30, 30]},
    {"minutes": 120, "label": "2 hours", "blocks": [40, 40, 40]},
    {"minutes": 210, "label": "3+ hours", "blocks": [45, 45, 40, 40, 40]},
]

WEEKDAY_CATEGORIES = [
    ("Monday", "Core Learning"),
    ("Tuesday", "DSA & Problem Solving"),
    ("Wednesday", "SQL & Tools"),
    ("Thursday", "Project Work"),
    ("Friday", "Aptitude & Reasoning"),
    ("Saturday", "Coding Practice"),
    ("Sunday", "Revision"),
]


def _active_career(user: User, db: Session) -> str:
    """The career the planner is built around."""
    p = user.profile
    preferred = (p.preferred_career if p else "") or ""
    if preferred in ROADMAPS:
        return preferred
    # fall back to the career with the most roadmap activity
    row = (
        db.query(RoadmapProgress)
        .filter(RoadmapProgress.user_id == user.id)
        .first()
    )
    if row and row.career in ROADMAPS:
        return row.career
    return "Software Developer"  # sensible default for students


def _content_stream(career: str, done_task_ids: set[str]) -> list[dict]:
    """Ordered study content based on roadmap position."""
    template = ROADMAPS[career]
    stream: list[dict] = []
    for i, phase in enumerate(template["phases"]):
        phase_done = all(f"p{i}t{j}" in done_task_ids for j in range(len(phase["tasks"])))
        prefix = "Practice" if phase_done else "Learn"
        for topic in phase["topics"][:4]:
            stream.append({
                "title": f"{prefix}: {topic}",
                "category": phase["title"],
            })
        if not phase_done:
            stream.append({"title": f"Practice: {phase['practice'][0]}", "category": phase["title"]})
    # always-available generic blocks
    stream.append({"title": "Coding Practice: solve 2 problems", "category": "Coding Practice"})
    stream.append({"title": "Aptitude Practice: quantitative + logical", "category": "Aptitude"})
    stream.append({"title": "Revision: review notes from this week", "category": "Revision"})
    return stream


def _blocks_for(minutes: int) -> list[int]:
    for opt in STUDY_TIME_OPTIONS:
        if minutes <= opt["minutes"]:
            return list(opt["blocks"])
    blocks, remaining = [], minutes
    while remaining > 0:
        b = 45 if remaining >= 45 else remaining
        blocks.append(b)
        remaining -= b
    return blocks


def _generate_daily(db: Session, user: User, date_str: str, carry_forward: bool = True) -> list[PlanTask]:
    profile = user.profile
    minutes = profile.daily_study_minutes if profile and profile.daily_study_minutes else 60
    career = _active_career(user, db)

    done_rows = (
        db.query(RoadmapProgress)
        .filter(RoadmapProgress.user_id == user.id, RoadmapProgress.career == career, RoadmapProgress.completed == True)  # noqa: E712
        .all()
    )
    done_ids = {r.task_id for r in done_rows}
    stream = _content_stream(career, done_ids)

    tasks: list[PlanTask] = []

    # 1. carry forward pending tasks from earlier days (max 2)
    if carry_forward:
        stale = (
            db.query(PlanTask)
            .filter(
                PlanTask.user_id == user.id,
                PlanTask.status == "pending",
                PlanTask.task_date < date_str,
            )
            .order_by(PlanTask.task_date.asc())
            .limit(2)
            .all()
        )
        for t in stale:
            tasks.append(
                PlanTask(
                    user_id=user.id, career=career, task_date=date_str,
                    title=t.title, category=t.category,
                    duration_minutes=t.duration_minutes, day_offset=dt.date.fromisoformat(date_str).weekday(),
                )
            )

    # avoid exact duplicate titles already planned today (done/skipped included)
    existing_titles = {
        t.title for t in db.query(PlanTask).filter(PlanTask.user_id == user.id, PlanTask.task_date == date_str).all()
    }

    # 2. fill remaining time with fresh content (no duplicate titles, even in-memory)
    used = sum(t.duration_minutes for t in tasks)
    used_titles = {t.title for t in tasks}
    blocks = _blocks_for(minutes)
    si = 0
    for b in blocks:
        if used + b > minutes + 15:
            break
        item = None
        for _ in range(len(stream)):
            candidate = stream[si % len(stream)]
            si += 1
            if candidate["title"] not in used_titles and candidate["title"] not in existing_titles:
                item = candidate
                break
        if item is None:  # stream exhausted without fresh content
            break
        used_titles.add(item["title"])
        tasks.append(
            PlanTask(
                user_id=user.id, career=career, task_date=date_str,
                title=item["title"], category=item["category"],
                duration_minutes=b, day_offset=dt.date.fromisoformat(date_str).weekday(),
            )
        )
        used += b

    db.add_all(tasks)
    db.commit()
    return tasks


def _plan_response(db: Session, user_id: int, date_str: str) -> PlanResponse:
    rows = (
        db.query(PlanTask)
        .filter(PlanTask.user_id == user_id, PlanTask.task_date == date_str)
        .order_by(PlanTask.id.asc())
        .all()
    )
    done = sum(1 for r in rows if r.status == "done")
    total = len(rows)
    return PlanResponse(
        date=date_str,
        tasks=[
            PlanTaskOut(
                id=r.id, title=r.title, category=r.category,
                duration_minutes=r.duration_minutes, status=r.status, task_date=r.task_date,
            )
            for r in rows
        ],
        completed=done,
        total=total,
        progress=round(done / total * 100) if total else 0,
    )


@router.get("/today", response_model=PlanResponse)
def get_today(
    generate: bool = Query(True, description="Generate the plan if it doesn't exist yet"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    today = dt.date.today().isoformat()
    existing = db.query(PlanTask).filter(PlanTask.user_id == user.id, PlanTask.task_date == today).count()
    if existing == 0 and generate:
        _generate_daily(db, user, today)
    return _plan_response(db, user_id, today)


@router.post("/regenerate", response_model=PlanResponse)
def regenerate_today(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Rebuild today's plan (keeps completed items, replaces the rest)."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    today = dt.date.today().isoformat()
    db.query(PlanTask).filter(
        PlanTask.user_id == user.id, PlanTask.task_date == today, PlanTask.status == "pending"
    ).delete()
    db.commit()
    _generate_daily(db, user, today, carry_forward=False)
    return _plan_response(db, user_id, today)


@router.get("/week", response_model=WeeklyPlanResponse)
def weekly_plan(
    start: Optional[str] = Query(None, description="Week start date YYYY-MM-DD (defaults to this week's Monday)"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    career = _active_career(user, db)
    template = ROADMAPS[career]

    if start:
        try:
            monday = dt.date.fromisoformat(start)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "start must be YYYY-MM-DD")
    else:
        today = dt.date.today()
        monday = today - dt.timedelta(days=today.weekday())

    done_rows = (
        db.query(RoadmapProgress)
        .filter(RoadmapProgress.user_id == user.id, RoadmapProgress.career == career, RoadmapProgress.completed == True)  # noqa: E712
        .all()
    )
    done_ids = {r.task_id for r in done_rows}

    # current roadmap focus for the "Core Learning" day
    focus_phase = None
    for i, phase in enumerate(template["phases"]):
        if not all(f"p{i}t{j}" in done_ids for j in range(len(phase["tasks"]))):
            focus_phase = phase
            break
    focus_title = focus_phase["title"] if focus_phase else template["phases"][-1]["title"]
    focus_topics = focus_phase["topics"][:3] if focus_phase else ["Interview preparation"]

    minutes = profile_minutes = user.profile.daily_study_minutes if user.profile else 60

    days = []
    total_done = total_tasks = 0
    for offset, (day_name, category) in enumerate(WEEKDAY_CATEGORIES):
        date = monday + dt.timedelta(days=offset)
        date_str = date.isoformat()
        rows = (
            db.query(PlanTask)
            .filter(PlanTask.user_id == user.id, PlanTask.task_date == date_str)
            .all()
        )
        done = sum(1 for r in rows if r.status == "done")
        total_done += done
        total_tasks += len(rows)

        suggestion = {
            "Core Learning": f"{focus_title} — {focus_topics[0] if focus_topics else 'next topic'}",
            "DSA & Problem Solving": "Solve 2-3 problems on your weak pattern",
            "SQL & Tools": "Practice SQL joins + one new tool",
            "Project Work": f"Advance your mini project ({template['phases'][min(4, len(template['phases'])-1)]['mini_project'][:40]}...)",
            "Aptitude & Reasoning": "Quantitative + logical reasoning practice set",
            "Coding Practice": "Timed practice: 2 easy + 1 medium problem",
            "Revision": "Review the week's notes and flashcards",
        }[category]

        days.append({
            "day": day_name,
            "date": date_str,
            "category": category,
            "suggestion": suggestion,
            "planned_minutes": minutes if rows else (minutes if date >= dt.date.today() else 0),
            "tasks": len(rows),
            "completed": done,
            "is_today": date == dt.date.today(),
        })

    return WeeklyPlanResponse(
        week_start=monday.isoformat(),
        days=days,
        overall_progress=round(total_done / total_tasks * 100) if total_tasks else 0,
    )


@router.patch("/tasks/{task_id}/status", response_model=PlanResponse)
def set_status(
    task_id: int,
    new_status: str = Query(..., pattern="^(done|pending|skipped)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    task = db.query(PlanTask).filter(PlanTask.id == task_id, PlanTask.user_id == user_id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    task.status = new_status
    db.commit()
    return _plan_response(db, user_id, task.task_date)


@router.post("/tasks/{task_id}/reschedule", response_model=PlanResponse)
def reschedule(
    task_id: int,
    to_date: Optional[str] = Query(None, description="Defaults to tomorrow"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    task = db.query(PlanTask).filter(PlanTask.id == task_id, PlanTask.user_id == user_id).first()
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    original_date = task.task_date
    target = to_date or (dt.date.fromisoformat(task.task_date) + dt.timedelta(days=1)).isoformat()
    task.task_date = target
    task.day_offset = dt.date.fromisoformat(target).weekday()
    task.status = "pending"
    db.commit()
    # return the plan for the date the task was moved FROM (what the UI is showing)
    return _plan_response(db, user_id, original_date)


@router.post("/study-time", response_model=PlanResponse)
def set_study_time(
    payload: StudyTimeIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Quick-set daily study time and rebuild today's pending plan."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    if not user.profile:
        from app.models import Profile
        user.profile = Profile(user_id=user.id, skills=[], interests=[])
    user.profile.daily_study_minutes = payload.minutes_per_day
    today = dt.date.today().isoformat()
    db.query(PlanTask).filter(
        PlanTask.user_id == user.id, PlanTask.task_date == today, PlanTask.status == "pending"
    ).delete()
    db.commit()
    _generate_daily(db, user, today, carry_forward=False)
    return _plan_response(db, user_id, today)
