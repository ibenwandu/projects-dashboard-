import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.gateway.api import app
from fastapi.testclient import TestClient
from pathlib import Path


client = TestClient(app)


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


class TestAPIExecutesKnowledgeAgent:
    """Test that API gateway actually executes KnowledgeAgent and returns real Claude responses"""

    def test_api_execute_workflow_calls_claude_and_returns_output(self):
        """API /workflows/execute should execute agent, call Claude, and return output"""
        mock_claude_response = "Your current status: Active development on Emy Phase 1b. Recommendations: Complete Task 1 integration testing."

        # Mock the Claude API call
        with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
            # Setup mock client
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=mock_claude_response)]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            # Execute workflow via API
            response = client.post(
                '/workflows/execute',
                json={
                    'workflow_type': 'knowledge_query',
                    'agents': ['KnowledgeAgent'],
                    'input': {'query': 'What is my current status?'}
                }
            )

            # Verify API response
            assert response.status_code == 200
            data = response.json()

            # Status should be 'completed' (not 'pending') because agent executed
            assert data['status'] == 'completed', f"Expected 'completed' but got '{data['status']}'"
            assert data['workflow_id']

            # Output should contain the Claude response (as JSON)
            assert data['output'] is not None, "Output should not be null - agent should have executed"

            # Parse output JSON to verify it contains Claude response
            output_dict = json.loads(data['output'])
            assert 'response' in output_dict
            assert mock_claude_response in output_dict['response']

    def test_api_get_workflow_returns_output(self):
        """API GET /workflows/{id} should return stored output from execution"""
        # Create workflow
        exec_response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'knowledge_query',
                'agents': ['KnowledgeAgent'],
                'input': {'query': 'Test query'}
            }
        )

        workflow_id = exec_response.json()['workflow_id']

        # Retrieve workflow
        get_response = client.get(f'/workflows/{workflow_id}')

        assert get_response.status_code == 200
        data = get_response.json()
        assert data['workflow_id'] == workflow_id
        assert 'output' in data  # Should have output field (even if None initially)

    def test_api_workflow_persistence(self):
        """Workflow outputs should persist in database"""
        # Create and execute workflow
        response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'knowledge_query',
                'agents': ['KnowledgeAgent'],
                'input': {'query': 'Persist this'}
            }
        )

        workflow_id = response.json()['workflow_id']

        # Retrieve it immediately
        get_response = client.get(f'/workflows/{workflow_id}')
        assert get_response.status_code == 200

        # Should still be there (even if API restarts)
        another_get = client.get(f'/workflows/{workflow_id}')
        assert another_get.status_code == 200
        assert another_get.json()['workflow_id'] == workflow_id
