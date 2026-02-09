# Real-Time Recommender System - Main Application
"""
FastAPI application entry point for the recommendation system.

This module provides:
- FastAPI application configuration
- Middleware setup (CORS, metrics, logging)
- API router inclusion
- Startup and shutdown event handlers

The application is designed for production deployment with:
- Proper error handling and logging
- Prometheus metrics integration
- Health checks and readiness probes
- Security middleware
"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from structlog.contextvars import clear_contextvars

from .api import events_router, health_router, metrics_router, recommend_router, mlops_router
from .core.config import settings
from .core.logging import configure_logging, get_logger
from .models.schemas import ErrorResponse
from .services.monitoring import get_monitoring_service
from .services.recommendation import get_recommendation_service

# Configure structured logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for:
    - Model loading
    - Service initialization
    - Metrics setup
    - Cleanup on shutdown
    """
    startup_time = time.time()

    logger.info(
        "application_starting",
        version=settings.version,
        environment=settings.app_env,
    )

    # AUTOMATIC TRAINING CHECK
    try:
        from .training.auto_train import should_train_model, train_model
        
        if should_train_model():
            logger.warning("model_missing_starting_automatic_training")
            try:
                train_model()
                logger.info("automatic_training_successful")
            except Exception as e:
                logger.error("automatic_training_failed", error=str(e))
                logger.warning("continuing_without_model_will_use_cold_start")
    except ImportError as e:
        logger.warning("could_not_import_auto_train", error=str(e))

    # Load recommendation model
    try:
        recommendation_service = get_recommendation_service()
        model_path = settings.model_path if hasattr(settings, 'model_path') else None
        recommendation_service.load_model(model_path=model_path)
        logger.info("model_loaded_successfully", model_path=model_path)
    except Exception as e:
        logger.warning("model_loading_failed", error=str(e))
        # Continue without model - will use cold start

    # Initialize monitoring
    monitoring_service = get_monitoring_service()

    logger.info(
        "application_started",
        startup_time_seconds=round(time.time() - startup_time, 2),
    )

    yield

    # Shutdown
    logger.info("application_shutting_down")
    clear_contextvars()


# Create FastAPI application
app = FastAPI(
    title="Real-Time Recommendation System",
    description="""
    Production-grade recommendation system API.

    ## Features
    - Personalized recommendations based on user preferences
    - Real-time event tracking and logging
    - Comprehensive monitoring and metrics
    - Health checks and readiness probes

    ## Model
    The system uses a LightGBM-based recommendation model trained on user
    interaction data. Cold start users receive popular item recommendations.

    ## API Version
    Current version: v1
    """,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Any) -> Response:
    """
    Middleware for request logging.

    Logs:
    - Request method and path
    - Response status code
    - Request duration
    - Client information
    """
    # Generate request ID
    request_id = f"req_{int(time.time() * 1000)}_{id(request)}"

    # Log request
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params),
        client_host=request.client.host if request.client else None,
    )

    # Process request
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Log response
    logger.info(
        "request_completed",
        request_id=request_id,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next: Any) -> Response:
    """
    Global error handling middleware.

    Catches unhandled exceptions and returns proper error responses.
    """
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(
            "unhandled_exception",
            error_type=type(e).__name__,
            error=str(e),
            path=request.url.path,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error_type": "InternalError",
                "message": "An unexpected error occurred",
                "details": {"error_type": type(e).__name__} if settings.debug else None,
            },
        )


# Include API routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(mlops_router, prefix="/api/v1")  # 🔥 Dynamic MLOps endpoints


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with service information.

    Returns basic service information and links to documentation.
    """
    return {
        "service": "Real-Time Recommendation System",
        "version": settings.version,
        "environment": settings.app_env,
        "documentation": "/docs",
        "health": "/api/v1/health",
    }


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error_type": "ValidationError",
            "message": str(exc),
        },
    )


# Create application instance for uvicorn
def create_app() -> FastAPI:
    """
    Application factory for creating FastAPI app instances.

    This pattern enables testing with different configurations.
    """
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
