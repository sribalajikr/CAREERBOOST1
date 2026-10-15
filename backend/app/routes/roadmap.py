"""Roadmap routes — generate phases, track per-user task completion."""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import RoadmapProgress, User
from app.schemas import RoadmapLevel, RoadmapLevelsResponse, RoadmapPhase, RoadmapResponse, RoadmapTask
from app.services.roadmap_data import ROADMAPS, extra_levels_for, roadmap_task_totals

router = APIRouter(prefix="/api/roadmap", tags=["roadmap"])


def _phase_task_id(phase_index: int, task_index: int) -> str:
    return f"p{phase_index}t{task_index}"


def _task_phase_index(task_id: str) -> int:
    """p10t2 -> 10 (works beyond single-digit phase indexes)."""
    return int(task_id[1:task_id.index("t")])


def _progress_rows(db: Session, user_id: int, career: str) -> set[str]:
    rows = (
        db.query(RoadmapProgress)
        .filter(RoadmapProgress.user_id == user_id, RoadmapProgress.career == career, RoadmapProgress.completed == True)  # noqa: E712
        .all()
    )
    return {r.task_id for r in rows}


def build_roadmap(db: Session, user_id: int, career: str) -> RoadmapResponse | None:
    template = ROADMAPS.get(career)
    if not template:
        return None
    done = _progress_rows(db, user_id, career)
    user = db.get(User, user_id)
    skills = (user.profile.skills if user and user.profile else None)

    phases_out: list[RoadmapPhase] = []
    completed = 0
    for i, phase in enumerate(template["phases"]):
        tasks = [
            RoadmapTask(id=_phase_task_id(i, j), title=t, done=(_phase_task_id(i, j) in done))
            for j, t in enumerate(phase["tasks"])
        ]
        c = sum(1 for t in tasks if t.done)
        completed += c
        phases_out.append(
            RoadmapPhase(
                index=i,
                title=phase["title"],
                goal=phase["goal"],
                beginner_note=phase["beginner_note"],
                topics=phase["topics"],
                resources=phase["resources"],
                practice=phase["practice"],
                mini_project=phase["mini_project"],
                tasks=tasks,
                completed_tasks=c,
                total_tasks=len(tasks),
                progress=round(c / len(tasks) * 100) if tasks else 0,
            )
        )
    # totals include the 4 finale levels so every module shows the same %
    extras = extra_levels_for(career, skills)
    valid_extra = {
        _phase_task_id(len(phases_out) + k, j)
        for k, lvl in enumerate(extras)
        for j in range(len(lvl["tasks"]))
    }
    completed += sum(1 for tid in done if tid in valid_extra)
    total = roadmap_task_totals(career, skills)
    return RoadmapResponse(
        career=career,
        phases=phases_out,
        overall_progress=round(completed / total * 100) if total else 0,
        completed_tasks=completed,
        total_tasks=total,
        estimated_weeks=template["estimated_weeks"],
    )


# ------------------------------------------------------------------ game-style levels

def _icon_hint(title: str, topics: list[str], index: int) -> str:
    text = (title + " " + " ".join(topics)).lower()
    rules = [
        (r"foundation|fundament|basics|intro", "foundation"),
        (r"exception|warning", "warning"),
        (r"thread|concurr", "threads"),
        (r"collection", "collections"),
        (r"ci.?cd|deploy|git|pipeline|docker|kubernetes|container", "devops"),
        (r"rest|\bapi\b|server|backend|endpoint", "api"),
        (r"database|\bsql\b|mongo|postgres", "database"),
        (r"\bhr\b|placement|resume|certification", "career"),
        (r"interview", "interview"),
        (r"project|portfolio|build", "project"),
        (r"coding|dsa|drill|practice|problem|leetcode", "practice"),
        (r"program", "code"),
        (r"selenium|automation|test", "testing"),
        (r"stat|visual|analy|pandas|excel|spreadsheet", "data"),
        (r"machine|deep|nlp|model|\bai\b|\bml\b", "ai"),
        (r"cloud|infra", "cloud"),
        (r"security|hack|defen", "security"),
        (r"oop|object|javascript|react|typescript|html|css|\bweb\b|styling?", "code"),
    ]
    for pattern, hint in rules:
        if re.search(pattern, text):
            return hint
    return "foundation" if index == 0 else "code"


def _level_defs(career: str, skills: list | None) -> list[dict]:
    """Level definitions = 7 phase levels + 4 career finale levels."""
    template = ROADMAPS[career]
    defs: list[dict] = []
    for i, phase in enumerate(template["phases"]):
        defs.append({
            "index": i,
            "title": phase["title"],
            "description": phase["goal"],
            "topics": phase["topics"],
            "tasks": phase["tasks"],
            "resources": phase["resources"],
            "note": phase["beginner_note"],
            "practice": phase["practice"],
            "mini_project": phase["mini_project"],
        })
    # finale levels reuse the career's own learning resources (nothing removed)
    all_resources: list[dict] = []
    seen_urls: set[str] = set()
    for phase in template["phases"]:
        for r in phase["resources"]:
            key = r.get("url") or r.get("name", "")
            if key not in seen_urls:
                seen_urls.add(key)
                all_resources.append(r)
    extras = extra_levels_for(career, skills)
    for k, lvl in enumerate(extras):
        n = len(all_resources)
        picked = [all_resources[(k * 3 + i) % n] for i in range(3)] if n else []
        defs.append({
            "index": len(template["phases"]) + k,
            "title": lvl["title"],
            "description": lvl["goal"],
            "topics": lvl["topics"],
            "tasks": lvl["tasks"],
            "resources": picked,
            "note": lvl.get("note", ""),
            "practice": [],
            "mini_project": "",
        })
    return defs


