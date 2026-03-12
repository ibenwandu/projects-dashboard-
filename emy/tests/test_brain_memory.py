"""Tests for MemoryStore workflow context persistence.

Test Coverage:
1. MemoryStore instantiation
2. save_step → load_latest roundtrip
3. load_latest returns None for unknown workflow
4. Multiple saves → load_latest returns latest step
5. clear_workflow removes context
6. EMyDatabase has save_workflow_context method
7. EMyDatabase has load_workflow_context method
8. Existing workflow persistence tests still pass
"""

import pytest
import tempfile
import json
from pathlib import Path
from emy.brain.memory_store import MemoryStore
from emy.core.database import EMyDatabase


@pytest.fixture
def test_db():
    """Provide temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        db = EMyDatabase(str(db_path))
        db.initialize_schema()
        yield db


class TestMemoryStore:
    """Tests for MemoryStore wrapper."""

    def test_instantiation(self, test_db):
        """Test MemoryStore instantiates with database."""
        store = MemoryStore(test_db)
        assert store.db is test_db

    def test_save_step_basic(self, test_db):
        """Test save_step stores context."""
        store = MemoryStore(test_db)
        context = {"query": "find jobs", "location": "Toronto"}

        # Should not raise
        store.save_step(
            workflow_id="wf_test_001",
            agent_name="JobSearchAgent",
            step=1,
            context=context,
        )

    def test_save_step_with_checkpoint(self, test_db):
        """Test save_step with checkpoint data."""
        store = MemoryStore(test_db)
        context = {"key": "value"}
        checkpoint = {"resume_from": "line_123"}

        store.save_step(
            workflow_id="wf_test_002",
            agent_name="JobSearchAgent",
            step=2,
            context=context,
            checkpoint=checkpoint,
        )

    def test_load_latest_returns_dict(self, test_db):
        """Test load_latest returns dict with correct fields."""
        store = MemoryStore(test_db)
        context = {"data": "test"}

        store.save_step(
            workflow_id="wf_test_003",
            agent_name="KnowledgeAgent",
            step=1,
            context=context,
        )

        result = store.load_latest("wf_test_003")

        assert result is not None
        assert "context" in result
        assert "checkpoint" in result
        assert "step_number" in result
        assert "agent_name" in result
        assert result["agent_name"] == "KnowledgeAgent"
        assert result["step_number"] == 1

    def test_load_latest_roundtrip(self, test_db):
        """Test save → load roundtrip preserves data."""
        store = MemoryStore(test_db)
        original_context = {"query": "test", "options": {"a": 1, "b": 2}}

        store.save_step(
            workflow_id="wf_roundtrip",
            agent_name="TestAgent",
            step=5,
            context=original_context,
        )

        result = store.load_latest("wf_roundtrip")

        assert result["context"] == original_context
        assert result["step_number"] == 5
        assert result["agent_name"] == "TestAgent"

    def test_load_latest_returns_none_for_unknown(self, test_db):
        """Test load_latest returns None for unknown workflow."""
        store = MemoryStore(test_db)
        result = store.load_latest("wf_nonexistent")
        assert result is None

    def test_multiple_saves_latest_wins(self, test_db):
        """Test multiple saves returns latest step."""
        store = MemoryStore(test_db)

        # Save step 1
        store.save_step(
            workflow_id="wf_multi",
            agent_name="Agent1",
            step=1,
            context={"step": 1},
        )

        # Save step 2
        store.save_step(
            workflow_id="wf_multi",
            agent_name="Agent2",
            step=2,
            context={"step": 2},
        )

        # Save step 3
        store.save_step(
            workflow_id="wf_multi",
            agent_name="Agent3",
            step=3,
            context={"step": 3},
        )

        # load_latest should return step 3
        result = store.load_latest("wf_multi")

        assert result["step_number"] == 3
        assert result["agent_name"] == "Agent3"
        assert result["context"]["step"] == 3

    def test_clear_workflow_removes_context(self, test_db):
        """Test clear_workflow removes all context for workflow."""
        store = MemoryStore(test_db)

        # Save context
        store.save_step(
            workflow_id="wf_clear_test",
            agent_name="TestAgent",
            step=1,
            context={"data": "test"},
        )

        # Verify it exists
        assert store.load_latest("wf_clear_test") is not None

        # Clear it
        store.clear_workflow("wf_clear_test")

        # Verify it's gone
        assert store.load_latest("wf_clear_test") is None


class TestEMyDatabaseWorkflowContext:
    """Tests for EMyDatabase workflow context methods."""

    def test_database_has_save_workflow_context(self, test_db):
        """Test EMyDatabase has save_workflow_context method."""
        assert hasattr(test_db, "save_workflow_context")
        assert callable(test_db.save_workflow_context)

    def test_database_has_load_workflow_context(self, test_db):
        """Test EMyDatabase has load_workflow_context method."""
        assert hasattr(test_db, "load_workflow_context")
        assert callable(test_db.load_workflow_context)

    def test_save_and_load_directly(self, test_db):
        """Test database methods work directly."""
        context = {"key": "value"}
        checkpoint = {"resume_from": "line_456"}

        test_db.save_workflow_context(
            workflow_id="wf_direct",
            agent_name="DirectAgent",
            step_number=7,
            context_dict=context,
            checkpoint_dict=checkpoint,
        )

        result = test_db.load_workflow_context("wf_direct")

        assert result is not None
        # load_workflow_context returns already-parsed dicts
        assert result["context"] == context
        assert result["checkpoint"] == checkpoint

    def test_workflow_contexts_table_created(self, test_db):
        """Test workflow_contexts table is created during initialization."""
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_contexts'"
            )
            assert cursor.fetchone() is not None


class TestWorkflowPersistenceRegression:
    """Regression tests: existing workflow persistence still works."""

    def test_store_workflow_output_still_works(self, test_db):
        """Test that existing store_workflow_output still works."""
        result = test_db.store_workflow_output(
            workflow_id="wf_regression_test",
            workflow_type="knowledge_query",
            status="complete",
            output='{"answer": "test"}',
        )

        assert result is True

    def test_get_workflow_still_works(self, test_db):
        """Test that existing get_workflow still works."""
        test_db.store_workflow_output(
            workflow_id="wf_get_test",
            workflow_type="trading",
            status="complete",
            output="test output",
        )

        retrieved = test_db.get_workflow("wf_get_test")

        assert retrieved is not None
        assert retrieved["workflow_id"] == "wf_get_test"
        assert retrieved["type"] == "trading"
        assert retrieved["status"] == "complete"
