# Real-Time Recommender System - Pydantic Schemas
"""
Data validation schemas for API requests and responses.

These schemas define the contract between clients and the API, ensuring
type safety and data validation at all entry points.

Why separate schemas?
- Clear API contract documentation
- Type validation at API boundaries
- Serialization/deserialization handling
- Request/response documentation via OpenAPI
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Types of user interactions to track."""

    VIEW = "view"  # User viewed an item
    CLICK = "click"  # User clicked on an item
    PURCHASE = "purchase"  # User purchased an item
    LIKE = "like"  # User liked an item
    DISLIKE = "dislike"  # User disliked/hidden an item
    SHARE = "share"  # User shared an item
    SEARCH = "search"  # User searched for items
    RATING = "rating"  # User rated an item


class RecommendationRequest(BaseModel):
    """Request schema for getting recommendations."""

    user_id: str = Field(
        ...,
        description="Unique user identifier",
        min_length=1,
        max_length=256,
        examples=["user_12345"],
    )
    num_recommendations: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of recommendations to return",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (time, location, device, etc.)",
        examples=[{"time_of_day": "evening", "device": "mobile"}],
    )
    exclude_items: Optional[List[str]] = Field(
        default=None,
        description="Item IDs to exclude from recommendations",
        max_length=100,
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate and sanitize user ID."""
        # Remove leading/trailing whitespace
        v = v.strip()
        # Check for invalid characters
        if not v:
            raise ValueError("user_id cannot be empty")
        # Normalize user ID format
        return v.lower().replace(" ", "_")


class RecommendationItem(BaseModel):
    """A single recommended item with score and metadata."""

    item_id: str = Field(..., description="Unique item identifier")
    score: float = Field(..., description="Relevance score (higher is better)")
    rank: int = Field(..., ge=1, description="Position in recommendation list")
    reason: Optional[str] = Field(
        default=None,
        description="Explanation for why this item was recommended",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional item metadata",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "item_456",
                "score": 0.95,
                "rank": 1,
                "reason": "Similar users also viewed",
                "metadata": {"category": "electronics", "price": 299.99},
            }
        }


class RecommendationResponse(BaseModel):
    """Response schema for recommendation endpoint."""

    user_id: str = Field(..., description="User ID for which recommendations were generated")
    recommendations: List[RecommendationItem] = Field(
        ..., description="List of recommended items"
    )
    model_version: str = Field(..., description="Version of the model used")
    model_stage: str = Field(..., description="Deployment stage of the model")
    generated_at: datetime = Field(
        ..., description="Timestamp when recommendations were generated"
    )
    generation_time_ms: float = Field(
        ..., description="Time taken to generate recommendations (milliseconds)"
    )
    cached: bool = Field(
        default=False,
        description="Whether the response was served from cache",
    )
    cold_start: bool = Field(
        default=False,
        description="Whether this was a cold start request",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "recommendations": [
                    {
                        "item_id": "item_456",
                        "score": 0.95,
                        "rank": 1,
                        "reason": "Similar users also viewed",
                        "metadata": {"category": "electronics"},
                    }
                ],
                "model_version": "abc123def456",
                "model_stage": "Production",
                "generated_at": "2024-01-15T10:30:00Z",
                "generation_time_ms": 45.5,
                "cached": False,
                "cold_start": False,
            }
        }


class EventCreate(BaseModel):
    """Schema for logging a user interaction event."""

    user_id: str = Field(..., description="User who performed the action")
    item_id: str = Field(..., description="Item that was interacted with")
    event_type: EventType = Field(..., description="Type of interaction")
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the event occurred (defaults to now)",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (device, location, etc.)",
    )
    value: Optional[float] = Field(
        default=None,
        description="Numeric value (e.g., purchase amount, watch time)",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Optional[datetime]) -> datetime:
        """Parse timestamp, defaulting to now if not provided."""
        if v is None:
            return datetime.utcnow()
        return v


class EventResponse(BaseModel):
    """Response schema for event logging."""

    event_id: str = Field(..., description="Unique identifier for the logged event")
    user_id: str = Field(..., description="User who performed the action")
    item_id: str = Field(..., description="Item that was interacted with")
    event_type: EventType = Field(..., description="Type of interaction")
    timestamp: datetime = Field(..., description="When the event was recorded")
    status: str = Field(default="logged", description="Status of the event logging")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123",
                "user_id": "user_12345",
                "item_id": "item_456",
                "event_type": "click",
                "timestamp": "2024-01-15T10:30:00Z",
                "status": "logged",
            }
        }


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status of an individual component."""

    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    message: Optional[str] = Field(default=None, description="Status message")
    latency_ms: Optional[float] = Field(default=None, description="Response latency")


class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: HealthStatus = Field(..., description="Overall system health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Check timestamp")
    uptime_seconds: float = Field(..., description="Time since service start")
    components: List[ComponentHealth] = Field(
        ..., description="Health status of individual components"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "uptime_seconds": 86400.0,
                "components": [
                    {
                        "name": "database",
                        "status": "healthy",
                        "message": "Connection active",
                        "latency_ms": 5.2,
                    },
                    {
                        "name": "feature_store",
                        "status": "healthy",
                        "message": "Connected",
                        "latency_ms": 12.1,
                    },
                ],
            }
        }


