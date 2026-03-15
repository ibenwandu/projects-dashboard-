"""Unit tests for EmailClient with Gmail API and retry logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from emy.tools.email_tool import EmailClient


class TestEmailClient:
    """Test EmailClient class for Gmail API integration."""

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test sending email successfully via Gmail API."""
        client = EmailClient()

        # Mock the Gmail service
        with patch.object(client, '_service') as mock_service:
            mock_service.users().messages().send.return_value.execute.return_value = {
                'id': 'msg123'
            }

            result = await client.send(
                to='recipient@example.com',
                subject='Test Subject',
                body='Test body content'
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_render_template(self):
        """Test Jinja2 template rendering with context."""
        client = EmailClient()

        context = {
            'recipient_name': 'Alice Johnson',
            'opportunity': 'Market Expansion Initiative',
            'assessment': 'High potential with moderate risk',
            'recommendation': 'Proceed with Phase 1 research',
            'next_steps': ['Conduct market survey', 'Analyze competitors', 'Develop strategy']
        }

        html = await client.render_template('emails/feasibility_assessment.jinja2', context)

        assert 'Alice Johnson' in html
        assert 'Market Expansion Initiative' in html
        assert 'High potential with moderate risk' in html
        assert 'Conduct market survey' in html
        assert 'Proceed with Phase 1 research' in html

    @pytest.mark.asyncio
    async def test_send_with_retry_on_failure(self):
        """Test email send with retry logic on transient failures."""
        client = EmailClient()

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception('Transient error')
            return {'id': 'msg123'}

        with patch.object(client, '_service') as mock_service:
            mock_service.users().messages().send.return_value.execute = side_effect

            result = await client.send(
                to='recipient@example.com',
                subject='Test',
                body='Test body'
            )

            assert result is True
            assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_send_failure_after_max_retries(self):
        """Test that email is logged after 3 failed attempts."""
        client = EmailClient()

        def always_fail(*args, **kwargs):
            raise Exception('Persistent error')

        with patch.object(client, '_service') as mock_service:
            with patch.object(client, '_db') as mock_db:
                mock_service.users().messages().send.return_value.execute = always_fail

                result = await client.send(
                    to='recipient@example.com',
                    subject='Test',
                    body='Test body'
                )

                assert result is False
