"""Database models — modular by domain so future modules plug in easily."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(120), default="")
    is_active = Column(Boolean, default=True)
    onboarded = Column(Boolean, default=False)
    reset_code = Column(String(10), nullable=True)
    reset_code_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    roadmap_progress = relationship("RoadmapProgress", back_populates="user", cascade="all, delete-orphan")
    plan_tasks = relationship("PlanTask", back_populates="user", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    speech_analyses = relationship("SpeechAnalysis", back_populates="user", cascade="all, delete-orphan")
    placement_tasks = relationship("PlacementTask", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    phone = Column(String(30), default="")
    college = Column(String(200), default="")
    degree = Column(String(120), default="")
    department = Column(String(120), default="")
    year_of_study = Column(String(30), default="")
    cgpa = Column(Float, nullable=True)
    skills = Column(JSON, default=list)          # list[str]
    preferred_career = Column(String(120), default="")
    experience_level = Column(String(40), default="Beginner")  # Beginner/Intermediate/Advanced
    interests = Column(JSON, default=list)       # list[str]
    daily_study_minutes = Column(Integer, default=60)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    file_name = Column(String(255), nullable=False)
    raw_text = Column(Text, default="")
    analysis = Column(JSON, nullable=False)      # output of the AI service
    score = Column(Integer, default=0)
    is_latest = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class RoadmapProgress(Base):
    """One row per (user, career, phase, task) completion record."""
    __tablename__ = "roadmap_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    career = Column(String(80), index=True)
    phase_index = Column(Integer)
    task_id = Column(String(120))
    completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="roadmap_progress")


class PlanTask(Base):
    __tablename__ = "plan_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    career = Column(String(80), default="")
    task_date = Column(String(10), index=True)   # "YYYY-MM-DD"
    title = Column(String(200), nullable=False)
    category = Column(String(60), default="General")
    duration_minutes = Column(Integer, default=30)
    status = Column(String(20), default="pending")  # pending | done | skipped
    day_offset = Column(Integer, default=0)         # 0=Mon .. 6=Sun within week plan
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="plan_tasks")


# ------------------------------------------------------------------
# Modules 6-10: interview preparation, mock interviews, speech,
# analytics (derived), and placement readiness.
# ------------------------------------------------------------------


def _wk() -> str:
    return datetime.utcnow().strftime("%G-W%V")


class InterviewSession(Base):
    """One mock-interview / practice session (module 6 practice sessions too)."""
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_type = Column(String(30), default="technical")  # quick|technical|hr|mixed|role
    mode = Column(String(20), default="mock")               # mock | practice | speech
    career = Column(String(80), default="")
    difficulty = Column(String(20), default="Intermediate")
    status = Column(String(20), default="active")           # active | completed
    requested_minutes = Column(Integer, default=15)
    scores = Column(JSON, default=dict)                      # final evaluation breakdown
    pending_question = Column(JSON, nullable=True)           # last question served (evaluated on answer)
    overall_score = Column(Integer, default=0)
    summary = Column(Text, default="")
    suggestions = Column(JSON, default=list)
    week_key = Column(String(10), default=_wk, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="interview_sessions")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")


class InterviewAnswer(Base):
    """A single Q&A turn inside a session — questions AND answers are stored."""
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), index=True)
    question_text = Column(Text, nullable=False)
    topic = Column(String(80), default="General")
    difficulty = Column(String(20), default="Beginner")
    answer_text = Column(Text, default="")
    input_mode = Column(String(20), default="text")          # text | voice
    scores = Column(JSON, default=dict)                       # relevance/structure/clarity/...
    overall = Column(Integer, default=0)
    feedback = Column(JSON, default=dict)                     # explanation/strengths/improvements/revise
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="answers")


class SpeechAnalysis(Base):
    """Result of one voice (or typed fallback) communication attempt (module 8)."""
    __tablename__ = "speech_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=True)
    question_text = Column(Text, default="")
    transcript = Column(Text, default="")
    input_mode = Column(String(20), default="voice")
    metrics = Column(JSON, default=dict)                      # pace/pauses/fillers/vocab/...
    scores = Column(JSON, default=dict)
    communication_score = Column(Integer, default=0)
    feedback = Column(JSON, default=dict)
    week_key = Column(String(10), default=_wk, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="speech_analyses")


class PlacementTask(Base):
    """One task of the personalized multi-week placement plan (module 10)."""
    __tablename__ = "placement_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    week_number = Column(Integer, default=1)
    focus = Column(String(120), default="")                   # e.g. "DSA + SQL"
    title = Column(String(200), nullable=False)
    detail = Column(Text, default="")
    category = Column(String(60), default="General")          # Technical|Testing|Projects|...
    status = Column(String(20), default="pending")            # pending | done | skipped
    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="placement_tasks")
