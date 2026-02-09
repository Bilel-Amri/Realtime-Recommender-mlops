# Real-Time Recommender System - Feature Views Package
"""
Feature view definitions for the Feast feature store.

This package contains pre-defined feature views that combine
user and item features for common use cases.
"""

from .user_item import user_item_combined_features

__all__ = ["user_item_combined_features"]
