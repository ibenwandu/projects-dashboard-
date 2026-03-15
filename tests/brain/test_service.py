"""Tests for Emy Brain FastAPI service."""
import pytest
import pytest_asyncio
import asyncio
from fastapi.testclient import TestClient
from emy.brain.service import app, job_queue
from emy.brain.checkpoint import checkpoint_manager
from emy.brain.state import create_initial_state_with_groups


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


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_submit_job(client):
    """Test job submission endpoint."""
    job_data = {
        "workflow_type": "trading_health",
        "agents": ["TradingAgent"],
        "input": {"query": "Test query"}
    }

    response = client.post("/jobs", json=job_data)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["workflow_type"] == "trading_health"
    assert data["status"] == "pending"


def test_get_job_status(client):
    """Test getting job status."""
    # First submit a job
    job_data = {
        "workflow_type": "trading_health",
        "agents": ["TradingAgent"],
        "input": {"query": "Test"}
    }

    submit_response = client.post("/jobs", json=job_data)
    job_id = submit_response.json()["job_id"]

    # Then get its status
    status_response = client.get(f"/jobs/{job_id}/status")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["job_id"] == job_id
    assert "status" in data


def test_submit_job_with_agent_groups(client):
    """Test submitting a job with agent groups."""
    job_data = {
        "workflow_type": "market_analysis",
        "agent_groups": [
            ["TradingAgent", "ResearchAgent"],
            ["KnowledgeAgent"]
        ],
        "input": {"query": "Analyze EUR/USD"}
    }

    response = client.post("/jobs", json=job_data)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["workflow_type"] == "market_analysis"


def test_resume_job_endpoint(client):
    """Test resuming a job from checkpoint via API endpoint."""
    # Create a checkpoint for a test job
    state = create_initial_state_with_groups(
        workflow_type="test_workflow",
        agent_groups=[["Agent1"], ["Agent2"]],
        input={"query": "Test"}
    )
    state.current_group_index = 1

    job_id = "test_resume_job_123"
    checkpoint_manager.save_checkpoint(job_id, state)

    # Call resume endpoint
    response = client.post(f"/jobs/{job_id}/resume")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["workflow_type"] == "test_workflow"
    assert data["status"] == "pending"

    # Cleanup
    checkpoint_manager.delete_checkpoint(job_id)


def test_resume_job_not_found(client):
    """Test resuming a job with no checkpoint."""
    response = client.post("/jobs/nonexistent_job_xyz/resume")

    assert response.status_code == 404
    data = response.json()
    assert "No checkpoint" in data["detail"]
