"""Async job queue for Emy Brain with SQLite persistence."""
import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('EMyBrain.Queue')


@dataclass
class Job:
    """Job submission request."""
    job_id: str
    workflow_type: str
    agents: List[str] = field(default_factory=list)
    agent_groups: List[List[str]] = field(default_factory=list)
    input: Dict[str, Any] = field(default_factory=dict)


class JobQueue:
    """Async job queue with SQLite persistence."""

    # Shared in-memory connection for testing
    _memory_conn = None

    def __init__(self, db_path: str = "jobs.db"):
        """Initialize job queue with database path."""
        self.db_path = db_path
        self.loop = None

    async def initialize(self):
        """Initialize database schema."""
        # Create tables in blocking manner via thread executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._create_tables)

    def _create_tables(self):
        """Create database tables (run in executor)."""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Enable WAL mode for concurrent access (file-based only)
        if self.db_path != ":memory:":
            cursor.execute("PRAGMA journal_mode = WAL")

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                workflow_type TEXT NOT NULL,
                agents TEXT NOT NULL,
                agent_groups TEXT,
                input TEXT,
                output TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error TEXT
            )
        """)

        # Job executions table (for tracking agent-level execution)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_executions (
                execution_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                input TEXT,
                output TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        conn.commit()
        logger.info("Database initialized with transaction support (implicit transactions enabled, foreign keys enabled)")

    def _get_connection(self):
        """Get database connection with PRAGMA settings."""
        if self.db_path == ":memory:":
            # For in-memory, use shared class-level connection
            if JobQueue._memory_conn is None:
                JobQueue._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                JobQueue._memory_conn.row_factory = sqlite3.Row
                # Set PRAGMA settings on first use
                cursor = JobQueue._memory_conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                JobQueue._memory_conn.commit()
            return JobQueue._memory_conn
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            # Set PRAGMA settings for file-based connection
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            conn.commit()
            return conn

    async def submit(self, job: Job) -> str:
        """
        Submit a job to the queue.

        Args:
            job: Job to submit

        Returns:
            Job ID
        """
        loop = asyncio.get_event_loop()
        agent_groups_json = json.dumps(job.agent_groups) if job.agent_groups else "[]"
        await loop.run_in_executor(
            None,
            self._insert_job,
            job.job_id,
            job.workflow_type,
            json.dumps(job.agents),
            agent_groups_json,
            json.dumps(job.input)
        )
        return job.job_id

    def _insert_job(self, job_id: str, workflow_type: str, agents_json: str, agent_groups_json: str, input_json: str):
        """Insert job into database with transaction safety."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            # SQLite uses implicit transactions; statements are auto-wrapped
            cursor.execute("""
                INSERT INTO jobs (job_id, workflow_type, agents, agent_groups, input, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (job_id, workflow_type, agents_json, agent_groups_json, input_json, now))

            # Commit transaction
            conn.commit()
            logger.info(f"Job {job_id} submitted in transaction")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Failed to submit job {job_id}: {str(e)}")
            raise

    async def get_status(self, job_id: str) -> str:
        """
        Get status of a job.

        Args:
            job_id: Job ID

        Returns:
            Status string (pending, executing, completed, failed)
        """
        loop = asyncio.get_event_loop()
        status = await loop.run_in_executor(None, self._fetch_status, job_id)
        return status

    def _fetch_status(self, job_id: str) -> str:
        """Fetch job status from database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

        return row["status"] if row else "not_found"

    async def get_next(self) -> Optional[Dict[str, Any]]:
        """
        Get next pending job from queue.

        Returns:
            Next job dict or None if queue empty
        """
        loop = asyncio.get_event_loop()
        job = await loop.run_in_executor(None, self._fetch_next_job)
        return job

    def _fetch_next_job(self) -> Optional[Dict[str, Any]]:
        """Fetch next pending job from database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT job_id, workflow_type, agents, agent_groups, input, status, created_at
            FROM jobs
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "job_id": row["job_id"],
            "workflow_type": row["workflow_type"],
            "agents": json.loads(row["agents"]) if row["agents"] else [],
            "agent_groups": json.loads(row["agent_groups"]) if row["agent_groups"] else [],
            "input": json.loads(row["input"]) if row["input"] else {},
            "status": row["status"],
            "created_at": row["created_at"]
        }

    async def mark_executing(self, job_id: str):
        """Mark job as executing."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._update_status, job_id, "executing")

    async def mark_complete(self, job_id: str, result: Dict[str, Any]):
        """
        Mark job as completed with result.

        Args:
            job_id: Job ID
            result: Result data
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._complete_job,
            job_id,
            json.dumps(result)
        )

    def _complete_job(self, job_id: str, result_json: str):
        """Mark job complete in database with transaction safety."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            # SQLite uses implicit transactions; statements are auto-wrapped
            cursor.execute("""
                UPDATE jobs
                SET status = 'completed', output = ?, completed_at = ?
                WHERE job_id = ?
            """, (result_json, now, job_id))

            # Commit transaction
            conn.commit()
            logger.info(f"Job {job_id} marked as completed")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Failed to mark job {job_id} complete: {str(e)}")
            raise

    async def mark_failed(self, job_id: str, error: str):
        """
        Mark job as failed.

        Args:
            job_id: Job ID
            error: Error message
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._fail_job, job_id, error)

    def _fail_job(self, job_id: str, error: str):
        """Mark job failed in database with transaction safety."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            # SQLite uses implicit transactions; statements are auto-wrapped
            cursor.execute("""
                UPDATE jobs
                SET status = 'failed', error = ?, completed_at = ?
                WHERE job_id = ?
            """, (error, now, job_id))

            # Commit transaction
            conn.commit()
            logger.info(f"Job {job_id} marked as failed")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Failed to mark job {job_id} failed: {str(e)}")
            raise

    async def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get result from completed job.

        Args:
            job_id: Job ID

        Returns:
            Result dict or None
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._fetch_result, job_id)
        return result

    def _fetch_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch job result from database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT output FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

        if not row or not row["output"]:
            return None

        return json.loads(row["output"])

    def _update_status(self, job_id: str, status: str):
        """Update job status in database with transaction safety."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            # SQLite uses implicit transactions; statements are auto-wrapped
            cursor.execute("""
                UPDATE jobs
                SET status = ?, started_at = COALESCE(started_at, ?)
                WHERE job_id = ?
            """, (status, now if status == "executing" else None, job_id))

            # Commit transaction
            conn.commit()
            logger.info(f"Job {job_id} marked as {status}")

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Failed to update job {job_id} status to {status}: {str(e)}")
            raise

    def _clear_jobs(self):
        """Clear all jobs from database (for testing)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs")
        cursor.execute("DELETE FROM job_executions")
        conn.commit()
