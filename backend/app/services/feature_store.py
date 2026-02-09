# Real-Time Recommender System - Feature Store Service
"""
Feature store integration for online feature retrieval.

This module provides:
- Feature retrieval from online store (Redis/Feast)
- Feature caching for performance
- Offline/online feature consistency
- Feature schema validation

The feature store is critical for real-time recommendation performance.
It must provide low-latency access to user and item features.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import redis
import structlog

from ..core.config import settings

logger = structlog.get_logger(__name__)


class FeatureStoreBackend(ABC):
    """
    Abstract base class for feature store backends.

    This defines the interface that all feature store implementations
    must follow. It enables swapping between different backends
    (Redis, Feast, mock, etc.) without changing the application code.
    """

    @abstractmethod
    async def get_user_features(self, user_id: str) -> Optional[np.ndarray]:
        """Retrieve features for a user."""
        pass

    @abstractmethod
    async def get_item_features(self, item_id: str) -> Optional[np.ndarray]:
        """Retrieve features for an item."""
        pass

    @abstractmethod
    async def get_user_features_batch(
        self, user_ids: List[str]
    ) -> Dict[str, Optional[np.ndarray]]:
        """Retrieve features for multiple users."""
        pass

    @abstractmethod
    async def get_item_features_batch(
        self, item_ids: List[str]
    ) -> np.ndarray:
        """Retrieve features for multiple items."""
        pass

    @abstractmethod
    async def write_user_features(
        self, user_id: str, features: np.ndarray, timestamp: Optional[datetime] = None
    ) -> bool:
        """Write user features to the store."""
        pass

    @abstractmethod
    async def write_item_features(
        self, item_id: str, features: np.ndarray, timestamp: Optional[datetime] = None
    ) -> bool:
        """Write item features to the store."""
        pass

    @abstractmethod
    async def health_check(self) -> Tuple[bool, float]:
        """Check feature store health and latency."""
        pass


class RedisFeatureStore(FeatureStoreBackend):
    """
    Redis-based feature store implementation.

    This implementation uses Redis as the online feature store,
    providing:
    - Sub-millisecond feature retrieval latency
    - Built-in caching with TTL support
    - Data type support for feature vectors

    Feature Storage Format:
        User features: user:{user_id}:features -> JSON array
        Item features: item:{item_id}:features -> JSON array
        Metadata: user:{user_id}:metadata -> JSON object
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: Optional[str] = None,
        ttl: int = None,
    ):
        """
        Initialize Redis feature store connection.

        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis authentication password
            ttl: Feature TTL in seconds (None for no expiry)
        """
        self._host = host or settings.redis_host
        self._port = port or settings.redis_port
        self._db = db
        self._password = password
        self._ttl = ttl or settings.redis_cache_ttl
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._metrics = {
            "total_reads": 0,
            "total_writes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_latency_ms": 0.0,
        }

    def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._pool = redis.ConnectionPool(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)

        return self._client

    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        return self._get_client()

    def _user_key(self, user_id: str) -> str:
        """Generate Redis key for user features."""
        return f"user:{user_id}:features"

    def _item_key(self, item_id: str) -> str:
        """Generate Redis key for item features."""
        return f"item:{item_id}:features"

    def _metadata_key(self, entity_type: str, entity_id: str) -> str:
        """Generate Redis key for metadata."""
        return f"{entity_type}:{entity_id}:metadata"

    async def get_user_features(self, user_id: str) -> Optional[np.ndarray]:
        """Retrieve user features from Redis."""
        start_time = time.perf_counter()
        self._metrics["total_reads"] += 1

        try:
            key = self._user_key(user_id)
            data = await asyncio.to_thread(self.client.get, key)

            if data is None:
                self._metrics["cache_misses"] += 1
                logger.debug("user_features_not_found", user_id=user_id)
                return None

            self._metrics["cache_hits"] += 1

            # Parse features from JSON
            features = np.array(json.loads(data), dtype=np.float32)

            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency_ms

            logger.debug(
                "user_features_retrieved",
                user_id=user_id,
                feature_dim=len(features),
                latency_ms=round(latency_ms, 2),
            )

            return features

        except Exception as e:
            logger.error(
                "user_features_retrieval_failed",
                user_id=user_id,
                error=str(e),
            )
            return None

    async def get_item_features(self, item_id: str) -> Optional[np.ndarray]:
        """Retrieve item features from Redis."""
        start_time = time.perf_counter()

        try:
            key = self._item_key(item_id)
            data = await asyncio.to_thread(self.client.get, key)

            if data is None:
                logger.debug("item_features_not_found", item_id=item_id)
                return None

            features = np.array(json.loads(data), dtype=np.float32)

            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency_ms

            return features

        except Exception as e:
            logger.error(
                "item_features_retrieval_failed",
                item_id=item_id,
                error=str(e),
            )
            return None

    async def get_user_features_batch(
        self, user_ids: List[str]
    ) -> Dict[str, Optional[np.ndarray]]:
        """Retrieve features for multiple users using pipeline."""
        start_time = time.perf_counter()
        results = {}

        try:
            pipe = self.client.pipeline()

            for user_id in user_ids:
                pipe.get(self._user_key(user_id))

            responses = await asyncio.to_thread(pipe.execute)

            for user_id, data in zip(user_ids, responses):
                if data is None:
                    results[user_id] = None
                else:
                    results[user_id] = np.array(json.loads(data), dtype=np.float32)

            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency_ms

            return results

        except Exception as e:
            logger.error("batch_user_features_failed", error=str(e))
            return {user_id: None for user_id in user_ids}

    async def get_item_features_batch(self, item_ids: List[str]) -> np.ndarray:
        """
        Retrieve features for multiple items.

        Returns a 2D array where each row is an item's feature vector.
        Missing items are padded with zeros.
        """
        start_time = time.perf_counter()

        try:
            # Get features for each item
            features_list = []
            for item_id in item_ids:
                features = await self.get_item_features(item_id)
                if features is None:
                    features = np.zeros(20, dtype=np.float32)  # Default feature dim
                features_list.append(features)

            result = np.vstack(features_list)

            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency_ms

            return result

        except Exception as e:
            logger.error("batch_item_features_failed", error=str(e))
            return np.zeros((len(item_ids), 20), dtype=np.float32)

    async def write_user_features(
        self,
        user_id: str,
        features: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Write user features to Redis."""
        self._metrics["total_writes"] += 1

        try:
            key = self._user_key(user_id)
            data = json.dumps(features.tolist())

            if self._ttl:
                await asyncio.to_thread(
                    self.client.setex, key, self._ttl, data
                )
            else:
                await asyncio.to_thread(self.client.set, key, data)

            # Write metadata
            metadata = {
                "updated_at": (timestamp or datetime.utcnow()).isoformat(),
                "feature_dim": len(features),
            }
            metadata_key = self._metadata_key("user", user_id)
            await asyncio.to_thread(
                self.client.setex, metadata_key, self._ttl, json.dumps(metadata)
            )

            logger.info(
                "user_features_written",
                user_id=user_id,
                feature_dim=len(features),
            )

            return True

        except Exception as e:
            logger.error(
                "user_features_write_failed",
                user_id=user_id,
                error=str(e),
            )
            return False

    async def write_item_features(
        self,
        item_id: str,
        features: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Write item features to Redis."""
        try:
            key = self._item_key(item_id)
            data = json.dumps(features.tolist())

            if self._ttl:
                await asyncio.to_thread(
                    self.client.setex, key, self._ttl, data
                )
            else:
                await asyncio.to_thread(self.client.set, key, data)

            logger.info(
                "item_features_written",
                item_id=item_id,
                feature_dim=len(features),
            )

            return True

        except Exception as e:
            logger.error(
                "item_features_write_failed",
                item_id=item_id,
                error=str(e),
            )
            return False

    async def health_check(self) -> Tuple[bool, float]:
        """Check Redis health and latency with timeout."""
        start_time = time.perf_counter()

        try:
            # Add a timeout wrapper for the ping operation
            ping_result = await asyncio.wait_for(
                asyncio.to_thread(self.client.ping),
                timeout=2.0  # 2 second timeout
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            return True, latency_ms
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("redis_health_check_timeout", latency_ms=latency_ms)
            return False, latency_ms
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("redis_health_check_failed", error=str(e))
            return False, latency_ms

    def get_metrics(self) -> Dict[str, Any]:
        """Get feature store metrics."""
        total = self._metrics["total_reads"]
        return {
            "total_reads": self._metrics["total_reads"],
            "total_writes": self._metrics["total_writes"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "cache_hit_rate": (
                self._metrics["cache_hits"] / total if total > 0 else 0
            ),
            "average_latency_ms": (
                self._metrics["total_latency_ms"] / total if total > 0 else 0
            ),
        }


class MockFeatureStore(FeatureStoreBackend):
    """
    In-memory mock feature store for development and testing.

    This implementation provides a simple in-memory dictionary-based
    feature store without external dependencies AND tracks user interactions
    to compute dynamic features.
    """

    def __init__(self, user_dim: int = 50, item_dim: int = 20):
        """
        Initialize mock feature store.

        Args:
            user_dim: User feature vector dimension
            item_dim: Item feature vector dimension
        """
        self._user_features: Dict[str, np.ndarray] = {}
        self._item_features: Dict[str, np.ndarray] = {}
        self._user_dim = user_dim
        self._item_dim = item_dim
        self._user_count =0
        self._item_count = 0
        
        # NEW: Track user interactions for dynamic features
        self._user_interactions: Dict[str, List[Dict[str, Any]]] = {}
        self._user_stats: Dict[str, Dict[str, Any]] = {}

    async def get_user_features(self, user_id: str) -> Optional[np.ndarray]:
        """
        Get user features from mock store.
        
        NOW USES DYNAMIC FEATURE COMPUTATION from user interactions!
        """
        if user_id not in self._user_features:
            # Compute features from interactions (if any) or create new user
            features = self.compute_user_features(user_id)
            await self.write_user_features(user_id, features)
            return features

        # Return cached features (will be updated by record_interaction)
        return self._user_features.get(user_id)

    async def get_item_features(self, item_id: str) -> Optional[np.ndarray]:
        """Get item features from mock store."""
        if item_id not in self._item_features:
            await self.write_item_features(item_id, self._generate_item_features())

        return self._item_features.get(item_id)

    async def get_user_features_batch(
        self, user_ids: List[str]
    ) -> Dict[str, Optional[np.ndarray]]:
        """Get features for multiple users."""
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.get_user_features(user_id)
        return results

    async def get_item_features_batch(self, item_ids: List[str]) -> np.ndarray:
        """Get features for multiple items."""
        features = []
        for item_id in item_ids:
            feat = await self.get_item_features(item_id)
            if feat is None:
                feat = np.zeros(self._item_dim, dtype=np.float32)
            features.append(feat)
        return np.vstack(features)

    async def write_user_features(
        self,
        user_id: str,
        features: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Write user features to mock store."""
        self._user_features[user_id] = features
        self._user_count += 1
        return True

    async def write_item_features(
        self,
        item_id: str,
        features: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Write item features to mock store."""
        self._item_features[item_id] = features
        self._item_count += 1
        return True

    async def health_check(self) -> Tuple[bool, float]:
        """Mock health check - always returns healthy."""
        return True, 0.1

    def _generate_user_features(self) -> np.ndarray:
        """Generate random user features."""
        return np.random.randn(self._user_dim).astype(np.float32)

    def _generate_item_features(self) -> np.ndarray:
        """Generate random item features."""
        return np.random.randn(self._item_dim).astype(np.float32)

    def get_metrics(self) -> Dict[str, Any]:
        """Get mock store metrics."""
        return {
            "total_users": self._user_count,
            "total_items": self._item_count,
            "cache_hit_rate": 1.0,
            "average_latency_ms": 0.1,
        }

    async def record_interaction(
        self,
        user_id: str,
        item_id: str,
        event_type: str,
        timestamp: datetime,
        value: Optional[float] = None
    ) -> None:
        """
        Record a user interaction for feature computation.
        
        This is KEY to making the system dynamic!
        """
        if user_id not in self._user_interactions:
            self._user_interactions[user_id] = []
            self._user_stats[user_id] = {
                "click_count": 0,
                "view_count": 0,
                "purchase_count": 0,
                "like_count": 0,
                "recent_items": [],
                "interacted_items": set(),
                "first_seen": timestamp,
                "last_seen": timestamp
            }
        
        # Add interaction
        interaction = {
            "item_id": item_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "value": value
        }
        self._user_interactions[user_id].append(interaction)
        
        # Update stats
        stats = self._user_stats[user_id]
        stats["last_seen"] = timestamp
        stats["interacted_items"].add(item_id)
        
        # Update event type counters
        event_key = f"{event_type}_count"
        if event_key in stats:
            stats[event_key] += 1
        
        # Keep recent itemsmaximum 20)
        if item_id not in stats["recent_items"]:
            stats["recent_items"].append(item_id)
            if len(stats["recent_items"]) > 20:
                stats["recent_items"].pop(0)
        
        logger.info(
            "interaction_recorded",
            user_id=user_id,
            item_id=item_id,
            event_type=event_type,
            total_interactions=len(self._user_interactions[user_id])
        )

    def compute_user_features(self, user_id: str) -> np.ndarray:
        """
        Compute user features from interactions (DYNAMIC FEATURE ENGINEERING).
        
        This creates a feature vector from user behavior patterns.
        """
        if user_id not in self._user_stats:
            # New user - return zero features
            return np.zeros(self._user_dim, dtype=np.float32)
        
        stats = self._user_stats[user_id]
        interactions = self._user_interactions.get(user_id, [])
        
        # Build feature vector dynamically
        features = []
        
        # 1. Interaction counts (normalized)
        features.append(min(stats["click_count"] / 100.0, 1.0))
        features.append(min(stats["view_count"] / 100.0, 1.0))
        features.append(min(stats["purchase_count"] / 50.0, 1.0))
        features.append(min(stats["like_count"] / 50.0, 1.0))
        
        # 2. Activity level
        total_interactions = len(interactions)
        features.append(min(total_interactions / 100.0, 1.0))
        
        # 3. Diversity of items
        unique_items = len(stats["interacted_items"])
        features.append(min(unique_items / 50.0, 1.0))
        
        # 4. Recency features
        if interactions:
            # Ensure both datetimes are offset-naive for comparison
            last_seen = stats["last_seen"]
            if hasattr(last_seen, 'tzinfo') and last_seen.tzinfo is not None:
                # Convert offset-aware to offset-naive UTC
                last_seen = last_seen.replace(tzinfo=None)
            
            time_since_last = (datetime.utcnow() - last_seen).total_seconds()
            recency_score = np.exp(-time_since_last / 3600.0)  # Decay over hours
            features.append(float(recency_score))
        else:
            features.append(0.0)
        
        # 5. Engagement rate
        if total_interactions > 0:
            engagement = (stats["click_count"] + stats["purchase_count"]) / total_interactions
            features.append(float(engagement))
        else:
            features.append(0.0)
        
        # 6. Recent item embeddings (simplified - use item IDs as pseudo-embeddings)
        recent_items = stats["recent_items"][-5:]  # Last 5 items
        item_embeddings = []
        for item in recent_items:
            # Use hash of item_id as pseudo-embedding
            item_hash = hash(item) % 1000000
            item_embeddings.append(item_hash / 1000000.0)
        
        # Pad to 5 items
        while len(item_embeddings) < 5:
            item_embeddings.append(0.0)
        features.extend(item_embeddings[:5])
        
        # 7. Category preferences (simplified - use item prefixes)
        category_counts = {}
        for item in stats["interacted_items"]:
            prefix = item.split('_')[0] if '_' in item else 'unknown'
            category_counts[prefix] = category_counts.get(prefix, 0) + 1
        
        # Top 3 category preferences
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        for i in range(3):
            if i < len(sorted_categories):
                features.append(sorted_categories[i][1] / total_interactions if total_interactions > 0 else 0.0)
            else:
                features.append(0.0)
        
        # 8. Time-based features
        if interactions:
            # Ensure both datetimes are offset-naive for comparison
            first_seen = stats["first_seen"]
            last_seen = stats["last_seen"]
            
            if hasattr(first_seen, 'tzinfo') and first_seen.tzinfo is not None:
                first_seen = first_seen.replace(tzinfo=None)
            if hasattr(last_seen, 'tzinfo') and last_seen.tzinfo is not None:
                last_seen = last_seen.replace(tzinfo=None)
            
            time_range = (last_seen - first_seen).total_seconds()
            features.append(min(time_range / (7 * 24 * 3600.0), 1.0))  # Weeks active
        else:
            features.append(0.0)
        
        # 9. Fill remaining dimensions with aggregated stats
        while len(features) < self._user_dim:
            # Add some variety based on user behavior
            if total_interactions > 0:
                features.append(np.random.randn() * 0.1 + stats["click_count"] / 100.0)
            else:
                features.append(0.0)
        
        feature_vector = np.array(features[:self._user_dim], dtype=np.float32)
        
        logger.debug(
            "user_features_computed",
            user_id=user_id,
            interactions=total_interactions,
            feature_norm=float(np.linalg.norm(feature_vector))
        )
        
        return feature_vector


class FeatureStoreService:
    """
    High-level feature store service with caching and consistency.

    This service wraps the backend feature store with:
    - Automatic caching layer
    - Feature transformation
    - Metrics collection
    - Fallback handling

    It ensures consistent feature access patterns across the application
    and provides observability into feature store performance.
    """

    def __init__(self, backend: Optional[FeatureStoreBackend] = None):
        """
        Initialize feature store service.

        Args:
            backend: Feature store backend implementation
        """
        self._backend = backend or self._create_default_backend()
        self._cache: Dict[str, tuple] = {}  # (features, timestamp)
        self._cache_ttl = timedelta(seconds=300)  # 5 minute cache

    def _create_default_backend(self) -> FeatureStoreBackend:
        """Create default backend based on configuration."""
        if settings.feature_store_type == "redis":
            try:
                backend = RedisFeatureStore()
                # Test connection
                import redis
                test_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0
                )
                test_client.ping()
                test_client.close()
                logger.info("redis_feature_store_connected")
                return backend
            except Exception as e:
                logger.warning(
                    "redis_connection_failed_fallback_to_mock",
                    error=str(e)
                )
                return MockFeatureStore()
        else:
            logger.info("using_mock_feature_store")
            return MockFeatureStore()

    async def get_online_features(
        self,
        entity_type: str,
        entity_id: str,
        feature_names: Optional[List[str]] = None,
    ) -> Optional[np.ndarray]:
        """
        Get online features for an entity.

        This is the primary interface for feature retrieval during inference.

        Args:
            entity_type: Type of entity ('user' or 'item')
            entity_id: Entity identifier
            feature_names: Specific features to retrieve (None for all)

        Returns:
            Feature vector or None if not found
        """
        # Check cache first
        cache_key = f"{entity_type}:{entity_id}"
        if cache_key in self._cache:
            features, timestamp = self._cache[cache_key]
            if datetime.utcnow() - timestamp < self._cache_ttl:
                return features

        # Get from backend
        if entity_type == "user":
            features = await self._backend.get_user_features(entity_id)
        elif entity_type == "item":
            features = await self._backend.get_item_features(entity_id)
        else:
            logger.error("unknown_entity_type", entity_type=entity_type)
            return None

        # Update cache
        if features is not None:
            self._cache[cache_key] = (features, datetime.utcnow())

        return features

    async def get_user_features(self, user_id: str) -> Optional[np.ndarray]:
        """Get user features."""
        return await self.get_online_features("user", user_id)

    async def get_item_features(self, item_id: str) -> Optional[np.ndarray]:
        """Get item features."""
        return await self.get_online_features("item", item_id)

    async def get_user_features_batch(
        self, user_ids: List[str]
    ) -> Dict[str, Optional[np.ndarray]]:
        """Get features for multiple users."""
        return await self._backend.get_user_features_batch(user_ids)

    async def get_item_features_batch(self, item_ids: List[str]) -> np.ndarray:
        """Get features for multiple items."""
        return await self._backend.get_item_features_batch(item_ids)

    async def write_features(
        self,
        entity_type: str,
        entity_id: str,
        features: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Write features to the store.

        This is used by the training pipeline to materialize features
        and by real-time feature computation jobs.
        """
        if entity_type == "user":
            result = await self._backend.write_user_features(
                entity_id, features, timestamp
            )
        elif entity_type == "item":
            result = await self._backend.write_item_features(
                entity_id, features, timestamp
            )
        else:
            return False

        # Invalidate cache
        cache_key = f"{entity_type}:{entity_id}"
        self._cache.pop(cache_key, None)

        return result

    async def update_user_features_from_event(
        self,
        user_id: str,
        item_id: str,
        event_type: str,
        timestamp: Optional[datetime] = None,
        value: Optional[float] = None
    ) -> bool:
        """
        Update user features based on interaction event.
        
        This is THE KEY METHOD that connects events to features!
        It records the interaction and recomputes user features dynamically.
        
        Args:
            user_id: User identifier
            item_id: Item identifier
            event_type: Type of event (click, view, purchase, like, dislike, share)
            timestamp: Event timestamp (default: now)
            value: Optional event value (e.g., rating, purchase amount)
            
        Returns:
            True if update successful
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Only MockFeatureStore supports record_interaction currently
            if isinstance(self._backend, MockFeatureStore):
                # Record the interaction
                await self._backend.record_interaction(
                    user_id=user_id,
                    item_id=item_id,
                    event_type=event_type,
                    timestamp=timestamp,
                    value=value
                )
                
                # Recompute user features
                new_features = self._backend.compute_user_features(user_id)
                
                # Write updated features to store
                await self._backend.write_user_features(user_id, new_features, timestamp)
                
                # Invalidate cache so next retrieval gets fresh features
                cache_key = f"user:{user_id}"
                self._cache.pop(cache_key, None)
                
                logger.info(
                    "user_features_updated_from_event",
                    user_id=user_id,
                    item_id=item_id,
                    event_type=event_type,
                    feature_norm=float(np.linalg.norm(new_features))
                )
                
                return True
            else:
                # For RedisFeatureStore, we'd implement similar logic
                # For now, log that it's not supported
                logger.warning(
                    "event_based_feature_update_not_supported",
                    backend_type=type(self._backend).__name__
                )
                return False
                
        except Exception as e:
            logger.error(
                "feature_update_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check feature store health."""
        healthy, latency = await self._backend.health_check()
        return {
            "healthy": healthy,
            "latency_ms": latency,
            "backend_type": type(self._backend).__name__,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get feature store metrics."""
        backend_metrics = self._backend.get_metrics()
        return {
            **backend_metrics,
            "cache_size": len(self._cache),
        }


# Global service instance
_feature_store_service: Optional[FeatureStoreService] = None


def get_feature_store_service() -> FeatureStoreService:
    """Get or create global feature store service."""
    global _feature_store_service
    if _feature_store_service is None:
        _feature_store_service = FeatureStoreService()
    return _feature_store_service
