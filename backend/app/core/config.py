"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "JobPilot AI"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-production-use-openssl-rand")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_db: str = "jobpilot"

    redis_url: str = "redis://redis:6379/0"

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_client_id: str = "jobpilot-api"
    kafka_group_id: str = "jobpilot-workers"
    kafka_topics: list[str] = Field(
        default_factory=lambda: [
            "job.fetch",
            "job.match",
            "job.apply",
            "job.success",
            "job.failed",
            "notifications",
            "reports",
        ]
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    scheduler_interval_seconds: int = 3600
    match_threshold: float = 0.7
    max_applications_per_day: int = 50
    playwright_headless: bool = True
    upload_dir: str = "/tmp/jobpilot/uploads"
    screenshot_dir: str = "/tmp/jobpilot/screenshots"
    report_dir: str = "/tmp/jobpilot/reports"

    log_level: str = "INFO"
    prometheus_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
