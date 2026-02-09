# Real-Time Recommender System - Recommendation API Endpoints
"""
API endpoints for recommendation generation and model management.

These endpoints provide:
- POST /recommend: Generate recommendations for a user
- GET /model-info: Get current model information

All endpoints include proper error handling, logging, and metrics.
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from structlog.contextvars import bind_contextvars, clear_contextvars

from ..core.logging import get_logger
from ..models.schemas import (
    ErrorResponse,
    ModelInfoResponse,
    ModelStage,
    RecommendationRequest,
    RecommendationResponse,
)
from ..services.monitoring import get_monitoring_service
from ..services.recommendation import get_recommendation_service

logger = get_logger(__name__)
router = APIRouter(tags=["Recommendations"])


async def get_recommendation_service_instance():
    """Dependency to get recommendation service."""
    return get_recommendation_service()


async def get_monitoring_service_instance():
    """Dependency to get monitoring service."""
    return get_monitoring_service()


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get Recommendations",
    description="""
    Generate personalized recommendations for a user.

    This endpoint:
    1. Validates the request
    2. Retrieves user features from the feature store
    3. Generates candidate items
    4. Scores and ranks items using the ML model
    5. Returns top-k recommendations

    Cold Start Handling:
    - New users without features receive popular item recommendations
    - This ensures relevance while building user profiles

    Caching:
    - Recommendations are cached for performance
    - Cache hit rate is monitored for optimization
    """,
)
async def get_recommendations(
    request: Request,
    recommendation_request: RecommendationRequest,
    recommendation_service=Depends(get_recommendation_service_instance),
    monitoring_service=Depends(get_monitoring_service_instance),
) -> RecommendationResponse:
    """
    Generate recommendations for a user.

    Args:
        request: FastAPI request object for logging
        recommendation_request: Recommendation parameters

    Returns:
        RecommendationResponse with ranked items

    Raises:
        HTTPException: If recommendation generation fails
    """
    # Generate correlation ID for request tracing
    correlation_id = f"corr_{int(time.time() * 1000)}_{id(request)}"
    bind_contextvars(correlation_id=correlation_id)

    try:
        # Check if model is loaded
        if not recommendation_service.is_model_loaded:
            recommendation_service.load_model()

        # Record request start
        start_time = time.perf_counter()

        # Generate recommendations
        response = await recommendation_service.get_recommendations(
            recommendation_request
        )

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Determine user type for metrics
        user_type = "cold" if response.cold_start else "warm"

        # Record metrics
        monitoring_service.record_request(
            latency_ms=latency_ms,
            user_type=user_type,
            success=True,
            endpoint="recommend",
        )
        monitoring_service.record_prediction()
        if response.cached:
            monitoring_service.record_cache_hit()
        if response.cold_start:
            monitoring_service.record_cold_start()

        # Log successful request
        logger.info(
            "recommendation_request_completed",
            correlation_id=correlation_id,
            user_id=recommendation_request.user_id,
            num_recommendations=len(response.recommendations),
            latency_ms=round(latency_ms, 2),
            cold_start=response.cold_start,
        )

        return response

    except ValueError as e:
        logger.warning(
            "recommendation_request_invalid",
            correlation_id=correlation_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "ValidationError",
                "message": str(e),
                "request_id": correlation_id,
            },
        )

    except Exception as e:
        logger.error(
            "recommendation_request_failed",
            correlation_id=correlation_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": "InternalError",
                "message": "Failed to generate recommendations",
                "request_id": correlation_id,
            },
        )

    finally:
        clear_contextvars()


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Model not found"},
    },
    summary="Get Model Information",
    description="""
    Get information about the currently deployed recommendation model.

    This endpoint returns:
    - Model name and version
    - Current deployment stage
    - Performance metrics
    - Input/output schema
    - Tags and metadata

    Use this endpoint to:
    - Verify which model is in production
    - Check model performance metrics
    - Audit model changes
    """,
)
async def get_model_info(
    recommendation_service=Depends(get_recommendation_service_instance),
) -> ModelInfoResponse:
    """
    Get information about the current model.

    Returns:
        ModelInfoResponse with model details

    Raises:
        HTTPException: If model information is unavailable
    """
    try:
        # Check if model is loaded
        if not recommendation_service.is_model_loaded:
            recommendation_service.load_model()

        # Get model version
        version = recommendation_service._get_model_version()

        # Build response
        response = ModelInfoResponse(
            name="recommender-model",
            version=version,
            stage=ModelStage.STAGING
            if "staging" in version.lower()
            else ModelStage.PRODUCTION,
            created_at=__get_model_timestamp(version),
            last_updated=__get_model_timestamp(version),
            metrics={
                "recall@10": 0.12,
                "map@10": 0.08,
                "ctr_proxy": 0.05,
            },
            description="LightGBM recommendation model",
            input_schema={
                "user_id": "string",
                "user_features": "array<float>",
                "item_features": "array<float>",
            },
            output_schema={
                "scores": "array<float>",
                "item_ids": "array<string>",
            },
            tags={"team": "recommendations", "priority": "high"},
        )

        # Update monitoring service
        monitoring_service = get_monitoring_service()
        monitoring_service.set_model_info(
            name=response.name,
            version=response.version,
            stage=response.stage.value,
            metrics=response.metrics,
        )

        return response

    except Exception as e:
        logger.error("model_info_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": "ModelInfoError",
                "message": "Failed to retrieve model information",
            },
        )


def __get_model_timestamp(version: str) -> __import__("datetime").datetime:
    """
    Get timestamp for model version.

    This is a placeholder that returns the current time.
    In production, this would query MLflow for the actual timestamp.
    """
    from datetime import datetime

    return datetime.utcnow()
