"""Tests for async job queue."""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from emy.brain.queue import JobQueue, Job


@pytest_asyncio.fixture
async def queue():
    """Create fresh job queue for each test."""
    q = JobQueue(db_path=":memory:")  # Use in-memory SQLite for testing
    await q.initialize()
    yield q
    # Cleanup: clear jobs table between tests
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, q._clear_jobs)


@pytest.mark.asyncio
async def test_submit_job(queue):
    """Test submitting a job to the queue."""
    job = Job(
        job_id="test-001",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    job_id = await queue.submit(job)
    assert job_id == "test-001"


@pytest.mark.asyncio
async def test_get_status_pending(queue):
    """Test getting status of pending job."""
    job = Job(
        job_id="test-002",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    await queue.submit(job)
    status = await queue.get_status("test-002")
    assert status == "pending"


@pytest.mark.asyncio
async def test_get_next_job(queue):
    """Test retrieving next job from queue."""
    job = Job(
        job_id="test-003",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    await queue.submit(job)
    next_job = await queue.get_next()

    assert next_job is not None
    assert next_job["job_id"] == "test-003"
    assert next_job["status"] == "pending"


@pytest.mark.asyncio
async def test_mark_executing(queue):
    """Test marking job as executing."""
    job = Job(
        job_id="test-004",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    await queue.submit(job)
    await queue.mark_executing("test-004")
    status = await queue.get_status("test-004")
    assert status == "executing"


@pytest.mark.asyncio
async def test_mark_complete(queue):
    """Test marking job as completed."""
    job = Job(
        job_id="test-005",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    await queue.submit(job)
    result = {"analysis": "Success", "data": []}
    await queue.mark_complete("test-005", result)
    status = await queue.get_status("test-005")
    assert status == "completed"


@pytest.mark.asyncio
async def test_mark_failed(queue):
    """Test marking job as failed."""
    job = Job(
        job_id="test-006",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    await queue.submit(job)
    await queue.mark_failed("test-006", "Connection timeout")
    status = await queue.get_status("test-006")
    assert status == "failed"


@pytest.mark.asyncio
async def test_get_result(queue):
    """Test retrieving result from completed job."""
    job = Job(
        job_id="test-007",
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "test"}
    )

    await queue.submit(job)
    result_data = {"analysis": "Market healthy", "signals": ["BUY"]}
    await queue.mark_complete("test-007", result_data)

    result = await queue.get_result("test-007")
    assert result is not None
    assert result["analysis"] == "Market healthy"
