"""Tests for TradingHoursMonitorAgent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent


class TestTradingHoursMonitorAgent:
    """Test suite for TradingHoursMonitorAgent."""

    @pytest.fixture
    def agent(self):
        """Fixture to create a TradingHoursMonitorAgent instance."""
        with patch('emy.agents.trading_hours_monitor_agent.OandaClient'):
            with patch('emy.agents.trading_hours_monitor_agent.EMyDatabase'):
                return TradingHoursMonitorAgent()

    def test_agent_initialization(self, agent):
        """Test that TradingHoursMonitorAgent initializes correctly with all required attributes."""
        # Check basic attributes
        assert hasattr(agent, 'name')
        assert agent.name == "TradingHoursMonitorAgent"

        assert hasattr(agent, 'description')
        assert "trading hours compliance" in agent.description.lower()

        # Check required clients and managers
        assert hasattr(agent, 'oanda_client')
        assert hasattr(agent, 'db')
        assert hasattr(agent, 'claude_client')

        # Verify claude_client is an Anthropic instance
        from anthropic import Anthropic
        assert isinstance(agent.claude_client, Anthropic)

    def test_execute_not_implemented(self, agent):
        """Test that execute() returns pending status."""
        import asyncio
        result = asyncio.run(agent.execute("test instruction"))
        assert result['status'] == 'pending'

    def test_run_not_implemented(self, agent):
        """Test that run() returns not implemented status."""
        success, result = agent.run()
        assert success is False
        assert result['status'] == 'not implemented'
