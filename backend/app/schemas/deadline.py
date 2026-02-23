"""Pydantic V2 schemas for deadline extraction and management."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Deadline(BaseModel):
    """A single extracted deadline from LLM output."""
    agency: str = Field(..., description="Swedish agency name")
    action: str = Field(..., description="What the user needs to do")
    deadline_date: Optional[date] = Field(
        default=None, description="ISO 8601 date if mentioned"
    )
    urgency: Literal["critical", "important", "informational"] = "informational"
    source_quote: str = Field(..., description="Exact text mentioning the deadline")


class ExtractionResult(BaseModel):
    """Result of deadline extraction from an LLM response."""
    deadlines: list[Deadline] = Field(default_factory=list)


class DeadlineRecord(BaseModel):
    """Full deadline record as stored in Firestore."""
    deadline_id: str
    agency: str
    action: str
    deadline_date: Optional[date] = None
    urgency: Literal["critical", "important", "informational"] = "informational"
    source_quote: str
    conversation_id: str
    status: Literal["active", "completed", "dismissed", "expired"] = "active"
    reminder_sent: bool = False
    reminder_task_id: Optional[str] = None
    fingerprint: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DeadlineUpdate(BaseModel):
    """Request body for updating a deadline's status."""
    status: Literal["completed", "dismissed"]
