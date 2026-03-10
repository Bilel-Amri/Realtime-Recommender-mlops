"""
/api/v1/users  —  Dynamic User Profile endpoints

Endpoints:
    POST   /users/{user_id}/profile       – create / overwrite profile
    GET    /users/{user_id}/profile       – get full profile
    PUT    /users/{user_id}/interests     – update one interest dimension
    GET    /users/{user_id}/top-interests – sorted list of interests
    GET    /users/interests/categories    – list of valid category names
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.user_profile import (
    INTEREST_CATEGORIES,
    get_user_profile_service,
)

router = APIRouter(prefix="/users", tags=["User Profiles"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CreateProfileRequest(BaseModel):
    """Create a dynamic user profile with explicit starting interest weights."""
    interests: Dict[str, float] = Field(
        default_factory=lambda: {cat: 0.5 for cat in INTEREST_CATEGORIES},
        description="Map of interest category -> weight [0.0, 1.0].",
    )


class UpdateInterestRequest(BaseModel):
    """Update a single interest dimension."""
    attribute: str = Field(
        ...,
        description="Name of the interest category to update.",
        examples=["action"],
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="New weight for the category, clamped to [0.0, 1.0].",
    )


class InterestItem(BaseModel):
    category: str
    weight: float
    label: str


class UserProfileResponse(BaseModel):
    user_id: str
    interests: Dict[str, float]
    vector: List[float]
    interaction_count: int
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    summary="Create or overwrite a user profile",
)
async def create_user_profile(user_id: str, request: CreateProfileRequest):
    svc = get_user_profile_service()
    if svc is None:
        raise HTTPException(status_code=503, detail="UserProfileService not initialised — Redis unavailable.")
    profile = svc.create_profile(user_id, request.interests)
    return profile


@router.get(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    summary="Retrieve a user profile",
)
async def get_user_profile(user_id: str):
    svc = get_user_profile_service()
    if svc is None:
        raise HTTPException(status_code=503, detail="UserProfileService not initialised — Redis unavailable.")
    profile = svc.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"No dynamic profile found for user '{user_id}'.",
        )
    return profile


@router.put(
    "/{user_id}/interests",
    response_model=UserProfileResponse,
    summary="Update one interest dimension for a user",
)
async def update_user_interest(user_id: str, request: UpdateInterestRequest):
    svc = get_user_profile_service()
    if svc is None:
        raise HTTPException(status_code=503, detail="UserProfileService not initialised — Redis unavailable.")
    try:
        profile = svc.update_user_interest(user_id, request.attribute, request.weight)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if profile is None:
        raise HTTPException(status_code=500, detail="Failed to persist interest update.")
    return profile


@router.get(
    "/{user_id}/top-interests",
    response_model=List[InterestItem],
    summary="Get user interests sorted by weight (highest first)",
)
async def get_top_interests(user_id: str):
    svc = get_user_profile_service()
    if svc is None:
        raise HTTPException(status_code=503, detail="UserProfileService not initialised — Redis unavailable.")
    profile = svc.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"No dynamic profile found for user '{user_id}'.",
        )
    return svc.get_top_interests(user_id)


@router.get(
    "/interests/categories",
    summary="List all valid interest category names",
)
async def get_interest_categories():
    return {
        "categories": INTEREST_CATEGORIES,
        "count": len(INTEREST_CATEGORIES),
    }
