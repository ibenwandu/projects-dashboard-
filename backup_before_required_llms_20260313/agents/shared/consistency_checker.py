"""
Consistency checking utilities for Analyst Agent.

Validates consistency between:
- UI activity logs and Scalp-Engine logs
- Scalp-Engine logs and OANDA trades
- SL types and values
"""

from typing import List, Dict, Any, Tuple, Optional


class ConsistencyChecker:
    """Check consistency between different data sources."""

    def __init__(
        self,
        max_price_deviation_pips: float = 15,
        max_time_deviation_minutes: float = 5
    ):
        """
        Initialize consistency checker.

        Args:
            max_price_deviation_pips: Maximum allowed price difference (pips)
            max_time_deviation_minutes: Maximum allowed timestamp difference (minutes)
        """
        self.max_price_deviation_pips = max_price_deviation_pips
        self.max_time_deviation_minutes = max_time_deviation_minutes

    def check_ui_to_scalp_engine(
        self,
        ui_trades: List[Dict[str, Any]],
        se_trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check consistency between UI and Scalp-Engine trades.

        Returns:
            {
                "status": "VALID" | "MISMATCH",
                "matches": int,
                "mismatches": int,
                "details": [mismatch details]
            }
        """
        result = {
            "status": "VALID",
            "matches": 0,
            "mismatches": 0,
            "details": []
        }

        for ui_trade in ui_trades:
            trade_id = ui_trade.get("trade_id")
            se_trade = self._find_trade(se_trades, trade_id)

            if not se_trade:
                result["mismatches"] += 1
                result["details"].append({
                    "trade_id": trade_id,
                    "issue": "Trade in UI but not found in Scalp-Engine",
                    "ui_price": ui_trade.get("price"),
                    "severity": "HIGH"
                })
                continue

            # Check price match
            ui_price = ui_trade.get("price", 0)
            se_price = se_trade.get("entry_price", 0)
            price_diff = abs(ui_price - se_price)

            if price_diff > self.max_price_deviation_pips * 0.0001:  # Convert pips to price
                result["mismatches"] += 1
                result["details"].append({
                    "trade_id": trade_id,
                    "issue": "Entry price mismatch",
                    "ui_value": ui_price,
                    "scalp_engine_value": se_price,
                    "severity": "MEDIUM"
                })
            else:
                result["matches"] += 1

        if result["mismatches"] == 0:
            result["status"] = "VALID"
        else:
            result["status"] = "MISMATCH"

        return result

    def check_scalp_engine_to_oanda(
        self,
        se_trades: List[Dict[str, Any]],
        oanda_trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check consistency between Scalp-Engine and OANDA trades.

        Returns:
            {
                "status": "VALID" | "MISMATCH",
                "matches": int,
                "mismatches": int,
                "details": [mismatch details]
            }
        """
        result = {
            "status": "VALID",
            "matches": 0,
            "mismatches": 0,
            "details": []
        }

        for se_trade in se_trades:
            trade_id = se_trade.get("trade_id")
            pair = se_trade.get("pair")
            direction = se_trade.get("direction")

            # Find matching OANDA trade
            oanda_trade = self._find_oanda_trade(oanda_trades, pair, direction)

            if not oanda_trade:
                if se_trade.get("status") == "OPEN":
                    result["mismatches"] += 1
                    result["details"].append({
                        "trade_id": trade_id,
                        "issue": "Open trade in Scalp-Engine but not found in OANDA",
                        "pair": pair,
                        "direction": direction,
                        "severity": "HIGH"
                    })
            else:
                result["matches"] += 1

        if result["mismatches"] == 0:
            result["status"] = "VALID"
        else:
            result["status"] = "MISMATCH"

        return result

    def check_sl_validity(
        self,
        trades: List[Dict[str, Any]],
        current_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Check if SL values are valid (correct direction relative to entry).

        Returns:
            {
                "total_checks": int,
                "valid": int,
                "invalid": int,
                "details": [invalid SL details]
            }
        """
        result = {
            "total_checks": 0,
            "valid": 0,
            "invalid": 0,
            "details": []
        }

        for trade in trades:
            if trade.get("status") != "OPEN":
                continue

            result["total_checks"] += 1
            trade_id = trade.get("trade_id")
            direction = trade.get("direction")
            entry_price = trade.get("entry_price", 0)
            current_sl = trade.get("initial_sl", 0)

            # For LONG: SL should be below entry
            # For SHORT: SL should be above entry
            if direction == "LONG":
                if current_sl < entry_price:
                    result["valid"] += 1
                else:
                    result["invalid"] += 1
                    result["details"].append({
                        "trade_id": trade_id,
                        "issue": "LONG SL above entry price (invalid)",
                        "entry": entry_price,
                        "sl": current_sl,
                        "severity": "CRITICAL"
                    })

            elif direction == "SHORT":
                if current_sl > entry_price:
                    result["valid"] += 1
                else:
                    result["invalid"] += 1
                    result["details"].append({
                        "trade_id": trade_id,
                        "issue": "SHORT SL below entry price (invalid)",
                        "entry": entry_price,
                        "sl": current_sl,
                        "severity": "CRITICAL"
                    })

        return result

    def _find_trade(
        self,
        trades: List[Dict[str, Any]],
        trade_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find trade by trade_id."""
        for trade in trades:
            if trade.get("trade_id") == trade_id:
                return trade
        return None

    def _find_oanda_trade(
        self,
        oanda_trades: List[Dict[str, Any]],
        pair: str,
        direction: str
    ) -> Optional[Dict[str, Any]]:
        """Find OANDA trade by pair and direction."""
        for trade in oanda_trades:
            if trade.get("instrument") == pair.replace("/", "_"):
                side = trade.get("initialUnits", 0)
                trade_dir = "LONG" if side > 0 else ("SHORT" if side < 0 else None)
                if trade_dir == direction:
                    return trade
        return None


class TrailingSLValidator:
    """Validate trailing stop loss behavior."""

    def __init__(
        self,
        expected_update_interval_seconds: int = 30,
        stall_threshold_minutes: int = 60,
        erratic_jump_threshold_percent: float = 50
    ):
        """
        Initialize trailing SL validator.

        Args:
            expected_update_interval_seconds: Expected frequency of SL updates
            stall_threshold_minutes: Time without update to consider "stalled"
            erratic_jump_threshold_percent: Percent change to consider "erratic"
        """
        self.expected_update_interval = expected_update_interval_seconds
        self.stall_threshold = stall_threshold_minutes
        self.erratic_jump_threshold = erratic_jump_threshold_percent

    def analyze_trailing_sl(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trailing SL behavior for a trade.

        Returns:
            {
                "trade_id": str,
                "status": "OK" | "STALLED" | "ERRATIC",
                "actively_trailing": bool,
                "update_count": int,
                "last_update": timestamp,
                "time_since_update_minutes": float,
                "issues": [issue details]
            }
        """
        sl_updates = trade.get("sl_updates", [])

        result = {
            "trade_id": trade.get("trade_id"),
            "status": "OK",
            "actively_trailing": len(sl_updates) > 0,
            "update_count": len(sl_updates),
            "last_update": sl_updates[-1].get("timestamp") if sl_updates else None,
            "time_since_update_minutes": None,
            "issues": []
        }

        if not sl_updates:
            return result

        # Check for stalls
        from datetime import datetime, timedelta
        if result["last_update"]:
            try:
                last_update_time = datetime.fromisoformat(
                    result["last_update"].replace("Z", "+00:00")
                )
                time_since_update = (datetime.now(last_update_time.tzinfo) - last_update_time).total_seconds() / 60
                result["time_since_update_minutes"] = time_since_update

                if time_since_update > self.stall_threshold:  # stall_threshold is already in minutes
                    result["status"] = "STALLED"
                    result["issues"].append({
                        "type": "STALLED",
                        "description": f"No SL update for {time_since_update:.0f} minutes",
                        "severity": "HIGH"
                    })
            except Exception:
                pass

        # Check for erratic jumps
        for i in range(1, len(sl_updates)):
            prev_sl = sl_updates[i - 1].get("new_sl", sl_updates[i - 1].get("old_sl", 0))
            curr_sl = sl_updates[i].get("new_sl", 0)

            if prev_sl > 0:
                change_percent = abs((curr_sl - prev_sl) / prev_sl) * 100
                if change_percent > self.erratic_jump_threshold:
                    if result["status"] == "OK":
                        result["status"] = "ERRATIC"
                    result["issues"].append({
                        "type": "ERRATIC_JUMP",
                        "description": f"SL jumped {change_percent:.1f}%",
                        "from": prev_sl,
                        "to": curr_sl,
                        "timestamp": sl_updates[i].get("timestamp"),
                        "severity": "MEDIUM"
                    })

        return result
