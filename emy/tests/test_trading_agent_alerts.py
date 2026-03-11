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
        mock_db.get_daily_pnl.return_value = 0  # No daily loss
        mock_db.get_open_positions_count.return_value = 0  # No open positions

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
