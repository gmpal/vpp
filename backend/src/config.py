"""
Centralized configuration management using Pydantic Settings.
All environment variables are validated and type-checked here.

Settings are resolved lazily on first call to ``get_settings()`` so that
importing the backend never requires a populated ``.env``. Every field has a
local-development default; real deployments override them via environment
variables. When ``ENVIRONMENT=testing`` the ``.env`` file is ignored so tests
see only the variables they set themselves.
"""

import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    timescaledb_host: str = Field(default="localhost", description="TimescaleDB host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="postgres", description="PostgreSQL database name")
    postgres_user: str = Field(default="postgres", description="PostgreSQL username")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="kafka:29092", description="Kafka bootstrap servers")
    kafka_topics: List[str] = Field(default=["solar", "load", "market"], description="Kafka topics")
    kafka_consumer_group: str = Field(default="test-group", description="Kafka consumer group ID")

    # MLflow Configuration
    mlflow_tracking_uri: str = Field(default="http://mlflow:5000", description="MLflow tracking URI")
    mlflow_backend_store_uri: str = Field(default="file:///app/mlruns", description="MLflow backend store")
    mlflow_default_artifact_root: str = Field(default="file:///app/artifacts", description="MLflow artifact root")

    # Optimization
    optimization_sell_price_factor: float = Field(
        default=0.3,
        description="Price received for energy sold to the grid, as a fraction of the market (buy) price",
    )

    # API Configuration
    backend_port: int = Field(default=8000, description="Backend API port")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")

    # Application Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment (development/production/testing)")

    @field_validator("postgres_port", "backend_port")
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}, got {v}")
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ["development", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}, got {v}")
        return v.lower()

    @property
    def database_url(self) -> str:
        """Construct database connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.timescaledb_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_config(self) -> dict:
        """Get database configuration as dict for psycopg2."""
        return {
            "host": self.timescaledb_host,
            "port": self.postgres_port,
            "database": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the settings singleton."""
    global _settings
    if _settings is None:
        testing = os.environ.get("ENVIRONMENT", "").lower() == "testing"
        _settings = Settings(_env_file=None) if testing else Settings()
    return _settings


def reset_settings() -> None:
    """Drop the cached settings so the next ``get_settings()`` re-reads the environment."""
    global _settings
    _settings = None
