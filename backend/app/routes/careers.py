"""Career recommendation routes backed by the AI service abstraction."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import Resume, User
from app.schemas import CareerResponse
from app.services.ai_service import get_ai_service

router = APIRouter(prefix="/api/careers", tags=["careers"])


@router.get("/recommend", response_model=CareerResponse)
def recommend(
    resume_id: Optional[int] = Query(None, description="Use a specific resume's skills"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        return CareerResponse(recommendations=[])

    profile = {}
    if user.profile:
        p = user.profile
        profile = {
            "skills": p.skills or [],
            "interests": p.interests or [],
            "degree": p.degree or "",
            "department": p.department or "",
            "preferred_career": p.preferred_career or "",
            "experience_level": p.experience_level or "Beginner",
            "cgpa": p.cgpa,
        }

    resume_skills = None
    if resume_id:
        r = db.get(Resume, resume_id)
        if r and r.user_id == user_id and isinstance(r.analysis, dict):
            resume_skills = r.analysis.get("skills") or []
    else:
        latest = (
            db.query(Resume)
            .filter(Resume.user_id == user_id, Resume.is_latest == True)  # noqa: E712
            .first()
        )
        if latest and isinstance(latest.analysis, dict):
            resume_skills = latest.analysis.get("skills") or []

    recs = get_ai_service().recommend_careers(profile, resume_skills)
    return CareerResponse(recommendations=recs)
