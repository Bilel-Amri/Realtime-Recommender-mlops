# Real-Time Recommender System - Training Pipeline Package
"""
ML training pipeline for recommendation models.

This package provides:
- Data loading and preprocessing
- Model training with hyperparameter tuning
- Model evaluation and validation
- Model registration to MLflow

The pipeline is designed for reproducibility and production deployment.
"""

from .train import train_model
from .evaluate import evaluate_model
from .register import register_model

__all__ = ["train_model", "evaluate_model", "register_model"]
