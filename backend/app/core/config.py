"""Application settings loaded from environment variables (.env)."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "AI Interview Prep & Career Guidance"
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # one week
    ALGORITHM: str = "HS256"

    DATABASE_URL: str = "sqlite:///./career_assistant.db"

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    AI_PROVIDER: str = "mock"  # "mock" = rule-based engine, no API key needed
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Offline speech-to-text (Vosk). Empty/missing model -> typed-answer path only.
    VOSK_MODEL_PATH: str = "models/vosk-model-small-en-us-0.15"

    # Real email delivery for password reset (optional, free via Gmail app password).
    # When SMTP_HOST/SMTP_USER/SMTP_PASSWORD are all set, reset codes are EMAILED;
    # otherwise demo mode keeps working and shows the code on screen instead.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "CareerBoost <no-reply@careerboost.local>"

    SEED_DEMO: bool = True

    @property
    def origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
