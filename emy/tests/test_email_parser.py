"""Unit tests for EmailParser with Gmail API integration and intent classification."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import base64
from emy.tools.email_parser import EmailParser


@pytest.mark.asyncio
async def test_check_inbox_returns_new_emails():
    """Test checking inbox retrieves new unread emails."""
    parser = EmailParser()

    with patch.object(parser, '_service') as mock_service:
        mock_service.users().messages().list = MagicMock(
            return_value=MagicMock(execute=MagicMock(
                return_value={'messages': [{'id': 'msg1'}, {'id': 'msg2'}]}
            ))
        )

        emails = await parser.check_inbox()

        assert len(emails) == 2
        assert emails[0]['id'] == 'msg1'
        assert emails[1]['id'] == 'msg2'


@pytest.mark.asyncio
async def test_parse_email_extracts_fields():
    """Test parsing email extracts sender, subject, body."""
    parser = EmailParser()

    # Base64 encode test body
    test_body = "Test body content"
    encoded_body = base64.urlsafe_b64encode(test_body.encode('utf-8')).decode('utf-8')

    with patch.object(parser, '_service') as mock_service:
        mock_service.users().messages().get = MagicMock(
            return_value=MagicMock(execute=MagicMock(
                return_value={
                    'payload': {
                        'headers': [
                            {'name': 'From', 'value': 'sender@example.com'},
                            {'name': 'Subject', 'value': 'Test Subject'}
                        ],
                        'parts': [
                            {
                                'mimeType': 'text/plain',
                                'body': {'data': encoded_body}
                            }
                        ]
                    }
                }
            ))
        )

        email = await parser.parse_email('msg1')

        assert email['sender'] == 'sender@example.com'
        assert email['subject'] == 'Test Subject'
        assert email['body'] == test_body
        assert email['email_id'] == 'msg1'


@pytest.mark.asyncio
async def test_classify_intent_identifies_email_type():
    """Test classifying email intent based on subject and body."""
    parser = EmailParser()

    # Test feedback intent
    email_feedback = {
        'sender': 'researcher@example.com',
        'subject': 'Feedback on feasibility assessment',
        'body': 'Great analysis, please consider feedback on the risks'
    }
    intent = await parser.classify_intent(email_feedback)
    assert intent == 'feedback'

    # Test research intent
    email_research = {
        'sender': 'analyst@example.com',
        'subject': 'Research request for market analysis',
        'body': 'Please investigate and analyze this market opportunity'
    }
    intent = await parser.classify_intent(email_research)
    assert intent == 'research'

    # Test status intent
    email_status = {
        'sender': 'manager@example.com',
        'subject': 'Project status update',
        'body': 'Status report on progress'
    }
    intent = await parser.classify_intent(email_status)
    assert intent == 'status'

    # Test question intent
    email_question = {
        'sender': 'user@example.com',
        'subject': 'Question about methodology',
        'body': 'What is the approach for this analysis?'
    }
    intent = await parser.classify_intent(email_question)
    assert intent == 'question'


@pytest.mark.asyncio
async def test_route_to_agent_selects_correct_agent():
    """Test routing email to correct agent based on intent."""
    parser = EmailParser()

    # Test feedback routes to ResearchAgent
    email_feedback = {
        'sender': 'user@example.com',
        'subject': 'Feedback on assessment',
        'body': 'Your analysis was helpful',
        'intent': 'feedback'
    }
    agent = await parser.route_to_agent(email_feedback)
    assert agent == 'ResearchAgent'

    # Test research routes to KnowledgeAgent
    email_research = {
        'sender': 'user@example.com',
        'subject': 'Research request',
        'body': 'Please research this topic',
        'intent': 'research'
    }
    agent = await parser.route_to_agent(email_research)
    assert agent == 'KnowledgeAgent'

    # Test status routes to ProjectMonitorAgent
    email_status = {
        'sender': 'user@example.com',
        'subject': 'Status request',
        'body': 'What is the current status',
        'intent': 'status'
    }
    agent = await parser.route_to_agent(email_status)
    assert agent == 'ProjectMonitorAgent'

    # Test question routes to KnowledgeAgent
    email_question = {
        'sender': 'user@example.com',
        'subject': 'Question',
        'body': 'How does this work?',
        'intent': 'question'
    }
    agent = await parser.route_to_agent(email_question)
    assert agent == 'KnowledgeAgent'

    # Test unknown intent defaults to KnowledgeAgent
    email_other = {
        'sender': 'user@example.com',
        'subject': 'Random message',
        'body': 'Some content',
        'intent': 'other'
    }
    agent = await parser.route_to_agent(email_other)
    assert agent == 'KnowledgeAgent'
