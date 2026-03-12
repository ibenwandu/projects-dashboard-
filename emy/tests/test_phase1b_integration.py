"""Phase 1b integration tests: Claude API with all agents."""

import pytest
from unittest.mock import patch, MagicMock
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.trading_agent import TradingAgent
from emy.agents.job_search_agent import JobSearchAgent


class TestPhase1bIntegration:
    """Integration tests for Phase 1b Claude API integration."""

    @pytest.fixture
    def agents(self):
        """Provide all agents."""
        return {
            "knowledge": KnowledgeAgent(),
            "trading": TradingAgent(),
            "job_search": JobSearchAgent()
        }

    def test_all_agents_have_call_claude_method(self, agents):
        """Test that all agents inherit Claude API method."""
        for agent_name, agent in agents.items():
            assert hasattr(agent, '_call_claude'), f"{agent_name} missing _call_claude"
            assert callable(agent._call_claude), f"{agent_name}._call_claude not callable"

    def test_knowledge_agent_run_returns_valid_structure(self, agents):
        """Test KnowledgeAgent.run() returns valid structure."""
        with patch.object(agents["knowledge"], '_call_claude',
                         return_value="Test response from Claude"):
            success, result = agents["knowledge"].run()

            assert isinstance(success, bool)
            # Result can be string (JSON) or dict depending on agent implementation
            assert isinstance(result, (dict, str))

    def test_trading_agent_run_returns_valid_structure(self, agents):
        """Test TradingAgent.run() returns valid structure."""
        with patch.object(agents["trading"], '_call_claude',
                         return_value="Market analysis response"):
            success, result = agents["trading"].run()

            assert isinstance(success, bool)
            assert isinstance(result, (dict, str))

    def test_job_search_agent_run_returns_valid_structure(self, agents):
        """Test JobSearchAgent.run() returns valid structure."""
        with patch.object(agents["job_search"], '_call_claude',
                         return_value="Job evaluation response"):
            success, result = agents["job_search"].run()

            assert isinstance(success, bool)
            # JobSearchAgent returns JSON string, not dict
            assert isinstance(result, (dict, str))

    def test_agents_handle_claude_errors_gracefully(self, agents):
        """Test that agents handle Claude API errors gracefully."""

        for agent_name, agent in agents.items():
            with patch.object(agent, '_call_claude',
                            side_effect=Exception("API Error")):
                success, result = agent.run()

                # Should return (False, ...) on error
                assert success == False, f"{agent_name} should return False on error"

    def test_all_agents_return_dict_or_string_results(self, agents):
        """Test that all agents return consistent result types."""

        mock_response = "Claude response"

        for agent_name, agent in agents.items():
            with patch.object(agent, '_call_claude', return_value=mock_response):
                success, result = agent.run()

                # All agents should return either dict or string (JSON)
                assert isinstance(result, (dict, str)), f"{agent_name} result should be dict or string"

    def test_phase1b_workflow_execution(self):
        """Test complete Phase 1b workflow: request -> agent -> Claude -> response."""

        # Simulate workflow: request comes in, agent processes with Claude
        agent = KnowledgeAgent()
        mock_claude_response = "Knowledge synthesis response"

        with patch.object(agent, '_call_claude', return_value=mock_claude_response):
            success, result = agent.run()

            # Verify complete flow
            assert success == True
            assert isinstance(result, dict)
            assert mock_claude_response in str(result) or 'response' in result


class TestPhase1bEdgeCases:
    """Test edge cases and error conditions."""

    def test_claude_timeout_handling(self):
        """Test graceful handling of Claude API timeout."""
        agent = KnowledgeAgent()

        with patch.object(agent, '_call_claude',
                         side_effect=TimeoutError("API timeout")):
            success, result = agent.run()
            assert success == False

    def test_claude_rate_limit_handling(self):
        """Test graceful handling of rate limit errors."""
        agent = TradingAgent()

        with patch.object(agent, '_call_claude',
                         side_effect=Exception("Rate limit exceeded")):
            success, result = agent.run()
            assert success == False

    def test_empty_claude_response(self):
        """Test handling of empty Claude responses."""
        agent = JobSearchAgent()

        with patch.object(agent, '_call_claude', return_value=""):
            success, result = agent.run()
            # Should still return result (can be dict or string)
            assert isinstance(result, (dict, str))

    def test_malformed_claude_response(self):
        """Test handling of malformed responses."""
        agent = KnowledgeAgent()

        with patch.object(agent, '_call_claude', return_value=None):
            success, result = agent.run()
            # Should handle None gracefully
            assert isinstance(result, dict)


class TestPhase1bDatabaseIntegration:
    """Test Phase 1b with database persistence."""

    def test_database_initialization(self):
        """Test that database can be initialized properly."""
        from emy.core.database import EMyDatabase

        # Verify EMyDatabase can be instantiated
        db = EMyDatabase(':memory:')
        assert db is not None

        # Verify it has required methods for workflow persistence
        assert hasattr(db, 'get_connection'), "Database should have get_connection method"
        assert hasattr(db, 'initialize_schema'), "Database should have initialize_schema method"
        assert hasattr(db, 'log_agent_run'), "Database should have log_agent_run method"

    def test_database_connection_available(self):
        """Test that database connection is available for agent logging."""
        from emy.core.database import EMyDatabase

        db = EMyDatabase(':memory:')

        # Verify connection context manager works
        with db.get_connection() as conn:
            assert conn is not None
            cursor = conn.cursor()
            assert cursor is not None
