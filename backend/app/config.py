"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # --- App ---
    APP_NAME: str = "PlayShield AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000"
    ALLOWED_ORIGINS: str = ""  # For production domain mappings

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://ipguardian:changeme_db_password@db:5432/ipguardian"

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- JWT ---
    JWT_SECRET_KEY: str = "changeme_jwt_secret_at_least_32_chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Google Cloud ---
    GCP_PROJECT_ID: str = "your-gcp-project-id"
    GCS_BUCKET_NAME: str = "ipguardian-media"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # --- Vertex AI (Gemini) ---
    VERTEX_AI_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- Email (SMTP) ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@playshield.ai"

    # --- Alerts ---
    SLACK_WEBHOOK_URL: str = ""
    ALERT_EMAIL_TO: str = "admin@playshield.ai"

    # --- Crawler ---
    CRAWLER_CONCURRENCY: int = 2
    CRAWLER_RATE_LIMIT_SECONDS: int = 3
    CRAWLER_RESPECT_ROBOTS: bool = True

    # --- Matching ---
    CONFIDENCE_THRESHOLD: float = 0.75
    WEIGHT_HASH: float = 0.4
    WEIGHT_EMBED: float = 0.4
    WEIGHT_RISK: float = 0.2

    # --- Paths ---
    MEDIA_DIR: str = "/app/media"
    FAISS_INDEX_DIR: str = "/app/faiss_index"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
