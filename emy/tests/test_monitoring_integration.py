"""End-to-End Integration Tests for Monitoring System

Tests written FIRST, implementation follows.
RED → GREEN → REFACTOR cycle.

Full workflow tests from task scheduling through agent execution to database persistence.
"""

import pytest
import pytz
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TestTradingHoursEnforcementFullWorkflow:
    """Full workflow test for TradingHoursMonitorAgent enforcement."""

    @pytest.fixture
    def mock_oanda_trades(self):
        """Mock OANDA trades for testing."""
        return [
            {
                "id": "1",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "initialUnits": 100,
                "currentUnits": 100,
                "unrealizedPL": 50.0,
                "pricingStatus": "OPEN",
                "openTime": datetime.now(pytz.UTC).isoformat(),
                "takeProfitOnFill": {"price": "1.1200"},
                "stopLossOnFill": {"price": "1.1000"}
            },
            {
                "id": "2",
                "instrument": "GBP/USD",
                "direction": "SELL",
                "initialUnits": 50,
                "currentUnits": 50,
                "unrealizedPL": -20.0,
                "pricingStatus": "OPEN",
                "openTime": datetime.now(pytz.UTC).isoformat(),
                "takeProfitOnFill": {"price": "1.2500"},
                "stopLossOnFill": {"price": "1.2700"}
            }
        ]

    @pytest.mark.asyncio
    async def test_trading_hours_enforcement_full_workflow(self, mock_oanda_trades):
        """Test enforcement from task to database persistence.

        Workflow:
        1. Trigger enforcement task
        2. Verify trades fetched from OANDA
        3. Verify compliance checked
        4. Verify non-compliant trades closed
        5. Verify audit records created
        6. Verify alert sent
        7. Verify report stored
        """
        from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent

        agent = TradingHoursMonitorAgent()

        # Mock OANDA client
        agent.oanda_client.get_trades = Mock(return_value=mock_oanda_trades)

        # Mock compliance check to mark trades as non-compliant
        def mock_check_compliance(trade, current_time):
            trade_id = trade["id"]
            pair = trade["instrument"]
            return {
                "trade_id": trade_id,
                "pair": pair,
                "compliant": False,  # Mark as non-compliant
                "close_reason": "FRIDAY_HARD_CLOSE" if trade_id == "1" else "RUNNER_DEADLINE",
                "profit_pips": 5000.0 if trade_id == "1" else -2000.0,
                "pricingStatus": "OPEN"
            }

        agent._check_compliance_status = mock_check_compliance

        # Mock OANDA close_trade (NOT async)
        def mock_close_trade(trade_id, **kwargs):
            return {
                "success": True,
                "trade_id": trade_id,
                "realized_pnl": 50.0 if trade_id == "1" else -20.0,
                "error": None
            }

        agent.oanda_client.close_trade = Mock(side_effect=mock_close_trade)

        # Mock database execute
        agent.db.execute = Mock(return_value=True)

        # Mock alert (not async)
        agent._send_pushover_alert = Mock()

        # Execute enforcement
        result = await agent._enforce_compliance()

        # Assertions
        assert result["trades_checked"] == 2
        assert result["trades_closed"] == 2
        assert result["total_pnl"] == 30.0
        assert result["alert_sent"] is True
        assert result["error"] is None

        # Verify OANDA was called
        agent.oanda_client.get_trades.assert_called_once()

        # Verify database execute was called for audit records and report
        assert agent.db.execute.call_count >= 2  # At least 2 execute calls

        # Verify alert was sent
        agent._send_pushover_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_enforcement_with_no_trades(self):
        """Test enforcement when no trades are open."""
        from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent

        agent = TradingHoursMonitorAgent()

        # Mock empty trades list
        agent.oanda_client.get_trades = Mock(return_value=[])
        agent.db.insert = AsyncMock(return_value={"success": True})

        result = await agent._enforce_compliance()

        assert result["trades_checked"] == 0
        assert result["trades_closed"] == 0
        assert result["total_pnl"] == 0.0
        agent.db.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_enforcement_with_all_compliant_trades(self, mock_oanda_trades):
        """Test enforcement when all trades are compliant."""
        from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent

        agent = TradingHoursMonitorAgent()

        agent.oanda_client.get_trades = Mock(return_value=mock_oanda_trades)

        # Mock compliance check to mark all trades as compliant
        def mock_check_compliance(trade, current_time):
            return {
                "trade_id": trade["id"],
                "pair": trade["instrument"],
                "compliant": True,  # All compliant
                "close_reason": None,
                "profit_pips": 5000.0,
                "pricingStatus": "OPEN"
            }

        agent._check_compliance_status = mock_check_compliance
        agent.db.insert = AsyncMock(return_value={"success": True})

        result = await agent._enforce_compliance()

        assert result["trades_checked"] == 2
        assert result["trades_closed"] == 0  # No trades closed
        assert result["total_pnl"] == 0.0
        agent.db.insert.assert_not_called()


