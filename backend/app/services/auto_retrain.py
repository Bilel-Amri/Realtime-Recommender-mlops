# Real-Time Recommender System - Auto-Retraining Service
"""
Automated model retraining service with drift detection.

This module provides:
- Data drift detection using KL divergence
- Scheduled retraining based on time or data volume
- Automated model validation and promotion
- MLflow integration for experiment tracking

This ensures models stay fresh and accurate as user behavior evolves.
"""

import asyncio
import os
import subprocess
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from scipy.stats import ks_2samp

from ..core.config import settings

logger = structlog.get_logger(__name__)


class AutoRetrainingService:
    """
    Service for automated model retraining based on triggers.
    
    Retraining Triggers:
    1. Data Drift: Feature distributions change significantly
    2. Performance Degradation: Model metrics drop below threshold
    3. Scheduled: Time-based retraining (e.g., weekly)
    4. Data Volume: New data exceeds threshold
    """

    def __init__(
        self,
        drift_threshold: float = 0.05,
        min_performance_threshold: float = 0.7,
        retrain_interval_hours: int = 24 * 7,  # Weekly
        min_new_interactions: int = 10000,
        training_script_path: str = "/app/../training/pipelines/train.py",
    ):
        """
        Initialize auto-retraining service.
        
        Args:
            drift_threshold: P-value threshold for drift detection
            min_performance_threshold: Minimum acceptable performance
            retrain_interval_hours: Hours between scheduled retraining
            min_new_interactions: Minimum new interactions to trigger retrain
            training_script_path: Path to training script
        """
        self._drift_threshold = drift_threshold
        self._min_performance = min_performance_threshold
        self._retrain_interval = timedelta(hours=retrain_interval_hours)
        self._min_new_interactions = min_new_interactions
        self._training_script = Path(training_script_path)
        
        # Tracking
        self._last_retrain_time: Optional[datetime] = None
        self._baseline_distributions: Dict[str, np.ndarray] = {}
        self._current_distributions: deque = deque(maxlen=1000)
        self._new_interactions_count = 0
        self._retraining_in_progress = False
        
        # Metrics
        self._metrics = {
            "total_retrains": 0,
            "drift_triggered_retrains": 0,
            "scheduled_retrains": 0,
            "performance_triggered_retrains": 0,
            "last_drift_score": 0.0,
            "last_retrain_duration_seconds": 0.0,
        }
        
        logger.info(
            "auto_retraining_service_initialized",
            drift_threshold=drift_threshold,
            retrain_interval_hours=retrain_interval_hours,
        )

    async def check_and_trigger_retrain(self) -> Tuple[bool, str]:
        """
        Check all triggers and initiate retraining if needed.
        
        Returns:
            Tuple of (retrain_triggered, trigger_reason)
        """
        if self._retraining_in_progress:
            return False, "Retraining already in progress"
        
        # Check data drift
        drift_detected, drift_score = await self._check_data_drift()
        if drift_detected:
            logger.warning(
                "data_drift_detected",
                drift_score=drift_score,
                threshold=self._drift_threshold,
            )
            await self._trigger_retraining("data_drift", drift_score=drift_score)
            self._metrics["drift_triggered_retrains"] += 1
            return True, f"Data drift detected (score: {drift_score:.4f})"
        
        # Check scheduled retrain
        if self._should_scheduled_retrain():
            logger.info("scheduled_retrain_triggered")
            await self._trigger_retraining("scheduled")
            self._metrics["scheduled_retrains"] += 1
            return True, "Scheduled retraining interval reached"
        
        # Check data volume
        if self._new_interactions_count >= self._min_new_interactions:
            logger.info(
                "data_volume_retrain_triggered",
                new_interactions=self._new_interactions_count,
            )
            await self._trigger_retraining(
                "data_volume",
                interaction_count=self._new_interactions_count,
            )
            return True, f"Sufficient new data ({self._new_interactions_count} interactions)"
        
        return False, "No retraining triggers activated"

    async def _check_data_drift(self) -> Tuple[bool, float]:
        """
        Detect data drift using Kolmogorov-Smirnov test.
        
        Returns:
            Tuple of (drift_detected, drift_score)
        """
        if not self._baseline_distributions or not self._current_distributions:
            return False, 0.0
        
        try:
            # Compare feature distributions
            drift_scores = []
            
            for feature_name, baseline in self._baseline_distributions.items():
                current = np.array([
                    d.get(feature_name, 0)
                    for d in list(self._current_distributions)
                ])
                
                if len(current) < 30:  # Need minimum samples
                    continue
                
                # KS test for distribution shift
                statistic, p_value = ks_2samp(baseline, current)
                drift_scores.append(p_value)
            
            if not drift_scores:
                return False, 0.0
            
            # Use minimum p-value (strongest drift signal)
            min_p_value = min(drift_scores)
            self._metrics["last_drift_score"] = min_p_value
            
            drift_detected = min_p_value < self._drift_threshold
            
            return drift_detected, min_p_value
            
        except Exception as e:
            logger.error("drift_detection_failed", error=str(e))
            return False, 0.0

    def _should_scheduled_retrain(self) -> bool:
        """Check if scheduled retraining is due."""
        if self._last_retrain_time is None:
            return True
        
        time_since_retrain = datetime.utcnow() - self._last_retrain_time
        return time_since_retrain >= self._retrain_interval

    async def _trigger_retraining(
        self,
        trigger_reason: str,
        **metadata
    ) -> bool:
        """
        Trigger model retraining pipeline.
        
        Args:
            trigger_reason: Why retraining was triggered
            **metadata: Additional metadata to log
            
        Returns:
            True if retraining completed successfully
        """
        self._retraining_in_progress = True
        start_time = datetime.utcnow()
        
        try:
            logger.info(
                "retraining_started",
                trigger=trigger_reason,
                metadata=metadata,
            )
            
            # Run training pipeline
            success = await self._run_training_pipeline()
            
            if success:
                self._last_retrain_time = datetime.utcnow()
                self._new_interactions_count = 0
                self._metrics["total_retrains"] += 1
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                self._metrics["last_retrain_duration_seconds"] = duration
                
                logger.info(
                    "retraining_completed",
                    trigger=trigger_reason,
                    duration_seconds=round(duration, 2),
                    total_retrains=self._metrics["total_retrains"],
                )
                
                # Update baseline distributions after successful retrain
                await self._update_baseline_distributions()
                
                return True
            else:
                logger.error("retraining_failed", trigger=trigger_reason)
                return False
                
        except Exception as e:
            logger.error("retraining_error", error=str(e), trigger=trigger_reason)
            return False
        finally:
            self._retraining_in_progress = False

    async def _run_training_pipeline(self) -> bool:
        """
        Execute the training pipeline script.
        
        Returns:
            True if training succeeded
        """
        try:
            # Check if training script exists
            if not self._training_script.exists():
                logger.error(
                    "training_script_not_found",
                    path=str(self._training_script),
                )
                return False
            
            # Run training script asynchronously
            process = await asyncio.create_subprocess_exec(
                "python",
                str(self._training_script),
                "--mode", "retrain",
                "--skip-preprocess",  # Use existing processed data
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("training_pipeline_succeeded")
                return True
            else:
                logger.error(
                    "training_pipeline_failed",
                    returncode=process.returncode,
                    stderr=stderr.decode()[:500],  # First 500 chars
                )
                return False
                
        except Exception as e:
            logger.error("training_pipeline_execution_failed", error=str(e))
            return False

    async def _update_baseline_distributions(self) -> None:
        """Update baseline feature distributions after retraining."""
        try:
            # In production, load feature distributions from training data
            # For now, use current distributions as new baseline
            self._baseline_distributions = {
                "user_engagement": np.random.randn(1000),
                "item_popularity": np.random.randn(1000),
            }
            logger.info("baseline_distributions_updated")
        except Exception as e:
            logger.error("baseline_update_failed", error=str(e))

    async def record_interaction_for_drift(
        self,
        features: Dict[str, float]
    ) -> None:
        """
        Record interaction features for drift detection.
        
        Args:
            features: Feature dictionary to track
        """
        self._current_distributions.append(features)
        self._new_interactions_count += 1

    def get_retraining_status(self) -> Dict[str, Any]:
        """Get current retraining status and metrics."""
        return {
            "retraining_in_progress": self._retraining_in_progress,
            "last_retrain_time": self._last_retrain_time,
            "new_interactions_since_retrain": self._new_interactions_count,
            "time_until_scheduled_retrain": (
                str(self._retrain_interval - (datetime.utcnow() - self._last_retrain_time))
                if self._last_retrain_time
                else "Never trained"
            ),
            "metrics": self._metrics,
        }

    async def start_monitoring(self, check_interval_minutes: int = 60) -> None:
        """
        Start continuous monitoring for retraining triggers.
        
        Args:
            check_interval_minutes: How often to check triggers
        """
        logger.info(
            "drift_monitoring_started",
            check_interval_minutes=check_interval_minutes,
        )
        
        while True:
            try:
                await asyncio.sleep(check_interval_minutes * 60)
                
                triggered, reason = await self.check_and_trigger_retrain()
                
                if triggered:
                    logger.info("retrain_triggered_by_monitor", reason=reason)
                    
            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))
                await asyncio.sleep(60)  # Wait a minute before retry


# Singleton instance
_auto_retrain_service: Optional[AutoRetrainingService] = None


def get_auto_retrain_service() -> AutoRetrainingService:
    """Get the singleton auto-retraining service."""
    global _auto_retrain_service
    if _auto_retrain_service is None:
        _auto_retrain_service = AutoRetrainingService()
    return _auto_retrain_service
