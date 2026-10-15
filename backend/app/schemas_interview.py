"""Pydantic schemas for modules 6-10 (interviews, speech, analytics, placement)."""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------- Module 6: technical prep ----------
class PrepQuestion(BaseModel):
    id: str
    category: str
    topic: str
    difficulty: str
    question: str
    concepts: List[str]
    hint: Optional[str] = None


class PrepQuestionOut(PrepQuestion):
    explanation: Optional[str] = None


class PrepAnswerIn(BaseModel):
    answer: str = Field(max_length=6000)


class PrepFeedback(BaseModel):
    explanation: str
    strengths: List[str]
    improvements: List[str]
    revise: str
    verdict: str


class PrepAnswerOut(BaseModel):
    scores: Dict[str, int]
    overall: int
    feedback: PrepFeedback


class PrepHistoryItem(BaseModel):
    topic: str
    category: str
    difficulty: str
    overall: int
    answered_at: str


class PrepHistoryOut(BaseModel):
    items: List[PrepHistoryItem]
    answered_ids: List[str]
    avg_score: int


class PrepStats(BaseModel):
    attempted: int
    avg_score: int
    topics_covered: int
    categories: List[str]


# ---------- Module 7: mock interview ----------
class InterviewStartIn(BaseModel):
    session_type: str = Field(pattern="^(quick|technical|hr|mixed|role)$")
    career: Optional[str] = None
    difficulty: str = Field(pattern="^(Beginner|Intermediate|Advanced)$")
    duration_minutes: int = Field(default=15, ge=5, le=60)


class InterviewQuestionOut(BaseModel):
    session_id: int
    question_number: int
    planned_total: int
    question: PrepQuestion
    transition: str = ""


class InterviewAnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
    input_mode: str = Field(default="text", pattern="^(text|voice)$")
    duration_seconds: Optional[float] = None


class InterviewAnswerOut(BaseModel):
    answer_id: int
    scores: Dict[str, int]
    overall: int
    feedback: PrepFeedback
    next_question: Optional[InterviewQuestionOut] = None


class InterviewReport(BaseModel):
    session_id: int
    session_type: str
    career: str
    difficulty: str
    questions_answered: int
    overall_score: int
    breakdown: Dict[str, int]
    summary: str
    strong_topics: List[str]
    weak_topics: List[str]
    suggestions: List[str]
    created_at: str


# ---------- Module 8: speech ----------
class SpeechAnalyzeIn(BaseModel):
    question_text: str = Field(min_length=1, max_length=2000)
    question_id: Optional[str] = None
    transcript: str = Field(min_length=1, max_length=8000)
    duration_seconds: Optional[float] = None
    input_mode: str = Field(default="voice", pattern="^(voice|text)$")
    career: Optional[str] = None


class SpeechAnalysisOut(BaseModel):
    metrics: Dict[str, object]
    scores: Dict[str, int]
    communication_score: int
    feedback: Dict[str, object]
    analysis_id: Optional[int] = None


class SpeechHistoryOut(BaseModel):
    attempts: List[dict]
    avg_communication: int


class TranscribeOut(BaseModel):
    text: str
    engine: str
    duration_seconds: float = 0.0


# ---------- Module 9: analytics ----------
class TopicScore(BaseModel):
    topic: str
    avg: int
    attempts: int


class AnalyticsResponse(BaseModel):
    has_data: bool
    attempts: int = 0
    sessions_completed: int = 0
    questions_answered: int = 0
    avg_overall: int = 0
    avg_technical: int = 0
    avg_communication: int = 0
    trend: List[dict] = []            # [{label, score}] chronological session scores
    weekly: List[dict] = []           # [{week, avg}] last 8 weeks
    strong_topics: List[TopicScore] = []
    weak_topics: List[TopicScore] = []
    roadmap_progress: int = 0
    planner_completed: int = 0
    speech_attempts: int = 0
    speech_avg: int = 0


class ProgressOut(BaseModel):
    """Single source of truth for every displayed module percentage."""
    has_data: bool
    modules: Dict[str, int] = Field(default_factory=dict)
    activity: Dict[str, int] = Field(default_factory=dict)


# ---------- Module 10: placement ----------
class ReadinessArea(BaseModel):
    label: str
    percent: int
    detail: str


class PlacementResponse(BaseModel):
    has_data: bool
    overall: int = 0
    areas: List[ReadinessArea] = []
    summary: str = ""
    ready_areas: List[str] = []
    improve_areas: List[str] = []
    next_steps: List[str] = []
    this_week: List[dict] = []


class PlacementTaskOut(BaseModel):
    id: int
    taskId: str = ""                      # stable unique id for the task
    week_number: int
    focus: str
    title: str
    detail: str
    category: str = "General"
    status: str
    completed: bool = False


class PlacementPlanOut(BaseModel):
    weeks: List[dict] = []
    progress: int = 0
    completed: int = 0
    total: int = 0


class PlacementTaskActionIn(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(pending|done|skipped)$")


class PlacementGenerateOut(BaseModel):
    detail: str
    plan: PlacementPlanOut
