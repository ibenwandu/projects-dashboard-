"""
Test suite for SQLiteStore - Workflow persistence layer.

Tests cover workflows, tasks, and agent metrics CRUD operations.
Uses in-memory SQLite (:memory:) for isolated, fast test execution.
"""

import pytest
import json
from datetime import datetime, timedelta
from emy.storage.sqlite_store import SQLiteStore


class TestSQLiteStoreBasics:
    """Test SQLiteStore initialization and basic operations."""

    @pytest.fixture
    def store(self):
        """Create in-memory SQLiteStore for each test."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    def test_initialization_creates_tables(self, store):
        """Test that store initializes with correct tables."""
        # Verify tables exist by querying schema
        cursor = store.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "workflows" in tables
        assert "tasks" in tables
        assert "agent_metrics" in tables

    def test_workflows_table_schema(self, store):
        """Test that workflows table has correct columns."""
        cursor = store.conn.cursor()
        cursor.execute("PRAGMA table_info(workflows)")
        columns = {row[1] for row in cursor.fetchall()}

        required_cols = {
            "id", "name", "status", "created_at", "started_at",
            "completed_at", "input_data", "output_data", "error_message", "created_by"
        }
        assert required_cols.issubset(columns)

    def test_tasks_table_schema(self, store):
        """Test that tasks table has correct columns."""
        cursor = store.conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = {row[1] for row in cursor.fetchall()}

        required_cols = {
            "id", "workflow_id", "step_number", "agent_type", "task_type",
            "status", "started_at", "completed_at", "input_data", "output_data",
            "error_message", "duration_seconds"
        }
        assert required_cols.issubset(columns)

    def test_agent_metrics_table_schema(self, store):
        """Test that agent_metrics table has correct columns."""
        cursor = store.conn.cursor()
        cursor.execute("PRAGMA table_info(agent_metrics)")
        columns = {row[1] for row in cursor.fetchall()}

        required_cols = {
            "agent_name", "tasks_completed", "tasks_failed", "total_duration_seconds",
            "avg_duration_seconds", "last_activity", "last_error", "status"
        }
        assert required_cols.issubset(columns)


class TestWorkflowCRUD:
    """Test workflow save, retrieve, and update operations."""

    @pytest.fixture
    def store(self):
        """Create in-memory SQLiteStore for each test."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    def test_save_workflow(self, store):
        """Test saving a workflow returns True."""
        workflow = {
            "id": "wf-001",
            "name": "Test Workflow",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "input_data": json.dumps({"key": "value"}),
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }

        result = store.save_workflow(workflow)
        assert result is True

    def test_get_workflow(self, store):
        """Test retrieving a saved workflow."""
        workflow = {
            "id": "wf-002",
            "name": "Test Workflow 2",
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "input_data": json.dumps({"param1": "value1"}),
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }

        store.save_workflow(workflow)
        retrieved = store.get_workflow("wf-002")

        assert retrieved is not None
        assert retrieved["id"] == "wf-002"
        assert retrieved["name"] == "Test Workflow 2"
        assert retrieved["status"] == "running"

    def test_get_nonexistent_workflow_returns_none(self, store):
        """Test retrieving non-existent workflow returns None."""
        result = store.get_workflow("nonexistent-id")
        assert result is None

    def test_update_workflow_status(self, store):
        """Test updating workflow status."""
        workflow = {
            "id": "wf-003",
            "name": "Test Workflow 3",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "input_data": json.dumps({}),
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }

        store.save_workflow(workflow)
        result = store.update_workflow_status("wf-003", "completed")

        assert result is True

        retrieved = store.get_workflow("wf-003")
        assert retrieved["status"] == "completed"

    def test_update_nonexistent_workflow_status_returns_false(self, store):
        """Test updating non-existent workflow returns False."""
        result = store.update_workflow_status("nonexistent-id", "completed")
        assert result is False

    def test_get_workflow_history(self, store):
        """Test retrieving workflow history."""
        # Save multiple workflows
        for i in range(5):
            workflow = {
                "id": f"wf-hist-{i}",
                "name": f"Workflow {i}",
                "status": "completed" if i % 2 == 0 else "failed",
                "created_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                "started_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                "completed_at": datetime.now().isoformat(),
                "input_data": json.dumps({"index": i}),
                "output_data": json.dumps({"result": f"result-{i}"}),
                "error_message": None,
                "created_by": "test_user"
            }
            store.save_workflow(workflow)

        # Get history with limit
        history = store.get_workflow_history(limit=3)

        assert len(history) <= 3
        assert all("id" in wf for wf in history)
        assert all("name" in wf for wf in history)


