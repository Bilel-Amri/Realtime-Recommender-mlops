# Real-Time Recommender System - Events API Endpoints
"""
API endpoints for logging user interaction events.

These endpoints provide:
- POST /event: Log a single user interaction
- POST /events/batch: Log multiple events at once

Event tracking is essential for:
- Building user interaction datasets
- Computing engagement metrics
- Enabling collaborative filtering
- Triggering model retraining
"""

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from ..core.logging import get_logger
from ..models.schemas import ErrorResponse, EventCreate, EventResponse
from ..services.monitoring import get_monitoring_service
from ..services.feature_store import get_feature_store_service
from ..services.online_learning import get_online_learning_service
from ..services.auto_retrain import get_auto_retrain_service

logger = get_logger(__name__)
router = APIRouter(tags=["Events"])


@router.post(
    "/event",
    response_model=EventResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid event data"},
        500: {"model": ErrorResponse, "description": "Failed to log event"},
    },
    summary="Log Single Event",
    description="""
    Log a single user interaction event.

    Event Types:
    - view: User viewed an item
    - click: User clicked on an item
    - purchase: User purchased an item
    - like: User liked an item
    - dislike: User disliked/hidden an item
    - share: User shared an item
    - search: User performed a search

    Use this endpoint for:
    - Tracking user interactions in real-time
    - Building training datasets
    - Computing engagement metrics
    """,
)
async def log_event(event: EventCreate) -> EventResponse:
    """
    Log a single user interaction event.

    Args:
        event: Event data to log

    Returns:
        EventResponse with logged event details

    Raises:
        HTTPException: If event logging fails
    """
    try:
        # Generate event ID
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

        # Set timestamp if not provided
        timestamp = event.timestamp or datetime.utcnow()

        # Log the event
        logger.info(
            "event_logged",
            event_id=event_id,
            user_id=event.user_id,
            item_id=event.item_id,
            event_type=event.event_type.value,
        )

        # Record metrics
        monitoring_service = get_monitoring_service()
        monitoring_service.record_event(event.event_type.value)

        # 🔥 DYNAMIC BEHAVIOR: Update user features in real-time
        try:
            feature_store_service = get_feature_store_service()
            await feature_store_service.update_user_features_from_event(
                user_id=event.user_id,
                item_id=event.item_id,
                event_type=event.event_type.value,
                timestamp=timestamp,
                value=event.value
            )
            logger.info(
                "user_features_updated",
                user_id=event.user_id,
                item_id=event.item_id,
                event_type=event.event_type.value
            )
        except Exception as e:
            logger.warning("feature_update_failed", error=str(e))
            # Continue even if feature update fails
        
        # 🔥 ONLINE LEARNING: Add interaction to learning buffer
        try:
            online_learning_service = get_online_learning_service()
            await online_learning_service.add_interaction(
                user_id=event.user_id,
                item_id=event.item_id,
                event_type=event.event_type.value,
                timestamp=timestamp,
            )
            logger.debug("interaction_added_to_learning_buffer")
        except Exception as e:
            logger.warning("online_learning_update_failed", error=str(e))
        
        # 🔥 DRIFT DETECTION: Record for auto-retraining triggers
        try:
            auto_retrain_service = get_auto_retrain_service()
            await auto_retrain_service.record_interaction_for_drift(
                features={
                    "event_type": hash(event.event_type.value) % 100,
                    "timestamp_hour": timestamp.hour,
                }
            )
        except Exception as e:
            logger.warning("drift_tracking_failed", error=str(e))

        return EventResponse(
            event_id=event_id,
            user_id=event.user_id,
            item_id=event.item_id,
            event_type=event.event_type,
            timestamp=timestamp,
            status="logged",
        )

    except Exception as e:
        logger.error("event_logging_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": "EventLoggingError",
                "message": "Failed to log event",
            },
        )


@router.post(
    "/events/batch",
    response_model=List[EventResponse],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid batch data"},
        500: {"model": ErrorResponse, "description": "Failed to log events"},
    },
    summary="Log Batch Events",
    description="""
    Log multiple user interaction events in a single request.

    This endpoint is optimized for:
    - Bulk event upload from client-side applications
    - Event replay from offline sources
    - Periodic batch logging of collected events

    Performance:
    - Events are processed in parallel
    - Batch size is limited to 1000 events per request
    """,
)
async def log_events_batch(events: List[EventCreate]) -> List[EventResponse]:
    """
    Log multiple events in a batch.

    Args:
        events: List of events to log

    Returns:
        List of EventResponse for each logged event

    Raises:
        HTTPException: If batch logging fails
    """
    # Validate batch size
    if len(events) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "ValidationError",
                "message": "Batch size exceeds maximum of 1000 events",
            },
        )

    try:
        responses = []
        monitoring_service = get_monitoring_service()

        for event in events:
            # Generate event ID
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            timestamp = event.timestamp or datetime.utcnow()

            responses.append(
                EventResponse(
                    event_id=event_id,
                    user_id=event.user_id,
                    item_id=event.item_id,
                    event_type=event.event_type,
                    timestamp=timestamp,
                    status="logged",
                )
            )

            # Record metrics
            monitoring_service.record_event(event.event_type.value)

        # Log batch completion
        logger.info(
            "events_batch_logged",
            batch_size=len(events),
            event_types={
                event_type.value: sum(1 for e in events if e.event_type == event_type)
                for event_type in set(e.event_type for e in events)
            },
        )

        return responses

    except Exception as e:
        logger.error("events_batch_logging_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": "BatchEventError",
                "message": "Failed to log events batch",
            },
        )
