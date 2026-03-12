"""Abstract base class for LangGraph domain nodes.

All domain nodes inherit from this to ensure consistent state handling.
"""

from abc import ABC, abstractmethod


class BaseDomainNode(ABC):
    """Abstract base for all domain agent nodes.

    Subclasses must implement execute() which:
    - Takes a state dict
    - Returns only the fields being updated (LangGraph merge semantics)
    - Never returns full state
    """

    @abstractmethod
    def execute(self, state: dict) -> dict:
        """Execute node logic and return state updates only.

        Args:
            state: Current workflow state dict

        Returns:
            Dict with only the fields being updated (step_count, execution_history,
            context, current_agent, etc.) — NOT the full state
        """
        ...
