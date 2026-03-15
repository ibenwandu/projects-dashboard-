import pytest
from fastapi.testclient import TestClient
from emy.gateway.api import app

client = TestClient(app)

def test_dashboard_endpoint_returns_html():
    """Test that GET /dashboard returns HTML content"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Emy Dashboard" in response.text
    assert "metric-real-time" in response.text  # Check for dashboard elements

def test_dashboard_serves_from_templates():
    """Test that dashboard is served from templates directory"""
    response = client.get("/dashboard")
    assert "Active Agents" in response.text
    assert "dashboard.js" in response.text  # Should link to JS
    assert "dashboard.css" in response.text  # Should link to CSS