class TestTaskCRUD:
    """Test task save, retrieve, and list operations."""

    @pytest.fixture
    def store(self):
        """Create in-memory SQLiteStore for each test."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    @pytest.fixture
    def workflow(self, store):
        """Create a test workflow."""
        workflow = {
            "id": "wf-task-test",
            "name": "Task Test Workflow",
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "input_data": json.dumps({}),
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }
        store.save_workflow(workflow)
        return workflow

    def test_save_task(self, store, workflow):
        """Test saving a task returns True."""
        task = {
            "id": "task-001",
            "workflow_id": workflow["id"],
            "step_number": 1,
            "agent_type": "ResearchAgent",
            "task_type": "research",
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "input_data": json.dumps({"query": "test query"}),
            "output_data": json.dumps({"findings": "test findings"}),
            "error_message": None,
            "duration_seconds": 45.5
        }

        result = store.save_task(task)
        assert result is True

    def test_get_task(self, store, workflow):
        """Test retrieving a saved task."""
        task = {
            "id": "task-002",
            "workflow_id": workflow["id"],
            "step_number": 1,
            "agent_type": "KnowledgeAgent",
            "task_type": "analysis",
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "input_data": json.dumps({"data": "test"}),
            "output_data": json.dumps({"result": "analyzed"}),
            "error_message": None,
            "duration_seconds": 30.2
        }

        store.save_task(task)
        retrieved = store.get_task("task-002")

        assert retrieved is not None
        assert retrieved["id"] == "task-002"
        assert retrieved["agent_type"] == "KnowledgeAgent"
        assert retrieved["status"] == "completed"

    def test_get_nonexistent_task_returns_none(self, store):
        """Test retrieving non-existent task returns None."""
        result = store.get_task("nonexistent-task")
        assert result is None

    def test_get_workflow_tasks(self, store, workflow):
        """Test retrieving all tasks for a workflow."""
        # Save multiple tasks for same workflow
        for i in range(3):
            task = {
                "id": f"task-wf-{i}",
                "workflow_id": workflow["id"],
                "step_number": i + 1,
                "agent_type": "TestAgent",
                "task_type": "test",
                "status": "completed",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "input_data": json.dumps({"step": i}),
                "output_data": json.dumps({"step_result": i}),
                "error_message": None,
                "duration_seconds": 10.0 * (i + 1)
            }
            store.save_task(task)

        # Retrieve tasks for this workflow
        tasks = store.get_workflow_tasks(workflow["id"])

        assert len(tasks) == 3
        assert all(t["workflow_id"] == workflow["id"] for t in tasks)
        assert all("id" in t for t in tasks)

    def test_get_workflow_tasks_empty_for_missing_workflow(self, store):
        """Test retrieving tasks for non-existent workflow returns empty list."""
        tasks = store.get_workflow_tasks("nonexistent-workflow")
        assert tasks == []


class TestAgentMetrics:
    """Test agent metrics save and retrieve operations."""

    @pytest.fixture
    def store(self):
        """Create in-memory SQLiteStore for each test."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    def test_update_agent_metrics_new_agent(self, store):
        """Test updating metrics for new agent."""
        result = store.update_agent_metrics(
            "ResearchAgent",
            tasks_completed=5,
            tasks_failed=0,
            total_duration_seconds=150.5,
            avg_duration_seconds=30.1,
            last_activity=datetime.now().isoformat(),
            status="active"
        )

        assert result is True

    def test_get_agent_metrics(self, store):
        """Test retrieving agent metrics."""
        store.update_agent_metrics(
            "TestAgent",
            tasks_completed=10,
            tasks_failed=2,
            total_duration_seconds=200.0,
            avg_duration_seconds=18.18,
            last_activity=datetime.now().isoformat(),
            status="active"
        )

        metrics = store.get_agent_metrics("TestAgent")

        assert metrics is not None
        assert metrics["agent_name"] == "TestAgent"
        assert metrics["tasks_completed"] == 10
        assert metrics["tasks_failed"] == 2
        assert metrics["total_duration_seconds"] == 200.0

    def test_get_nonexistent_agent_metrics_returns_none(self, store):
        """Test retrieving metrics for non-existent agent returns None."""
        result = store.get_agent_metrics("NonexistentAgent")
        assert result is None

    def test_update_existing_agent_metrics(self, store):
        """Test updating metrics for existing agent."""
        # Create initial metrics
        store.update_agent_metrics(
            "UpdateAgent",
            tasks_completed=5,
            tasks_failed=1,
            total_duration_seconds=100.0,
            avg_duration_seconds=20.0,
            last_activity=datetime.now().isoformat(),
            status="active"
        )

        # Update metrics
        later_time = (datetime.now() + timedelta(minutes=5)).isoformat()
        result = store.update_agent_metrics(
            "UpdateAgent",
            tasks_completed=10,
            tasks_failed=2,
            total_duration_seconds=200.0,
            avg_duration_seconds=20.0,
            last_activity=later_time,
            last_error="test error",
            status="active"
        )

        assert result is True

        metrics = store.get_agent_metrics("UpdateAgent")
        assert metrics["tasks_completed"] == 10
        assert metrics["tasks_failed"] == 2
        assert metrics["total_duration_seconds"] == 200.0


