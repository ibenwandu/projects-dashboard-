"""LangGraph agent nodes for Emy Brain."""
from typing import Type
from emy.brain.state import EMyState
from emy.agents.base_agent import EMySubAgent
from emy.agents.trading_agent import TradingAgent
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.research_agent import ResearchAgent
from emy.agents.project_monitor_agent import ProjectMonitorAgent
from emy.agents.job_search_agent import JobSearchAgent
import logging

logger = logging.getLogger('EMyBrain')


# Agent registry: maps agent names to their classes
AGENT_REGISTRY = {
    'TradingAgent': TradingAgent,
    'KnowledgeAgent': KnowledgeAgent,
    'ResearchAgent': ResearchAgent,
    'ProjectMonitorAgent': ProjectMonitorAgent,
    'JobSearchAgent': JobSearchAgent,
}


async def router_node(state: EMyState) -> EMyState:
    """
    Route workflow to appropriate agent.

    Selects the first agent in the agents list and sets it as current_agent.

    Args:
        state: Current EMyState

    Returns:
        Updated state with current_agent set
    """
    if state.agents and len(state.agents) > 0:
        next_agent = state.agents[0]
        state.current_agent = next_agent

        # Add routing message to audit trail
        state.messages.append({
            "agent": "Router",
            "message": f"Routing to {next_agent}"
        })

        logger.info(f"Routing workflow {state.workflow_id} to {next_agent}")
    else:
        logger.warning(f"No agents specified for workflow {state.workflow_id}")

    state.status = "executing"
    return state


def create_agent_node(agent_name: str):
    """
    Create a LangGraph node for an agent.

    Factory function that returns an async function that executes the agent
    and updates the state with results.

    Args:
        agent_name: Name of agent (must be in AGENT_REGISTRY)

    Returns:
        Async function that takes state and returns updated state
    """
    async def agent_node(state: EMyState) -> EMyState:
        """
        Execute agent and update state.

        Args:
            state: Current EMyState

        Returns:
            Updated state with results
        """
        if agent_name not in AGENT_REGISTRY:
            error_msg = f"Agent {agent_name} not found in registry"
            logger.error(error_msg)
            state.error = error_msg
            state.status = "failed"
            return state

        try:
            # Instantiate agent
            agent_class: Type[EMySubAgent] = AGENT_REGISTRY[agent_name]
            agent = agent_class()

            # Log agent execution start
            logger.info(f"Executing agent {agent_name} for workflow {state.workflow_id}")
            state.messages.append({
                "agent": agent_name,
                "message": f"Starting execution with input: {state.input}"
            })

            # Execute agent
            success, output = agent.run()

            # Store result
            if success:
                state.results[agent_name] = output
                state.status = "completed"
                state.messages.append({
                    "agent": agent_name,
                    "message": f"Execution completed successfully"
                })
                logger.info(f"Agent {agent_name} completed successfully")
            else:
                state.error = f"Agent {agent_name} failed"
                state.results[agent_name] = output
                state.status = "failed"
                state.messages.append({
                    "agent": agent_name,
                    "message": f"Execution failed: {output}"
                })
                logger.warning(f"Agent {agent_name} failed: {output}")

        except Exception as e:
            state.error = f"Exception in {agent_name}: {str(e)}"
            state.status = "failed"
            state.messages.append({
                "agent": agent_name,
                "message": f"Exception: {str(e)}"
            })
            logger.exception(f"Exception in agent {agent_name}")

        return state

    return agent_node
