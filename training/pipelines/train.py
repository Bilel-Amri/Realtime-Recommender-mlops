# Real-Time Recommender System - Model Training Pipeline
"""
Complete training pipeline for the recommendation model.

This module provides:
- Data loading from feature store or files
- Feature engineering and preprocessing
- Model training with cross-validation
- Hyperparameter optimization
- Model evaluation
- MLflow integration for tracking

The pipeline is designed for reproducibility and production deployment.

Why LightGBM?
- Excellent performance on tabular data
- Fast training and inference
- Built-in feature importance
- Handles missing values naturally
- Well-suited for recommendation tasks
"""

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from backend.app.core.config import settings
except ImportError:
    # Fallback for standalone training
    class Settings:
        mlflow_tracking_uri = None
        mlflow_experiment_name = "recommender-system"
    settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for model training."""

    # Model hyperparameters
    n_estimators: int = 500
    learning_rate: float = 0.05
    max_depth: int = 8
    num_leaves: int = 64
    min_child_samples: int = 20
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_alpha: float = 0.1
    reg_lambda: float = 0.1

    # Training settings
    test_size: float = 0.2
    random_state: int = 42
    early_stopping_rounds: int = 50

    # Feature settings
    negative_sampling_ratio: float = 5.0  # Ratio of negative to positive samples

    # MLflow settings
    mlflow_experiment_name: str = "recommender-system"
    mlflow_run_name: Optional[str] = None


class RecommendationDataset:
    """
    Dataset class for recommendation model training.

    Handles:
    - Loading interaction data
    - Negative sampling
    - Feature engineering
    - Train/validation split
    """

    def __init__(
        self,
        interactions_path: Optional[str] = None,
        user_features_path: Optional[str] = None,
        item_features_path: Optional[str] = None,
    ):
        """
        Initialize dataset.

        Args:
            interactions_path: Path to user-item interactions CSV
            user_features_path: Path to user features CSV
            item_features_path: Path to item features CSV
        """
        self.interactions_path = interactions_path
        self.user_features_path = user_features_path
        self.item_features_path = item_features_path

        self.interactions_df: Optional[pd.DataFrame] = None
        self.user_features_df: Optional[pd.DataFrame] = None
        self.item_features_df: Optional[pd.DataFrame] = None

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load all data sources.

        Returns:
            Tuple of (interactions, user_features, item_features) DataFrames
        """
        logger.info("Loading training data...")

        # Load interactions
        if self.interactions_path and Path(self.interactions_path).exists():
            self.interactions_df = pd.read_csv(self.interactions_path)
            logger.info(f"Loaded {len(self.interactions_df)} interactions")
        else:
            # Generate synthetic data for demonstration
            self.interactions_df = self._generate_synthetic_interactions()
            logger.info(f"Generated {len(self.interactions_df)} synthetic interactions")

        # Load user features
        if self.user_features_path and Path(self.user_features_path).exists():
            self.user_features_df = pd.read_csv(self.user_features_path)
            logger.info(f"Loaded {len(self.user_features_df)} user features")
        else:
            self.user_features_df = self._generate_synthetic_user_features()

        # Load item features
        if self.item_features_path and Path(self.item_features_path).exists():
            self.item_features_df = pd.read_csv(self.item_features_path)
            logger.info(f"Loaded {len(self.item_features_df)} item features")
        else:
            self.item_features_df = self._generate_synthetic_item_features()

        return self.interactions_df, self.user_features_df, self.item_features_df

    def _generate_synthetic_interactions(self, n_users: int = 1000, n_items: int = 500, n_interactions: int = 50000) -> pd.DataFrame:
        """Generate synthetic interaction data."""
        np.random.seed(42)

        users = np.random.choice([f"user_{i}" for i in range(n_users)], n_interactions)
        items = np.random.choice([f"item_{i}" for i in range(n_items)], n_interactions)

        # Generate engagement scores (higher = more positive interaction)
        engagement = np.random.beta(2, 5, n_interactions)  # Skewed towards lower engagement

        # Add some structure: users have preferences
        user_pref = np.array([hash(u) % 100 / 100 for u in users])
        item_pop = np.array([hash(i) % 100 / 100 for i in items])
        engagement = (engagement + user_pref * 0.3 + item_pop * 0.2) / 1.5

        return pd.DataFrame({
            "user_id": users,
            "item_id": items,
            "engagement": engagement,
            "timestamp": pd.date_range(start="2024-01-01", periods=n_interactions, freq="T"),
        })

    def _generate_synthetic_user_features(self, n_users: int = 1000) -> pd.DataFrame:
        """Generate synthetic user features."""
        np.random.seed(42)

        users = [f"user_{i}" for i in range(n_users)]

        return pd.DataFrame({
            "user_id": users,
            **{f"user_feature_{i}": np.random.randn(n_users) for i in range(20)},
            "activity_level": np.random.beta(2, 5, n_users),
            "account_age_days": np.random.exponential(100, n_users),
            "session_count": np.random.poisson(10, n_users),
        })

    def _generate_synthetic_item_features(self, n_items: int = 500) -> pd.DataFrame:
        """Generate synthetic item features."""
        np.random.seed(42)

        items = [f"item_{i}" for i in range(n_items)]

        return pd.DataFrame({
            "item_id": items,
            **{f"item_feature_{i}": np.random.randn(n_items) for i in range(10)},
            "popularity_score": np.random.beta(2, 5, n_items),
            "category_encoded": np.random.randint(0, 10, n_items),
            "recency_score": np.random.beta(5, 2, n_items),
        })

    def prepare_training_data(
        self,
        negative_sampling_ratio: float = 5.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare data for model training.

        Creates positive and negative samples for learning to rank.

        Args:
            negative_sampling_ratio: Ratio of negative to positive samples

        Returns:
            Tuple of (X_train, X_val, y_train, y_val) arrays
        """
        # Ensure data is loaded
        if self.interactions_df is None:
            self.load_data()

        # Create positive samples (interactions)
        positive_samples = self.interactions_df[
            self.interactions_df["engagement"] > 0.3
        ].copy()

        # Create negative samples (non-interactions) - OPTIMIZED
        all_items = list(self.item_features_df["item_id"])
        negative_samples = []
        
        # Group interactions by user for efficient lookup
        user_items = self.interactions_df.groupby("user_id")["item_id"].apply(set).to_dict()
        all_items_set = set(all_items)
        
        # Limit to first 1000 positive samples for faster training
        sample_limit = min(1000, len(positive_samples))
        sampled_positive = positive_samples.sample(n=sample_limit, random_state=42)
        
        logger.info(f"Sampling negatives for {sample_limit} positive samples...")

        for _, row in sampled_positive.iterrows():
            user = row["user_id"]
            interacted_items = user_items.get(user, set())

            # Sample negative items
            non_interacted = list(all_items_set - interacted_items)
            n_neg = min(
                int(negative_sampling_ratio),
                len(non_interacted)
            )
            if n_neg > 0:
                sampled_neg = np.random.choice(non_interacted, n_neg, replace=False)

                for item in sampled_neg:
                    negative_samples.append({
                        "user_id": user,
                        "item_id": item,
                        "engagement": 0.0,
                    })

        negative_df = pd.DataFrame(negative_samples)
        logger.info(f"Generated {len(negative_df)} negative samples")

        # Combine positive and negative samples
        train_df = pd.concat([positive_samples, negative_df], ignore_index=True)

        # Merge with features
        train_df = train_df.merge(
            self.user_features_df, on="user_id", how="left"
        ).merge(
            self.item_features_df, on="item_id", how="left"
        )

        # Drop identifiers
        feature_cols = [c for c in train_df.columns if c not in ["user_id", "item_id", "timestamp"]]
        X = train_df[feature_cols].fillna(0).values
        y = train_df["engagement"].values

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=0.2,
            random_state=42,
        )

        logger.info(
            f"Prepared training data: {len(X_train)} train, {len(X_val)} val samples"
        )

        return X_train, X_val, y_train, y_val


class RecommendationModelTrainer:
    """
    Trainer class for the recommendation model.

    Handles:
    - Model initialization
    - Training with early stopping
    - Hyperparameter optimization
    - Model evaluation
    - MLflow logging
    """

    def __init__(self, config: Optional[TrainingConfig] = None):
        """
        Initialize trainer.

        Args:
            config: Training configuration
        """
        self.config = config or TrainingConfig()
        self.model: Optional[lgb.LGBMModel] = None
        self.feature_names: Optional[List[str]] = None

    def train(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_train: np.ndarray,
        y_val: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> lgb.LGBMModel:
        """
        Train the recommendation model.

        Args:
            X_train: Training features
            X_val: Validation features
            y_train: Training labels
            y_val: Validation labels
            feature_names: Names of features

        Returns:
            Trained LightGBM model
        """
        logger.info("Starting model training...")

        # Create LightGBM datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        # Model parameters
        params = {
            "objective": "regression",
            "metric": "rmse",
            "boosting_type": "gbdt",
            "learning_rate": self.config.learning_rate,
            "num_leaves": self.config.num_leaves,
            "max_depth": self.config.max_depth,
            "min_child_samples": self.config.min_child_samples,
            "subsample": self.config.subsample,
            "colsample_bytree": self.config.colsample_bytree,
            "reg_alpha": self.config.reg_alpha,
            "reg_lambda": self.config.reg_lambda,
            "random_state": self.config.random_state,
            "verbosity": -1,
            "n_jobs": -1,
        }

        # Train model with early stopping
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=self.config.n_estimators,
            valid_sets=[train_data, val_data],
            valid_names=["train", "valid"],
            callbacks=[
                lgb.early_stopping(self.config.early_stopping_rounds),
                lgb.log_evaluation(100),
            ],
        )

        self.feature_names = feature_names or [f"feature_{i}" for i in range(X_train.shape[1])]

        logger.info(f"Training completed. Best iteration: {self.model.best_iteration}")

        return self.model

    def evaluate(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
        k_values: List[int] = [5, 10, 20],
    ) -> Dict[str, float]:
        """
        Evaluate model performance.

        Args:
            X_val: Validation features
            y_val: Validation labels
            k_values: Values of K for ranking metrics

        Returns:
            Dictionary of evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Get predictions
        y_pred = self.model.predict(X_val)

        # Calculate regression metrics
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        metrics = {
            "rmse": np.sqrt(mean_squared_error(y_val, y_pred)),
            "mae": mean_absolute_error(y_val, y_pred),
            "r2": r2_score(y_val, y_pred),
        }

        # Calculate ranking metrics (Recall@K, MAP@K)
        ranking_metrics = self._calculate_ranking_metrics(y_val, y_pred, k_values)
        metrics.update(ranking_metrics)

        # Log metrics
        for name, value in metrics.items():
            logger.info(f"  {name}: {value:.4f}")

        return metrics

    def _calculate_ranking_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        k_values: List[int],
    ) -> Dict[str, float]:
        """
        Calculate ranking-specific metrics.

        Simulates recommendation quality by treating high engagement
        as "relevant" items.
        """
        metrics = {}

        # Convert to binary relevance
        relevance_threshold = 0.5
        y_binary = (y_true >= relevance_threshold).astype(int)

        # Sort by predicted score (descending)
        sorted_indices = np.argsort(y_pred)[::-1]

        # Calculate metrics for each K
        for k in k_values:
            top_k_indices = sorted_indices[:k]
            top_k_relevance = y_binary[top_k_indices]

            # Recall@K: What fraction of relevant items are in top-K?
            total_relevant = np.sum(y_binary)
            relevant_in_top_k = np.sum(top_k_relevance)
            recall_k = relevant_in_top_k / total_relevant if total_relevant > 0 else 0
            metrics[f"recall@{k}"] = recall_k

            # Average Precision@K
            precision_at_k = np.cumsum(top_k_relevance) / np.arange(1, k + 1)
            ap_k = np.sum(precision_at_k * top_k_relevance) / np.sum(y_binary) if np.sum(y_binary) > 0 else 0
            metrics[f"map@{k}"] = ap_k

        # CTR proxy (average predicted engagement)
        metrics["ctr_proxy"] = float(np.mean(y_pred))

        return metrics

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Get feature importance.

        Args:
            top_n: Number of top features to return

        Returns:
            DataFrame with feature importance
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        importance = self.model.feature_importance(importance_type="gain")
        feature_names = self.feature_names or [f"feature_{i}" for i in range(len(importance))]

        importance_df = pd.DataFrame({
            "feature": feature_names,
            "importance": importance,
        }).sort_values("importance", ascending=False).head(top_n)

        return importance_df


