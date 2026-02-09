# Real-Time Recommender System - API Package
"""
API endpoint routers for the recommendation system.

This package provides:
- recommend: Recommendation generation endpoints
- events: Event logging endpoints
- metrics: Metrics and monitoring endpoints
- health: Health check endpoints
- mlops: MLOps and dynamic model management endpoints

All endpoints are documented with OpenAPI schemas.
"""

from .recommend import router as recommend_router
from .events import router as events_router
from .metrics import router as metrics_router
from .health import router as health_router
from .mlops import router as mlops_router

__all__ = [
    "recommend_router",
    "events_router",
    "metrics_router",
    "health_router",
    "mlops_router",
]
