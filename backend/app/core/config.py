# Real-Time Recommender System - Configuration Module
"""
Application configuration using Pydantic Settings with environment variable support.

This module provides centralized configuration management for the entire application.
It loads settings from environment variables with sensible defaults, supporting
different deployment environments (development, staging, production).

Why Pydantic Settings?
- Type validation ensures configuration correctness at startup
- Environment variable binding for 12-factor app compliance
- Secret management without hardcoding credentials
- Nested configurations for complex deployments
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class serves as the single source of truth for all application configuration.
    It validates types, provides defaults, and supports environment variable overrides.

    Environment variables are automatically mapped from ALL_CAPS names to nested
    structures. For example, MLFLOW_TRACKING_URI becomes mlflow.tracking_uri.

    Attributes:
        app_env: Deployment environment (development/staging/production)
        debug: Enable debug mode for additional logging and hot reload
        log_level: Logging verbosity level
        version: Application version string

        mlflow_tracking_uri: MLflow tracking server URI
        mlflow_registry_uri: MLflow model registry URI
        mlflow_experiment_name: Name of MLflow experiment
        mlflow_artifact_root: Root directory for MLflow artifacts

        model_name: Name of the model in MLflow registry
        model_stage: Current deployment stage (Staging/Production)
        candidate_pool_size: Number of candidates to score
        recommendation_top_k: Number of recommendations to return

        feature_store_type: Type of feature store (redis/feast/simulated)
        feast_core_url: Feast feature server URL
        redis_host: Redis server hostname
        redis_port: Redis server port

        database_url: PostgreSQL connection URL
        database_pool_size: Connection pool minimum size
        database_max_overflow: Connection pool maximum overflow

        metrics_port: Port for Prometheus metrics endpoint
        prometheus_retention: Prometheus retention period
        drift_detection_threshold: Threshold for drift alerts
        alert_webhook_url: Webhook URL for alert notifications

        redis_cache_host: Redis cache hostname
        redis_cache_port: Redis cache port
        redis_cache_ttl: Cache TTL in seconds

        api_key_enabled: Enable API key authentication
        api_keys: Comma-separated list of valid API keys
        cors_origins: List of allowed CORS origins

        max_request_size: Maximum request size in bytes
        request_timeout: Request timeout in seconds
        concurrent_requests: Maximum concurrent requests

        cold_start_popular_items: Comma-separated list of popular item IDs
        cold_start_default_count: Default number of recommendations for cold start

        log_format: Log format (json/console)
        log_file: Path to log file
        log_rotation_size: Log file rotation size in bytes
        log_backup_count: Number of log file backups to keep
    """

    # Application Settings
    app_env: str = Field(default="development", description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    version: str = Field(default="1.0.0", description="Application version")

    # MLflow Configuration
    mlflow_tracking_uri: Optional[str] = Field(default=None, description="MLflow tracking URI")
    mlflow_registry_uri: Optional[str] = Field(default=None, description="MLflow registry URI")
    mlflow_experiment_name: str = Field(default="recommender-system", description="MLflow experiment name")
    mlflow_artifact_root: Optional[str] = Field(default=None, description="MLflow artifact root")

    # Model Settings
    model_path: Optional[str] = Field(default=None, description="Local path to model file")
    model_name: str = Field(default="recommender-model", description="Model name in MLflow")
    model_stage: str = Field(default="Production", description="Model deployment stage")
    candidate_pool_size: int = Field(default=100, description="Number of candidates to score")
    recommendation_top_k: int = Field(default=10, description="Number of recommendations to return")

    # Feature Store Settings
    feature_store_type: str = Field(default="simulated", description="Feature store type")
    feast_core_url: Optional[str] = Field(default=None, description="Feast core URL")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")

    # Database Settings
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_max_overflow: int = Field(default=20, description="Connection pool overflow")

    # Monitoring Settings
    metrics_port: int = Field(default=8001, description="Metrics port")
    prometheus_retention: str = Field(default="15d", description="Prometheus retention")
    drift_detection_threshold: float = Field(default=0.05, description="Drift detection threshold")
    alert_webhook_url: Optional[str] = Field(default=None, description="Alert webhook URL")

    # Redis Cache Settings
    redis_cache_host: str = Field(default="localhost", description="Redis cache host")
    redis_cache_port: int = Field(default=6379, description="Redis cache port")
    redis_cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    # Security Settings
    api_key_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_keys: List[str] = Field(default=[], description="List of API keys")
    cors_origins: List[str] = Field(default=["*"], description="List of CORS origins")

    # Performance Settings
    max_request_size: int = Field(default=10_485_760, description="Max request size in bytes")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    concurrent_requests: int = Field(default=100, description="Max concurrent requests")

    # Cold Start Settings
    cold_start_popular_items: str = Field(
        default="item_1,item_2,item_3,item_4,item_5",
        description="Popular items for cold start"
    )
    cold_start_default_count: int = Field(default=5, description="Cold start recommendation count")

    # Logging Settings
    log_format: str = Field(default="json", description="Log format")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_rotation_size: int = Field(default=104_857_600, description="Log rotation size")
    log_backup_count: int = Field(default=10, description="Log backup count")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, v):
        """Parse comma-separated API keys into a list."""
        if isinstance(v, str) and v:
            return [key.strip() for key in v.split(",")]
        return []

    @property
    def mlflow_enabled(self) -> bool:
        """Check if MLflow is configured."""
        return bool(self.mlflow_tracking_uri or self.mlflow_artifact_root)

    @property
    def cold_start_items_list(self) -> List[str]:
        """Get cold start popular items as a list."""
        return [item.strip() for item in self.cold_start_popular_items.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
        protected_namespaces = ()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures that settings are loaded only once and reused
    across the application. This is safe because settings are immutable after
    loading and the cache is cleared when the application restarts.

    Returns:
        Settings: Cached settings instance
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()
