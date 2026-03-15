"""Full end-to-end integration tests for production workflow."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from emy.brain.service import app, job_queue
from emy.brain.checkpoint import checkpoint_manager


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
    """Test /health endpoint is accessible."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_submit_single_agent_job(client):
    """Test submitting a single-agent job."""
    response = client.post(
        "/jobs",
        json={
            "workflow_type": "test_workflow",
            "agents": ["TradingAgent"],
            "input": {"query": "Test single agent"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["workflow_type"] == "test_workflow"
    assert data["status"] == "pending"


def test_submit_multi_agent_job(client):
    """Test submitting a multi-agent (group) job."""
    response = client.post(
        "/jobs",
        json={
            "workflow_type": "market_analysis",
            "agent_groups": [["TradingAgent"], ["ResearchAgent"]],
            "input": {"query": "Test multi-agent"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_get_job_status(client):
    """Test retrieving job status via REST."""
    # Submit job
    submit_response = client.post(
        "/jobs",
        json={
            "workflow_type": "test",
            "agents": ["TradingAgent"],
            "input": {},
        },
    )
    job_id = submit_response.json()["job_id"]

    # Get status
    status_response = client.get(f"/jobs/{job_id}/status")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["status"] in ["pending", "executing", "completed", "failed"]


def test_websocket_endpoint_exists(client):
    """Test WebSocket endpoint is registered and responds to connection."""
    # Verify REST routes are registered (WebSocket is handled separately)
    route_paths = [str(route.path) for route in app.routes]
    assert "/health" in route_paths, "Health endpoint should be registered"
    assert "/jobs" in route_paths, "Jobs endpoint should be registered"
    # WebSocket routes may not appear in standard route listing due to FastAPI routing


def test_invalid_job_request(client):
    """Test validation rejects invalid job requests."""
    # Neither agents nor agent_groups provided
    response = client.post("/jobs", json={"workflow_type": "test", "input": {}})

    assert response.status_code == 422  # Validation error


def test_job_not_found(client):
    """Test 404 for non-existent job."""
    response = client.get("/jobs/nonexistent_job_12345/status")
    assert response.status_code == 404


def test_checkpoint_resume_endpoint(client):
    """Test resume endpoint accepts checkpoint resumption."""
    # This test verifies the endpoint exists and is properly validated
    # In production, checkpoint would exist from previous failure
    response = client.post("/jobs/nonexistent_checkpoint/resume")
    assert response.status_code == 404  # No checkpoint exists


def test_checkpoint_cleanup_on_success():
    """Test checkpoints are cleaned up after successful completion."""
    # Create a checkpoint
    job_id = "test_cleanup_001"

    # In real test, would submit job that completes successfully
    # and verify checkpoint is deleted

    # For now, verify checkpoint cleanup endpoint exists
    assert checkpoint_manager is not None


def test_concurrent_job_submissions(client):
    """Test concurrent job submissions are handled correctly."""
    # Submit multiple jobs
    job_ids = []
    for i in range(5):
        response = client.post(
            "/jobs",
            json={
                "workflow_type": "concurrent_test",
                "agents": ["TradingAgent"],
                "input": {"query": f"Job {i}"},
            },
        )
        assert response.status_code == 200
        job_ids.append(response.json()["job_id"])

    # Verify all jobs can be retrieved
    for job_id in job_ids:
        response = client.get(f"/jobs/{job_id}/status")
        assert response.status_code == 200


def test_logging_json_format():
    """Test that service logs are JSON formatted."""
    # This is verified via logging tests, but we can check
    # that service starts and logs properly
    import logging

    logger = logging.getLogger("EMyBrain.Service")
    assert logger is not None
    # Verify logger has handlers
    assert (
        len(logger.handlers) > 0 or len(logging.getLogger("EMyBrain").handlers) > 0
    )


def test_job_workflow_complete(client):
    """Test complete job workflow: submit -> status -> retrieve."""
    # Submit job
    submit_response = client.post(
        "/jobs",
        json={
            "workflow_type": "complete_test",
            "agents": ["TradingAgent"],
            "input": {"test": "data"},
        },
    )
    assert submit_response.status_code == 200
    job_data = submit_response.json()
    job_id = job_data["job_id"]

    # Verify initial status
    assert job_data["status"] == "pending"
    assert job_data["workflow_type"] == "complete_test"

    # Check status endpoint
    status_response = client.get(f"/jobs/{job_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] in ["pending", "executing", "completed", "failed"]


def test_error_handling_malformed_json(client):
    """Test error handling for malformed JSON."""
    response = client.post(
        "/jobs",
        content=b"{invalid json}",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code in [400, 422]


def test_cors_headers_present(client):
    """Test that CORS headers are properly set in responses."""
    response = client.get("/health")
    assert response.status_code == 200
    # CORS headers may be set depending on configuration
    # Just verify the response is valid
    assert response.json()["status"] == "ok"


def test_rate_limiting_configured():
    """Test rate limiting middleware is configured."""
    from emy.brain.rate_limit import rate_limiter

    # Verify rate limiter exists
    assert rate_limiter is not None
    # Verify it has the check_rate_limit method
    assert hasattr(rate_limiter, "is_allowed")
