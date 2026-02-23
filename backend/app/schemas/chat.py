from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(
        default=None,
        description="Existing conversation ID. If None, a new conversation is created.",
    )


class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = Field(default_factory=list)


class ConversationMetadata(BaseModel):
    """Metadata about a conversation."""
    conversation_id: str
    title: str = "New Conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0


class StreamEvent(BaseModel):
    """A single event in the SSE stream."""
    token: Optional[str] = None
    done: bool = False
    error: bool = False
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    conversation_id: Optional[str] = None