def build_levels(db: Session, user_id: int, career: str) -> RoadmapLevelsResponse | None:
    template = ROADMAPS.get(career)
    if not template:
        return None
    user = db.get(User, user_id)
    profile = user.profile if user else None
    skills = profile.skills if profile else None
    experience = (profile.experience_level if profile else None) or "Beginner"

    done = _progress_rows(db, user_id, career)
    defs = _level_defs(career, skills)

    # ---- per-level stats + game states (all from THIS user's DB rows)
    stats = []
    for d in defs:
        tasks = [
            RoadmapTask(id=_phase_task_id(d["index"], j), title=t, done=(_phase_task_id(d["index"], j) in done))
            for j, t in enumerate(d["tasks"])
        ]
        c = sum(1 for t in tasks if t.done)
        stats.append({"tasks": tasks, "completed": c, "total": len(tasks),
                      "progress": round(c / len(tasks) * 100) if tasks else 0})

    completed_levels = sum(1 for s in stats if s["total"] and s["completed"] == s["total"])
    first_incomplete = next((i for i, s in enumerate(stats) if not (s["total"] and s["completed"] == s["total"])), None)

    factor = {"Beginner": 1.0, "Intermediate": 0.9, "Advanced": 0.8}.get(experience, 1.0)

    levels: list[RoadmapLevel] = []
    for d, s in zip(defs, stats):
        i = d["index"]
        is_done = s["total"] > 0 and s["completed"] == s["total"]
        if is_done:
            state = "completed"
        elif first_incomplete is None:
            state = "completed"
        elif i == first_incomplete:
            state = "current"
        elif i == first_incomplete + 1:
            state = "unlocked"          # the "next level" — available to start
        else:
            state = "locked"

        # personalisation (deterministic): highlight topics none of the user's skills touch
        gap_topics = [
            t for t in d["topics"]
            if not any(s and s.lower() in t.lower() for s in (skills or []))
        ][:2]
        description = d["description"]
        if gap_topics and state != "completed":
            description += " Focus area for you: " + ", ".join(gap_topics) + "."

        est = max(40, round((len(d["tasks"]) * 45 + i * 10) * factor / 10) * 10)

        levels.append(RoadmapLevel(
            index=i,
            number=f"{i + 1:02d}",
            title=d["title"],
            description=description,
            state=state,
            progress=s["progress"],
            completed_tasks=s["completed"],
            total_tasks=s["total"],
            est_minutes=est,
            topics=d["topics"],
            icon=_icon_hint(d["title"], d["topics"], i),
            tasks=s["tasks"],
            resources=d["resources"],
            note=d["note"],
            practice=d["practice"],
            mini_project=d["mini_project"],
        ))

    total = sum(s["total"] for s in stats)
    completed = sum(s["completed"] for s in stats)
    return RoadmapLevelsResponse(
        career=career,
        summary=template.get("summary", ""),
        estimated_weeks=template.get("estimated_weeks", 7),
        levels=levels,
        overall_progress=round(completed / total * 100) if total else 0,
        completed_tasks=completed,
        total_tasks=total,
        completed_levels=completed_levels,
        current_level=first_incomplete,
    )




@router.get("/careers", response_model=list[str])
def available_careers():
    return list(ROADMAPS.keys())


# registered BEFORE get_roadmap so "/{career:path}" doesn't swallow "/…/levels"
@router.get("/{career:path}/levels", response_model=RoadmapLevelsResponse)
def get_levels(career: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    levels = build_levels(db, user_id, career)
    if levels is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No roadmap found for '{career}'. Pick one from the Careers page.")
    return levels


# ":path" lets career names that contain a slash ("AI/ML Engineer",
# "QA / Automation Engineer") survive URL routing — encodeURIComponent turns
# the slash into %2F, which decodes back to "/" before route matching.
@router.get("/{career:path}", response_model=RoadmapResponse)
def get_roadmap(career: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rm = build_roadmap(db, user_id, career)
    if rm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No roadmap found for '{career}'. Pick one from the Careers page.")
    return rm


@router.post("/{career:path}/tasks/{task_id}", response_model=RoadmapResponse)
def toggle_task(
    career: str,
    task_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    template = ROADMAPS.get(career)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No roadmap found for '{career}'.")

    user = db.get(User, user_id)
    skills = user.profile.skills if user and user.profile else None
    valid_ids = {
        _phase_task_id(d["index"], j)
        for d in _level_defs(career, skills)
        for j in range(len(d["tasks"]))
    }
    if task_id not in valid_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown task.")

    row = (
        db.query(RoadmapProgress)
        .filter(
            RoadmapProgress.user_id == user_id,
            RoadmapProgress.career == career,
            RoadmapProgress.task_id == task_id,
        )
        .first()
    )
    if row:
        row.completed = not row.completed
        was_completed = row.completed
    else:
        db.add(RoadmapProgress(user_id=user_id, career=career, phase_index=_task_phase_index(task_id), task_id=task_id, completed=True))
        was_completed = True
    db.commit()
    return build_roadmap(db, user_id, career)


@router.delete("/{career:path}", status_code=200)
def reset_roadmap(career: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.query(RoadmapProgress).filter(
        RoadmapProgress.user_id == user_id, RoadmapProgress.career == career
    ).delete()
    db.commit()
    return {"detail": f"Roadmap progress for {career} has been reset."}
