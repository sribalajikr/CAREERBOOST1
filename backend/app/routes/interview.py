"""Routes for Module 6 (technical prep) and Module 7 (mock interviews)."""
import random
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import InterviewAnswer, InterviewSession, Resume, User
from app.schemas_interview import (
    InterviewAnswerIn,
    InterviewAnswerOut,
    InterviewQuestionOut,
    InterviewReport,
    InterviewStartIn,
    PrepAnswerIn,
    PrepAnswerOut,
    PrepHistoryOut,
    PrepHistoryItem,
    PrepQuestion,
    PrepStats,
)
from app.services.interview_engine import evaluate_answer, final_evaluation, pick_next_question
from app.services.question_bank import HR, QUESTION_BY_ID, all_categories_for

router = APIRouter(prefix="/api/interview", tags=["interview"])


# ------------------------------------------------------------------ helpers
def _level_to_difficulty(level: Optional[str]) -> str:
    l = (level or "").lower()
    if "inter" in l:
        return "Intermediate"
    if "adv" in l:
        return "Advanced"
    return "Beginner"


def _user_career(user: User) -> str:
    if user.profile and user.profile.preferred_career:
        return user.profile.preferred_career
    return "Software Developer"


def _engine_profile(db: Session, user: User) -> dict:
    """Profile shape the engine expects (skills + latest resume analysis)."""
    skills: List[str] = (user.profile.skills if user.profile else []) or []
    latest = (
        db.query(Resume)
        .filter(Resume.user_id == user.id, Resume.is_latest == True)  # noqa: E712
        .order_by(Resume.created_at.desc())
        .first()
    )
    latest_resume = latest.analysis if latest and latest.score > 0 and isinstance(latest.analysis, dict) else None
    return {"skills": skills, "latest_resume": latest_resume}


def _answers_history(session: InterviewSession) -> List[dict]:
    return [
        {
            "question_id": (a.scores or {}).get("question_id", ""),
            "overall": a.overall or 0,
            "topic": a.topic or "General",
            "category": (a.scores or {}).get("category", ""),
        }
        for a in session.answers
    ]


def _store_answer(db: Session, session: InterviewSession, question: dict, result: dict, answer: str, input_mode: str) -> InterviewAnswer:
    row = InterviewAnswer(
        session_id=session.id,
        question_text=question["question"],
        topic=question.get("topic", "General"),
        difficulty=question.get("difficulty", "Intermediate"),
        answer_text=answer[:8000],
        input_mode=input_mode,
        scores={**result["scores"], "question_id": question.get("id", ""), "category": question.get("category", "")},
        overall=result["overall"],
        feedback=result["feedback"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_practice_session(db: Session, user: User) -> InterviewSession:
    career = _user_career(user)
    sess = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user.id, InterviewSession.mode == "practice")
        .order_by(InterviewSession.created_at.desc())
        .first()
    )
    if not sess:
        sess = InterviewSession(user_id=user.id, session_type="technical", mode="practice", career=career)
        db.add(sess)
        db.commit()
        db.refresh(sess)
    elif career and sess.career != career:
        # profile role changed — prep questions must follow the CURRENT role
        sess.career = career
        db.commit()
    return sess


def _planned_total(minutes: int, session_type: str = "technical") -> int:
    planned = max(3, min(10, round(minutes / 3)))
    if session_type == "hr":
        # never plan more HR questions than exist — repeats are not allowed
        planned = min(planned, len(HR))
    return planned


def _question_out(session: InterviewSession, question: dict) -> InterviewQuestionOut:
    return InterviewQuestionOut(
        session_id=session.id,
        question_number=len(session.answers) + 1,
        planned_total=session.requested_minutes and _planned_total(session.requested_minutes, session.session_type) or 5,
        question=PrepQuestion(
            id=question.get("id", ""),
            category=question.get("category", "General"),
            topic=question.get("topic", "General"),
            difficulty=question.get("difficulty", "Intermediate"),
            question=question["question"],
            concepts=question.get("concepts", []),
            hint=question.get("hint"),
        ),
        transition=question.get("transition", ""),
    )


