import pytest
from unittest.mock import Mock, patch, MagicMock
from emy.agents.knowledge_agent import KnowledgeAgent
from pathlib import Path


class TestKnowledgeAgentIntegration:
    """End-to-end integration tests for dashboard updates"""

    @pytest.fixture
    def agent(self):
        return KnowledgeAgent()

    def test_full_claude_knowledge_synthesis(self, agent):
        """Complete workflow: build prompt -> call Claude -> store response"""
        # Mock Claude response
        mock_claude_response = "Status: All systems operational\nProjects: Trading, Job Search\nRecommendations: Continue current trajectory"

        with patch.object(agent, '_call_claude', return_value=mock_claude_response):
            # Run workflow
            success, results = agent.run()

            # Verify results
            assert success is True
            assert 'response' in results
            assert results['response'] == mock_claude_response
            assert 'timestamp' in results
            assert 'agent' in results

    def test_claude_integration_handles_errors(self, agent):
        """Claude integration gracefully handles API errors"""
        with patch.object(agent, '_call_claude', side_effect=Exception("API Error")):
            # Should return failure with error message
            success, results = agent.run()

            # Graceful error handling
            assert success is False
            assert 'error' in results

    def test_build_knowledge_prompt_includes_guidelines(self, agent):
        """_build_knowledge_prompt() includes global guidelines in prompt"""
        prompt = agent._build_knowledge_prompt()

        # Verify prompt structure
        assert "You are Ibe's AI Chief of Staff" in prompt
        assert "Global Guidelines and Context:" in prompt
        assert "Current request:" in prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 100
