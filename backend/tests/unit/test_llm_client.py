"""Unit tests for ai/llm_client.py — hardened version."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.llm_client import (
    LLMClient,
    LLMClientError,
    LLMContentFilterError,
    LLMTimeoutError,
    _backoff_with_jitter,
)


@pytest.fixture
def llm_client():
    """Create an LLMClient with a fake API key."""
    with patch("app.ai.llm_client.genai") as mock_genai:
        client = LLMClient(
            model_name="gemini-2.0-flash",
            api_key="fake-api-key",
            timeout=5.0,
            max_retries=2,
        )
        yield client, mock_genai


# --- backoff_with_jitter ---


def test_backoff_with_jitter_increases():
    """Backoff should grow exponentially."""
    b0 = _backoff_with_jitter(0)
    b1 = _backoff_with_jitter(1)
    b2 = _backoff_with_jitter(2)
    # Base values are 1, 2, 4 — with jitter up to +0.5
    assert 1.0 <= b0 <= 1.5
    assert 2.0 <= b1 <= 2.5
    assert 4.0 <= b2 <= 4.5


def test_backoff_with_jitter_is_non_deterministic():
    """Two calls with the same attempt should produce different values (usually)."""
    results = {_backoff_with_jitter(1) for _ in range(20)}
    assert len(results) > 1  # With jitter, we expect variance


# --- generate() ---


@pytest.mark.asyncio
async def test_generate_success(llm_client):
    client, mock_genai = llm_client
    mock_response = MagicMock()
    mock_response.text = "Hello, I can help with Skatteverket."

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    mock_genai.GenerativeModel.return_value = mock_model
    client._model = mock_model

    result = await client.generate("How do I register at Skatteverket?")
    assert result == "Hello, I can help with Skatteverket."


@pytest.mark.asyncio
async def test_generate_timeout_raises(llm_client):
    client, mock_genai = llm_client

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(side_effect=asyncio.TimeoutError)
    client._model = mock_model

    with pytest.raises(LLMTimeoutError):
        await client.generate("test prompt")


@pytest.mark.asyncio
async def test_generate_content_filter_raises(llm_client):
    client, mock_genai = llm_client

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=Exception("Content was blocked by safety filters")
    )
    client._model = mock_model

    with pytest.raises(LLMContentFilterError):
        await client.generate("test prompt")


# --- stream() ---


@pytest.mark.asyncio
async def test_stream_yields_tokens(llm_client):
    client, mock_genai = llm_client

    chunk1 = MagicMock()
    chunk1.text = "Hello"
    chunk2 = MagicMock()
    chunk2.text = " world"

    async def mock_aiter():
        for c in [chunk1, chunk2]:
            yield c

    mock_response = mock_aiter()
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    client._model = mock_model

    tokens = []
    async for token in client.stream("test prompt"):
        tokens.append(token)

    assert tokens == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_timeout_raises(llm_client):
    client, mock_genai = llm_client

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(side_effect=asyncio.TimeoutError)
    client._model = mock_model

    with pytest.raises(LLMTimeoutError):
        async for _ in client.stream("test prompt"):
            pass


@pytest.mark.asyncio
async def test_stream_per_chunk_timeout():
    """If a chunk stalls beyond PER_CHUNK_TIMEOUT, it should raise."""
    async def stalling_aiter():
        yield MagicMock(text="ok")
        await asyncio.sleep(999)  # simulate stall
        yield MagicMock(text="never reached")

    with pytest.raises(LLMTimeoutError) as exc_info:
        async for _ in LLMClient._iter_with_chunk_timeout(stalling_aiter(), timeout=0.1):
            pass

    assert "stalled" in str(exc_info.value.message).lower()
