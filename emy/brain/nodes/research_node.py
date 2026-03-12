"""ResearchBrainNode - wraps ResearchAgent for LangGraph."""

import logging
from emy.brain.nodes.base_node import BaseDomainNode
from emy.agents.research_agent import ResearchAgent

logger = logging.getLogger("ResearchBrainNode")


class ResearchBrainNode(BaseDomainNode):
    """Adapter node for ResearchAgent.

    Wraps ResearchAgent.run() and integrates result into workflow state.
    Extracts project_name from user_request before calling agent.
    """

    def __init__(self):
        """Initialize node with ResearchAgent instance."""
        self._agent = ResearchAgent()

    def execute(self, state: dict) -> dict:
        """Execute ResearchAgent and return state updates.

        Extracts project_name from user_request and passes to agent.

        Args:
            state: Current workflow state dict

        Returns:
            State updates dict with step_count, execution_history, context, current_agent
        """
        # Extract project_name from user_request
        project_name = state.get("user_request", {}).get("project_name")

        try:
            success, result = self._agent.run(project_name=project_name)
        except Exception as e:
            logger.error(f"ResearchAgent failed: {e}")
            result = {"error": str(e)}
            success = False

        # Increment step count and append to history
        step = state.get("step_count", 0) + 1
        history = list(state.get("execution_history", []))
        history.append({
            "step": step,
            "agent": "ResearchAgent",
            "success": success,
            "result": result,
        })

        return {
            "step_count": step,
            "execution_history": history,
            "context": {**state.get("context", {}), "agent_result": result},
            "current_agent": "ResearchAgent",
        }
