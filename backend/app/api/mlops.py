# Real-Time Recommender System - MLOps API Endpoints
"""
API endpoints for MLOps operations and dynamic model management.

These endpoints provide:
- POST /mlops/retrain: Trigger model retraining
- GET /mlops/retrain/status: Get retraining status
- POST /mlops/online-learning/trigger: Trigger online learning update
- GET /mlops/online-learning/status: Get online learning metrics
- POST /mlops/experiments: Create A/B test experiment
- GET /mlops/experiments: List all experiments
- GET /mlops/experiments/{id}: Get experiment results
- POST /mlops/experiments/{id}/start: Start experiment
- POST /mlops/experiments/{id}/stop: Stop experiment

These are the core MLOps endpoints that make the system dynamic and adaptive.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..core.logging import get_logger
from ..models.schemas import ErrorResponse
from ..services.ab_testing import get_ab_testing_service
from ..services.auto_retrain import get_auto_retrain_service
from ..services.online_learning import get_online_learning_service

logger = get_logger(__name__)
router = APIRouter(tags=["MLOps"])


# Request/Response Models
class RetrainRequest(BaseModel):
    """Request to trigger model retraining."""
    force: bool = False
    reason: Optional[str] = None


class RetrainResponse(BaseModel):
    """Response from retrain trigger."""
    triggered: bool
    reason: str
    status: Dict[str, Any]


class OnlineLearningTriggerResponse(BaseModel):
    """Response from online learning trigger."""
    success: bool
    message: str
    metrics: Dict[str, Any]


class ExperimentCreateRequest(BaseModel):
    """Request to create A/B test experiment."""
    name: str
    description: str
    variants: List[Dict[str, Any]]
    allocation_strategy: str = "thompson_sampling"
    traffic_percentage: float = 100.0


class ExperimentResponse(BaseModel):
    """Response with experiment details."""
    experiment_id: str
    message: str


# ==================== Auto-Retraining Endpoints ====================

@router.post(
    "/mlops/retrain",
    response_model=RetrainResponse,
    summary="Trigger Model Retraining",
    description="""
    Trigger model retraining pipeline.
    
    This initiates a full model retraining cycle:
    1. Check retraining triggers (drift, performance, schedule)
    2. Run training pipeline if triggers are met
    3. Validate new model
    4. Promote to production if validation passes
    
    Use `force=true` to bypass trigger checks.
    """,
)
async def trigger_retrain(request: RetrainRequest) -> RetrainResponse:
    """Trigger model retraining."""
    try:
        auto_retrain_service = get_auto_retrain_service()
        
        if request.force:
            # Force retraining regardless of triggers
            logger.info("forced_retrain_requested", reason=request.reason)
            success = await auto_retrain_service._trigger_retraining(
                trigger_reason=request.reason or "manual_force",
            )
            triggered = success
            reason = "Forced retraining initiated" if success else "Retraining failed"
        else:
            # Check triggers and retrain if needed
            triggered, reason = await auto_retrain_service.check_and_trigger_retrain()
        
        status = auto_retrain_service.get_retraining_status()
        
        return RetrainResponse(
            triggered=triggered,
            reason=reason,
            status=status,
        )
        
    except Exception as e:
        logger.error("retrain_trigger_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": "RetrainError",
                "message": str(e),
            },
        )


@router.get(
    "/mlops/retrain/status",
    response_model=Dict[str, Any],
    summary="Get Retraining Status",
    description="""
    Get current status of auto-retraining system.
    
    Returns:
    - Whether retraining is in progress
    - Last retrain time
    - New interactions since last retrain
    - Time until next scheduled retrain
    - Drift detection metrics
    """,
)
async def get_retrain_status() -> Dict[str, Any]:
    """Get retraining status and metrics."""
    try:
        auto_retrain_service = get_auto_retrain_service()
        return auto_retrain_service.get_retraining_status()
    except Exception as e:
        logger.error("retrain_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==================== Online Learning Endpoints ====================

@router.post(
    "/mlops/online-learning/trigger",
    response_model=OnlineLearningTriggerResponse,
    summary="Trigger Online Learning Update",
    description="""
    Trigger an incremental model update using buffered interactions.
    
    This performs online learning:
    1. Takes recent interactions from buffer
    2. Performs mini-batch gradient update
    3. Updates model weights incrementally
    4. Creates checkpoint for rollback
    
    This is lightweight compared to full retraining.
    """,
)
async def trigger_online_learning() -> OnlineLearningTriggerResponse:
    """Trigger online learning update."""
    try:
        online_learning_service = get_online_learning_service()
        
        success = await online_learning_service.trigger_update(force=True)
        
        metrics = online_learning_service.get_performance_metrics()
        
        return OnlineLearningTriggerResponse(
            success=success,
            message="Online learning update completed" if success else "Update failed or insufficient data",
            metrics=metrics,
        )
        
    except Exception as e:
        logger.error("online_learning_trigger_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/mlops/online-learning/status",
    response_model=Dict[str, Any],
    summary="Get Online Learning Status",
    description="""
    Get status and metrics for online learning system.
    
    Returns:
    - Total incremental updates performed
    - Interactions processed
    - Buffer utilization
    - Average update time
    - Model performance metrics
    """,
)
async def get_online_learning_status() -> Dict[str, Any]:
    """Get online learning status and metrics."""
    try:
        online_learning_service = get_online_learning_service()
        return online_learning_service.get_performance_metrics()
    except Exception as e:
        logger.error("online_learning_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ==================== A/B Testing Endpoints ====================

@router.post(
    "/mlops/experiments",
    response_model=ExperimentResponse,
    summary="Create A/B Test Experiment",
    description="""
    Create a new A/B test experiment to compare model variants.
    
    Allocation Strategies:
    - fixed: Fixed percentage split
    - thompson_sampling: Adaptive allocation based on performance
    - epsilon_greedy: Exploit best + random exploration
    
    Example variants:
    ```json
    {
      "name": "Model Comparison Test",
      "description": "Compare LightGBM vs Neural CF",
      "variants": [
        {
          "name": "champion",
          "model_path": "/app/models/champion.pkl",
          "model_version": "v1.0"
        },
        {
          "name": "challenger",
          "model_path": "/app/models/challenger.pkl",
          "model_version": "v2.0"
        }
      ],
      "allocation_strategy": "thompson_sampling",
      "traffic_percentage": 50.0
    }
    ```
    """,
)
async def create_experiment(request: ExperimentCreateRequest) -> ExperimentResponse:
    """Create A/B test experiment."""
    try:
        ab_testing_service = get_ab_testing_service()
        
        experiment_id = ab_testing_service.create_experiment(
            name=request.name,
            description=request.description,
            variants=request.variants,
            allocation_strategy=request.allocation_strategy,
            traffic_percentage=request.traffic_percentage,
        )
        
        logger.info("experiment_created", experiment_id=experiment_id)
        
        return ExperimentResponse(
            experiment_id=experiment_id,
            message=f"Experiment '{request.name}' created successfully",
        )
        
    except Exception as e:
        logger.error("experiment_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/mlops/experiments",
    response_model=List[Dict[str, Any]],
    summary="List All Experiments",
    description="Get a list of all A/B test experiments.",
)
async def list_experiments() -> List[Dict[str, Any]]:
    """List all experiments."""
    try:
        ab_testing_service = get_ab_testing_service()
        return ab_testing_service.list_experiments()
    except Exception as e:
        logger.error("list_experiments_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/mlops/experiments/{experiment_id}",
    response_model=Dict[str, Any],
    summary="Get Experiment Results",
    description="""
    Get detailed results for an A/B test experiment.
    
    Returns:
    - Impressions and conversions per variant
    - Conversion rates
    - Statistical significance
    - Winning variant (if determined)
    - Confidence level
    """,
)
async def get_experiment_results(experiment_id: str) -> Dict[str, Any]:
    """Get experiment results."""
    try:
        ab_testing_service = get_ab_testing_service()
        
        results = ab_testing_service.get_experiment_results(experiment_id)
        
        if results is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found",
            )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_experiment_results_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/mlops/experiments/{experiment_id}/start",
    response_model=Dict[str, str],
    summary="Start Experiment",
    description="Start running an A/B test experiment.",
)
async def start_experiment(experiment_id: str) -> Dict[str, str]:
    """Start an experiment."""
    try:
        ab_testing_service = get_ab_testing_service()
        
        success = ab_testing_service.start_experiment(experiment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found",
            )
        
        return {
            "experiment_id": experiment_id,
            "status": "started",
            "message": "Experiment started successfully",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("start_experiment_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/mlops/experiments/{experiment_id}/stop",
    response_model=Dict[str, str],
    summary="Stop Experiment",
    description="Stop running an A/B test experiment.",
)
async def stop_experiment(experiment_id: str) -> Dict[str, str]:
    """Stop an experiment."""
    try:
        ab_testing_service = get_ab_testing_service()
        
        success = ab_testing_service.stop_experiment(experiment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment {experiment_id} not found",
            )
        
        return {
            "experiment_id": experiment_id,
            "status": "stopped",
            "message": "Experiment stopped successfully",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("stop_experiment_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/mlops/ab-results-demo",
    summary="Get A/B Test Results Demo",
    description="""
    Get simulated A/B test results for demonstration purposes.
    
    This endpoint provides realistic A/B test metrics showing:
    - Model A (baseline) vs Model B (retrained)
    - Engagement rates, click rates, average ratings
    - Statistical significance
    - Visual comparison data
    
    Use this for academic presentations to show experimentation capability.
    """,
)
async def get_ab_results_demo() -> Dict[str, Any]:
    """Get demo A/B test results for presentation."""
    return {
        "experiment": {
            "name": "Retrained Model vs Baseline",
            "description": "Comparing retrained model (v1.1) against baseline (v1.0)",
            "status": "concluded",
            "duration_hours": 48,
            "total_users": 2847,
        },
        "variants": [
            {
                "name": "Model A (Baseline)",
                "version": "v1.0",
                "users": 1423,
                "impressions": 14230,
                "clicks": 1137,
                "likes": 398,
                "ratings_given": 285,
                "metrics": {
                    "click_rate": 0.0799,  # 7.99%
                    "like_rate": 0.0280,    # 2.80%
                    "engagement_rate": 0.1079,  # 10.79%
                    "avg_rating": 3.82,
                    "avg_latency_ms": 12.4,
                }
            },
            {
                "name": "Model B (Retrained)",
                "version": "v1.1",
                "users": 1424,
                "impressions": 14240,
                "clicks": 1282,
                "likes": 467,
                "ratings_given": 334,
                "metrics": {
                    "click_rate": 0.0900,  # 9.00%
                    "like_rate": 0.0328,    # 3.28%
                    "engagement_rate": 0.1228,  # 12.28%
                    "avg_rating": 4.03,
                    "avg_latency_ms": 12.1,
                }
            }
        ],
        "comparison": {
            "click_rate_improvement": 12.64,  # % improvement
            "like_rate_improvement": 17.14,
            "engagement_improvement": 13.81,
            "rating_improvement": 5.50,
            "winner": "Model B (Retrained)",
            "confidence_level": 0.95,
            "statistically_significant": True,
            "p_value": 0.0012,
        },
        "recommendation": {
            "action": "Deploy Model B to production",
            "reason": "Significantly higher engagement (12.28% vs 10.79%)",
            "estimated_impact": "+13.81% overall engagement",
        },
        "timestamp": "2026-02-09T00:00:00Z",
    }
