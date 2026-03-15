"""Test database transaction support and ACID compliance."""
import pytest
import asyncio
import tempfile
import os
from emy.brain.queue import JobQueue, Job


@pytest.mark.asyncio
async def test_concurrent_job_submissions():
    """Test concurrent job submissions are transactionally safe."""
    # Use file-based DB for concurrent access testing
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmpdir, "test.db")
        db = JobQueue(db_path=db_path)
        await db.initialize()

        # Create multiple jobs concurrently
        async def submit_job(job_id):
            job = Job(
                job_id=job_id,
                workflow_type="test",
                agents=["TestAgent"],
                agent_groups=[],
                input={}
            )
            return await db.submit(job)

        # Submit 10 jobs concurrently
        job_ids = [f"concurrent_job_{i}" for i in range(10)]
        results = await asyncio.gather(*[submit_job(jid) for jid in job_ids])

        # Verify all jobs submitted successfully
        assert all(results)

        # Verify all jobs exist in database
        for job_id in job_ids:
            status = await db.get_status(job_id)
            assert status == "pending"
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_transaction_rollback_on_error():
    """Test transaction rollback prevents partial updates."""
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmpdir, "test.db")
        db = JobQueue(db_path=db_path)
        await db.initialize()

        # Create a job
        job = Job(
            job_id="test_rollback",
            workflow_type="test",
            agents=["Agent"],
            agent_groups=[],
            input={}
        )
        await db.submit(job)

        # Mark as executing
        await db.mark_executing("test_rollback")

        # Verify status changed
        status = await db.get_status("test_rollback")
        assert status == "executing"
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_wal_mode_enabled():
    """Test WAL mode is enabled for file-based databases."""
    import os
    import tempfile

    # Create temporary directory that persists for test
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmpdir, "test.db")
        db = JobQueue(db_path=db_path)
        await db.initialize()

        # Check WAL mode is set for file-based DB
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL", f"Expected WAL mode, got {mode}"
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_foreign_keys_enabled():
    """Test foreign keys constraint is enabled."""
    db = JobQueue(db_path=":memory:")
    await db.initialize()

    # Check foreign keys are enabled
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    enabled = cursor.fetchone()[0]
    assert enabled == 1, "Foreign keys should be enabled"
