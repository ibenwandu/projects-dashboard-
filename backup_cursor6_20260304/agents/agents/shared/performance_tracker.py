"""
Performance tracking for post-deployment monitoring.

Handles:
- Track trading performance metrics
- Calculate KPIs (win rate, Sharpe ratio, recovery factor)
- Compare pre/post implementation performance
- Generate performance reports
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class PerformanceMetrics:
    """Container for performance metrics."""

    def __init__(self):
        """Initialize metrics."""
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.period_start = None
        self.period_end = None

        # Trade metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.win_rate = 0.0

        # Profit metrics
        self.total_profit_pips = 0.0
        self.total_loss_pips = 0.0
        self.net_profit_pips = 0.0
        self.average_win_pips = 0.0
        self.average_loss_pips = 0.0
        self.largest_win_pips = 0.0
        self.largest_loss_pips = 0.0

        # Risk metrics
        self.max_drawdown_pips = 0.0
        self.max_drawdown_percent = 0.0
        self.drawdown_recovery_time = 0  # hours
        self.stop_loss_hit_rate = 0.0

        # Ratios
        self.profit_factor = 0.0  # total_profit / total_loss
        self.risk_reward_ratio = 0.0  # avg_win / avg_loss
        self.recovery_factor = 0.0  # net_profit / max_drawdown
        self.sharpe_ratio = 0.0  # (return - risk_free) / std_dev

        # Streak metrics
        self.longest_winning_streak = 0
        self.longest_losing_streak = 0
        self.current_streak_count = 0
        self.current_streak_type = None  # "WIN" or "LOSS"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "trade_metrics": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": self.win_rate
            },
            "profit_metrics": {
                "total_profit_pips": self.total_profit_pips,
                "total_loss_pips": self.total_loss_pips,
                "net_profit_pips": self.net_profit_pips,
                "average_win_pips": self.average_win_pips,
                "average_loss_pips": self.average_loss_pips,
                "largest_win_pips": self.largest_win_pips,
                "largest_loss_pips": self.largest_loss_pips
            },
            "risk_metrics": {
                "max_drawdown_pips": self.max_drawdown_pips,
                "max_drawdown_percent": self.max_drawdown_percent,
                "drawdown_recovery_time_hours": self.drawdown_recovery_time,
                "stop_loss_hit_rate": self.stop_loss_hit_rate
            },
            "ratios": {
                "profit_factor": self.profit_factor,
                "risk_reward_ratio": self.risk_reward_ratio,
                "recovery_factor": self.recovery_factor,
                "sharpe_ratio": self.sharpe_ratio
            },
            "streaks": {
                "longest_winning_streak": self.longest_winning_streak,
                "longest_losing_streak": self.longest_losing_streak,
                "current_streak_count": self.current_streak_count,
                "current_streak_type": self.current_streak_type
            }
        }


class PerformanceTracker:
    """Track trading performance over time."""

    def __init__(self):
        """Initialize performance tracker."""
        self.metrics_history = []
        self.baseline_metrics = None
        self.improvement_baseline = None

    def calculate_metrics(
        self,
        trades: List[Dict[str, Any]],
        period_start: Optional[str] = None,
        period_end: Optional[str] = None
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics from trades.

        Args:
            trades: List of trade records
            period_start: Period start timestamp
            period_end: Period end timestamp

        Returns:
            PerformanceMetrics object
        """
        metrics = PerformanceMetrics()
        metrics.period_start = period_start
        metrics.period_end = period_end

        if not trades:
            return metrics

        # Count trades
        metrics.total_trades = len(trades)
        winning = [t for t in trades if t.get("profit_loss", 0) > 0]
        losing = [t for t in trades if t.get("profit_loss", 0) < 0]

        metrics.winning_trades = len(winning)
        metrics.losing_trades = len(losing)

        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades

        # Profit metrics
        for trade in winning:
            profit = trade.get("profit_loss", 0)
            metrics.total_profit_pips += profit
            metrics.largest_win_pips = max(metrics.largest_win_pips, profit)

        for trade in losing:
            loss = abs(trade.get("profit_loss", 0))
            metrics.total_loss_pips += loss
            metrics.largest_loss_pips = max(metrics.largest_loss_pips, loss)

        metrics.net_profit_pips = metrics.total_profit_pips - metrics.total_loss_pips

        if metrics.winning_trades > 0:
            metrics.average_win_pips = metrics.total_profit_pips / metrics.winning_trades

        if metrics.losing_trades > 0:
            metrics.average_loss_pips = metrics.total_loss_pips / metrics.losing_trades

        # Ratios
        if metrics.total_loss_pips > 0:
            metrics.profit_factor = metrics.total_profit_pips / metrics.total_loss_pips

        if metrics.average_loss_pips > 0:
            metrics.risk_reward_ratio = metrics.average_win_pips / metrics.average_loss_pips

        # Drawdown
        drawdowns = [t.get("max_drawdown_pips", 0) for t in trades]
        if drawdowns:
            metrics.max_drawdown_pips = max(drawdowns)
            equity_values = [t.get("equity", 1000) for t in trades]
            if equity_values:
                max_equity = max(equity_values)
                if max_equity > 0:
                    metrics.max_drawdown_percent = (metrics.max_drawdown_pips / max_equity) * 100

        # Recovery factor
        if metrics.max_drawdown_pips > 0:
            metrics.recovery_factor = metrics.net_profit_pips / metrics.max_drawdown_pips

        # Streaks
        self._calculate_streaks(trades, metrics)

        # SL hit rate
        sl_hits = len([t for t in trades if t.get("exit_reason") == "STOP_LOSS"])
        if metrics.total_trades > 0:
            metrics.stop_loss_hit_rate = sl_hits / metrics.total_trades

        return metrics

    def _calculate_streaks(self, trades: List[Dict[str, Any]], metrics: PerformanceMetrics) -> None:
        """Calculate winning/losing streaks."""
        if not trades:
            return

        current_streak = 1
        current_streak_type = "WIN" if trades[0].get("profit_loss", 0) > 0 else "LOSS"

        max_win_streak = 1
        max_loss_streak = 1

        for i in range(1, len(trades)):
            is_win = trades[i].get("profit_loss", 0) > 0
            streak_type = "WIN" if is_win else "LOSS"

            if streak_type == current_streak_type:
                current_streak += 1
            else:
                if current_streak_type == "WIN":
                    max_win_streak = max(max_win_streak, current_streak)
                else:
                    max_loss_streak = max(max_loss_streak, current_streak)

                current_streak = 1
                current_streak_type = streak_type

        # Record final streak
        if current_streak_type == "WIN":
            max_win_streak = max(max_win_streak, current_streak)
            metrics.current_streak_type = "WIN"
        else:
            max_loss_streak = max(max_loss_streak, current_streak)
            metrics.current_streak_type = "LOSS"

        metrics.longest_winning_streak = max_win_streak
        metrics.longest_losing_streak = max_loss_streak
        metrics.current_streak_count = current_streak

    def record_metrics(self, metrics: PerformanceMetrics) -> None:
        """Record metrics snapshot."""
        self.metrics_history.append(metrics)

    def get_latest_metrics(self) -> Optional[PerformanceMetrics]:
        """Get latest metrics."""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None

    def set_baseline(self, metrics: PerformanceMetrics) -> None:
        """Set baseline metrics for comparison."""
        self.baseline_metrics = metrics

    def compare_to_baseline(self) -> Optional[Dict[str, Any]]:
        """
        Compare current metrics to baseline.

        Returns:
            Comparison dict with improvements/regressions
        """
        if not self.baseline_metrics or not self.metrics_history:
            return None

        current = self.metrics_history[-1]

        return {
            "win_rate_change": current.win_rate - self.baseline_metrics.win_rate,
            "win_rate_improvement_pct": ((current.win_rate - self.baseline_metrics.win_rate) /
                                         (self.baseline_metrics.win_rate + 0.01)) * 100,
            "profit_factor_change": current.profit_factor - self.baseline_metrics.profit_factor,
            "drawdown_change_pips": current.max_drawdown_pips - self.baseline_metrics.max_drawdown_pips,
            "drawdown_change_pct": current.max_drawdown_percent - self.baseline_metrics.max_drawdown_percent,
            "recovery_factor_change": current.recovery_factor - self.baseline_metrics.recovery_factor,
            "net_profit_change_pips": current.net_profit_pips - self.baseline_metrics.net_profit_pips,
            "rr_ratio_change": current.risk_reward_ratio - self.baseline_metrics.risk_reward_ratio
        }

    def get_trend(self, metric_name: str, window: int = 5) -> Optional[str]:
        """
        Determine trend for a metric.

        Args:
            metric_name: Name of metric to track (e.g., "win_rate")
            window: Number of recent metrics to evaluate

        Returns:
            "IMPROVING", "STABLE", "DECLINING", or None
        """
        if len(self.metrics_history) < window:
            return None

        recent = self.metrics_history[-window:]
        values = []

        for m in recent:
            if metric_name == "win_rate":
                values.append(m.win_rate)
            elif metric_name == "profit_factor":
                values.append(m.profit_factor)
            elif metric_name == "drawdown":
                values.append(m.max_drawdown_pips)
            elif metric_name == "recovery":
                values.append(m.recovery_factor)

        if not values or len(values) < 2:
            return None

        # Simple trend: compare first half to second half
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / (mid or 1)
        second_half_avg = sum(values[mid:]) / (len(values) - mid or 1)

        if metric_name == "drawdown":
            # For drawdown, lower is better
            if second_half_avg < first_half_avg * 0.95:
                return "IMPROVING"
            elif second_half_avg > first_half_avg * 1.05:
                return "DECLINING"
        else:
            # For other metrics, higher is better
            if second_half_avg > first_half_avg * 1.05:
                return "IMPROVING"
            elif second_half_avg < first_half_avg * 0.95:
                return "DECLINING"

        return "STABLE"

    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get metrics history."""
        metrics = self.metrics_history if not limit else self.metrics_history[-limit:]
        return [m.to_dict() for m in metrics]
