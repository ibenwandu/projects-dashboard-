"""Tests for LangGraph state graph."""
import pytest
import pytest_asyncio
from emy.brain.graph import build_graph, execute_workflow
from emy.brain.state import create_initial_state, EMyState


@pytest.mark.asyncio
async def test_build_graph_creates_valid_graph():
    """Test that build_graph creates a valid LangGraph."""
    graph = build_graph()
    assert graph is not None
    # Graph should have ainvoke method
    assert hasattr(graph, 'ainvoke')


@pytest.mark.asyncio
async def test_execute_workflow_with_trading_agent():
    """Test executing workflow with TradingAgent."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market health"}
    )

    result = await execute_workflow(state)

    # Workflow should complete (status may be completed or failed depending on agent)
    assert result.workflow_id == state.workflow_id
    assert result.workflow_type == "trading_health"
    # Router should have set current_agent
    assert result.current_agent is not None


@pytest.mark.asyncio
async def test_workflow_updates_state_with_messages():
    """Test that workflow execution adds messages to state."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Test"}
    )

    initial_messages = len(state.messages)
    result = await execute_workflow(state)

    # Messages should be added during execution
    assert len(result.messages) > initial_messages
    # Should have router message
    assert any("Router" in msg.get("agent", "") for msg in result.messages)


@pytest.mark.asyncio
async def test_graph_with_agent_groups_executes_parallel():
    """Test that graph supports agent groups and executes them."""
    from emy.brain.state import create_initial_state_with_groups

    state = create_initial_state_with_groups(
        workflow_type="market_analysis",
        agent_groups=[
            ["TradingAgent"],
            ["KnowledgeAgent"]
        ],
        input={"query": "Check market"}
    )

    graph = build_graph()
    result = await execute_workflow(state)

    # Both groups should have executed
    assert result.current_group_index == 2  # Both groups processed
    assert "TradingAgent" in result.results
    assert "KnowledgeAgent" in result.results
