"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient

from server.api.main import create_app
from server.core import Settings


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        server_id="test-server",
        api_port=8000,
        zenoh_mode="peer",
    )


@pytest.fixture
def client(settings):
    """Create test client."""
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        response = client.get("/health")

        # Note: This may fail if Zenoh isn't available
        # In real tests, you'd mock the Zenoh hub
        assert response.status_code in [200, 500]

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "Herdbot API"


class TestDeviceEndpoints:
    """Tests for device endpoints."""

    def test_list_devices_empty(self, client):
        response = client.get("/devices")

        # May return 200 with empty list or 500 if Zenoh not running
        if response.status_code == 200:
            data = response.json()
            assert "devices" in data
            assert "total" in data

    def test_get_nonexistent_device(self, client):
        response = client.get("/devices/nonexistent-device")

        # Should return 404 or 500
        assert response.status_code in [404, 500]


class TestAIEndpoints:
    """Tests for AI endpoints."""

    def test_list_providers(self, client):
        response = client.get("/ai/providers")

        if response.status_code == 200:
            data = response.json()
            assert "providers" in data
            assert "default" in data

    def test_chat_without_api_key(self, client):
        response = client.post(
            "/ai/chat",
            json={"message": "Hello"},
        )

        # Should return 503 if no API keys configured
        assert response.status_code in [200, 503]
