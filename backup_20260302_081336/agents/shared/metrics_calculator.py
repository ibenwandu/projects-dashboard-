"""
Metrics calculation utilities for Analyst Agent.

Calculates:
- Win rate
- Profit factor
- Max drawdown
- Risk/reward ratio
- Average win/loss sizes
"""

from typing import List, Dict, Any, Tuple, Optional


class MetricsCalculator:
    """Calculate trading performance metrics."""

    @staticmethod
    def calculate_profitability_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate profitability metrics from trades.

        Args:
            trades: List of trade records with profit_pips field

        Returns:
            {
                "total_profit_pips": float,
                "total_loss_pips": float,
                "net_profit_pips": float,
                "win_rate": float,
                "winning_trades": int,
                "losing_trades": int,
                "average_win_pips": float,
                "average_loss_pips": float,
                "profit_factor": float,
                "largest_winning_trade_pips": float,
                "largest_losing_trade_pips": float
            }
        """
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]

        if not closed_trades:
            return {
                "total_profit_pips": 0.0,
                "total_loss_pips": 0.0,
                "net_profit_pips": 0.0,
                "win_rate": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "average_win_pips": 0.0,
                "average_loss_pips": 0.0,
                "profit_factor": 0.0,
                "largest_winning_trade_pips": 0.0,
                "largest_losing_trade_pips": 0.0
            }

        winning_trades = []
        losing_trades = []

        for trade in closed_trades:
            profit_pips = trade.get("profit_pips", 0)
            if profit_pips > 0:
                winning_trades.append(profit_pips)
            else:
                losing_trades.append(profit_pips)

        total_profit = sum(winning_trades)
        total_loss = sum(losing_trades)
        net_profit = total_profit + total_loss  # Note: total_loss is negative

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_trades = win_count + loss_count

        win_rate = win_count / total_trades if total_trades > 0 else 0.0
        avg_win = total_profit / win_count if win_count > 0 else 0.0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0.0

        # Profit factor: total profit / abs(total loss)
        profit_factor = total_profit / abs(total_loss) if total_loss != 0 else float('inf')

        return {
            "total_profit_pips": total_profit,
            "total_loss_pips": total_loss,
            "net_profit_pips": net_profit,
            "win_rate": win_rate,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "average_win_pips": avg_win,
            "average_loss_pips": avg_loss,
            "profit_factor": profit_factor,
            "largest_winning_trade_pips": max(winning_trades) if winning_trades else 0.0,
            "largest_losing_trade_pips": min(losing_trades) if losing_trades else 0.0
        }

    @staticmethod
    def calculate_risk_management_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate risk management metrics.

        Returns:
            {
                "max_drawdown_pips": float,
                "max_drawdown_percent": float,
                "stop_loss_hit_rate": float,
                "average_sl_distance_pips": float
            }
        """
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]

        if not closed_trades:
            return {
                "max_drawdown_pips": 0.0,
                "max_drawdown_percent": 0.0,
                "stop_loss_hit_rate": 0.0,
                "average_sl_distance_pips": 0.0
            }

        # Calculate running balance
        running_balance = 0.0
        peak_balance = 0.0
        max_drawdown = 0.0

        for trade in closed_trades:
            profit_pips = trade.get("profit_pips", 0)
            running_balance += profit_pips

            if running_balance > peak_balance:
                peak_balance = running_balance

            drawdown = peak_balance - running_balance
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Calculate SL hit rate
        sl_hit_count = 0
        for trade in closed_trades:
            exit_type = trade.get("exit_type", "UNKNOWN")
            if exit_type == "STOP_LOSS":
                sl_hit_count += 1

        sl_hit_rate = sl_hit_count / len(closed_trades) if closed_trades else 0.0

        # Calculate average SL distance
        sl_distances = []
        for trade in closed_trades:
            entry = trade.get("entry_price", 0)
            sl = trade.get("initial_sl", 0)
            if entry > 0 and sl > 0:
                distance = abs(entry - sl) * 10000  # Convert to pips (approximate)
                sl_distances.append(distance)

        avg_sl_distance = sum(sl_distances) / len(sl_distances) if sl_distances else 0.0

        # Drawdown as percent (assuming ~100 pips per 1%)
        max_drawdown_percent = (max_drawdown / 100.0) if max_drawdown > 0 else 0.0

        return {
            "max_drawdown_pips": max_drawdown,
            "max_drawdown_percent": max_drawdown_percent,
            "stop_loss_hit_rate": sl_hit_rate,
            "average_sl_distance_pips": avg_sl_distance
        }

    @staticmethod
    def calculate_risk_reward_ratio(trades: List[Dict[str, Any]]) -> float:
        """
        Calculate average risk/reward ratio.

        Returns:
            Average RR ratio (higher is better)
        """
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]

        if not closed_trades:
            return 0.0

        rr_ratios = []

        for trade in closed_trades:
            entry = trade.get("entry_price", 0)
            sl = trade.get("initial_sl", 0)
            tp = trade.get("take_profit", entry)  # Default to entry if not specified

            if entry <= 0 or sl <= 0:
                continue

            risk = abs(entry - sl)
            reward = abs(tp - entry)

            if risk > 0:
                ratio = reward / risk
                rr_ratios.append(ratio)

        return sum(rr_ratios) / len(rr_ratios) if rr_ratios else 0.0

    @staticmethod
    def calculate_equity_curve(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate equity curve (running balance over time).

        Returns:
            List of {timestamp, balance} points
        """
        closed_trades = sorted(
            [t for t in trades if t.get("status") == "CLOSED"],
            key=lambda t: t.get("timestamp", "")
        )

        equity_curve = []
        running_balance = 0.0

        for trade in closed_trades:
            profit_pips = trade.get("profit_pips", 0)
            running_balance += profit_pips

            equity_curve.append({
                "timestamp": trade.get("timestamp"),
                "trade_id": trade.get("trade_id"),
                "profit_pips": profit_pips,
                "balance_pips": running_balance
            })

        return equity_curve

    @staticmethod
    def identify_losing_streak(trades: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Identify if there's a losing streak.

        Returns:
            {
                "has_streak": bool,
                "streak_length": int,
                "trades": [trade_ids],
                "total_loss_pips": float
            }
        """
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]

        if not closed_trades:
            return None

        max_streak = 0
        current_streak = 0
        max_streak_trades = []
        current_streak_trades = []
        current_streak_loss = 0.0

        for trade in closed_trades:
            profit = trade.get("profit_pips", 0)

            if profit < 0:
                current_streak += 1
                current_streak_trades.append(trade.get("trade_id"))
                current_streak_loss += profit

                if current_streak > max_streak:
                    max_streak = current_streak
                    max_streak_trades = current_streak_trades.copy()
            else:
                current_streak = 0
                current_streak_trades = []
                current_streak_loss = 0.0

        return {
            "has_streak": max_streak >= 3,  # Consider 3+ losses a streak
            "streak_length": max_streak,
            "trades": max_streak_trades,
            "total_loss_pips": -max(abs(sum([t.get("profit_pips", 0) for t in closed_trades
                                             if t.get("trade_id") in max_streak_trades])), 0)
        }