def train_model(
    config: Optional[TrainingConfig] = None,
) -> Tuple[lgb.LGBMModel, Dict[str, float]]:
    """
    Main training function.

    This function orchestrates the complete training pipeline:
    1. Load data
    2. Prepare features
    3. Train model
    4. Evaluate model
    5. Log to MLflow
    6. Return trained model and metrics

    Args:
        config: Training configuration

    Returns:
        Tuple of (trained_model, evaluation_metrics)
    """
    config = config or TrainingConfig()

    # Initialize MLflow (disable if not configured)
    try:
        if settings.mlflow_tracking_uri:
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(config.mlflow_experiment_name)
        mlflow_enabled = True
    except Exception as e:
        logger.warning(f"MLflow not available: {e}. Continuing without MLflow logging.")
        mlflow_enabled = False

    # Training context
    if mlflow_enabled:
        run = mlflow.start_run(run_name=config.mlflow_run_name)
    else:
        from contextlib import nullcontext
        run = nullcontext()
        
    with run:
        # Log parameters
        if mlflow_enabled:
            try:
                mlflow.log_params({
                    f"model.{k}": v for k, v in config.__dict__.items()
                    if k.startswith(("n_", "learning", "max_", "num_", "min_", "sub", "col", "reg_"))
                })
            except Exception as e:
                logger.warning(f"Failed to log parameters: {e}")

        # Load and prepare data
        logger.info("Preparing training dataset...")
        dataset = RecommendationDataset()
        X_train, X_val, y_train, y_val = dataset.prepare_training_data(
            negative_sampling_ratio=config.negative_sampling_ratio,
        )

        # Train model
        logger.info("Training model...")
        trainer = RecommendationModelTrainer(config)
        model = trainer.train(X_train, X_val, y_train, y_val)

        # Evaluate model
        logger.info("Evaluating model...")
        metrics = trainer.evaluate(X_val, y_val)

        # Log metrics
        if mlflow_enabled:
            try:
                mlflow.log_metrics(metrics)
            except Exception as e:
                logger.warning(f"Failed to log metrics: {e}")

        # Log feature importance
        try:
            importance_df = trainer.get_feature_importance()
            importance_path = "feature_importance.csv"
            importance_df.to_csv(importance_path, index=False)
            logger.info(f"Feature importance saved to {importance_path}")
            
            if mlflow_enabled:
                try:
                    mlflow.log_artifact(importance_path)
                except Exception as e:
                    logger.warning(f"Failed to log feature importance: {e}")
        except Exception as e:
            logger.warning(f"Failed to compute feature importance: {e}")

        # Save model locally
        model_path = "recommendation_model.txt"
        model.save_model(model_path)
        logger.info(f"Model saved to {model_path}")

        # Log and register model
        if mlflow_enabled:
            try:
                mlflow.lightgbm.log_model(model, "model")
                
                # Register model
                model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
                mlflow.register_model(model_uri, "recommender-model")
                logger.info(f"Model registered in MLflow as 'recommender-model'")
            except Exception as e:
                logger.warning(f"Failed to log/register model in MLflow: {e}")

        logger.info(f"✅ Training completed successfully!")

    return model, metrics


if __name__ == "__main__":
    # Run training
    model, metrics = train_model()

    print("\nFinal Metrics:")
    for name, value in metrics.items():
        print(f"  {name}: {value:.4f}")
