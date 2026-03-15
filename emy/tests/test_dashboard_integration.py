import pytest
from fastapi.testclient import TestClient
from emy.gateway.api import app

client = TestClient(app)

def test_dashboard_full_cycle():
    """Test: Load dashboard → see metrics displayed"""

    # 1. Load dashboard
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Emy Dashboard" in response.text
    assert "metric-real-time" in response.text
    assert "agents-stack" in response.text

def test_metrics_api_returns_all_data():
    """Test: GET /api/metrics returns complete response"""

    response = client.get("/api/metrics")
    assert response.status_code == 200

    data = response.json()

    # Verify top-level structure
    assert "timestamp" in data
    assert "agents" in data
    assert "workflows" in data
    assert "budget" in data
    assert "system" in data

    # Verify agents
    assert isinstance(data["agents"], list)
    assert len(data["agents"]) == 3  # TradingAgent, ResearchAgent, KnowledgeAgent
    for agent in data["agents"]:
        assert "name" in agent
        assert "status" in agent
        assert agent["status"] in ["healthy", "executing", "error", "disabled"]
        assert "last_execution" in agent
        assert "execution_count_today" in agent
        assert "last_result_summary" in agent

    # Verify workflows
    assert isinstance(data["workflows"]["recent"], list)
    assert "total_today" in data["workflows"]
    assert "completed" in data["workflows"]
    assert "failed" in data["workflows"]
    assert "running" in data["workflows"]

    # Verify budget
    assert data["budget"]["daily_limit"] == 10.0
    assert data["budget"]["spent_today"] >= 0
    assert 0 <= data["budget"]["percentage_used"] <= 100
    assert data["budget"]["remaining"] >= 0

    # Verify system
    assert data["system"]["response_time_ms"] >= 0
    assert data["system"]["db_disk_usage_gb"] >= 0
    assert data["system"]["db_disk_limit_gb"] == 2.0
    assert data["system"]["status"] in ["ok", "warning", "error"]

def test_dashboard_css_loads():
    """Test that CSS file is served correctly"""
    response = client.get("/static/dashboard.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "--bg:" in response.text or "var(--bg)" in response.text or "background" in response.text

def test_dashboard_js_loads():
    """Test that JS file is served correctly"""
    response = client.get("/static/dashboard.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "connectWebSocket" in response.text or "updateMetrics" in response.text or "fetch" in response.text

def test_websocket_connection_and_message():
    """Test: WebSocket connects and receives initial message"""
    with client.websocket_connect("/ws/metrics") as websocket:
        # Should receive initial system metrics
        data = websocket.receive_json(mode="text")
        assert "event" in data
        assert data["event"] == "system_metrics"
        assert "timestamp" in data
        assert "data" in data
        assert "response_time_ms" in data["data"]
        assert "db_usage_percentage" in data["data"]
        assert "status" in data["data"]

def test_all_dashboard_components_together():
    """Test: All dashboard components work together"""

    # 1. Dashboard HTML loads
    html_response = client.get("/dashboard")
    assert html_response.status_code == 200

    # 2. CSS loads
    css_response = client.get("/static/dashboard.css")
    assert css_response.status_code == 200

    # 3. JS loads
    js_response = client.get("/static/dashboard.js")
    assert js_response.status_code == 200

    # 4. Metrics API works
    metrics_response = client.get("/api/metrics")
    assert metrics_response.status_code == 200
    metrics_data = metrics_response.json()
    assert len(metrics_data["agents"]) == 3

    # 5. WebSocket works
    with client.websocket_connect("/ws/metrics") as websocket:
        data = websocket.receive_json(mode="text")
        assert data["event"] == "system_metrics"
