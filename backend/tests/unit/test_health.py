"""Unit tests for the health and readiness endpoints."""

from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_liveness_check():
    """Liveness probe should return ok with version and uptime."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data


def test_readiness_check():
    """Readiness probe should return checks for all subsystems."""
    response = client.get(f"{settings.API_V1_STR}/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "model_loaded" in data["checks"]
    assert data["status"] in ("ok", "degraded")
