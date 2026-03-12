"""UnknownBrainNode - fallback node for unrecognized workflow types."""

from emy.brain.nodes.base_node import BaseDomainNode


class UnknownBrainNode(BaseDomainNode):
    """Fallback node for unknown workflow types.

    Routes here when workflow_type doesn't match any known domain agent.
    Sets status=error with descriptive message.
    """

    def execute(self, state: dict) -> dict:
        """Handle unknown workflow type.

        Args:
            state: Current workflow state dict

        Returns:
            State updates with status=error and error message
        """
        workflow_type = state.get("workflow_type", "")
        return {
            "status": "error",
            "error": f"unknown_workflow_type: {workflow_type}",
            "final_result": {},
        }
