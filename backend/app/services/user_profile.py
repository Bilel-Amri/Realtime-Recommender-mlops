# Real-Time Recommender System - Dynamic User Profile Service
"""
Dynamic User Profile system backed by Redis.

Each user has a UserFeatureVector — an 8-dimensional interest vector
over genre/category dimensions. Item feature vectors are generated
deterministically from item IDs, enabling cosine-similarity scoring
that updates instantly as users adjust their interests.

Interest Categories (aligned with MovieLens genres):
    action, comedy, drama, romance, thriller, sci_fi, horror, documentary

Storage format in Redis:
    user:{user_id}:profile  ->  JSON   (interest dict + raw vector)
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# The 8-dimensional interest space
INTEREST_CATEGORIES: List[str] = [
    "action",
    "comedy",
    "drama",
    "romance",
    "thriller",
    "sci_fi",
    "horror",
    "documentary",
]
FEATURE_DIM = len(INTEREST_CATEGORIES)
PROFILE_TTL = 86400 * 30  # 30 days in seconds


# ---------------------------------------------------------------------------
# Item feature vectors  (deterministic, seeded from item_id)
# ---------------------------------------------------------------------------

def item_feature_vector(item_id: str) -> np.ndarray:
    """
    Return a deterministic 8-dim feature vector for an item.

    Uses Dirichlet(1,...,1) sampling from a seeded RNG derived from
    the item_id hash.  The result sums to 1 and lies on the simplex,
    which makes cosine similarity well-behaved.
    """
    seed = int(hashlib.md5(item_id.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.RandomState(seed)
    vec = rng.dirichlet(np.ones(FEATURE_DIM))
    return vec.astype(np.float32)


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------

def cosine_similarity(u: np.ndarray, v: np.ndarray) -> float:
    """Cosine similarity between two vectors, returns 0 if either is zero."""
    norm_u = float(np.linalg.norm(u))
    norm_v = float(np.linalg.norm(v))
    if norm_u == 0.0 or norm_v == 0.0:
        return 0.0
    return float(np.dot(u, v) / (norm_u * norm_v))


def dot_product_score(u: np.ndarray, v: np.ndarray) -> float:
    """Raw dot product (useful when magnitudes carry meaning)."""
    return float(np.dot(u, v))


# ---------------------------------------------------------------------------
# UserProfileService
# ---------------------------------------------------------------------------

class UserProfileService:
    """
    Manages dynamic user interest profiles stored in Redis.

    Each profile contains:
        - interests: {category: weight}  — weights in [0.0, 1.0]
        - vector: list[float]            — raw numpy-compatible array
        - interaction_count: int
        - created_at / updated_at: ISO timestamps
    """

    def __init__(self, redis_client):
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, user_id: str) -> str:
        return f"user:{user_id}:profile"

    def _build_vector(self, interests: Dict[str, float]) -> np.ndarray:
        return np.array(
            [float(interests.get(cat, 0.5)) for cat in INTEREST_CATEGORIES],
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str) -> Optional[Dict]:
        """Retrieve user profile from Redis.  Returns None if not found."""
        try:
            raw = self._redis.get(self._key(user_id))
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.error("get_profile_error", user_id=user_id, error=str(e))
        return None

    def create_profile(
        self,
        user_id: str,
        interests: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Create (or overwrite) a user profile with given interest weights.

        Args:
            user_id:   Unique user identifier.
            interests: Dict mapping category names to weights [0, 1].
                       Missing categories receive a neutral weight of 0.5.

        Returns:
            The newly created profile dict.
        """
        interests = interests or {}

        # Clip all weights to [0, 1] and fill defaults
        sanitized: Dict[str, float] = {
            cat: float(np.clip(interests.get(cat, 0.5), 0.0, 1.0))
            for cat in INTEREST_CATEGORIES
        }

        vector = self._build_vector(sanitized)

        profile = {
            "user_id": user_id,
            "interests": sanitized,
            "vector": vector.tolist(),
            "interaction_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self._redis.setex(self._key(user_id), PROFILE_TTL, json.dumps(profile))
            logger.info("user_profile_created", user_id=user_id, interests=sanitized)
        except Exception as e:
            logger.error("create_profile_error", user_id=user_id, error=str(e))

        return profile

    def update_user_interest(
        self,
        user_id: str,
        attribute: str,
        weight: float,
    ) -> Optional[Dict]:
        """
        Update (or add) a single interest dimension for a user.

        This is the core scoring-function hook:
            update_user_interest(user_id, attribute, weight)

        If the user has no profile yet, one is auto-created with neutral
        weights and then the requested attribute is applied.

        Args:
            user_id:   Target user.
            attribute: One of INTEREST_CATEGORIES.
            weight:    New weight value, clamped to [0.0, 1.0].

        Returns:
            Updated profile dict, or None on Redis error.
        """
        if attribute not in INTEREST_CATEGORIES:
            raise ValueError(
                f"Unknown interest attribute: '{attribute}'. "
                f"Valid values: {INTEREST_CATEGORIES}"
            )

        weight = float(np.clip(weight, 0.0, 1.0))

        profile = self.get_profile(user_id)
        if profile is None:
            profile = self.create_profile(user_id, {attribute: weight})
            return profile

        profile["interests"][attribute] = weight
        profile["vector"] = self._build_vector(profile["interests"]).tolist()
        profile["updated_at"] = datetime.utcnow().isoformat()
        profile["interaction_count"] = profile.get("interaction_count", 0) + 1

        try:
            self._redis.setex(self._key(user_id), PROFILE_TTL, json.dumps(profile))
            logger.info(
                "user_interest_updated",
                user_id=user_id,
                attribute=attribute,
                weight=weight,
            )
        except Exception as e:
            logger.error("update_interest_error", user_id=user_id, error=str(e))
            return None

        return profile

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_items(
        self,
        user_id: str,
        item_ids: List[str],
        method: str = "cosine",
    ) -> Optional[np.ndarray]:
        """
        Score a list of items for a user via vector similarity.

        Args:
            user_id:  Target user (must have a profile).
            item_ids: Items to score.
            method:   "cosine" (default) or "dot".

        Returns:
            Array of scores in [0, 1], or None if no profile exists.
        """
        profile = self.get_profile(user_id)
        if profile is None:
            return None

        user_vec = np.array(profile["vector"], dtype=np.float32)

        scores = []
        for item_id in item_ids:
            item_vec = item_feature_vector(item_id)
            if method == "dot":
                raw = dot_product_score(user_vec, item_vec)
            else:
                raw = cosine_similarity(user_vec, item_vec)

            # Map cosine similarity from [-1,1] to [0.5, 1.0] for UX
            scores.append(0.5 + raw * 0.5)

        return np.array(scores, dtype=np.float32)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_top_interests(self, user_id: str) -> List[Dict]:
        """Return interests sorted descending by weight."""
        profile = self.get_profile(user_id)
        if profile is None:
            return []
        return sorted(
            [
                {"category": cat, "weight": round(w, 3), "label": cat.replace("_", "-").title()}
                for cat, w in profile["interests"].items()
            ],
            key=lambda x: x["weight"],
            reverse=True,
        )

    def has_profile(self, user_id: str) -> bool:
        """Check if a user has a dynamic profile."""
        try:
            return bool(self._redis.exists(self._key(user_id)))
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_user_profile_service: Optional[UserProfileService] = None


def get_user_profile_service() -> Optional[UserProfileService]:
    """Return the singleton UserProfileService, or None if Redis unavailable."""
    return _user_profile_service


def init_user_profile_service(redis_client) -> UserProfileService:
    """Initialise the singleton with a Redis client."""
    global _user_profile_service
    _user_profile_service = UserProfileService(redis_client)
    logger.info("user_profile_service_initialized")
    return _user_profile_service
