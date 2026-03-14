"""
Tests for ResearchAgent - TDD approach.

Tests written FIRST, before implementation.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from emy.agents.base_agent import EMySubAgent
from emy.agents.research_agent import ResearchAgent
from emy.agents.agent_executor import AgentExecutor, AGENT_MAP


class TestResearchAgentPattern:
    """Test ResearchAgent conforms to EMySubAgent pattern."""

    def test_inherits_from_base_agent(self):
        """ResearchAgent must extend EMySubAgent."""
        assert issubclass(ResearchAgent, EMySubAgent)

    @pytest.fixture
    def agent(self):
        """Create a ResearchAgent instance for testing."""
        return ResearchAgent()

    def test_run_returns_tuple(self, agent):
        """run() must return a tuple."""
        with patch.object(agent, '_call_claude', return_value="Analysis"):
            result = agent.run()
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_run_success_returns_true(self, agent):
        """run() must return (True, {...}) on success."""
        with patch.object(agent, '_call_claude', return_value="Analysis"):
            success, _ = agent.run()
            assert success is True

    def test_run_result_has_required_keys(self, agent):
        """Result dict must contain response, timestamp, agent keys."""
        with patch.object(agent, '_call_claude', return_value="Analysis"):
            success, result = agent.run()
            assert success is True
            assert 'response' in result
            assert 'timestamp' in result
            assert 'agent' in result

    def test_run_agent_name_correct(self, agent):
        """Result must have agent='ResearchAgent'."""
        with patch.object(agent, '_call_claude', return_value="Analysis"):
            _, result = agent.run()
            assert result['agent'] == 'ResearchAgent'

    def test_run_response_contains_claude_output(self, agent):
        """Result response must contain Claude output."""
        expected_response = "Test analysis from Claude"
        with patch.object(agent, '_call_claude', return_value=expected_response):
            _, result = agent.run()
            assert result['response'] == expected_response

    def test_run_handles_claude_error_gracefully(self, agent):
        """run() must catch exceptions and return (False, {error: ...})."""
        with patch.object(agent, '_call_claude', side_effect=Exception("API Error")):
            success, result = agent.run()
            assert success is False
            assert 'error' in result
            assert 'API Error' in result['error']

    def test_run_timestamp_is_iso_format(self, agent):
        """Timestamp must be ISO format."""
        with patch.object(agent, '_call_claude', return_value="Analysis"):
            _, result = agent.run()
            # ISO format check: must be parseable
            from datetime import datetime
            datetime.fromisoformat(result['timestamp'])


class TestResearchAgentRegistration:
    """Test ResearchAgent is properly registered."""

    def test_registered_in_agent_map(self):
        """ResearchAgent must be registered under research_query and research_evaluation."""
        assert 'research_query' in AGENT_MAP
        assert 'research_evaluation' in AGENT_MAP
        assert AGENT_MAP['research_query'] is ResearchAgent
        assert AGENT_MAP['research_evaluation'] is ResearchAgent


class TestResearchAgentExecution:
    """Test ResearchAgent executes via AgentExecutor."""

    def test_executor_runs_research_query(self):
        """AgentExecutor must run research_query workflow."""
        with patch('emy.agents.research_agent.ResearchAgent._call_claude', return_value="Analysis"):
            success, output = AgentExecutor.execute('research_query', ['ResearchAgent'], {})
            assert success is True
            assert output is not None
            result = json.loads(output)
            assert 'response' in result

    def test_executor_runs_research_evaluation(self):
        """AgentExecutor must run research_evaluation workflow."""
        with patch('emy.agents.research_agent.ResearchAgent._call_claude', return_value="Analysis"):
            success, output = AgentExecutor.execute('research_evaluation', ['ResearchAgent'], {})
            assert success is True
            assert output is not None
            result = json.loads(output)
            assert 'response' in result