class TestContextManager:
    """Test SQLiteStore as context manager."""

    def test_context_manager_usage(self):
        """Test using SQLiteStore with context manager pattern."""
        with SQLiteStore(db_path=":memory:") as store:
            workflow = {
                "id": "wf-ctx",
                "name": "Context Workflow",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "input_data": json.dumps({}),
                "output_data": None,
                "error_message": None,
                "created_by": "test_user"
            }

            result = store.save_workflow(workflow)
            assert result is True

            retrieved = store.get_workflow("wf-ctx")
            assert retrieved is not None

    def test_close_is_safe_after_context_exit(self):
        """Test that close() can be called safely after context exit."""
        store = SQLiteStore(db_path=":memory:")
        with store:
            workflow = {
                "id": "wf-safe",
                "name": "Safe Close Workflow",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "input_data": json.dumps({}),
                "output_data": None,
                "error_message": None,
                "created_by": "test_user"
            }
            store.save_workflow(workflow)

        # Should not raise exception
        store.close()


class TestDataIntegrity:
    """Test data integrity and JSON handling."""

    @pytest.fixture
    def store(self):
        """Create in-memory SQLiteStore for each test."""
        store = SQLiteStore(db_path=":memory:")
        yield store
        store.close()

    def test_json_data_roundtrip_workflow(self, store):
        """Test JSON data roundtrip for workflow."""
        input_obj = {"query": "test", "params": {"limit": 10}, "nested": {"key": "value"}}

        workflow = {
            "id": "wf-json",
            "name": "JSON Test Workflow",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "input_data": json.dumps(input_obj),
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }

        store.save_workflow(workflow)
        retrieved = store.get_workflow("wf-json")

        restored_input = json.loads(retrieved["input_data"])
        assert restored_input == input_obj

    def test_json_data_roundtrip_task(self, store):
        """Test JSON data roundtrip for task."""
        # Create workflow first (foreign key constraint)
        workflow = {
            "id": "wf-json-task",
            "name": "JSON Task Workflow",
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "input_data": json.dumps({}),
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }
        store.save_workflow(workflow)

        output_obj = {"status": "success", "data": [1, 2, 3], "metadata": {"timestamp": "2026-03-11"}}

        task = {
            "id": "task-json",
            "workflow_id": "wf-json-task",
            "step_number": 1,
            "agent_type": "TestAgent",
            "task_type": "test",
            "status": "completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "input_data": json.dumps({}),
            "output_data": json.dumps(output_obj),
            "error_message": None,
            "duration_seconds": 25.0
        }

        store.save_task(task)
        retrieved = store.get_task("task-json")

        restored_output = json.loads(retrieved["output_data"])
        assert restored_output == output_obj

    def test_null_values_handled_correctly(self, store):
        """Test that NULL values are handled correctly."""
        workflow = {
            "id": "wf-nulls",
            "name": "Null Test Workflow",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "input_data": None,
            "output_data": None,
            "error_message": None,
            "created_by": "test_user"
        }

        store.save_workflow(workflow)
        retrieved = store.get_workflow("wf-nulls")

        assert retrieved["started_at"] is None
        assert retrieved["completed_at"] is None
        assert retrieved["error_message"] is None
