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
    with client.websocket_connect("/ws/jobs") as websocket:
        # Connect successfully
        data = websocket.receive_json()
        assert data["status"] == "connected"


def test_websocket_connection_and_disconnect(client):
    """Test WebSocket connection and disconnection."""
    with client.websocket_connect("/ws/jobs") as websocket:
        # Receive connection confirmation
        data = websocket.receive_json()
        assert data["status"] == "connected"
        # Connection closes cleanly when exiting context


def test_websocket_multiple_connections(client):
    """Test multiple concurrent WebSocket connections."""
    with client.websocket_connect("/ws/jobs") as ws1:
        data1 = ws1.receive_json()
        assert data1["status"] == "connected"

        with client.websocket_connect("/ws/jobs") as ws2:
            data2 = ws2.receive_json()
            assert data2["status"] == "connected"
