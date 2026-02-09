# Real-Time Recommender System - Core Package
"""
Core configuration, logging, and security utilities.

This package provides:
- Application configuration management via Pydantic Settings
- Structured JSON logging with structlog
- Security utilities for API key validation
- Common utilities shared across the application
"""

from .config import settings
from .logging import configure_logging, get_logger

__all__ = ["settings", "configure_logging", "get_logger"]
