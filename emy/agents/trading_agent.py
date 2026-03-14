"""
TradingAgent - monitors trading systems, logs, and OANDA activity.

Phase 1 TradingAgent monitors:
- Render services (Trade-Alerts, Scalp-Engine, config-api)
- Phase 1 testing logs from Desktop/Test/Manual logs
- OANDA account and open trades
"""

import logging
import os
from typing import Tuple, Dict, Any
from emy.agents.base_agent import EMySubAgent
from emy.tools.api_client import OandaClient, RenderClient
from emy.tools.file_ops import FileOpsTool
from emy.tools.notification_tool import PushoverNotifier
from emy.core.alert_manager import AlertManager

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
            self.db.initialize_schema()
        else:
            self.db = db

        # Initialize AlertManager for centralized throttling and persistence
        self.alert_manager = AlertManager(notifier=self.notifier, db=self.db)

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute trading agent.

        Analyzes market conditions and generates trading signals using Claude.
        Also monitors OANDA account for loss alerts.

        Returns:
            (True, {"analysis": claude_analysis, "signals": [...], ...})
        """
        try:
            if self.check_disabled():
                self.logger.warning("TradingAgent disabled")
                return (False, {'reason': 'disabled'})

            # Update daily limits and check for loss alerts (critical monitoring)
            self.db.update_daily_limits()
            daily_loss = abs(self.db.get_daily_pnl())  # Absolute value for loss
            max_daily_loss = self.db.get_max_daily_loss()

            # Check for 100% loss (emergency)
            if daily_loss >= max_daily_loss:
                logger.critical(f"Daily loss limit hit: ${daily_loss:.2f} >= ${max_daily_loss:.2f}")

                message = (
                    f"OANDA STOP: Daily loss limit hit (${daily_loss:.2f})\n"
                    f"Trading disabled until market open tomorrow (UTC)"
                )
                self.alert_manager.send(
                    'daily_loss_100',
                    title="OANDA Trading Disabled",
                    message=message,
                    priority=2  # Emergency
                )

                # Disable trading
                self._set_disabled(True)

            # Check for 75% loss (warning)
            elif daily_loss >= (max_daily_loss * 0.75):
                logger.warning(f"Daily loss at 75%: ${daily_loss:.2f} / ${max_daily_loss:.2f}")

                message = (
                    f"OANDA Alert: Daily loss 75% (${daily_loss:.2f}/${max_daily_loss:.2f})\n"
                    f"Monitor closely. Further losses will trigger emergency stop."
                )
                self.alert_manager.send(
                    'daily_loss_75',
                    title="Daily Loss Warning",
                    message=message,
                    priority=1  # High
                )

            # Get market context
            market_context = self._get_market_context()

            # Build analysis prompt
            prompt = self._build_analysis_prompt(market_context)

            # Get Claude analysis
            analysis = self._call_claude(prompt, max_tokens=1024)

            # Parse signals from analysis
            signals = self._extract_signals_from_analysis(analysis)

            result = {
                "analysis": analysis,
                "signals": signals,
                "market_context": market_context,
                "timestamp": self._get_timestamp(),
                "agent": self.agent_name
            }

            self.logger.info(f"Trading agent generated analysis ({len(analysis)} chars)")
            return (True, result)

        except Exception as e:
            error_msg = f"TradingAgent error: {e}"
            self.logger.error(error_msg)
            return (False, {"error": error_msg})

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

            # Send alert via AlertManager
            message = (
                f"OANDA: {symbol} {units:,} REJECTED\n"
                f"Reason: {reason}"
            )
            self.alert_manager.send(
                'trade_rejected',
                title="Trade Rejected",
                message=message,
                priority=0  # Normal
            )

            return False, reason

        # Check 2: Daily loss
        self.db.update_daily_limits()
        daily_pnl = self.db.get_daily_pnl()
        if daily_pnl < -max_daily_loss:
            reason = f"Daily loss ${abs(daily_pnl):.2f} exceeds limit ${max_daily_loss}"
            self.db.log_trade_rejection(symbol, units, reason)

            # Send alert via AlertManager
            message = (
                f"OANDA: {symbol} {units:,} REJECTED\n"
                f"Reason: {reason}"
            )
            self.alert_manager.send(
                'trade_rejected',
                title="Trade Rejected",
                message=message,
                priority=0  # Normal
            )

            return False, reason

        # Check 3: Concurrent positions
        open_count = self.db.get_open_positions_count()
        if open_count >= max_concurrent:
            reason = f"Open positions {open_count} at limit {max_concurrent}"
            self.db.log_trade_rejection(symbol, units, reason)

            # Send alert via AlertManager
            message = (
                f"OANDA: {symbol} {units:,} REJECTED\n"
                f"Reason: {reason}"
            )
            self.alert_manager.send(
                'trade_rejected',
                title="Trade Rejected",
                message=message,
                priority=0  # Normal
            )

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

            # Send alert via AlertManager
            entry_price = result.get('price', '?')
            message = (
                f"OANDA: {symbol} {direction} {units:,} @ {entry_price}\n"
                f"SL:{stop_loss} TP:{take_profit}"
            )
            self.alert_manager.send(
                'trade_executed',
                title="Trade Executed",
                message=message,
                priority=0  # Normal
            )

            return result
        else:
            self.logger.error(f"[ERR] Trade execution failed: {symbol} {direction} {units}")
            return None


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

    def _get_market_context(self) -> str:
        """Get current market context (placeholder for Phase 3 OANDA integration)."""
        return "Current market state: Ready for Phase 3 OANDA API integration..."

    def _build_analysis_prompt(self, market_context: str) -> str:
        """Build prompt for market analysis."""
        prompt = f"""You are a professional forex trader analyzing markets.

Market Context:
{market_context}

Provide:
1. Market trend analysis (50 words)
2. Key support/resistance levels
3. Trading signals (BUY/SELL/HOLD for major pairs)
4. Risk assessment

Format each signal as: PAIR: SIGNAL (confidence %)"""

        return prompt

    def _extract_signals_from_analysis(self, analysis: str) -> list:
        """Extract trading signals from Claude analysis."""
        # Simple extraction: look for SIGNAL patterns
        signals = []
        for line in analysis.split('\n'):
            if 'BUY' in line or 'SELL' in line or 'HOLD' in line:
                signals.append(line.strip())
        return signals if signals else ["Analysis available: see full response"]

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
