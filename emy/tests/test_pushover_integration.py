import os
import time
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from emy.agents.trading_agent import TradingAgent
from emy.tools.notification_tool import PushoverNotifier


@pytest.fixture
def mock_pushover_env():
    """Fixture to enable Pushover alerts with test credentials"""
    with patch.dict(os.environ, {
        'PUSHOVER_ALERT_ENABLED': 'true',
        'PUSHOVER_USER_KEY': 'test_user_key',
        'PUSHOVER_API_TOKEN': 'test_api_token',
        'PUSHOVER_NO_THROTTLE': 'true'
    }):
        yield


class TestPushoverIntegration:
    """End-to-end integration tests for Pushover alerts"""

    @pytest.fixture
    def trading_agent(self, mock_pushover_env):
        """Create TradingAgent with mocked database and API"""
        mock_db = MagicMock()
        # Configure default mock values
        mock_db.get_max_position_size.return_value = 10000
        mock_db.get_max_daily_loss.return_value = 100.0
        mock_db.get_daily_pnl.return_value = 0.0
        mock_db.get_open_positions_count.return_value = 0
        mock_db.log_trade_rejection.return_value = None
        mock_db.log_oanda_trade.return_value = None
        mock_db.update_daily_limits.return_value = None
        mock_db.log_task.return_value = None
        mock_db.check_disabled.return_value = False

        agent = TradingAgent(db=mock_db)
        # Create notifier with Pushover enabled
        agent.notifier = PushoverNotifier()
        return agent

    @patch('emy.tools.notification_tool.requests.post')
    def test_trade_execution_workflow(self, mock_post, trading_agent):
        """Complete workflow: Execute trade -> Send Pushover alert"""
        # Mock Pushover API success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 1}
        mock_post.return_value = mock_response

        # Mock OANDA execution
        trading_agent.oanda_client = MagicMock()
        trading_agent.oanda_client.execute_trade.return_value = {
            'trade_id': 'trade123',
            'entry_price': 1.0850,
            'price': 1.0850
        }

        # Execute trade
        result = trading_agent._execute_trade(
            symbol='EUR_USD',
            direction='BUY',
            units=5000,
            stop_loss=1.0820,
            take_profit=1.0900
        )

        # Verify Pushover API was called
        assert mock_post.called
        call_data = mock_post.call_args[1]['data']
        assert call_data['priority'] == 0  # Normal
        assert 'EUR_USD' in call_data['message']

    @patch('emy.tools.notification_tool.requests.post')
    def test_rejection_alert_workflow(self, mock_post, trading_agent):
        """Complete workflow: Validate -> Reject -> Send alert"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 1}
        mock_post.return_value = mock_response

        # Mock database limits - position too large
        trading_agent.db.get_max_position_size.return_value = 10000

        # Validate oversized trade (should reject)
        is_valid, reason = trading_agent._validate_trade(
            symbol='GBP_USD',
            units=15000
        )

        assert is_valid is False
        assert mock_post.called
        call_data = mock_post.call_args[1]['data']
        assert call_data['priority'] == 0  # Normal
        assert 'exceeds' in call_data['message'].lower()

    @patch('emy.tools.notification_tool.requests.post')
    def test_daily_loss_75_alert_workflow(self, mock_post, trading_agent):
        """Complete workflow: Check daily loss -> Send 75% warning"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 1}
        mock_post.return_value = mock_response

        # Mock agent not disabled
        trading_agent.check_disabled = MagicMock(return_value=False)

        # Mock daily loss at 75%
        trading_agent.db.get_daily_pnl.return_value = -75.0
        trading_agent.db.get_max_daily_loss.return_value = 100.0
        trading_agent.db.update_daily_limits.return_value = None

        # Mock render and oanda clients
        trading_agent.render_client = MagicMock()
        trading_agent.render_client.get_service_status.return_value = {'status': 'live', 'updatedAt': '2026-03-10'}
        trading_agent.oanda_client = MagicMock()
        trading_agent.oanda_client.get_account_summary.return_value = {
            'account': {'balance': 10000, 'currency': 'USD'}
        }
        trading_agent.oanda_client.list_open_trades.return_value = []
        trading_agent.file_ops = MagicMock()
        trading_agent.file_ops.list_files.return_value = []

        # Run agent (which checks daily loss)
        trading_agent.run()

        # Verify alert sent with High priority
        assert mock_post.called
        call_data = mock_post.call_args[1]['data']
        assert call_data['priority'] == 1  # High
        assert '75' in call_data['message']

    @patch('emy.tools.notification_tool.requests.post')
    def test_daily_loss_emergency_alert_workflow(self, mock_post, trading_agent):
        """Complete workflow: Daily loss 100% -> Emergency alert + disable"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 1}
        mock_post.return_value = mock_response

        # Mock agent not disabled
        trading_agent.check_disabled = MagicMock(return_value=False)

        # Mock daily loss at 100%
        trading_agent.db.get_daily_pnl.return_value = -100.0
        trading_agent.db.get_max_daily_loss.return_value = 100.0
        trading_agent.db.update_daily_limits.return_value = None

        # Mock render and oanda clients
        trading_agent.render_client = MagicMock()
        trading_agent.render_client.get_service_status.return_value = {'status': 'live', 'updatedAt': '2026-03-10'}
        trading_agent.oanda_client = MagicMock()
        trading_agent.oanda_client.get_account_summary.return_value = {
            'account': {'balance': 10000, 'currency': 'USD'}
        }
        trading_agent.oanda_client.list_open_trades.return_value = []
        trading_agent.file_ops = MagicMock()
        trading_agent.file_ops.list_files.return_value = []

        # Run agent
        trading_agent.run()

        # Verify emergency alert with correct properties
        assert mock_post.called
        call_data = mock_post.call_args[1]['data']
        assert call_data['priority'] == 2  # Emergency
        assert 'STOP' in call_data['message']
        # Verify retry/expire set for emergency
        assert call_data['retry'] == 300
        assert call_data['expire'] == 3600

    @patch('emy.tools.notification_tool.requests.post')
    def test_alert_throttling_end_to_end(self, mock_post, trading_agent):
        """Throttling prevents duplicate alerts within 60-second window (disabled in fixture)"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 1}
        mock_post.return_value = mock_response

        # Mock OANDA
        trading_agent.oanda_client = MagicMock()
        trading_agent.oanda_client.execute_trade.return_value = {
            'trade_id': 'trade123',
            'entry_price': 1.0850,
            'price': 1.0850
        }

        # First trade execution - alert sent
        trading_agent._execute_trade(
            symbol='EUR_USD',
            direction='BUY',
            units=5000,
            stop_loss=1.0820,
            take_profit=1.0900
        )
        first_count = mock_post.call_count

        # Second trade immediately - alert sent (throttling disabled in fixture)
        trading_agent._execute_trade(
            symbol='GBP_USD',
            direction='SELL',
            units=3000,
            stop_loss=1.5220,
            take_profit=1.5000
        )
        second_count = mock_post.call_count

        # Should have sent both alerts (throttling disabled via PUSHOVER_NO_THROTTLE=true)
        assert second_count > first_count

    @patch('emy.tools.notification_tool.requests.post')
    def test_throttling_enforced_without_env_var(self, mock_post):
        """Throttling is enforced (60 seconds) when PUSHOVER_NO_THROTTLE is not set"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 1}
        mock_post.return_value = mock_response

        # Create agent WITHOUT the PUSHOVER_NO_THROTTLE env var
        # We need to unset it for this test
        env_dict = {
            'PUSHOVER_ALERT_ENABLED': 'true',
            'PUSHOVER_USER_KEY': 'test_user_key',
            'PUSHOVER_API_TOKEN': 'test_api_token'
        }
        with patch.dict(os.environ, env_dict, clear=False):
            # Remove PUSHOVER_NO_THROTTLE if it exists
            if 'PUSHOVER_NO_THROTTLE' in os.environ:
                del os.environ['PUSHOVER_NO_THROTTLE']

            mock_db = MagicMock()
            mock_db.get_max_position_size.return_value = 10000
            mock_db.get_daily_pnl.return_value = 0.0
            mock_db.get_open_positions_count.return_value = 0
            mock_db.log_trade_rejection.return_value = None
            mock_db.log_oanda_trade.return_value = None
            mock_db.update_daily_limits.return_value = None

            agent = TradingAgent(db=mock_db)
            agent.notifier = PushoverNotifier()
            agent.oanda_client = MagicMock()
            agent.oanda_client.execute_trade.return_value = {
                'trade_id': 'trade123',
                'entry_price': 1.0850,
                'price': 1.0850
            }

            # First trade execution - alert sent
            agent._execute_trade(
                symbol='EUR_USD',
                direction='BUY',
                units=5000,
                stop_loss=1.0820,
                take_profit=1.0900
            )
            first_count = mock_post.call_count

            # Second trade immediately - alert SUPPRESSED (throttling enforced)
            agent._execute_trade(
                symbol='GBP_USD',
                direction='SELL',
                units=3000,
                stop_loss=1.5220,
                take_profit=1.5000
            )
            second_count = mock_post.call_count

            # Should NOT have sent second alert (same event type, within 60-second window)
            assert second_count == first_count
