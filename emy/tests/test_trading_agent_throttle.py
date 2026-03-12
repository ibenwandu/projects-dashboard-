import time
import pytest
from unittest.mock import MagicMock, patch
from emy.agents.trading_agent import TradingAgent


class TestTradingAgentThrottle:
    """Test alert throttling mechanism"""

    @pytest.fixture
    def agent(self):
        """Create TradingAgent instance for testing"""
        agent = TradingAgent(db=MagicMock())
        return agent

    def test_throttle_initialized(self, agent):
        """TradingAgent initializes throttle state"""
        assert hasattr(agent, 'last_alert_time')
        assert agent.last_alert_time == {
            'trade_executed': None,
            'trade_rejected': None,
            'daily_loss_75': None,
            'daily_loss_100': None
        }

    def test_should_send_alert_first_time(self, agent):
        """should_send_alert() returns True for first alert of type"""
        result = agent.should_send_alert('trade_executed')
        assert result is True

    def test_should_send_alert_within_window(self, agent):
        """should_send_alert() returns False within 60-second window"""
        # Simulate first alert sent
        agent.last_alert_time['trade_executed'] = time.time()

        # Check again immediately
        result = agent.should_send_alert('trade_executed')
        assert result is False

    def test_should_send_alert_after_window(self, agent):
        """should_send_alert() returns True after 60-second window"""
        # Simulate alert sent 61 seconds ago
        agent.last_alert_time['trade_executed'] = time.time() - 61

        result = agent.should_send_alert('trade_executed')
        assert result is True

    def test_should_send_alert_independent_types(self, agent):
        """Throttle windows are independent per event type"""
        # Set one alert as recent
        agent.last_alert_time['trade_executed'] = time.time()

        # Other types should still be sendable
        assert agent.should_send_alert('trade_executed') is False
        assert agent.should_send_alert('trade_rejected') is True
        assert agent.should_send_alert('daily_loss_75') is True
        assert agent.should_send_alert('daily_loss_100') is True

    def test_record_alert_sent(self, agent):
        """record_alert_sent() updates last_alert_time"""
        before = time.time()
        agent.record_alert_sent('trade_executed')
        after = time.time()

        recorded_time = agent.last_alert_time['trade_executed']
        assert before <= recorded_time <= after
