"""Unit tests for services/bureaucracy_service.py — hardened version."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.bureaucracy_service import BureaucracyService
from app.ai.llm_client import LLMClientError


@pytest.fixture
def mock_rag():
    rag = AsyncMock()
    rag.query.return_value = "Augmented prompt with context about Skatteverket"
    return rag


@pytest.fixture
def mock_llm():
    llm = MagicMock()

    async def fake_stream(*args, **kwargs):
        for token in ["To register ", "at Skatteverket, ", "you need..."]:
            yield token

    llm.stream = MagicMock(return_value=fake_stream())
    return llm


@pytest.fixture
def service(mock_rag, mock_llm):
    """BureaucracyService with no Firestore (db=None)."""
    return BureaucracyService(
        rag_pipeline=mock_rag,
        llm_client=mock_llm,
        firestore_client=None,
    )


@pytest.mark.asyncio
async def test_stream_chat_yields_tokens(service, mock_rag):
    tokens = []
    async for token in service.stream_chat(
        user_id="user123",
        conversation_id="conv456",
        message="How do I register at Skatteverket?",
    ):
        tokens.append(token)

    assert len(tokens) == 3
    assert "".join(tokens) == "To register at Skatteverket, you need..."
    mock_rag.query.assert_called_once()


@pytest.mark.asyncio
async def test_stream_chat_creates_conversation_when_none(service):
    tokens = []
    async for token in service.stream_chat(
        user_id="user123",
        conversation_id=None,
        message="Hello",
    ):
        tokens.append(token)

    assert len(tokens) > 0


@pytest.mark.asyncio
async def test_stream_chat_handles_llm_error(mock_rag):
    """When LLM raises an error mid-stream, service should yield an error message."""
    llm = MagicMock()

    async def failing_stream(*args, **kwargs):
        yield "partial "
        raise LLMClientError("Rate limit exceeded", code="RATE_LIMITED")

    llm.stream = MagicMock(return_value=failing_stream())

    service = BureaucracyService(
        rag_pipeline=mock_rag,
        llm_client=llm,
        firestore_client=None,
    )

    tokens = []
    async for token in service.stream_chat("user1", "conv1", "test"):
        tokens.append(token)

    full_response = "".join(tokens)
    assert "partial" in full_response
    assert "Rate limit exceeded" in full_response


@pytest.mark.asyncio
async def test_get_conversations_without_firestore(service):
    result = await service.get_conversations("user123")
    assert result == []


@pytest.mark.asyncio
async def test_create_conversation_returns_uuid(service):
    """_create_conversation should return a valid UUID string."""
    conv_id = await service._create_conversation("user123")
    assert len(conv_id) == 36  # UUID format
    assert "-" in conv_id


@pytest.mark.asyncio
async def test_load_chat_history_returns_empty_without_firestore(service):
    result = await service._load_chat_history("user123", "conv456")
    assert result == []
