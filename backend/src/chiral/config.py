"""Settings, read from environment variables and the `.env` file at the repo root."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/chiral/config.py -> parents[3] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_ignore_empty=True,  # `ANTHROPIC_API_KEY=` in .env means "not set"
        extra="ignore",
    )

    # Defaults match docker-compose.yml, so local development needs no .env.
    database_url: str = "postgresql://chiral:chiral@localhost:5432/chiral"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-opus-5-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
