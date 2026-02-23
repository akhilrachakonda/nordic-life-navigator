"""Cultural Interpretation API endpoints."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.core.dependencies import get_cultural_service
from app.schemas.cultural import (
    CulturalAnalysisRequest,
    CulturalAnalysisResponse,
    RewriteRequest,
    RewriteResponse,
)
from app.services.cultural_service import CulturalService

router = APIRouter(prefix="/cultural", tags=["cultural"])


@router.post("/analyze", response_model=CulturalAnalysisResponse)
async def analyze_message(
    body: CulturalAnalysisRequest,
    user: dict = Depends(get_current_user),
    service: CulturalService = Depends(get_cultural_service),
):
    """Analyze a message for Swedish cultural context and communication style."""
    return await service.analyze(body.text, body.context)


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_message(
    body: RewriteRequest,
    user: dict = Depends(get_current_user),
    service: CulturalService = Depends(get_cultural_service),
):
    """Rewrite user's draft in culturally appropriate Swedish professional style."""
    return await service.rewrite(body.text, body.target_register, body.context)
