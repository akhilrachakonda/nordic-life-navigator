"""
Deadlines API — REST endpoints for managing extracted deadlines.

Endpoints:
- GET  /deadlines          — list user's deadlines
- PATCH /deadlines/{id}    — update status (complete/dismiss)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.core.dependencies import get_deadline_service
from app.schemas.deadline import DeadlineUpdate
from app.services.deadline_service import DeadlineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


@router.get("")
async def list_deadlines(
    status_filter: Optional[str] = Query(
        default="active",
        description="Filter by status: active, completed, dismissed, expired, or null for all",
    ),
    user: dict = Depends(get_current_user),
    service: DeadlineService = Depends(get_deadline_service),
):
    """List all deadlines for the authenticated user."""
    filter_val = status_filter if status_filter != "all" else None
    deadlines = await service.get_deadlines(user["uid"], status_filter=filter_val)
    return {"deadlines": deadlines, "count": len(deadlines)}


@router.patch("/{deadline_id}")
async def update_deadline(
    deadline_id: str,
    body: DeadlineUpdate,
    user: dict = Depends(get_current_user),
    service: DeadlineService = Depends(get_deadline_service),
):
    """Update a deadline's status (complete or dismiss)."""
    success = await service.update_deadline_status(
        user["uid"], deadline_id, body.status
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    return {"status": "updated", "deadline_id": deadline_id, "new_status": body.status}
