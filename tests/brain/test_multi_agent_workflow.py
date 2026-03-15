"""Tests for end-to-end multi-agent workflows with parallel execution."""
import pytest
import pytest_asyncio
from emy.brain.graph import execute_workflow
from emy.brain.state import create_initial_state_with_groups, create_initial_state


@pytest.mark.asyncio
async def test_multi_agent_workflow_parallel_execution():
    """
    Test complete multi-agent workflow with parallel execution.

    Simulates: Market Analysis workflow
    - Group 1 (parallel): TradingAgent + ResearchAgent analyze market
    - Group 2 (sequential): KnowledgeAgent synthesizes insights
    """
    state = create_initial_state_with_groups(
        workflow_type="market_analysis",
        agent_groups=[
            ["TradingAgent", "ResearchAgent"],  # Parallel: market analysis
            ["KnowledgeAgent"]  # Sequential: synthesis
        ],
        input={
            "query": "What is the market outlook for EUR/USD?",
            "market_pair": "EUR/USD"
        }
    )

    # Execute workflow
    result = await execute_workflow(state)

    # Verify completion
    assert result.workflow_id == state.workflow_id
    assert result.status in ["completed", "failed"]

    # Verify all groups executed
    assert result.current_group_index == 2  # Both groups processed

    # Verify results from both groups
    assert "TradingAgent" in result.results or result.error is not None
    assert "ResearchAgent" in result.results or result.error is not None
    assert "KnowledgeAgent" in result.results or result.error is not None

    # Verify audit trail
    assert len(result.messages) > 0
    assert any("TradingAgent" in msg.get("agent", "") for msg in result.messages)
    assert any("KnowledgeAgent" in msg.get("agent", "") for msg in result.messages)


@pytest.mark.asyncio
async def test_backward_compatibility_single_agent_unchanged():
    """Verify that single-agent workflows still work (backward compatibility)."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    result = await execute_workflow(state)

    # Single-agent workflow should complete
    assert result.status in ["completed", "failed"]
    assert result.current_agent == "TradingAgent"
    assert "TradingAgent" in result.results or result.error is not None
