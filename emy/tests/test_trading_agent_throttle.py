import pytest
from unittest.mock import MagicMock
from emy.agents.trading_agent import TradingAgent


class TestTradingAgentAlertManagerIntegration:
    """Test AlertManager integration in TradingAgent"""

    @pytest.fixture
    def agent(self):
        """Create TradingAgent instance for testing"""
        agent = TradingAgent(db=MagicMock())
        return agent

    def test_alert_manager_initialized_on_agent(self, agent):
        """TradingAgent has alert_manager attribute"""
        assert hasattr(agent, 'alert_manager')
        assert agent.alert_manager is not None

    def test_alert_manager_uses_agent_notifier(self, agent):
        """AlertManager.notifier is the same object as agent.notifier"""
        assert agent.alert_manager.notifier is agent.notifier

    def test_alert_manager_uses_agent_db(self, agent):
        """AlertManager.db is the same object as agent.db"""
        assert agent.alert_manager.db is agent.db
