"""Unit tests for services/wellbeing_service.py"""

import pytest

from app.services.wellbeing_service import WellbeingService


@pytest.fixture
def service():
    """WellbeingService with no Firestore."""
    return WellbeingService(firestore_client=None)


@pytest.mark.asyncio
async def test_get_summary_without_firestore(service):
    result = await service.get_summary("user1")
    assert result["current_risk_level"] == "low"
    assert result["current_risk_score"] == 0


@pytest.mark.asyncio
async def test_get_signals_without_firestore(service):
    result = await service.get_signals("user1")
    assert result == []


@pytest.mark.asyncio
async def test_delete_data_without_firestore(service):
    result = await service.delete_data("user1")
    assert result is False


@pytest.mark.asyncio
async def test_process_classification_without_firestore(service):
    """Should silently return when no Firestore available."""
    from app.schemas.wellbeing import WellbeingClassification, WellbeingSignal

    classification = WellbeingClassification(
        signals=[
            WellbeingSignal(
                category="social_isolation",
                intensity="moderate",
                confidence=0.8,
                trigger_quote="I feel alone",
            )
        ],
        overall_sentiment="concerned",
        urgency="low",
    )

    # Should not raise
    await service.process_classification(
        "user1", "conv1", "I feel alone", classification
    )
