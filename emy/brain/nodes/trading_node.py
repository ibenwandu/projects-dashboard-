"""TradingBrainNode - wraps TradingAgent for LangGraph."""

import logging
from emy.brain.nodes.base_node import BaseDomainNode
from emy.agents.trading_agent import TradingAgent

logger = logging.getLogger("TradingBrainNode")


class TradingBrainNode(BaseDomainNode):
    """Adapter node for TradingAgent.

    Wraps TradingAgent.run() and integrates result into workflow state.
    """

    def __init__(self):
        """Initialize node with TradingAgent instance."""
        self._agent = TradingAgent()

    def execute(self, state: dict) -> dict:
        """Execute TradingAgent and return state updates.

        Args:
            state: Current workflow state dict

        Returns:
            State updates dict with step_count, execution_history, context, current_agent
        """
        try:
            success, result = self._agent.run()
        except Exception as e:
            logger.error(f"TradingAgent failed: {e}")
            result = {"error": str(e)}
            success = False

        # Increment step count and append to history
        step = state.get("step_count", 0) + 1
        history = list(state.get("execution_history", []))
        history.append({
            "step": step,
            "agent": "TradingAgent",
            "success": success,
            "result": result,
        })

        return {
            "step_count": step,
            "execution_history": history,
            "context": {**state.get("context", {}), "agent_result": result},
            "current_agent": "TradingAgent",
        }
