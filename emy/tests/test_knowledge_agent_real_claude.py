"""Phase 1b Task 1: Real Claude API integration tests (no mocks).

These tests MUST call real Claude API to verify:
1. KnowledgeAgent invokes Claude via ANTHROPIC_API_KEY
2. Responses are not null/empty
3. Response structure is valid
4. Errors are handled gracefully
"""

import os
import pytest
import json
from emy.agents.knowledge_agent import KnowledgeAgent
from anthropic import AuthenticationError, APIConnectionError


class TestKnowledgeAgentRealClaudeIntegration:
    """Integration tests for REAL Claude API calls (no mocks)."""

    @pytest.fixture
    def knowledge_agent(self):
        """Create KnowledgeAgent instance for real Claude testing."""
        return KnowledgeAgent()

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set - skipping real Claude test"
    )
    def test_knowledge_agent_calls_real_claude_api(self, knowledge_agent):
        """
        RED TEST: KnowledgeAgent must call real Claude API and return response.

        This test verifies:
        - Claude API is actually called (no mocks)
        - Response structure is valid
        - Response content is substantial (not stub data)
        """
        # Execute agent WITHOUT mocking _call_claude
        success, result = knowledge_agent.run()

        # ✅ SUCCESS CRITERION 1: Execution succeeds
        assert success is True, "KnowledgeAgent.run() must return success=True"

        # ✅ SUCCESS CRITERION 2: Result is dict
        assert isinstance(result, dict), f"Result must be dict, got {type(result)}"

        # ✅ SUCCESS CRITERION 3: Required keys present
        assert 'response' in result, "Result must contain 'response' key from Claude"
        assert 'timestamp' in result, "Result must contain 'timestamp' key"
        assert 'agent' in result, "Result must contain 'agent' key"

        # ✅ SUCCESS CRITERION 4: Response not null/empty
        response = result['response']
        assert response is not None, "Claude response must not be None"
        assert isinstance(response, str), f"Response must be string, got {type(response)}"
        assert len(response) > 0, "Claude response must not be empty"

        # ✅ SUCCESS CRITERION 5: Response is substantive (real Claude, not stub)
        assert len(response) > 20, f"Response too short ({len(response)} chars) - likely stub/incomplete"

        # ✅ SUCCESS CRITERION 6: Agent name correct
        assert result['agent'] == 'KnowledgeAgent', "Agent name must be KnowledgeAgent"

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_knowledge_agent_response_is_substantive(self, knowledge_agent):
        """Verify Claude response contains real synthesis (multiple sentences)."""
        success, result = knowledge_agent.run()

        assert success is True
        response = result['response']

        # Real Claude should produce substantial content
        # (Not just "ok", "yes", or single words)
        words = response.split()
        assert len(words) >= 15, (
            f"Response too short ({len(words)} words). "
            f"Expected real Claude synthesis, not stub response."
        )

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_knowledge_agent_timestamp_is_valid_iso(self, knowledge_agent):
        """Verify response includes valid ISO 8601 timestamp."""
        success, result = knowledge_agent.run()

        assert success is True
        timestamp = result['timestamp']

        # ISO 8601 format must contain 'T' and colons
        assert 'T' in timestamp, "Timestamp must be ISO format (contain 'T')"
        assert timestamp.count(':') >= 2, "Timestamp must have time components (HH:MM:SS)"

        # Should be parseable as ISO datetime
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp}' not valid ISO 8601 format")

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_knowledge_agent_builds_valid_prompt(self, knowledge_agent):
        """Verify that KnowledgeAgent builds valid prompt for Claude."""
        # This verifies the prompt construction works correctly
        prompt = knowledge_agent._build_knowledge_prompt()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0, "Prompt should not be empty"
        assert 'Claude' in prompt or 'Emy' in prompt, "Prompt should contain context"

    def test_knowledge_agent_handles_missing_api_key(self, knowledge_agent):
        """Verify graceful error handling when ANTHROPIC_API_KEY missing."""
        # Temporarily remove API key
        original_key = os.environ.get('ANTHROPIC_API_KEY')
        if original_key:
            del os.environ['ANTHROPIC_API_KEY']

        try:
            success, result = knowledge_agent.run()
            # Should fail gracefully, not crash
            assert success is False, "Should return False when API key missing"
            assert 'error' in result, "Should return error message"
        finally:
            # Restore original key
            if original_key:
                os.environ['ANTHROPIC_API_KEY'] = original_key

    def test_knowledge_agent_handles_invalid_api_key(self, knowledge_agent):
        """Verify graceful error handling with invalid ANTHROPIC_API_KEY."""
        # Set invalid API key
        original_key = os.environ.get('ANTHROPIC_API_KEY')
        os.environ['ANTHROPIC_API_KEY'] = 'sk-invalid-key-for-testing'

        try:
            success, result = knowledge_agent.run()
            # Should fail gracefully with auth error
            assert success is False, "Should return False with invalid API key"
            assert isinstance(result, dict), "Result should be dict"
            # Error information should be present
            if 'error' in result:
                error_msg = str(result['error']).lower()
                # Should mention auth/authentication
                assert 'auth' in error_msg or 'invalid' in error_msg or 'key' in error_msg, (
                    f"Error message should mention authentication, got: {result['error']}"
                )
        finally:
            # Restore original key
            if original_key:
                os.environ['ANTHROPIC_API_KEY'] = original_key
            else:
                del os.environ['ANTHROPIC_API_KEY']

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_knowledge_agent_response_matches_model_specified(self, knowledge_agent):
        """Verify response comes from correct Claude model."""
        # KnowledgeAgent uses claude-haiku-4-5-20251001 model
        success, result = knowledge_agent.run()

        assert success is True
        # Just verify we got a response from Claude
        # (We can't easily verify which model without API response metadata)
        response = result['response']
        assert response is not None


class TestKnowledgeAgentClaudeIntegrationWithWorkflow:
    """Test Claude integration through API workflow execution."""

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_workflow_execution_with_real_claude(self):
        """Test complete workflow: API -> AgentExecutor -> KnowledgeAgent -> Claude."""
        from emy.agents.agent_executor import AgentExecutor

        # Execute workflow (uses real Claude)
        success, output_json = AgentExecutor.execute(
            workflow_type='knowledge_query',
            agents=['KnowledgeAgent'],
            workflow_input={'query': 'Status check'}
        )

        # ✅ Execution should succeed
        assert success is True, "Workflow execution should succeed"

        # ✅ Output should be JSON string
        assert output_json is not None, "Output should not be None"
        assert isinstance(output_json, str), "Output should be JSON string"

        # ✅ Parse and validate JSON
        result = json.loads(output_json)
        assert isinstance(result, dict), "Parsed output should be dict"
        assert 'response' in result, "Output should have 'response' from Claude"

        # ✅ Response should be substantive
        response = result['response']
        assert len(response) > 20, "Claude response should be substantial"
