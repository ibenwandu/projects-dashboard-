import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from emy.tools.notification_tool import PushoverNotifier


class TestPushoverNotifier:
    """Test PushoverNotifier initialization and API calls"""

    def test_init_with_env_variables(self):
        """PushoverNotifier initializes with credentials from environment"""
        with patch.dict(os.environ, {
            'PUSHOVER_USER_KEY': 'test_user_key',
            'PUSHOVER_API_TOKEN': 'test_api_token',
            'PUSHOVER_ALERT_ENABLED': 'true'
        }):
            notifier = PushoverNotifier()
            assert notifier.user_key == 'test_user_key'
            assert notifier.api_token == 'test_api_token'
            assert notifier.enabled is True

    def test_init_missing_credentials(self):
        """PushoverNotifier disables itself if credentials missing"""
        with patch.dict(os.environ, {}, clear=True):
            notifier = PushoverNotifier()
            assert notifier.enabled is False

    def test_init_disabled_via_env(self):
        """PushoverNotifier respects PUSHOVER_ALERT_ENABLED=false"""
        with patch.dict(os.environ, {
            'PUSHOVER_USER_KEY': 'test_user_key',
            'PUSHOVER_API_TOKEN': 'test_api_token',
            'PUSHOVER_ALERT_ENABLED': 'false'
        }):
            notifier = PushoverNotifier()
            assert notifier.enabled is False

    def test_send_alert_success(self):
        """send_alert() successfully sends notification"""
        with patch.dict(os.environ, {
            'PUSHOVER_USER_KEY': 'test_user_key',
            'PUSHOVER_API_TOKEN': 'test_api_token',
            'PUSHOVER_ALERT_ENABLED': 'true'
        }):
            notifier = PushoverNotifier()

            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'status': 1}
                mock_post.return_value = mock_response

                result = notifier.send_alert(
                    title='Test',
                    message='Test message',
                    priority=0
                )

                assert result is True
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[1]['timeout'] == 5

    def test_send_alert_disabled(self):
        """send_alert() returns False if notifier disabled"""
        with patch.dict(os.environ, {}, clear=True):
            notifier = PushoverNotifier()
            result = notifier.send_alert(
                title='Test',
                message='Test message',
                priority=0
            )
            assert result is False

    def test_send_alert_timeout(self):
        """send_alert() handles timeout gracefully"""
        with patch.dict(os.environ, {
            'PUSHOVER_USER_KEY': 'test_user_key',
            'PUSHOVER_API_TOKEN': 'test_api_token',
            'PUSHOVER_ALERT_ENABLED': 'true'
        }):
            notifier = PushoverNotifier()

            with patch('requests.post') as mock_post:
                mock_post.side_effect = requests.Timeout()

                result = notifier.send_alert(
                    title='Test',
                    message='Test message',
                    priority=0
                )

                assert result is False

    def test_send_alert_network_error(self):
        """send_alert() handles network errors gracefully"""
        with patch.dict(os.environ, {
            'PUSHOVER_USER_KEY': 'test_user_key',
            'PUSHOVER_API_TOKEN': 'test_api_token',
            'PUSHOVER_ALERT_ENABLED': 'true'
        }):
            notifier = PushoverNotifier()

            with patch('requests.post') as mock_post:
                mock_post.side_effect = requests.ConnectionError()

                result = notifier.send_alert(
                    title='Test',
                    message='Test message',
                    priority=0
                )

                assert result is False
