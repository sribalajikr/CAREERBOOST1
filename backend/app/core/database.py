"""SQLAlchemy engine/session with automatic MySQL -> SQLite fallback."""
import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger("uvicorn.app")

_engine = None
_is_fallback = False


def _build_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def get_engine():
    global _engine, _is_fallback
    if _engine is not None:
        return _engine
    try:
        engine = _build_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _engine = engine
        logger.info("Database connected: %s", settings.DATABASE_URL.split("@")[-1])
    except Exception as exc:  # noqa: BLE001 - graceful fallback keeps demo working
        logger.warning("Primary database unreachable (%s) - falling back to SQLite.", exc)
        _is_fallback = True
        _engine = _build_engine("sqlite:///./career_assistant.db")
    return _engine


def is_fallback() -> bool:
    return _is_fallback


class Base(DeclarativeBase):
    pass


get_engine()

SessionLocal = sessionmaker(bind=_engine, autocommit=False, expire_on_commit=False)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
