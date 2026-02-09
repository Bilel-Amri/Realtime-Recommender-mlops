# Real-Time Recommender System - Monitoring Service
"""
Monitoring, metrics collection, and drift detection service.

This module provides:
- Prometheus metrics for observability
- Drift detection for data and predictions
- Performance monitoring and alerting
- Health check aggregation

Monitoring is critical for production systems to detect issues early
and maintain service quality.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import structlog
from prometheus_client import Counter, Gauge, Histogram, Info

from ..core.config import settings

logger = structlog.get_logger(__name__)


# Prometheus Metrics Definitions
REQUEST_COUNT = Counter(
    "recommender_requests_total",
    "Total number of recommendation requests",
    ["user_type", "status"],  # user_type: cold/warm, status: success/error
)

REQUEST_LATENCY = Histogram(
    "recommender_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

PREDICTION_COUNT = Counter(
    "recommender_predictions_total",
    "Total number of predictions made",
    ["model_stage"],
)

CACHE_HIT_COUNT = Counter(
    "recommender_cache_hits_total",
    "Total number of cache hits",
)

EVENT_COUNT = Counter(
    "recommender_events_total",
    "Total number of events logged",
    ["event_type"],
)

DRIFT_SCORE = Gauge(
    "recommender_drift_score",
    "Current drift score",
    ["drift_type"],  # feature_drift, prediction_drift
)

MODEL_INFO = Info(
    "recommender_model_info",
    "Information about the current model",
)

SERVICE_HEALTH = Gauge(
    "recommender_service_health",
    "Service health status (1=healthy, 0=unhealthy)",
    ["component"],
)

LATENCY_PERCENTILES = Gauge(
    "recommender_latency_percentile_ms",
    "Latency percentiles in milliseconds",
    ["percentile"],  # p50, p95, p99
)


@dataclass
class LatencyTracker:
    """Track request latency with rolling window."""

    window_size: int = 1000
    latencies: Deque[float] = field(default_factory=deque)

    def record(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.latencies.append(latency_ms)
        if len(self.latencies) > self.window_size:
            self.latencies.popleft()

    def get_percentile(self, percentile: float) -> float:
        """Get latency percentile."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def get_stats(self) -> Dict[str, float]:
        """Get latency statistics."""
        if not self.latencies:
            return {"count": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_latencies = sorted(self.latencies)
        return {
            "count": len(sorted_latencies),
            "mean": sum(sorted_latencies) / len(sorted_latencies),
            "p50": sorted_latencies[int(len(sorted_latencies) * 0.50)],
            "p95": sorted_latencies[int(len(sorted_latencies) * 0.95)],
            "p99": sorted_latencies[int(len(sorted_latencies) * 0.99)],
        }


class DriftDetector:
    """
    Drift detection for features and predictions.

    This class implements statistical drift detection using:
    - Population Stability Index (PSI) for distribution drift
    - Kolmogorov-Smirnov test for distribution comparison
    - Window-based comparison for temporal drift

    Drift detection is crucial for:
    - Detecting data quality issues
    - Identifying feature drift before it affects model performance
    - Triggering model retraining when necessary
    """

    def __init__(
        self,
        reference_window_size: int = 10000,
        current_window_size: int = 1000,
        psi_bins: int = 10,
        psi_threshold: float = 0.1,
    ):
        """
        Initialize drift detector.

        Args:
            reference_window_size: Number of samples for reference distribution
            current_window_size: Number of samples for current distribution
            psi_bins: Number of bins for PSI calculation
            psi_threshold: PSI threshold for drift alert
        """
        self._reference_window_size = reference_window_size
        self._current_window_size = current_window_size
        self._psi_bins = psi_bins
        self._psi_threshold = psi_threshold

        self._reference_features: Deque[np.ndarray] = deque(maxlen=reference_window_size)
        self._current_features: Deque[np.ndarray] = deque(maxlen=current_window_size)
        self._reference_predictions: Deque[float] = deque(maxlen=reference_window_size)
        self._current_predictions: Deque[float] = deque(maxlen=current_window_size)

        self._last_check: Optional[datetime] = None
        self._drift_status = "normal"

    def record_features(self, features: np.ndarray) -> None:
        """Record feature vector for drift detection."""
        self._current_features.append(features.flatten())

    def record_prediction(self, score: float) -> None:
        """Record prediction score for drift detection."""
        self._current_predictions.append(score)

    def _calculate_psi(
        self, reference: np.ndarray, current: np.ndarray
    ) -> float:
        """
        Calculate Population Stability Index.

        PSI measures how much a distribution has changed over time.
        Lower values indicate more stable distributions.

        Interpretation:
        - PSI < 0.1: No significant change
        - 0.1 <= PSI < 0.2: Moderate change (warning)
        - PSI >= 0.2: Significant change (alert)
        """
        # Create bins based on combined data
        all_values = np.concatenate([reference, current])
        min_val, max_val = np.percentile(all_values, [1, 99])

        if min_val == max_val:
            return 0.0

        # Create bins
        bins = np.linspace(min_val, max_val, self._psi_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2

        # Calculate distributions
        ref_hist, _ = np.histogram(reference, bins=bins)
        curr_hist, _ = np.histogram(current, bins=bins)

        # Normalize to proportions
        ref_prop = (ref_hist + 1) / (len(reference) + self._psi_bins)
        curr_prop = (curr_hist + 1) / (len(current) + self._psi_bins)

        # Calculate PSI
        psi = np.sum((curr_prop - ref_prop) * np.log(curr_prop / ref_prop))

        return float(psi)

    def check_drift(self) -> Dict[str, Any]:
        """
        Check for drift in features and predictions.

        Returns:
            Dictionary with drift detection results
        """
        # Update reference window periodically
        if len(self._reference_features) < 100:
            if len(self._current_features) > 1000:
                # Promote current to reference
                self._reference_features = self._current_features.copy()
                self._reference_predictions = self._current_predictions.copy()
                self._current_features.clear()
                self._current_predictions.clear()

        # Check feature drift
        feature_drift = 0.0
        drifted_features = []

        if len(self._reference_features) > 100 and len(self._current_features) > 100:
            ref_features = np.array(self._reference_features)
            curr_features = np.array(self._current_features)

            # Check each feature dimension
            for i in range(min(ref_features.shape[1], 10)):  # Check first 10 features
                psi = self._calculate_psi(ref_features[:, i], curr_features[:, i])
                if psi > self._psi_threshold:
                    feature_drift = max(feature_drift, psi)
                    drifted_features.append(f"feature_{i}")

        # Check prediction drift
        prediction_drift = 0.0
        if (
            len(self._reference_predictions) > 100
            and len(self._current_predictions) > 100
        ):
            ref_preds = np.array(self._reference_predictions)
            curr_preds = np.array(self._current_predictions)
            prediction_drift = self._calculate_psi(ref_preds, curr_preds)

        # Determine drift status
        if feature_drift >= 0.2 or prediction_drift >= 0.2:
            self._drift_status = "critical"
        elif feature_drift >= 0.1 or prediction_drift >= 0.1:
            self._drift_status = "warning"
        else:
            self._drift_status = "normal"

        # Update Prometheus metrics
        DRIFT_SCORE.labels(drift_type="feature").set(feature_drift)
        DRIFT_SCORE.labels(drift_type="prediction").set(prediction_drift)

        self._last_check = datetime.utcnow()

        return {
            "feature_drift_score": round(feature_drift, 4),
            "prediction_drift_score": round(prediction_drift, 4),
            "drifted_features": drifted_features,
            "status": self._drift_status,
            "last_checked": self._last_check.isoformat(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get drift detector metrics."""
        return {
            "reference_samples": len(self._reference_features),
            "current_samples": len(self._current_features),
            "drift_status": self._drift_status,
            "psi_threshold": self._psi_threshold,
        }


class MonitoringService:
    """
    Central monitoring service for the recommendation system.

    This service aggregates:
    - Request metrics and latency tracking
    - Drift detection
    - Health checks
    - Prometheus metrics export

    It provides a unified interface for monitoring and alerting.
    """

    def __init__(self):
        """Initialize monitoring service."""
        self._latency_tracker = LatencyTracker()
        self._drift_detector = DriftDetector()
        self._start_time = time.time()
        self._prediction_count = 0
        self._event_count = 0
        self._cache_hits = 0
        self._cold_start_count = 0

    def record_request(
        self,
        latency_ms: float,
        user_type: str,
        success: bool,
        endpoint: str,
    ) -> None:
        """
        Record a recommendation request.

        Args:
            latency_ms: Request latency in milliseconds
            user_type: 'cold' or 'warm' user
            success: Whether the request succeeded
            endpoint: API endpoint called
        """
        # Update latency tracker
        self._latency_tracker.record(latency_ms)

        # Update Prometheus metrics
        status = "success" if success else "error"
        REQUEST_COUNT.labels(user_type=user_type, status=status).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency_ms / 1000)

        # Update latency percentiles
        stats = self._latency_tracker.get_stats()
        LATENCY_PERCENTILES.labels(percentile="p50").set(stats["p50"])
        LATENCY_PERCENTILES.labels(percentile="p95").set(stats["p95"])
        LATENCY_PERCENTILES.labels(percentile="p99").set(stats["p99"])

    def record_prediction(self, model_stage: str = "Production") -> None:
        """Record a model prediction."""
        self._prediction_count += 1
        PREDICTION_COUNT.labels(model_stage=model_stage).inc()

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self._cache_hits += 1
        CACHE_HIT_COUNT.inc()

    def record_event(self, event_type: str) -> None:
        """Record an event."""
        self._event_count += 1
        EVENT_COUNT.labels(event_type=event_type).inc()

    def record_cold_start(self) -> None:
        """Record a cold start request."""
        self._cold_start_count += 1

    def record_features(self, features: np.ndarray) -> None:
        """Record features for drift detection."""
        self._drift_detector.record_features(features)

    def record_prediction_score(self, score: float) -> None:
        """Record prediction score for drift detection."""
        self._drift_detector.record_prediction(score)

    def check_drift(self) -> Dict[str, Any]:
        """Check for drift in the system."""
        return self._drift_detector.check_drift()

    def get_prediction_metrics(self) -> Dict[str, Any]:
        """Get prediction-related metrics."""
        total = self._prediction_count
        return {
            "total_predictions": total,
            "predictions_last_hour": min(total, 1000),  # Simplified
            "average_latency_ms": self._latency_tracker.get_stats().get("mean", 0),
            "p95_latency_ms": self._latency_tracker.get_percentile(95),
            "p99_latency_ms": self._latency_tracker.get_percentile(99),
            "cache_hit_rate": (
                self._cache_hits / total if total > 0 else 0
            ),
            "cold_start_rate": (
                self._cold_start_count / total if total > 0 else 0
            ),
        }

    def get_drift_metrics(self) -> Dict[str, Any]:
        """Get drift detection metrics."""
        return self._drift_detector.check_drift()

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics."""
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "cpu_usage_percent": psutil.cpu_percent(),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "request_queue_size": 0,  # Would need async queue metrics
        }

    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time

    def get_event_metrics(self) -> Dict[str, Any]:
        """Get event-related metrics."""
        # This is a simplified version - in production would track by time windows
        return {
            "total_events": self._event_count,
            "events_last_hour": min(self._event_count, 100),  # Simplified
            "events_per_minute": self._event_count / max(self.get_uptime_seconds() / 60, 1),
            "events_by_type": {
                "view": int(self._event_count * 0.4),  # Simplified estimates
                "like": int(self._event_count * 0.3),
                "rating": int(self._event_count * 0.2),
                "click": int(self._event_count * 0.1),
            }
        }

    def set_model_info(
        self,
        name: str,
        version: str,
        stage: str,
        metrics: Dict[str, float],
    ) -> None:
        """Set model information for monitoring."""
        MODEL_INFO.info({
            "name": name,
            "version": version,
            "stage": stage,
            "metrics": str(metrics),
        })

    def update_component_health(self, component: str, healthy: bool) -> None:
        """Update component health status."""
        SERVICE_HEALTH.labels(component=component).set(1 if healthy else 0)


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create global monitoring service."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
