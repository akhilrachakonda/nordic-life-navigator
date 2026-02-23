"""Pydantic V2 schemas for the wellbeing engine."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# --- Classification schemas ---

WELLBEING_CATEGORIES = (
    "cultural_confusion",
    "social_isolation",
    "academic_stress",
    "bureaucratic_stress",
    "financial_anxiety",
    "homesickness",
)


class WellbeingSignal(BaseModel):
    """A single detected wellbeing signal from user text."""
    category: Literal[
        "cultural_confusion", "social_isolation", "academic_stress",
        "bureaucratic_stress", "financial_anxiety", "homesickness",
    ]
    intensity: Literal["mild", "moderate", "severe"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    trigger_quote: str = Field(..., max_length=200)


class WellbeingClassification(BaseModel):
    """Result of wellbeing classification on user input."""
    signals: list[WellbeingSignal] = Field(default_factory=list)
    overall_sentiment: Literal["positive", "neutral", "concerned", "distressed"]
    urgency: Literal["none", "low", "medium", "high"]


# --- Risk score schemas ---

class RiskAssessment(BaseModel):
    """Computed risk score with level."""
    risk_score: int = Field(default=0, ge=0, le=100)
    risk_level: Literal["low", "medium", "high"] = "low"
    components: dict[str, float] = Field(default_factory=dict)


# --- API response schemas ---

class WellbeingSummaryResponse(BaseModel):
    """User-facing wellbeing summary."""
    current_risk_level: str = "low"
    current_risk_score: int = 0
    signal_count_7d: int = 0
    top_categories: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This is not a medical or psychological assessment. "
        "If you are in crisis, please contact emergency services (112) "
        "or the national helpline (Mind: 90101)."
    )


class WellbeingSignalRecord(BaseModel):
    """Signal as stored in Firestore."""
    signal_id: str
    category: str
    intensity: str
    confidence: float
    trigger_quote: str
    risk_score: int
    conversation_id: str
    created_at: datetime
