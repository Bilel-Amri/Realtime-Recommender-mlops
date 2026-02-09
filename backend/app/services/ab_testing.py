# Real-Time Recommender System - A/B Testing Framework
"""
A/B testing and multi-armed bandit framework for model serving.

This module provides:
- Traffic splitting between model variants
- Thompson Sampling for adaptive allocation
- Conversion tracking and statistical testing
- Model champion/challenger framework

This enables safe model deployment and continuous optimization.
"""

import asyncio
import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from scipy.stats import beta, chi2_contingency

from ..core.config import settings

logger = structlog.get_logger(__name__)


class ExperimentStatus(str, Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    CONCLUDED = "concluded"


class AllocationStrategy(str, Enum):
    """Strategy for allocating traffic to variants."""
    FIXED = "fixed"  # Fixed percentage split
    THOMPSON_SAMPLING = "thompson_sampling"  # Adaptive based on performance
    EPSILON_GREEDY = "epsilon_greedy"  # Exploit best with epsilon exploration


class ModelVariant:
    """Represents a model variant in an A/B test."""
    
    def __init__(
        self,
        variant_id: str,
        name: str,
        model_path: str,
        model_version: str,
        description: str = "",
    ):
        self.variant_id = variant_id
        self.name = name
        self.model_path = model_path
        self.model_version = model_version
        self.description = description
        
        # Performance tracking
        self.impressions = 0
        self.conversions = 0
        self.total_revenue = 0.0
        self.latency_samples = []
        
        # Thompson Sampling parameters (Beta distribution)
        self.alpha = 1.0  # Success prior
        self.beta_param = 1.0  # Failure prior
        
    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate."""
        return self.conversions / self.impressions if self.impressions > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        return (
            float(np.mean(self.latency_samples[-100:]))
            if self.latency_samples
            else 0.0
        )
    
    def record_impression(self) -> None:
        """Record an impression (recommendation served)."""
        self.impressions += 1
    
    def record_conversion(self, revenue: float = 0.0) -> None:
        """Record a conversion (user acted on recommendation)."""
        self.conversions += 1
        self.total_revenue += revenue
        self.alpha += 1  # Update Thompson Sampling prior
    
    def record_no_conversion(self) -> None:
        """Record no conversion."""
        self.beta_param += 1  # Update Thompson Sampling prior
    
    def record_latency(self, latency_ms: float) -> None:
        """Record prediction latency."""
        self.latency_samples.append(latency_ms)
        if len(self.latency_samples) > 1000:
            self.latency_samples = self.latency_samples[-1000:]
    
    def sample_conversion_rate(self) -> float:
        """Sample from posterior distribution (Thompson Sampling)."""
        return beta.rvs(self.alpha, self.beta_param)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "model_version": self.model_version,
            "impressions": self.impressions,
            "conversions": self.conversions,
            "conversion_rate": round(self.conversion_rate, 4),
            "total_revenue": round(self.total_revenue, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


class ABTestExperiment:
    """Represents an A/B testing experiment."""
    
    def __init__(
        self,
        experiment_id: str,
        name: str,
        description: str,
        variants: List[ModelVariant],
        allocation_strategy: AllocationStrategy = AllocationStrategy.THOMPSON_SAMPLING,
        traffic_percentage: float = 100.0,
        min_sample_size: int = 1000,
    ):
        self.experiment_id = experiment_id
        self.name = name
        self.description = description
        self.variants = {v.variant_id: v for v in variants}
        self.allocation_strategy = allocation_strategy
        self.traffic_percentage = traffic_percentage
        self.min_sample_size = min_sample_size
        
        self.status = ExperimentStatus.DRAFT
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Fixed allocation weights (for FIXED strategy)
        self.fixed_weights = {
            v.variant_id: 1.0 / len(variants)
            for v in variants
        }
        
        logger.info(
            "ab_test_experiment_created",
            experiment_id=experiment_id,
            variants=[v.name for v in variants],
        )
    
    def start(self) -> None:
        """Start the experiment."""
        self.status = ExperimentStatus.RUNNING
        self.start_time = datetime.utcnow()
        logger.info("experiment_started", experiment_id=self.experiment_id)
    
    def stop(self) -> None:
        """Stop the experiment."""
        self.status = ExperimentStatus.CONCLUDED
        self.end_time = datetime.utcnow()
        logger.info("experiment_stopped", experiment_id=self.experiment_id)
    
    def select_variant(self, user_id: str) -> Optional[ModelVariant]:
        """
        Select a variant for the given user.
        
        Args:
            user_id: User identifier for consistent assignment
            
        Returns:
            Selected model variant
        """
        if self.status != ExperimentStatus.RUNNING:
            return None
        
        # Check if user should be in experiment
        if random.random() * 100 > self.traffic_percentage:
            return None
        
        if self.allocation_strategy == AllocationStrategy.FIXED:
            return self._select_fixed(user_id)
        elif self.allocation_strategy == AllocationStrategy.THOMPSON_SAMPLING:
            return self._select_thompson_sampling()
        elif self.allocation_strategy == AllocationStrategy.EPSILON_GREEDY:
            return self._select_epsilon_greedy()
        else:
            return self._select_fixed(user_id)
    
    def _select_fixed(self, user_id: str) -> ModelVariant:
        """Select variant using fixed allocation."""
        # Use hash of user_id for consistent assignment
        hash_value = hash(user_id) % 1000 / 1000.0
        
        cumulative = 0.0
        for variant_id, weight in self.fixed_weights.items():
            cumulative += weight
            if hash_value <= cumulative:
                return self.variants[variant_id]
        
        return list(self.variants.values())[0]
    
    def _select_thompson_sampling(self) -> ModelVariant:
        """Select variant using Thompson Sampling (adaptive)."""
        # Sample from each variant's posterior distribution
        samples = {
            variant_id: variant.sample_conversion_rate()
            for variant_id, variant in self.variants.items()
        }
        
        # Select variant with highest sampled value
        best_variant_id = max(samples, key=samples.get)
        return self.variants[best_variant_id]
    
    def _select_epsilon_greedy(self, epsilon: float = 0.1) -> ModelVariant:
        """Select variant using epsilon-greedy strategy."""
        if random.random() < epsilon:
            # Explore: random selection
            return random.choice(list(self.variants.values()))
        else:
            # Exploit: select best performing
            best_variant = max(
                self.variants.values(),
                key=lambda v: v.conversion_rate
            )
            return best_variant
    
    def get_winning_variant(self) -> Tuple[Optional[ModelVariant], float]:
        """
        Determine winning variant using statistical testing.
        
        Returns:
            Tuple of (winning_variant, confidence_level)
        """
        # Need minimum sample size
        if any(v.impressions < self.min_sample_size for v in self.variants.values()):
            return None, 0.0
        
        try:
            # Chi-square test for independence
            data = [
                [v.conversions, v.impressions - v.conversions]
                for v in self.variants.values()
            ]
            
            chi2, p_value, dof, expected = chi2_contingency(data)
            
            # Find best variant
            best_variant = max(
                self.variants.values(),
                key=lambda v: v.conversion_rate
            )
            
            confidence = 1 - p_value
            
            return best_variant, confidence
            
        except Exception as e:
            logger.error("statistical_test_failed", error=str(e))
            return None, 0.0
    
    def get_results(self) -> Dict[str, Any]:
        """Get experiment results."""
        winning_variant, confidence = self.get_winning_variant()
        
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "variants": [v.to_dict() for v in self.variants.values()],
            "winning_variant": winning_variant.name if winning_variant else None,
            "confidence": round(confidence, 4) if winning_variant else 0.0,
            "total_impressions": sum(v.impressions for v in self.variants.values()),
            "total_conversions": sum(v.conversions for v in self.variants.values()),
        }


class ABTestingService:
    """Service for managing A/B tests across model variants."""
    
    def __init__(self):
        self._experiments: Dict[str, ABTestExperiment] = {}
        self._user_assignments: Dict[str, Dict[str, str]] = defaultdict(dict)
        
        logger.info("ab_testing_service_initialized")
    
    def create_experiment(
        self,
        name: str,
        description: str,
        variants: List[Dict[str, Any]],
        allocation_strategy: str = "thompson_sampling",
        traffic_percentage: float = 100.0,
    ) -> str:
        """
        Create a new A/B test experiment.
        
        Args:
            name: Experiment name
            description: Experiment description
            variants: List of variant configurations
            allocation_strategy: Traffic allocation strategy
            traffic_percentage: Percentage of traffic in experiment
            
        Returns:
            Experiment ID
        """
        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        
        # Create variant objects
        variant_objects = [
            ModelVariant(
                variant_id=v.get("variant_id", f"var_{i}"),
                name=v["name"],
                model_path=v["model_path"],
                model_version=v["model_version"],
                description=v.get("description", ""),
            )
            for i, v in enumerate(variants)
        ]
        
        experiment = ABTestExperiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variant_objects,
            allocation_strategy=AllocationStrategy(allocation_strategy),
            traffic_percentage=traffic_percentage,
        )
        
        self._experiments[experiment_id] = experiment
        
        logger.info(
            "experiment_created",
            experiment_id=experiment_id,
            name=name,
            num_variants=len(variants),
        )
        
        return experiment_id
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        if experiment_id in self._experiments:
            self._experiments[experiment_id].start()
            return True
        return False
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop an experiment."""
        if experiment_id in self._experiments:
            self._experiments[experiment_id].stop()
            return True
        return False
    
    def get_variant_for_user(
        self,
        user_id: str,
        experiment_id: Optional[str] = None,
    ) -> Optional[ModelVariant]:
        """
        Get model variant for a user.
        
        Args:
            user_id: User identifier
            experiment_id: Specific experiment (if None, use active experiments)
            
        Returns:
            Model variant to use for this user
        """
        if experiment_id:
            experiment = self._experiments.get(experiment_id)
            if experiment:
                return experiment.select_variant(user_id)
            return None
        
        # Check all running experiments
        for exp_id, experiment in self._experiments.items():
            if experiment.status == ExperimentStatus.RUNNING:
                variant = experiment.select_variant(user_id)
                if variant:
                    # Store assignment for consistency
                    self._user_assignments[user_id][exp_id] = variant.variant_id
                    return variant
        
        return None
    
    def record_impression(
        self,
        experiment_id: str,
        variant_id: str,
        latency_ms: float = 0.0,
    ) -> None:
        """Record an impression for a variant."""
        experiment = self._experiments.get(experiment_id)
        if experiment and variant_id in experiment.variants:
            variant = experiment.variants[variant_id]
            variant.record_impression()
            if latency_ms > 0:
                variant.record_latency(latency_ms)
    
    def record_conversion(
        self,
        experiment_id: str,
        variant_id: str,
        revenue: float = 0.0,
    ) -> None:
        """Record a conversion for a variant."""
        experiment = self._experiments.get(experiment_id)
        if experiment and variant_id in experiment.variants:
            variant = experiment.variants[variant_id]
            variant.record_conversion(revenue)
    
    def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get results for an experiment."""
        experiment = self._experiments.get(experiment_id)
        if experiment:
            return experiment.get_results()
        return None
    
    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments."""
        return [
            {
                "experiment_id": exp_id,
                "name": exp.name,
                "status": exp.status.value,
                "num_variants": len(exp.variants),
            }
            for exp_id, exp in self._experiments.items()
        ]


# Singleton instance
_ab_testing_service: Optional[ABTestingService] = None


def get_ab_testing_service() -> ABTestingService:
    """Get the singleton A/B testing service."""
    global _ab_testing_service
    if _ab_testing_service is None:
        _ab_testing_service = ABTestingService()
    return _ab_testing_service
