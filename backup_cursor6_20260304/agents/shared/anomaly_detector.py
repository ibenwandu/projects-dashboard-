"""
Anomaly detection for performance monitoring.

Handles:
- Detect anomalies in performance metrics
- Identify performance regressions
- Alert on critical issues
- Generate anomaly reports
"""

import statistics
from typing import Dict, Any, List, Optional, Tuple


class AnomalyDetector:
    """Detect anomalies in performance data."""

    def __init__(self, sensitivity: float = 2.0):
        """
        Initialize anomaly detector.

        Args:
            sensitivity: Standard deviation multiplier (lower = more sensitive)
        """
        self.sensitivity = sensitivity
        self.anomalies = []
        self.alerts = []

    def detect_metric_anomalies(
        self,
        values: List[float],
        metric_name: str,
        threshold_std: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in metric values using statistical analysis.

        Args:
            values: List of metric values
            metric_name: Name of metric
            threshold_std: Custom standard deviation threshold

        Returns:
            List of anomalies detected
        """
        anomalies = []

        if len(values) < 3:
            return anomalies

        try:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0

            # Use custom threshold or calculate based on sensitivity
            threshold = threshold_std or (self.sensitivity * stdev)

            for i, value in enumerate(values):
                z_score = abs((value - mean) / (stdev or 1))

                if z_score > self.sensitivity:
                    anomalies.append({
                        "index": i,
                        "value": value,
                        "metric": metric_name,
                        "mean": mean,
                        "stdev": stdev,
                        "z_score": z_score,
                        "severity": self._calculate_severity(z_score)
                    })

        except Exception:
            pass

        return anomalies

    def detect_regression(
        self,
        baseline: Dict[str, float],
        current: Dict[str, float],
        tolerance_pct: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Detect regression in performance metrics.

        Args:
            baseline: Baseline metrics
            current: Current metrics
            tolerance_pct: Tolerance percentage (default 5%)

        Returns:
            List of regressions detected
        """
        regressions = []

        # Metrics where higher is better
        higher_better = ["win_rate", "profit_factor", "recovery_factor", "sharpe_ratio", "rr_ratio"]

        # Metrics where lower is better
        lower_better = ["max_drawdown_pips", "max_drawdown_percent", "stop_loss_hit_rate"]

        # Check higher-is-better metrics
        for metric in higher_better:
            if metric in baseline and metric in current:
                baseline_val = baseline[metric]
                current_val = current[metric]

                if baseline_val > 0:
                    change_pct = ((current_val - baseline_val) / baseline_val) * 100
                    if change_pct < -tolerance_pct:
                        regressions.append({
                            "metric": metric,
                            "baseline": baseline_val,
                            "current": current_val,
                            "change_pct": change_pct,
                            "severity": self._calculate_regression_severity(change_pct)
                        })

        # Check lower-is-better metrics
        for metric in lower_better:
            if metric in baseline and metric in current:
                baseline_val = baseline[metric]
                current_val = current[metric]

                if baseline_val > 0:
                    change_pct = ((current_val - baseline_val) / baseline_val) * 100
                    if change_pct > tolerance_pct:
                        regressions.append({
                            "metric": metric,
                            "baseline": baseline_val,
                            "current": current_val,
                            "change_pct": change_pct,
                            "severity": self._calculate_regression_severity(change_pct)
                        })

        return regressions

    def detect_losing_streak(
        self,
        current_streak_type: str,
        current_streak_count: int,
        threshold: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Detect concerning losing streaks.

        Args:
            current_streak_type: "WIN" or "LOSS"
            current_streak_count: Current streak length
            threshold: Minimum streak length to alert

        Returns:
            Alert dict or None
        """
        if current_streak_type == "LOSS" and current_streak_count >= threshold:
            return {
                "type": "LOSING_STREAK",
                "severity": "HIGH" if current_streak_count > 5 else "MEDIUM",
                "streak_count": current_streak_count,
                "message": f"Losing streak of {current_streak_count} trades detected"
            }

        return None

    def detect_drawdown_spike(
        self,
        current_drawdown: float,
        max_acceptable_drawdown: float
    ) -> Optional[Dict[str, Any]]:
        """
        Detect excessive drawdown.

        Args:
            current_drawdown: Current drawdown value
            max_acceptable_drawdown: Maximum acceptable level

        Returns:
            Alert dict or None
        """
        if current_drawdown > max_acceptable_drawdown:
            excess_pct = ((current_drawdown - max_acceptable_drawdown) / max_acceptable_drawdown) * 100
            return {
                "type": "DRAWDOWN_SPIKE",
                "severity": "CRITICAL" if excess_pct > 50 else "HIGH",
                "current": current_drawdown,
                "threshold": max_acceptable_drawdown,
                "excess_pct": excess_pct,
                "message": f"Drawdown {excess_pct:.1f}% above acceptable threshold"
            }

        return None

    def detect_low_win_rate(
        self,
        win_rate: float,
        threshold: float = 0.50
    ) -> Optional[Dict[str, Any]]:
        """
        Detect concerning win rate.

        Args:
            win_rate: Current win rate (0.0-1.0)
            threshold: Minimum acceptable win rate

        Returns:
            Alert dict or None
        """
        if win_rate < threshold:
            return {
                "type": "LOW_WIN_RATE",
                "severity": "HIGH",
                "current": win_rate,
                "threshold": threshold,
                "gap_pct": ((threshold - win_rate) / threshold) * 100,
                "message": f"Win rate {win_rate:.1%} below threshold {threshold:.1%}"
            }

        return None

    def detect_poor_risk_reward(
        self,
        risk_reward_ratio: float,
        threshold: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect poor risk/reward ratio.

        Args:
            risk_reward_ratio: Current RR ratio
            threshold: Minimum acceptable ratio

        Returns:
            Alert dict or None
        """
        if risk_reward_ratio < threshold:
            return {
                "type": "POOR_RISK_REWARD",
                "severity": "MEDIUM",
                "current": risk_reward_ratio,
                "threshold": threshold,
                "gap_pct": ((threshold - risk_reward_ratio) / threshold) * 100,
                "message": f"Risk/reward {risk_reward_ratio:.2f} below threshold {threshold:.2f}"
            }

        return None

    def generate_anomaly_report(
        self,
        metrics: Dict[str, Any],
        baseline: Optional[Dict[str, Any]] = None,
        max_drawdown_threshold: float = 5.0
    ) -> Dict[str, Any]:
        """
        Generate comprehensive anomaly report.

        Args:
            metrics: Current metrics
            baseline: Baseline metrics for comparison
            max_drawdown_threshold: Maximum acceptable drawdown

        Returns:
            Comprehensive anomaly report
        """
        report = {
            "timestamp": None,
            "anomalies_detected": [],
            "regressions_detected": [],
            "alerts": [],
            "overall_status": "HEALTHY"
        }

        # Collect all anomalies and alerts
        all_issues = []

        # Check for regressions
        if baseline:
            regressions = self.detect_regression(baseline, metrics)
            report["regressions_detected"] = regressions
            all_issues.extend([r for r in regressions if r.get("severity") in ["HIGH", "CRITICAL"]])

        # Check for losing streak
        streak_alert = self.detect_losing_streak(
            metrics.get("current_streak_type"),
            metrics.get("current_streak_count", 0)
        )
        if streak_alert:
            report["alerts"].append(streak_alert)
            all_issues.append(streak_alert)

        # Check for drawdown spike
        drawdown_alert = self.detect_drawdown_spike(
            metrics.get("max_drawdown_pips", 0),
            max_drawdown_threshold
        )
        if drawdown_alert:
            report["alerts"].append(drawdown_alert)
            all_issues.append(drawdown_alert)

        # Check for low win rate
        win_rate_alert = self.detect_low_win_rate(metrics.get("win_rate", 0))
        if win_rate_alert:
            report["alerts"].append(win_rate_alert)
            all_issues.append(win_rate_alert)

        # Check for poor risk/reward
        rr_alert = self.detect_poor_risk_reward(metrics.get("risk_reward_ratio", 0))
        if rr_alert:
            report["alerts"].append(rr_alert)
            all_issues.append(rr_alert)

        # Determine overall status
        critical_issues = [i for i in all_issues if i.get("severity") == "CRITICAL"]
        high_issues = [i for i in all_issues if i.get("severity") == "HIGH"]

        if critical_issues:
            report["overall_status"] = "CRITICAL"
        elif high_issues:
            report["overall_status"] = "WARNING"
        elif all_issues:
            report["overall_status"] = "CAUTION"
        else:
            report["overall_status"] = "HEALTHY"

        report["critical_issues_count"] = len(critical_issues)
        report["high_issues_count"] = len(high_issues)

        return report

    def _calculate_severity(self, z_score: float) -> str:
        """Calculate anomaly severity based on Z-score."""
        if z_score > 4.0:
            return "CRITICAL"
        elif z_score > 3.0:
            return "HIGH"
        elif z_score > 2.0:
            return "MEDIUM"
        return "LOW"

    def _calculate_regression_severity(self, change_pct: float) -> str:
        """Calculate regression severity based on percentage change."""
        abs_change = abs(change_pct)

        if abs_change > 20:
            return "CRITICAL"
        elif abs_change > 10:
            return "HIGH"
        elif abs_change > 5:
            return "MEDIUM"
        return "LOW"
