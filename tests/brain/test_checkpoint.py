"""Tests for checkpoint management and job resumption."""
import pytest
import os
from pathlib import Path
from emy.brain.checkpoint import CheckpointManager, checkpoint_manager
from emy.brain.state import create_initial_state_with_groups


def test_save_and_load_checkpoint():
    """Test saving and loading job checkpoints."""
    # Create state
    state = create_initial_state_with_groups(
        workflow_type="test_workflow",
        agent_groups=[["Agent1"], ["Agent2"], ["Agent3"]],
        input={"query": "Test"}
    )
    state.current_group_index = 1
    state.status = "failed"
    state.results = {"Agent1": {"output": "test"}}

    job_id = "test_checkpoint_001"

    # Save checkpoint
    checkpoint_manager.save_checkpoint(job_id, state)

    # Load and verify
    loaded_state = checkpoint_manager.load_checkpoint(job_id)

    assert loaded_state is not None
    assert loaded_state.workflow_type == "test_workflow"
    assert loaded_state.current_group_index == 1
    assert loaded_state.status == "failed"
    assert loaded_state.results["Agent1"]["output"] == "test"

    # Cleanup
    checkpoint_manager.delete_checkpoint(job_id)


def test_resume_job_from_checkpoint():
    """Test resuming job from group checkpoint."""
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[["Agent1"], ["Agent2"], ["Agent3"]],
        input={"query": "Test"}
    )
    state.current_group_index = 1
    state.agents = ["Agent1", "Agent2", "Agent3"]

    job_id = "test_resume_001"

    # Save checkpoint
    checkpoint_manager.save_checkpoint(job_id, state)

    # Load checkpoint
    resumed_state = checkpoint_manager.load_checkpoint(job_id)

    # Verify all fields intact
    assert resumed_state.current_group_index == 1
    assert resumed_state.agents == ["Agent1", "Agent2", "Agent3"]
    assert resumed_state.agent_groups == [["Agent1"], ["Agent2"], ["Agent3"]]

    checkpoint_manager.delete_checkpoint(job_id)


def test_checkpoint_not_found():
    """Test loading non-existent checkpoint."""
    loaded = checkpoint_manager.load_checkpoint("nonexistent_job_12345")
    assert loaded is None


def test_delete_checkpoint():
    """Test checkpoint deletion."""
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[["Agent1"]],
        input={}
    )
    job_id = "test_delete_001"

    # Save and verify file exists
    checkpoint_manager.save_checkpoint(job_id, state)
    assert checkpoint_manager.load_checkpoint(job_id) is not None

    # Delete and verify
    checkpoint_manager.delete_checkpoint(job_id)
    assert checkpoint_manager.load_checkpoint(job_id) is None