class TestTradingHoursMonitoringFullWorkflow:
    """Full workflow test for TradingHoursMonitorAgent monitoring."""

    @pytest.fixture
    def mock_monitoring_trades(self):
        """Mock trades for monitoring workflow."""
        return [
            {
                "id": "3",
                "instrument": "USD/JPY",
                "direction": "BUY",
                "currentUnits": 200,
                "unrealizedPL": 100.0,
                "pricingStatus": "TRAILING"
            },
            {
                "id": "4",
                "instrument": "AUD/USD",
                "direction": "SELL",
                "currentUnits": 75,
                "unrealizedPL": 30.0,
                "pricingStatus": "AT_BREAKEVEN"
            }
        ]

    @pytest.mark.asyncio
    async def test_trading_hours_monitoring_full_workflow(self, mock_monitoring_trades):
        """Test monitoring from task to database storage.

        Workflow:
        1. Trigger monitoring task
        2. Verify trades fetched
        3. Verify violations detected
        4. Verify alert sent if critical
        5. Verify report stored
        """
        from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent

        agent = TradingHoursMonitorAgent()

        agent.oanda_client.get_trades = Mock(return_value=mock_monitoring_trades)

        # Mock compliance check
        def mock_check_compliance(trade, current_time):
            trade_id = trade["id"]
            # Mark first trade as violation
            compliant = trade_id != "3"
            return {
                "trade_id": trade_id,
                "pair": trade["instrument"],
                "compliant": compliant,
                "close_reason": "VIOLATION" if not compliant else None,
                "profit_pips": 1000.0 if compliant else 500.0,
                "pricingStatus": trade["pricingStatus"]
            }

        agent._check_compliance_status = mock_check_compliance
        agent.db.execute = Mock(return_value=True)
        agent._send_pushover_alert = Mock()

        result = await agent._monitor_compliance()

        # Assertions
        assert result["trades_checked"] == 2
        assert result["violations_detected"] >= 1
        assert result["error"] is None

        # Verify alert was sent if violations detected
        if result["violations_detected"] > 0:
            agent._send_pushover_alert.assert_called()

    @pytest.mark.asyncio
    async def test_monitoring_with_critical_violations(self):
        """Test monitoring detects critical violations."""
        from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent

        agent = TradingHoursMonitorAgent()

        # Mock trades with critical violations
        trades = [
            {
                "id": "5",
                "instrument": "EUR/JPY",
                "direction": "BUY",
                "currentUnits": 500,
                "unrealizedPL": 5000.0,
                "pricingStatus": "OPEN"
            }
        ]

        agent.oanda_client.get_trades = Mock(return_value=trades)

        def mock_check_compliance(trade, current_time):
            return {
                "trade_id": trade["id"],
                "pair": trade["instrument"],
                "compliant": False,  # Critical violation
                "close_reason": "CRITICAL_HOURS_VIOLATION",
                "profit_pips": 50000.0,
                "pricingStatus": "OPEN"
            }

        agent._check_compliance_status = mock_check_compliance
        agent.db.execute = Mock()
        agent._send_pushover_alert = Mock()

        result = await agent._monitor_compliance()

        assert result["violations_detected"] == 1
        agent._send_pushover_alert.assert_called_once()


