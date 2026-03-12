"""ProjectMonitorBrainNode - wraps ProjectMonitorAgent for LangGraph."""

import logging
from emy.brain.nodes.base_node import BaseDomainNode
from emy.agents.project_monitor_agent import ProjectMonitorAgent

logger = logging.getLogger("ProjectMonitorBrainNode")


class ProjectMonitorBrainNode(BaseDomainNode):
    """Adapter node for ProjectMonitorAgent.

    Wraps ProjectMonitorAgent.run() and integrates result into workflow state.
    """

    def __init__(self):
        """Initialize node with ProjectMonitorAgent instance."""
        self._agent = ProjectMonitorAgent()

    def execute(self, state: dict) -> dict:
        """Execute ProjectMonitorAgent and return state updates.

        Args:
            state: Current workflow state dict

        Returns:
            State updates dict with step_count, execution_history, context, current_agent
        """
        try:
            success, result = self._agent.run()
        except Exception as e:
            logger.error(f"ProjectMonitorAgent failed: {e}")
            result = {"error": str(e)}
            success = False

        # Increment step count and append to history
        step = state.get("step_count", 0) + 1
        history = list(state.get("execution_history", []))
        history.append({
            "step": step,
            "agent": "ProjectMonitorAgent",
            "success": success,
            "result": result,
        })

        return {
            "step_count": step,
            "execution_history": history,
            "context": {**state.get("context", {}), "agent_result": result},
            "current_agent": "ProjectMonitorAgent",
        }
