"""
Log parsing utilities for Analyst Agent.

Parses logs from:
- Scalp-Engine (scalp_engine.log)
- UI Activity (ui_activity.log)
- OANDA Trades (oanda_trades.log)
"""

import re
import json
import glob
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path


class LogParser:
    """Base log parser."""

    def parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse timestamp from log line."""
        # Try multiple formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        return None


class ScalpEngineLogParser(LogParser):
    """Parse Scalp-Engine logs."""

    def parse_file(self, filepath: str, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Parse scalp-engine.log file.

        Returns:
            List of parsed trade events
        """
        events = []

        if not Path(filepath).exists():
            return events

        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    event = self._parse_line(line)
                    if event:
                        events.append(event)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

        return events

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse single log line."""
        # Expected format: YYYY-MM-DD HH:MM:SS | EVENT | Details
        match = re.match(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*(.+?)\s*\|\s*(.+)",
            line
        )

        if not match:
            return None

        timestamp_str, event_type, details = match.groups()
        timestamp = self.parse_timestamp(timestamp_str)

        if not timestamp:
            return None

        return {
            "timestamp": timestamp.isoformat() + "Z",
            "event_type": event_type.strip(),
            "details": details.strip(),
            "raw_line": line
        }

    def extract_trades(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract trade information from events.

        Looks for trade entry/exit/SL update events.
        """
        trades = {}

        for event in events:
            event_type = event.get("event_type", "").upper()
            details = event.get("details", "")

            # Look for trade entry patterns
            if "TRADE ENTRY" in event_type or "OPENED" in event_type:
                trade_info = self._parse_trade_entry(details)
                if trade_info:
                    trade_id = trade_info.get("trade_id")
                    if trade_id:
                        trades[trade_id] = trade_info

            # Look for SL update patterns
            elif "SL UPDATE" in event_type or "STOP LOSS" in event_type:
                sl_info = self._parse_sl_update(details, event.get("timestamp"))
                if sl_info:
                    trade_id = sl_info.get("trade_id")
                    if trade_id in trades:
                        if "sl_updates" not in trades[trade_id]:
                            trades[trade_id]["sl_updates"] = []
                        trades[trade_id]["sl_updates"].append(sl_info)

            # Look for trade exit patterns
            elif "TRADE EXIT" in event_type or "CLOSED" in event_type:
                exit_info = self._parse_trade_exit(details)
                if exit_info:
                    trade_id = exit_info.get("trade_id")
                    if trade_id in trades:
                        trades[trade_id].update(exit_info)

        return list(trades.values())

    def _parse_trade_entry(self, details: str) -> Optional[Dict[str, Any]]:
        """Parse trade entry details."""
        # Expected: EUR/USD LONG @ 1.0850 SL: 1.0800 TP: 1.0900
        match = re.search(
            r"([A-Z]{3}/[A-Z]{3})\s+(LONG|SHORT)\s+@\s+([\d.]+)\s+SL:\s*([\d.]+)",
            details
        )

        if not match:
            return None

        pair, direction, entry_str, sl_str = match.groups()

        return {
            "trade_id": f"{pair}_{direction}",
            "pair": pair,
            "direction": direction,
            "entry_price": float(entry_str),
            "initial_sl": float(sl_str),
            "status": "OPEN",
            "sl_updates": []
        }

    def _parse_sl_update(self, details: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """Parse SL update details."""
        # Expected: EUR/USD SL updated from 1.0800 to 1.0850
        match = re.search(
            r"([A-Z]{3}/[A-Z]{3})\s+SL\s+.*from\s+([\d.]+)\s+to\s+([\d.]+)",
            details
        )

        if not match:
            return None

        pair, old_sl_str, new_sl_str = match.groups()

        # Determine direction from context
        direction = "LONG" if "LONG" in details else ("SHORT" if "SHORT" in details else "UNKNOWN")

        return {
            "trade_id": f"{pair}_{direction}",
            "pair": pair,
            "timestamp": timestamp,
            "old_sl": float(old_sl_str),
            "new_sl": float(new_sl_str),
            "sl_change_pips": abs(float(new_sl_str) - float(old_sl_str))
        }

    def _parse_trade_exit(self, details: str) -> Optional[Dict[str, Any]]:
        """Parse trade exit details."""
        # Expected: EUR/USD LONG closed at 1.0900 Profit: +50 pips
        match = re.search(
            r"([A-Z]{3}/[A-Z]{3})\s+(LONG|SHORT)\s+closed\s+at\s+([\d.]+)\s+.*Profit:\s*([+-]?\d+)",
            details
        )

        if not match:
            return None

        pair, direction, exit_str, profit_str = match.groups()

        return {
            "trade_id": f"{pair}_{direction}",
            "exit_price": float(exit_str),
            "profit_pips": int(profit_str),
            "status": "CLOSED"
        }


class UIActivityLogParser(LogParser):
    """Parse UI activity logs."""

    def parse_file(self, filepath: str, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """Parse UI activity log file."""
        events = []

        if not Path(filepath).exists():
            return events

        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    event = self._parse_line(line)
                    if event:
                        events.append(event)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

        return events

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse single UI activity log line."""
        # Format: YYYY-MM-DD HH:MM:SS | ACTION | Details
        match = re.match(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*(.+?)\s*\|\s*(.+)",
            line
        )

        if not match:
            return None

        timestamp_str, action, details = match.groups()
        timestamp = self.parse_timestamp(timestamp_str)

        if not timestamp:
            return None

        return {
            "timestamp": timestamp.isoformat() + "Z",
            "action": action.strip(),
            "details": details.strip(),
            "raw_line": line
        }

    def extract_ui_trades(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract trades from UI events."""
        trades = {}

        for event in events:
            action = event.get("action", "").upper()
            details = event.get("details", "")

            if "TRADE" in action or "EXECUTED" in action:
                # Parse trade details
                trade_info = self._parse_ui_trade(details, event.get("timestamp"))
                if trade_info:
                    trade_id = trade_info.get("trade_id")
                    if trade_id:
                        trades[trade_id] = trade_info

        return list(trades.values())

    def _parse_ui_trade(self, details: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """Parse UI trade details."""
        match = re.search(
            r"([A-Z]{3}/[A-Z]{3})\s+(LONG|SHORT)\s+@?\s*([\d.]+)",
            details
        )

        if not match:
            return None

        pair, direction, price_str = match.groups()

        return {
            "trade_id": f"{pair}_{direction}",
            "pair": pair,
            "direction": direction,
            "price": float(price_str),
            "timestamp": timestamp
        }


class OandaTradeLogParser(LogParser):
    """Parse OANDA trade logs."""

    def parse_file(self, filepath: str, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """Parse OANDA trade log file."""
        trades = []

        if not Path(filepath).exists():
            return trades

        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    trade = self._parse_line(line)
                    if trade:
                        trades.append(trade)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

        return trades

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse OANDA trade log line."""
        # Format: YYYY-MM-DD HH:MM:SS | OANDA_TRADE | JSON_DATA
        match = re.match(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*OANDA_TRADE\s*\|\s*({.+})",
            line
        )

        if not match:
            return None

        timestamp_str, json_str = match.groups()

        try:
            trade_data = json.loads(json_str)
            timestamp = self.parse_timestamp(timestamp_str)

            if not timestamp:
                return None

            return {
                "timestamp": timestamp.isoformat() + "Z",
                **trade_data
            }
        except json.JSONDecodeError:
            return None


def get_log_files(log_dir: str = "Scalp-Engine/logs") -> Dict[str, str]:
    """
    Get paths to all available log files.

    Handles both:
    - Expected names: scalp_engine.log, ui_activity.log, oanda_trades.log
    - Actual dated names: scalp_engine_YYYYMMDD.log, scalp_ui_YYYYMMDD.log, oanda_YYYYMMDD.log

    Returns the most recent version if dated files exist.
    """
    log_path = Path(log_dir)
    files = {}

    # Patterns to search for (in order of preference)
    patterns = {
        "scalp_engine": [
            f"{log_dir}/scalp_engine.log",           # Expected exact name
            f"{log_dir}/scalp_engine_*.log",         # Dated version
        ],
        "ui_activity": [
            f"{log_dir}/ui_activity.log",            # Expected exact name
            f"{log_dir}/scalp_ui_*.log",             # Actual dated name
        ],
        "oanda_trades": [
            f"{log_dir}/oanda_trades.log",           # Expected exact name
            f"{log_dir}/oanda_*.log",                # Actual dated name
        ]
    }

    for log_type, patterns_list in patterns.items():
        for pattern in patterns_list:
            matches = sorted(glob.glob(pattern), reverse=True)
            if matches:
                files[log_type] = matches[0]  # Get most recent
                break

        # If still not found, use expected default (may not exist)
        if log_type not in files:
            if log_type == "scalp_engine":
                files[log_type] = f"{log_dir}/scalp_engine.log"
            elif log_type == "ui_activity":
                files[log_type] = f"{log_dir}/ui_activity.log"
            elif log_type == "oanda_trades":
                files[log_type] = f"{log_dir}/oanda_trades.log"

    return files
