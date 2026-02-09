# Real-Time Recommender System - User Feature Definitions
"""
User feature definitions for the recommendation system.

This module defines:
- User entity schema
- User feature views
- Feature transformations
- Feature metadata

User features are organized into:
- Static features (demographics, account info)
- Behavioral features (activity, engagement)
- Derived features (embeddings, aggregations)
"""

from datetime import timedelta
from feast import Entity, Field, FeatureView
from feast.types import Float32, Int64, String, Bool

# ============================================
# User Entity Definition
# ============================================
user = Entity(
    name="user",
    description="Unique user identifier",
    join_keys=["user_id"],
)

# ============================================
# User Feature Views
# ============================================
user_features = FeatureView(
    name="user_features",
    entities=[user],
    ttl=timedelta(days=7),  # Features expire after 7 days
    schema=[
        Field(name="user_id", dtype=String, description="User identifier"),
        Field(name="activity_level", dtype=Float32, description="Normalized activity score (0-1)"),
        Field(name="session_count", dtype=Int64, description="Total number of sessions"),
        Field(name="account_age_days", dtype=Int64, description="Account age in days"),
        Field(name="last_active_days_ago", dtype=Int64, description="Days since last activity"),
        Field(name="preferred_categories", dtype=String, description="Comma-separated preferred categories"),
        Field(name="avg_session_duration_min", dtype=Float32, description="Average session duration in minutes"),
        Field(name="devices_used", dtype=Int64, description="Number of unique devices"),
        Field(name="is_premium", dtype=Bool, description="Premium subscription status"),
        Field(name="engagement_rate", dtype=Float32, description="Historical engagement rate"),
    ],
    description="Core user features for recommendation",
)

# ============================================
# User Statistical Features (Rolling Window)
# ============================================
user_stat_features = FeatureView(
    name="user_stat_features",
    entities=[user],
    ttl=timedelta(hours=24),  # Statistics recomputed daily
    schema=[
        Field(name="user_id", dtype=String, description="User identifier"),
        Field(name="views_7d", dtype=Int64, description="Number of views in last 7 days"),
        Field(name="clicks_7d", dtype=Int64, description="Number of clicks in last 7 days"),
        Field(name="purchases_7d", dtype=Int64, description="Number of purchases in last 7 days"),
        Field(name="avg_item_rating_7d", dtype=Float32, description="Average rating given in last 7 days"),
        Field(name="ctr_7d", dtype=Float32, description="Click-through rate in last 7 days"),
        Field(name="diversity_score_7d", dtype=Float32, description="Category diversity score"),
        Field(name="recency_weighted_engagement", dtype=Float32, description="Recency-weighted engagement"),
    ],
    description="Rolling window statistics for user behavior",
)

# ============================================
# Feature Transformation Functions
# ============================================
def compute_user_features(user_interactions_df) -> "DataFrame":
    """
    Compute user features from interaction data.

    Args:
        user_interactions_df: DataFrame with user interactions

    Returns:
        DataFrame with computed user features
    """
    import pandas as pd

    # Group by user and compute features
    user_features = user_interactions_df.groupby("user_id").agg(
        activity_level=("engagement", "mean"),
        session_count=("session_id", "nunique"),
        avg_session_duration_min=("session_duration", "mean"),
        devices_used=("device_id", "nunique"),
        engagement_rate=("engagement", lambda x: (x > 0.3).mean()),
    ).reset_index()

    # Normalize activity level
    user_features["activity_level"] = user_features["activity_level"].clip(0, 1)

    return user_features


def compute_user_stat_features(
    user_interactions_df,
    window_days: int = 7,
) -> "DataFrame":
    """
    Compute rolling window statistics for users.

    Args:
        user_interactions_df: DataFrame with user interactions
        window_days: Rolling window size in days

    Returns:
        DataFrame with rolling statistics
    """
    import pandas as pd

    # Filter to window
    cutoff_date = user_interactions_df["timestamp"].max() - pd.Timedelta(days=window_days)
    window_df = user_interactions_df[
        user_interactions_df["timestamp"] >= cutoff_date
    ]

    # Compute statistics
    stats = window_df.groupby("user_id").agg(
        views_7d=("event_type", lambda x: (x == "view").sum()),
        clicks_7d=("event_type", lambda x: (x == "click").sum()),
        purchases_7d=("event_type", lambda x: (x == "purchase").sum()),
        avg_item_rating_7d=("rating", "mean"),
        ctr_7d=("engagement", lambda x: (x[x > 0.3].sum() / len(x)) if len(x) > 0 else 0),
    ).reset_index()

    return stats
