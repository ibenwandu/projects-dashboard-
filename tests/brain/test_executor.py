"""Tests for parallel agent executor."""

import pytest
import pytest_asyncio
from emy.brain.executor import execute_agent_group_parallel
from emy.brain.state import create_initial_state_with_groups


@pytest.mark.asyncio
async def test_execute_agent_group_parallel_with_two_agents():
    """Test that two agents in a group execute concurrently."""
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[["TradingAgent", "KnowledgeAgent"]],
        input={"query": "Test"}
    )

    # Execute the group
    result = await execute_agent_group_parallel(state)

    # Both agents should have results
    assert "TradingAgent" in result.results
    assert "KnowledgeAgent" in result.results

    # agents_executing should be set
    assert result.current_group_index == 1
    assert len(result.agents_executing) == 0  # Cleared after execution

    # Messages should include both agent executions
    assert any("TradingAgent" in msg.get("agent", "") for msg in result.messages)
    assert any("KnowledgeAgent" in msg.get("agent", "") for msg in result.messages)


@pytest.mark.asyncio
async def test_execute_multiple_groups_sequentially():
    """Test that groups execute sequentially."""
    state = create_initial_state_with_groups(
        workflow_type="test",
        agent_groups=[
            ["TradingAgent"],  # Group 0
            ["KnowledgeAgent", "ResearchAgent"]  # Group 1
        ],
        input={"query": "Test"}
    )

    # Execute first group
    state = await execute_agent_group_parallel(state)
    assert state.current_group_index == 1
    assert "TradingAgent" in state.results

    # Execute second group (both agents in parallel)
    state = await execute_agent_group_parallel(state)
    assert state.current_group_index == 2
    assert "KnowledgeAgent" in state.results
    assert "ResearchAgent" in state.results
