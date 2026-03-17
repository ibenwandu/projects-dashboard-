"""
TradingHoursMonitorAgent - monitors and enforces trading hours compliance.

This agent monitors the trading system to ensure trading hours rules (defined in
TradingHoursManager) are being respected. It can run in two modes:

- Enforcement Mode: Closes non-compliant trades at 21:30 UTC (Friday) and 23:00 UTC (Mon-Thu)
- Monitoring Mode: Checks for violations every 6 hours without taking action
"""

import logging
from typing import Dict, List
from datetime import datetime
import pytz
from anthropic import Anthropic
from emy.agents.base_agent import EMySubAgent
from emy.tools.api_client import OandaClient
from emy.core.database import EMyDatabase

logger = logging.getLogger('TradingHoursMonitorAgent')


class TradingHoursMonitorAgent(EMySubAgent):
    """Monitors trading hours compliance and autonomously closes non-compliant trades.

    This agent monitors the trading system to ensure trading hours rules (defined in
    TradingHoursManager) are being respected. It can run in two modes:

    - Enforcement Mode: Closes non-compliant trades at 21:30 UTC (Friday) and 23:00 UTC (Mon-Thu)
    - Monitoring Mode: Checks for violations every 6 hours without taking action
    """

    def __init__(self):
        """Initialize TradingHoursMonitorAgent with required clients and managers."""
        super().__init__(
            'TradingHoursMonitorAgent',
            'claude-haiku-4-5-20251001'
        )

        # Add name and description attributes for compatibility
        self.name = "TradingHoursMonitorAgent"
        self.description = "Monitors trading hours compliance and autonomously closes non-compliant trades"

        # Initialize OANDA client for trade management
        self.oanda_client = OandaClient()

        # Initialize database for storing reports and audit records
        self.db = EMyDatabase()

        # Initialize Claude client for compliance analysis (Haiku for routine analysis)
        self.claude_client = Anthropic()
        logger.info(f"[TradingHoursMonitorAgent] Claude client initialized")

        # Import TradingHoursManager from Scalp-Engine
        try:
            from Scalp_Engine.trading_hours_manager import TradingHoursManager
            self.trading_hours_manager = TradingHoursManager()
            logger.info("[TradingHoursMonitorAgent] TradingHoursManager imported successfully")
        except ImportError:
            logger.warning("[TradingHoursMonitorAgent] Could not import TradingHoursManager from Scalp-Engine")
            self.trading_hours_manager = None

        logger.info(f"[TradingHoursMonitorAgent] Initialized: {self.name}")

    async def execute(self, instruction: str = None, **kwargs):
        """Execute the agent's primary logic.

        Args:
            instruction (str, optional): User instruction (e.g., "enforce compliance now")
            **kwargs: Additional parameters

        Returns:
            dict: Execution result with status and details
        """
        logger.info(f"[TradingHoursMonitorAgent] execute() called with instruction: {instruction}")
        # To be implemented in future tasks
        return {"status": "pending", "message": "execute() not yet implemented"}

    def run(self):
        """Execute the agent's primary task (inherited run interface).

        Returns:
            tuple: (success: bool, results: Dict)
        """
        # Placeholder for future implementation
        logger.info("[TradingHoursMonitorAgent] run() called")
        return (False, {"status": "not implemented"})

    def _get_open_trades(self) -> List[Dict]:
        """Fetch all open trades from OANDA API.

        Returns:
            list: List of open trade dictionaries with keys:
                - id, instrument, initialUnits, currentUnits, openTime
                - pricingStatus, unrealizedPL, takeProfitOnFill, stopLossOnFill
                - clientExtensions (optional)

        Returns empty list if no trades open or on API error.
        """
        try:
            trades = self.oanda_client.get_trades()

            if not trades:
                logger.info("[TradingHoursMonitorAgent] No open trades")
                return []

            # Filter to active trades only (OPEN, TRAILING, AT_BREAKEVEN)
            active_states = ["OPEN", "TRAILING", "AT_BREAKEVEN"]
            active_trades = [t for t in trades if t.get("pricingStatus") in active_states]

            logger.info(f"[TradingHoursMonitorAgent] Found {len(active_trades)} open trades")
            return active_trades

        except Exception as e:
            logger.error(f"[TradingHoursMonitorAgent] Error fetching open trades: {e}")
            return []

    def _check_compliance_status(self, trade: Dict, current_time) -> Dict:
        """Check compliance status of a single trade.

        Args:
            trade (dict): Trade object from OANDA with keys: id, instrument, direction,
                         currentUnits, unrealizedPL, pricingStatus
            current_time: Current UTC time for compliance check

        Returns:
            dict: Compliance status with keys:
                - trade_id (str): The trade ID
                - pair (str): The trading pair (instrument)
                - compliant (bool): True if trade is compliant with trading hours rules
                - close_reason (str or None): Reason trade should be closed (or None if compliant)
                - profit_pips (float): Unrealized profit in pips
                - pricingStatus (str): Trade status (OPEN, TRAILING, AT_BREAKEVEN)
        """
        trade_id = trade.get("id")
        pair = trade.get("instrument")
        pricingStatus = trade.get("pricingStatus")

        # Calculate unrealized profit in pips
        # Standard pip value: 0.0001 for most pairs
        unrealized_pl = trade.get("unrealizedPL", 0.0)
        current_units = trade.get("currentUnits", 1)
        profit_pips = unrealized_pl / (abs(current_units) * 0.0001) if current_units != 0 else 0.0

        # Default: compliant (if TradingHoursManager not available, assume trade is compliant)
        should_close = False
        close_reason = None

        # Check compliance using TradingHoursManager if available
        if self.trading_hours_manager:
            try:
                direction = trade.get("direction", "UNKNOWN")
                should_close, close_reason = self.trading_hours_manager.should_close_trade(
                    now_utc=current_time,
                    profit_pips=profit_pips,
                    trade_direction=direction
                )
            except Exception as e:
                logger.warning(f"[TradingHoursMonitorAgent] Error checking compliance for {trade_id}: {e}")
                should_close = False  # Default to compliant on error

        # Convert should_close to compliant (opposite)
        compliant = not should_close

        result = {
            "trade_id": trade_id,
            "pair": pair,
            "compliant": compliant,
            "close_reason": close_reason if not compliant else None,
            "profit_pips": profit_pips,
            "pricingStatus": pricingStatus
        }

        # Log for audit trail
        if not compliant:
            logger.info(f"[TradingHoursMonitorAgent] Trade {trade_id} ({pair}) non-compliant: {close_reason}")

        return result

    def _enforce_compliance(self, enforcement_time: str = "21:30 Friday") -> Dict:
        """Enforce trading hours compliance by closing non-compliant trades.

        Args:
            enforcement_time (str): Enforcement window descriptor (e.g., "21:30 Friday")

        Returns:
            dict: Enforcement report with keys:
                - report_type (str): Always "trading_hours_enforcement"
                - timestamp (str): ISO8601 timestamp
                - enforcement_time (str): Enforcement window descriptor
                - trades_checked (int): Total trades checked
                - trades_closed (int): Number of trades closed
                - total_pnl (float): Total P&L from closures
                - closed_trades (list): List of closed trade details
                - alert_sent (bool): Whether Pushover alert was sent
                - error (str or None): Error message if enforcement failed
        """
        report = {
            "report_type": "trading_hours_enforcement",
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "enforcement_time": enforcement_time,
            "trades_checked": 0,
            "trades_closed": 0,
            "total_pnl": 0.0,
            "closed_trades": [],
            "alert_sent": False,
            "error": None
        }

        try:
            # Step 1: Fetch all open trades
            open_trades = self._get_open_trades()
            report["trades_checked"] = len(open_trades)

            if not open_trades:
                logger.info(f"[TradingHoursMonitorAgent] Enforcement {enforcement_time}: 0 trades to check")
                return report

            # Step 2: Check compliance for each trade and close non-compliant ones
            current_time = datetime.now(pytz.UTC)
            closed_trades_list = []

            for trade in open_trades:
                compliance = self._check_compliance_status(trade, current_time)

                if not compliance["compliant"]:
                    # Step 3: Close non-compliant trade
                    close_result = self.oanda_client.close_trade(
                        trade_id=trade["id"],
                        reason=f"Trading hours enforcement: {compliance['close_reason']}"
                    )

                    if close_result["success"]:
                        report["trades_closed"] += 1
                        realized_pnl = close_result.get("realized_pnl", 0.0)
                        report["total_pnl"] += realized_pnl

                        # Step 4: Store enforcement audit record
                        try:
                            self.db.execute(
                                """
                                INSERT INTO enforcement_audit
                                (timestamp, trade_id, pair, direction, entry_price, close_price,
                                 realized_pnl, closure_reason, closed_by)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    report["timestamp"],
                                    trade["id"],
                                    trade.get("instrument"),
                                    trade.get("direction"),
                                    None,  # entry_price would come from trade object
                                    None,  # close_price would come from close_result
                                    realized_pnl,
                                    compliance["close_reason"],
                                    "Emy"
                                )
                            )
                        except Exception as db_error:
                            logger.error(f"[TradingHoursMonitorAgent] Database error for trade {trade['id']}: {db_error}")

                        closed_trades_list.append({
                            "trade_id": trade["id"],
                            "pair": trade.get("instrument"),
                            "direction": trade.get("direction"),
                            "realized_pnl": realized_pnl,
                            "closure_reason": compliance["close_reason"]
                        })

                        logger.info(f"[TradingHoursMonitorAgent] Closed trade {trade['id']} ({trade.get('instrument')}): ${realized_pnl:.2f}")
                    else:
                        logger.warning(f"[TradingHoursMonitorAgent] Failed to close trade {trade['id']}: {close_result.get('error')}")

            report["closed_trades"] = closed_trades_list

            # Step 5: Use Claude to analyze closure summary
            if closed_trades_list:
                claude_analysis = None
                try:
                    closure_summary = f"Closed {len(closed_trades_list)} trades. Total P&L: ${report['total_pnl']:.2f}. "
                    closure_summary += ", ".join(
                        [f"{t['pair']}: {'+'if t['realized_pnl'] >= 0 else ''}${t['realized_pnl']:.2f}" for t in closed_trades_list]
                    )

                    claude_response = self.claude_client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=200,
                        messages=[{
                            "role": "user",
                            "content": f"Summarize this trading enforcement: {closure_summary}"
                        }]
                    )
                    claude_analysis = claude_response.content[0].text
                    logger.info(f"[TradingHoursMonitorAgent] Claude analysis: {claude_analysis}")
                except Exception as e:
                    logger.error(f"[TradingHoursMonitorAgent] Claude analysis error: {e}")

                # Step 6: Send Pushover alert
                try:
                    alert_message = f"Trading Hours Enforcement {enforcement_time}: Closed {len(closed_trades_list)} trades. Total P&L: ${report['total_pnl']:.2f}"
                    self._send_pushover_alert("critical", alert_message)
                    report["alert_sent"] = True
                    logger.info(f"[TradingHoursMonitorAgent] Critical alert sent: {alert_message}")
                except Exception as e:
                    logger.error(f"[TradingHoursMonitorAgent] Alert error: {e}")

            # Step 7: Store report in database
            try:
                self.db.execute(
                    """
                    INSERT INTO monitoring_reports
                    (report_type, timestamp, enforcement_action, trades_affected, total_pnl, critical)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report["report_type"],
                        report["timestamp"],
                        True,
                        str(closed_trades_list),
                        report["total_pnl"],
                        report["alert_sent"]
                    )
                )
            except Exception as e:
                logger.error(f"[TradingHoursMonitorAgent] Error storing report: {e}")

            logger.info(f"[TradingHoursMonitorAgent] Enforcement complete: {report['trades_closed']} closed, ${report['total_pnl']:.2f} P&L")
            return report

        except Exception as e:
            logger.error(f"[TradingHoursMonitorAgent] Enforcement error: {e}")
            report["error"] = str(e)
            return report

    def _send_pushover_alert(self, severity: str, message: str) -> None:
        """Send alert via Pushover.

        Args:
            severity (str): Alert severity ("critical", "warning", "info")
            message (str): Alert message content
        """
        try:
            from emy.tools.notification_tool import PushoverNotifier
            notifier = PushoverNotifier()
            # Map severity to priority: critical -> 2, high/warning -> 1, info -> 0
            priority_map = {"critical": 2, "warning": 1, "high": 1, "info": 0}
            priority = priority_map.get(severity, 0)
            notifier.send_alert(message, priority=priority)
        except Exception as e:
            logger.error(f"[TradingHoursMonitorAgent] Failed to send alert: {e}")

    def _monitor_compliance(self) -> Dict:
        """Monitor compliance without closing trades.

        Detects trading hours violations and alerts if critical, but does not take enforcement action.

        Returns:
            dict: Monitoring report with keys:
                - report_type (str): Always "trading_hours_monitoring"
                - timestamp (str): ISO8601 datetime
                - trades_checked (int): Total trades checked
                - violations_detected (int): Count of violations
                - violations (list): Details of non-compliant trades
                - critical (bool): True if violations exist
                - alert_sent (bool): Whether alert was sent
                - error (str or None): Error message if monitoring failed
        """
        import json

        report = {
            "report_type": "trading_hours_monitoring",
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "trades_checked": 0,
            "violations_detected": 0,
            "violations": [],
            "critical": False,
            "alert_sent": False,
            "error": None
        }

        try:
            # Step 1: Fetch all open trades
            open_trades = self._get_open_trades()
            report["trades_checked"] = len(open_trades)

            if not open_trades:
                logger.info(f"[TradingHoursMonitorAgent] Monitoring: 0 trades to monitor")
                return report

            # Step 2: Check compliance for each trade
            current_time = datetime.now(pytz.UTC)
            violations_list = []

            for trade in open_trades:
                compliance = self._check_compliance_status(trade, current_time)

                if not compliance["compliant"]:
                    violations_list.append({
                        "trade_id": compliance["trade_id"],
                        "pair": compliance["pair"],
                        "pricingStatus": compliance["pricingStatus"],
                        "violation_reason": compliance["close_reason"],
                        "profit_pips": compliance["profit_pips"]
                    })

            report["violations"] = violations_list
            report["violations_detected"] = len(violations_list)
            report["critical"] = len(violations_list) > 0

            # Step 3: Alert if critical violations detected (but don't close)
            if report["critical"]:
                try:
                    # Build alert message
                    violation_details = ", ".join([f"{v['pair']}: {v['violation_reason']}" for v in violations_list])
                    alert_message = f"Trading Hours Monitoring: {report['violations_detected']} violations detected ({violation_details})"

                    self._send_pushover_alert("high", alert_message)
                    report["alert_sent"] = True
                    logger.warning(f"[TradingHoursMonitorAgent] Monitoring alert sent: {alert_message}")
                except Exception as e:
                    logger.error(f"[TradingHoursMonitorAgent] Alert error during monitoring: {e}")

            # Step 4: Store report in database
            try:
                self.db.execute(
                    """
                    INSERT INTO monitoring_reports
                    (report_type, timestamp, enforcement_action, findings, critical, data_sources)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report["report_type"],
                        report["timestamp"],
                        False,
                        json.dumps(violations_list),
                        report["critical"],
                        json.dumps({"source": "OANDA", "trades_checked": report["trades_checked"]})
                    )
                )
            except Exception as e:
                logger.error(f"[TradingHoursMonitorAgent] Database error during monitoring: {e}")

            logger.info(f"[TradingHoursMonitorAgent] Monitoring complete: {report['violations_detected']} violations detected")
            return report

        except Exception as e:
            logger.error(f"[TradingHoursMonitorAgent] Monitoring error: {e}")
            report["error"] = str(e)
            return report
