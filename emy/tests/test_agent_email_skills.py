"""Unit tests for agent email skills - TDD approach."""

import pytest
from unittest.mock import AsyncMock, patch
from emy.agents.research_agent import ResearchAgent
from emy.agents.project_monitor_agent import ProjectMonitorAgent
from emy.agents.knowledge_agent import KnowledgeAgent


@pytest.mark.asyncio
async def test_research_agent_send_feasibility_assessment():
    """Test ResearchAgent can send feasibility assessment email."""
    agent = ResearchAgent()

    with patch.object(agent, 'email_client') as mock_email_client:
        mock_email_client.render_template = AsyncMock(return_value='<html>Test</html>')
        mock_email_client.send = AsyncMock(return_value=True)

        result = await agent.send_feasibility_assessment(
            opportunity={
                'contact_name': 'John Doe',
                'title': 'New Market Expansion',
                'email': 'john@example.com'
            },
            assessment='High potential market with growth opportunity',
            recommendation='Proceed with market research phase'
        )

        assert result is True
        mock_email_client.render_template.assert_called_once()
        mock_email_client.send.assert_called_once()


@pytest.mark.asyncio
async def test_project_monitor_send_daily_digest():
    """Test ProjectMonitorAgent can send daily status digest."""
    agent = ProjectMonitorAgent()

    with patch.object(agent, 'email_client') as mock_email_client:
        mock_email_client.render_template = AsyncMock(return_value='<html>Test</html>')
        mock_email_client.send = AsyncMock(return_value=True)

        result = await agent.send_daily_status_digest(
            recipient_email='stakeholder@example.com',
            recipient_name='Jane Smith',
            projects=[
                {'name': 'Project A', 'status': 'On Track', 'progress': 75}
            ]
        )

        assert result is True
        mock_email_client.send.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_agent_send_research_summary():
    """Test KnowledgeAgent can send research summary."""
    agent = KnowledgeAgent()

    with patch.object(agent, 'email_client') as mock_email_client:
        mock_email_client.render_template = AsyncMock(return_value='<html>Test</html>')
        mock_email_client.send = AsyncMock(return_value=True)

        result = await agent.send_research_summary(
            recipient_email='researcher@example.com',
            topic='AI in Healthcare',
            findings='AI is transforming healthcare delivery',
            insights=['Insight 1', 'Insight 2']
        )

        assert result is True
        mock_email_client.send.assert_called_once()
