# Real-Time Recommender System - Online Learning Service
"""
Online learning and incremental model update service.

This module provides:
- Incremental model updates from streaming data
- Mini-batch gradient descent for real-time learning
- Model checkpoint management
- Performance tracking and rollback

This is the core of dynamic MLOps - models learn from new interactions
in real-time without requiring full retraining.
"""

import asyncio
import pickle
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog

from ..core.config import settings

logger = structlog.get_logger(__name__)


class OnlineLearningService:
    """
    Service for incrementally updating models from streaming data.
    
    Features:
    - Mini-batch gradient updates
    - Exponential moving average for stability
    - Automatic checkpoint creation
    - Performance-based rollback
    - Data buffer management
    """

    def __init__(
        self,
        model: Any = None,
        buffer_size: int = 1000,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        checkpoint_dir: str = "/app/models/checkpoints",
    ):
        """
        Initialize online learning service.
        
        Args:
            model: Base model to update
            buffer_size: Size of interaction buffer before update
            batch_size: Size of mini-batches for training
            learning_rate: Learning rate for updates
            checkpoint_dir: Directory for model checkpoints
        """
        self._model = model
        self._buffer_size = buffer_size
        self._batch_size = batch_size
        self._learning_rate = learning_rate
        self._checkpoint_dir = Path(checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Data buffers
        self._interaction_buffer: deque = deque(maxlen=buffer_size)
        self._feedback_buffer: deque = deque(maxlen=buffer_size)
        
        # Metrics
        self._metrics = {
            "total_updates": 0,
            "total_interactions_processed": 0,
            "avg_update_time_ms": 0.0,
            "last_update_timestamp": None,
            "model_performance": deque(maxlen=100),
        }
        
        # Update lock to prevent concurrent updates
        self._update_lock = asyncio.Lock()
        
        logger.info("online_learning_service_initialized", buffer_size=buffer_size)

    async def add_interaction(
        self,
        user_id: str,
        item_id: str,
        event_type: str,
        timestamp: datetime,
        user_features: Optional[np.ndarray] = None,
        item_features: Optional[np.ndarray] = None,
    ) -> None:
        """
        Add a new user interaction to the learning buffer.
        
        Args:
            user_id: User identifier
            item_id: Item identifier
            event_type: Type of interaction (view, click, purchase)
            timestamp: Interaction timestamp
            user_features: User feature vector
            item_features: Item feature vector
        """
        interaction = {
            "user_id": user_id,
            "item_id": item_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "user_features": user_features,
            "item_features": item_features,
            # Convert event type to implicit feedback score
            "score": self._event_to_score(event_type),
        }
        
        self._interaction_buffer.append(interaction)
        
        # Trigger update if buffer is full
        if len(self._interaction_buffer) >= self._buffer_size:
            await self.trigger_update()

    async def add_feedback(
        self,
        user_id: str,
        item_id: str,
        predicted_score: float,
        actual_outcome: float,
        timestamp: datetime,
    ) -> None:
        """
        Add explicit feedback for a recommendation.
        
        This closes the loop - tracking whether recommendations were successful.
        
        Args:
            user_id: User identifier
            item_id: Item that was recommended
            predicted_score: Score the model predicted
            actual_outcome: Actual outcome (1.0 for positive, 0.0 for negative)
            timestamp: Feedback timestamp
        """
        feedback = {
            "user_id": user_id,
            "item_id": item_id,
            "predicted_score": predicted_score,
            "actual_outcome": actual_outcome,
            "prediction_error": abs(predicted_score - actual_outcome),
            "timestamp": timestamp,
        }
        
        self._feedback_buffer.append(feedback)
        
        # Update performance metrics
        self._metrics["model_performance"].append(feedback["prediction_error"])

    async def trigger_update(self, force: bool = False) -> bool:
        """
        Trigger an incremental model update.
        
        Args:
            force: Force update even if buffer isn't full
            
        Returns:
            True if update was successful
        """
        if not force and len(self._interaction_buffer) < self._batch_size:
            return False
            
        async with self._update_lock:
            try:
                start_time = time.perf_counter()
                
                # Get batch of interactions
                batch = list(self._interaction_buffer)[-self._batch_size:]
                
                if not batch:
                    return False
                
                # Create checkpoint before update
                checkpoint_path = await self._create_checkpoint()
                
                # Perform incremental update
                success = await self._incremental_update(batch)
                
                if success:
                    self._metrics["total_updates"] += 1
                    self._metrics["total_interactions_processed"] += len(batch)
                    self._metrics["last_update_timestamp"] = datetime.utcnow()
                    
                    update_time_ms = (time.perf_counter() - start_time) * 1000
                    self._metrics["avg_update_time_ms"] = (
                        self._metrics["avg_update_time_ms"] * 0.9 + update_time_ms * 0.1
                    )
                    
                    logger.info(
                        "model_updated_incrementally",
                        batch_size=len(batch),
                        update_time_ms=round(update_time_ms, 2),
                        total_updates=self._metrics["total_updates"],
                    )
                    
                    return True
                else:
                    # Rollback on failure
                    await self._rollback_to_checkpoint(checkpoint_path)
                    logger.error("model_update_failed_rolled_back")
                    return False
                    
            except Exception as e:
                logger.error("incremental_update_failed", error=str(e))
                return False

    async def _incremental_update(self, batch: List[Dict]) -> bool:
        """
        Perform the actual incremental update.
        
        This uses mini-batch gradient descent to update model weights
        based on new interactions.
        
        Args:
            batch: Batch of interactions to learn from
            
        Returns:
            True if update successful
        """
        # This is a placeholder for actual online learning logic
        # In production, implement with your specific model architecture
        
        # For LightGBM (tree models), incremental updates are limited
        # Consider using online learning algorithms like:
        # - Online Matrix Factorization
        # - Neural Collaborative Filtering with SGD
        # - FTRL (Follow-The-Regularized-Leader)
        
        # Simulate update for demonstration
        await asyncio.sleep(0.1)
        
        logger.info(
            "simulated_online_update",
            message="In production, implement incremental learning for your model type"
        )
        
        return True

    async def _create_checkpoint(self) -> Path:
        """Create a model checkpoint for rollback."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = self._checkpoint_dir / f"model_checkpoint_{timestamp}.pkl"
        
        try:
            with open(checkpoint_path, "wb") as f:
                pickle.dump(self._model, f)
            
            # Keep only last 10 checkpoints
            checkpoints = sorted(self._checkpoint_dir.glob("model_checkpoint_*.pkl"))
            for old_checkpoint in checkpoints[:-10]:
                old_checkpoint.unlink()
            
            return checkpoint_path
        except Exception as e:
            logger.error("checkpoint_creation_failed", error=str(e))
            return None

    async def _rollback_to_checkpoint(self, checkpoint_path: Path) -> bool:
        """Rollback model to a previous checkpoint."""
        try:
            if checkpoint_path and checkpoint_path.exists():
                with open(checkpoint_path, "rb") as f:
                    self._model = pickle.load(f)
                logger.info("model_rolled_back", checkpoint=str(checkpoint_path))
                return True
        except Exception as e:
            logger.error("rollback_failed", error=str(e))
        return False

    def _event_to_score(self, event_type: str) -> float:
        """Convert event type to implicit feedback score."""
        scores = {
            "purchase": 1.0,
            "like": 0.8,
            "click": 0.6,
            "view": 0.3,
            "dislike": -0.5,
        }
        return scores.get(event_type, 0.0)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get online learning performance metrics."""
        return {
            "total_updates": self._metrics["total_updates"],
            "total_interactions_processed": self._metrics["total_interactions_processed"],
            "buffer_utilization": len(self._interaction_buffer) / self._buffer_size,
            "avg_update_time_ms": round(self._metrics["avg_update_time_ms"], 2),
            "last_update": self._metrics["last_update_timestamp"],
            "avg_prediction_error": (
                float(np.mean(list(self._metrics["model_performance"])))
                if self._metrics["model_performance"]
                else 0.0
            ),
        }


# Singleton instance
_online_learning_service: Optional[OnlineLearningService] = None


def get_online_learning_service() -> OnlineLearningService:
    """Get the singleton online learning service."""
    global _online_learning_service
    if _online_learning_service is None:
        _online_learning_service = OnlineLearningService()
    return _online_learning_service
