"""Tests for LangGraph state schema."""
from typing import Any, Dict, List
from emy.brain.state import EMyState, create_initial_state, create_initial_state_with_groups
import pytest


def test_initial_state_creation():
    """Test creating initial state for a workflow."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check market health"}
    )

    assert state.workflow_type == "trading_health"
    assert state.agents == ["TradingAgent"]
    assert state.input == {"query": "Check market health"}
    assert state.current_agent is None
    assert state.results == {}
    assert state.messages == []
    assert state.status == "pending"


def test_state_update_after_agent_execution():
    """Test updating state after an agent processes a task."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    # Simulate agent execution
    state.current_agent = "TradingAgent"
    state.status = "executing"

    assert state.current_agent == "TradingAgent"
    assert state.status == "executing"


def test_state_add_result():
    """Test adding result from an agent execution."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    result = {
        "analysis": "Market is healthy",
        "signals": ["BUY", "HOLD"],
        "timestamp": "2026-03-15T12:00:00Z"
    }

    state.results["TradingAgent"] = result

    assert "TradingAgent" in state.results
    assert state.results["TradingAgent"] == result


def test_state_add_message():
    """Test adding a message to state for audit trail."""
    state = create_initial_state(
        workflow_type="trading_health",
        agents=["TradingAgent"],
        input={"query": "Check health"}
    )

    state.messages.append({
        "agent": "Router",
        "message": "Routing to TradingAgent"
    })

    assert len(state.messages) == 1
    assert state.messages[0]["agent"] == "Router"


def test_state_with_agent_groups():
    """Test that state supports agent groups."""
    state = create_initial_state_with_groups(
        workflow_type="market_analysis",
        agent_groups=[
            ["TradingAgent", "ResearchAgent"],  # Group 1: run in parallel
            ["KnowledgeAgent"]  # Group 2: run sequentially after Group 1
        ],
        input={"query": "Analyze EUR/USD"}
    )

    assert state.agent_groups == [
        ["TradingAgent", "ResearchAgent"],
        ["KnowledgeAgent"]
    ]
    assert state.agents == ["TradingAgent", "ResearchAgent", "KnowledgeAgent"]  # Flat list for backward compat
    assert state.current_group_index == 0
    assert state.agents_executing == []  # Track which agents are currently running
