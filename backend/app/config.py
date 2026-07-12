"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app config is loaded from a `.env` file or real env vars."""

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Default to the documented local PostgreSQL database for development.
    DATABASE_URL: str = "postgresql://postgres:Binbud123%23@localhost:5433/trello_clone"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
