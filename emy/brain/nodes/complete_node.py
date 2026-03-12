"""CompleteBrainNode - terminal node that marks workflow as complete."""

from emy.brain.nodes.base_node import BaseDomainNode


class CompleteBrainNode(BaseDomainNode):
    """Terminal node that sets status=complete.

    All domain nodes route here before END. Prepares final_result from agent output.
    """

    def execute(self, state: dict) -> dict:
        """Mark workflow complete and set final_result.

        Preserves error status if already set (from unknown_node or other error handlers).

        Args:
            state: Current workflow state dict

        Returns:
            State updates with status and final_result
        """
        # If status is already error, preserve it; otherwise mark complete
        current_status = state.get("status", "running")
        status = current_status if current_status == "error" else "complete"

        return {
            "status": status,
            "final_result": state.get("context", {}).get("agent_result", {}),
        }
