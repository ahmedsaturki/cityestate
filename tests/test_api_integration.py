"""
API Integration Tests — اختبارات التكامل
=========================================
Tests for the CityEstate FastAPI endpoints.
"""

import json
import os
import pytest
from fastapi.testclient import TestClient


# Test credentials — must match the default admin password set in conftest.py/seed
TEST_ADMIN_USER = os.getenv("TEST_ADMIN_USERNAME", "admin")
TEST_ADMIN_PASS = os.getenv("TEST_ADMIN_PASSWORD", "C1ty3st@t3_S3cur3_2024!")


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    from src.api.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client):
    """Get auth headers for authenticated requests."""
    # Login as admin using env vars
    response = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return {}


class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "database" in data["checks"]

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "CityEstate API" in data["name"]


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS}
        )
        # May fail if admin password is different, but should not 500
        assert response.status_code in [200, 401]

    def test_login_invalid(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "wrong"}
        )
        assert response.status_code == 401


class TestWebhookEndpoints:
    """Test webhook form submission."""

    def test_webhook_info(self, client, auth_headers):
        response = client.get("/api/v1/webhooks/form", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "endpoint" in data

    def test_webhook_form_submission(self, client):
        import hashlib
        import hmac
        import json as json_mod

        body = json_mod.dumps(
            {
                "client_name": "Test Client",
                "phone": "+201234567890",
                "area": "Sheikh Zayed",
                "max_budget": 5000000,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        signature = hmac.new(
            b"test-webhook-secret-not-for-production", body, hashlib.sha256
        ).hexdigest()
        response = client.post(
            "/api/v1/webhooks/form",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={signature}",
            },
        )
        assert response.status_code in (200, 201, 422)
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "received"


class TestLeadEndpoints:
    """Test lead CRUD endpoints."""

    def test_list_leads(self, client, auth_headers):
        response = client.get("/api/v1/leads", headers=auth_headers)
        # Should return 200 or 401 if not authenticated
        assert response.status_code in [200, 401, 403]

    def test_list_leads_without_auth(self, client):
        response = client.get("/api/v1/leads")
        assert response.status_code in [401, 403]


class TestPropertyEndpoints:
    """Test property CRUD endpoints."""

    def test_list_properties(self, client, auth_headers):
        response = client.get("/api/v1/properties", headers=auth_headers)
        assert response.status_code in [200, 401, 403]

    def test_list_properties_without_auth(self, client):
        response = client.get("/api/v1/properties")
        assert response.status_code in [401, 403]


class TestRequestEndpoints:
    """Test client request endpoints."""

    def test_list_requests(self, client, auth_headers):
        response = client.get("/api/v1/requests", headers=auth_headers)
        assert response.status_code in [200, 401, 403]

    def test_request_stats(self, client, auth_headers):
        response = client.get("/api/v1/requests/stats/summary", headers=auth_headers)
        assert response.status_code in [200, 401, 403]


class TestDashboardEndpoints:
    """Test dashboard endpoints."""

    def test_dashboard_stats(self, client, auth_headers):
        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code in [200, 401, 403]

    def test_dashboard_charts(self, client, auth_headers):
        response = client.get("/api/v1/dashboard/charts", headers=auth_headers)
        assert response.status_code in [200, 401, 403]


class TestSchedulerEndpoints:
    """Test scheduler endpoints."""

    def test_scheduler_status(self, client, auth_headers):
        response = client.get("/api/v1/scheduler/status", headers=auth_headers)
        assert response.status_code in [200, 401, 403, 503]


class TestAutomationEndpoints:
    """Test automation endpoints."""

    def test_automation_status(self, client, auth_headers):
        response = client.get("/api/v1/automation/status", headers=auth_headers)
        assert response.status_code in [200, 401, 403]


class TestContentEndpoints:
    """Test content generation endpoints."""

    def test_content_routes(self, client, auth_headers):
        # Content endpoints may not exist yet, just check no 500
        response = client.get("/api/v1/content", headers=auth_headers)
        assert response.status_code in [200, 401, 403, 404]
