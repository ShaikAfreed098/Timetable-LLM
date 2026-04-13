from pydantic_settings import BaseSettings
from typing import Optional
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Timetable LLM"
    DEBUG: bool = False

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database — can be set as a full URL or as individual components
    DATABASE_URL: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.0

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    def get_database_url(self) -> str:
        """
        Return the database URL, building it safely from individual components
        when DATABASE_URL is not explicitly set.  This avoids special-character
        issues when embedding the password directly in a connection string.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_HOST and self.DB_NAME and self.DB_USER:
            password = quote_plus(self.DB_PASSWORD or "")
            return (
                f"postgresql+psycopg2://{self.DB_USER}:{password}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        raise ValueError("DATABASE_URL must be configured.")

    model_config = {"env_file": ".env"}


settings = Settings()
