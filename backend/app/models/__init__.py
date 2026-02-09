# Real-Time Recommender System - Models Package
"""
Pydantic models for API requests, responses, and ML data structures.

This package provides:
- Request/response schemas for all API endpoints
- ML model input/output schemas
- Event tracking schemas
- Configuration schemas

All schemas are validated at API boundaries to ensure data integrity.
"""

from .schemas import (
    EventCreate,
    EventResponse,
    HealthCheckResponse,
    ModelInfoResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationItem,
    MetricsResponse,
    UserFeatures,
    ItemFeatures,
    PredictionMetrics,
)

__all__ = [
    "EventCreate",
    "EventResponse",
    "HealthCheckResponse",
    "ModelInfoResponse",
    "RecommendationRequest",
    "RecommendationResponse",
    "RecommendationItem",
    "UserFeatures",
    "ItemFeatures",
    "PredictionMetrics",
    "MetricsResponse",
]
