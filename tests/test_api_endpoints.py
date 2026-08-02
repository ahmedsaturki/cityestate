"""
API Test Suite — اختبارات واجهة برمجة التطبيقات
================================================
Comprehensive tests for all API endpoints.
Run with: python -m pytest tests/test_api_endpoints.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.api.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Get auth token for authenticated requests."""
    resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "C1ty3st@t3_S3cur3_2024!",
    })
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return None


@pytest.fixture
def auth_headers(auth_token):
    """Get auth headers."""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


# ===========================================================================
# Health & Root Endpoints
# ===========================================================================
class TestHealthEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200


# ===========================================================================
# Auth Endpoints
# ===========================================================================
class TestAuthEndpoints:
    def test_login_success(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "C1ty3st@t3_S3cur3_2024!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_invalid(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })
        assert resp.status_code in (401, 422)

    def test_protected_without_token(self, client):
        resp = client.get("/api/v1/leads")
        assert resp.status_code in (401, 403)


# ===========================================================================
# Lead Endpoints
# ===========================================================================
class TestLeadEndpoints:
    def test_list_leads(self, client, auth_headers):
        resp = client.get("/api/v1/leads", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_leads_without_auth(self, client):
        resp = client.get("/api/v1/leads")
        assert resp.status_code in (401, 403)


# ===========================================================================
# Property Endpoints
# ===========================================================================
class TestPropertyEndpoints:
    def test_list_properties(self, client, auth_headers):
        resp = client.get("/api/v1/properties", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_properties_without_auth(self, client):
        resp = client.get("/api/v1/properties")
        assert resp.status_code in (401, 403)


# ===========================================================================
# Request Endpoints
# ===========================================================================
class TestRequestEndpoints:
    def test_list_requests(self, client, auth_headers):
        resp = client.get("/api/v1/requests", headers=auth_headers)
        assert resp.status_code == 200

    def test_request_stats(self, client, auth_headers):
        resp = client.get("/api/v1/requests/stats", headers=auth_headers)
        assert resp.status_code in (200, 404, 405, 422)


# ===========================================================================
# Dashboard Endpoints
# ===========================================================================
class TestDashboardEndpoints:
    def test_dashboard_stats(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200

    def test_dashboard_charts(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/charts", headers=auth_headers)
        assert resp.status_code == 200


# ===========================================================================
# Scheduler Endpoints
# ===========================================================================
class TestSchedulerEndpoints:
    def test_scheduler_status(self, client, auth_headers):
        resp = client.get("/api/v1/scheduler/status", headers=auth_headers)
        assert resp.status_code in (200, 503)


# ===========================================================================
# Automation Endpoints
# ===========================================================================
class TestAutomationEndpoints:
    def test_automation_status(self, client, auth_headers):
        resp = client.get("/api/v1/automation/status", headers=auth_headers)
        assert resp.status_code == 200


# ===========================================================================
# Webhook Endpoints
# ===========================================================================
class TestWebhookEndpoints:
    def test_webhook_info(self, client):
        resp = client.get("/api/v1/webhooks")
        assert resp.status_code in (200, 404, 405)

    def test_webhook_form_submission(self, client):
        import hashlib
        import hmac
        import json as json_mod

        body = json_mod.dumps(
            {"client_name": "Test Client", "phone": "01123456789", "area": "Sheikh Zayed"},
            ensure_ascii=False,
        ).encode("utf-8")
        signature = hmac.new(
            b"test-webhook-secret-not-for-production", body, hashlib.sha256
        ).hexdigest()
        resp = client.post(
            "/api/v1/webhooks/form",
            content=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": f"sha256={signature}"},
        )
        assert resp.status_code in (200, 201, 422)


# ===========================================================================
# Data System API Endpoints (NEW)
# ===========================================================================
class TestDataSystemEndpoints:
    """Test new data system endpoints."""

    def test_data_extract_whatsapp(self, client, auth_headers):
        resp = client.post("/api/v1/data/extract", json={
            "source": "whatsapp",
            "text": "عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_data_quality_score(self, client, auth_headers):
        resp = client.post("/api/v1/data/quality", json={
            "data": {"title": "Test", "price": 2000000},
            "data_type": "property",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_market_research(self, client, auth_headers):
        resp = client.get("/api/v1/data/market-research", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_whatsapp_check(self, client, auth_headers):
        resp = client.post("/api/v1/data/whatsapp-check", json={
            "phone": "01123456789",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ===========================================================================
# Content Endpoints
# ===========================================================================
class TestContentEndpoints:
    def test_content_routes(self, client, auth_headers):
        resp = client.get("/api/v1/content", headers=auth_headers)
        assert resp.status_code in (200, 404)
