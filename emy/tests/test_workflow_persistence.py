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
