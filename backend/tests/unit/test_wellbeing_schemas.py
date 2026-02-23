"""Unit tests for schemas/wellbeing.py"""

import pytest
from pydantic import ValidationError

from app.schemas.wellbeing import (
    WellbeingSignal,
    WellbeingClassification,
    WellbeingSummaryResponse,
    RiskAssessment,
)


def test_valid_signal():
    signal = WellbeingSignal(
        category="social_isolation",
        intensity="moderate",
        confidence=0.85,
        trigger_quote="I don't know anyone here",
    )
    assert signal.category == "social_isolation"
    assert signal.confidence == 0.85


def test_signal_rejects_invalid_category():
    with pytest.raises(ValidationError):
        WellbeingSignal(
            category="invalid_category",
            intensity="mild",
            confidence=0.5,
            trigger_quote="test",
        )


def test_signal_rejects_invalid_intensity():
    with pytest.raises(ValidationError):
        WellbeingSignal(
            category="homesickness",
            intensity="extreme",  # not valid
            confidence=0.5,
            trigger_quote="test",
        )


def test_signal_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        WellbeingSignal(
            category="homesickness",
            intensity="mild",
            confidence=1.5,  # > 1.0
            trigger_quote="test",
        )


def test_classification_empty_signals():
    classification = WellbeingClassification(
        signals=[],
        overall_sentiment="neutral",
        urgency="none",
    )
    assert len(classification.signals) == 0


def test_classification_valid():
    classification = WellbeingClassification(
        signals=[
            WellbeingSignal(
                category="academic_stress",
                intensity="severe",
                confidence=0.9,
                trigger_quote="I'm failing my thesis",
            )
        ],
        overall_sentiment="distressed",
        urgency="high",
    )
    assert len(classification.signals) == 1
    assert classification.urgency == "high"


def test_risk_assessment_bounds():
    with pytest.raises(ValidationError):
        RiskAssessment(risk_score=101, risk_level="high")

    with pytest.raises(ValidationError):
        RiskAssessment(risk_score=-1, risk_level="low")


def test_summary_response_has_disclaimer():
    summary = WellbeingSummaryResponse()
    assert "not a medical" in summary.disclaimer
    assert summary.current_risk_level == "low"
