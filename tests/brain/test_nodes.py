"""Tests for LangGraph agent nodes."""
import pytest
import pytest_asyncio
import asyncio
from emy.brain.nodes import router_node, create_agent_node, AGENT_REGISTRY
from emy.brain.state import create_initial_state, EMyState


@pytest.mark.asyncio
async def test_router_node_routes_to_trading_agent():
    """Test that router node correctly routes to TradingAgent."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market health"}
    )

    # Router should set current_agent and add routing message
    result = await router_node(state)

    assert result.current_agent == "TradingAgent"
    assert len(result.messages) > 0
    assert any("Router" in msg.get("agent", "") for msg in result.messages)


@pytest.mark.asyncio
async def test_agent_registry_contains_trading_agent():
    """Test that TradingAgent is registered."""
    assert "TradingAgent" in AGENT_REGISTRY
    assert AGENT_REGISTRY["TradingAgent"] is not None


@pytest.mark.asyncio
async def test_create_agent_node_returns_callable():
    """Test that create_agent_node returns a callable node function."""
    node = create_agent_node("TradingAgent")
    assert callable(node)


@pytest.mark.asyncio
async def test_agent_node_execution_updates_state():
    """Test that agent node execution updates state with results."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market"}
    )
    state.current_agent = "TradingAgent"

    # Create and execute agent node
    agent_node = create_agent_node("TradingAgent")
    result = await agent_node(state)

    # State should be updated with agent result
    assert result.current_agent == "TradingAgent"
    assert "TradingAgent" in result.results
    assert result.results["TradingAgent"] is not None
