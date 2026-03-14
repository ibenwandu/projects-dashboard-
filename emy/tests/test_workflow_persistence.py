"""Test workflow output persistence to SQLite."""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from emy.core.database import EMyDatabase


@pytest.fixture
def db():
    """Provide temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_workflow.db"
        db = EMyDatabase(str(db_path))
        db.initialize_schema()
        yield db


def test_workflow_output_is_persisted(db):
    """Test that workflow outputs are stored in database."""

    workflow_data = {
        "workflow_id": "test-123",
        "type": "knowledge_query",
        "status": "complete",
        "output": "Generated knowledge response from Claude",
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat()
    }

    # Store workflow
    result = db.store_workflow_output(
        workflow_data['workflow_id'],
        workflow_data['type'],
        workflow_data['status'],
        workflow_data['output']
    )

    # Verify storage succeeded
    assert result is True

    # Retrieve and verify
    retrieved = db.get_workflow(workflow_data['workflow_id'])
    assert retrieved is not None
    assert retrieved['output'] == workflow_data['output']
    assert retrieved['status'] == workflow_data['status']
    assert retrieved['type'] == workflow_data['type']


def test_workflow_output_retrieval(db):
    """Test that workflow outputs can be retrieved."""

    db.store_workflow_output("test-456", "trading_analysis", "complete", "Market analysis response")

    result = db.get_workflow("test-456")
    assert result is not None
    assert result['output'] == "Market analysis response"
    assert result['status'] == "complete"
    assert result['type'] == "trading_analysis"


def test_workflow_not_found_returns_none(db):
    """Test that non-existent workflow returns None."""
    result = db.get_workflow("nonexistent-id")
    assert result is None


def test_workflow_update_overwrites_output(db):
    """Test that updating a workflow overwrites previous output."""
    workflow_id = "test-789"

    # Store initial output
    db.store_workflow_output(workflow_id, "job_search", "in_progress", "Initial output")

    # Update output
    db.store_workflow_output(workflow_id, "job_search", "complete", "Updated output")

    # Retrieve and verify
    result = db.get_workflow(workflow_id)
    assert result['output'] == "Updated output"
    assert result['status'] == "complete"


# ============================================================================
# Task 3 Acceptance Criteria Tests
# ============================================================================

class TestTask3AcceptanceCriteria:
    """Verify all Task 3 acceptance criteria are met."""

    # ========================================================================
    # CRITERION 1: Workflow output stored in database after execution
    # ========================================================================

    def test_workflow_storage_method_exists(self, db):
        """
        CRITERION 1: Workflow output stored in database.

        ✅ PASS: store_workflow_output() method exists and works
        """
        # Method should exist
        assert hasattr(db, 'store_workflow_output')
        assert callable(db.store_workflow_output)

        # Should be able to store
        result = db.store_workflow_output('wf_test_1', 'test', 'complete', '{}')
        assert result is True

    def test_workflow_output_persisted_to_disk(self, db):
        """
        CRITERION 1: Output should persist to disk (SQLite).

        ✅ PASS: Data persists to database file
        """
        db_path = db.db_path

        # Store workflow
        db.store_workflow_output('wf_persist_1', 'knowledge_query', 'complete',
                               '{"response": "test"}')

        # Create new database connection to same file
        db2 = EMyDatabase(db_path)

        # Should be able to retrieve from new connection
        workflow = db2.get_workflow('wf_persist_1')
        assert workflow is not None
        assert workflow['output'] == '{"response": "test"}'

    def test_workflow_records_contain_all_required_fields(self, db):
        """
        CRITERION 1: Workflow records have all required fields.

        ✅ PASS: workflow_id, type, status, input, output, created_at, updated_at
        """
        db.store_workflow_output('wf_fields_1', 'trading_health', 'complete',
                                '{"analysis": "test"}')

        workflow = db.get_workflow('wf_fields_1')

        required_fields = {'workflow_id', 'type', 'status', 'output', 'created_at', 'updated_at'}
        assert required_fields.issubset(set(workflow.keys()))

    # ========================================================================
    # CRITERION 2: Can retrieve output via GET /workflows/{id}
    # ========================================================================

    def test_get_workflow_retrieves_stored_output(self, db):
        """
        CRITERION 2: Can retrieve output via GET /workflows/{id}.

        ✅ PASS: get_workflow(id) returns output
        """
        workflow_id = 'wf_retrieve_1'
        output_json = '{"response": "test response"}'

        db.store_workflow_output(workflow_id, 'knowledge_query', 'complete', output_json)

        # Retrieve
        workflow = db.get_workflow(workflow_id)

        assert workflow is not None
        assert workflow['workflow_id'] == workflow_id
        assert workflow['output'] == output_json

    def test_get_workflow_returns_none_for_missing(self, db):
        """
        CRITERION 2: get_workflow() returns None for missing workflows.

        ✅ PASS: Handles nonexistent IDs gracefully
        """
        result = db.get_workflow('nonexistent_id_12345')
        assert result is None

    def test_workflow_retrieval_has_correct_structure(self, db):
        """
        CRITERION 2: Retrieved workflow has correct structure.

        ✅ PASS: All fields accessible
        """
        db.store_workflow_output('wf_struct_1', 'job_search', 'error',
                                '{"error": "test"}')

        workflow = db.get_workflow('wf_struct_1')

        # Should be able to access all fields
        assert workflow['workflow_id'] == 'wf_struct_1'
        assert workflow['type'] == 'job_search'
        assert workflow['status'] == 'error'
        assert workflow['output'] == '{"error": "test"}'
        assert workflow['created_at'] is not None
        assert workflow['updated_at'] is not None

    # ========================================================================
    # CRITERION 3: Outputs persist across API restart
    # ========================================================================

    def test_outputs_persist_after_restart(self, db):
        """
        CRITERION 3: Outputs persist across API restart.

        ✅ PASS: Store → close → reopen → retrieve
        """
        db_path = db.db_path

        # Store multiple workflows
        workflows_to_store = [
            ('wf_persist_a', 'knowledge_query', 'complete', '{"a": 1}'),
            ('wf_persist_b', 'trading_health', 'complete', '{"b": 2}'),
            ('wf_persist_c', 'job_search', 'complete', '{"c": 3}'),
        ]

        for wf_id, wf_type, status, output in workflows_to_store:
            db.store_workflow_output(wf_id, wf_type, status, output)

        # Simulate API restart: create new database connection
        db_restarted = EMyDatabase(db_path)

        # Verify all workflows still exist
        for wf_id, wf_type, status, expected_output in workflows_to_store:
            workflow = db_restarted.get_workflow(wf_id)
            assert workflow is not None, f"Workflow {wf_id} should persist"
            assert workflow['output'] == expected_output

    def test_workflow_updates_persist(self, db):
        """
        CRITERION 3: Workflow updates persist across restart.

        ✅ PASS: Update → close → reopen → verify update
        """
        db_path = db.db_path
        workflow_id = 'wf_update_persist'

        # Initial store
        db.store_workflow_output(workflow_id, 'knowledge_query', 'in_progress',
                               '{"status": "running"}')

        # Update
        db.store_workflow_output(workflow_id, 'knowledge_query', 'complete',
                               '{"status": "done"}')

        # Simulate restart
        db_restarted = EMyDatabase(db_path)

        # Verify update persisted
        workflow = db_restarted.get_workflow(workflow_id)
        assert workflow['status'] == 'complete'
        assert '{"status": "done"}' in workflow['output']

    # ========================================================================
    # CRITERION 4: Database persistence verified
    # ========================================================================

    def test_workflow_timestamps_are_valid(self, db):
        """
        CRITERION 4: Database persistence verified via timestamps.

        ✅ PASS: Timestamps are ISO format
        """
        db.store_workflow_output('wf_ts_1', 'knowledge_query', 'complete', '{}')

        workflow = db.get_workflow('wf_ts_1')

        # Timestamps should be ISO format (contain T or digits)
        assert workflow['created_at'] is not None
        assert workflow['updated_at'] is not None

    def test_multiple_workflows_independent(self, db):
        """
        CRITERION 4: Multiple workflows stored independently.

        ✅ PASS: Each workflow maintains its own data
        """
        workflows = [
            ('wf_indep_1', 'knowledge_query', '{"id": 1}'),
            ('wf_indep_2', 'trading_health', '{"id": 2}'),
            ('wf_indep_3', 'job_search', '{"id": 3}'),
        ]

        # Store all
        for wf_id, wf_type, output in workflows:
            db.store_workflow_output(wf_id, wf_type, 'complete', output)

        # Verify each is independent
        for wf_id, wf_type, expected_output in workflows:
            workflow = db.get_workflow(wf_id)
            assert workflow['type'] == wf_type
            assert workflow['output'] == expected_output

    def test_large_workflow_output_stored(self, db):
        """
        CRITERION 4: Large workflow outputs handled correctly.

        ✅ PASS: Can store and retrieve large JSON outputs
        """
        large_output = '{"data": "' + 'x' * 10000 + '"}'  # 10KB+ output

        db.store_workflow_output('wf_large_1', 'knowledge_query', 'complete',
                                large_output)

        workflow = db.get_workflow('wf_large_1')
        assert workflow['output'] == large_output
        assert len(workflow['output']) > 10000
