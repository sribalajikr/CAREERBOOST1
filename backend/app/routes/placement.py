"""Routes for Module 10 (placement readiness + personalized plan).

The readiness percentage is a PREPARATION PROGRESS indicator only — it never
claims anything about actual job-selection probability.
"""
import datetime as dt
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import PlacementTask, Resume, User
from app.schemas_interview import (
    PlacementGenerateOut,
    PlacementPlanOut,
    PlacementResponse,
    PlacementTaskActionIn,
    PlacementTaskOut,
    ReadinessArea,
)
from app.routes.analytics import collect_stats
from app.services.ai_service import get_ai_service
from app.services.roadmap_data import ROADMAPS

router = APIRouter(prefix="/api/placement", tags=["placement"])


@router.get("", response_model=PlacementResponse)
def readiness(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    profile = user.profile
    stats = collect_stats(db, user_id)

    latest = (
        db.query(Resume)
        .filter(Resume.user_id == user.id, Resume.is_latest == True)  # noqa: E712
        .order_by(Resume.created_at.desc())
        .first()
    )
    resume_score = latest.score if latest and latest.score > 0 else None

    # ---- career match
    career_match = None
    recommended = None
    if profile and (profile.skills or profile.preferred_career):
        recs = get_ai_service().recommend_careers({
            "skills": profile.skills or [],
            "interests": profile.interests or [],
            "degree": profile.degree or "",
            "department": profile.department or "",
            "preferred_career": profile.preferred_career or "",
            "experience_level": profile.experience_level or "Beginner",
            "cgpa": profile.cgpa,
        }, (latest.analysis.get("skills") if latest and isinstance(latest.analysis, dict) else None))
        if recs:
            recommended = recs[0]["career"]
            career_match = recs[0]["match_percent"]

    interview_pct = stats["avg_overall"]
    comm_pct = stats["speech_avg"] or stats["avg_communication"]

    has_any = any(v is not None for v in [resume_score, career_match]) or stats["questions_answered"] > 0
    if not has_any:
        return PlacementResponse(has_data=False)

    areas: List[ReadinessArea] = []
    if resume_score is not None:
        areas.append(ReadinessArea(label="Resume", percent=resume_score,
                                   detail=f"Latest resume: {latest.file_name}"))
    if career_match is not None:
        areas.append(ReadinessArea(label="Career Fit", percent=career_match,
                                   detail=f"Best match: {recommended}"))
    if stats["questions_answered"]:
        areas.append(ReadinessArea(label="Technical Preparation", percent=interview_pct,
                                   detail=f"{stats['questions_answered']} questions answered across {stats['attempts']} sessions"))
    if stats["speech_attempts"] or stats["avg_communication"]:
        areas.append(ReadinessArea(label="Communication", percent=comm_pct,
                                   detail=f"{stats['speech_attempts']} speech practice attempts"))
    if stats["roadmap_progress"]:
        areas.append(ReadinessArea(label="Roadmap Progress", percent=stats["roadmap_progress"],
                                   detail=f"{stats['planner_completed']} planner tasks completed"))
    sessions_done = len(stats["sessions_completed"])
    if sessions_done:
        areas.append(ReadinessArea(label="Interview Practice", percent=min(98, sessions_done * 20),
                                   detail=f"{sessions_done} mock interviews completed"))

    overall = round(sum(a.percent for a in areas) / len(areas)) if areas else 0

    # ---- summary (varied, evidence-based)
    strong_areas = [a.label for a in areas if a.percent >= 70]
    improve_areas = [a.label for a in areas if a.percent < 60]

    parts = []
    if strong_areas:
        parts.append(f"Your {' and '.join(strong_areas[:2])} {'is' if len(strong_areas) == 1 else 'are'} progressing well")
    if improve_areas:
        parts.append(f"{', '.join(improve_areas[:2])} still need{'s' if len(improve_areas) == 1 else ''} attention")
    if stats["weak_topics"]:
        parts.append(f"recent interviews suggest extra practice on {', '.join(t.topic for t in stats['weak_topics'][:2])}")

    if parts:
        summary = ". ".join(parts) + "."
    else:
        summary = "Every area is in a healthy range — keep practising to stay sharp."
    summary += f" Overall preparation stands at {overall}% — use it as a progress indicator, not a prediction of results."

    # ---- next steps, personalized from the weakest real data
    next_steps: List[str] = []
    if resume_score is not None and resume_score < 70:
        next_steps.append("Re-upload an improved resume after applying the analysis suggestions")
    if stats["questions_answered"] and stats["avg_overall"] < 65:
        wt = stats["weak_topics"][0].topic if stats["weak_topics"] else "core concepts"
        next_steps.append(f"Practise 10 {wt} questions in Technical Prep")
    if stats["speech_attempts"] < 3:
        next_steps.append("Record 2-3 voice answers in Speech Practice to build communication scores")
    if sessions_done < 3:
        next_steps.append("Complete at least one mock interview per week")
    if stats["roadmap_progress"] < 50:
        next_steps.append("Push your roadmap progress past 50% — tick off one phase task today")
    if not next_steps:
        next_steps.append("Increase interview difficulty to Advanced and keep the streak going")

    # ---- this week's focus (top 5 by weakest area)
    this_week = [{"text": s} for s in next_steps[:5]]

    return PlacementResponse(
        has_data=True, overall=overall, areas=areas, summary=summary,
        ready_areas=strong_areas, improve_areas=improve_areas,
        next_steps=next_steps, this_week=this_week,
    )


# ------------------------------------------------------------------ plan
# Role-specific 4-week plans: each task is [title, category].
# The plan is chosen from the user's PROFILE ROLE (and skills) — never one
# generic plan for everyone.
_PLANS: dict = {
    "Software Developer": [
        {"week": 1, "focus": "DSA + Core Languages", "tasks": [
            ["Solve 10 easy array & string problems", "Technical"],
            ["Revise SQL joins — write 10 queries", "Technical"],
            ["Learn hash maps & sets — 5 problems", "Technical"],
            ["One timed 45-min mock problem set", "Interview Practice"],
        ]},
        {"week": 2, "focus": "Projects + GitHub", "tasks": [
            ["Polish resume project descriptions with measurable results", "Projects"],
            ["Push all projects to GitHub with clean READMEs", "Projects"],
            ["Add one new feature to your strongest project", "Projects"],
            ["Prepare a 90-second project walkthrough", "Communication"],
        ]},
        {"week": 3, "focus": "Technical Interviews", "tasks": [
            ["Complete 2 Technical Prep sessions on weak topics", "Interview Practice"],
            ["Revise OS + Networks fundamentals (2 topics each)", "Technical"],
            ["Practise explaining OOP with project examples", "Communication"],
            ["One full mock interview — Technical", "Interview Practice"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Mixed mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish + upload for a fresh score", "Career Prep"],
        ]},
    ],
    "QA / Automation Engineer": [
        {"week": 1, "focus": "Testing Fundamentals + SQL", "tasks": [
            ["Write test cases for a login & signup feature (happy + negative paths)", "Testing"],
            ["Revise bug lifecycle, severity vs priority, smoke vs sanity vs regression", "Testing"],
            ["Practise boundary value & equivalence partitioning on 3 form fields", "Testing"],
            ["Write 5 SQL queries to verify data (joins, duplicates, counts)", "Technical"],
        ]},
        {"week": 2, "focus": "Automation with Selenium", "tasks": [
            ["Set up a small Selenium/Playwright project and automate one login flow", "Testing"],
            ["Practise implicit vs explicit waits — fix one flaky element interaction", "Testing"],
            ["Write 5 API tests with Postman (status codes, schema, auth)", "Testing"],
            ["Add assertions and reporting to your automation scripts", "Tools"],
        ]},
        {"week": 3, "focus": "Applied Testing", "tasks": [
            ["Test a live site end-to-end and log 10 structured bug reports", "Testing"],
            ["Complete 2 Technical Prep sessions on testing & SQL topics", "Interview Practice"],
            ["Explore one test-management or bug-tracking tool (Jira/TestRail)", "Tools"],
            ["Write a mini test plan: scope, approach, entry/exit criteria", "Testing"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One QA-focused mock interview (testing + bug lifecycle questions)", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish highlighting testing tools + upload for a score", "Career Prep"],
        ]},
    ],
    "Java Developer": [
        {"week": 1, "focus": "Java Core + DSA", "tasks": [
            ["Revise Java fundamentals: JVM, String immutability, equals/hashCode", "Technical"],
            ["Solve 10 problems using ArrayList, HashMap and HashSet", "Technical"],
            ["Write 5 SQL joins on a practice database", "Technical"],
            ["Implement one sorting algorithm from scratch in Java", "Technical"],
        ]},
        {"week": 2, "focus": "OOP, Exceptions + Collections", "tasks": [
            ["Explain the 4 OOP pillars with Java code examples you write yourself", "Technical"],
            ["Build a mini CRUD console app with checked/unchecked exception handling", "Projects"],
            ["Practise try-with-resources and custom exceptions", "Technical"],
            ["Push all Java practice code to GitHub with clean READMEs", "Projects"],
        ]},
        {"week": 3, "focus": "Multithreading + Spring + REST", "tasks": [
            ["Build a small Spring Boot REST API (controller-service-repository)", "Projects"],
            ["Practise threads & synchronization with a producer-consumer example", "Technical"],
            ["Complete 2 Technical Prep sessions on Java & SQL topics", "Interview Practice"],
            ["Explain dependency injection and write one unit test with mocks", "Technical"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Java-focused mock interview (OOP, collections, multithreading)", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish highlighting Java/Spring projects + fresh score", "Career Prep"],
        ]},
    ],
    "Data Analyst": [
        {"week": 1, "focus": "SQL + Excel", "tasks": [
            ["Write 10 SQL queries: GROUP BY, HAVING, joins, subqueries", "Technical"],
            ["Build 2 Excel pivot tables and one chart from a public dataset", "Technical"],
            ["Practise VLOOKUP / INDEX-MATCH / XLOOKUP on sample data", "Technical"],
            ["Clean a messy dataset: duplicates, missing values, formats", "Technical"],
        ]},
        {"week": 2, "focus": "Python + Statistics", "tasks": [
            ["Load a CSV in pandas and produce 5 summary statistics", "Technical"],
            ["Revise mean/median, correlation, p-values with one worked example", "Technical"],
            ["Make 3 visualizations in matplotlib and pick the right chart type", "Technical"],
            ["Write a 5-bullet insight summary of one dataset", "Communication"],
        ]},
        {"week": 3, "focus": "Analysis + Storytelling", "tasks": [
            ["Complete a small end-to-end case study: question → data → insight", "Projects"],
            ["Complete 2 Technical Prep sessions on SQL & analytics topics", "Interview Practice"],
            ["Build one dashboard (Excel/Power BI/Tableau Public)", "Projects"],
            ["Practise explaining a chart's story in 60 seconds", "Communication"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Data Analyst mock interview (SQL + case questions)", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with project metrics + fresh score", "Career Prep"],
        ]},
    ],
    "Data Scientist": [
        {"week": 1, "focus": "Python + Statistics", "tasks": [
            ["Revise distributions, hypothesis testing and p-values with examples", "Technical"],
            ["Solve 10 pandas exercises: grouping, merging, pivoting", "Technical"],
            ["Write 5 SQL analytical queries (window functions if ready)", "Technical"],
            ["Complete one exploratory data analysis notebook", "Projects"],
        ]},
        {"week": 2, "focus": "Machine Learning Basics", "tasks": [
            ["Train one regression and one classification model with scikit-learn", "Technical"],
            ["Explain overfitting, train/test split and cross-validation in your words", "Technical"],
            ["Practise precision/recall trade-offs on an imbalanced dataset", "Technical"],
            ["Document feature engineering choices in a notebook", "Projects"],
        ]},
        {"week": 3, "focus": "Projects + Storytelling", "tasks": [
            ["Complete 2 Technical Prep sessions on ML & statistics topics", "Interview Practice"],
            ["Build one end-to-end mini project: data → model → metrics → summary", "Projects"],
            ["Create 3 visualizations that each carry one clear message", "Communication"],
            ["Write a project README a non-expert can follow", "Communication"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Data Science mock interview (ML + case questions)", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with model metrics + fresh score", "Career Prep"],
        ]},
    ],
    "AI/ML Engineer": [
        {"week": 1, "focus": "ML Fundamentals + Python", "tasks": [
            ["Revise supervised vs unsupervised learning with 3 algorithm examples", "Technical"],
            ["Practise pandas + numpy on one public dataset", "Technical"],
            ["Explain bias-variance trade-off and regularization in your words", "Technical"],
            ["Set up a Python ML environment (venv, jupyter, sklearn)", "Tools"],
        ]},
        {"week": 2, "focus": "Models + Evaluation", "tasks": [
            ["Train and evaluate 2 models; record precision, recall, F1", "Technical"],
            ["Apply one feature-engineering technique and measure its impact", "Technical"],
            ["Read one LLM/RAG overview and summarise it in 5 bullets", "Technical"],
            ["Push an ML notebook to GitHub with clear results", "Projects"],
        ]},
        {"week": 3, "focus": "Projects + Interview Depth", "tasks": [
            ["Complete 2 Technical Prep sessions on ML topics", "Interview Practice"],
            ["Build one mini end-to-end ML project with a README", "Projects"],
            ["Explain one model decision to a friend in plain language", "Communication"],
            ["Explore one deployment option (Streamlit/FastAPI demo)", "Tools"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One AI/ML-focused mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with ML project metrics + fresh score", "Career Prep"],
        ]},
    ],
    "Cloud Engineer": [
        {"week": 1, "focus": "Cloud Fundamentals", "tasks": [
            ["Revise compute vs storage vs networking in your target cloud", "Technical"],
            ["Deploy a small app to a free-tier VM or PaaS", "Projects"],
            ["Explain object vs block storage with a real use case", "Technical"],
            ["Practise one Linux + networking drill (ports, SSH, DNS)", "Technical"],
        ]},
        {"week": 2, "focus": "Services + Cost Awareness", "tasks": [
            ["Set up object storage + CDN for static assets", "Projects"],
            ["Practise vertical vs horizontal scaling decisions on paper", "Technical"],
            ["Complete 2 Technical Prep sessions on cloud & backend topics", "Interview Practice"],
            ["Estimate a monthly bill for a sample architecture", "Career Prep"],
        ]},
        {"week": 3, "focus": "Reliability + Security", "tasks": [
            ["Configure monitoring/alerts on one deployed service", "Tools"],
            ["Practise IAM basics: least-privilege roles for one project", "Technical"],
            ["Write a one-page incident runbook for your demo app", "Communication"],
            ["Back up and restore one dataset end to end", "Projects"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Cloud-focused mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with deployed projects + fresh score", "Career Prep"],
        ]},
    ],
    "DevOps Engineer": [
        {"week": 1, "focus": "Linux + Git", "tasks": [
            ["Complete one Linux practice set (processes, permissions, logs)", "Technical"],
            ["Practise git branching: merge vs rebase on a scratch repo", "Tools"],
            ["Write 5 shell one-liners you actually understand", "Technical"],
            ["Explain CI/CD stages and draw one pipeline on paper", "Technical"],
        ]},
        {"week": 2, "focus": "Docker + CI/CD", "tasks": [
            ["Containerise one small app with a Dockerfile", "Projects"],
            ["Set up a CI pipeline that runs tests on push (GitHub Actions)", "Projects"],
            ["Explain images vs containers with your own example", "Technical"],
            ["Add one automated deployment step (staging)", "Tools"],
        ]},
        {"week": 3, "focus": "Monitoring + Reliability", "tasks": [
            ["Add logging + one alert to your pipeline", "Tools"],
            ["Complete 2 Technical Prep sessions on DevOps & backend topics", "Interview Practice"],
            ["Write a rollback plan for your demo deployment", "Communication"],
            ["Practise the four golden signals with a sample dashboard", "Technical"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One DevOps-focused mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with pipeline links + fresh score", "Career Prep"],
        ]},
    ],
    "Cybersecurity Analyst": [
        {"week": 1, "focus": "Security Fundamentals", "tasks": [
            ["Revise the CIA triad, authentication vs authorization, least privilege", "Technical"],
            ["Explain SQL injection + XSS with one prevention each", "Technical"],
            ["Practise password hashing concepts (bcrypt vs MD5) in a demo", "Technical"],
            ["Complete 2 Technical Prep sessions on security topics", "Interview Practice"],
        ]},
        {"week": 2, "focus": "Hands-on Practice", "tasks": [
            ["Complete one beginner CTF-style challenge (e.g. OverTheWire)", "Projects"],
            ["Audit a sample form for input-validation weaknesses", "Projects"],
            ["Set up 2FA and a password manager; write down the habit", "Tools"],
            ["Read one OWASP Top-10 item in depth and summarise it", "Technical"],
        ]},
        {"week": 3, "focus": "Defence + Response", "tasks": [
            ["Write an incident-response first-hour checklist", "Communication"],
            ["Practise reading server logs to spot suspicious patterns", "Technical"],
            ["Explain encryption in transit vs at rest with real examples", "Technical"],
            ["Review OWASP prevention for one vulnerability in your stack", "Technical"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Cybersecurity-focused mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with labs/CTFs listed + fresh score", "Career Prep"],
        ]},
    ],
    "Frontend Developer": [
        {"week": 1, "focus": "HTML/CSS/JS + Git", "tasks": [
            ["Build one responsive page with flexbox/grid (mobile-first)", "Projects"],
            ["Revise JS array methods and DOM events with 5 exercises", "Technical"],
            ["Fix 5 accessibility issues in one of your pages (labels, focus, contrast)", "Technical"],
            ["Push everything to GitHub with a README", "Projects"],
        ]},
        {"week": 2, "focus": "React + State", "tasks": [
            ["Build one small React app with useState + useEffect", "Projects"],
            ["Explain the virtual DOM, keys and prop-drilling in your words", "Technical"],
            ["Refactor one component to remove prop-drilling (context or lifting)", "Technical"],
            ["Complete 2 Technical Prep sessions on frontend topics", "Interview Practice"],
        ]},
        {"week": 3, "focus": "APIs + Polish", "tasks": [
            ["Fetch and display data from a public API with loading/error states", "Projects"],
            ["Practise explaining a REST API design out loud", "Communication"],
            ["Add one form with client-side validation", "Projects"],
            ["Lighthouse-audit one page and fix the top 3 issues", "Tools"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Frontend-focused mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish with live project links + fresh score", "Career Prep"],
        ]},
    ],
    "Full Stack Developer": [
        {"week": 1, "focus": "DSA + Web Basics", "tasks": [
            ["Solve 10 easy DSA problems (arrays, strings, hash maps)", "Technical"],
            ["Revise SQL joins + write 5 queries", "Technical"],
            ["Build one small page with a form and client validation", "Projects"],
            ["One timed 45-min problem set", "Interview Practice"],
        ]},
        {"week": 2, "focus": "Full-stack Project", "tasks": [
            ["Build one feature end-to-end: API + database + UI", "Projects"],
            ["Push all projects to GitHub with clean READMEs", "Projects"],
            ["Explain your project's architecture in 90 seconds", "Communication"],
            ["Practise explaining authentication flow with JWT", "Technical"],
        ]},
        {"week": 3, "focus": "Technical Interviews", "tasks": [
            ["Complete 2 Technical Prep sessions on weak topics", "Interview Practice"],
            ["Revise OS + Networks fundamentals (2 topics each)", "Technical"],
            ["Practise explaining OOP with project examples", "Communication"],
            ["One full mock interview — Technical", "Interview Practice"],
        ]},
        {"week": 4, "focus": "Mock Interviews + Communication", "tasks": [
            ["One Mixed mock interview", "Interview Practice"],
            ["3 voice answers in Speech Practice; review filler words", "Communication"],
            ["Prepare HR answers: intro, strengths, weakness, conflict", "Communication"],
            ["Final resume polish + upload for a fresh score", "Career Prep"],
        ]},
    ],
}

# careers the UI may not list but that should still map to a plan
_PLAN_ALIASES = {
    "Java Developer": "Java Developer",
    "Python Developer": "Software Developer",
    "Data Engineer": "Data Analyst",
    "QA Engineer": "QA / Automation Engineer",
}


def _plan_key_for(user: User) -> str:
    """Pick the plan template from the user's PROFILE ROLE and skills."""
    profile = user.profile
    career = (profile.preferred_career or "") if profile else ""
    skills_blob = " ".join(s.lower() for s in (profile.skills or [])) if profile else ""

    key = _PLAN_ALIASES.get(career, career)
    if key not in _PLANS:
        key = "Software Developer"

    # a developer role with Java/Spring skills gets the Java-specific plan
    import re as _re
    if key == "Software Developer" and _re.search(r"\bjava\b|spring", skills_blob):
        key = "Java Developer"
    return key



@router.get("/plan", response_model=PlacementPlanOut)
def get_plan(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = (
        db.query(PlacementTask)
        .filter(PlacementTask.user_id == user_id)
        .order_by(PlacementTask.week_number.asc(), PlacementTask.id.asc())
        .all()
    )
    weeks: dict = {}
    for r in rows:
        weeks.setdefault(r.week_number, {"week": r.week_number, "focus": r.focus, "tasks": []})
        weeks[r.week_number]["tasks"].append(PlacementTaskOut(
            id=r.id, taskId=f"pt_{r.id}", week_number=r.week_number, focus=r.focus,
            title=r.title, detail=r.detail, category=r.category or "General",
            status=r.status, completed=r.status == "done",
        ))
    total = len(rows)
    done = sum(1 for r in rows if r.status == "done")
    return PlacementPlanOut(
        weeks=[weeks[k] for k in sorted(weeks)],
        progress=round(done / total * 100) if total else 0,
        completed=done, total=total,
    )


@router.post("/plan/generate", response_model=PlacementGenerateOut)
def generate_plan(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    stats = collect_stats(db, user_id)

    # wipe the old plan (regeneration is intentional — completion state is per-user
    # and a regenerated plan starts fresh for THIS user only)
    db.query(PlacementTask).filter(PlacementTask.user_id == user_id).delete()

    plan_key = _plan_key_for(user)
    templates = _PLANS[plan_key]
    study = profile_daily_minutes(user)
    for tpl in templates:
        for title, category in tpl["tasks"]:
            db.add(PlacementTask(
                user_id=user_id, week_number=tpl["week"], focus=tpl["focus"],
                title=title, detail=f"Target: ~{max(20, study // 2)} min per session",
                category=category,
            ))
    db.commit()

    role = (user.profile.preferred_career if user.profile and user.profile.preferred_career else "your target role")
    note = f"Plan generated for your profile role: {role} — built from your skills, interview history and study time."
    if plan_key != "Software Developer":
        note = f"{plan_key} plan generated from your profile role — tasks are specific to that role's interviews."
    if stats["weak_topics"]:
        note += f" Week 1 leads with {stats['weak_topics'][0].topic} — your weakest topic right now."
    plan = get_plan(user_id=user_id, db=db)
    return PlacementGenerateOut(detail=note, plan=plan)


def profile_daily_minutes(user: User) -> int:
    return (user.profile.daily_study_minutes if user.profile else 60) or 60


@router.patch("/plan/tasks/{task_id}", response_model=PlacementPlanOut)
def update_task(
    task_id: int,
    payload: PlacementTaskActionIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    row = db.query(PlacementTask).filter(
        PlacementTask.id == task_id, PlacementTask.user_id == user_id
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan task not found.")
    if payload.status:
        row.status = payload.status
        db.commit()
    return get_plan(user_id=user_id, db=db)
