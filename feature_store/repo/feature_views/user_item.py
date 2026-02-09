# Real-Time Recommender System - Combined User-Item Features
"""
Combined feature views for user-item pairs.

This module provides feature views that combine user and item
features for direct use in recommendation models.
"""

from feast import FeatureView, Entity
from feast.types import Float32, Int64, String

# Import entity definitions
from ..features.user_features import user
from ..features.item_features import item


# ============================================
# User-Item Pair Features
# ============================================
user_item_combined_features = FeatureView(
    name="user_item_features",
    entities=[user, item],
    ttl=None,  # No TTL for training data
    schema=[
        # User features
        Field(name="user_id", dtype=String),
        Field(name="user_activity_level", dtype=Float32),
        Field(name="user_session_count", dtype=Int64),
        Field(name="user_engagement_rate", dtype=Float32),
        Field(name="user_is_premium", dtype=String),

        # Item features
        Field(name="item_id", dtype=String),
        Field(name="item_category", dtype=Int64),
        Field(name="item_price", dtype=Float32),
        Field(name="item_popularity", dtype=Float32),
        Field(name="item_quality", dtype=Float32),
        Field(name="item_recency", dtype=Float32),

        # Interaction features
        Field(name="category_match", dtype=Float32, description="1 if item category in user preferences"),
        Field(name="price_affordability", dtype=Float32, description="Price relative to user budget"),
        Field(name="popularity_surprise", dtype=Float32, description="Item popularity vs user typical engagement"),
    ],
    description="Combined user-item features for recommendation model",
)


def compute_interaction_features(
    user_features_df,
    item_features_df,
    interactions_df,
) -> "DataFrame":
    """
    Compute user-item interaction features.

    These features capture the interaction between user preferences
    and item characteristics.

    Args:
        user_features_df: DataFrame with user features
        item_features_df: DataFrame with item features
        interactions_df: DataFrame with past interactions

    Returns:
        DataFrame with interaction features
    """
    import pandas as pd
    import numpy as np

    # Merge user and item features
    pairs = interactions_df[["user_id", "item_id"]].drop_duplicates()

    # Get user and item features
    user_feat = user_features_df.rename(
        columns={c: f"user_{c}" for c in user_features_df.columns if c != "user_id"}
    )
    item_feat = item_features_df.rename(
        columns={c: f"item_{c}" for c in item_features_df.columns if c != "item_id"}
    )

    # Merge features
    features = pairs.merge(user_feat, on="user_id", how="left")
    features = features.merge(item_feat, on="item_id", how="left")

    # Compute interaction features
    # Category match: 1 if user's preferred category matches item category
    features["category_match"] = features.apply(
        lambda row: 1.0 if str(row["item_category"]) in str(row.get("user_preferred_categories", ""))
        else 0.0,
        axis=1,
    )

    # Price affordability (simplified)
    features["price_affordability"] = 1.0 - np.minimum(
        features["item_price"] / 100.0, 1.0
    )

    # Popularity surprise
    avg_user_popularity = features["user_engagement_rate"].mean()
    features["popularity_surprise"] = features["item_popularity"] / (
        avg_user_popularity + 0.01
    )

    return features
