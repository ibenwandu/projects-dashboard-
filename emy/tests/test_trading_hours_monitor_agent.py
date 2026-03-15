"""
Unit tests for TradingHoursMonitorAgent.

Tests cover:
- Agent initialization with correct name, description, and attributes
- Required method signatures
- Proper inheritance from EMySubAgent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent
from emy.agents.base_agent import EMySubAgent


class TestTradingHoursMonitorAgent:
    """Test suite for TradingHoursMonitorAgent."""

    def test_agent_initialization(self):
        """Test TradingHoursMonitorAgent initializes with correct name and description."""
        agent = TradingHoursMonitorAgent()

        assert agent.name == "TradingHoursMonitorAgent"
        assert "compliance" in agent.description.lower()
        assert hasattr(agent, 'oanda_client')
        assert hasattr(agent, 'db')
        assert hasattr(agent, 'trading_hours_manager')

    def test_agent_has_required_methods(self):
        """Test TradingHoursMonitorAgent has all required methods."""
        agent = TradingHoursMonitorAgent()

        assert hasattr(agent, '_get_open_trades')
        assert hasattr(agent, '_check_compliance_status')
        assert hasattr(agent, '_enforce_compliance')
        assert hasattr(agent, '_monitor_compliance')

        assert callable(agent._get_open_trades)
        assert callable(agent._check_compliance_status)
        assert callable(agent._enforce_compliance)
        assert callable(agent._monitor_compliance)

    def test_agent_inherits_from_emysubagent(self):
        """Test TradingHoursMonitorAgent properly inherits from EMySubAgent."""
        agent = TradingHoursMonitorAgent()

        assert isinstance(agent, EMySubAgent)
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)
