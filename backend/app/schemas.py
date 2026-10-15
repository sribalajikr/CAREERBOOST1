"""Pydantic schemas shared across the API."""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class SignUpRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(min_length=8, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ---------- Profile ----------
class ProfileIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    college: Optional[str] = None
    degree: Optional[str] = None
    department: Optional[str] = None
    year_of_study: Optional[str] = None
    cgpa: Optional[float] = None
    skills: Optional[List[str]] = None
    preferred_career: Optional[str] = None
    experience_level: Optional[str] = None
    interests: Optional[List[str]] = None
    daily_study_minutes: Optional[int] = None


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    onboarded: bool
    profile: Optional[dict] = None

    model_config = {"from_attributes": True}


class ProfileCompletion(BaseModel):
    completion: int
    next_missing_field: Optional[str] = None


# ---------- Resume ----------
class ResumeOut(BaseModel):
    id: int
    file_name: str
    score: int
    analysis: dict
    created_at: str
    is_latest: bool


class ResumeAnalysisOut(BaseModel):
    score: int
    grade_label: str
    summary: str
    skills: List[str]
    strengths: List[str]
    improvements: List[str]
    sections: dict
    keyword_coverage: dict
    job_readiness: int
    formatting: List[dict]
    missing_sections: List[str]


# ---------- Career ----------
class CareerMatch(BaseModel):
    career: str
    description: str
    match_percent: int
    level: str
    required_skills: List[str]
    user_skills: List[str]
    missing_skills: List[str]
    why: List[str]
    learning_path: List[str]
    salary_hint: str


class CareerResponse(BaseModel):
    recommendations: List[CareerMatch]


# ---------- Roadmap ----------
class RoadmapTask(BaseModel):
    id: str
    title: str
    done: bool = False


class RoadmapPhase(BaseModel):
    index: int
    title: str
    goal: str
    beginner_note: str
    topics: List[str]
    resources: List[dict]
    practice: List[str]
    mini_project: str
    tasks: List[RoadmapTask]
    completed_tasks: int = 0
    total_tasks: int = 0
    progress: int = 0


class RoadmapResponse(BaseModel):
    career: str
    phases: List[RoadmapPhase]
    overall_progress: int
    completed_tasks: int
    total_tasks: int
    estimated_weeks: int


class RoadmapLevel(BaseModel):
    """One game-style level (7 phase levels + 4 career finale levels)."""
    index: int
    number: str                       # "01"
    title: str
    description: str
    state: str                        # completed | current | unlocked | locked
    progress: int
    completed_tasks: int
    total_tasks: int
    est_minutes: int
    topics: List[str]
    icon: str                         # icon hint for the frontend
    tasks: List[RoadmapTask]
    resources: List[dict]
    note: str = ""
    practice: List[str] = []
    mini_project: str = ""


class RoadmapLevelsResponse(BaseModel):
    career: str
    summary: str = ""
    estimated_weeks: int = 7
    levels: List[RoadmapLevel]
    overall_progress: int
    completed_tasks: int
    total_tasks: int
    completed_levels: int
    current_level: Optional[int] = None   # 0-based index of the active level


# ---------- Planner ----------
class PlanTaskOut(BaseModel):
    id: int
    title: str
    category: str
    duration_minutes: int
    status: str
    task_date: str


class PlanResponse(BaseModel):
    date: str
    tasks: List[PlanTaskOut]
    completed: int
    total: int
    progress: int


class WeeklyPlanResponse(BaseModel):
    week_start: str
    days: List[dict]
    overall_progress: int


class StudyTimeIn(BaseModel):
    minutes_per_day: int = Field(ge=15, le=480)


# ---------- Dashboard ----------
class DashboardResponse(BaseModel):
    name: str
    completion: int
    resume_score: Optional[int] = None
    resume_file: Optional[str] = None
    career_match: Optional[int] = None
    recommended_career: Optional[str] = None
    roadmap_progress: Optional[int] = None
    roadmap_career: Optional[str] = None
    roadmap_completed: int = 0
    roadmap_total: int = 0
    today_progress: int = 0
    today_done: int = 0
    today_total: int = 0
    upcoming: List[PlanTaskOut] = []
    message: str


TokenResponse.model_rebuild()
