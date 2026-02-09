# Real-Time Recommender System - Logging Module
"""
Structured JSON logging configuration using structlog.

This module provides production-grade logging with:
- Structured JSON output for log aggregation systems
- Contextual logging with bound variables
- Log level filtering
- Exception tracking with stack traces

Why structured logging?
- Machine-parseable logs for automated analysis
- Correlation IDs for request tracing
- Easier integration with log aggregation (ELK, Loki, etc.)
- Consistent log format across services
"""

import logging as stdlib_logging
import sys
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

import structlog
from structlog.processors import JSONRenderer, TimeStamper

from .config import settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    This function sets up structlog with:
    - JSON rendering for production environments
    - Console rendering for development
    - Timestamp formatting
    - Log level filtering
    - Exception tracking

    The configuration is applied globally to all logging calls.

    Side Effects:
        Replaces stdlib logging handlers with structlog processors
    """
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        processors.append(JSONRenderer())
    else:
        # Console rendering for development
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    stdlib_logging.basicConfig(
        level=getattr(stdlib_logging, settings.log_level.upper()),
        format="%(message)s",
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        BoundLogger: Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_action", user_id="user_123", action="click")
    """
    return structlog.get_logger(name)


@contextmanager
def log_context(**kwargs: Any):
    """
    Context manager for adding temporary context to logs.

    All log entries within this context will include the provided
    key-value pairs.

    Args:
        **kwargs: Context variables to bind

    Example:
        >>> with log_context(request_id="req_123"):
        ...     logger.info("processing_request")
    """
    with structlog.contextvars.bound_contextvars(**kwargs):
        yield


def log_execution(
    log_args: bool = False,
    log_result: bool = True,
    log_duration: bool = True,
):
    """
    Decorator to automatically log function execution.

    This decorator adds comprehensive logging to any function:
    - Function name and arguments
    - Execution duration
    - Return value or exception
    - Context variables from settings

    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log return value
        log_duration: Whether to log execution time

    Returns:
        Decorator function

    Example:
        >>> @log_execution(log_args=True, log_duration=True)
        ... def recommend_items(user_id: str) -> List[str]:
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Prepare log data
            log_data: Dict[str, Any] = {
                "function": func.__name__,
            }

            if log_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)

            # Add correlation ID if available
            try:
                from structlog.contextvars import get_contextvars
                ctx = get_contextvars()
                if "correlation_id" in ctx:
                    log_data["correlation_id"] = ctx["correlation_id"]
            except Exception:
                pass

            # Log start
            logger.info("function_started", **log_data)

            # Execute function
            import time
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time

                # Log success
                log_data_success = log_data.copy()
                if log_duration:
                    log_data_success["duration_seconds"] = round(duration, 4)
                if log_result:
                    log_data_success["result_type"] = type(result).__name__

                logger.info("function_completed", **log_data_success)
                return result

            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(
                    "function_failed",
                    **log_data,
                    duration_seconds=round(duration, 4),
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                raise

        return wrapper
    return decorator


class CorrelationLogger:
    """
    Logger wrapper that automatically includes correlation ID.

    This class provides a convenient interface for logging with
    automatic correlation ID injection from context variables.

    Usage:
        >>> logger = CorrelationLogger(__name__)
        >>> logger.info("message")  # Includes correlation_id from context
    """

    def __init__(self, name: str):
        self._logger = get_logger(name)

    def _get_correlation_id(self) -> Optional[str]:
        """Get correlation ID from context variables."""
        try:
            from structlog.contextvars import get_contextvars
            ctx = get_contextvars()
            return ctx.get("correlation_id")
        except Exception:
            return None

    def debug(self, msg: str, **kwargs: Any):
        self._logger.debug(msg, correlation_id=self._get_correlation_id(), **kwargs)

    def info(self, msg: str, **kwargs: Any):
        self._logger.info(msg, correlation_id=self._get_correlation_id(), **kwargs)

    def warning(self, msg: str, **kwargs: Any):
        self._logger.warning(msg, correlation_id=self._get_correlation_id(), **kwargs)

    def error(self, msg: str, **kwargs: Any):
        self._logger.error(msg, correlation_id=self._get_correlation_id(), **kwargs)

    def critical(self, msg: str, **kwargs: Any):
        self._logger.critical(msg, correlation_id=self._get_correlation_id(), **kwargs)
