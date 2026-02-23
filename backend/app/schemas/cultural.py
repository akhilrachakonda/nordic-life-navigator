"""Pydantic V2 schemas for the cultural interpretation module."""

from typing import Literal

from pydantic import BaseModel, Field


class CulturalAnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Message or email to analyze",
    )
    context: str = Field(
        default="workplace",
        description="Context: workplace, social, academic, housing",
    )


class CulturalSignal(BaseModel):
    concept: str = Field(
        ...,
        description="Swedish cultural concept e.g. lagom, fika",
    )
    explanation: str
    relevance: str = Field(
        ...,
        description="Why this concept applies to the text",
    )


class CulturalAnalysisResponse(BaseModel):
    tone_category: Literal[
        "direct",
        "indirect",
        "formal",
        "informal",
        "passive-aggressive",
        "warm",
    ]
    directness_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="1=very indirect, 10=very direct",
    )
    implied_meaning: str = Field(
        ...,
        description="What the sender likely means beyond literal words",
    )
    cultural_signals: list[CulturalSignal]
    suggested_response_tone: str
    summary: str


class RewriteRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=3000,
        description="User's draft message to rewrite",
    )
    target_register: Literal[
        "professional",
        "friendly-professional",
        "formal",
    ] = "professional"
    context: str = Field(default="workplace email")


class RewriteResponse(BaseModel):
    original: str
    rewritten: str
    changes_made: list[str] = Field(
        ...,
        description="List of changes and why",
    )
    tone_achieved: str