# ------------------------------------------------------------------ Module 6
@router.get("/prep/next", response_model=PrepQuestion)
def prep_next(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    sess = _get_practice_session(db, user)
    profile = _engine_profile(db, user)
    difficulty = _level_to_difficulty(user.profile.experience_level if user.profile else "Beginner")
    q = pick_next_question(
        career=sess.career or _user_career(user),
        difficulty=difficulty,
        session_type="technical",
        answers=_answers_history(sess),
        profile=profile,          # no latest_resume -> bank questions only (clean answer round-trip)
        question_number=len(sess.answers) + 1,
        total_planned=10,
    )
    return PrepQuestion(
        id=q["id"], category=q["category"], topic=q["topic"], difficulty=q["difficulty"],
        question=q["question"], concepts=q.get("concepts", []), hint=q.get("hint"),
    )


@router.post("/prep/answer", response_model=PrepAnswerOut)
def prep_answer(
    payload: PrepAnswerIn,
    question_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    question = QUESTION_BY_ID.get(question_id)
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown question — load a new one.")
    user = db.get(User, user_id)
    sess = _get_practice_session(db, user)
    result = evaluate_answer(question, payload.answer, "text")
    row = _store_answer(db, sess, question, result, payload.answer, "text")
    return PrepAnswerOut(scores=result["scores"], overall=result["overall"], feedback=result["feedback"])


@router.get("/prep/history", response_model=PrepHistoryOut)
def prep_history(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    sess = _get_practice_session(db, user)
    rows = list(reversed(sess.answers))[:20]
    items = [
        PrepHistoryItem(
            topic=r.topic, category=(r.scores or {}).get("category", "General"),
            difficulty=r.difficulty, overall=r.overall,
            answered_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
    scores = [r.overall for r in sess.answers if r.overall]
    return PrepHistoryOut(
        items=items,
        answered_ids=[(r.scores or {}).get("question_id", "") for r in sess.answers],
        avg_score=round(sum(scores) / len(scores)) if scores else 0,
    )


@router.get("/prep/stats", response_model=PrepStats)
def prep_stats(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    sess = _get_practice_session(db, user)
    scores = [r.overall for r in sess.answers if r.overall]
    topics = {r.topic for r in sess.answers}
    cats = all_categories_for(sess.career or _user_career(user))
    return PrepStats(
        attempted=len(sess.answers),
        avg_score=round(sum(scores) / len(scores)) if scores else 0,
        topics_covered=len(topics),
        categories=cats,
    )


# ------------------------------------------------------------------ Module 7
@router.post("/sessions", response_model=InterviewQuestionOut)
def start_session(
    payload: InterviewStartIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    career = payload.career or _user_career(user)
    sess = InterviewSession(
        user_id=user.id,
        session_type=payload.session_type,
        mode="mock",
        career=career,
        difficulty=payload.difficulty,
        requested_minutes=payload.duration_minutes,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    profile = _engine_profile(db, user)
    q = pick_next_question(
        career=career, difficulty=payload.difficulty, session_type=payload.session_type,
        answers=[], profile=profile, question_number=1,
        total_planned=_planned_total(payload.duration_minutes, payload.session_type),
    )
    sess.pending_question = q
    db.commit()
    return _question_out(sess, q)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sess = db.query(InterviewSession).filter(
        InterviewSession.id == session_id, InterviewSession.user_id == user_id
    ).first()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview session not found.")
    base = {
        "session_id": sess.id,
        "session_type": sess.session_type,
        "career": sess.career,
        "difficulty": sess.difficulty,
        "status": sess.status,
        "questions_answered": len(sess.answers),
        "planned_total": _planned_total(sess.requested_minutes, sess.session_type),
    }
    if sess.status == "completed":
        base["report"] = _report(sess)
        return base
    user = db.get(User, user_id)
    history = _answers_history(sess)
    # the question currently on screen must not be re-served after a refresh
    pending = sess.pending_question or {}
    if pending.get("id") and all(h.get("question_id") != pending["id"] for h in history):
        history = history + [{"question_id": pending["id"], "overall": 0,
                              "topic": pending.get("topic", "General"),
                              "category": pending.get("category", "")}]
    q = pick_next_question(
        career=sess.career, difficulty=sess.difficulty, session_type=sess.session_type,
        answers=history, profile=_engine_profile(db, user),
        question_number=len(sess.answers) + 1, total_planned=_planned_total(sess.requested_minutes, sess.session_type),
    )
    sess.pending_question = q
    db.commit()
    base["next_question"] = _question_out(sess, q)
    return base


@router.post("/sessions/{session_id}/answer", response_model=InterviewAnswerOut)
def answer_session(
    session_id: int,
    payload: InterviewAnswerIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sess = db.query(InterviewSession).filter(
        InterviewSession.id == session_id, InterviewSession.user_id == user_id
    ).first()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview session not found.")
    if sess.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "This interview is already finished. Start a new one.")

    # evaluate against the exact question that was served (persisted at start/next)
    question = sess.pending_question
    if not question:
        # legacy sessions created before pending_question existed
        history = _answers_history(sess)
        last_qid = history[-1]["question_id"] if history else ""
        question = QUESTION_BY_ID.get(last_qid) or {
            "id": last_qid or "adhoc", "category": "General", "topic": "General",
            "difficulty": sess.difficulty, "question": "Tell me about a project you built.",
            "keywords": ["project", "built", "team", "challenge", "learn", "result"],
            "explanation": "Project questions test depth beyond theory. Structure: context → your contribution → decisions and why → outcome.",
        }

    result = evaluate_answer(question, payload.answer, payload.input_mode)
    row = _store_answer(db, sess, question, result, payload.answer, payload.input_mode)

    next_q = None
    if len(sess.answers) < _planned_total(sess.requested_minutes, sess.session_type):
        user = db.get(User, user_id)
        history = _answers_history(sess)
        answered_q = (sess.pending_question or {}).get("id", "")
        if answered_q and all(h.get("question_id") != answered_q for h in history):
            history = history + [{"question_id": answered_q, "overall": 0,
                                  "topic": question.get("topic", "General"),
                                  "category": question.get("category", "")}]
        q = pick_next_question(
            career=sess.career, difficulty=sess.difficulty, session_type=sess.session_type,
            answers=history, profile=_engine_profile(db, user),
            question_number=len(sess.answers) + 1, total_planned=_planned_total(sess.requested_minutes, sess.session_type),
        )
        sess.pending_question = q
        next_q = _question_out(sess, q)

    db.commit()
    return InterviewAnswerOut(
        answer_id=row.id, scores=result["scores"], overall=result["overall"],
        feedback=result["feedback"], next_question=next_q,
    )


def _report(sess: InterviewSession) -> dict:
    answers = [
        {
            "scores": a.scores or {},
            "overall": a.overall or 0,
            "topic": a.topic,
        }
        for a in sess.answers
    ]
    ev = final_evaluation(sess.session_type, sess.career or "", answers)
    return {
        "session_id": sess.id,
        "session_type": sess.session_type,
        "career": sess.career or "",
        "difficulty": sess.difficulty,
        "questions_answered": len(sess.answers),
        "overall_score": sess.overall_score or ev["overall_score"],
        "breakdown": (sess.scores or {}).get("breakdown", ev.get("breakdown", {})),
        "summary": sess.summary or ev.get("summary", ""),
        "strong_topics": ev.get("strong_topics", []),
        "weak_topics": ev.get("weak_topics", []),
        "suggestions": (sess.suggestions if sess.suggestions else ev.get("suggestions", [])),
        "created_at": sess.created_at.isoformat() if sess.created_at else "",
    }


@router.post("/sessions/{session_id}/finish", response_model=InterviewReport)
def finish_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sess = db.query(InterviewSession).filter(
        InterviewSession.id == session_id, InterviewSession.user_id == user_id
    ).first()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview session not found.")
    if not sess.answers:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Answer at least one question before finishing.")
    if sess.status != "completed":
        answers = [{"scores": a.scores or {}, "overall": a.overall or 0, "topic": a.topic} for a in sess.answers]
        ev = final_evaluation(sess.session_type, sess.career or "", answers)
        sess.scores = ev.get("breakdown", {})
        sess.overall_score = ev["overall_score"]
        sess.summary = ev.get("summary", "")
        sess.suggestions = ev.get("suggestions", [])
        sess.status = "completed"
        from datetime import datetime
        sess.completed_at = datetime.utcnow()
        db.commit()
    rep = _report(sess)
    return InterviewReport(**rep)


@router.get("/sessions", response_model=List[InterviewReport])
def list_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sess_rows = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id, InterviewSession.mode == "mock", InterviewSession.status == "completed")  # noqa: E712
        .order_by(InterviewSession.created_at.desc())
        .limit(10)
        .all()
    )
    return [InterviewReport(**_report(s)) for s in sess_rows]
