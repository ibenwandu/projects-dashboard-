"""Parallel agent executor for LangGraph."""

import asyncio
import logging
from typing import Type, Tuple, Dict, Any
from emy.brain.state import EMyState
from emy.agents.base_agent import EMySubAgent
from emy.brain.nodes import AGENT_REGISTRY

logger = logging.getLogger('EMyBrain.Executor')


async def execute_agent_group_parallel(state: EMyState) -> EMyState:
    """
    Execute all agents in the current group in parallel.

    Args:
        state: Current EMyState with agent_groups set

    Returns:
        Updated state with results from all agents in the group
    """
    if not state.agent_groups or state.current_group_index >= len(state.agent_groups):
        logger.warning(f"Invalid group index {state.current_group_index}")
        return state

    # Get current group
    current_group = state.agent_groups[state.current_group_index]
    state.agents_executing = current_group.copy()

    logger.info(f"Executing agent group {state.current_group_index}: {current_group}")

    # Create tasks for all agents in the group
    tasks = []
    for agent_name in current_group:
        task = execute_single_agent(agent_name, state)
        tasks.append(task)

    # Run all tasks concurrently with timeout protection
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=300  # 5 minutes per group
        )
    except asyncio.TimeoutError:
        logger.error(f"Agent group {state.current_group_index} execution timed out")
        state.status = "timeout"
        state.messages.append({
            "agent": "Executor",
            "message": f"Group timed out after 300s"
        })
        return state

    # Merge results into state
    for agent_name, result in zip(current_group, results):
        if isinstance(result, Exception):
            state.results[agent_name] = {"error": str(result)}
            state.messages.append({
                "agent": agent_name,
                "message": f"Failed: {str(result)}"
            })
            logger.error(f"Agent {agent_name} failed: {result}")
        else:
            success, output = result
            state.results[agent_name] = output
            state.messages.append({
                "agent": agent_name,
                "message": f"Completed: {success}"
            })
            logger.info(f"Agent {agent_name} completed: {success}")

    # Move to next group
    state.current_group_index += 1
    state.agents_executing = []

    return state


async def execute_single_agent(agent_name: str, state: EMyState) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute a single agent asynchronously.

    Args:
        agent_name: Name of agent to execute
        state: Current workflow state

    Returns:
        (success: bool, results: dict) from agent.run()
    """
    if agent_name not in AGENT_REGISTRY:
        raise ValueError(f"Agent {agent_name} not found in registry")

    agent_class: Type[EMySubAgent] = AGENT_REGISTRY[agent_name]
    agent = agent_class()

    logger.info(f"Starting agent {agent_name}")

    # Run agent in thread pool to prevent blocking event loop
    success, output = await asyncio.to_thread(agent.run)

    return (success, output)
