"""WorkflowState dataclass for LangGraph state management.

Represents the complete state of a workflow as it progresses through the Brain's graph,
including routing decisions, context, execution history, and final results.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class WorkflowState:
    """Immutable state object for LangGraph workflow execution.

    Attributes:
        user_request: Initial user request/input as dict
        workflow_type: Classification (job_search, trading, knowledge_query, etc.)
        current_agent: Which agent is currently handling this step
        step_count: Number of steps executed so far
        context: Accumulated context from previous steps
        execution_history: List of step results and transitions
        final_result: The ultimate output (populated at END)
        status: Current workflow status (running, complete, error)
        error: Error message if status is error
        checkpoint: Saved state for resumption
    """

    user_request: dict
    workflow_type: str = ""
    current_agent: str = ""
    step_count: int = 0
    context: dict = field(default_factory=dict)
    execution_history: list = field(default_factory=list)
    final_result: dict = field(default_factory=dict)
    status: str = "running"
    error: Optional[str] = None
    checkpoint: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert state to dictionary for serialization.

        Returns:
            Dictionary representation of all state fields
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowState:
        """Reconstruct WorkflowState from dictionary.

        Args:
            data: Dictionary with fields matching WorkflowState attributes

        Returns:
            Reconstructed WorkflowState instance
        """
        # Only include fields that exist in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
