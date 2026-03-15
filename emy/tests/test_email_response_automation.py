import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from emy.tasks.email_response_task import process_and_respond_to_email
from emy.agents.research_agent import ResearchAgent

@pytest.mark.asyncio
async def test_agent_generates_response_to_feedback_email():
    """Test that ResearchAgent generates response to feedback email"""
    email = {
        'id': 'msg123',
        'sender': 'user@example.com',
        'subject': 'Feedback on feasibility assessment',
        'body': 'Great assessment! Can you evaluate another project?',
        'intent': 'feedback'
    }

    with patch('emy.tasks.email_response_task.EmailClient') as mock_client:
        mock_client_instance = AsyncMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.send.return_value = True

        with patch('emy.tasks.email_response_task.ResearchAgent') as mock_agent:
            mock_agent_instance = AsyncMock()
            mock_agent.return_value = mock_agent_instance
            mock_agent_instance.generate_email_response.return_value = {
                'to': 'user@example.com',
                'subject': 'Re: Feedback on feasibility assessment',
                'body': 'Thank you for the feedback! I am ready to evaluate your next project.'
            }

            result = await process_and_respond_to_email(email)

            assert result['status'] == 'response_sent'
            assert 'user@example.com' in result['recipient']

@pytest.mark.asyncio
async def test_response_email_sent_via_email_client():
    """Test that response is sent via EmailClient"""
    email = {
        'id': 'msg456',
        'sender': 'analyst@example.com',
        'subject': 'Research request',
        'body': 'Can you analyze this market trend?',
        'intent': 'research'
    }

    with patch('emy.tasks.email_response_task.EmailClient') as mock_client:
        mock_client_instance = AsyncMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.send.return_value = True

        with patch('emy.agents.knowledge_agent.KnowledgeAgent') as mock_agent:
            mock_agent_instance = AsyncMock()
            mock_agent.return_value = mock_agent_instance
            mock_agent_instance.generate_email_response.return_value = {
                'to': 'analyst@example.com',
                'subject': 'Re: Research request',
                'body': 'Here is my analysis...'
            }

            result = await process_and_respond_to_email(email)

            mock_client_instance.send.assert_called_once()
            assert result['status'] == 'response_sent'

@pytest.mark.asyncio
async def test_no_response_for_unclassified_email():
    """Test that unclassified emails are logged but not responded to"""
    email = {
        'id': 'msg789',
        'sender': 'unknown@example.com',
        'subject': 'Random subject',
        'body': 'Some random content',
        'intent': 'other'
    }

    result = await process_and_respond_to_email(email)

    assert result['status'] == 'no_response'
    assert result['reason'] == 'unclassified_intent'
