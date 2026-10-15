"""Authentication routes — sign up, login, logout, forgot/reset password."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, validate_password_strength, verify_password
from app.models import Profile, User
from app.routes.users import build_user_out
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignUpRequest,
    TokenResponse,
)
from app.services.email_service import send_reset_code

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignUpRequest, db: Session = Depends(get_db)):
    validate_password_strength(payload.password)
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Try logging in.")
    user = User(email=email, name=payload.name.strip(), hashed_password=hash_password(payload.password))
    user.profile = Profile(skills=[], interests=[], experience_level="Beginner")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=build_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user=build_user_out(user))


@router.post("/logout")
def logout():
    # With stateless JWTs the client simply discards the token.
    return {"detail": "Logged out. See you soon!"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    # The reset code exists ONLY in the user's inbox — it is never returned by
    # the API. Unknown emails get the same answer so the endpoint can't reveal
    # who signed up.
    result = {"detail": "If that email is registered, a reset code has been sent. Check your inbox.", "demo_mode": False}
    if user:
        code = f"{secrets.randbelow(900000) + 100000}"
        user.reset_code = hash_password(code)
        user.reset_code_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()
        if not send_reset_code(email, code):
            # SMTP failure: tell the user plainly instead of leaking the code.
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Could not send the reset email right now. Please try again in a minute.",
            )
    return result


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    validate_password_strength(payload.new_password)
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.reset_code or not user.reset_code_expires:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No password reset was requested for this email.")
    if datetime.now(timezone.utc) > user.reset_code_expires.replace(tzinfo=timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset code has expired. Request a new one.")
    if not verify_password(payload.code, user.reset_code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That reset code doesn't match. Check and try again.")
    user.hashed_password = hash_password(payload.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.commit()
    return {"detail": "Password updated! You can now log in with your new password."}
