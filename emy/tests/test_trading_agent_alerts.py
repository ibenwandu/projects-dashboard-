import pytest
from unittest.mock import MagicMock, patch, call
from emy.agents.trading_agent import TradingAgent


class TestTradingAgentAlerts:
    """Test alert integration in TradingAgent"""

    @pytest.fixture
    def agent(self):
        """Create TradingAgent with mocked notifier and db"""
        mock_db = MagicMock()
        # Mock database methods for validation
        mock_db.get_max_position_size.return_value = 10000  # Max position size
        mock_db.get_daily_pnl.return_value = 0  # No daily loss
        mock_db.get_max_daily_loss.return_value = 100.0  # Max daily loss
        mock_db.get_open_positions_count.return_value = 0  # No open positions
        mock_db.update_daily_limits.return_value = None  # No-op

        agent = TradingAgent(db=mock_db)
        agent.notifier = MagicMock()
        return agent

    def test_execute_trade_sends_alert(self, agent):
        """_execute_trade() sends Pushover alert on success"""
        # Mock successful trade execution
        agent.oanda_client = MagicMock()
        agent.oanda_client.execute_trade.return_value = {
            'id': 'trade123',
            'instrument': 'EUR_USD',
            'units': 5000,
            'price': 1.0850,
            'stopLossOnFill': {'price': 1.0820},
            'takeProfitOnFill': {'price': 1.0900}
        }

        # Execute trade
        result = agent._execute_trade(
            symbol='EUR_USD',
            direction='BUY',
            units=5000,
            stop_loss=1.0820,
            take_profit=1.0900
        )

        # Verify alert was sent
        agent.notifier.send_alert.assert_called_once()
        call_args = agent.notifier.send_alert.call_args

        # Check priority is Normal (0)
        assert call_args[1]['priority'] == 0
        # Check message format
        assert 'EUR_USD' in call_args[1]['message']
        assert 'BUY' in call_args[1]['message']
        assert '5000' in call_args[1]['message'] or '5,000' in call_args[1]['message']

    def test_execute_trade_throttles_alert(self, agent):
        """_execute_trade() respects throttle window"""
        # Mock successful trade execution
        agent.oanda_client = MagicMock()
        agent.oanda_client.execute_trade.return_value = {
            'id': 'trade123',
            'instrument': 'EUR_USD',
            'units': 5000,
            'price': 1.0850,
            'stopLossOnFill': {'price': 1.0820},
            'takeProfitOnFill': {'price': 1.0900}
        }

        # First trade - alert sent
        agent._execute_trade(
            symbol='EUR_USD',
            direction='BUY',
            units=5000,
            stop_loss=1.0820,
            take_profit=1.0900
        )
        first_call_count = agent.notifier.send_alert.call_count

        # Second trade immediately - alert suppressed by throttle
        agent._execute_trade(
            symbol='EUR_USD',
            direction='BUY',
            units=5000,
            stop_loss=1.0820,
            take_profit=1.0900
        )
        second_call_count = agent.notifier.send_alert.call_count

        # Should not have incremented
        assert second_call_count == first_call_count

    def test_validate_trade_rejection_sends_alert(self, agent):
        """_validate_trade() sends Pushover alert on rejection"""
        # Force rejection via position size limit
        agent.db.get_max_position_size = MagicMock(return_value=10000)

        # Try to execute with oversized position
        is_valid, reason = agent._validate_trade(
            symbol='EUR_USD',
            units=15000  # Exceeds limit
        )

        assert is_valid is False
        assert 'exceeds limit' in reason.lower()

        # Verify alert was sent
        agent.notifier.send_alert.assert_called_once()
        call_args = agent.notifier.send_alert.call_args

        # Check priority is Normal (0)
        assert call_args[1]['priority'] == 0
        # Check message mentions rejection
        assert 'REJECTED' in call_args[1]['message']
        assert '15000' in call_args[1]['message'] or '15,000' in call_args[1]['message']

    def test_daily_loss_75_sends_alert(self, agent):
        """TradingAgent.run() sends High priority alert at 75% daily loss"""
        # Simulate 75% daily loss
        agent.db.get_daily_pnl.return_value = -75.0
        agent.db.get_max_daily_loss.return_value = 100.0

        agent.run()

        # Check that High priority alert was sent
        calls = [c for c in agent.notifier.send_alert.call_args_list
                 if 'daily_loss' in str(c).lower() or '75' in str(c)]

        assert len(calls) > 0
        # Verify priority is High (1)
        alert_call = calls[0]
        assert alert_call[1]['priority'] == 1

    def test_daily_loss_100_sends_emergency_alert(self, agent):
        """TradingAgent.run() sends Emergency alert at 100% daily loss"""
        # Simulate 100% daily loss
        agent.db.get_daily_pnl.return_value = -100.0
        agent.db.get_max_daily_loss.return_value = 100.0

        agent.run()

        # Check for Emergency alert
        calls = [c for c in agent.notifier.send_alert.call_args_list
                 if '100' in str(c) or 'STOP' in str(c) or 'disabled' in str(c).lower()]

        assert len(calls) > 0
        alert_call = calls[0]
        # Verify priority is Emergency (2)
        assert alert_call[1]['priority'] == 2
        # Verify message mentions trading disabled
        assert 'disabled' in alert_call[1]['message'].lower()
