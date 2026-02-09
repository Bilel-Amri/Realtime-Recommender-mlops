# Real-Time Recommender System - Health Check API Endpoints
"""
API endpoints for health checks and readiness probes.

These endpoints provide:
- GET /health: Basic health check
- GET /health/live: Liveness probe (is the service running?)
- GET /health/ready: Readiness probe (is the service ready to serve?)

Health checks are essential for:
- Kubernetes liveness/readiness probes
- Load balancer health monitoring
- Service discovery
- Debugging deployment issues
"""

import time
from datetime import datetime
from typing import List, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..core.config import settings
from ..core.logging import get_logger
from ..models.schemas import ComponentHealth, HealthCheckResponse, HealthStatus
from ..services.feature_store import get_feature_store_service
from ..services.monitoring import get_monitoring_service
from ..services.recommendation import get_recommendation_service

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


class SimpleHealthResponse(BaseModel):
    """Simple health check response."""

    status: str
    timestamp: datetime


async def get_feature_store_health() -> ComponentHealth:
    """Check feature store health."""
    try:
        feature_store_service = get_feature_store_service()
        start_time = time.perf_counter()

        healthy, latency_ms = await feature_store_service._backend.health_check()

        return ComponentHealth(
            name="feature_store",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            message="Connected" if healthy else "Connection failed",
            latency_ms=round(latency_ms, 2) if latency_ms else None,
        )
    except Exception as e:
        logger.error("feature_store_health_check_failed", error=str(e))
        return ComponentHealth(
            name="feature_store",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)}",
        )


async def get_model_health() -> ComponentHealth:
    """Check model health."""
    try:
        recommendation_service = get_recommendation_service()

        if recommendation_service.is_model_loaded:
            return ComponentHealth(
                name="model",
                status=HealthStatus.HEALTHY,
                message="Model loaded",
                latency_ms=None,
            )
        else:
            return ComponentHealth(
                name="model",
                status=HealthStatus.DEGRADED,
                message="Model not loaded",
            )
    except Exception as e:
        logger.error("model_health_check_failed", error=str(e))
        return ComponentHealth(
            name="model",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)}",
        )


async def get_monitoring_health() -> ComponentHealth:
    """Check monitoring service health."""
    try:
        monitoring_service = get_monitoring_service()
        return ComponentHealth(
            name="monitoring",
            status=HealthStatus.HEALTHY,
            message="Monitoring active",
        )
    except Exception as e:
        logger.error("monitoring_health_check_failed", error=str(e))
        return ComponentHealth(
            name="monitoring",
            status=HealthStatus.UNHEALTHY,
            message=f"Error: {str(e)}",
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Comprehensive Health Check",
    description="""
    Get comprehensive health status of the service.

    This endpoint checks:
    - Feature store connectivity
    - Model availability
    - Monitoring service status
    - Overall system health

    Returns:
        HealthCheckResponse with detailed status
    """,
)
async def health_check() -> HealthCheckResponse:
    """
    Get comprehensive health check.

    Returns:
        HealthCheckResponse with component statuses
    """
    monitoring_service = get_monitoring_service()

    # Check all components
    components = [
        await get_feature_store_health(),
        await get_model_health(),
        await get_monitoring_health(),
    ]

    # Determine overall status
    if any(c.status == HealthStatus.UNHEALTHY for c in components):
        overall_status = HealthStatus.UNHEALTHY
    elif any(c.status == HealthStatus.DEGRADED for c in components):
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    # Update monitoring service
    for component in components:
        monitoring_service.update_component_health(
            component.name,
            component.status == HealthStatus.HEALTHY,
        )

    return HealthCheckResponse(
        status=overall_status,
        version=settings.version,
        timestamp=datetime.utcnow(),
        uptime_seconds=monitoring_service.get_uptime_seconds(),
        components=components,
    )


@router.get(
    "/health/live",
    response_model=SimpleHealthResponse,
    summary="Liveness Probe",
    description="""
    Kubernetes liveness probe endpoint.

    Returns 200 if the service is running.
    Used by Kubernetes to determine if the pod should be restarted.
    """,
)
async def liveness_probe() -> SimpleHealthResponse:
    """
    Liveness probe - is the service running?

    Returns:
        Simple health response
    """
    return SimpleHealthResponse(
        status="alive",
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/health/ready",
    response_model=SimpleHealthResponse,
    summary="Readiness Probe",
    description="""
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Used by Kubernetes to determine if the pod should receive requests.
    """,
)
async def readiness_probe() -> SimpleHealthResponse:
    """
    Readiness probe - is the service ready to serve?

    Returns:
        Simple health response or raises HTTPException
    """
    try:
        # Check critical components
        components = [
            await get_feature_store_health(),
            await get_model_health(),
        ]

        # If any critical component is unhealthy, return 503
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            logger.warning(
                "readiness_probe_failed",
                unhealthy_components=[c.name for c in components if c.status != HealthStatus.HEALTHY],
            )
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Service not ready")

        return SimpleHealthResponse(
            status="ready",
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("readiness_probe_error", error=str(e))
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service not ready")
