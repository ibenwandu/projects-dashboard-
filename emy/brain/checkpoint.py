"""Checkpoint management for job resumption."""

import json
import logging
from pathlib import Path
from typing import Optional
from emy.brain.state import EMyState

logger = logging.getLogger('EMyBrain.Checkpoint')


class CheckpointManager:
    """Saves and loads job state for resumption."""

    def __init__(self, checkpoint_dir: str = "emy_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save_checkpoint(self, job_id: str, state: EMyState):
        """Save job state as checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{job_id}.json"

        # Convert state to dict
        state_dict = {
            "workflow_id": state.workflow_id,
            "workflow_type": state.workflow_type,
            "agents": state.agents,
            "agent_groups": state.agent_groups,
            "current_agent": state.current_agent,
            "current_group_index": state.current_group_index,
            "agents_executing": state.agents_executing,
            "input": state.input,
            "results": state.results,
            "messages": state.messages,
            "status": state.status,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "error": state.error,
            "error_context": state.error_context
        }

        with open(checkpoint_file, 'w') as f:
            json.dump(state_dict, f, indent=2)

        logger.info(f"Saved checkpoint for job {job_id}")

    def load_checkpoint(self, job_id: str) -> Optional[EMyState]:
        """Load job state from checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{job_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, 'r') as f:
            state_dict = json.load(f)

        # Reconstruct state from dict
        state = EMyState(
            workflow_id=state_dict['workflow_id'],
            workflow_type=state_dict['workflow_type'],
            agents=state_dict['agents'],
            input=state_dict['input']
        )

        # Set remaining fields
        state.agent_groups = state_dict.get('agent_groups', [])
        state.current_agent = state_dict.get('current_agent')
        state.current_group_index = state_dict.get('current_group_index', 0)
        state.agents_executing = state_dict.get('agents_executing', [])
        state.results = state_dict.get('results', {})
        state.messages = state_dict.get('messages', [])
        state.status = state_dict.get('status', 'pending')
        state.created_at = state_dict.get('created_at')
        state.updated_at = state_dict.get('updated_at')
        state.error = state_dict.get('error')
        state.error_context = state_dict.get('error_context', {})

        logger.info(f"Loaded checkpoint for job {job_id}")
        return state

    def delete_checkpoint(self, job_id: str):
        """Delete checkpoint after successful completion."""
        checkpoint_file = self.checkpoint_dir / f"{job_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Deleted checkpoint for job {job_id}")


# Global checkpoint manager
checkpoint_manager = CheckpointManager()
