"""User & profile routes — view/update profile, completion %, onboarding."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models import Profile, User
from app.schemas import ProfileCompletion, ProfileIn, UserOut
from app.services.ai_service import canonical_skill

router = APIRouter(prefix="/api/users", tags=["users"])

# fields tracked for profile completion
COMPLETION_FIELDS = [
    "name", "phone", "college", "degree", "department", "year_of_study",
    "cgpa", "skills", "preferred_career", "experience_level",
]


def _profile_dict(user: User) -> dict:
    p = user.profile
    if p is None:
        p = Profile(user_id=user.id, skills=[], interests=[])
        user.profile = p
    return {
        "name": user.name or "",
        "email": user.email,
        "phone": p.phone or "",
        "college": p.college or "",
        "degree": p.degree or "",
        "department": p.department or "",
        "year_of_study": p.year_of_study or "",
        "cgpa": p.cgpa,
        "skills": p.skills or [],
        "preferred_career": p.preferred_career or "",
        "experience_level": p.experience_level or "Beginner",
        "interests": p.interests or [],
        "daily_study_minutes": p.daily_study_minutes or 60,
    }


def build_user_out(user: User) -> UserOut:
    """UserOut with the profile serialized as a plain dict."""
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name or "",
        onboarded=bool(user.onboarded),
        profile=_profile_dict(user),
    )


def completion_info(user: User) -> ProfileCompletion:
    p = _profile_dict(user)
    filled = 0
    next_missing = None
    for f in COMPLETION_FIELDS:
        v = p.get(f)
        ok = v not in (None, "", []) and v is not False
        if ok:
            filled += 1
        elif next_missing is None:
            next_missing = f
    pct = round(filled / len(COMPLETION_FIELDS) * 100)
    return ProfileCompletion(completion=pct, next_missing_field=next_missing)


@router.get("/me", response_model=UserOut)
def me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    return build_user_out(user)
@router.get("/me/completion", response_model=ProfileCompletion)
def get_completion(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    return completion_info(user)


@router.put("/me", response_model=UserOut)
def update_me(payload: ProfileIn, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    p = user.profile or Profile(user_id=user.id, skills=[], interests=[])

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        user.name = str(data.pop("name")).strip()
    if "cgpa" in data and data["cgpa"] is not None:
        cgpa = float(data.pop("cgpa"))
        if not 0 <= cgpa <= 10:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "CGPA should be between 0 and 10.")
        p.cgpa = cgpa
    if "skills" in data and data["skills"] is not None:
        cleaned, seen = [], set()
        for s in data.pop("skills"):
            c = canonical_skill(str(s))
            if c and c.lower() not in seen and len(c) <= 40:
                seen.add(c.lower())
                cleaned.append(c)
        p.skills = cleaned[:25]
    if "interests" in data and data["interests"] is not None:
        p.interests = [str(i).strip()[:60] for i in data.pop("interests") if str(i).strip()][:15]
    if "experience_level" in data and data["experience_level"] is not None:
        if data["experience_level"] not in ("Beginner", "Intermediate", "Advanced"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Experience level must be Beginner, Intermediate or Advanced.")
    if "daily_study_minutes" in data and data["daily_study_minutes"] is not None:
        minutes = int(data.pop("daily_study_minutes"))
        if not 15 <= minutes <= 480:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Daily study time must be between 15 and 480 minutes.")
        p.daily_study_minutes = minutes

    for key, value in data.items():
        if value is None:
            continue
        if hasattr(p, key):
            setattr(p, key, str(value).strip()[:200] if isinstance(value, str) else value)

    if p.id is None:
        db.add(p)
    user.onboarded = True
    db.commit()
    db.refresh(user)

    out = build_user_out(user)
    return out
