"""
Workflow state management for orchestrator.

Handles:
- Tracking phase transitions
- Maintaining workflow state
- Recording status changes
- Workflow history
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class WorkflowStateManager:
    """Manages workflow state and transitions."""

    # Valid phase states
    PHASES = ["PENDING", "ANALYST", "FOREX_EXPERT", "CODING_EXPERT", "ORCHESTRATOR", "DEPLOYED"]

    # Valid statuses
    STATUSES = ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "BLOCKED"]

    def __init__(self):
        """Initialize workflow state manager."""
        self.current_cycle = 0
        self.current_phase = "PENDING"
        self.current_status = "PENDING"
        self.phase_history = []
        self.state_snapshots = []

    def start_cycle(self, cycle_number: int) -> None:
        """
        Start a new workflow cycle.

        Args:
            cycle_number: Cycle number to start
        """
        self.current_cycle = cycle_number
        self.current_phase = "PENDING"
        self.current_status = "PENDING"
        self._record_snapshot()

    def transition_to_phase(
        self,
        phase: str,
        status: str = "IN_PROGRESS"
    ) -> bool:
        """
        Transition workflow to a new phase.

        Args:
            phase: Target phase name
            status: Initial status for phase

        Returns:
            Success flag
        """
        if phase not in self.PHASES:
            return False

        if status not in self.STATUSES:
            return False

        # Record transition
        self.phase_history.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "from_phase": self.current_phase,
            "from_status": self.current_status,
            "to_phase": phase,
            "to_status": status,
            "cycle_number": self.current_cycle
        })

        self.current_phase = phase
        self.current_status = status
        self._record_snapshot()

        return True

    def update_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update current phase status.

        Args:
            status: New status
            details: Optional status details

        Returns:
            Success flag
        """
        if status not in self.STATUSES:
            return False

        # Record transition
        self.phase_history.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "phase": self.current_phase,
            "from_status": self.current_status,
            "to_status": status,
            "cycle_number": self.current_cycle,
            "details": details or {}
        })

        self.current_status = status
        self._record_snapshot()

        return True

    def is_phase_complete(self) -> bool:
        """
        Check if current phase is complete.

        Returns:
            True if phase is completed
        """
        return self.current_status == "COMPLETED"

    def is_workflow_blocked(self) -> bool:
        """
        Check if workflow is blocked.

        Returns:
            True if any phase is blocked
        """
        return self.current_status == "BLOCKED"

    def get_next_phase(self) -> Optional[str]:
        """
        Get the next phase in workflow.

        Returns:
            Next phase name or None if at end
        """
        current_index = self.PHASES.index(self.current_phase) if self.current_phase in self.PHASES else -1

        if current_index >= 0 and current_index < len(self.PHASES) - 1:
            return self.PHASES[current_index + 1]

        return None

    def get_phase_history(self) -> List[Dict[str, Any]]:
        """
        Get phase transition history.

        Returns:
            List of transitions
        """
        return self.phase_history.copy()

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current workflow state.

        Returns:
            Current state dict
        """
        return {
            "cycle_number": self.current_cycle,
            "phase": self.current_phase,
            "status": self.current_status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    def _record_snapshot(self) -> None:
        """Record current state snapshot."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cycle_number": self.current_cycle,
            "phase": self.current_phase,
            "status": self.current_status

        }
        self.state_snapshots.append(snapshot)


class WorkflowOrchestrator:
    """High-level workflow orchestration."""

    def __init__(self):
        """Initialize orchestrator."""
        self.state_manager = WorkflowStateManager()
        self.pending_actions = []

    def queue_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Queue an action for workflow.

        Args:
            action: Action name (ANALYZE, RECOMMEND, IMPLEMENT, APPROVE, DEPLOY)
            details: Optional action details
        """
        self.pending_actions.append({
            "action": action,
            "details": details or {},
            "queued_at": datetime.utcnow().isoformat() + "Z"
        })

    def get_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Get next action to execute.

        Returns:
            Next action dict or None
        """
        if self.pending_actions:
            return self.pending_actions.pop(0)
        return None

    def has_pending_actions(self) -> bool:
        """
        Check if there are pending actions.

        Returns:
            True if actions are pending
        """
        return len(self.pending_actions) > 0

    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get overall workflow status.

        Returns:
            Status dict with current state and pending actions
        """
        return {
            "current_state": self.state_manager.get_current_state(),
            "pending_actions": len(self.pending_actions),
            "is_blocked": self.state_manager.is_workflow_blocked(),
            "next_phase": self.state_manager.get_next_phase()
        }
