import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from emy.gateway.api import app

client = TestClient(app)

def test_websocket_endpoint_exists():
    """Test that WebSocket endpoint can be connected"""
    with client.websocket_connect("/ws/metrics") as websocket:
        # Connection successful
        assert websocket is not None

def test_websocket_receives_messages():
    """Test that WebSocket sends system_metrics message"""
    with client.websocket_connect("/ws/metrics") as websocket:
        # Should receive system_metrics shortly
        data = websocket.receive_json(mode="text")
        assert "event" in data
        assert data["event"] in ["agent_status_change", "workflow_complete", "budget_update", "system_metrics"]
        assert "timestamp" in data
        assert "data" in data
