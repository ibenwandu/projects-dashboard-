"""Pytest configuration and shared fixtures for Emy test suite."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service for testing."""
    with patch('emy.tools.email_tool.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_email_client(mock_gmail_service):
    """Fixture providing mock EmailClient."""
    from emy.tools.email_tool import EmailClient

    with patch.object(EmailClient, '_initialize_service'):
        client = EmailClient()
        client._service = mock_gmail_service
        return client


@pytest.fixture
def mock_email_parser(mock_gmail_service):
    """Fixture providing mock EmailParser."""
    from emy.tools.email_parser import EmailParser

    with patch.object(EmailParser, '_initialize_service'):
        parser = EmailParser()
        parser._service = mock_gmail_service
        return parser


@pytest.fixture
def mock_research_agent():
    """Fixture providing mock ResearchAgent."""
    from emy.agents.research_agent import ResearchAgent

    with patch.object(ResearchAgent, 'email_client'):
        agent = ResearchAgent()
        agent.email_client = MagicMock()
        return agent


@pytest.fixture
def mock_project_monitor_agent():
    """Fixture providing mock ProjectMonitorAgent."""
    from emy.agents.project_monitor_agent import ProjectMonitorAgent

    with patch.object(ProjectMonitorAgent, 'email_client'):
        agent = ProjectMonitorAgent()
        agent.email_client = MagicMock()
        return agent


@pytest.fixture
def mock_knowledge_agent():
    """Fixture providing mock KnowledgeAgent."""
    from emy.agents.knowledge_agent import KnowledgeAgent

    with patch.object(KnowledgeAgent, 'email_client'):
        agent = KnowledgeAgent()
        agent.email_client = MagicMock()
        return agent
