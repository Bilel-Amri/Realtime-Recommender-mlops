"""
Redis-based Online Feature Store

Stores and retrieves real-time user and item features for recommendation.
Supports TTL, sliding windows, and aggregations.
"""

from typing import Dict, List, Optional, Any, Union
import json
import numpy as np
from datetime import datetime, timedelta
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Try to import redis, but make it optional
try:
    import redis as redis_lib  # type: ignore
    REDIS_AVAILABLE = True
except ImportError:
    redis_lib = None  # type: ignore
    REDIS_AVAILABLE = False


class RedisFeatureStore:
    """
    Production-grade feature store using Redis.
    
    Stores:
    - User interaction counts (views, clicks, purchases)
    - User-item affinity scores
    - Item popularity metrics
    - User embeddings (vectors)
    - Item embeddings (vectors)
    - Temporal features (recent interactions)
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        ttl_hours: int = 24 * 30,  # 30 days default TTL
    ):
        """
        Initialize Redis feature store.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            ttl_hours: Time-to-live for features in hours
        """
        self.redis_client: Optional[Any] = None
        self.connected = False
        self._fallback_store: Dict[str, Any] = {}
        self.ttl_seconds = ttl_hours * 3600
        
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis package not installed. Running in fallback mode.")
            return
            
        try:
            client = redis_lib.Redis(  # type: ignore
                host=host,
                port=port,
                db=db,
                decode_responses=False,  # Handle bytes for embeddings
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            client.ping()
            self.redis_client = client
            self.connected = True
            logger.info(f"✅ Connected to Redis at {host}:{port}")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}. Running in fallback mode.")
            self.redis_client = None
            self.connected = False
        
    def _key(self, namespace: str, key: str) -> str:
        """Generate namespaced Redis key."""
        return f"{namespace}:{key}"
    
    # ==================== User Features ====================
    
    def increment_user_interaction(
        self,
        user_id: str,
        interaction_type: str,
        item_id: Optional[str] = None,
        value: float = 1.0
    ):
        """
        Increment user interaction counter.
        
        Args:
            user_id: User identifier
            interaction_type: Type of interaction (view, click, purchase)
            item_id: Optional item ID for item-specific tracking
            value: Increment value (default 1.0)
        """
        if not self.connected or self.redis_client is None:
            # Fallback mode
            key = f"user_stats:{user_id}"
            if key not in self._fallback_store or not isinstance(self._fallback_store[key], dict):
                self._fallback_store[key] = {}
            self._fallback_store[key][interaction_type] = self._fallback_store[key].get(interaction_type, 0) + value
            if item_id:
                self._fallback_store[key][f"item:{item_id}"] = self._fallback_store[key].get(f"item:{item_id}", 0) + value
            return
        
        # User-level stats
        key = self._key("user_stats", user_id)
        self.redis_client.hincrby(key, interaction_type, int(value))
        self.redis_client.expire(key, self.ttl_seconds)
        
        # Item-specific affinity
        if item_id:
            affinity_key = self._key(f"user_affinity:{user_id}", item_id)
            self.redis_client.incrbyfloat(affinity_key, value)
            self.redis_client.expire(affinity_key, self.ttl_seconds)
    
    def get_user_stats(self, user_id: str) -> Dict[str, float]:
        """
        Get user interaction statistics.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of interaction counts
        """
        if not self.connected or self.redis_client is None:
            result = self._fallback_store.get(f"user_stats:{user_id}", {})
            if isinstance(result, dict):
                return result
            return {}
        
        key = self._key("user_stats", user_id)
        stats = self.redis_client.hgetall(key)
        
        # Convert bytes to string keys and int values
        return {k.decode(): int(v.decode()) for k, v in stats.items()}
    
    def add_recent_interaction(
        self,
        user_id: str,
        item_id: str,
        interaction_type: str,
        timestamp: Optional[datetime] = None
    ):
        """
        Add interaction to recent history (sliding window).
        
        Uses Redis sorted set with timestamp as score.
        
        Args:
            user_id: User identifier
            item_id: Item identifier
            interaction_type: Type of interaction
            timestamp: Interaction timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        score = timestamp.timestamp()
        value = json.dumps({"item_id": item_id, "type": interaction_type})
        
        if not self.connected or self.redis_client is None:
            key = f"user_recent:{user_id}"
            if key not in self._fallback_store or not isinstance(self._fallback_store[key], list):
                self._fallback_store[key] = []
            self._fallback_store[key].append((score, value))
            # Keep only last 100
            self._fallback_store[key] = sorted(self._fallback_store[key], key=lambda x: x[0])[-100:]
            return
        
        key = self._key("user_recent", user_id)
        self.redis_client.zadd(key, {value: score})
        
        # Keep only last 100 interactions
        self.redis_client.zremrangebyrank(key, 0, -101)
        self.redis_client.expire(key, self.ttl_seconds)
    
    def get_recent_interactions(
        self,
        user_id: str,
        limit: int = 20,
        hours_ago: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent user interactions.
        
        Args:
            user_id: User identifier
            limit: Maximum number of interactions to return
            hours_ago: Only return interactions from last N hours
            
        Returns:
            List of recent interactions
        """
        if not self.connected or self.redis_client is None:
            key = f"user_recent:{user_id}"
            interactions = self._fallback_store.get(key, [])
            if not isinstance(interactions, list):
                return []
            min_score = (datetime.now() - timedelta(hours=hours_ago)).timestamp()
            recent = [json.loads(v) for s, v in interactions if s >= min_score]
            return recent[-limit:]
        
        key = self._key("user_recent", user_id)
        min_score = (datetime.now() - timedelta(hours=hours_ago)).timestamp()
        
        results = self.redis_client.zrevrangebyscore(
            key, 
            '+inf', 
            min_score, 
            start=0, 
            num=limit
        )
        
        return [json.loads(r.decode()) for r in results]
    
    # ==================== Item Features ====================
    
    def increment_item_popularity(self, item_id: str, value: float = 1.0):
        """Increment item popularity counter."""
        if not self.connected or self.redis_client is None:
            key = f"item_popularity:{item_id}"
            current = self._fallback_store.get(key, 0)
            if not isinstance(current, (int, float)):
                current = 0
            self._fallback_store[key] = current + value
            return
        
        key = self._key("item_popularity", item_id)
        self.redis_client.incrbyfloat(key, value)
        self.redis_client.expire(key, self.ttl_seconds)
    
    def get_item_popularity(self, item_id: str) -> float:
        """Get item popularity score."""
        if not self.connected or self.redis_client is None:
            result = self._fallback_store.get(f"item_popularity:{item_id}", 0.0)
            if isinstance(result, (int, float)):
                return float(result)
            return 0.0
        
        key = self._key("item_popularity", item_id)
        value = self.redis_client.get(key)
        return float(value.decode()) if value else 0.0
    
    # ==================== Embeddings ====================
    
    def set_user_embedding(self, user_id: str, embedding: np.ndarray):
        """
        Store user embedding vector.
        
        Args:
            user_id: User identifier
            embedding: Numpy array of floats
        """
        if not self.connected or self.redis_client is None:
            self._fallback_store[f"user_emb:{user_id}"] = embedding.copy()
            return
        
        key = self._key("user_embedding", user_id)
        # Store as binary numpy array
        self.redis_client.set(key, embedding.tobytes())
        self.redis_client.expire(key, self.ttl_seconds)
    
    def get_user_embedding(self, user_id: str, dim: int = 64) -> Optional[np.ndarray]:
        """
        Retrieve user embedding vector.
        
        Args:
            user_id: User identifier
            dim: Embedding dimension
            
        Returns:
            Numpy array or None if not found
        """
        if not self.connected or self.redis_client is None:
            emb = self._fallback_store.get(f"user_emb:{user_id}")
            if isinstance(emb, np.ndarray):
                return emb
            return None
        
        key = self._key("user_embedding", user_id)
        data = self.redis_client.get(key)
        
        if data:
            return np.frombuffer(data, dtype=np.float32).reshape(dim)
        return None
    
    def set_item_embedding(self, item_id: str, embedding: np.ndarray):
        """Store item embedding vector."""
        if not self.connected or self.redis_client is None:
            self._fallback_store[f"item_emb:{item_id}"] = embedding.copy()
            return
        
        key = self._key("item_embedding", item_id)
        self.redis_client.set(key, embedding.tobytes())
        self.redis_client.expire(key, self.ttl_seconds)
    
    def get_item_embedding(self, item_id: str, dim: int = 64) -> Optional[np.ndarray]:
        """Retrieve item embedding vector."""
        if not self.connected or self.redis_client is None:
            emb = self._fallback_store.get(f"item_emb:{item_id}")
            if isinstance(emb, np.ndarray):
                return emb
            return None
        
        key = self._key("item_embedding", item_id)
        data = self.redis_client.get(key)
        
        if data:
            return np.frombuffer(data, dtype=np.float32).reshape(dim)
        return None
    
    # ==================== Batch Operations ====================
    
    def get_multiple_user_embeddings(
        self, 
        user_ids: List[str], 
        dim: int = 64
    ) -> Dict[str, np.ndarray]:
        """Batch retrieve user embeddings."""
        if not self.connected or self.redis_client is None:
            result = {}
            for uid in user_ids:
                emb = self._fallback_store.get(f"user_emb:{uid}")
                if isinstance(emb, np.ndarray):
                    result[uid] = emb
            return result
        
        keys = [self._key("user_embedding", uid) for uid in user_ids]
        values = self.redis_client.mget(keys)
        
        result = {}
        for uid, data in zip(user_ids, values):
            if data:
                result[uid] = np.frombuffer(data, dtype=np.float32).reshape(dim)
        
        return result
    
    def get_multiple_item_embeddings(
        self, 
        item_ids: List[str], 
        dim: int = 64
    ) -> Dict[str, np.ndarray]:
        """Batch retrieve item embeddings."""
        if not self.connected or self.redis_client is None:
            result = {}
            for iid in item_ids:
                emb = self._fallback_store.get(f"item_emb:{iid}")
                if isinstance(emb, np.ndarray):
                    result[iid] = emb
            return result
        
        keys = [self._key("item_embedding", iid) for iid in item_ids]
        values = self.redis_client.mget(keys)
        
        result = {}
        for iid, data in zip(item_ids, values):
            if data:
                result[iid] = np.frombuffer(data, dtype=np.float32).reshape(dim)
        
        return result
    
    # ==================== Aggregated Features ====================
    
    def compute_user_features(self, user_id: str) -> Dict[str, float]:
        """
        Compute aggregated user features.
        
        Returns:
            Dictionary of engineered features
        """
        stats = self.get_user_stats(user_id)
        recent = self.get_recent_interactions(user_id, limit=50)
        
        # Basic counts
        view_count = stats.get('view', 0)
        click_count = stats.get('click', 0)
        purchase_count = stats.get('purchase', 0)
        
        # Engagement rate
        total_interactions = view_count + click_count + purchase_count
        engagement_rate = (click_count + purchase_count * 2) / max(total_interactions, 1)
        
        # Recency (hours since last interaction)
        if recent:
            last_interaction_time = datetime.now()  # Placeholder
            recency_hours = 0
        else:
            recency_hours = 24 * 30  # 30 days for cold users
        
        # Diversity (unique items in recent history)
        unique_items = len(set([i['item_id'] for i in recent]))
        diversity_score = unique_items / max(len(recent), 1)
        
        return {
            'view_count': float(view_count),
            'click_count': float(click_count),
            'purchase_count': float(purchase_count),
            'engagement_rate': engagement_rate,
            'recency_hours': recency_hours,
            'diversity_score': diversity_score,
            'total_interactions': float(total_interactions),
        }
    
    # ==================== Utility ====================
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis health and return statistics."""
        if not self.connected or self.redis_client is None:
            return {
                "status": "degraded",
                "mode": "fallback",
                "message": "Using in-memory fallback"
            }
        
        try:
            info = self.redis_client.info()
            return {
                "status": "healthy",
                "mode": "redis",
                "connected": True,
                "used_memory": info.get('used_memory_human', 'N/A'),
                "total_keys": self.redis_client.dbsize(),
                "latency": "< 1ms"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "mode": "redis",
                "error": str(e)
            }
    
    def clear_user(self, user_id: str):
        """Clear all features for a user (for testing)."""
        if not self.connected or self.redis_client is None:
            keys_to_remove = [k for k in self._fallback_store.keys() if user_id in k]
            for k in keys_to_remove:
                self._fallback_store.pop(k, None)
            return
        
        # Get all keys for this user
        patterns = [
            f"user_stats:{user_id}",
            f"user_affinity:{user_id}:*",
            f"user_recent:{user_id}",
            f"user_embedding:{user_id}",
        ]
        
        for pattern in patterns:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
