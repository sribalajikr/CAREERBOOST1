"""Routes for Module 9 (performance analytics) and Module 10 (placement readiness).

Analytics is computed ONLY from real stored activity — interview answers,
speech attempts, roadmap progress, planner tasks. When there is no data the
response says so and the UI shows a friendly empty state.
"""
import datetime as dt
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import InterviewAnswer, InterviewSession, PlacementTask, PlanTask, Resume, RoadmapProgress, SpeechAnalysis, User
from app.schemas_interview import AnalyticsResponse, ProgressOut, TopicScore
from app.services.roadmap_data import ROADMAPS, roadmap_task_totals

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _weekly_key(d: dt.datetime) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def collect_stats(db: Session, user_id: int) -> dict:
    """Shared aggregation used by analytics, placement readiness and the dashboard."""
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.asc())
        .all()
    )
    completed = [s for s in sessions if s.status == "completed"]

    speech_rows = (
        db.query(SpeechAnalysis)
        .filter(SpeechAnalysis.user_id == user_id)
        .order_by(SpeechAnalysis.created_at.asc())
        .all()
    )

    questions_answered = sum(len(s.answers) for s in sessions)
    overalls = [a.overall for s in sessions for a in s.answers if a.overall]

    tech, comm = [], []
    for s in sessions:
        for a in s.answers:
            sc = a.scores or {}
            if sc.get("depth"):
                tech.append(sc["depth"])
            if sc.get("clarity"):
                comm.append(sc["clarity"])

    # topic-level performance (practice + mock combined)
    topic_scores: Dict[str, List[int]] = defaultdict(list)
    for s in sessions:
        for a in s.answers:
            if a.overall:
                topic_scores[a.topic or "General"].append(a.overall)
    ranked = sorted(
        ((t, round(sum(v) / len(v)), len(v)) for t, v in topic_scores.items()),
        key=lambda x: -x[1],
    )
    strong = [TopicScore(topic=t, avg=a, attempts=n) for t, a, n in ranked if a >= 65][:4]
    weak = [TopicScore(topic=t, avg=a, attempts=n) for t, a, n in reversed(ranked) if a < 65][:4]

    # roadmap progress (any career the user has progress in, else preferred)
    user = db.get(User, user_id)
    career = (user.profile.preferred_career if user.profile and user.profile.preferred_career else None)
    prog_row = db.query(RoadmapProgress).filter(RoadmapProgress.user_id == user_id).first()
    rc = prog_row.career if prog_row else career
    roadmap_progress = 0
    if rc and rc in ROADMAPS:
        done = db.query(RoadmapProgress).filter(
            RoadmapProgress.user_id == user_id,
            RoadmapProgress.career == rc,
            RoadmapProgress.completed == True,  # noqa: E712
        ).count()
        # same totals as the Planner levels UI and the Dashboard (phases + finale levels)
        total = roadmap_task_totals(rc, user.profile.skills if user.profile else None)
        roadmap_progress = round(done / total * 100) if total else 0

    planner_completed = (
        db.query(PlanTask)
        .filter(PlanTask.user_id == user_id, PlanTask.status == "done")  # noqa: E712
        .count()
    )

    speech_scores = [r.communication_score for r in speech_rows if r.communication_score]

    return {
        "sessions_all": sessions,
        "sessions_completed": completed,
        "speech_rows": speech_rows,
        "questions_answered": questions_answered,
        "attempts": len(sessions),
        "avg_overall": round(sum(overalls) / len(overalls)) if overalls else 0,
        "avg_technical": round(sum(tech) / len(tech)) if tech else 0,
        "avg_communication": round(sum(comm) / len(comm)) if comm else 0,
        "strong_topics": strong,
        "weak_topics": weak,
        "roadmap_progress": roadmap_progress,
        "planner_completed": planner_completed,
        "speech_attempts": len(speech_rows),
        "speech_avg": round(sum(speech_scores) / len(speech_scores)) if speech_scores else 0,
    }


