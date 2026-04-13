"""Tests for the health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from src.app.main import app


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["mode"] == "local"
