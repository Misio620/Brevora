from pydantic_settings import BaseSettings
from functools import lru_cache

from cryptography.fernet import Fernet

# The old default, published in this repo; a server signing JWTs with it lets anyone forge logins
_PUBLIC_JWT_SECRETS = {"", "change-me-in-production"}
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/youtube_reader"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Google Gemini API
    GOOGLE_API_KEY: str = ""
    # Gemini retires model versions; keep names configurable instead of hardcoded
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash"

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24 * 7  # 7 days

    # Encryption for stored OAuth tokens
    ENCRYPTION_KEY: str = ""

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def secret_problems(settings: Settings) -> list[str]:
    """Lists secret settings the API server must not start with."""
    problems = []
    if settings.JWT_SECRET in _PUBLIC_JWT_SECRETS or len(settings.JWT_SECRET) < MIN_JWT_SECRET_LENGTH:
        problems.append(
            f"JWT_SECRET must be a random string of at least {MIN_JWT_SECRET_LENGTH} characters "
            '(python -c "import secrets; print(secrets.token_hex(32))")'
        )
    try:
        Fernet(settings.ENCRYPTION_KEY.encode())
    except ValueError:
        problems.append(
            "ENCRYPTION_KEY must be a valid Fernet key "
            '(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")'
        )
    return problems
