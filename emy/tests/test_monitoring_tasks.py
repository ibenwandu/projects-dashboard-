"""
Unit tests for Celery Beat monitoring task definitions.

These tests verify that task definitions are properly configured and callable.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMonitoringTasks:
    """Tests for Celery Beat task wrappers."""

    def test_trading_hours_enforcement_task_exists(self):
        """Test trading_hours_enforcement task is defined and callable."""
        from emy.tasks.monitoring_tasks import trading_hours_enforcement

        assert callable(trading_hours_enforcement)
        assert hasattr(trading_hours_enforcement, 'delay')

    def test_trading_hours_monitoring_task_exists(self):
        """Test trading_hours_monitoring task is defined and callable."""
        from emy.tasks.monitoring_tasks import trading_hours_monitoring

        assert callable(trading_hours_monitoring)
        assert hasattr(trading_hours_monitoring, 'delay')

    def test_log_analysis_daily_task_exists(self):
        """Test log_analysis_daily task is defined and callable."""
        from emy.tasks.monitoring_tasks import log_analysis_daily

        assert callable(log_analysis_daily)
        assert hasattr(log_analysis_daily, 'delay')

    def test_profitability_analysis_weekly_task_exists(self):
        """Test profitability_analysis_weekly task is defined and callable."""
        from emy.tasks.monitoring_tasks import profitability_analysis_weekly

        assert callable(profitability_analysis_weekly)
        assert hasattr(profitability_analysis_weekly, 'delay')

    @patch('emy.tasks.monitoring_tasks.TradingHoursMonitorAgent')
    def test_trading_hours_enforcement_task_execution(self, mock_agent_class):
        """Test trading_hours_enforcement task calls agent correctly."""
        from emy.tasks.monitoring_tasks import trading_hours_enforcement

        # Setup mock
        mock_agent = MagicMock()
        mock_agent._enforce_compliance = AsyncMock(
            return_value={'trades_closed': 2, 'violations': []}
        )
        mock_agent_class.return_value = mock_agent

        # Execute task
        result = trading_hours_enforcement('21:30 Friday')

        # Verify
        assert result is not None
        mock_agent_class.assert_called_once()

    @patch('emy.tasks.monitoring_tasks.TradingHoursMonitorAgent')
    def test_trading_hours_monitoring_task_execution(self, mock_agent_class):
        """Test trading_hours_monitoring task calls agent correctly."""
        from emy.tasks.monitoring_tasks import trading_hours_monitoring

        # Setup mock
        mock_agent = MagicMock()
        mock_agent._monitor_compliance = AsyncMock(
            return_value={'violations_detected': 1}
        )
        mock_agent_class.return_value = mock_agent

        # Execute task
        result = trading_hours_monitoring()

        # Verify
        assert result is not None
        mock_agent_class.assert_called_once()

    @patch('emy.tasks.monitoring_tasks.LogAnalysisAgent')
    def test_log_analysis_daily_task_execution(self, mock_agent_class):
        """Test log_analysis_daily task calls agent correctly."""
        from emy.tasks.monitoring_tasks import log_analysis_daily

        # Setup mock
        mock_agent = MagicMock()
        mock_agent.analyze = AsyncMock(
            return_value={'anomalies': 3, 'period': '24 hours'}
        )
        mock_agent_class.return_value = mock_agent

        # Execute task
        result = log_analysis_daily()

        # Verify
        assert result is not None
        mock_agent_class.assert_called_once()

    @patch('emy.tasks.monitoring_tasks.ProfitabilityAgent')
    def test_profitability_analysis_weekly_task_execution(self, mock_agent_class):
        """Test profitability_analysis_weekly task calls agent correctly."""
        from emy.tasks.monitoring_tasks import profitability_analysis_weekly

        # Setup mock
        mock_agent = MagicMock()
        mock_agent.analyze = AsyncMock(
            return_value={'recommendations': ['adjust_slippage', 'reduce_frequency']}
        )
        mock_agent_class.return_value = mock_agent

        # Execute task
        result = profitability_analysis_weekly()

        # Verify
        assert result is not None
        mock_agent_class.assert_called_once()

    @patch('emy.tasks.monitoring_tasks.TradingHoursMonitorAgent')
    def test_trading_hours_enforcement_task_error_handling(self, mock_agent_class):
        """Test trading_hours_enforcement task handles errors gracefully."""
        from emy.tasks.monitoring_tasks import trading_hours_enforcement

        # Setup mock to raise exception
        mock_agent_class.side_effect = Exception("Agent initialization failed")

        # Execute task - should raise
        with pytest.raises(Exception):
            trading_hours_enforcement('21:30 Friday')

    @patch('emy.tasks.monitoring_tasks.TradingHoursMonitorAgent')
    def test_trading_hours_monitoring_task_error_handling(self, mock_agent_class):
        """Test trading_hours_monitoring task handles errors gracefully."""
        from emy.tasks.monitoring_tasks import trading_hours_monitoring

        # Setup mock to raise exception
        mock_agent_class.side_effect = Exception("Monitoring failed")

        # Execute task - should raise
        with pytest.raises(Exception):
            trading_hours_monitoring()

    @patch('emy.tasks.monitoring_tasks.LogAnalysisAgent')
    def test_log_analysis_daily_task_error_handling(self, mock_agent_class):
        """Test log_analysis_daily task handles errors gracefully."""
        from emy.tasks.monitoring_tasks import log_analysis_daily

        # Setup mock to raise exception
        mock_agent_class.side_effect = Exception("Analysis failed")

        # Execute task - should raise
        with pytest.raises(Exception):
            log_analysis_daily()

    @patch('emy.tasks.monitoring_tasks.ProfitabilityAgent')
    def test_profitability_analysis_weekly_task_error_handling(self, mock_agent_class):
        """Test profitability_analysis_weekly task handles errors gracefully."""
        from emy.tasks.monitoring_tasks import profitability_analysis_weekly

        # Setup mock to raise exception
        mock_agent_class.side_effect = Exception("Profitability analysis failed")

        # Execute task - should raise
        with pytest.raises(Exception):
            profitability_analysis_weekly()
