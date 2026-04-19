"""Tests for API endpoints."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add backend to path 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client():
    """Create a test client with ADMIN_API_KEY set."""
    import os
    os.environ["ADMIN_API_KEY"] = "test-secret-key"
    
    # Need to reimport to pick up env var
    import importlib
    import main as main_module
    importlib.reload(main_module)
    
    return TestClient(main_module.app)


class TestHealthEndpoint:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "Vector Wealth" in data["name"]


class TestAnalyzeEndpoint:
    def test_empty_ticker_returns_422(self, client):
        response = client.post("/analyze", json={})
        assert response.status_code == 422

    def test_missing_body_returns_422(self, client):
        response = client.post("/analyze")
        assert response.status_code == 422


class TestAdminAuth:
    def test_admin_no_key_returns_401(self, client):
        response = client.get("/admin/live-news/status")
        assert response.status_code == 401

    def test_admin_wrong_key_returns_401(self, client):
        response = client.get(
            "/admin/live-news/status",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_admin_correct_key_returns_200(self, client):
        response = client.get(
            "/admin/live-news/status",
            headers={"X-Admin-Key": "test-secret-key"},
        )
        assert response.status_code == 200


class TestOpportunityEndpoints:
    def test_get_opportunities(self, client):
        response = client.get("/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert "opportunities" in data
        assert "is_market_hours" in data

    def test_get_scanner_status(self, client):
        response = client.get("/opportunities/status")
        assert response.status_code == 200
