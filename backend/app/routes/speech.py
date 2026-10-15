"""Routes for Module 8 (speech & communication analysis)."""
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import SpeechAnalysis, User
from app.schemas_interview import (
    SpeechAnalysisOut,
    SpeechAnalyzeIn,
    SpeechHistoryOut,
    TranscribeOut,
)
from app.services.interview_engine import analyze_speech
from app.services.question_bank import QUESTION_BY_ID
from app.services.speech_paragraphs import (
    generate_paragraph,
    get_paragraph_question,
    significant_words_from,
)
from app.services.transcription import transcribe_audio, transcription_available

router = APIRouter(prefix="/api/speech", tags=["speech"])


@router.get("/paragraph")
def new_paragraph(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """A fresh 80-150 word interview-style paragraph for reading/fluency practice.

    Never the same paragraph twice in a row: recent texts are excluded using the
    user's stored practice history plus this process's in-memory recent set.
    """
    recent = [
        r.question_text
        for r in db.query(SpeechAnalysis.question_text)
        .filter(SpeechAnalysis.user_id == user_id)
        .order_by(SpeechAnalysis.created_at.desc())
        .limit(12)
        .all()
        if r.question_text
    ]
    para = generate_paragraph(user_id, exclude_texts=recent)
    return {
        "id": para["id"],
        "text": para["text"],
        "word_count": para["word_count"],
        "topic": para["topic"],
        "category": "Interview Communication",
        "difficulty": "Intermediate",
    }


@router.post("/analyze", response_model=SpeechAnalysisOut)
def analyze(
    payload: SpeechAnalyzeIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)

    # resolve the question (bank question, generated paragraph, or free-form)
    question = QUESTION_BY_ID.get(payload.question_id or "") or get_paragraph_question(payload.question_id or "")
    if not question:
        question = {
            "id": payload.question_id or "custom",
            "topic": "Reading Practice",
            "category": "Interview Communication",
            "difficulty": "Intermediate",
            "question": payload.question_text,
            # score reading accuracy against the paragraph's own significant words
            "keywords": significant_words_from(payload.question_text),
            "explanation": "",
        }

    result = analyze_speech(question, payload.transcript, payload.duration_seconds, payload.input_mode)

    row = SpeechAnalysis(
        user_id=user.id,
        question_text=payload.question_text[:2000],
        transcript=payload.transcript[:8000],
        input_mode=payload.input_mode,
        metrics=result["metrics"],
        scores=result["scores"],
        communication_score=result["communication_score"],
        feedback=result["feedback"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return SpeechAnalysisOut(
        metrics=result["metrics"], scores=result["scores"],
        communication_score=result["communication_score"],
        feedback=result["feedback"], analysis_id=row.id,
    )


@router.get("/history", response_model=SpeechHistoryOut)
def history(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SpeechAnalysis)
        .filter(SpeechAnalysis.user_id == user_id)
        .order_by(SpeechAnalysis.created_at.desc())
        .limit(20)
        .all()
    )
    scores = [r.communication_score for r in rows if r.communication_score]
    return SpeechHistoryOut(
        attempts=[
            {
                "id": r.id,
                "question": (r.question_text or "")[:120],
                "communication": r.communication_score,
                "scores": r.scores or {},
                "mode": r.input_mode,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ],
        avg_communication=round(sum(scores) / len(scores)) if scores else 0,
    )


@router.get("/transcribe-status")
def transcribe_status():
    """Frontend capability probe: can the server transcribe recorded audio?"""
    return {"available": transcription_available(), "engine": "vosk"}


@router.post("/transcribe", response_model=TranscribeOut)
async def transcribe(
    audio: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    """Offline fallback STT: browser records audio, Vosk transcribes locally.

    Used when the browser's SpeechRecognition API is unavailable (Firefox,
    embedded webviews) or fails silently, so the 'speak your answer' flow
    still produces typed text without any paid API.
    """
    if not transcription_available():
        raise HTTPException(
            status_code=503,
            detail="Server speech-to-text is not available. Please type your answer instead.",
        )
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="No audio received.")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Recording too long (max 15 MB).")
    try:
        result = transcribe_audio(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not result.get("text"):
        raise HTTPException(
            status_code=422,
            detail="We couldn't hear any clear speech in that recording. Try again a bit closer to the mic, or type your answer.",
        )
    return TranscribeOut(**result)
