"""
Agent Executor - Instantiates and executes agents based on workflow requests.

Responsible for:
- Mapping workflow type to agent
- Instantiating agents with proper configuration
- Executing agent.run() and capturing results
- Error handling and logging
"""

import logging
import json
from typing import Dict, Any, Tuple, Optional

from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.trading_agent import TradingAgent

logger = logging.getLogger('AgentExecutor')

# Map workflow types to agent classes
AGENT_MAP = {
    'knowledge_query': KnowledgeAgent,
    'knowledge_synthesis': KnowledgeAgent,
    'trading_health': TradingAgent,
    'trading_analysis': TradingAgent,
    # Future agents will be added here
    # 'job_search': JobSearchAgent,
}


class AgentExecutor:
    """Executor for running agents based on workflow requests."""

    @staticmethod
    def execute(workflow_type: str, agents: list, workflow_input: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Execute a workflow by instantiating and running the appropriate agent(s).

        Args:
            workflow_type: Type of workflow (e.g., 'knowledge_query')
            agents: List of agent names to execute (e.g., ['KnowledgeAgent'])
            workflow_input: Input data for the agents

        Returns:
            (success: bool, output: str or None)
                success=True if at least one agent executed successfully
                output=JSON string containing combined results or None on failure
        """
        try:
            # For now, execute the first agent (Phase 1b only supports single agents)
            if not agents:
                logger.error("No agents specified in workflow")
                return (False, None)

            agent_name = agents[0]

            # Get agent class from workflow type
            agent_class = AGENT_MAP.get(workflow_type)
            if not agent_class:
                logger.error(f"Unknown workflow type: {workflow_type}")
                return (False, None)

            # Instantiate agent
            logger.info(f"Instantiating {agent_name} for workflow: {workflow_type}")
            agent = agent_class()

            # Execute agent
            logger.info(f"Executing {agent_name}...")
            success, result = agent.run()

            if success:
                # Serialize result to JSON
                output_json = json.dumps(result)
                logger.info(f"Agent {agent_name} completed successfully")
                return (True, output_json)
            else:
                error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                logger.error(f"Agent {agent_name} failed: {error_msg}")
                return (False, None)

        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            return (False, None)
