"""Unit tests for api/v1/bureaucracy.py — hardened version."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def mock_deps():
    """Override all dependencies for the bureaucracy endpoint."""
    from app.core.dependencies import get_bureaucracy_service
    from app.core.security import get_current_user

    mock_user = {"uid": "test-user-123", "email": "test@example.com"}

    mock_service = MagicMock()

    async def fake_stream(*args, **kwargs):
        for token in ["Hello", " from", " Nordic"]:
            yield token

    mock_service.stream_chat = MagicMock(return_value=fake_stream())
    mock_service.get_conversation_id.return_value = "conv-new-123"
    mock_service.get_conversations = AsyncMock(return_value=[
        {"conversation_id": "conv-1", "title": "Tax help"},
    ])

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_bureaucracy_service] = lambda: mock_service

    yield mock_service, mock_user

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_returns_sse_stream(client, mock_deps):
    """POST /api/v1/bureaucracy/chat should return an SSE stream."""
    response = client.post(
        f"{settings.API_V1_STR}/bureaucracy/chat",
        json={"message": "How do I get a personnummer?"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert "data:" in body
    assert "Hello" in body
    assert "Nordic" in body


def test_chat_requires_auth(client):
    """Chat endpoint should reject unauthenticated requests."""
    app.dependency_overrides.clear()

    response = client.post(
        f"{settings.API_V1_STR}/bureaucracy/chat",
        json={"message": "test"},
    )
    assert response.status_code in (401, 403)


def test_chat_validates_empty_message(client, mock_deps):
    """Chat endpoint should reject empty messages."""
    response = client.post(
        f"{settings.API_V1_STR}/bureaucracy/chat",
        json={"message": ""},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422


def test_list_conversations(client, mock_deps):
    """GET /api/v1/bureaucracy/conversations should return user conversations."""
    response = client.get(
        f"{settings.API_V1_STR}/bureaucracy/conversations",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert len(data["conversations"]) == 1
    assert data["conversations"][0]["title"] == "Tax help"


def test_rate_limiting_enforcement(client, mock_deps):
    """Rate limiter should kick in after exceeding the limit."""
    from app.core.rate_limiter import rate_limiter

    # Reset the rate limiter state for this test
    rate_limiter._requests.clear()

    # Set a very low limit for testing
    original_max = rate_limiter._max_requests
    rate_limiter._max_requests = 2

    try:
        for _ in range(2):
            response = client.post(
                f"{settings.API_V1_STR}/bureaucracy/chat",
                json={"message": "test"},
                headers={"Authorization": "Bearer fake-token"},
            )
            assert response.status_code == 200

        # Third request should be rate limited
        response = client.post(
            f"{settings.API_V1_STR}/bureaucracy/chat",
            json={"message": "test"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 429
    finally:
        rate_limiter._max_requests = original_max
        rate_limiter._requests.clear()
