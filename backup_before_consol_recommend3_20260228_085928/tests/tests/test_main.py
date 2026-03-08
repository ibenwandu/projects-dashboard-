"""Unit tests for TradeAlertSystem helper methods — no external services required."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


def make_system():
    """Build a TradeAlertSystem with all external dependencies mocked out."""
    import os
    os.environ.setdefault('GOOGLE_DRIVE_FOLDER_ID', 'test_folder_id')

    from main import TradeAlertSystem

    with patch.object(TradeAlertSystem, '_build_components'):
        system = TradeAlertSystem.__new__(TradeAlertSystem)
        # Minimal attributes set by __init__ that _should_run_analysis needs
        system.scheduler = MagicMock()
        system.last_analysis_time = None
        system.ANALYSIS_MIN_INTERVAL = TradeAlertSystem.ANALYSIS_MIN_INTERVAL
    return system


# ---------------------------------------------------------------------------
# _should_run_analysis
# ---------------------------------------------------------------------------

class TestShouldRunAnalysis:
    def _now(self):
        return datetime.now(timezone.utc)

    def test_scheduler_says_no(self):
        sys = make_system()
        sys.scheduler.should_run_analysis.return_value = False
        assert sys._should_run_analysis(self._now()) is False

    def test_first_run_no_previous_analysis(self):
        sys = make_system()
        sys.scheduler.should_run_analysis.return_value = True
        sys.last_analysis_time = None
        assert sys._should_run_analysis(self._now()) is True

    def test_too_soon_after_last_analysis(self):
        sys = make_system()
        sys.scheduler.should_run_analysis.return_value = True
        # Last analysis was 60 seconds ago — min interval is 300 s
        sys.last_analysis_time = self._now() - timedelta(seconds=60)
        assert sys._should_run_analysis(self._now()) is False

    def test_enough_time_elapsed(self):
        sys = make_system()
        sys.scheduler.should_run_analysis.return_value = True
        # Last analysis was 10 minutes ago
        sys.last_analysis_time = self._now() - timedelta(seconds=600)
        assert sys._should_run_analysis(self._now()) is True

    def test_exactly_at_min_interval_boundary(self):
        sys = make_system()
        sys.scheduler.should_run_analysis.return_value = True
        # Just below the boundary (not strictly greater) → should return False
        # Use 299 seconds to account for execution time between setting last_analysis_time and calling _should_run_analysis
        sys.last_analysis_time = self._now() - timedelta(
            seconds=sys.ANALYSIS_MIN_INTERVAL - 1
        )
        # elapsed < ANALYSIS_MIN_INTERVAL; condition is `elapsed > interval` → False
        assert sys._should_run_analysis(self._now()) is False
