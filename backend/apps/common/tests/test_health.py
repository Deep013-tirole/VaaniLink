"""
Tests for system health check endpoints.
"""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealthEndpoints:
    def setup_method(self):
        self.client = APIClient()

    def test_ping_endpoint(self):
        response = self.client.get("/api/v1/ping/")
        assert response.status_code == 200
        assert response.data == {"status": "ok", "service": "vaanilink-backend"}

    def test_health_check_healthy(self):
        response = self.client.get("/api/v1/health/")
        assert response.status_code == 200
        assert response.data["status"] == "healthy"
        assert response.data["components"]["database"] == "healthy"
        assert response.data["components"]["cache"] == "healthy"
