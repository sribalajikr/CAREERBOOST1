"""JWT helpers and password hashing."""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def validate_password_strength(password: str) -> None:
    """Raise 400 unless the password meets the policy:
    at least 8 chars, 1 uppercase letter and 1 special character."""
    problems = []
    if len(password or "") < 8:
        problems.append("at least 8 characters")
    if not re.search(r"[A-Z]", password or ""):
        problems.append("one uppercase letter (A-Z)")
    if not re.search(r"[^A-Za-z0-9]", password or ""):
        problems.append("one special character (e.g. @ # $ % !)")
    if problems:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Password must contain " + ", ".join(problems) + ".",
        )



def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication token.")


async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> int:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload.")
    return int(sub)
