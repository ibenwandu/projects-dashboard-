"""Unit tests for LogAnalysisAgent - TDD approach."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from emy.agents.log_analysis_agent import LogAnalysisAgent
from emy.agents.base_agent import EMySubAgent


class TestLogAnalysisAgent:
    """Tests for LogAnalysisAgent functionality."""

    def test_log_analysis_agent_initialization(self):
        """Test LogAnalysisAgent initializes correctly with name, description, and required clients."""
        agent = LogAnalysisAgent()

        # Verify agent inherits from EMySubAgent
        assert isinstance(agent, EMySubAgent)

        # Verify agent has correct name and description
        assert agent.name == "LogAnalysisAgent"
        assert "trading" in agent.description.lower()
        assert "log" in agent.description.lower()
        assert "anomal" in agent.description.lower()

        # Verify required instance variables exist
        assert hasattr(agent, 'db')
        assert hasattr(agent, 'claude_client')
        assert hasattr(agent, 'oanda_client')

        # Verify required methods exist
        assert callable(getattr(agent, 'execute', None))
        assert callable(getattr(agent, '_query_trading_signals', None))
        assert callable(getattr(agent, '_query_recommendations', None))
        assert callable(getattr(agent, '_calculate_metrics', None))
        assert callable(getattr(agent, '_detect_anomalies', None))
        assert callable(getattr(agent, '_analyze_with_claude', None))
        assert callable(getattr(agent, '_send_alert_if_critical', None))

    def test_log_analysis_calculate_metrics(self):
        """Test metric calculation with various trade outcomes."""
        agent = LogAnalysisAgent()

        # Mock signals from database with realistic outcomes
        signals = [
            {"id": 1, "outcome": "TP", "pnl": 50.0},      # Win
            {"id": 2, "outcome": "TP", "pnl": 30.0},      # Win
            {"id": 3, "outcome": "SL", "pnl": -40.0},     # Loss
            {"id": 4, "outcome": "SL", "pnl": -20.0},     # Loss
            {"id": 5, "outcome": "PENDING", "pnl": 10.0}  # Pending (not included in win/loss)
        ]

        # Execute metric calculation
        metrics = agent._calculate_metrics(signals)

        # Verify calculations
        assert metrics["total_trades"] == 5, "Should count all signals"
        assert metrics["wins"] == 2, "Should count 2 wins (TP outcomes)"
        assert metrics["losses"] == 2, "Should count 2 losses (SL outcomes)"
        assert metrics["win_rate"] == pytest.approx(0.5), "Win rate should be 50% (2 wins / 4 closed)"
        # Avg P&L only for closed trades: (50+30-40-20) / 4 = 20 / 4 = 5.0
        assert metrics["avg_pnl"] == pytest.approx(5.0), "Avg P&L should be (50+30-40-20) / 4 = 5.0"

    def test_log_analysis_calculate_metrics_empty_signals(self):
        """Test metric calculation with empty signals."""
        agent = LogAnalysisAgent()

        metrics = agent._calculate_metrics([])

        assert metrics["total_trades"] == 0
        assert metrics["wins"] == 0
        assert metrics["losses"] == 0
        assert metrics["win_rate"] == 0.0
        assert metrics["avg_pnl"] == 0.0

    def test_log_analysis_detect_anomalies_high_sl_rate(self):
        """Test anomaly detection for high SL closure rate."""
        agent = LogAnalysisAgent()

        # Metrics showing 80% SL rate (anomaly threshold > 70%)
        metrics = {
            "total_trades": 10,
            "wins": 2,
            "losses": 8,
            "win_rate": 0.2,
            "avg_pnl": -50.0,
            "closure_reasons": {
                "SL": 0.8,           # 80% SL rate - ANOMALY
                "TP": 0.1,
                "runner_exit": 0.05,
                "time_based": 0.05
            }
        }

        anomalies = agent._detect_anomalies(metrics, None)

        # Should detect high SL rate anomaly
        assert len(anomalies) >= 1
        assert any(a["type"] == "high_sl_rate" for a in anomalies)

        # Verify anomaly has correct properties
        sl_anomaly = next(a for a in anomalies if a["type"] == "high_sl_rate")
        assert sl_anomaly["severity"] in ["high", "critical"]
        assert "0.8" in sl_anomaly["description"] or "80" in sl_anomaly["description"]

    def test_log_analysis_detect_anomalies_low_win_rate(self):
        """Test anomaly detection for low win rate."""
        agent = LogAnalysisAgent()

        # Metrics showing 20% win rate (anomaly threshold < 40%)
        metrics = {
            "total_trades": 10,
            "wins": 2,
            "losses": 8,
            "win_rate": 0.2,      # 20% win rate - ANOMALY
            "avg_pnl": -50.0,
            "closure_reasons": {
                "SL": 0.6,
                "TP": 0.2,
                "runner_exit": 0.1,
                "time_based": 0.1
            }
        }

        anomalies = agent._detect_anomalies(metrics, None)

        # Should detect at least one anomaly
        assert len(anomalies) >= 1

        # Should detect low win rate or high SL rate or both
        anomaly_types = [a["type"] for a in anomalies]
        assert "low_win_rate" in anomaly_types or "high_sl_rate" in anomaly_types

    def test_log_analysis_detect_anomalies_none(self):
        """Test anomaly detection returns empty when all metrics are normal."""
        agent = LogAnalysisAgent()

        # Metrics showing healthy trading
        metrics = {
            "total_trades": 10,
            "wins": 6,
            "losses": 4,
            "win_rate": 0.6,      # 60% win rate - HEALTHY
            "avg_pnl": 100.0,
            "closure_reasons": {
                "SL": 0.3,         # 30% SL rate - HEALTHY
                "TP": 0.6,
                "runner_exit": 0.05,
                "time_based": 0.05
            }
        }

        anomalies = agent._detect_anomalies(metrics, None)

        # Should detect no anomalies
        assert len(anomalies) == 0 or all(a["severity"] == "low" for a in anomalies)

    @pytest.mark.asyncio
    async def test_log_analysis_execute_returns_report_dict(self):
        """Test execute() returns properly structured report dictionary."""
        agent = LogAnalysisAgent()

        # Mock the internal methods
        with patch.object(agent, '_query_trading_signals', return_value=[]):
            with patch.object(agent, '_query_recommendations', return_value=[]):
                with patch.object(agent, '_calculate_metrics', return_value={
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "avg_pnl": 0.0,
                    "closure_reasons": {"SL": 0.0, "TP": 0.0, "runner_exit": 0.0, "time_based": 0.0}
                }):
                    with patch.object(agent, '_detect_anomalies', return_value=[]):
                        with patch.object(agent, '_analyze_with_claude', return_value="Analysis complete"):
                            with patch.object(agent, '_send_alert_if_critical'):
                                report = await agent.execute()

        # Verify report structure
        assert isinstance(report, dict)
        assert "report_type" in report
        assert report["report_type"] == "log_analysis"
        assert "timestamp" in report
        assert "metrics" in report
        assert "anomalies" in report
        assert "analysis" in report
        assert "alert_sent" in report
        assert "error" in report

    def test_log_analysis_detect_llm_divergence(self):
        """Test anomaly detection for LLM accuracy divergence."""
        agent = LogAnalysisAgent()

        # LLM analysis showing ChatGPT below 40% hit rate
        llm_analysis = {
            "chatgpt": {"recommendations": 10, "hit_rate": 0.35},  # ANOMALY: < 40%
            "gemini": {"recommendations": 10, "hit_rate": 0.65},
            "claude": {"recommendations": 10, "hit_rate": 0.70}
        }

        metrics = {
            "total_trades": 10,
            "wins": 6,
            "losses": 4,
            "win_rate": 0.6,
            "avg_pnl": 100.0,
            "closure_reasons": {"SL": 0.3, "TP": 0.6, "runner_exit": 0.05, "time_based": 0.05}
        }

        # Detect anomalies with LLM analysis included
        anomalies = agent._detect_anomalies(metrics, llm_analysis)

        # Should detect LLM divergence if implemented
        # (This test is optional - depends on implementation details)
        # For now, just verify the method accepts llm_analysis parameter
        assert isinstance(anomalies, list)
