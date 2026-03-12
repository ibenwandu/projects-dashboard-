"""Test Claude API integration in base agent."""

import os
import pytest
from unittest.mock import MagicMock, patch
from emy.agents.base_agent import EMySubAgent


class ConcreteAgent(EMySubAgent):
    """Concrete implementation for testing."""
    def run(self):
        return (True, {"result": "test"})


@pytest.fixture
def agent():
    """Provide test agent instance."""
    return ConcreteAgent("TestAgent", "claude-opus-4-6")


def test_call_claude_with_valid_prompt(agent):
    """Test that _call_claude successfully calls Claude API."""
    prompt = "What is 2 + 2?"

    with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
        # Mock the API response
        mock_response = MagicMock()
        mock_response.content[0].text = "2 + 2 equals 4"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # Call the method (will fail until implemented)
        response = agent._call_claude(prompt)

        # Assertions
        assert response == "2 + 2 equals 4"
        mock_client.messages.create.assert_called_once()


def test_call_claude_handles_api_error(agent):
    """Test that _call_claude handles API errors gracefully."""
    prompt = "Test prompt"

    with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client

        # Should raise exception (to be caught by caller)
        with pytest.raises(Exception):
            agent._call_claude(prompt)


def test_call_claude_uses_model_from_init(agent):
    """Test that _call_claude uses the model specified in __init__."""
    prompt = "Test"

    with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
        mock_response = MagicMock()
        mock_response.content[0].text = "Response"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        agent._call_claude(prompt)

        # Verify model parameter was passed
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['model'] == 'claude-opus-4-6'


def test_call_claude_handles_malformed_response(agent):
    """Test that _call_claude handles malformed API responses."""
    with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
        # Test 1: Empty content
        mock_response = MagicMock()
        mock_response.content = []

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with pytest.raises(ValueError):
            agent._call_claude("test")

        # Test 2: Missing text attribute
        mock_response.content = [MagicMock(spec=[])]  # No text attribute
        with pytest.raises(ValueError):
            agent._call_claude("test")
