"""Unit tests for core/middleware.py"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import CorrelationIdMiddleware, correlation_id_var


@pytest.fixture
def test_app():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"correlation_id": correlation_id_var.get("-")}

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_generates_correlation_id_if_not_provided(client):
    response = client.get("/test")
    assert response.status_code == 200
    # X-Request-ID should be in response headers
    assert "x-request-id" in response.headers
    # Should be a UUID-like string
    assert len(response.headers["x-request-id"]) == 36


def test_uses_provided_correlation_id(client):
    custom_id = "my-custom-request-id"
    response = client.get("/test", headers={"x-request-id": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id


def test_correlation_id_available_in_endpoint(client):
    custom_id = "test-123"
    response = client.get("/test", headers={"x-request-id": custom_id})
    data = response.json()
    assert data["correlation_id"] == custom_id
