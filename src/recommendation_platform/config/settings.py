from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration with safe local defaults and environment overrides."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_events_topic: str = "user-events"
    kafka_recommendations_topic: str = "recommendation-events"
    kafka_dlq_topic: str = "dead-letter-events"
    redis_url: str = "redis://localhost:6379/0"
    postgres_url: str = (
        "postgresql+psycopg://recommendation:recommendation@localhost:5432/recommendation"
    )
    mlflow_tracking_uri: str = "http://localhost:5000"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "events"
    model_path: Path = Path("data/processed/model.joblib")
    feature_version: str = "v1"
    model_version: str = "baseline-v1"
    experiment_name: str = "recommendation-platform"
    promotion_min_ndcg_gain: float = Field(default=0.01, ge=0)
    api_rate_limit_per_minute: int = Field(default=120, gt=0)
    candidate_limit: int = Field(default=100, gt=0)
    default_recommendation_limit: int = Field(default=10, gt=0, le=100)
    random_seed: int = 42


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
