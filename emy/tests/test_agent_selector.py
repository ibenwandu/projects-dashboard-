"""Test suite for intelligent agent selection logic."""

import pytest
from emy.brain.agent_selector import AgentSelector


def test_auto_select_agents_for_market_analysis():
    """Test auto-selecting agents for market analysis task."""
    selector = AgentSelector()

    task = {
        'type': 'market_analysis',
        'input': 'Analyze EUR/USD trend'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'TradingAgent' in agents
    # Market analysis is trading-focused
    assert len(agents) >= 1


def test_auto_select_agents_for_research():
    """Test auto-selecting agents for research task."""
    selector = AgentSelector()

    task = {
        'type': 'research',
        'input': 'Evaluate feasibility of new project'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'ResearchAgent' in agents
    assert len(agents) >= 1


def test_auto_select_agents_for_knowledge_query():
    """Test auto-selecting agents for knowledge query."""
    selector = AgentSelector()

    task = {
        'type': 'knowledge_query',
        'input': 'What is my project status?'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'KnowledgeAgent' in agents


def test_explicit_agent_selection():
    """Test explicit agent selection."""
    selector = AgentSelector()

    agents = selector.select_agents(
        {},
        mode='explicit',
        agents=['TradingAgent', 'ResearchAgent']
    )

    assert agents == ['TradingAgent', 'ResearchAgent']


def test_select_agents_by_capability():
    """Test selecting agents by required capability."""
    selector = AgentSelector()

    task = {
        'required_capabilities': ['market_analysis', 'sentiment']
    }

    agents = selector.select_agents(task, mode='auto')

    # TradingAgent has market_analysis, should be selected
    assert 'TradingAgent' in agents


def test_validate_agent_exists():
    """Test validation of agent existence."""
    selector = AgentSelector()

    # Valid agent
    assert selector.is_valid_agent('TradingAgent') is True

    # Invalid agent
    assert selector.is_valid_agent('NonExistentAgent') is False


def test_get_agent_capabilities():
    """Test getting agent capabilities."""
    selector = AgentSelector()

    caps = selector.get_agent_capabilities('TradingAgent')

    assert isinstance(caps, list)
    assert len(caps) > 0
    assert 'market_analysis' in caps


def test_combine_agents_for_complex_task():
    """Test combining multiple agents for complex task."""
    selector = AgentSelector()

    task = {
        'type': 'complex',
        'input': 'Analyze market AND evaluate opportunity'
    }

    agents = selector.select_agents(task, mode='auto')

    # Should select both TradingAgent and ResearchAgent
    assert len(agents) >= 2