class TestLogAnalysisFullWorkflow:
    """Full workflow test for LogAnalysisAgent."""

    @pytest.fixture
    def mock_trading_signals(self):
        """Mock trading signals for analysis."""
        return [
            {"id": 1, "instrument": "EUR/USD", "outcome": "TP", "pnl": 50.0, "timestamp": "2026-03-15T10:00:00Z"},
            {"id": 2, "instrument": "EUR/USD", "outcome": "SL", "pnl": -40.0, "timestamp": "2026-03-15T11:00:00Z"},
            {"id": 3, "instrument": "GBP/USD", "outcome": "TP", "pnl": 30.0, "timestamp": "2026-03-15T12:00:00Z"}
        ]

    @pytest.mark.asyncio
    async def test_log_analysis_full_workflow(self, mock_trading_signals):
        """Test log analysis from execution to database storage.

        Workflow:
        1. Trigger daily analysis task
        2. Verify metrics calculated
        3. Verify Claude analysis
        4. Verify anomalies detected
        5. Verify report stored
        """
        from emy.agents.log_analysis_agent import LogAnalysisAgent

        agent = LogAnalysisAgent()

        # Mock database query
        agent._query_trading_signals = Mock(return_value=mock_trading_signals)
        agent._query_recommendations = Mock(return_value=[])

        # Mock database execute
        agent.db.execute = Mock(return_value=True)

        # Mock alert (not async)
        agent._send_alert_if_critical = Mock()

        # Mock Claude analysis
        agent._analyze_with_claude = Mock(return_value="Analysis: Good performance")
        agent._detect_anomalies = Mock(return_value=[])

        # Execute analysis
        result = await agent.analyze()

        # Assertions
        assert result["report_type"] == "log_analysis"
        assert result["metrics"]["total_trades"] == 3
        assert result["metrics"]["wins"] == 2
        assert result["metrics"]["losses"] == 1
        assert result["metrics"]["win_rate"] == pytest.approx(2/3, abs=0.01)
        assert result["error"] is None

        # Verify queries were made
        agent._query_trading_signals.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_analysis_detects_anomalies(self):
        """Test log analysis detects concerning patterns."""
        from emy.agents.log_analysis_agent import LogAnalysisAgent

        agent = LogAnalysisAgent()

        # Mock signals with poor performance
        signals = [
            {"id": i, "instrument": "EUR/USD", "outcome": "SL", "pnl": -50.0}
            for i in range(5)
        ]

        agent._query_trading_signals = Mock(return_value=signals)
        agent._query_recommendations = Mock(return_value=[])
        agent.db.execute = Mock()
        agent._send_alert_if_critical = Mock()
        agent._analyze_with_claude = Mock(return_value="Warning: All losses")
        agent._detect_anomalies = Mock(return_value=[{"type": "zero_win_rate", "severity": "high"}])

        result = await agent.analyze()

        assert result["metrics"]["win_rate"] == 0.0  # All losses
        assert result["metrics"]["losses"] == 5

        # Alert should be sent for critical anomaly
        agent._send_alert_if_critical.assert_called()

    @pytest.mark.asyncio
    async def test_log_analysis_with_no_trades(self):
        """Test log analysis when no trades exist."""
        from emy.agents.log_analysis_agent import LogAnalysisAgent

        agent = LogAnalysisAgent()

        agent._query_trading_signals = Mock(return_value=[])
        agent._query_recommendations = Mock(return_value=[])
        agent.db.execute = Mock()

        result = await agent.analyze()

        # When no trades, metrics should not be in result (early return)
        assert result["error"] is None


