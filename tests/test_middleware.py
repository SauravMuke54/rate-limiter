"""
Tests for RateLimitMiddleware — exempt paths, route resolution errors,
and rate-limit rejection responses.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from rate_limit_middleware import RateLimitMiddleware


def build_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/{path:path}")
    async def catchall(path: str):
        return {"path": path}

    return app


@pytest.fixture
def client():
    return TestClient(build_app())


def test_exempt_path_bypasses_rate_limit(client):
    """/health should never hit resolve_route or check_rate_limit."""
    with patch("rate_limit_middleware.resolve_route") as mock_resolve:
        response = client.get("/health")
        assert response.status_code == 200
        mock_resolve.assert_not_called()


def test_resolve_route_exception_returns_502(client):
    with patch("rate_limit_middleware.resolve_route", side_effect=Exception("boom")):
        response = client.get("/some/path")
        assert response.status_code == 502
        assert "error" in response.json()


def test_no_route_config_returns_404(client):
    with patch("rate_limit_middleware.resolve_route", return_value=None):
        response = client.get("/some/path")
        assert response.status_code == 404


def test_rate_limit_exceeded_returns_429_with_headers(client):
    fake_route_cfg = {"upstream": "http://upstream", "limit": 5, "window": 60}
    with (
        patch("rate_limit_middleware.resolve_route", return_value=fake_route_cfg),
        patch(
            "rate_limit_middleware.check_rate_limit",
            new=AsyncMock(return_value=(False, 0, 42)),
        ),
    ):
        response = client.get("/some/path")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "42"
        assert response.json()["error"] == "Rate limit exceeded"


def test_allowed_request_sets_rate_limit_headers(client):
    fake_route_cfg = {"upstream": "http://upstream", "limit": 5, "window": 60}
    with (
        patch("rate_limit_middleware.resolve_route", return_value=fake_route_cfg),
        patch(
            "rate_limit_middleware.check_rate_limit",
            new=AsyncMock(return_value=(True, 3, 30)),
        ),
    ):
        response = client.get("/some/path")
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "3"
        assert response.headers["X-RateLimit-Reset"] == "30"
