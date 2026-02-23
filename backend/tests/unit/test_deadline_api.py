"""Unit tests for api/v1/deadlines.py"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def mock_deadline_deps():
    """Override dependencies for deadline endpoints."""
    from app.core.dependencies import get_deadline_service
    from app.core.security import get_current_user

    mock_user = {"uid": "test-user-123", "email": "test@example.com"}

    mock_service = MagicMock()
    mock_service.get_deadlines = AsyncMock(return_value=[
        {
            "deadline_id": "dl-1",
            "agency": "Skatteverket",
            "action": "Register for personnummer",
            "urgency": "critical",
            "status": "active",
        },
    ])
    mock_service.update_deadline_status = AsyncMock(return_value=True)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_deadline_service] = lambda: mock_service

    yield mock_service, mock_user

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_list_deadlines(client, mock_deadline_deps):
    """GET /api/v1/deadlines should return user's deadlines."""
    response = client.get(
        f"{settings.API_V1_STR}/deadlines",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "deadlines" in data
    assert data["count"] == 1
    assert data["deadlines"][0]["agency"] == "Skatteverket"


def test_list_deadlines_requires_auth(client):
    """Deadline endpoint should reject unauthenticated requests."""
    app.dependency_overrides.clear()
    response = client.get(f"{settings.API_V1_STR}/deadlines")
    assert response.status_code in (401, 403)


def test_update_deadline_status(client, mock_deadline_deps):
    """PATCH /api/v1/deadlines/{id} should update status."""
    response = client.patch(
        f"{settings.API_V1_STR}/deadlines/dl-1",
        json={"status": "completed"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_status"] == "completed"


def test_update_deadline_not_found(client, mock_deadline_deps):
    """Should return 404 if deadline doesn't exist."""
    mock_service, _ = mock_deadline_deps
    mock_service.update_deadline_status = AsyncMock(return_value=False)

    response = client.patch(
        f"{settings.API_V1_STR}/deadlines/nonexistent",
        json={"status": "dismissed"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 404


def test_update_deadline_invalid_status(client, mock_deadline_deps):
    """Should reject invalid status values."""
    response = client.patch(
        f"{settings.API_V1_STR}/deadlines/dl-1",
        json={"status": "invalid_status"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422
