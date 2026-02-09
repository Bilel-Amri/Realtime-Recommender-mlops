# Real-Time Recommender System - Feature Store Features Package
"""
Feature definitions for the recommendation system.

This package contains:
- User feature definitions
- Item feature definitions
- Feature transformation logic
- Feature metadata and descriptions

All features are defined using Feast Feature View definitions.
"""

from .user_features import user_features, user_stat_features
from .item_features import item_features, item_stat_features

__all__ = [
    "user_features",
    "user_stat_features",
    "item_features",
    "item_stat_features",
]
