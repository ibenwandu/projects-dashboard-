"""Tests for RouterAgent Claude classification.

Test Coverage:
1. RouterAgent instantiation
2. Classify job_search correctly
3. Classify trading correctly
4. Classify unknown (not error)
5. Handle Claude API failures gracefully
6. Set current_agent from DOMAIN_MAP
7. Brain.execute_workflow includes workflow_type in result
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from anthropic import APIError, AuthenticationError, APIConnectionError
from emy.brain.router_agent import RouterAgent, DOMAIN_MAP
from emy.brain.engine import EMyBrain


class TestRouterAgent:
    """Tests for RouterAgent."""

    def test_instantiation_default_model(self):
        """Test RouterAgent instantiates with default model."""
        router = RouterAgent()
        assert router.model == "claude-haiku-4-5-20251001"

    def test_instantiation_custom_model(self):
        """Test RouterAgent accepts custom model parameter."""
        router = RouterAgent(model="claude-sonnet-4-6")
        assert router.model == "claude-sonnet-4-6"

    @patch("emy.brain.router_agent.Anthropic")
    def test_classify_job_search(self, mock_anthropic_class):
        """Test RouterAgent correctly classifies job_search request."""
        # Mock Claude response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='{"workflow_type": "job_search", "confidence": 0.95, "rationale": "Job search"}')]
        mock_client.messages.create.return_value = mock_message

        router = RouterAgent()
        state = {"user_request": {"query": "find jobs in Toronto"}, "step_count": 0}
        result = router.route(state)

        assert result["workflow_type"] == "job_search"
        assert result["current_agent"] == "JobSearchAgent"
        assert result["step_count"] == 1

    @patch("emy.brain.router_agent.Anthropic")
    def test_classify_trading(self, mock_anthropic_class):
        """Test RouterAgent correctly classifies trading request."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='{"workflow_type": "trading", "confidence": 0.92, "rationale": "Trading query"}')]
        mock_client.messages.create.return_value = mock_message

        router = RouterAgent()
        state = {"user_request": {"query": "what is my portfolio?"}, "step_count": 2}
        result = router.route(state)

        assert result["workflow_type"] == "trading"
        assert result["current_agent"] == "TradingAgent"
        assert result["step_count"] == 3

    @patch("emy.brain.router_agent.Anthropic")
    def test_classify_knowledge_query(self, mock_anthropic_class):
        """Test RouterAgent classifies knowledge_query correctly."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='{"workflow_type": "knowledge_query", "confidence": 0.85, "rationale": "General knowledge"}')]
        mock_client.messages.create.return_value = mock_message

        router = RouterAgent()
        state = {"user_request": {"query": "what is Python?"}, "step_count": 0}
        result = router.route(state)

        assert result["workflow_type"] == "knowledge_query"
        assert result["current_agent"] == "KnowledgeAgent"

    @patch("emy.brain.router_agent.Anthropic")
    def test_classify_unknown_type(self, mock_anthropic_class):
        """Test RouterAgent classifies unknown request without error."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='{"workflow_type": "unknown", "confidence": 0.3, "rationale": "Unclear"}')]
        mock_client.messages.create.return_value = mock_message

        router = RouterAgent()
        state = {"user_request": {"query": "xyz123"}, "step_count": 1}
        result = router.route(state)

        assert result["workflow_type"] == "unknown"
        assert result["current_agent"] == "UnknownHandlerAgent"
        assert "error" not in result

    @patch("emy.brain.router_agent.Anthropic")
    def test_handle_json_decode_error(self, mock_anthropic_class):
        """Test RouterAgent handles JSON decode errors gracefully."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='invalid json {not parseable}')]
        mock_client.messages.create.return_value = mock_message

        router = RouterAgent()
        state = {"user_request": {"query": "test"}, "step_count": 0}
        result = router.route(state)

        assert result["status"] == "error"
        assert "router_json_decode_failed" in result["error"]
        assert result["workflow_type"] == "unknown"

    @patch("emy.brain.router_agent.Anthropic")
    def test_handle_api_error(self, mock_anthropic_class):
        """Test RouterAgent handles Claude API errors gracefully."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = APIError(message="Rate limited", request=Mock(), body={})

        router = RouterAgent()
        state = {"user_request": {"query": "test"}, "step_count": 0}
        result = router.route(state)

        assert result["status"] == "error"
        assert "router_api_failed" in result["error"]
        assert result["workflow_type"] == "unknown"

    @patch("emy.brain.router_agent.Anthropic")
    def test_handle_authentication_error(self, mock_anthropic_class):
        """Test RouterAgent handles authentication errors gracefully."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = AuthenticationError(
            message="Invalid key", response=Mock(), body={}
        )

        router = RouterAgent()
        state = {"user_request": {"query": "test"}, "step_count": 0}
        result = router.route(state)

        assert result["status"] == "error"
        assert "router_api_failed" in result["error"]
        assert "AuthenticationError" in result["error"]

    @patch("emy.brain.router_agent.Anthropic")
    def test_handle_connection_error(self, mock_anthropic_class):
        """Test RouterAgent handles connection errors gracefully."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = APIConnectionError(
            message="Network error", request=Mock()
        )

        router = RouterAgent()
        state = {"user_request": {"query": "test"}, "step_count": 0}
        result = router.route(state)

        assert result["status"] == "error"
        assert "router_api_failed" in result["error"]

    def test_domain_map_completeness(self):
        """Test DOMAIN_MAP has all workflow types mapped."""
        workflow_types = ["job_search", "trading", "knowledge_query", "project_monitor", "research", "unknown"]
        for wtype in workflow_types:
            assert wtype in DOMAIN_MAP
            assert isinstance(DOMAIN_MAP[wtype], str)

    @patch("emy.brain.router_agent.Anthropic")
    def test_state_step_count_missing(self, mock_anthropic_class):
        """Test RouterAgent handles missing step_count in state."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='{"workflow_type": "job_search", "confidence": 0.9, "rationale": "test"}')]
        mock_client.messages.create.return_value = mock_message

        router = RouterAgent()
        state = {"user_request": {"query": "test"}}  # No step_count
        result = router.route(state)

        assert result["step_count"] == 1  # Should default to 0 + 1


class TestBrainWithRouter:
    """Tests for Brain integration with RouterAgent."""

    @pytest.mark.asyncio
    @patch("emy.brain.router_agent.Anthropic")
    async def test_brain_execute_workflow_includes_workflow_type(self, mock_anthropic_class):
        """Test execute_workflow result includes workflow_type from router."""
        # Mock Claude to return job_search classification
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_message = Mock()
        mock_message.content = [Mock(text='{"workflow_type": "job_search", "confidence": 0.95, "rationale": "Job search"}')]
        mock_client.messages.create.return_value = mock_message

        brain = EMyBrain()
        result = await brain.execute_workflow(
            workflow_id="wf_router_test",
            request={"query": "find jobs"},
        )

        assert "workflow_type" in result
        assert result["workflow_id"] == "wf_router_test"

    @pytest.mark.asyncio
    @patch("emy.brain.router_agent.Anthropic")
    async def test_brain_routes_different_request_types(self, mock_anthropic_class):
        """Test brain handles different request types through routing."""
        # Mock Claude to return appropriate classifications
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create mocks for different classifications
        responses = [
            '{"workflow_type": "job_search", "confidence": 0.95, "rationale": "Job search"}',
            '{"workflow_type": "trading", "confidence": 0.90, "rationale": "Trading"}',
            '{"workflow_type": "knowledge_query", "confidence": 0.85, "rationale": "Knowledge"}',
        ]

        def create_response(response_text):
            mock_msg = Mock()
            mock_msg.content = [Mock(text=response_text)]
            return mock_msg

        mock_client.messages.create.side_effect = [
            create_response(responses[0]),
            create_response(responses[1]),
            create_response(responses[2]),
        ]

        brain = EMyBrain()

        # Different request types
        requests = [
            {"query": "find jobs in Toronto"},
            {"query": "what is my portfolio?"},
            {"query": "what is AI?"},
        ]

        for i, req in enumerate(requests):
            result = await brain.execute_workflow(
                workflow_id=f"wf_test_{i}",
                request=req,
            )
            assert result["status"] == "complete", f"Request {i} failed: {result.get('error')}"
            assert "workflow_id" in result
