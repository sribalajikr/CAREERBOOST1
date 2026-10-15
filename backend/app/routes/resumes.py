"""Resume upload + AI analysis routes."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import Resume, User
from app.schemas import ResumeAnalysisOut, ResumeOut
from app.services.ai_service import get_ai_service

logger = logging.getLogger("uvicorn.app")
router = APIRouter(prefix="/api/resumes", tags=["resumes"])

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB


def _latest(db: Session, user_id: int) -> Optional[Resume]:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id, Resume.is_latest == True)  # noqa: E712
        .order_by(Resume.created_at.desc())
        .first()
    )


def _to_out(r: Resume) -> ResumeOut:
    return ResumeOut(
        id=r.id,
        file_name=r.file_name,
        score=r.score,
        analysis=r.analysis,
        created_at=r.created_at.isoformat(),
        is_latest=r.is_latest,
    )


@router.post("/analyze", response_model=ResumeAnalysisOut, status_code=201)
async def analyze_resume(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please upload a PDF file (your resume).")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file looks empty. Please try again.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "PDF is larger than 5 MB. Please compress it.")

    user = db.get(User, user_id)
    profile = {}
    if user and user.profile:
        p = user.profile
        profile = {
            "skills": p.skills or [],
            "degree": p.degree or "",
            "department": p.department or "",
            "experience_level": p.experience_level or "Beginner",
        }

    ai = get_ai_service()
    try:
        analysis = ai.analyze_resume(file.filename, data, profile)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Resume analysis failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "We couldn't analyze that PDF. Try exporting it again.")

    if analysis.get("score", 0) == 0 and analysis.get("word_count", 0) == 0:
        # still store the attempt so the user sees the message, but not as latest good analysis
        res = Resume(user_id=user_id, file_name=file.filename, raw_text="", analysis=analysis, score=0, is_latest=True)
        db.add(res)
        db.commit()
        return ResumeAnalysisOut(**{k: v for k, v in analysis.items() if k in ResumeAnalysisOut.model_fields})

    # mark previous ones not latest
    db.query(Resume).filter(Resume.user_id == user_id, Resume.is_latest == True).update({"is_latest": False})  # noqa: E712
    res = Resume(
        user_id=user_id,
        file_name=file.filename,
        raw_text=analysis.get("_text", ""),
        analysis=analysis,
        score=int(analysis.get("score", 0)),
        is_latest=True,
    )
    db.add(res)
    db.commit()
    db.refresh(res)
    return ResumeAnalysisOut(**{k: v for k, v in analysis.items() if k in ResumeAnalysisOut.model_fields})


@router.get("/latest", response_model=Optional[ResumeOut])
def latest_resume(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    r = _latest(db, user_id)
    if not r:
        return None
    return _to_out(r)


@router.get("/history", response_model=list[ResumeOut])
def history(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(10)
        .all()
    )
    return [_to_out(r) for r in rows]
