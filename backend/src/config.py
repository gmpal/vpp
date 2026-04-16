"""
Centralized configuration management using Pydantic Settings.
All environment variables are validated and type-checked here.
"""

from typing import List

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    timescaledb_host: str = Field(default="localhost", description="TimescaleDB host", validation_alias="TIMESCALEDB_HOST")
    postgres_port: int = Field(default=5432, description="PostgreSQL port", validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(..., description="PostgreSQL database name", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(..., description="PostgreSQL username", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(..., description="PostgreSQL password", validation_alias="POSTGRES_PASSWORD")

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="kafka:29092", description="Kafka bootstrap servers", validation_alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topics: List[str] = Field(default=["solar", "load", "market"], description="Kafka topics")
    kafka_consumer_group: str = Field(default="test-group", description="Kafka consumer group ID")

    # MLflow Configuration
    mlflow_tracking_uri: str = Field(default="http://mlflow:5000", description="MLflow tracking URI", validation_alias="MLFLOW_TRACKING_URI")
    mlflow_backend_store_uri: str = Field(default="file:///app/mlruns", description="MLflow backend store", validation_alias="MLFLOW_BACKEND_STORE_URI")
    mlflow_default_artifact_root: str = Field(default="file:///app/artifacts", description="MLflow artifact root", validation_alias="MLFLOW_DEFAULT_ARTIFACT_ROOT")

    # API Configuration
    backend_port: int = Field(default=8000, description="Backend API port", validation_alias="BACKEND_PORT")
    frontend_port: int = Field(default=3000, description="Frontend port", validation_alias="FRONTEND_PORT")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")

    # Application Configuration
    log_level: str = Field(default="INFO", description="Logging level", validation_alias="LOG_LEVEL")
    environment: str = Field(default="development", description="Environment (development/production)", validation_alias="ENVIRONMENT")

    @field_validator("postgres_port", "backend_port", "frontend_port")
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


# Singleton instance
_settings: Settings = None


def get_settings() -> Settings:
    """Get or create settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Export for convenience
settings = get_settings()
