"""
Wellbeing API — endpoints for accessing wellbeing data.

Endpoints:
- GET    /wellbeing/summary    — current risk level and top categories
- GET    /wellbeing/signals    — recent wellbeing signals
- DELETE /wellbeing/data       — right-to-delete all wellbeing data
"""

import logging

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.core.dependencies import get_wellbeing_service
from app.schemas.wellbeing import WellbeingSummaryResponse
from app.services.wellbeing_service import WellbeingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wellbeing", tags=["wellbeing"])

DISCLAIMER = (
    "This is not a medical or psychological assessment. "
    "If you are in crisis, please contact emergency services (112) "
    "or the national helpline (Mind: 90101)."
)


@router.get("/summary", response_model=WellbeingSummaryResponse)
async def get_summary(
    user: dict = Depends(get_current_user),
    service: WellbeingService = Depends(get_wellbeing_service),
):
    """Get the current wellbeing summary for the authenticated user."""
    summary = await service.get_summary(user["uid"])
    return WellbeingSummaryResponse(
        **summary,
        disclaimer=DISCLAIMER,
    )


@router.get("/signals")
async def get_signals(
    limit: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user),
    service: WellbeingService = Depends(get_wellbeing_service),
):
    """List recent wellbeing signals."""
    signals = await service.get_signals(user["uid"], limit=limit)
    return {
        "signals": signals,
        "count": len(signals),
        "disclaimer": DISCLAIMER,
    }


@router.delete("/data")
async def delete_wellbeing_data(
    user: dict = Depends(get_current_user),
    service: WellbeingService = Depends(get_wellbeing_service),
):
    """Delete all wellbeing data for the authenticated user (GDPR right-to-delete)."""
    success = await service.delete_data(user["uid"])
    return {
        "status": "deleted" if success else "no_data",
        "message": "All wellbeing data has been deleted.",
    }
