# Real-Time Recommender System - Item Feature Definitions
"""
Item feature definitions for the recommendation system.

This module defines:
- Item entity schema
- Item feature views
- Item popularity and quality metrics
- Content-based features

Item features are organized into:
- Content features (category, description embeddings)
- Quality features (ratings, reviews)
- Popularity features (views, purchases)
- Recency features (launch date, trends)
"""

from datetime import timedelta
from feast import Entity, Field, FeatureView
from feast.types import Float32, Int64, String, Bool

# ============================================
# Item Entity Definition
# ============================================
item = Entity(
    name="item",
    description="Unique item identifier",
    join_keys=["item_id"],
)

# ============================================
# Item Feature Views
# ============================================
item_features = FeatureView(
    name="item_features",
    entities=[item],
    ttl=timedelta(days=30),  # Item features expire after 30 days
    schema=[
        Field(name="item_id", dtype=String, description="Item identifier"),
        Field(name="category_encoded", dtype=Int64, description="Category identifier"),
        Field(name="category_name", dtype=String, description="Category name"),
        Field(name="subcategory_encoded", dtype=Int64, description="Subcategory identifier"),
        Field(name="price", dtype=Float32, description="Item price"),
        Field(name="price_bucket", dtype=String, description="Price bucket (budget/mid/premium)"),
        Field(name="popularity_score", dtype=Float32, description="Historical popularity score (0-1)"),
        Field(name="avg_rating", dtype=Float32, description="Average user rating (1-5)"),
        Field(name="review_count", dtype=Int64, description="Number of reviews"),
        Field(name="recency_score", dtype=Float32, description="Recency score (newer = higher)"),
        Field(name="is_available", dtype=Bool, description="Availability status"),
        Field(name="quality_score", dtype=Float32, description="Computed quality score"),
        Field(name="content_embedding_0", dtype=Float32, description="Content embedding dimension 0"),
        Field(name="content_embedding_1", dtype=Float32, description="Content embedding dimension 1"),
        Field(name="content_embedding_2", dtype=Float32, description="Content embedding dimension 2"),
        Field(name="content_embedding_3", dtype=Float32, description="Content embedding dimension 3"),
        Field(name="content_embedding_4", dtype=Float32, description="Content embedding dimension 4"),
    ],
    description="Core item content features",
)

# ============================================
# Item Statistical Features (Rolling Window)
# ============================================
item_stat_features = FeatureView(
    name="item_stat_features",
    entities=[item],
    ttl=timedelta(hours=6),  # Recomputed every 6 hours
    schema=[
        Field(name="item_id", dtype=String, description="Item identifier"),
        Field(name="views_24h", dtype=Int64, description="Views in last 24 hours"),
        Field(name="clicks_24h", dtype=Int64, description="Clicks in last 24 hours"),
        Field(name="purchases_24h", dtype=Int64, description="Purchases in last 24 hours"),
        Field(name="ctr_24h", dtype=Float32, description="Click-through rate in last 24 hours"),
        Field(name="conversion_rate_24h", dtype=Float32, description="Purchase conversion rate"),
        Field(name="trend_score", dtype=Float32, description="Popularity trend score"),
        Field(name="freshness_score", dtype=Float32, description="Content freshness score"),
        Field(name="shelf_position", dtype=Int64, description="Recommended shelf position"),
    ],
    description="Real-time item statistics for trending/popularity",
)

# ============================================
# Feature Transformation Functions
# ============================================
def compute_item_features(items_df) -> "DataFrame":
    """
    Compute item features from item metadata.

    Args:
        items_df: DataFrame with item metadata

    Returns:
        DataFrame with computed item features
    """
    import numpy as np

    # Compute derived features
    items_df["price_bucket"] = pd.cut(
        items_df["price"],
        bins=[0, 25, 100, 500, float("inf")],
        labels=["budget", "mid", "premium", "luxury"],
    )

    # Compute quality score from ratings and reviews
    items_df["quality_score"] = (
        items_df["avg_rating"] / 5.0 * 0.7 +
        np.minimum(items_df["review_count"], 1000) / 1000 * 0.3
    )

    return items_df


def compute_item_stat_features(
    interactions_df,
    items_df,
    window_hours: int = 24,
) -> "DataFrame":
    """
    Compute rolling window statistics for items.

    Args:
        interactions_df: DataFrame with user interactions
        items_df: DataFrame with item metadata
        window_hours: Rolling window size in hours

    Returns:
        DataFrame with rolling statistics
    """
    import pandas as pd

    # Filter to window
    cutoff = interactions_df["timestamp"].max() - pd.Timedelta(hours=window_hours)
    window_df = interactions_df[
        interactions_df["timestamp"] >= cutoff
    ]

    # Compute statistics
    stats = window_df.groupby("item_id").agg(
        views_24h=("event_type", lambda x: (x == "view").sum()),
        clicks_24h=("event_type", lambda x: (x == "click").sum()),
        purchases_24h=("event_type", lambda x: (x == "purchase").sum()),
    ).reset_index()

    # Compute rates
    stats["ctr_24h"] = stats["clicks_24h"] / stats["views_24h"].clip(lower=1)
    stats["conversion_rate_24h"] = stats["purchases_24h"] / stats["clicks_24h"].clip(lower=1)

    # Compute trend score (compare to historical average)
    historical_avg = interactions_df.groupby("item_id").size()
    current_count = stats["views_24h"]
    stats["trend_score"] = (current_count / historical_avg.reindex(stats["item_id"]).fillna(1)).clip(0, 10)

    # Compute freshness score
    items_df_lookup = items_df.set_index("item_id")["launch_date"]
    stats["freshness_score"] = stats["item_id"].map(
        lambda x: (pd.Timestamp.now() - items_df_lookup.get(x, pd.Timestamp.now())).days
    )
    stats["freshness_score"] = np.exp(-stats["freshness_score"] / 30)  # Decay over 30 days

    return stats


# Import pandas for the functions above
import pandas as pd
import numpy as np
