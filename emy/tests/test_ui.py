"""
Test suite for Gradio Chat Interface.

Tests all UI components with proper mocking of API requests:
- CommandParser: Parse natural language commands to workflows
- ChatMessage: Message model for chat history
- ChatInterface: Main Gradio chat interface
- APIClient: HTTP client for gateway communication
"""

import pytest
import json
import requests
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Test command parser
class TestCommandParser:
    """Test command parsing logic."""

    def test_parse_research_command(self):
        """Test parsing 'Research X' command."""
        from emy.ui.chat import CommandParser

        parser = CommandParser()
        result = parser.parse("Research AI trends for 2 hours")

        assert result is not None
        assert result["workflow_type"] == "research"
        assert result["topic"] == "ai trends"  # Parsed as lowercase
        assert result["duration_minutes"] == 120
        assert "research" in result["agents"]

    def test_parse_analysis_command(self):
        """Test parsing 'Analyze X' command."""
        from emy.ui.chat import CommandParser

        parser = CommandParser()
        result = parser.parse("Analyze market data for 30 minutes")

        assert result is not None
        assert result["workflow_type"] == "analysis"
        assert result["topic"] == "market data"
        assert result["duration_minutes"] == 30
        assert "analysis" in result["agents"]

    def test_parse_generate_command(self):
        """Test parsing 'Generate X' command."""
        from emy.ui.chat import CommandParser

        parser = CommandParser()
        result = parser.parse("Generate report for 1 hour")

        assert result is not None
        assert result["workflow_type"] == "generation"
        assert result["topic"] == "report"
        assert result["duration_minutes"] == 60
        assert "generation" in result["agents"]

    def test_parse_invalid_command(self):
        """Test parsing invalid command returns error."""
        from emy.ui.chat import CommandParser

        parser = CommandParser()
        result = parser.parse("Tell me something random")

        assert result is None or "error" in result

    def test_parse_missing_duration_defaults_to_30_minutes(self):
        """Test parsing command without duration defaults to 30 minutes."""
        from emy.ui.chat import CommandParser

        parser = CommandParser()
        result = parser.parse("Research AI trends")

        assert result is not None
        assert result["duration_minutes"] == 30

    def test_parse_various_duration_formats(self):
        """Test parsing various time format specifications."""
        from emy.ui.chat import CommandParser

        parser = CommandParser()

        # Test "for 2 hours"
        result = parser.parse("Research X for 2 hours")
        assert result["duration_minutes"] == 120

        # Test "for 30 minutes"
        result = parser.parse("Analyze Y for 30 minutes")
        assert result["duration_minutes"] == 30

        # Test "for 1 hour"
        result = parser.parse("Generate Z for 1 hour")
        assert result["duration_minutes"] == 60


class TestChatMessage:
    """Test chat message model."""

    def test_create_user_message(self):
        """Test creating a user message."""
        from emy.ui.chat import ChatMessage

        msg = ChatMessage(role="user", content="Research AI trends for 2 hours")

        assert msg.role == "user"
        assert msg.content == "Research AI trends for 2 hours"
        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, str)

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        from emy.ui.chat import ChatMessage

        msg = ChatMessage(
            role="assistant",
            content="Starting workflow...",
            workflow_id="wf_abc123"
        )

        assert msg.role == "assistant"
        assert msg.content == "Starting workflow..."
        assert msg.workflow_id == "wf_abc123"

    def test_message_to_dict(self):
        """Test converting message to dict."""
        from emy.ui.chat import ChatMessage

        msg = ChatMessage(role="user", content="Test message")
        msg_dict = msg.to_dict()

        assert msg_dict["role"] == "user"
        assert msg_dict["content"] == "Test message"
        assert "timestamp" in msg_dict


class TestAPIClient:
    """Test API client for gateway communication."""

    @patch('emy.ui.chat.requests.post')
    def test_execute_workflow_success(self, mock_post):
        """Test successful workflow execution."""
        from emy.ui.chat import APIClient

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "workflow_id": "wf_abc123",
            "status": "running",
            "created_at": "2026-03-12T00:00:00Z"
        }
        mock_post.return_value = mock_response

        client = APIClient(base_url="http://localhost:8000")
        result = client.execute_workflow(
            workflow_type="research",
            agents=["research"],
            input={"topic": "AI trends"}
        )

        assert result["workflow_id"] == "wf_abc123"
        assert result["status"] == "running"
        mock_post.assert_called_once()

    @patch('emy.ui.chat.requests.post')
    def test_execute_workflow_failure(self, mock_post):
        """Test workflow execution failure."""
        from emy.ui.chat import APIClient

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        client = APIClient(base_url="http://localhost:8000")
        result = client.execute_workflow(
            workflow_type="research",
            agents=["research"],
            input={"topic": "AI trends"}
        )

        assert result is None or "error" in result

    @patch('emy.ui.chat.requests.get')
    def test_get_workflow_status(self, mock_get):
        """Test getting workflow status."""
        from emy.ui.chat import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "wf_abc123",
            "status": "running",
            "output": None
        }
        mock_get.return_value = mock_response

        client = APIClient(base_url="http://localhost:8000")
        result = client.get_workflow_status("wf_abc123")

        assert result["id"] == "wf_abc123"
        assert result["status"] == "running"
        mock_get.assert_called_once()

    @patch('emy.ui.chat.requests.get')
    def test_health_check_success(self, mock_get):
        """Test health check."""
        from emy.ui.chat import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "database": "connected"
        }
        mock_get.return_value = mock_response

        client = APIClient(base_url="http://localhost:8000")
        result = client.health_check()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"

    @patch('emy.ui.chat.requests.get')
    def test_health_check_failure(self, mock_get):
        """Test health check when server is down."""
        from emy.ui.chat import APIClient

        mock_get.side_effect = requests.RequestException("Connection refused")

        client = APIClient(base_url="http://localhost:8000")
        result = client.health_check()

        assert result is None or "error" in result


