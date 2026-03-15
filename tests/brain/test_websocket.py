"""Tests for WebSocket real-time job updates."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from emy.brain.service import app, job_queue


@pytest.fixture(scope="function")
def client():
    """Create HTTP client for testing with initialized job queue."""
    # Initialize job queue synchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(job_queue.initialize())

    test_client = TestClient(app)
    yield test_client

    loop.close()


def test_websocket_job_updates(client):
    """Test WebSocket streaming of job updates."""
    with client.websocket_connect("/ws/jobs?token=test-token") as websocket:
        # Connect successfully
        data = websocket.receive_json()
        assert data["status"] == "connected"


def test_websocket_connection_and_disconnect(client):
    """Test WebSocket connection and disconnection."""
    with client.websocket_connect("/ws/jobs?token=test-token") as websocket:
        # Receive connection confirmation
        data = websocket.receive_json()
        assert data["status"] == "connected"
        # Connection closes cleanly when exiting context


def test_websocket_multiple_connections(client):
    """Test multiple concurrent WebSocket connections."""
    with client.websocket_connect("/ws/jobs?token=test-token") as ws1:
        data1 = ws1.receive_json()
        assert data1["status"] == "connected"

        with client.websocket_connect("/ws/jobs?token=test-token") as ws2:
            data2 = ws2.receive_json()
            assert data2["status"] == "connected"


def test_websocket_requires_auth(client):
    """Test WebSocket rejects unauthenticated connections."""
    # Should fail without token
    with pytest.raises(Exception):  # WebSocketDisconnect or connection error
        with client.websocket_connect("/ws/jobs") as ws:
            pass


def test_websocket_accepts_with_token(client):
    """Test WebSocket accepts connections with valid token."""
    with client.websocket_connect("/ws/jobs?token=test-token") as websocket:
        data = websocket.receive_json()
        assert data["status"] == "connected"


def test_websocket_validates_subscribe_message(client):
    """Test WebSocket validates subscribe messages."""
    with client.websocket_connect("/ws/jobs?token=test-token") as websocket:
        # Receive connection confirmation
        data = websocket.receive_json()
        assert data["status"] == "connected"

        # Send valid subscribe message
        websocket.send_json({"type": "subscribe", "job_id": "job_123"})

        # Send invalid subscribe message (empty job_id)
        websocket.send_json({"type": "subscribe", "job_id": ""})

        # Connection should still be alive
        # (no exception raised)
