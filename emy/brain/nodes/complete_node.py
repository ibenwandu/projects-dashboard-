"""CompleteBrainNode - terminal node that marks workflow as complete."""

from emy.brain.nodes.base_node import BaseDomainNode


class CompleteBrainNode(BaseDomainNode):
    """Terminal node that sets status=complete.

    All domain nodes route here before END. Prepares final_result from agent output.
    """

    def execute(self, state: dict) -> dict:
        """Mark workflow complete and set final_result.

        Args:
            state: Current workflow state dict

        Returns:
            State updates with status=complete and final_result
        """
        return {
            "status": "complete",
            "final_result": state.get("context", {}).get("agent_result", {}),
        }
