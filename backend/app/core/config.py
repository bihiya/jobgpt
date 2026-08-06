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
    redis_max_connections: int = 50
    redis_cache_ttl_seconds: int = 60
    redis_hot_ttl_seconds: int = 300

    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    mongodb_max_pool_size: int = 50
    mongodb_min_pool_size: int = 5
    request_timeout_seconds: int = 60

    otel_enabled: bool = False
    otel_exporter_endpoint: str = "http://otel-collector:4317"

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
            "job.dlq",
        ]
    )

    # LLM ranking
    llm_enabled: bool = False
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Object storage (S3-compatible)
    s3_enabled: bool = False
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint_url: str = ""
    s3_public_base_url: str = ""

    # Captcha / 2FA
    captcha_provider: str = "noop"
    captcha_api_key: str = ""
    captcha_api_url: str = "https://api.2captcha.com/createTask"
    totp_test_code: str = ""

    # Email alerts
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@jobpilot.ai"
    smtp_tls: bool = True

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
