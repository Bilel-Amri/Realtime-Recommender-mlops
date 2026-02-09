# Real-Time Recommender System - Model Evaluation Module
"""
Model evaluation and validation for the recommendation system.

This module provides:
- Model evaluation on test datasets
- A/B testing simulation
- Model comparison
- Threshold-based model rejection
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Comprehensive model evaluation toolkit.

    Provides:
    - Standard metrics (RMSE, MAE, AUC)
    - Ranking metrics (Precision@K, Recall@K, MAP, NDCG)
    - Business metrics (CTR proxy, engagement rate)
    - Threshold validation for model promotion
    """

    def __init__(self, threshold_config: Optional[Dict[str, float]] = None):
        """
        Initialize evaluator.

        Args:
            threshold_config: Minimum thresholds for model promotion
        """
        self.threshold_config = threshold_config or {
            "recall@10": 0.05,
            "map@10": 0.03,
            "auc": 0.55,
            "rmse": 0.5,
        }

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        k_values: List[int] = [5, 10, 20],
    ) -> Dict[str, float]:
        """
        Comprehensive model evaluation.

        Args:
            y_true: Ground truth labels
            y_pred: Model predictions
            k_values: K values for ranking metrics

        Returns:
            Dictionary of all evaluation metrics
        """
        metrics = {}

        # Regression metrics
        metrics.update(self._regression_metrics(y_true, y_pred))

        # Ranking metrics
        metrics.update(self._ranking_metrics(y_true, y_pred, k_values))

        # Classification metrics (at engagement threshold)
        metrics.update(self._classification_metrics(y_true, y_pred))

        return metrics

    def _regression_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Calculate regression metrics."""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)

        # Clip predictions to valid range
        y_pred_clipped = np.clip(y_pred, 0, 1)

        return {
            "rmse": float(rmse),
            "mae": float(mae),
            "r2": float(r2),
        }

    def _ranking_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray, k_values: List[int]
    ) -> Dict[str, float]:
        """Calculate ranking-specific metrics."""
        metrics = {}

        # Convert to binary relevance at threshold
        relevance_threshold = 0.3
        y_binary = (y_true >= relevance_threshold).astype(int)

        # Sort predictions (descending)
        sorted_indices = np.argsort(y_pred)[::-1]

        # Calculate metrics for each K
        for k in k_values:
            top_k_indices = sorted_indices[:k]
            top_k_relevance = y_binary[top_k_indices]

            # Precision@K
            precision_k = np.mean(top_k_relevance)
            metrics[f"precision@{k}"] = float(precision_k)

            # Recall@K
            total_relevant = np.sum(y_binary)
            relevant_in_top_k = np.sum(top_k_relevance)
            recall_k = relevant_in_top_k / total_relevant if total_relevant > 0 else 0
            metrics[f"recall@{k}"] = float(recall_k)

            # Average Precision@K
            precision_cumsum = np.cumsum(top_k_relevance) / np.arange(1, k + 1)
            ap_k = np.sum(precision_cumsum * top_k_relevance) / np.sum(y_binary) if np.sum(y_binary) > 0 else 0
            metrics[f"map@{k}"] = float(ap_k)

            # NDCG@K
            dcg_k = np.sum(top_k_relevance / np.log2(np.arange(2, k + 2)))
            ideal_relevance = np.sort(y_binary)[::-1][:k]
            idcg_k = np.sum(ideal_relevance / np.log2(np.arange(2, k + 2)))
            ndcg_k = dcg_k / idcg_k if idcg_k > 0 else 0
            metrics[f"ndcg@{k}"] = float(ndcg_k)

        # MRR (Mean Reciprocal Rank)
        first_relevant = np.where(y_binary[sorted_indices] == 1)[0]
        mr = 1 / (first_relevant[0] + 1) if len(first_relevant) > 0 else 0
        metrics["mrr"] = float(mr)

        return metrics

    def _classification_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Calculate classification metrics at engagement threshold."""
        threshold = 0.3
        y_binary = (y_true >= threshold).astype(int)
        y_pred_proba = np.clip(y_pred, 0, 1)

        # AUC-ROC
        auc = roc_auc_score(y_binary, y_pred_proba)

        # Average Precision (AUC-PR)
        ap = average_precision_score(y_binary, y_pred_proba)

        # CTR proxy (average predicted engagement)
        ctr_proxy = float(np.mean(y_pred_proba))

        return {
            "auc": float(auc),
            "average_precision": float(ap),
            "ctr_proxy": ctr_proxy,
        }

    def check_promotion_thresholds(
        self, metrics: Dict[str, float]
    ) -> Tuple[bool, List[str]]:
        """
        Check if model meets promotion thresholds.

        Args:
            metrics: Model evaluation metrics

        Returns:
            Tuple of (passed: bool, failures: List[str])
        """
        failures = []

        for metric, threshold in self.threshold_config.items():
            if metric in metrics:
                if metrics[metric] < threshold:
                    failures.append(
                        f"{metric}={metrics[metric]:.4f} < threshold={threshold:.4f}"
                    )

        return len(failures) == 0, failures


def evaluate_model(
    model_uri: str,
    test_data: Tuple[np.ndarray, np.ndarray],
    model_name: str = "recommender-model",
) -> Dict[str, float]:
    """
    Evaluate a model from MLflow.

    Args:
        model_uri: MLflow model URI
        test_data: Tuple of (X_test, y_test)
        model_name: Name for logging

    Returns:
        Dictionary of evaluation metrics
    """
    # Load model
    model = mlflow.pyfunc.load_model(model_uri)

    # Prepare data
    X_test, y_test = test_data

    # Get predictions
    y_pred = model.predict(X_test)

    # Evaluate
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate(y_test, y_pred)

    # Log to MLflow
    mlflow.log_metrics(metrics)

    # Check thresholds
    passed, failures = evaluator.check_promotion_thresholds(metrics)

    if passed:
        logger.info(f"Model {model_name} PASSED evaluation thresholds")
    else:
        logger.warning(
            f"Model {model_name} FAILED evaluation thresholds: {failures}"
        )

    return metrics


if __name__ == "__main__":
    # Example usage
    from train import train_model

    # Train model
    model, train_metrics = train_model()

    # Generate test data
    np.random.seed(42)
    X_test = np.random.randn(1000, 50)
    y_test = np.random.beta(2, 5, 1000)

    # Evaluate
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate(y_test, model.predict(X_test))

    print("\nEvaluation Metrics:")
    for name, value in metrics.items():
        print(f"  {name}: {value:.4f}")

    # Check thresholds
    passed, failures = evaluator.check_promotion_thresholds(metrics)
    print(f"\nPromotion Check: {'PASSED' if passed else 'FAILED'}")
    if failures:
        print(f"Failures: {failures}")
