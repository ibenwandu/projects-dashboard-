"""
SQLiteStore - Persistence layer for Emy workflows, tasks, and agent metrics.

Provides CRUD operations for:
- Workflows: Complete execution records with input/output data
- Tasks: Individual steps within workflows with agent and performance metrics
- Agent Metrics: Aggregated performance data per agent type

Uses sqlite3 stdlib with auto-table creation on initialization.
Thread-safe for single-threaded async operations.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SQLiteStore:
    """SQLiteStore provides persistent storage for Emy workflow system."""

    def __init__(self, db_path: str = "emy/data/workflows.db"):
        """
        Initialize SQLiteStore with auto-table creation.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory DB.
                   Defaults to "emy/data/workflows.db".
        """
        self.db_path = db_path
        self.conn = None

        try:
            self._connect()
            self._create_tables()
            logger.info(f"SQLiteStore initialized: {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLiteStore: {e}")
            raise

    def _connect(self):
        """Establish database connection."""
        if self.db_path != ":memory:":
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _create_tables(self):
        """Create tables if they don't exist (idempotent)."""
        cursor = self.conn.cursor()

        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                created_by TEXT NOT NULL
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                agent_type TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                duration_seconds REAL,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        """)

        # Agent metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics (
                agent_name TEXT PRIMARY KEY,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                total_duration_seconds REAL DEFAULT 0.0,
                avg_duration_seconds REAL DEFAULT 0.0,
                last_activity TEXT,
                last_error TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

        self.conn.commit()

    def save_workflow(self, workflow: Dict) -> bool:
        """
        Save a workflow to the database.

        Args:
            workflow: Dictionary with keys:
                id, name, status, created_at, started_at, completed_at,
                input_data, output_data, error_message, created_by

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO workflows
                (id, name, status, created_at, started_at, completed_at,
                 input_data, output_data, error_message, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow.get("id"),
                workflow.get("name"),
                workflow.get("status"),
                workflow.get("created_at"),
                workflow.get("started_at"),
                workflow.get("completed_at"),
                workflow.get("input_data"),
                workflow.get("output_data"),
                workflow.get("error_message"),
                workflow.get("created_by")
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save workflow {workflow.get('id')}: {e}")
            return False

    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """
        Retrieve a workflow by ID.

        Args:
            workflow_id: The workflow ID to retrieve

        Returns:
            Dictionary with workflow data, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            return None

    def update_workflow_status(self, workflow_id: str, status: str) -> bool:
        """
        Update workflow status.

        Args:
            workflow_id: The workflow ID to update
            status: New status value

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE workflows SET status = ? WHERE id = ?",
                (status, workflow_id)
            )
            self.conn.commit()

            if cursor.rowcount == 0:
                logger.warning(f"Workflow {workflow_id} not found for status update")
                return False

            return True
        except Exception as e:
            logger.error(f"Failed to update workflow status {workflow_id}: {e}")
            return False

    def get_workflow_history(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve workflow history.

        Args:
            limit: Maximum number of workflows to return (default: 100)

        Returns:
            List of workflow dictionaries, ordered by creation time (newest first)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM workflows ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get workflow history: {e}")
            return []

    def save_task(self, task: Dict) -> bool:
        """
        Save a task to the database.

        Args:
            task: Dictionary with keys:
                id, workflow_id, step_number, agent_type, task_type, status,
                started_at, completed_at, input_data, output_data,
                error_message, duration_seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (id, workflow_id, step_number, agent_type, task_type, status,
                 started_at, completed_at, input_data, output_data,
                 error_message, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.get("id"),
                task.get("workflow_id"),
                task.get("step_number"),
                task.get("agent_type"),
                task.get("task_type"),
                task.get("status"),
                task.get("started_at"),
                task.get("completed_at"),
                task.get("input_data"),
                task.get("output_data"),
                task.get("error_message"),
                task.get("duration_seconds")
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save task {task.get('id')}: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        Retrieve a task by ID.

        Args:
            task_id: The task ID to retrieve

        Returns:
            Dictionary with task data, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    def get_workflow_tasks(self, workflow_id: str) -> List[Dict]:
        """
        Retrieve all tasks for a workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            List of task dictionaries, ordered by step number
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE workflow_id = ? ORDER BY step_number ASC",
                (workflow_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get tasks for workflow {workflow_id}: {e}")
            return []

    def update_agent_metrics(self, agent_name: str, **kwargs) -> bool:
        """
        Update or insert agent metrics.

        Args:
            agent_name: The agent name (primary key)
            **kwargs: Metric fields to update (tasks_completed, tasks_failed,
                     total_duration_seconds, avg_duration_seconds, last_activity,
                     last_error, status)

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check if agent exists
            cursor.execute(
                "SELECT agent_name FROM agent_metrics WHERE agent_name = ?",
                (agent_name,)
            )
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing record
                set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
                values = list(kwargs.values()) + [agent_name]

                cursor.execute(
                    f"UPDATE agent_metrics SET {set_clause} WHERE agent_name = ?",
                    values
                )
            else:
                # Insert new record with defaults
                defaults = {
                    "agent_name": agent_name,
                    "tasks_completed": 0,
                    "tasks_failed": 0,
                    "total_duration_seconds": 0.0,
                    "avg_duration_seconds": 0.0,
                    "last_activity": None,
                    "last_error": None,
                    "status": "active"
                }
                defaults.update(kwargs)

                cols = ", ".join(defaults.keys())
                placeholders = ", ".join(["?" for _ in defaults])
                values = list(defaults.values())

                cursor.execute(
                    f"INSERT INTO agent_metrics ({cols}) VALUES ({placeholders})",
                    values
                )

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update metrics for agent {agent_name}: {e}")
            return False

    def get_agent_metrics(self, agent_name: str) -> Optional[Dict]:
        """
        Retrieve metrics for an agent.

        Args:
            agent_name: The agent name

        Returns:
            Dictionary with agent metrics, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_metrics WHERE agent_name = ?",
                (agent_name,)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get metrics for agent {agent_name}: {e}")
            return None

    def close(self):
        """Close the database connection."""
        try:
            if self.conn:
                self.conn.close()
                logger.debug("SQLiteStore connection closed")
        except Exception as e:
            logger.error(f"Error closing SQLiteStore connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
