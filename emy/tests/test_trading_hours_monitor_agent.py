"""Tests for TradingHoursMonitorAgent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytz
from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent


class TestTradingHoursMonitorAgent:
    """Test suite for TradingHoursMonitorAgent."""

    @pytest.fixture
    def agent(self):
        """Fixture to create a TradingHoursMonitorAgent instance."""
        with patch('emy.agents.trading_hours_monitor_agent.OandaClient'):
            with patch('emy.agents.trading_hours_monitor_agent.EMyDatabase'):
                agent = TradingHoursMonitorAgent()
                # Mock the TradingHoursManager since it won't import
                if agent.trading_hours_manager is None:
                    agent.trading_hours_manager = MagicMock()
                return agent

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

    def test_get_open_trades_success(self, agent):
        """Test _get_open_trades() returns list of open trades."""
        # Mock OandaClient.get_trades() to return 3 trades
        mock_trades = [
            {
                "id": "123456",
                "instrument": "EUR/USD",
                "initialUnits": 100,
                "currentUnits": 100,
                "openTime": "2026-03-15T14:00:00Z",
                "pricingStatus": "OPEN",
                "unrealizedPL": 45.50,
                "takeProfitOnFill": {"price": "1.1050"},
                "stopLossOnFill": {"price": "1.0950"}
            },
            {
                "id": "123457",
                "instrument": "GBP/USD",
                "initialUnits": 50,
                "currentUnits": 50,
                "openTime": "2026-03-15T15:00:00Z",
                "pricingStatus": "TRAILING",
                "unrealizedPL": 25.00,
                "takeProfitOnFill": {"price": "1.3200"},
                "stopLossOnFill": {"price": "1.2900"}
            },
            {
                "id": "123458",
                "instrument": "USD/JPY",
                "initialUnits": 200,
                "currentUnits": 200,
                "openTime": "2026-03-15T16:00:00Z",
                "pricingStatus": "AT_BREAKEVEN",
                "unrealizedPL": 0.0,
                "takeProfitOnFill": {"price": "150.50"},
                "stopLossOnFill": {"price": "149.50"}
            }
        ]

        with patch.object(agent.oanda_client, 'get_trades', return_value=mock_trades):
            trades = agent._get_open_trades()

        assert len(trades) == 3
        assert trades[0]["id"] == "123456"
        assert trades[0]["instrument"] == "EUR/USD"
        assert all("id" in t for t in trades)
        assert all("instrument" in t for t in trades)
        assert all("currentUnits" in t for t in trades)
        assert all("pricingStatus" in t for t in trades)

    def test_get_open_trades_empty(self, agent):
        """Test _get_open_trades() returns empty list when no trades open."""
        with patch.object(agent.oanda_client, 'get_trades', return_value=[]):
            trades = agent._get_open_trades()

        assert trades == []

    def test_get_open_trades_api_error(self, agent):
        """Test _get_open_trades() handles API errors gracefully."""
        with patch.object(agent.oanda_client, 'get_trades', side_effect=Exception("API Error")):
            trades = agent._get_open_trades()

        assert trades == []

    def test_check_compliance_compliant_trade(self, agent):
        """Test _check_compliance_status() for compliant trade."""
        trade = {
            "id": "123456",
            "instrument": "EUR/USD",
            "direction": "BUY",
            "currentUnits": 100,
            "unrealizedPL": 45.50,
            "pricingStatus": "OPEN"
        }

        # Mock should_close_trade to return compliant (should_close=False)
        with patch.object(agent.trading_hours_manager, 'should_close_trade', return_value=(False, "NORMAL_TRADING_HOURS")):
            current_time = datetime(2026, 3, 16, 14, 0, 0, tzinfo=pytz.UTC)
            result = agent._check_compliance_status(trade, current_time)

        assert result["trade_id"] == "123456"
        assert result["pair"] == "EUR/USD"
        assert result["compliant"] is True
        assert result["close_reason"] is None
        assert result["profit_pips"] == 4550.0  # 45.50 / (100 * 0.0001)
        assert result["pricingStatus"] == "OPEN"

    def test_check_compliance_non_compliant_trade(self, agent):
        """Test _check_compliance_status() for non-compliant trade."""
        trade = {
            "id": "123457",
            "instrument": "GBP/USD",
            "direction": "SELL",
            "currentUnits": 50,
            "unrealizedPL": -25.00,
            "pricingStatus": "OPEN"
        }

        # Mock should_close_trade to return non-compliant (should_close=True)
        with patch.object(agent.trading_hours_manager, 'should_close_trade', return_value=(True, "SATURDAY_CLOSED")):
            current_time = datetime(2026, 3, 15, 21, 30, 0, tzinfo=pytz.UTC)
            result = agent._check_compliance_status(trade, current_time)

        assert result["trade_id"] == "123457"
        assert result["pair"] == "GBP/USD"
        assert result["compliant"] is False
        assert result["close_reason"] == "SATURDAY_CLOSED"
        assert result["profit_pips"] == -5000.0  # -25.00 / (50 * 0.0001)
        assert result["pricingStatus"] == "OPEN"

    def test_check_compliance_missing_hours_manager(self, agent):
        """Test _check_compliance_status() when TradingHoursManager is None."""
        agent.trading_hours_manager = None  # Simulate missing manager

        trade = {
            "id": "123458",
            "instrument": "USD/JPY",
            "direction": "BUY",
            "currentUnits": 200,
            "unrealizedPL": 100.0,
            "pricingStatus": "TRAILING"
        }

        current_time = datetime(2026, 3, 16, 10, 0, 0, tzinfo=pytz.UTC)
        result = agent._check_compliance_status(trade, current_time)

        assert result["trade_id"] == "123458"
        assert result["pair"] == "USD/JPY"
        assert result["compliant"] is True  # Defaults to compliant when manager missing
        assert result["close_reason"] is None
        assert result["profit_pips"] == 5000.0  # 100.0 / (200 * 0.0001)
        assert result["pricingStatus"] == "TRAILING"

    @pytest.mark.asyncio
    async def test_enforce_compliance_success(self, agent):
        """Test enforcement successfully closes non-compliant trades."""
        # Mock trades: 3 trades, 2 non-compliant
        trades = [
            {
                "id": "111",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "currentUnits": 100,
                "unrealizedPL": 45.0,
                "pricingStatus": "OPEN"
            },
            {
                "id": "222",
                "instrument": "GBP/USD",
                "direction": "SELL",
                "currentUnits": 50,
                "unrealizedPL": -20.0,
                "pricingStatus": "OPEN"
            },
            {
                "id": "333",
                "instrument": "USD/JPY",
                "direction": "BUY",
                "currentUnits": 200,
                "unrealizedPL": 10.0,
                "pricingStatus": "OPEN"
            }
        ]

        # Compliance status: trades 111, 222 non-compliant
        compliance_map = {
            "111": {
                "trade_id": "111",
                "pair": "EUR/USD",
                "compliant": False,
                "close_reason": "FRIDAY_HARD_CLOSE",
                "profit_pips": 4500.0,
                "pricingStatus": "OPEN"
            },
            "222": {
                "trade_id": "222",
                "pair": "GBP/USD",
                "compliant": False,
                "close_reason": "RUNNER_DEADLINE_23:00",
                "profit_pips": -4000.0,
                "pricingStatus": "OPEN"
            },
            "333": {
                "trade_id": "333",
                "pair": "USD/JPY",
                "compliant": True,
                "close_reason": None,
                "profit_pips": 1000.0,
                "pricingStatus": "OPEN"
            }
        }

        # Close results
        close_results = {
            "111": {"success": True, "trade_id": "111", "realized_pnl": 45.0, "error": None},
            "222": {"success": True, "trade_id": "222", "realized_pnl": -20.0, "error": None}
        }

        def get_compliance(trade, current_time):
            return compliance_map[trade["id"]]

        def close_trade(trade_id, **kwargs):
            return close_results[trade_id]

        with patch.object(agent, '_get_open_trades', return_value=trades):
            with patch.object(agent, '_check_compliance_status', side_effect=get_compliance):
                with patch.object(agent.oanda_client, 'close_trade', side_effect=close_trade):
                    with patch.object(agent.db, 'execute'):
                        with patch.object(agent.db, 'query_one', return_value=(1,)):
                            with patch.object(agent.claude_client.messages, 'create') as mock_claude:
                                mock_claude.return_value = Mock(content=[Mock(text="Enforcement summary: 2 trades closed.")])
                                with patch.object(agent, '_send_pushover_alert'):
                                    result = await agent._enforce_compliance(enforcement_time="21:30 Friday")

        assert result["trades_checked"] == 3
        assert result["trades_closed"] == 2
        assert result["total_pnl"] == 25.0
        assert result["alert_sent"] is True
        assert len(result["closed_trades"]) == 2
        assert result["closed_trades"][0]["pair"] == "EUR/USD"
        assert result["closed_trades"][1]["pair"] == "GBP/USD"

    @pytest.mark.asyncio
    async def test_enforce_compliance_no_violations(self, agent):
        """Test enforcement when all trades are compliant."""
        trades = [
            {
                "id": "111",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "currentUnits": 100,
                "unrealizedPL": 45.0,
                "pricingStatus": "OPEN"
            }
        ]

        compliance_map = {
            "111": {
                "trade_id": "111",
                "pair": "EUR/USD",
                "compliant": True,
                "close_reason": None,
                "profit_pips": 4500.0,
                "pricingStatus": "OPEN"
            }
        }

        with patch.object(agent, '_get_open_trades', return_value=trades):
            with patch.object(agent, '_check_compliance_status', side_effect=lambda t, ct: compliance_map[t["id"]]):
                with patch.object(agent.db, 'execute'):
                    result = await agent._enforce_compliance()

        assert result["trades_checked"] == 1
        assert result["trades_closed"] == 0
        assert result["alert_sent"] is False
        assert len(result["closed_trades"]) == 0

    @pytest.mark.asyncio
    async def test_enforce_compliance_partial_failure(self, agent):
        """Test enforcement when some closures fail."""
        trades = [
            {
                "id": "111",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "currentUnits": 100,
                "unrealizedPL": 45.0,
                "pricingStatus": "OPEN"
            },
            {
                "id": "222",
                "instrument": "GBP/USD",
                "direction": "SELL",
                "currentUnits": 50,
                "unrealizedPL": -20.0,
                "pricingStatus": "OPEN"
            }
        ]

        compliance_map = {
            "111": {
                "trade_id": "111",
                "pair": "EUR/USD",
                "compliant": False,
                "close_reason": "FRIDAY_HARD_CLOSE",
                "profit_pips": 4500.0,
                "pricingStatus": "OPEN"
            },
            "222": {
                "trade_id": "222",
                "pair": "GBP/USD",
                "compliant": False,
                "close_reason": "RUNNER_DEADLINE",
                "profit_pips": -4000.0,
                "pricingStatus": "OPEN"
            }
        }

        close_results = {
            "111": {"success": True, "trade_id": "111", "realized_pnl": 45.0, "error": None},
            "222": {"success": False, "trade_id": "222", "realized_pnl": None, "error": "Trade not found"}
        }

        def get_compliance(trade, current_time):
            return compliance_map[trade["id"]]

        def close_trade(trade_id, **kwargs):
            return close_results[trade_id]

        with patch.object(agent, '_get_open_trades', return_value=trades):
            with patch.object(agent, '_check_compliance_status', side_effect=get_compliance):
                with patch.object(agent.oanda_client, 'close_trade', side_effect=close_trade):
                    with patch.object(agent.db, 'execute'):
                        with patch.object(agent.db, 'query_one', return_value=(1,)):
                            with patch.object(agent.claude_client.messages, 'create') as mock_claude:
                                mock_claude.return_value = Mock(content=[Mock(text="Enforcement summary.")])
                                with patch.object(agent, '_send_pushover_alert'):
                                    result = await agent._enforce_compliance()

        assert result["trades_checked"] == 2
        assert result["trades_closed"] == 1
        assert result["total_pnl"] == 45.0
        assert len(result["closed_trades"]) == 1

    @pytest.mark.asyncio
    async def test_monitor_compliance_violations_detected(self, agent):
        """Test monitoring detects violations without closing."""
        trades = [
            {
                "id": "111",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "currentUnits": 100,
                "unrealizedPL": 45.0,
                "pricingStatus": "OPEN"
            },
            {
                "id": "222",
                "instrument": "GBP/USD",
                "direction": "SELL",
                "currentUnits": 50,
                "unrealizedPL": -20.0,
                "pricingStatus": "OPEN"
            },
            {
                "id": "333",
                "instrument": "USD/JPY",
                "direction": "BUY",
                "currentUnits": 200,
                "unrealizedPL": 10.0,
                "pricingStatus": "OPEN"
            }
        ]

        compliance = {
            "111": {
                "trade_id": "111",
                "pair": "EUR/USD",
                "compliant": False,
                "close_reason": "FRIDAY_HARD_CLOSE",
                "profit_pips": 4500.0,
                "pricingStatus": "OPEN"
            },
            "222": {
                "trade_id": "222",
                "pair": "GBP/USD",
                "compliant": False,
                "close_reason": "RUNNER_DEADLINE",
                "profit_pips": -4000.0,
                "pricingStatus": "OPEN"
            },
            "333": {
                "trade_id": "333",
                "pair": "USD/JPY",
                "compliant": True,
                "close_reason": None,
                "profit_pips": 1000.0,
                "pricingStatus": "OPEN"
            }
        }

        with patch.object(agent, '_get_open_trades', return_value=trades):
            with patch.object(agent, '_check_compliance_status', side_effect=lambda t, ct: compliance[t["id"]]):
                with patch.object(agent.db, 'execute'):
                    with patch.object(agent, '_send_pushover_alert'):
                        result = await agent._monitor_compliance()

        assert result["trades_checked"] == 3
        assert result["violations_detected"] == 2
        assert result["critical"] is True
        assert result["alert_sent"] is True
        assert len(result["violations"]) == 2
        assert result["violations"][0]["pair"] == "EUR/USD"
        assert result["violations"][1]["pair"] == "GBP/USD"

    @pytest.mark.asyncio
    async def test_monitor_compliance_no_violations(self, agent):
        """Test monitoring with all trades compliant."""
        trades = [
            {
                "id": "111",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "currentUnits": 100,
                "unrealizedPL": 45.0,
                "pricingStatus": "OPEN"
            }
        ]

        compliance = {
            "111": {
                "trade_id": "111",
                "pair": "EUR/USD",
                "compliant": True,
                "close_reason": None,
                "profit_pips": 4500.0,
                "pricingStatus": "OPEN"
            }
        }

        with patch.object(agent, '_get_open_trades', return_value=trades):
            with patch.object(agent, '_check_compliance_status', side_effect=lambda t, ct: compliance[t["id"]]):
                with patch.object(agent.db, 'execute'):
                    result = await agent._monitor_compliance()

        assert result["trades_checked"] == 1
        assert result["violations_detected"] == 0
        assert result["critical"] is False
        assert result["alert_sent"] is False
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_monitor_compliance_api_error(self, agent):
        """Test monitoring handles API errors gracefully."""
        with patch.object(agent, '_get_open_trades', side_effect=Exception("API Error")):
            with patch.object(agent.db, 'execute'):
                result = await agent._monitor_compliance()

        assert result["error"] is not None
        assert "API Error" in result["error"]
        assert result["trades_checked"] == 0