@router.get("/progress", response_model=ProgressOut)
def progress(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Single source of truth for module percentages (items 9 & 10).

    Every component that shows a module % fetches it HERE, computed from the
    current user's stored activity only. A brand-new user gets all zeros and
    has_data=False — never a random number.
    """
    stats = collect_stats(db, user_id)

    latest = (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.is_latest == True)  # noqa: E712
        .order_by(Resume.created_at.desc())
        .first()
    )
    resume_score = latest.score if latest and latest.score > 0 else 0

    # split practice-mode answers from mock interviews
    practice_sessions = [s for s in stats["sessions_all"] if s.mode == "practice"]
    prep_answered = sum(len(s.answers) for s in practice_sessions)
    prep_scores = [a.overall for s in practice_sessions for a in s.answers if a.overall]
    prep_avg = round(sum(prep_scores) / len(prep_scores)) if prep_scores else 0

    mock_done = stats["sessions_completed"]
    mock_scores = [s.overall_score for s in mock_done if s.overall_score]
    mock_avg = round(sum(mock_scores) / len(mock_scores)) if mock_scores else 0

    speech_attempts = stats["speech_attempts"]
    speech_avg = stats["speech_avg"]
    planner = stats["roadmap_progress"]

    # placement readiness uses the exact same computation as the Placement page
    from app.routes.placement import readiness  # lazy: placement imports this module
    placement = readiness(user_id=user_id, db=db)
    placement_pct = placement.overall if placement.has_data else 0

    plan_total = db.query(PlacementTask).filter(PlacementTask.user_id == user_id).count()
    plan_completed = (
        db.query(PlacementTask)
        .filter(PlacementTask.user_id == user_id, PlacementTask.status == "done")  # noqa: E712
        .count()
    )

    def _mix(count: int, target: int, avg: int) -> int:
        """usage (count vs target, 60%) + quality (avg score, 40%) — deterministic."""
        usage = min(1, count / target)
        return round(usage * 60 + (avg / 100) * 40)

    modules = {
        "resumeAnalysis": resume_score,
        "interviewPreparation": _mix(prep_answered, 20, prep_avg),
        "speechPractice": _mix(speech_attempts, 10, speech_avg),
        "mockInterview": _mix(len(mock_done), 5, mock_avg),
        "planner": planner,
        "placementReadiness": placement_pct,
    }
    activity = {
        "prep_answered": prep_answered,
        "prep_avg": prep_avg,
        "questions_answered": stats["questions_answered"],
        "mock_completed": len(mock_done),
        "mock_avg": mock_avg,
        "speech_attempts": speech_attempts,
        "speech_avg": speech_avg,
        "roadmap_progress": planner,
        "planner_completed": stats["planner_completed"],
        "plan_total": plan_total,
        "plan_completed": plan_completed,
        "resume_score": resume_score,
    }
    has_data = (
        resume_score > 0
        or stats["questions_answered"] > 0
        or speech_attempts > 0
        or len(mock_done) > 0
        or planner > 0
        or plan_total > 0
    )
    if not has_data:
        return ProgressOut(has_data=False, modules={k: 0 for k in modules}, activity=activity)
    return ProgressOut(has_data=True, modules=modules, activity=activity)


@router.get("", response_model=AnalyticsResponse)
def analytics(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    stats = collect_stats(db, user_id)

    has_data = stats["questions_answered"] > 0 or stats["speech_attempts"] > 0
    if not has_data:
        return AnalyticsResponse(has_data=False)

    # ---- trend: per completed mock session (chronological)
    trend = [
        {"label": f"#{i + 1}", "score": s.overall_score or 0, "type": s.session_type}
        for i, s in enumerate(stats["sessions_completed"])
        if s.overall_score
    ][-10:]

    # ---- weekly averages, last 8 weeks
    weekly_scores: Dict[str, List[int]] = defaultdict(list)
    for s in stats["sessions_all"]:
        if s.created_at:
            for a in s.answers:
                if a.overall:
                    weekly_scores[_weekly_key(s.created_at)].append(a.overall)
    for r in stats["speech_rows"]:
        if r.created_at and r.communication_score:
            weekly_scores[_weekly_key(r.created_at)].append(r.communication_score)
    weeks = sorted(weekly_scores.keys())[-8:]
    weekly = [
        {"week": w, "avg": round(sum(v) / len(v))}
        for w, v in ((w, weekly_scores[w]) for w in weeks)
    ]

    return AnalyticsResponse(
        has_data=True,
        attempts=stats["attempts"],
        sessions_completed=len(stats["sessions_completed"]),
        questions_answered=stats["questions_answered"],
        avg_overall=stats["avg_overall"],
        avg_technical=stats["avg_technical"],
        avg_communication=stats["avg_communication"],
        trend=trend,
        weekly=weekly,
        strong_topics=stats["strong_topics"],
        weak_topics=stats["weak_topics"],
        roadmap_progress=stats["roadmap_progress"],
        planner_completed=stats["planner_completed"],
        speech_attempts=stats["speech_attempts"],
        speech_avg=stats["speech_avg"],
    )
