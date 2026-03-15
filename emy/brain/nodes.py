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
    Route workflow to next agent group or individual agent.

    If agent_groups is set, route to group executor. Otherwise use agents list (backward compat).

    Args:
        state: Current EMyState

    Returns:
        Updated state with routing decision made
    """
    # Check if using agent groups
    if state.agent_groups and state.current_group_index < len(state.agent_groups):
        current_group = state.agent_groups[state.current_group_index]
        logger.info(f"Routing to agent group {state.current_group_index}: {current_group}")
        state.messages.append({
            "agent": "Router",
            "message": f"Routing to group {state.current_group_index}: {current_group}"
        })
    elif state.agents and len(state.agents) > 0:
        # Backward compatibility: single agent mode
        next_agent = state.agents[0]
        state.current_agent = next_agent
        logger.info(f"Routing to agent {next_agent} (backward compat mode)")
        state.messages.append({
            "agent": "Router",
            "message": f"Routing to {next_agent}"
        })
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


def create_agent_group_node():
    """
    Create a LangGraph node for executing an agent group in parallel.

    Returns:
        Async function that executes the current group and updates state
    """
    async def agent_group_node(state: EMyState) -> EMyState:
        """
        Execute all agents in current group in parallel.
        """
        from emy.brain.executor import execute_agent_group_parallel

        if not state.agent_groups or state.current_group_index >= len(state.agent_groups):
            logger.info(f"No more agent groups to execute")
            return state

        logger.info(f"Executing agent group {state.current_group_index}")

        try:
            result = await execute_agent_group_parallel(state)
            result.status = "completed"
            return result
        except Exception as e:
            state.error = f"Agent group execution failed: {str(e)}"
            state.status = "failed"
            logger.exception(f"Agent group execution error")
            return state

    return agent_group_node