class TestChatInterface:
    """Test Gradio chat interface integration."""

    @patch('emy.ui.chat.APIClient')
    def test_process_user_message(self, mock_api_client_class):
        """Test processing a user message."""
        from emy.ui.chat import ChatInterface

        # Mock API client
        mock_client = Mock()
        mock_client.execute_workflow.return_value = {
            "workflow_id": "wf_abc123",
            "status": "running"
        }
        mock_api_client_class.return_value = mock_client

        # Create interface
        interface = ChatInterface(api_base_url="http://localhost:8000")

        # Process message
        response = interface.process_message("Research AI trends for 2 hours")

        assert response is not None
        assert "workflow_id" in response or "error" in response

    @patch('emy.ui.chat.APIClient')
    def test_process_invalid_message(self, mock_api_client_class):
        """Test processing invalid message."""
        from emy.ui.chat import ChatInterface

        mock_client = Mock()
        mock_api_client_class.return_value = mock_client

        interface = ChatInterface(api_base_url="http://localhost:8000")
        response = interface.process_message("Random invalid text")

        # Should contain error or guidance
        assert response is not None
        assert isinstance(response, (str, dict))

    @patch('emy.ui.chat.APIClient')
    def test_get_workflow_suggestions(self, mock_api_client_class):
        """Test getting workflow command suggestions."""
        from emy.ui.chat import ChatInterface

        mock_client = Mock()
        mock_api_client_class.return_value = mock_client

        interface = ChatInterface(api_base_url="http://localhost:8000")
        suggestions = interface.get_command_suggestions()

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should include the three workflow types
        assert any("Research" in s for s in suggestions)
        assert any("Analyze" in s for s in suggestions)
        assert any("Generate" in s for s in suggestions)

    @patch('emy.ui.chat.APIClient')
    def test_chat_history_management(self, mock_api_client_class):
        """Test in-memory chat history management."""
        from emy.ui.chat import ChatInterface

        mock_client = Mock()
        mock_api_client_class.return_value = mock_client

        interface = ChatInterface(api_base_url="http://localhost:8000")

        # Check initial history is empty
        history = interface.get_chat_history()
        assert isinstance(history, list)

        # Add a message manually
        from emy.ui.chat import ChatMessage
        msg = ChatMessage(role="user", content="Test message")
        interface.add_message(msg)

        # Check history has the message
        history = interface.get_chat_history()
        assert len(history) > 0

    @patch('emy.ui.chat.APIClient')
    def test_get_system_status(self, mock_api_client_class):
        """Test getting system status."""
        from emy.ui.chat import ChatInterface

        mock_client = Mock()
        mock_client.health_check.return_value = {
            "status": "healthy",
            "database": "connected"
        }
        mock_api_client_class.return_value = mock_client

        interface = ChatInterface(api_base_url="http://localhost:8000")
        status = interface.get_system_status()

        assert status is not None
        # Check for expected fields in status response
        assert "api_status" in status or "error" in status


class TestEndToEnd:
    """End-to-end integration tests."""

    @patch('emy.ui.chat.APIClient')
    def test_full_workflow_execution(self, mock_api_client_class):
        """Test complete workflow from message to execution."""
        from emy.ui.chat import ChatInterface, ChatMessage

        # Setup mock
        mock_client = Mock()
        mock_client.execute_workflow.return_value = {
            "workflow_id": "wf_test123",
            "status": "running",
            "created_at": "2026-03-12T00:00:00Z"
        }
        mock_client.get_workflow_status.return_value = {
            "id": "wf_test123",
            "status": "completed",
            "output": {"results": "Analysis complete"}
        }
        mock_api_client_class.return_value = mock_client

        # Create interface
        interface = ChatInterface(api_base_url="http://localhost:8000")

        # User sends message
        user_message = "Research AI trends for 1 hour"
        response = interface.process_message(user_message)

        # Should return workflow info
        assert response is not None

        # Check history contains messages
        history = interface.get_chat_history()
        assert isinstance(history, list)

    @patch('emy.ui.chat.APIClient')
    def test_multiple_commands_in_sequence(self, mock_api_client_class):
        """Test handling multiple commands."""
        from emy.ui.chat import ChatInterface

        mock_client = Mock()
        mock_client.execute_workflow.return_value = {
            "workflow_id": "wf_test123",
            "status": "running"
        }
        mock_api_client_class.return_value = mock_client

        interface = ChatInterface(api_base_url="http://localhost:8000")

        # Send multiple commands
        commands = [
            "Research AI trends for 1 hour",
            "Analyze market data for 30 minutes",
            "Generate report for 45 minutes"
        ]

        for cmd in commands:
            response = interface.process_message(cmd)
            assert response is not None
