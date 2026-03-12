"""
Test suite for Monitoring Agent.

Tests:
- Performance tracking and metrics
- Anomaly detection
- Regression detection
- Monitoring workflow

Run with: python agents/tests/test_monitoring_agent.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.shared.performance_tracker import PerformanceTracker, PerformanceMetrics
from agents.shared.anomaly_detector import AnomalyDetector


class TestPerformanceTracker:
    """Test performance tracking."""

    def setup_method(self):
        """Setup for each test."""
        self.tracker = PerformanceTracker()

    def test_calculate_metrics_empty_trades(self):
        """Test metrics with no trades."""
        metrics = self.tracker.calculate_metrics([])

        assert metrics.total_trades == 0, "Should have 0 trades"
        assert metrics.win_rate == 0.0, "Win rate should be 0"
        assert metrics.net_profit_pips == 0.0, "Net profit should be 0"

    def test_calculate_metrics_all_wins(self):
        """Test metrics with all winning trades."""
        trades = [
            {"profit_loss": 50, "max_drawdown_pips": 10, "equity": 1050},
            {"profit_loss": 75, "max_drawdown_pips": 15, "equity": 1125},
            {"profit_loss": 25, "max_drawdown_pips": 5, "equity": 1150},
        ]

        metrics = self.tracker.calculate_metrics(trades)

        assert metrics.total_trades == 3, "Should have 3 trades"
        assert metrics.winning_trades == 3, "Should have 3 wins"
        assert metrics.losing_trades == 0, "Should have 0 losses"
        assert metrics.win_rate == 1.0, "Win rate should be 100%"
        assert metrics.net_profit_pips == 150, "Net profit should be 150"
        assert metrics.average_win_pips == 50, "Average win should be 50"

    def test_calculate_metrics_mixed_trades(self):
        """Test metrics with mixed results."""
        trades = [
            {"profit_loss": 50, "max_drawdown_pips": 10, "equity": 1050},
            {"profit_loss": -30, "max_drawdown_pips": 20, "equity": 1020},
            {"profit_loss": 40, "max_drawdown_pips": 10, "equity": 1060},
            {"profit_loss": -20, "max_drawdown_pips": 15, "equity": 1040},
        ]

        metrics = self.tracker.calculate_metrics(trades)

        assert metrics.total_trades == 4, "Should have 4 trades"
        assert metrics.winning_trades == 2, "Should have 2 wins"
        assert metrics.losing_trades == 2, "Should have 2 losses"
        assert metrics.win_rate == 0.5, "Win rate should be 50%"
        assert metrics.net_profit_pips == 40, "Net profit should be 40"

    def test_calculate_profit_factor(self):
        """Test profit factor calculation."""
        trades = [
            {"profit_loss": 100, "max_drawdown_pips": 0, "equity": 1100},
            {"profit_loss": -50, "max_drawdown_pips": 20, "equity": 1050},
        ]

        metrics = self.tracker.calculate_metrics(trades)

        assert metrics.profit_factor == 2.0, "Profit factor should be 2.0"

    def test_calculate_risk_reward_ratio(self):
        """Test risk/reward ratio."""
        trades = [
            {"profit_loss": 100, "max_drawdown_pips": 0, "equity": 1100},
            {"profit_loss": 80, "max_drawdown_pips": 0, "equity": 1180},
            {"profit_loss": -40, "max_drawdown_pips": 50, "equity": 1140},
            {"profit_loss": -40, "max_drawdown_pips": 50, "equity": 1100},
        ]

        metrics = self.tracker.calculate_metrics(trades)

        # avg_win = 90, avg_loss = 40
        assert metrics.risk_reward_ratio == 2.25, "RR ratio should be 2.25"

    def test_calculate_streaks(self):
        """Test streak calculation."""
        trades = [
            {"profit_loss": 50, "max_drawdown_pips": 0, "equity": 1050},
            {"profit_loss": 30, "max_drawdown_pips": 0, "equity": 1080},
            {"profit_loss": -20, "max_drawdown_pips": 10, "equity": 1060},
            {"profit_loss": -30, "max_drawdown_pips": 10, "equity": 1030},
            {"profit_loss": -10, "max_drawdown_pips": 10, "equity": 1020},
        ]

        metrics = self.tracker.calculate_metrics(trades)

        assert metrics.longest_winning_streak == 2, "Longest win streak should be 2"
        assert metrics.longest_losing_streak == 3, "Longest loss streak should be 3"
        assert metrics.current_streak_type == "LOSS", "Current streak should be loss"
        assert metrics.current_streak_count == 3, "Current streak count should be 3"

    def test_record_and_retrieve_metrics(self):
        """Test recording and retrieving metrics."""
        metrics1 = self.tracker.calculate_metrics([
            {"profit_loss": 50, "max_drawdown_pips": 10, "equity": 1050}
        ])
        self.tracker.record_metrics(metrics1)

        metrics2 = self.tracker.calculate_metrics([
            {"profit_loss": 75, "max_drawdown_pips": 15, "equity": 1125}
        ])
        self.tracker.record_metrics(metrics2)

        latest = self.tracker.get_latest_metrics()
        assert latest.net_profit_pips == 75, "Latest should be second metrics"

        history = self.tracker.get_metrics_history()
        assert len(history) == 2, "Should have 2 records"

    def test_set_baseline_and_compare(self):
        """Test baseline setting and comparison."""
        baseline_metrics = self.tracker.calculate_metrics([
            {"profit_loss": 50, "max_drawdown_pips": 10, "equity": 1050}
        ])
        self.tracker.set_baseline(baseline_metrics)

        current_metrics = self.tracker.calculate_metrics([
            {"profit_loss": 60, "max_drawdown_pips": 8, "equity": 1060}
        ])
        self.tracker.record_metrics(current_metrics)

        comparison = self.tracker.compare_to_baseline()
        assert comparison is not None, "Should return comparison"
        assert comparison["net_profit_change_pips"] == 10, "Profit change should be 10"


class TestAnomalyDetector:
    """Test anomaly detection."""

    def setup_method(self):
        """Setup for each test."""
        self.detector = AnomalyDetector(sensitivity=2.0)

    def test_detect_no_anomalies_in_stable_data(self):
        """Test detecting anomalies in stable data."""
        values = [10.0, 10.1, 10.2, 10.1, 10.0, 10.1, 10.2]

        anomalies = self.detector.detect_metric_anomalies(values, "test_metric")

        assert len(anomalies) <= 1, "Stable data should have minimal anomalies"

    def test_detect_outlier_anomaly(self):
        """Test detecting outlier anomalies."""
        values = [10.0, 10.1, 10.2, 50.0, 10.1, 10.0, 10.1]  # 50.0 is outlier

        anomalies = self.detector.detect_metric_anomalies(values, "test_metric")

        assert len(anomalies) > 0, "Should detect outlier"
        assert any(a["index"] == 3 for a in anomalies), "Should identify index 3"

    def test_detect_regression_decline(self):
        """Test detecting performance regression."""
        baseline = {
            "win_rate": 0.65,
            "profit_factor": 2.5,
            "max_drawdown_pips": 100
        }
        current = {
            "win_rate": 0.55,  # 15% decline
            "profit_factor": 1.8,
            "max_drawdown_pips": 150
        }

        regressions = self.detector.detect_regression(baseline, current, tolerance_pct=5.0)

        assert len(regressions) > 0, "Should detect regressions"
        assert any(r["metric"] == "win_rate" for r in regressions), "Should flag win rate"

    def test_detect_losing_streak(self):
        """Test detecting losing streaks."""
        alert = self.detector.detect_losing_streak("LOSS", 5)

        assert alert is not None, "Should alert on losing streak"
        assert alert["severity"] == "MEDIUM", "5-trade loss should be MEDIUM"

        alert_high = self.detector.detect_losing_streak("LOSS", 6)
        assert alert_high["severity"] == "HIGH", "6-trade loss should be HIGH"

    def test_no_alert_winning_streak(self):
        """Test no alert on winning streak."""
        alert = self.detector.detect_losing_streak("WIN", 5)

        assert alert is None, "Should not alert on winning streak"

    def test_detect_drawdown_spike(self):
        """Test detecting drawdown spikes."""
        alert = self.detector.detect_drawdown_spike(
            current_drawdown=150.0,
            max_acceptable_drawdown=100.0
        )

        assert alert is not None, "Should alert on spike"
        assert alert["severity"] == "HIGH", "50% excess should be HIGH"

    def test_detect_low_win_rate(self):
        """Test detecting low win rate."""
        alert = self.detector.detect_low_win_rate(win_rate=0.40, threshold=0.50)

        assert alert is not None, "Should alert on low win rate"
        assert alert["severity"] == "HIGH", "Below threshold should be HIGH"

    def test_detect_poor_risk_reward(self):
        """Test detecting poor risk/reward ratio."""
        alert = self.detector.detect_poor_risk_reward(
            risk_reward_ratio=0.8,
            threshold=1.0
        )

        assert alert is not None, "Should alert on poor RR"
        assert alert["severity"] == "MEDIUM", "Poor RR should be MEDIUM"

    def test_generate_anomaly_report_healthy(self):
        """Test anomaly report for healthy metrics."""
        metrics = {
            "win_rate": 0.65,
            "profit_factor": 2.5,
            "max_drawdown_pips": 40,
            "max_drawdown_percent": 2.0,
            "recovery_factor": 5.0,
            "rr_ratio": 2.0,
            "sharpe_ratio": 1.5,
            "stop_loss_hit_rate": 0.2,
            "current_streak_type": "WIN",
            "current_streak_count": 2
        }

        report = self.detector.generate_anomaly_report(metrics, max_drawdown_threshold=50)

        # Healthy metrics should not have critical or high severity issues
        alerts = report.get("alerts", [])
        critical_alerts = [a for a in alerts if a.get("severity") == "CRITICAL"]
        assert len(critical_alerts) == 0, "No critical alerts expected"

    def test_generate_anomaly_report_critical(self):
        """Test anomaly report for critical metrics."""
        metrics = {
            "win_rate": 0.30,  # Very low
            "profit_factor": 0.5,  # Losing
            "max_drawdown_pips": 500,  # Very high
            "rr_ratio": 0.5,  # Poor
            "current_streak_type": "LOSS",
            "current_streak_count": 8  # Long losing streak
        }

        report = self.detector.generate_anomaly_report(
            metrics,
            max_drawdown_threshold=100
        )

        assert report["overall_status"] != "HEALTHY", "Should not be healthy"
        assert report["critical_issues_count"] > 0, "Should have critical issues"


def run_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MONITORING AGENT TEST SUITE")
    print("=" * 70 + "\n")

    # Test performance tracker
    print("[OK] Testing Performance Tracker...")
    tracker_tests = [
        "test_calculate_metrics_empty_trades",
        "test_calculate_metrics_all_wins",
        "test_calculate_metrics_mixed_trades",
        "test_calculate_profit_factor",
        "test_calculate_risk_reward_ratio",
        "test_calculate_streaks",
        "test_record_and_retrieve_metrics",
        "test_set_baseline_and_compare"
    ]

    tracker_test = TestPerformanceTracker()
    for method_name in tracker_tests:
        tracker_test.setup_method()
        getattr(tracker_test, method_name)()

    print(f"   PASS: All {len(tracker_tests)} tracker tests passed\n")

    # Test anomaly detector
    print("[OK] Testing Anomaly Detector...")
    detector_tests = [
        "test_detect_no_anomalies_in_stable_data",
        "test_detect_outlier_anomaly",
        "test_detect_regression_decline",
        "test_detect_losing_streak",
        "test_no_alert_winning_streak",
        "test_detect_drawdown_spike",
        "test_detect_low_win_rate",
        "test_detect_poor_risk_reward",
        "test_generate_anomaly_report_healthy",
        "test_generate_anomaly_report_critical"
    ]

    detector_test = TestAnomalyDetector()
    for method_name in detector_tests:
        detector_test.setup_method()
        getattr(detector_test, method_name)()

    print(f"   PASS: All {len(detector_tests)} detector tests passed\n")

    total_tests = len(tracker_tests) + len(detector_tests)
    print("=" * 70)
    print(f"[SUCCESS] ALL MONITORING AGENT TESTS PASSED ({total_tests} tests)")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
