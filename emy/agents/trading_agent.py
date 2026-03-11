"""
TradingAgent - monitors trading systems, logs, and OANDA activity.

Phase 1 TradingAgent monitors:
- Render services (Trade-Alerts, Scalp-Engine, config-api)
- Phase 1 testing logs from Desktop/Test/Manual logs
- OANDA account and open trades
"""

import logging
import os
import time
from typing import Tuple, Dict, Any
from emy.agents.base_agent import EMySubAgent
from emy.tools.api_client import OandaClient, RenderClient
from emy.tools.file_ops import FileOpsTool
from emy.tools.notification_tool import PushoverNotifier

logger = logging.getLogger('TradingAgent')


class TradingAgent(EMySubAgent):
    """Agent for trading system monitoring."""

    def __init__(self, db=None):
        """Initialize TradingAgent.

        Args:
            db: EMyDatabase instance (optional, for testing)
        """
        super().__init__('TradingAgent', 'claude-haiku-4-5-20251001')
        self.oanda_client = OandaClient()
        self.render_client = RenderClient()
        self.notifier = PushoverNotifier()
        self.file_ops = FileOpsTool()

        # Database for risk validation and trade logging
        if db is None:
            from emy.core.database import EMyDatabase
            self.db = EMyDatabase()
        else:
            self.db = db

        # Initialize alert throttle state (60-second window per event type)
        self.last_alert_time = {
            'trade_executed': None,
            'trade_rejected': None,
            'daily_loss_75': None,
            'daily_loss_100': None
        }

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        """Execute trading monitoring tasks."""
        if self.check_disabled():
            self.logger.warning("TradingAgent disabled")
            return (False, {'reason': 'disabled'})

        results = {
            'render_health': self._monitor_render_health(),
            'oanda_account': self._monitor_oanda_account(),
            'phase1_logs': self._monitor_phase1_logs(),
            'timestamp': self._get_timestamp()
        }

        success = all([
            results['render_health'] is not None,
            results['oanda_account'] is not None,
        ])

        # Monitor OANDA account and log to database
        try:
            account = self.oanda_client.get_account_summary()
            if account:
                monitor_result = {
                    'account_equity': account['equity'],
                    'margin_available': account['margin_available'],
                    'unrealized_pl': account['unrealized_pl']
                }
                self.db.log_task(
                    source='trading_agent',
                    domain='trading',
                    task_type='monitor',
                    description='OANDA account monitor'
                )
                self.logger.info(f"[OK] OANDA monitored: Equity ${account['equity']:.2f}")
                results['oanda_monitor'] = monitor_result
        except Exception as e:
            self.logger.error(f"OANDA monitoring error: {e}")
            results['oanda_monitor'] = {'error': str(e)}

        # Update daily limits and check for loss alerts
        self.db.update_daily_limits()
        daily_loss = abs(self.db.get_daily_pnl())  # Absolute value for loss
        max_daily_loss = self.db.get_max_daily_loss()

        # Check for 100% loss (emergency)
        if daily_loss >= max_daily_loss:
            logger.critical(f"Daily loss limit hit: ${daily_loss:.2f} >= ${max_daily_loss:.2f}")

            if self.should_send_alert('daily_loss_100'):
                message = (
                    f"OANDA STOP: Daily loss limit hit (${daily_loss:.2f})\n"
                    f"Trading disabled until market open tomorrow (UTC)"
                )
                self.notifier.send_alert(
                    title="OANDA Trading Disabled",
                    message=message,
                    priority=2,  # Emergency
                    retry=300,   # Retry every 5 minutes
                    expire=3600  # For 60 minutes
                )
                self.record_alert_sent('daily_loss_100')

            # Disable trading
            self._set_disabled(True)

        # Check for 75% loss (warning)
        elif daily_loss >= (max_daily_loss * 0.75):
            logger.warning(f"Daily loss at 75%: ${daily_loss:.2f} / ${max_daily_loss:.2f}")

            if self.should_send_alert('daily_loss_75'):
                message = (
                    f"OANDA Alert: Daily loss 75% (${daily_loss:.2f}/${max_daily_loss:.2f})\n"
                    f"Monitor closely. Further losses will trigger emergency stop."
                )
                self.notifier.send_alert(
                    title="Daily Loss Warning",
                    message=message,
                    priority=1  # High
                )
                self.record_alert_sent('daily_loss_75')

        self.logger.info(f"[RUN] TradingAgent completed: {success}")
        return (success, results)

    def _monitor_render_health(self) -> Dict[str, Any]:
        """Monitor Render services health."""
        services = {
            'trade-alerts': 'ser_XXXX',  # Placeholder - would be configured
            'scalp-engine': 'ser_YYYY',
            'config-api': 'ser_ZZZZ'
        }

        health = {}
        for service_name, service_id in services.items():
            try:
                status = self.render_client.get_service_status(service_id)
                if status:
                    health[service_name] = {
                        'status': status.get('status', 'unknown'),
                        'updated_at': status.get('updatedAt')
                    }
                    self.logger.debug(f"Render {service_name}: {health[service_name]['status']}")
                else:
                    health[service_name] = {'status': 'error', 'reason': 'api_failed'}
            except Exception as e:
                self.logger.error(f"Error checking Render {service_name}: {e}")
                health[service_name] = {'status': 'error', 'reason': str(e)}

        return health

    def _monitor_oanda_account(self) -> Dict[str, Any]:
        """Monitor OANDA account status."""
        try:
            account_data = self.oanda_client.get_account_summary()
            if account_data:
                account = account_data.get('account', {})
                open_trades = self.oanda_client.list_open_trades() or []

                result = {
                    'balance': account.get('balance'),
                    'currency': account.get('currency'),
                    'open_trades_count': len(open_trades),
                    'unrealized_pl': account.get('unrealizedPL'),
                    'status': 'ok'
                }

                self.logger.debug(f"OANDA: {len(open_trades)} open trades, "
                                f"balance {account.get('balance')}")
                return result
            else:
                self.logger.warning("OANDA account summary failed")
                return {'status': 'error', 'reason': 'account_summary_failed'}
        except Exception as e:
            self.logger.error(f"OANDA monitoring error: {e}")
            return {'status': 'error', 'reason': str(e)}

    def _monitor_phase1_logs(self) -> Dict[str, Any]:
        """Monitor Phase 1 testing logs."""
        log_dir = '/c/Users/user/Desktop/Test/Manual logs'  # Windows path

        try:
            log_files = self.file_ops.list_files(log_dir, pattern='*.log', recursive=False)
            if not log_files:
                log_files = self.file_ops.list_files(log_dir, pattern='*.txt', recursive=False)

            latest_logs = {}
            for log_file in log_files[-5:]:  # Last 5 files
                size = self.file_ops.get_file_size(log_file)
                latest_logs[log_file] = {'size': size}

            self.logger.debug(f"Phase 1 logs: {len(log_files)} total files")
            return {
                'status': 'ok',
                'total_files': len(log_files),
                'latest_logs': latest_logs
            }
        except Exception as e:
            self.logger.error(f"Phase 1 log monitoring error: {e}")
            return {'status': 'error', 'reason': str(e)}

    def _validate_trade(self, symbol: str, units: int, direction: str = None) -> Tuple[bool, str]:
        """Validate trade against risk limits.

        Checks:
        1. Position size does not exceed OANDA_MAX_POSITION_SIZE
        2. Daily loss does not exceed OANDA_MAX_DAILY_LOSS_USD
        3. Concurrent open positions do not exceed OANDA_MAX_CONCURRENT_POSITIONS

        Sends Normal priority (0) Pushover alert when trade is rejected.

        Args:
            symbol: Instrument (e.g., 'EUR_USD')
            units: Number of units requested
            direction: 'BUY' or 'SELL' (optional)

        Returns:
            Tuple[bool, str]: (is_valid, reason)
                is_valid=True if all checks pass, reason='OK'
                is_valid=False if any check fails, reason contains rejection reason
        """
        # Get max position from db if available, otherwise from env
        try:
            max_position = self.db.get_max_position_size()
        except (AttributeError, TypeError):
            max_position = int(os.getenv('OANDA_MAX_POSITION_SIZE', '10000'))

        max_daily_loss = float(os.getenv('OANDA_MAX_DAILY_LOSS_USD', '100.0'))
        max_concurrent = int(os.getenv('OANDA_MAX_CONCURRENT_POSITIONS', '5'))

        # Check 1: Position size
        if units > max_position:
            reason = f"Position size {units:,} exceeds limit {max_position:,}"
            self.db.log_trade_rejection(symbol, units, reason)

            # Send alert (check throttle)
            if self.should_send_alert('trade_rejected'):
                message = (
                    f"OANDA: {symbol} {units:,} REJECTED\n"
                    f"Reason: {reason}"
                )
                self.notifier.send_alert(
                    title="Trade Rejected",
                    message=message,
                    priority=0  # Normal
                )
                self.record_alert_sent('trade_rejected')

            return False, reason

        # Check 2: Daily loss
        self.db.update_daily_limits()
        daily_pnl = self.db.get_daily_pnl()
        if daily_pnl < -max_daily_loss:
            reason = f"Daily loss ${abs(daily_pnl):.2f} exceeds limit ${max_daily_loss}"
            self.db.log_trade_rejection(symbol, units, reason)

            # Send alert (check throttle)
            if self.should_send_alert('trade_rejected'):
                message = (
                    f"OANDA: {symbol} {units:,} REJECTED\n"
                    f"Reason: {reason}"
                )
                self.notifier.send_alert(
                    title="Trade Rejected",
                    message=message,
                    priority=0  # Normal
                )
                self.record_alert_sent('trade_rejected')

            return False, reason

        # Check 3: Concurrent positions
        open_count = self.db.get_open_positions_count()
        if open_count >= max_concurrent:
            reason = f"Open positions {open_count} at limit {max_concurrent}"
            self.db.log_trade_rejection(symbol, units, reason)

            # Send alert (check throttle)
            if self.should_send_alert('trade_rejected'):
                message = (
                    f"OANDA: {symbol} {units:,} REJECTED\n"
                    f"Reason: {reason}"
                )
                self.notifier.send_alert(
                    title="Trade Rejected",
                    message=message,
                    priority=0  # Normal
                )
                self.record_alert_sent('trade_rejected')

            return False, reason

        return True, "OK"

    def _execute_trade(self, symbol: str, units: int, direction: str,
                      stop_loss: float, take_profit: float) -> Dict[str, Any]:
        """Execute trade on OANDA and log to database.

        Validates trade against risk limits before execution. If validation
        passes, executes the trade via OANDA API and logs to database.

        Args:
            symbol: Instrument (e.g., 'EUR_USD')
            units: Number of units
            direction: 'BUY' or 'SELL'
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            dict with trade details (trade_id, entry_price, status) or None
        """
        # Validate first
        is_valid, reason = self._validate_trade(symbol, units, direction)
        if not is_valid:
            self.logger.warning(f"[REJECT] {symbol} {direction} {units}: {reason}")
            return None

        # Execute on OANDA
        result = self.oanda_client.execute_trade(symbol, units, direction,
                                                 stop_loss, take_profit)

        if result:
            self.db.log_oanda_trade(
                trade_id=result.get('trade_id'),
                account_id=os.getenv('OANDA_ACCOUNT_ID'),
                symbol=symbol,
                units=units,
                direction=direction,
                entry_price=result.get('entry_price'),
                stop_loss=stop_loss,
                take_profit=take_profit,
                status='OPEN'
            )
            self.logger.info(f"[OK] Trade executed: {symbol} {direction} {units}")

            # Send Pushover alert (check throttle first)
            if self.should_send_alert('trade_executed'):
                entry_price = result.get('price', '?')
                message = (
                    f"OANDA: {symbol} {direction} {units:,} @ {entry_price}\n"
                    f"SL:{stop_loss} TP:{take_profit}"
                )
                self.notifier.send_alert(
                    title="Trade Executed",
                    message=message,
                    priority=0  # Normal
                )
                self.record_alert_sent('trade_executed')

            return result
        else:
            self.logger.error(f"[ERR] Trade execution failed: {symbol} {direction} {units}")
            return None

    def should_send_alert(self, alert_type: str) -> bool:
        """
        Check if alert should be sent based on throttle window

        Args:
            alert_type: One of 'trade_executed', 'trade_rejected', 'daily_loss_75', 'daily_loss_100'

        Returns:
            True if alert should be sent (not in throttle window), False otherwise
        """
        # Check if throttling is disabled (testing)
        if os.getenv('PUSHOVER_NO_THROTTLE', 'false').lower() == 'true':
            return True

        last_time = self.last_alert_time.get(alert_type)
        if last_time is None:
            return True  # First alert of this type

        elapsed = time.time() - last_time
        return elapsed >= 60  # Only send if 60+ seconds passed

    def record_alert_sent(self, alert_type: str) -> None:
        """Record that an alert was sent to update throttle window"""
        self.last_alert_time[alert_type] = time.time()

    def _set_disabled(self, disabled: bool):
        """Set or clear the .emy_disabled kill switch"""
        disabled_file = '.emy_disabled'
        if disabled:
            # Create file to disable trading
            with open(disabled_file, 'w') as f:
                f.write('disabled')
            logger.critical(f"Trading disabled by emergency stop")
        else:
            # Remove file to enable trading
            try:
                os.remove(disabled_file)
                logger.info(f"Trading re-enabled")
            except FileNotFoundError:
                pass

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
