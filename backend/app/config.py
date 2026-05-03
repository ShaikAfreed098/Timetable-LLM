from pydantic_settings import BaseSettings
from typing import Optional
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Timetable LLM"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production
    AUDIT_LOG_RETENTION_DAYS: int = 365
    SENTRY_DSN: Optional[str] = None
    MAX_FACULTY_PERIODS_PER_WEEK: int = 18

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Bootstrap
    BOOTSTRAP_TOKEN: Optional[str] = None

    # Firebase
    FIREBASE_PROJECT_ID: str = "timetable-lm"

    # Database
    DATABASE_URL: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_SSL_MODE: Optional[str] = None  # e.g. "require" in production

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM — explicit provider selection, no key-prefix sniffing
    LLM_PROVIDER: str = "openai"  # openai | nvidia | anthropic | openrouter
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.0

    # Legacy aliases — kept so existing .env files continue to work.
    # Prefer LLM_API_KEY going forward.
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    # SMTP (for invite emails)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_HOST and self.DB_NAME and self.DB_USER:
            password = quote_plus(self.DB_PASSWORD or "")
            url = (
                f"postgresql+psycopg2://{self.DB_USER}:{password}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
            if self.DB_SSL_MODE:
                url += f"?sslmode={self.DB_SSL_MODE}"
            return url
        raise ValueError("DATABASE_URL must be configured.")

    def resolved_llm_api_key(self) -> Optional[str]:
        return self.LLM_API_KEY or self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY

    def resolved_llm_base_url(self) -> Optional[str]:
        if self.LLM_BASE_URL:
            return self.LLM_BASE_URL
        if self.LLM_PROVIDER == "nvidia":
            return "https://integrate.api.nvidia.com/v1"
        return None

    def validate_for_production(self) -> list[str]:
        """Return a list of misconfiguration errors. Empty list = OK."""
        errors: list[str] = []
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                errors.append("DEBUG must be False in production.")
            if self.JWT_SECRET == "change-me-in-production" or len(self.JWT_SECRET) < 32:
                errors.append("JWT_SECRET must be set to a value with at least 32 characters.")
            if not self.resolved_llm_api_key():
                errors.append("LLM_API_KEY must be set.")
            if not self.DATABASE_URL and not (self.DB_HOST and self.DB_NAME and self.DB_USER):
                errors.append("Database connection is not configured.")
            if "*" in self.ALLOWED_ORIGINS or not self.ALLOWED_ORIGINS.startswith("http"):
                errors.append("ALLOWED_ORIGINS must list explicit HTTPS origins in production.")
        return errors

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