class TestProfitabilityAnalysisFullWorkflow:
    """Full workflow test for ProfitabilityAgent."""

    @pytest.fixture
    def mock_weekly_trades(self):
        """Mock trades for profitability analysis."""
        return [
            {
                "id": "t1",
                "pair": "EUR/USD",
                "outcome": "TP",
                "pnl": 50.0,
                "hour": 10,
                "regime": "TRENDING",
                "strength": 0.8,
                "timestamp": "2026-03-15T10:00:00Z"
            },
            {
                "id": "t2",
                "pair": "EUR/USD",
                "outcome": "TP",
                "pnl": 30.0,
                "hour": 14,
                "regime": "RANGING",
                "strength": 0.5,
                "timestamp": "2026-03-15T14:00:00Z"
            },
            {
                "id": "t3",
                "pair": "GBP/USD",
                "outcome": "SL",
                "pnl": -40.0,
                "hour": 18,
                "regime": "HIGH_VOL",
                "strength": 0.3,
                "timestamp": "2026-03-15T18:00:00Z"
            }
        ]

    @pytest.mark.asyncio
    async def test_profitability_analysis_full_workflow(self, mock_weekly_trades):
        """Test profitability analysis from execution to recommendations.

        Workflow:
        1. Trigger weekly analysis task
        2. Verify multi-dimensional analysis
        3. Verify recommendations generated
        4. Verify report stored
        """
        from emy.agents.profitability_agent import ProfitabilityAgent

        agent = ProfitabilityAgent()

        # Mock database query
        agent._query_trades_last_week = Mock(return_value=mock_weekly_trades)

        # Mock database execute
        agent.db.execute = Mock(return_value=True)

        # Mock Claude analysis
        with patch.object(agent.claude_client.messages, 'create') as mock_claude:
            mock_claude.return_value = MagicMock(
                content=[MagicMock(text="EUR/USD is strongest pair. Focus on 10am-14pm window.")]
            )

            # Execute analysis
            result = await agent.analyze()

        # Assertions
        assert result["report_type"] == "profitability"
        assert "profitability_analysis" in result
        assert "by_pair" in result["profitability_analysis"]
        assert "EUR/USD" in result["profitability_analysis"]["by_pair"]
        assert result["profitability_analysis"]["by_pair"]["EUR/USD"]["trades"] == 2
        # avg_pnl = 80 / 2 = 40
        assert result["profitability_analysis"]["by_pair"]["EUR/USD"]["avg_pnl"] == 40.0
        assert result["error"] is None

        # Verify queries were made
        agent._query_trades_last_week.assert_called_once()

    @pytest.mark.asyncio
    async def test_profitability_analysis_by_hour(self):
        """Test profitability analysis identifies best trading hours."""
        from emy.agents.profitability_agent import ProfitabilityAgent

        agent = ProfitabilityAgent()

        trades = [
            {"id": "t1", "pair": "EUR/USD", "outcome": "TP", "pnl": 100.0, "hour": 10, "regime": "TRENDING", "strength": 0.9},
            {"id": "t2", "pair": "EUR/USD", "outcome": "TP", "pnl": 80.0, "hour": 10, "regime": "TRENDING", "strength": 0.8},
            {"id": "t3", "pair": "EUR/USD", "outcome": "SL", "pnl": -50.0, "hour": 22, "regime": "ILLIQUID", "strength": 0.2},
        ]

        agent._query_trades_last_week = Mock(return_value=trades)
        agent.db.execute = Mock()

        with patch.object(agent.claude_client.messages, 'create') as mock_claude:
            mock_claude.return_value = MagicMock(
                content=[MagicMock(text="10am is best trading hour")]
            )
            result = await agent.analyze()

        # Verify by_hour analysis (time windows: "08:00-12:00", "12:00-16:00", "16:00-20:00")
        assert "by_hour" in result["profitability_analysis"]
        # Hour 10 falls in 08:00-12:00 window (2 trades), hour 22 falls outside all windows
        assert result["profitability_analysis"]["by_hour"]["08:00-12:00"]["trades"] == 2
        assert result["profitability_analysis"]["by_hour"]["08:00-12:00"]["win_rate"] == 1.0  # 2/2 wins

    @pytest.mark.asyncio
    async def test_profitability_analysis_by_regime(self):
        """Test profitability analysis identifies best market regimes."""
        from emy.agents.profitability_agent import ProfitabilityAgent

        agent = ProfitabilityAgent()

        trades = [
            {"id": "t1", "pair": "EUR/USD", "outcome": "TP", "pnl": 100.0, "hour": 10, "regime": "TRENDING", "strength": 0.9},
            {"id": "t2", "pair": "EUR/USD", "outcome": "TP", "pnl": 80.0, "hour": 11, "regime": "TRENDING", "strength": 0.85},
            {"id": "t3", "pair": "EUR/USD", "outcome": "SL", "pnl": -50.0, "hour": 15, "regime": "RANGING", "strength": 0.3},
        ]

        agent._query_trades_last_week = Mock(return_value=trades)
        agent.db.execute = Mock()

        with patch.object(agent.claude_client.messages, 'create') as mock_claude:
            mock_claude.return_value = MagicMock(
                content=[MagicMock(text="Trending regime is best")]
            )
            result = await agent.analyze()

        # Verify by_regime analysis
        assert "by_regime" in result["profitability_analysis"]

    @pytest.mark.asyncio
    async def test_profitability_analysis_with_no_trades(self):
        """Test profitability analysis when no trades in period."""
        from emy.agents.profitability_agent import ProfitabilityAgent

        agent = ProfitabilityAgent()

        agent._query_trades_last_week = Mock(return_value=[])
        agent.db.execute = Mock()

        result = await agent.analyze()

        assert result["error"] is None
        # Report type should still be profitability
        assert result["report_type"] == "profitability"


class TestMonitoringSystemIntegration:
    """Integration tests for the complete monitoring system."""

    @pytest.mark.asyncio
    async def test_enforcement_and_monitoring_coordinated(self):
        """Test that enforcement and monitoring don't conflict."""
        from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent

        agent = TradingHoursMonitorAgent()

        trades = [
            {
                "id": "1",
                "instrument": "EUR/USD",
                "direction": "BUY",
                "currentUnits": 100,
                "unrealizedPL": 50.0,
                "pricingStatus": "OPEN"
            }
        ]

        agent.oanda_client.get_trades = Mock(return_value=trades)

        # Mock compliance: always not compliant to trigger closure
        def mock_check_compliance(trade, current_time):
            return {
                "trade_id": trade["id"],
                "pair": trade["instrument"],
                "compliant": False,  # Always non-compliant to test closure
                "close_reason": "FRIDAY_CLOSE",
                "profit_pips": 5000.0,
                "pricingStatus": "OPEN"
            }

        agent._check_compliance_status = mock_check_compliance
        agent.oanda_client.close_trade = Mock(return_value={"success": True, "realized_pnl": 50.0})
        agent.db.execute = Mock()
        agent._send_pushover_alert = Mock()

        # Run enforcement
        enforcement_result = await agent._enforce_compliance()
        assert enforcement_result["trades_closed"] == 1

        # After enforcement closes the trade, monitoring should see 0 trades
        agent.oanda_client.get_trades = Mock(return_value=[])
        monitoring_result = await agent._monitor_compliance()
        assert monitoring_result["trades_checked"] == 0
