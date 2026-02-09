# Real-Time Recommender System - Services Package
"""
Business logic services for the recommendation system.

This package provides:
- RecommendationService: Core recommendation logic
- FeatureStoreService: Feature retrieval and caching
- MonitoringService: Metrics collection and drift detection
- EventService: User interaction logging

Services are designed to be stateless and thread-safe for production deployment.
"""

from .recommendation import RecommendationService
from .feature_store import FeatureStoreService
from .monitoring import MonitoringService

__all__ = [
    "RecommendationService",
    "FeatureStoreService",
    "MonitoringService",
]
