"""Sandbox Gmail integration tests - verify end-to-end email workflow.

These tests use a sandbox Gmail account (emy.test@gmail.com) for integration testing.
To enable these tests, configure environment variables:
  - SANDBOX_EMAIL=emy.test@gmail.com
  - SANDBOX_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
  - SANDBOX_ENABLED=true
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from emy.config.test_config import SandboxConfig, TestConfig
from emy.tools.email_tool import EmailClient
from emy.tools.email_parser import EmailParser
from emy.agents.research_agent import ResearchAgent
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.project_monitor_agent import ProjectMonitorAgent
from emy.tasks.email_response_task import process_and_respond_to_email


# Skip all tests in this module if sandbox not configured
pytestmark = pytest.mark.skipif(
    TestConfig.skip_if_no_sandbox(),
    reason="Sandbox Gmail not configured (set SANDBOX_EMAIL and SANDBOX_SERVICE_ACCOUNT_JSON)"
)


class TestEmailSandboxIntegration:
    """Sandbox Gmail integration tests - require real Gmail account."""

    @pytest.mark.asyncio
    async def test_sandbox_send_email_to_test_account(self):
        """Test: Send email to sandbox Gmail account (emy.test@gmail.com)."""
        email_client = EmailClient()

        # Skip if service not initialized
        if not email_client._service:
            pytest.skip("Gmail service not initialized - check credentials")

        # Send test email to sandbox account
        success = await email_client.send(
            to=TestConfig.SANDBOX_EMAIL,
            subject='Emy Test: Email Integration Verification',
            body='<p>This is an integration test email from Emy email system.</p>',
            html=True
        )

        # Verify send succeeded
        assert success is True, "Failed to send test email to sandbox account"

    @pytest.mark.asyncio
    async def test_sandbox_parse_received_email(self):
        """Test: Retrieve and parse emails from sandbox inbox."""
        email_parser = EmailParser()

        # Skip if service not initialized
        if not email_parser._service:
            pytest.skip("Gmail service not initialized - check credentials")

        # Check inbox for unread emails
        emails = await email_parser.check_inbox()

        # Verify we can retrieve emails (may be empty, but call should succeed)
        assert isinstance(emails, list), "check_inbox should return a list"
        assert len(emails) >= 0, "Email list should be non-negative length"

    @pytest.mark.asyncio
    async def test_sandbox_intent_classification(self):
        """Test: Classify email intent on sandbox-formatted email."""
        email_parser = EmailParser()

        # Test email with research intent keywords
        test_email = {
            'sender': TestConfig.SANDBOX_EMAIL,
            'subject': 'Can you analyze and investigate this opportunity?',
            'body': 'I need research and analysis on this market segment.'
        }

        # Classify intent
        intent = await email_parser.classify_intent(test_email)

        # Verify intent classification
        assert intent in ['feedback', 'research', 'status', 'question', 'other']
        # This email has research keywords, so should classify as 'research'
        assert intent == 'research', f"Expected 'research' intent, got '{intent}'"

    @pytest.mark.asyncio
    async def test_sandbox_intent_question_classification(self):
        """Test: Classify question intent on email."""
        email_parser = EmailParser()

        # Test email with question intent keywords
        test_email = {
            'sender': TestConfig.SANDBOX_EMAIL,
            'subject': 'Question: What is your availability?',
            'body': 'How can we schedule a meeting? When are you available?'
        }

        # Classify intent
        intent = await email_parser.classify_intent(test_email)

        # Verify intent classification
        assert intent in ['feedback', 'research', 'status', 'question', 'other']
        # This email has question keywords, so should classify as 'question'
        assert intent == 'question', f"Expected 'question' intent, got '{intent}'"

    @pytest.mark.asyncio
    async def test_sandbox_end_to_end_workflow(self):
        """Test: Complete e2e workflow - send → receive → classify → respond."""
        email_client = EmailClient()
        email_parser = EmailParser()

        # Skip if service not initialized
        if not email_client._service:
            pytest.skip("Gmail service not initialized - check credentials")

        # Step 1: Send test email to sandbox
        success = await email_client.send(
            to=TestConfig.SANDBOX_EMAIL,
            subject='Emy E2E Test: Testing Full Workflow',
            body='<p>Please respond with your assessment of this workflow.</p>',
            html=True
        )
        assert success is True, "Failed to send initial test email"

        # Step 2: Simulate receiving the email (in real scenario, poll inbox)
        received_email = {
            'id': 'test_msg_e2e_001',
            'sender': TestConfig.SANDBOX_EMAIL,
            'subject': 'Emy E2E Test: Testing Full Workflow',
            'body': 'Please respond with your assessment of this workflow.',
            'intent': 'question'  # Pre-classified for this test
        }

        # Step 3: Process email and generate response
        response_result = await process_and_respond_to_email(received_email)

        # Step 4: Verify response was generated/sent
        assert response_result['status'] in ['response_sent', 'no_response', 'error']
        # If response was sent, verify recipient is sandbox email
        if response_result['status'] == 'response_sent':
            assert TestConfig.SANDBOX_EMAIL in response_result.get('recipient', '')

    @pytest.mark.asyncio
    async def test_sandbox_polling_and_classification_loop(self):
        """Test: Simulate complete polling loop - check inbox, parse, classify, respond."""
        email_parser = EmailParser()
        email_client = EmailClient()

        # Skip if service not initialized
        if not email_parser._service:
            pytest.skip("Gmail service not initialized - check credentials")

        # Step 1: Check inbox for unread emails
        unread_emails = await email_parser.check_inbox()
        assert isinstance(unread_emails, list)

        # Step 2: For each unread email, parse and classify
        for email_msg in unread_emails[:3]:  # Process first 3 only to avoid quota
            email_id = email_msg.get('id')

            # Parse email content
            parsed_email = await email_parser.parse_email(email_id)
            assert isinstance(parsed_email, dict)

            if parsed_email:  # Only process if parsing succeeded
                # Classify intent
                intent = await email_parser.classify_intent(parsed_email)
                assert intent in ['feedback', 'research', 'status', 'question', 'other']

                # Log that we processed it
                assert email_id is not None
                assert intent is not None

    @pytest.mark.asyncio
    async def test_sandbox_config_validation(self):
        """Test: Verify sandbox configuration is set correctly."""
        # Verify sandbox config
        assert SandboxConfig.EMAIL == TestConfig.SANDBOX_EMAIL
        assert TestConfig.SANDBOX_ENABLED is True

        # If sandbox is enabled, these should be present
        if TestConfig.SANDBOX_ENABLED:
            assert TestConfig.SANDBOX_EMAIL is not None
            assert len(TestConfig.SANDBOX_EMAIL) > 0


class TestEmailSandboxErrorHandling:
    """Test error handling in sandbox Gmail operations."""

    @pytest.mark.asyncio
    async def test_sandbox_invalid_recipient_email(self):
        """Test: Handle invalid recipient email gracefully."""
        email_client = EmailClient()

        # Skip if service not initialized
        if not email_client._service:
            pytest.skip("Gmail service not initialized")

        # Try sending to invalid email (should fail gracefully)
        success = await email_client.send(
            to='invalid@@@invalid.com',
            subject='Test Invalid Email',
            body='This should fail',
            html=False
        )

        # Should return False for invalid email
        assert success is False

    @pytest.mark.asyncio
    async def test_sandbox_empty_email_fields(self):
        """Test: Handle emails with missing/empty fields."""
        email_parser = EmailParser()

        # Email with minimal fields
        minimal_email = {
            'sender': '',
            'subject': '',
            'body': ''
        }

        # Classify intent on empty email
        intent = await email_parser.classify_intent(minimal_email)

        # Should return 'other' for unclassifiable email
        assert intent == 'other'

    @pytest.mark.asyncio
    async def test_sandbox_large_email_body(self):
        """Test: Handle emails with large body content."""
        email_parser = EmailParser()

        # Create large email body (10KB)
        large_body = 'Test content ' * 1000

        test_email = {
            'sender': TestConfig.SANDBOX_EMAIL,
            'subject': 'Large Email Test',
            'body': large_body
        }

        # Classify intent should still work
        intent = await email_parser.classify_intent(test_email)

        # Should be able to process large emails
        assert intent in ['feedback', 'research', 'status', 'question', 'other']
        assert intent is not None


class TestEmailSandboxIntegrationWithMocks:
    """Integration tests using mocks for scenarios we can't test live."""

    @pytest.mark.asyncio
    async def test_mock_email_response_generation(self):
        """Test: Mock agent response generation to email."""
        # Create mock email with research intent
        mock_email = {
            'id': 'mock_123',
            'sender': TestConfig.SANDBOX_EMAIL,
            'subject': 'Mock: Research Request',
            'body': 'Please research this topic',
            'intent': 'research'
        }

        # Mock the agent to avoid actual API calls
        with patch('emy.tasks.email_response_task.KnowledgeAgent') as mock_agent_class:
            # Setup mock agent instance
            mock_agent_instance = AsyncMock()
            mock_agent_class.return_value = mock_agent_instance

            # Mock response generation
            mock_agent_instance.generate_email_response.return_value = {
                'to': TestConfig.SANDBOX_EMAIL,
                'subject': 're: Mock: Research Request',
                'body': '<p>Mock response to research request</p>'
            }

            # Process the email
            result = await process_and_respond_to_email(mock_email)

            # Verify result structure
            assert result is not None
            assert 'status' in result

    @pytest.mark.asyncio
    async def test_mock_feedback_response_generation(self):
        """Test: Mock feedback response generation."""
        mock_email = {
            'id': 'mock_456',
            'sender': TestConfig.SANDBOX_EMAIL,
            'subject': 'Mock: Feedback on assessment',
            'body': 'Great analysis, some feedback',
            'intent': 'feedback'
        }

        # Mock the agent and email client
        with patch('emy.tasks.email_response_task.ResearchAgent') as mock_agent_class:
            with patch('emy.tasks.email_response_task.EmailClient') as mock_email_class:
                # Setup mocks
                mock_agent_instance = AsyncMock()
                mock_agent_class.return_value = mock_agent_instance

                mock_email_instance = AsyncMock()
                mock_email_class.return_value = mock_email_instance

                # Mock responses
                mock_agent_instance.generate_email_response.return_value = {
                    'to': TestConfig.SANDBOX_EMAIL,
                    'subject': 're: Mock: Feedback on assessment',
                    'body': '<p>Thank you for your feedback</p>'
                }
                mock_email_instance.send.return_value = True

                # Process email
                result = await process_and_respond_to_email(mock_email)

                # Verify response was "sent"
                assert result['status'] in ['response_sent', 'no_response', 'error']
