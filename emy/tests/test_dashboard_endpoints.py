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

def test_metrics_endpoint_returns_json():
    """Test that GET /api/metrics returns valid JSON"""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert "timestamp" in data
    assert "agents" in data
    assert "workflows" in data
    assert "budget" in data
    assert "system" in data

def test_metrics_agents_structure():
    """Test that agents have required fields"""
    response = client.get("/api/metrics")
    data = response.json()

    assert isinstance(data["agents"], list)
    assert len(data["agents"]) >= 0

    if len(data["agents"]) > 0:
        agent = data["agents"][0]
        assert "name" in agent
        assert "status" in agent
        assert "last_execution" in agent
        assert "execution_count_today" in agent

def test_metrics_workflows_structure():
    """Test that workflows have required fields"""
    response = client.get("/api/metrics")
    data = response.json()

    assert "total_today" in data["workflows"]
    assert "running" in data["workflows"]
    assert "completed" in data["workflows"]
    assert "failed" in data["workflows"]
    assert "recent" in data["workflows"]

def test_metrics_budget_structure():
    """Test that budget has required fields"""
    response = client.get("/api/metrics")
    data = response.json()

    budget = data["budget"]
    assert "daily_limit" in budget
    assert "spent_today" in budget
    assert "percentage_used" in budget
    assert "remaining" in budget