class ModelStage(str, Enum):
    """Model deployment stages."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class ModelInfoResponse(BaseModel):
    """Response schema for model information endpoint."""

    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version (git hash or semantic)")
    stage: ModelStage = Field(..., description="Current deployment stage")
    created_at: datetime = Field(..., description="When the model was registered")
    last_updated: datetime = Field(..., description="When the model was last updated")
    metrics: Dict[str, float] = Field(
        ..., description="Model performance metrics"
    )
    description: Optional[str] = Field(default=None, description="Model description")
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Expected input schema"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Output schema"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Model tags")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "recommender-model",
                "version": "abc123def456",
                "stage": "Production",
                "created_at": "2024-01-01T00:00:00Z",
                "last_updated": "2024-01-15T00:00:00Z",
                "metrics": {
                    "recall@10": 0.12,
                    "map@10": 0.08,
                    "ctr_proxy": 0.05,
                },
                "description": "LightGBM recommendation model v2.1",
                "tags": {"team": "recommendations", "priority": "high"},
            }
        }


class PredictionMetrics(BaseModel):
    """Metrics about model predictions."""

    total_predictions: int = Field(..., description="Total predictions made")
    predictions_last_hour: int = Field(
        ..., description="Predictions in the last hour"
    )
    average_latency_ms: float = Field(..., description="Average prediction latency")
    p95_latency_ms: float = Field(..., description="95th percentile latency")
    p99_latency_ms: float = Field(..., description="99th percentile latency")
    cache_hit_rate: float = Field(
        ..., description="Rate of cache hits (0.0 to 1.0)"
    )
    cold_start_rate: float = Field(
        ..., description="Rate of cold start predictions"
    )


class DriftMetrics(BaseModel):
    """Metrics for data/prediction drift detection."""

    feature_drift_score: float = Field(
        ..., description="Feature distribution drift score (0.0 to 1.0)"
    )
    prediction_drift_score: float = Field(
        ..., description="Prediction distribution drift score (0.0 to 1.0)"
    )
    last_checked: datetime = Field(..., description="When drift was last checked")
    status: str = Field(..., description="Drift status (normal/warning/critical)")
    drifted_features: List[str] = Field(
        default_factory=list, description="Features with detected drift"
    )


class MetricsResponse(BaseModel):
    """Response schema for metrics endpoint."""

    prediction_metrics: PredictionMetrics = Field(
        ..., description="Prediction-related metrics"
    )
    drift_metrics: DriftMetrics = Field(..., description="Drift detection metrics")
    system_metrics: Dict[str, float] = Field(
        default_factory=dict, description="System resource metrics"
    )
    custom_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Custom business metrics"
    )
    timestamp: datetime = Field(..., description="Metrics timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "prediction_metrics": {
                    "total_predictions": 1000000,
                    "predictions_last_hour": 50000,
                    "average_latency_ms": 45.5,
                    "p95_latency_ms": 120.0,
                    "p99_latency_ms": 250.0,
                    "cache_hit_rate": 0.35,
                    "cold_start_rate": 0.02,
                },
                "drift_metrics": {
                    "feature_drift_score": 0.02,
                    "prediction_drift_score": 0.01,
                    "last_checked": "2024-01-15T10:30:00Z",
                    "status": "normal",
                    "drifted_features": [],
                },
                "system_metrics": {
                    "cpu_usage_percent": 45.2,
                    "memory_usage_percent": 62.8,
                    "request_queue_size": 5,
                },
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class UserFeatures(BaseModel):
    """Schema for user feature vector."""

    user_id: str = Field(..., description="User identifier")
    feature_vector: List[float] = Field(..., description="Feature values")
    created_at: Optional[datetime] = Field(
        default=None, description="When features were computed"
    )
    source: Optional[str] = Field(default=None, description="Feature source")


class ItemFeatures(BaseModel):
    """Schema for item feature vector."""

    item_id: str = Field(..., description="Item identifier")
    feature_vector: List[float] = Field(..., description="Feature values")
    created_at: Optional[datetime] = Field(
        default=None, description="When features were computed"
    )
    source: Optional[str] = Field(default=None, description="Feature source")


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")
    request_id: Optional[str] = Field(default=None, description="Request correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "ModelNotFoundError",
                "message": "Model 'recommender-model' not found in Production stage",
                "details": {"stage": "Production", "model_name": "recommender-model"},
                "request_id": "req_abc123",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }
