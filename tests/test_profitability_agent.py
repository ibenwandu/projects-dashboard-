"""
Tests for ProfitabilityAgent - profitability analysis and optimization recommendations.

Tests validate that:
1. Agent initializes with correct name, description, and methods
2. Profitability analysis by pair calculates win rate and P&L correctly
3. Claude generates 3-5 recommendations with priority and rationale
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import pytz
from emy.agents.profitability_agent import ProfitabilityAgent


class TestProfitabilityAgent:
    """Test suite for ProfitabilityAgent."""

    def test_profitability_agent_initialization(self):
        """Test ProfitabilityAgent initializes correctly."""
        agent = ProfitabilityAgent()

        # Verify name and description
        assert agent.name == "ProfitabilityAgent"
        assert "profitability" in agent.description.lower()

        # Verify required methods exist
        assert hasattr(agent, '_analyze_by_pair')
        assert hasattr(agent, '_analyze_by_hour')
        assert hasattr(agent, '_analyze_by_regime')
        assert hasattr(agent, '_analyze_by_signal_strength')
        assert hasattr(agent, '_generate_recommendations')
        assert hasattr(agent, 'execute')
        assert hasattr(agent, 'analyze')

    def test_profitability_analysis_by_pair(self):
        """Test pair-based profitability analysis calculates win rate and P&L correctly."""
        agent = ProfitabilityAgent()

        # Prepare test data: mixed outcomes for two pairs
        trades = [
            {"pair": "EUR/USD", "outcome": "TP", "pnl": 50.0},
            {"pair": "EUR/USD", "outcome": "TP", "pnl": 30.0},
            {"pair": "EUR/USD", "outcome": "SL", "pnl": -40.0},
            {"pair": "GBP/USD", "outcome": "TP", "pnl": 100.0},
            {"pair": "GBP/USD", "outcome": "SL", "pnl": -50.0},
            {"pair": "GBP/USD", "outcome": "SL", "pnl": -30.0}
        ]

        # Execute analysis
        by_pair = agent._analyze_by_pair(trades)

        # Verify structure has expected pairs
        assert "EUR/USD" in by_pair
        assert "GBP/USD" in by_pair

        # Verify EUR/USD metrics (2 wins, 1 loss)
        # P&L: (50 + 30 - 40) / 3 = 13.33
        assert by_pair["EUR/USD"]["trades"] == 3
        assert by_pair["EUR/USD"]["win_rate"] == pytest.approx(2/3, abs=0.01)
        assert by_pair["EUR/USD"]["avg_pnl"] == pytest.approx(13.33, abs=1.0)

        # Verify GBP/USD metrics (1 win, 2 losses)
        # P&L: (100 - 50 - 30) / 3 = 6.67
        assert by_pair["GBP/USD"]["trades"] == 3
        assert by_pair["GBP/USD"]["win_rate"] == pytest.approx(1/3, abs=0.01)
        assert by_pair["GBP/USD"]["avg_pnl"] == pytest.approx(6.67, abs=1.0)

    def test_profitability_generate_recommendations(self):
        """Test Claude generates 3-5 recommendations with priority and rationale."""
        agent = ProfitabilityAgent()

        # Prepare profitability analysis data
        analysis = {
            "by_pair": {
                "EUR/USD": {"trades": 20, "win_rate": 0.75, "avg_pnl": 50.0},
                "GBP/USD": {"trades": 10, "win_rate": 0.30, "avg_pnl": -25.0}
            },
            "by_regime": {
                "TRENDING": {"trades": 15, "win_rate": 0.80},
                "RANGING": {"trades": 10, "win_rate": 0.40},
                "HIGH_VOL": {"trades": 5, "win_rate": 0.20}
            },
            "by_signal_strength": {
                "low": {"trades": 5, "win_rate": 0.20},
                "medium": {"trades": 15, "win_rate": 0.40},
                "high": {"trades": 10, "win_rate": 0.80}
            }
        }

        # Mock Claude response with structured format recommendations
        mock_response = Mock()
        mock_response.content = [Mock(text="""PRIORITY: 1
TITLE: Focus on EUR/USD in trending markets
RATIONALE: EUR/USD has 75% win rate vs GBP/USD's 30% - concentrate capital on high-performing pair
EXPECTED_IMPACT: Increase overall win rate from 56% to 65%

PRIORITY: 2
TITLE: Avoid high volatility trading
RATIONALE: HIGH_VOL regime shows only 20% win rate vs TRENDING at 80%
EXPECTED_IMPACT: Reduce losses by 40%

PRIORITY: 3
TITLE: Increase position size on high signal strength
RATIONALE: High signal strength trades win 80% vs low signal at 20%
EXPECTED_IMPACT: Improve avg P&L per trade by 60%

PRIORITY: 4
TITLE: Focus trading on TRENDING and RANGING regimes
RATIONALE: TRENDING 80% + RANGING 40% combined win rate vs HIGH_VOL 20%
EXPECTED_IMPACT: Reduce drawdowns by 35%

PRIORITY: 5
TITLE: Reduce exposure to GBP/USD pair
RATIONALE: Consistent losses, -25 avg P&L, 30% win rate
EXPECTED_IMPACT: Preserve capital for higher-probability opportunities""")]

        with patch.object(agent.claude_client.messages, 'create', return_value=mock_response):
            recommendations = agent._generate_recommendations(analysis)

        # Verify we got recommendations
        assert len(recommendations) >= 3
        assert len(recommendations) <= 5

        # Verify each recommendation has required fields
        for rec in recommendations:
            assert "priority" in rec
            assert "title" in rec
            assert "rationale" in rec
            assert "expected_impact" in rec
            assert isinstance(rec["priority"], int)
            assert 1 <= rec["priority"] <= 5


class TestProfitabilityAnalysisMethods:
    """Test profitability analysis helper methods."""

    def test_analyze_by_hour(self):
        """Test hourly profitability analysis."""
        agent = ProfitabilityAgent()

        trades = [
            {"pair": "EUR/USD", "hour": 9, "outcome": "TP", "pnl": 50.0},
            {"pair": "EUR/USD", "hour": 9, "outcome": "TP", "pnl": 30.0},
            {"pair": "EUR/USD", "hour": 14, "outcome": "SL", "pnl": -40.0},
            {"pair": "EUR/USD", "hour": 18, "outcome": "TP", "pnl": 60.0}
        ]

        by_hour = agent._analyze_by_hour(trades)

        # Verify structure exists
        assert "08:00-12:00" in by_hour
        assert "12:00-16:00" in by_hour
        assert "16:00-20:00" in by_hour

    def test_analyze_by_regime(self):
        """Test market regime profitability analysis."""
        agent = ProfitabilityAgent()

        trades = [
            {"pair": "EUR/USD", "regime": "TRENDING", "outcome": "TP", "pnl": 50.0},
            {"pair": "EUR/USD", "regime": "TRENDING", "outcome": "TP", "pnl": 60.0},
            {"pair": "EUR/USD", "regime": "RANGING", "outcome": "SL", "pnl": -40.0},
            {"pair": "EUR/USD", "regime": "HIGH_VOL", "outcome": "SL", "pnl": -30.0}
        ]

        by_regime = agent._analyze_by_regime(trades)

        # Verify structure exists
        assert "TRENDING" in by_regime
        assert "RANGING" in by_regime
        assert "HIGH_VOL" in by_regime

    def test_analyze_by_signal_strength(self):
        """Test signal strength profitability analysis."""
        agent = ProfitabilityAgent()

        trades = [
            {"pair": "EUR/USD", "signal_strength": 0.9, "outcome": "TP", "pnl": 100.0},
            {"pair": "EUR/USD", "signal_strength": 0.85, "outcome": "TP", "pnl": 80.0},
            {"pair": "EUR/USD", "signal_strength": 0.5, "outcome": "TP", "pnl": 30.0},
            {"pair": "EUR/USD", "signal_strength": 0.3, "outcome": "SL", "pnl": -40.0}
        ]

        by_strength = agent._analyze_by_signal_strength(trades)

        # Verify structure exists
        assert "low" in by_strength
        assert "medium" in by_strength
        assert "high" in by_strength


class TestProfitabilityAgentExecution:
    """Test agent execution flow."""

    @pytest.mark.asyncio
    async def test_execute_returns_report_structure(self):
        """Test execute() returns properly structured report."""
        agent = ProfitabilityAgent()

        # Mock database query to return empty trades
        with patch.object(agent, '_query_trades_last_week', return_value=[]):
            report = await agent.execute()

        # Verify report structure
        assert "report_type" in report
        assert report["report_type"] == "profitability"
        assert "timestamp" in report
        assert "period" in report
        assert "profitability_analysis" in report
        assert "recommendations" in report
        assert "alert_sent" in report
        assert "error" in report

    @pytest.mark.asyncio
    async def test_analyze_with_trades(self):
        """Test analyze() with actual trade data."""
        agent = ProfitabilityAgent()

        mock_trades = [
            {"pair": "EUR/USD", "outcome": "TP", "pnl": 50.0},
            {"pair": "EUR/USD", "outcome": "SL", "pnl": -40.0}
        ]

        with patch.object(agent, '_query_trades_last_week', return_value=mock_trades):
            with patch.object(agent, '_generate_recommendations', return_value=[]):
                report = await agent.analyze()

        # Verify report has analysis results
        assert report["report_type"] == "profitability"
        assert "profitability_analysis" in report
        assert report["error"] is None
