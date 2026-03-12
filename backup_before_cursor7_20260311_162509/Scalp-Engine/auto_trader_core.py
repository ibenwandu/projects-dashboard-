"""
Auto-Trader Core System
Integrates Trade-Alerts intelligence with OANDA execution
"""

import os
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pytz

# OANDA API imports
from oandapyV20.endpoints import orders, trades, accounts
from oandapyV20.exceptions import V20Error

# Execution mode enforcer (stable opp ID from shared module so UI and engine keys match)
from src.execution.opportunity_id import get_stable_opportunity_id
from src.execution.execution_mode_enforcer import (
    ExecutionModeEnforcer,
    ExecutionDirective,
    ExecutionMode as EnforcerExecutionMode,
    get_stable_opp_id,
)

# Trading hours (weekend / Friday 21:30 close)
try:
    from trading_hours_manager import TradingHoursManager as _TradingHoursManager
except ImportError:
    _TradingHoursManager = None  # type: ignore[misc, assignment]

# For MACD calculation
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

def round_price_for_oanda(price: float, pair: str) -> float:
    """
    Round price to OANDA's required precision
    
    OANDA requires:
    - 5 decimal places for most pairs (EUR/USD, USD/CHF, etc.) - pip = 0.00001
    - 3 decimal places for JPY pairs (USD/JPY, etc.) - pip = 0.001
    
    Args:
        price: Price to round
        pair: Currency pair (e.g., "EUR/USD" or "USD_JPY")
        
    Returns:
        Rounded price with correct precision
    """
    if not price or price <= 0:
        return price
    
    # Check if pair contains JPY
    if 'JPY' in pair.upper():
        # JPY pairs: 3 decimal places
        return round(price, 3)
    else:
        # Most pairs: 5 decimal places
        return round(price, 5)

class TradeState(Enum):
    """Trade lifecycle states"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    AT_BREAKEVEN = "AT_BREAKEVEN"
    TRAILING = "TRAILING"
    CLOSED_WIN = "CLOSED_WIN"
    CLOSED_LOSS = "CLOSED_LOSS"
    CLOSED_MANUAL = "CLOSED_MANUAL"

class TradingMode(Enum):
    """Trading modes"""
    MANUAL = "MANUAL"       # Alerts only, no execution
    SEMI_AUTO = "SEMI_AUTO" # Execute only trades explicitly enabled in Fisher/opportunities tab
    AUTO = "AUTO"           # Execute automatically

class StopLossType(Enum):
    """Stop loss types"""
    FIXED = "FIXED"           # Standard fixed SL
    TRAILING = "TRAILING"     # Immediate trailing
    BE_TO_TRAILING = "BE_TO_TRAILING"  # Fixed → BE → Trailing
    ATR_TRAILING = "ATR_TRAILING"        # ATR Trailing: ATR-based dynamic trailing
    AI_TRAILING = "ATR_TRAILING"         # DEPRECATED: Backward compatibility alias for ATR_TRAILING (live trades may use this)
    MACD_CROSSOVER = "MACD_CROSSOVER"  # Close on MACD reverse crossover
    DMI_CROSSOVER = "DMI_CROSSOVER"  # Close on +DI/-DI reverse crossover
    STRUCTURE_ATR_STAGED = "STRUCTURE_ATR_STAGED"  # FT-DMI-EMA: Structure+ATR at entry, BE +1R, partial +2R, trail +3R to 1H EMA 26
    STRUCTURE_ATR = "STRUCTURE_ATR"  # ATR + structure for LLM/Fisher: structure+ATR at entry, BE at +1R, then trail to 1H EMA 26 (no Phase 3 exits)

    @classmethod
    def from_string(cls, value: str):
        """Convert string to StopLossType, handling backward compatibility

        Supports:
        - Standard values: "FIXED", "TRAILING", "BE_TO_TRAILING", etc.
        - Deprecated names: "AI_TRAILING" → "ATR_TRAILING"
        """
        if not isinstance(value, str):
            return value

        # Handle deprecated name
        if value == "AI_TRAILING":
            return cls.ATR_TRAILING

        # Handle standard values
        try:
            return cls(value)
        except ValueError:
            # Try by name as fallback
            try:
                return cls[value]
            except KeyError:
                raise ValueError(f"'{value}' is not a valid StopLossType")

class ExecutionMode(Enum):
    """Trade execution modes"""
    MARKET = "MARKET"  # Execute immediately at current market price
    RECOMMENDED = "RECOMMENDED"  # Place LIMIT/STOP orders at recommended entry price
    MACD_CROSSOVER = "MACD_CROSSOVER"  # Wait for MACD crossover signal before executing
    HYBRID = "HYBRID"  # Place pending order AND watch for MACD (whichever triggers first)

@dataclass
class TradeConfig:
    """Configuration for auto-trader"""
    trading_mode: TradingMode = TradingMode.MANUAL
    max_open_trades: int = 5
    stop_loss_type: StopLossType = StopLossType.BE_TO_TRAILING
    execution_mode: ExecutionMode = ExecutionMode.RECOMMENDED  # MARKET or RECOMMENDED price execution

    # Auto mode: which opportunity sources may open trades (only when trading_mode == AUTO)
    auto_trade_llm: bool = True
    auto_trade_fisher: bool = True
    auto_trade_ft_dmi_ema: bool = True
    auto_trade_dmi_ema: bool = True

    # Consensus filters
    min_consensus_level: int = 2  # 1=any, 2=two agree, 3=all agree
    required_llms: List[str] = None  # List of required LLMs (e.g., ['gemini'] or ['chatgpt', 'gemini'])
    
    # Position sizing
    base_position_size: float = 1000  # Base units
    consensus_multiplier: Dict[int, float] = None  # Size multiplier by consensus
    
    # Trailing stop configuration
    hard_trailing_pips: Optional[float] = 20.0  # For TRAILING mode
    be_trigger_pips: float = 0.0  # Pips needed to trigger BE (0 = at entry)
    be_min_pips: float = 50.0  # Research: move SL to breakeven when profit >= this (default 50)
    trailing_activation_min_pips: float = 100.0  # Research: activate trailing only when profit >= this (default 100)
    atr_multiplier_low_vol: float = 1.5  # For ATR Trailing in low vol
    atr_multiplier_high_vol: float = 3.0  # For ATR Trailing in high vol
    
    # Risk limits
    max_account_risk_pct: float = 10.0  # Max % of account at risk
    max_daily_loss: float = 500.0  # Max daily loss in account currency
    max_daily_loss_pct: Optional[float] = None  # If set, daily loss limit as % of account (e.g. 2.0)
    # Position sizing from research (Phase 1): risk-based formula
    trading_phase: str = 'phase_1'  # phase_1=0.5%, phase_2=1%, phase_3=2%
    risk_percent_per_trade: Optional[float] = None  # Override: e.g. 0.5 for 0.5%; None = use trading_phase
    account_balance_override: Optional[float] = None  # If set, use for risk calc; else use OANDA balance
    consecutive_losses_max: int = 5  # Circuit breaker: no new opens after this many consecutive losses
    # Phase 3 exit strategy (optional)
    half_and_run_enabled: bool = False  # If True: close 50% at 1.5R, trail remainder
    half_and_run_r_multiple: float = 1.5  # R-multiple for first TP (default 1.5× risk)
    max_hold_seconds: Optional[float] = None  # If set, close trade when hold time exceeds this (e.g. 4h = 14400)
    
    # MACD Crossover configuration
    macd_timeframe: str = "H1"  # Timeframe for MACD entry calculation (default: 1 hour)
    macd_sl_timeframe: Optional[str] = None  # Timeframe for MACD stop loss (None = use macd_timeframe)
    macd_fast_period: int = 12  # Fast EMA period
    macd_slow_period: int = 26  # Slow EMA period
    macd_signal_period: int = 9  # Signal line period
    macd_close_on_reverse: bool = True  # Close trades when MACD crosses in opposite direction
    
    # DMI stop loss (when stop_loss_type = DMI_CROSSOVER)
    dmi_sl_timeframe: Optional[str] = None  # H1 or M15; None = H1
    
    def __post_init__(self):
        if self.consensus_multiplier is None:
            self.consensus_multiplier = {
                1: 0.5,  # Single LLM = 50% position
                2: 1.0,  # Two agree = 100% position
                3: 1.5,  # Three agree = 150% position
                4: 2.0   # All four base LLMs agree = 200% position
            }
        # Ensure required_llms is always a non-empty list
        if self.required_llms is None or (isinstance(self.required_llms, list) and len(self.required_llms) == 0):
            self.required_llms = ['gemini']  # Default: require Gemini

@dataclass
class ManagedTrade:
    """Represents a managed trade"""
    # Identification
    trade_id: Optional[str] = None  # OANDA trade ID
    opportunity_id: str = ""        # From market_state
    
    # Trade details
    pair: str = ""
    direction: str = ""  # LONG/SHORT
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: Optional[float] = None
    order_type: str = "LIMIT"  # LIMIT or STOP order type
    
    # Position sizing
    units: float = 0.0
    position_size_multiplier: float = 1.0
    
    # State tracking
    state: TradeState = TradeState.PENDING
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Stop loss management
    current_sl: float = 0.0
    sl_type: StopLossType = StopLossType.FIXED
    trailing_distance: Optional[float] = None
    
    # Intelligence context
    consensus_level: int = 1
    llm_sources: List[str] = None
    rationale: str = ""
    confidence: float = 0.5
    
    # Performance tracking
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: Optional[float] = None
    oanda_unrealized_pl: float = 0.0  # OANDA's actual P/L in account currency
    
    # FT-DMI-EMA staged profit (STRUCTURE_ATR_STAGED)
    opportunity_source: str = ""  # e.g. "FT_DMI_EMA"
    initial_stop_loss: Optional[float] = None  # For R-multiple calculation
    breakeven_applied: bool = False
    partial_profit_taken: bool = False
    trailing_active: bool = False
    
    def __post_init__(self):
        if self.llm_sources is None:
            self.llm_sources = []
        if self.current_sl == 0.0:
            self.current_sl = self.stop_loss


def _is_connection_error(e: Exception) -> bool:
    """True if exception is a transient connection/network error worth retrying."""
    if e is None:
        return False
    msg = str(e).lower()
    if "connection aborted" in msg or "remotedisconnected" in msg or "remote end closed" in msg:
        return True
    try:
        import requests
        if isinstance(e, requests.exceptions.ConnectionError):
            return True
    except ImportError:
        pass
    return False


class TradeExecutor:
    """Handles OANDA trade execution"""
    
    # Retries for transient connection errors (OANDA/network)
    REQUEST_RETRIES = 3
    REQUEST_RETRY_DELAY_SEC = 2
    
    def __init__(self, oanda_client, account_id: str):
        self.client = oanda_client
        self.account_id = account_id
        self.logger = self._setup_logger()
        self._last_reject_reason: Optional[str] = None  # for "Trade not opened" reason (e.g. excluded_pair)
    
    def _request_with_retry(self, r, label: str = "request"):
        """Call client.request(r) with retries on connection errors and 502/5xx (cursor6 §5.5)."""
        last_e = None
        for attempt in range(1, self.REQUEST_RETRIES + 1):
            try:
                self.client.request(r)
                return
            except V20Error as e:
                last_e = e
                code = getattr(e, "code", None)
                msg = getattr(e, "msg", str(e)) or ""
                # cursor6 §5.5: 502/5xx — do not log raw HTML; retry with backoff
                if code in (502, 503, 504) or (isinstance(code, int) and code >= 500):
                    if attempt < self.REQUEST_RETRIES:
                        msg_safe = msg[:100] + "..." if len(str(msg)) > 100 or "<" in str(msg) else str(msg)
                        self.logger.warning(
                            f"⚠️ OANDA {label}: {code} bad gateway / server error — retry later (attempt {attempt}/{self.REQUEST_RETRIES}). {msg_safe}"
                        )
                        delay = self.REQUEST_RETRY_DELAY_SEC * attempt
                        time.sleep(delay)
                    else:
                        raise
                else:
                    raise
            except Exception as e:
                last_e = e
                if _is_connection_error(e) and attempt < self.REQUEST_RETRIES:
                    self.logger.warning(
                        f"⚠️ OANDA {label} connection error (attempt {attempt}/{self.REQUEST_RETRIES}): {e}. Retrying in {self.REQUEST_RETRY_DELAY_SEC}s..."
                    )
                    time.sleep(self.REQUEST_RETRY_DELAY_SEC)
                else:
                    raise
        if last_e is not None:
            raise last_e

    def request(self, r, label: str = "request"):
        """Public API: run OANDA request with retry (for use by PositionManager etc.)."""
        self._request_with_retry(r, label)
    
    def _setup_logger(self):
        import logging
        logger = logging.getLogger('TradeExecutor')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def open_trade(self, trade: ManagedTrade) -> Optional[str]:
        """
        Open a trade on OANDA using MARKET, LIMIT, or STOP order
        Returns: trade_id if successful, None otherwise
        """
        # Broker exclude list at placement only (consol-recommend2 Phase 2.2): skip + log; do not filter market state
        excluded_raw = os.getenv('EXCLUDED_PAIRS', '').strip()
        if excluded_raw:
            excluded_set = {p.strip().replace('_', '/').upper() for p in excluded_raw.split(',') if p.strip()}
            pair_norm = (trade.pair or '').strip().replace('_', '/').upper()
            if pair_norm and pair_norm in excluded_set:
                self._last_reject_reason = "excluded_pair"
                self.logger.info(f"Pair not tradeable on broker: {trade.pair} (EXCLUDED_PAIRS); skipping placement")
                return None
        self._last_reject_reason = None
        try:
            # Prepare order request
            units = int(trade.units) if trade.direction in ["LONG", "BUY"] else -int(trade.units)
            order_type = getattr(trade, 'order_type', 'LIMIT')
            entry_price = trade.entry_price
            pair_upper = (trade.pair or "").upper()

            # JPY price sanity check — applies to ALL order types (improvementplan Fix 3; consol-recommend4 Phase 1.1)
            # JPY pairs trade in 15x.xxx; entry must not be wrongly scaled (e.g. 1.56 instead of 156.xxx)
            if "JPY" in pair_upper and entry_price > 0 and entry_price < 10:
                if trade.take_profit and trade.take_profit > 10:
                    entry_price = entry_price * 100.0
                    self.logger.warning(
                        f"JPY price auto-corrected: {trade.pair} entry scaled to {entry_price}"
                    )
                else:
                    self._last_reject_reason = "validation_failed"
                    self.logger.error(
                        f"JPY price sanity check failed: {trade.pair} entry={entry_price} (expected 100+). Refusing to send order."
                    )
                    return None
            if "JPY" in pair_upper and entry_price <= 0:
                self._last_reject_reason = "validation_failed"
                self.logger.error(f"JPY pair {trade.pair}: invalid entry price {entry_price}. Refusing to send order.")
                return None

            entry_price = round_price_for_oanda(entry_price, trade.pair)
            
            # Build order request based on order type
            if order_type == "MARKET":
                # MARKET order: Execute immediately at current market price
                order_request = {
                    "order": {
                        "type": "MARKET",
                        "instrument": trade.pair,
                        "units": str(units),
                        "timeInForce": "FOK",  # Fill Or Kill - execute immediately or cancel
                        "positionFill": "DEFAULT"
                    }
                }
            elif order_type == "STOP":
                # STOP order: triggers when price reaches entry_price from the opposite direction
                # For LONG: triggers when price rises to entry_price
                # For SHORT: triggers when price falls to entry_price
                order_request = {
                    "order": {
                        "type": "MARKET_IF_TOUCHED",  # OANDA's stop order type
                        "instrument": trade.pair,
                        "units": str(units),
                        "price": str(entry_price),
                        "timeInForce": "GTC",  # Good Till Cancelled
                        "positionFill": "DEFAULT"
                    }
                }
            else:
                # LIMIT order: executes at or better than entry_price
                # For LONG: executes at or below entry_price
                # For SHORT: executes at or above entry_price
                order_request = {
                    "order": {
                        "type": "LIMIT",
                        "instrument": trade.pair,
                        "units": str(units),
                        "price": str(entry_price),
                        "timeInForce": "GTC",  # Good Till Cancelled
                        "positionFill": "DEFAULT"
                    }
                }
            
            # Add stop loss (only if valid)
            if trade.sl_type == StopLossType.TRAILING:
                # Immediate trailing stop (requires trailing_distance)
                if trade.trailing_distance and trade.trailing_distance > 0:
                    pip_size = 0.01 if "JPY" in trade.pair else 0.0001
                    distance = trade.trailing_distance * pip_size
                    order_request["order"]["trailingStopLossOnFill"] = {
                        "distance": str(distance)
                    }
                else:
                    self.logger.warning(
                        f"⚠️ No trailing distance for {trade.pair} - order will be placed without stop loss"
                    )
            else:
                # Fixed stop loss (will convert to trailing later if needed)
                # Only add stop loss if it's valid (not None, not 0, not NaN)
                if trade.stop_loss and trade.stop_loss > 0:
                    # Round stop loss to OANDA precision
                    rounded_sl = round_price_for_oanda(trade.stop_loss, trade.pair)
                    order_request["order"]["stopLossOnFill"] = {
                        "price": str(rounded_sl)
                    }
                else:
                    self.logger.warning(
                        f"⚠️ No valid stop loss for {trade.pair} (stop_loss={trade.stop_loss}) - "
                        f"order will be placed without stop loss"
                    )
            
            # Add take profit if specified
            if trade.take_profit:
                # Round take profit to OANDA precision
                rounded_tp = round_price_for_oanda(trade.take_profit, trade.pair)
                order_request["order"]["takeProfitOnFill"] = {
                    "price": str(rounded_tp)
                }
            
            # Execute order using OANDA v20 API pattern
            # Create order endpoint with account ID and order data
            r = orders.OrderCreate(accountID=self.account_id, data=order_request)
            
            try:
                self._request_with_retry(r, "open_trade")
                response = r.response
                
                # Check response based on order type
                # MARKET orders should fill immediately, LIMIT/STOP orders may be pending
                if 'orderFillTransaction' in response:
                    # Trade was opened immediately (order filled - common for MARKET orders)
                    trade_id = response['orderFillTransaction'].get('tradeOpened', {}).get('tradeID')
                    if trade_id:
                        fill_price = response['orderFillTransaction'].get('price', trade.entry_price)
                        self.logger.info(
                            f"✅ Opened trade {trade_id}: {trade.pair} {trade.direction} "
                            f"{abs(units)} units @ {fill_price} (filled immediately)"
                        )
                        return trade_id
                elif 'orderCreateTransaction' in response:
                    # Order was created (pending order - for LIMIT/STOP orders)
                    order_id = response['orderCreateTransaction'].get('id')
                    self.logger.info(
                        f"✅ Created {order_type} order {order_id}: {trade.pair} {trade.direction} "
                        f"{abs(units)} units @ {entry_price} (pending fill)"
                    )
                    # Return order ID (will be converted to trade ID when filled)
                    return order_id
                
                # If we get here, response doesn't match expected format
                self._last_reject_reason = "oanda_reject"
                self.logger.error(f"❌ Unexpected response format: {response}")
                return None
                
            except V20Error as e:
                # OANDA API error - request failed
                self._last_reject_reason = "oanda_reject"
                error_msg = getattr(e, 'msg', str(e))
                self.logger.error(f"❌ OANDA API error opening trade: {error_msg}")
                return None

        except Exception as e:
            self._last_reject_reason = "oanda_reject"
            self.logger.error(f"❌ Error opening trade: {e}", exc_info=True)
            return None
    
    def cancel_order(self, order_id: str, reason: str = "Manual cancel") -> bool:
        """Cancel a pending order. Returns False if broker rejected cancel (ORDER_CANCEL_REJECT); do not assume cancelled (consol-recommend2 Phase 3.1)."""
        try:
            # Use OANDA v20 API pattern
            r = orders.OrderCancel(accountID=self.account_id, orderID=order_id)

            try:
                self._request_with_retry(r, "cancel_order")
                # ORDER_CANCEL_REJECT: broker rejected cancel (e.g. order already filled); treat as still active (Phase 3.1)
                resp = getattr(r, 'response', None) or {}
                rej = resp.get('orderCancelRejectTransaction')
                txn = resp.get('orderCancelTransaction') or {}
                txn_type = (rej or txn).get('type') if (rej or txn) else None
                if rej or txn_type == 'ORDER_CANCEL_REJECT':
                    self.logger.warning(
                        f"⚠️ ORDER_CANCEL_REJECT for order {order_id} - broker rejected cancel; treating order as still active/filled"
                    )
                    return False
                self.logger.info(f"✅ Cancelled order {order_id}: {reason}")
                return True
            except V20Error as e:
                # Order already gone on OANDA (filled, cancelled, or never existed) -> treat as success so caller removes from state
                error_msg = getattr(e, 'msg', str(e))
                error_code = getattr(e, 'code', None)
                is_order_gone = (
                    error_code == 404
                    or (isinstance(error_msg, str) and 'ORDER_DOESNT_EXIST' in error_msg.upper())
                    or (isinstance(error_msg, str) and "order doesn't exist" in error_msg.lower())
                )
                if is_order_gone:
                    self.logger.info(
                        f"ℹ️ Order {order_id} already gone on OANDA (ORDER_DOESNT_EXIST or 404) - treat as cancelled"
                    )
                    return True
                self.logger.error(f"❌ OANDA API error cancelling order {order_id}: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error cancelling order {order_id}: {e}", exc_info=True)
            return False
    
    def close_trade(self, trade_id: str, reason: str = "Manual close") -> bool:
        """Close a trade"""
        try:
            # Use OANDA v20 API pattern
            r = trades.TradeClose(accountID=self.account_id, tradeID=trade_id)
            try:
                self._request_with_retry(r, "close_trade")
                self.logger.info(f"✅ Closed trade {trade_id}: {reason}")
                return True
            except V20Error as e:
                # OANDA API error - request failed
                error_msg = getattr(e, 'msg', str(e))
                self.logger.error(f"❌ OANDA API error closing trade {trade_id}: {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error closing trade {trade_id}: {e}", exc_info=True)
            return False
    
    def close_trade_partial(self, trade_id: str, units_to_close: int, is_long: bool, pair: str, reason: str = "Partial profit") -> bool:
        """Close part of a trade (units_to_close is positive; sign for OANDA: + for long, - for short)."""
        try:
            units_param = str(units_to_close) if is_long else str(-int(units_to_close))
            data = {"units": units_param}
            r = trades.TradeClose(accountID=self.account_id, tradeID=trade_id, data=data)
            try:
                self._request_with_retry(r, "close_trade_partial")
                self.logger.info(f"✅ Partially closed trade {trade_id}: {units_to_close} units ({reason})")
                return True
            except V20Error as e:
                error_msg = getattr(e, 'msg', str(e))
                self.logger.error(f"❌ OANDA API error partial close trade {trade_id}: {error_msg}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Error partial close trade {trade_id}: {e}", exc_info=True)
            return False
    
    def update_stop_loss(self, trade_id: str, new_sl: float, pair: str) -> bool:
        """Update stop loss to fixed price via OrderCreate (StopLossOrder).
        TradeClientExtensions does not update actual SL on OANDA (gemini-suggestions1, cursor5 §5.4).
        """
        try:
            rounded_sl = round_price_for_oanda(new_sl, pair)

            # Cancel existing stop loss order so we can attach a new one
            try:
                from oandapyV20.endpoints.trades import TradeDetails
                r_td = TradeDetails(accountID=self.account_id, tradeID=trade_id)
                self._request_with_retry(r_td, "trade_details_for_sl_update")
                trade_detail = r_td.response.get("trade", {})
                sl_order_id = (trade_detail.get("stopLossOrder") or {}).get("id")
                if sl_order_id:
                    self.cancel_order(sl_order_id, "Replace with new SL price")
            except Exception as cancel_e:
                self.logger.debug(f"Could not cancel existing SL order before update (non-fatal): {cancel_e}")

            order_body = {
                "order": {
                    "type": "STOP_LOSS",
                    "tradeID": str(trade_id),
                    "price": str(rounded_sl),
                    "timeInForce": "GTC",
                }
            }
            r = orders.OrderCreate(accountID=self.account_id, data=order_body)

            try:
                self._request_with_retry(r, "update_stop_loss")
                self.logger.info(f"✅ Updated SL for trade {trade_id} to {new_sl}")
                return True
            except V20Error as e:
                error_msg = getattr(e, 'msg', str(e))
                self.logger.error(f"❌ OANDA API error updating SL for trade {trade_id}: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error updating SL: {e}", exc_info=True)
            return False
    
    def convert_to_trailing_stop(self, trade_id: str, distance_pips: float, pair: str) -> bool:
        """Convert fixed SL to trailing stop via OrderCreate (TrailingStopLossOrder).
        TradeClientExtensions is for metadata only and does not update SL/trailing on OANDA (gemini-suggestions1, cursor5 §5.4).
        cursor6 §5.2: Check before create; if trailing already exists skip; on ALREADY_EXISTS treat as success.
        Fix: Create trailing first; only cancel fixed SL if OANDA rejects (trade already has stop loss).
        This avoids leaving the trade with no SL if trailing creation fails after we cancelled.
        """
        try:
            pip_size = 0.01 if "JPY" in pair else 0.0001
            distance = distance_pips * pip_size

            # cursor6 §5.2: Check if trade already has a trailing stop — skip creation to avoid TRAILING_STOP_LOSS_ORDER_ALREADY_EXISTS
            try:
                from oandapyV20.endpoints.trades import TradeDetails
                r_td = TradeDetails(accountID=self.account_id, tradeID=trade_id)
                self._request_with_retry(r_td, "trade_details_for_trailing")
                trade_detail = r_td.response.get("trade", {})
                if trade_detail.get("trailingStopLossOrder") or trade_detail.get("trailingStopLossOrderID"):
                    self.logger.debug(
                        f"Trailing stop already exists for trade_id {trade_id}, skipping"
                    )
                    return True
                sl_order_id = (trade_detail.get("stopLossOrder") or {}).get("id")
            except Exception as fetch_e:
                self.logger.debug(f"Could not fetch trade details for trailing (non-fatal): {fetch_e}")
                sl_order_id = None

            # OANDA v20: create TrailingStopLoss order via OrderCreate.
            # Try create first so we never leave the trade without protection (cancel-then-create could leave no SL if create fails).
            order_body = {
                "order": {
                    "type": "TRAILING_STOP_LOSS",
                    "tradeID": str(trade_id),
                    "distance": str(round(distance, 10)),
                    "timeInForce": "GTC",
                }
            }
            r = orders.OrderCreate(accountID=self.account_id, data=order_body)

            try:
                self._request_with_retry(r, "convert_to_trailing_stop")
                self.logger.info(
                    f"🎯 Converted to trailing stop for trade {trade_id}: "
                    f"{distance_pips} pips"
                )
                return True
            except V20Error as e:
                error_msg = getattr(e, 'msg', str(e)) or ""
                err_upper = str(error_msg).upper()
                # cursor6 §5.2: ALREADY_EXISTS means trailing is already on — treat as success
                if "ALREADY_EXISTS" in err_upper:
                    self.logger.info(
                        f"Trailing stop already exists for trade_id {trade_id} (OANDA ALREADY_EXISTS) — treating as success"
                    )
                    return True
                # Trade already has a stop loss — we must cancel it first, then retry create (so we don't leave trade with no SL until create succeeds)
                if ("STOP_LOSS" in err_upper and "ALREADY" in err_upper) or "ALREADY HAS" in err_upper or "already has a stop" in str(error_msg).lower():
                    if sl_order_id:
                        if self.cancel_order(sl_order_id, "Replace with trailing stop"):
                            r_retry = orders.OrderCreate(accountID=self.account_id, data=order_body)
                            try:
                                self._request_with_retry(r_retry, "convert_to_trailing_stop")
                                self.logger.info(
                                    f"🎯 Converted to trailing stop for trade {trade_id}: {distance_pips} pips (after cancelling fixed SL)"
                                )
                                return True
                            except V20Error as e2:
                                msg_safe = (str(getattr(e2, 'msg', str(e2)))[:100] + "...") if len(str(e2)) > 100 else str(getattr(e2, 'msg', str(e2)))
                                self.logger.error(f"❌ OANDA API error on retry after cancel: {msg_safe}")
                                return False
                    # Could not cancel or no sl_order_id — do not leave trade without SL
                    self.logger.warning(
                        f"⚠️ Could not replace fixed SL with trailing for trade {trade_id} (trade already has stop loss); keeping fixed SL"
                    )
                    return False
                msg_safe = (str(error_msg)[:100] + "...") if len(str(error_msg)) > 100 or "<" in str(error_msg) else str(error_msg)
                self.logger.error(f"❌ OANDA API error converting to trailing stop for trade {trade_id}: {msg_safe}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error converting to trailing: {e}", exc_info=True)
            return False
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions from OANDA (with retry on connection errors)"""
        try:
            from oandapyV20.endpoints.trades import OpenTrades
            r = OpenTrades(accountID=self.account_id)
            try:
                self._request_with_retry(r, "get_open_positions")
                return r.response.get('trades', [])
            except V20Error as e:
                error_msg = getattr(e, 'msg', str(e))
                self.logger.error(f"❌ OANDA API error fetching positions: {error_msg}")
                return []
        except Exception as e:
            self.logger.error(f"❌ Error fetching positions: {e}", exc_info=True)
            return []

    def get_pending_orders(self) -> List[Dict]:
        """Get all pending (unfilled) orders from OANDA. Used to block duplicate (pair, direction) and for sync."""
        try:
            from oandapyV20.endpoints.orders import PendingOrders
            r = PendingOrders(accountID=self.account_id)
            self._request_with_retry(r, "get_pending_orders")
            return r.response.get('orders', [])
        except Exception as e:
            self.logger.debug(f"Could not fetch pending orders from OANDA: {e}")
            return []

    def get_account_summary(self) -> Optional[Dict]:
        """Get OANDA account summary (balance, marginUsed, NAV, etc.)"""
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            self._request_with_retry(r, "get_account_summary")
            return r.response.get('account', {})
        except Exception as e:
            self.logger.debug(f"Could not get account summary: {e}")
            return None

    def check_order_exists(self, order_id: str) -> bool:
        """Check if an order still exists in OANDA (not cancelled)"""
        try:
            # Try to get order details - if it doesn't exist, it was cancelled
            from oandapyV20.endpoints.orders import OrderDetails
            r = OrderDetails(accountID=self.account_id, orderID=order_id)
            
            try:
                self._request_with_retry(r, "check_order_exists")
                return True
            except V20Error as e:
                # If order not found (404 or ORDER_DOESNT_EXIST), it was cancelled or doesn't exist
                error_code = getattr(e, 'code', None)
                error_msg = getattr(e, 'msg', str(e))
                is_order_gone = (
                    error_code == 404
                    or (isinstance(error_msg, str) and 'ORDER_DOESNT_EXIST' in error_msg.upper())
                    or (isinstance(error_msg, str) and "order doesn't exist" in error_msg.lower())
                )
                if is_order_gone:
                    return False
                self.logger.debug(f"⚠️ Error checking order {order_id}: {error_msg}")
                return False
            
        except Exception as e:
            self.logger.debug(f"⚠️ Error checking if order {order_id} exists: {e}")
            return False


class PositionManager:
    """Manages open positions and their lifecycle"""
    
    def __init__(self, executor: TradeExecutor, config: TradeConfig, 
                 state_file: str = "/var/data/trade_states.json",
                 config_api_url: Optional[str] = None,
                 risk_controller: Optional['RiskController'] = None):
        self.executor = executor
        self.config = config
        self.state_file = state_file
        self.config_api_url = config_api_url
        self.risk_controller = risk_controller
        self.active_trades: Dict[str, ManagedTrade] = {}
        self.logger = self._setup_logger()
        
        # MACD state tracking: pair -> {'macd_above_signal': bool, 'last_check_time': datetime}
        # Tracks previous MACD position relative to signal line for crossover detection
        self.macd_state: Dict[str, Dict] = {}
        # Execution mode enforcer (CRITICAL for rogue trade prevention)
        self.execution_enforcer = ExecutionModeEnforcer(config)
        self.pending_signals = {}
        self.pending_signals_file = "/var/data/pending_signals.json"
        # Last reject reason for "Trade not opened" log (consol-recommend2 Phase 1.3); do not change open_trade return signature
        self._last_reject_reason: Optional[str] = None
        # Orphan warning throttle: (pair, direction) -> last WARNING time (suggestions cursor3 §5.3 optional)
        self._orphan_warning_last_logged: Dict[tuple, float] = {}
        self._orphan_warning_window_seconds = 900  # 15 min
        self._load_pending_signals()
        self.logger.info("✅ ExecutionModeEnforcer initialized")
        # Sync pending signals to config-api so UI shows them (e.g. "1 pending: waiting for 15m crossover")
        if self.config_api_url and self.pending_signals:
            try:
                self._save_state()
            except Exception as e:
                self.logger.debug("Could not push pending signals to API on init: %s", e)
    
    @staticmethod
    def normalize_pair(pair: str) -> str:
        """Normalize pair format to consistent format (EUR/USD) for comparison
        
        OANDA uses EUR_USD, opportunities use EUR/USD
        Normalize both to EUR/USD for consistent comparison
        """
        if not pair:
            return pair
        # Convert underscores to slashes (OANDA format -> standard format)
        return pair.replace('_', '/').replace('-', '/')
    
    def _setup_logger(self):
        import logging
        logger = logging.getLogger('PositionManager')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_state(self):
        """Load trade states from disk"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for trade_data in data.get('trades', []):
                        trade = ManagedTrade(**trade_data)
                        # Restore datetime objects
                        if trade.opened_at:
                            trade.opened_at = datetime.fromisoformat(trade_data['opened_at'])
                        if trade.closed_at:
                            trade.closed_at = datetime.fromisoformat(trade_data['closed_at'])
                        # Restore enum
                        trade.state = TradeState(trade_data['state'])
                        try:
                            trade.sl_type = StopLossType(trade_data['sl_type'])
                        except (ValueError, TypeError):
                            # State was saved with a sl_type this version doesn't know (e.g. DMI_CROSSOVER on old deploy)
                            trade.sl_type = getattr(self, 'config', None) and getattr(self.config, 'stop_loss_type', None) or StopLossType.BE_TO_TRAILING
                            self.logger.warning(
                                f"⚠️ Unknown sl_type '{trade_data.get('sl_type')}' for trade {trade_data.get('trade_id')}, using config stop_loss_type"
                            )
                        
                        # Load all trades with a valid ID (OPEN, AT_BREAKEVEN, TRAILING, PENDING)
                        # Previously we only loaded OPEN/AT_BREAKEVEN/TRAILING, so PENDING were dropped on restart
                        # and UI showed only one row per pair when OANDA had multiple (e.g. 3x GBP/USD).
                        if trade.trade_id and trade.state in [
                            TradeState.OPEN, TradeState.AT_BREAKEVEN, TradeState.TRAILING, TradeState.PENDING
                        ]:
                            self.active_trades[trade.trade_id] = trade
                
                self.logger.info(f"📥 Loaded {len(self.active_trades)} active trades from disk")
            else:
                # Initialize empty state file if it doesn't exist (indicates auto-trader is running)
                self._save_state()  # Creates empty state file
                self.logger.info(f"📝 Initialized empty state file: {self.state_file}")
        except Exception as e:
            self.logger.error(f"❌ Error loading state: {e}")
    
    def _save_state(self):
        """Save trade states to disk"""
        try:
            # One entry per trade/order (keyed by trade_id/order_id in memory). Do not merge by (pair, direction)
            # or the UI will show one row for multiple OANDA orders (e.g. duplicate pending same pair).
            trades_data = []
            for trade in self.active_trades.values():
                trade_dict = asdict(trade)
                # Convert datetime to ISO format
                if trade.opened_at:
                    trade_dict['opened_at'] = trade.opened_at.isoformat()
                if trade.closed_at:
                    trade_dict['closed_at'] = trade.closed_at.isoformat()
                # Convert enums to strings
                trade_dict['state'] = trade.state.value
                trade_dict['sl_type'] = trade.sl_type.value
                trades_data.append(trade_dict)
            
            # Serialize pending signals for API (so UI can show "waiting for trigger")
            pending_signals_list = []
            for _sid, sig in (getattr(self, 'pending_signals', None) or {}).items():
                if not isinstance(sig, dict):
                    continue
                opp = sig.get('opportunity') or {}
                direc = sig.get('directive') or {}
                pending_signals_list.append({
                    'pair': opp.get('pair', ''),
                    'direction': opp.get('direction', ''),
                    'wait_for_signal': direc.get('wait_for_signal', ''),
                    'reason': direc.get('reason', ''),
                    'stored_at': sig.get('stored_at', ''),
                })
            data = {
                'trades': trades_data,
                'pending_signals': pending_signals_list,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Also POST to config-api if URL is provided (bypasses disk sharing issues)
            if self.config_api_url:
                try:
                    import requests
                    # Construct trades API URL (e.g., https://config-api-8n37.onrender.com/trades)
                    api_base = self.config_api_url.rstrip('/')
                    # Remove '/config' from end if present
                    if api_base.endswith('/config'):
                        api_base = api_base[:-7]
                    trades_api_url = f"{api_base}/trades"
                    
                    response = requests.post(
                        trades_api_url,
                        json=data,
                        timeout=5
                    )
                    if response.status_code == 200:
                        self.logger.debug(f"✅ Trade states posted to API: {trades_api_url}")
                    else:
                        self.logger.warning(f"⚠️ Failed to POST trade states to API: {response.status_code} - {response.text}")
                except Exception as e:
                    # Don't fail if API POST fails - disk save succeeded
                    self.logger.debug(f"⚠️ Could not POST trade states to API (disk save succeeded): {e}")
                
        except Exception as e:
            self.logger.error(f"❌ Error saving state: {e}")
    
    def can_open_new_trade(self) -> Tuple[bool, str]:
        """
        Check if we can open a new trade.
        Only filled/open positions count toward max_trades; pending orders do not (cursor5 §5.1).
        """
        # Circuit breaker: no new opens after N consecutive losses (research Phase 1.5)
        if self.risk_controller:
            ok, reason = self.risk_controller.circuit_breaker_ok()
            if not ok:
                return False, reason
            # Daily loss % limit (research Phase 1.4): block if already at/over 2%
            if getattr(self.config, 'max_daily_loss_pct', None) is not None:
                account_balance = getattr(self.config, 'account_balance_override', None)
                if account_balance is None and self.executor:
                    try:
                        summary = self.executor.get_account_summary()
                        if summary and summary.get('balance') is not None:
                            account_balance = float(summary['balance'])
                    except Exception:
                        pass
                if account_balance and account_balance > 0:
                    ok, reason = self.risk_controller.can_take_loss(0.0, account_balance)
                    if not ok:
                        return False, reason
        # In-memory: count only OPEN/TRAILING/AT_BREAKEVEN (not PENDING)
        open_states = (TradeState.OPEN, TradeState.TRAILING, TradeState.AT_BREAKEVEN)
        in_memory_open_count = sum(
            1 for t in self.active_trades.values()
            if getattr(t, 'state', None) in open_states
        )
        in_memory_total = len(self.active_trades)

        oanda_count = 0
        try:
            oanda_trades = self.executor.get_open_positions()
            oanda_count = len(oanda_trades)
        except Exception as e:
            self.logger.debug(f"Could not check OANDA for trade count: {e}")
            oanda_count = in_memory_open_count

        actual_count = max(in_memory_open_count, oanda_count)
        max_trades = self.config.max_open_trades

        if in_memory_total > max_trades:
            self.logger.warning(
                f"Active count exceeds config: in_memory_total={in_memory_total}, "
                f"open_count={in_memory_open_count}, max_trades={max_trades}, OANDA_open={oanda_count}"
            )
        if oanda_count > max_trades:
            self.logger.error(
                f"OANDA has more open positions ({oanda_count}) than max_trades ({max_trades}). "
                f"Not opening new trades until count is below limit."
            )

        if actual_count >= max_trades:
            return False, (
                f"Max trades limit reached ({actual_count}/{max_trades}) - "
                f"in-memory open: {in_memory_open_count}, OANDA: {oanda_count}"
            )
        return True, "OK"
    
    def has_existing_position(self, pair: str, direction: str) -> bool:
        """
        Check if we already have an open position for this pair/direction
        This checks BOTH in-memory active_trades AND OANDA directly to prevent duplicates
        
        Args:
            pair: Currency pair (e.g., "EUR/USD")
            direction: Trade direction ("LONG", "SHORT", "BUY", "SELL")
            
        Returns:
            True if position exists, False otherwise
        """
        # Normalize inputs
        normalized_pair = self.normalize_pair(pair)
        direction_upper = direction.upper()
        
        # Normalize direction: BUY -> LONG, SELL -> SHORT
        if direction_upper in ['BUY', 'LONG']:
            direction_normalized = 'LONG'
        elif direction_upper in ['SELL', 'SHORT']:
            direction_normalized = 'SHORT'
        else:
            direction_normalized = direction_upper
        
        # Check in-memory active trades first (fast)
        for trade in self.active_trades.values():
            trade_pair = self.normalize_pair(trade.pair)
            trade_direction = trade.direction.upper()
            
            # Normalize trade direction too
            if trade_direction in ['BUY', 'LONG']:
                trade_direction_normalized = 'LONG'
            elif trade_direction in ['SELL', 'SHORT']:
                trade_direction_normalized = 'SHORT'
            else:
                trade_direction_normalized = trade_direction
            
            if trade_pair == normalized_pair and trade_direction_normalized == direction_normalized:
                if trade.state == TradeState.PENDING:
                    # Placeholder (no trade_id yet) or pending order: block duplicate
                    if not trade.trade_id:
                        return True
                    if self.executor.check_order_exists(trade.trade_id):
                        return True
                else:
                    return True
        
        # Also check OANDA directly to catch any trades we might have missed
        # This is CRITICAL after service restarts when active_trades might be empty
        try:
            # Check open trades
            oanda_trades = self.executor.get_open_positions()
            for oanda_trade in oanda_trades:
                oanda_instrument = oanda_trade.get('instrument', '')
                oanda_units = float(oanda_trade.get('currentUnits', 0))
                oanda_direction = "LONG" if oanda_units > 0 else "SHORT"
                
                # Normalize OANDA instrument format
                oanda_pair_normalized = self.normalize_pair(oanda_instrument)
                
                if oanda_pair_normalized == normalized_pair and oanda_direction == direction_normalized:
                    self.logger.warning(
                        f"🚫 BLOCKED: Found existing OANDA position not in active_trades: "
                        f"{pair} {direction} (Trade ID: {oanda_trade.get('id')}) - "
                        f"syncing now to prevent duplicate"
                    )
                    # Sync this trade into active_trades so we don't miss it again
                    try:
                        managed_trade = self._create_trade_from_oanda(oanda_trade)
                        if managed_trade:
                            trade_id = str(oanda_trade.get('id', ''))
                            self.active_trades[trade_id] = managed_trade
                            self.logger.info(f"✅ Synced missing trade {trade_id} into active_trades")
                    except Exception as sync_error:
                        self.logger.debug(f"Could not sync trade: {sync_error}")
                    
                    return True
            
            # Also check pending orders (they will become trades)
            try:
                from oandapyV20.endpoints.orders import PendingOrders
                r = PendingOrders(accountID=self.executor.account_id)
                self.executor.request(r, "pending_orders_has_order")
                pending_orders = r.response.get('orders', [])
                
                for order in pending_orders:
                    order_instrument = order.get('instrument', '')
                    order_units = float(order.get('units', 0))
                    order_direction = "LONG" if order_units > 0 else "SHORT"
                    
                    # Normalize OANDA instrument format
                    order_pair_normalized = self.normalize_pair(order_instrument)
                    
                    if order_pair_normalized == normalized_pair and order_direction == direction_normalized:
                        self.logger.warning(
                            f"🚫 BLOCKED: Found existing pending order in OANDA: "
                            f"{pair} {direction} (Order ID: {order.get('id')})"
                        )
                        return True
            except Exception as e:
                # If we can't get pending orders, continue (not critical)
                self.logger.debug(f"Could not check pending orders: {e}")
                
        except Exception as e:
            # If OANDA check fails, log but don't block - rely on in-memory check
            self.logger.warning(f"⚠️ Could not check OANDA for existing positions: {e}")
        
        return False

    def has_open_position_for_pair(self, pair: str) -> bool:
        """
        True if there is any OPEN position (any direction) for this pair.
        Used to enforce: no pending order for a pair while that pair has an open position.
        """
        normalized_pair = self.normalize_pair(pair)
        open_states = (TradeState.OPEN, TradeState.TRAILING, TradeState.AT_BREAKEVEN)
        for trade in self.active_trades.values():
            if trade.state not in open_states:
                continue
            if self.normalize_pair(trade.pair) == normalized_pair:
                return True
        try:
            oanda_trades = self.executor.get_open_positions()
            for ot in oanda_trades:
                inst = self.normalize_pair(ot.get('instrument', ''))
                if inst == normalized_pair:
                    return True
        except Exception as e:
            self.logger.debug(f"Could not check OANDA for open position for pair: {e}")
        return False
    
    def is_pair_in_cooldown(self, pair: str) -> bool:
        """
        Check if pair is in cooldown (e.g. recently closed as duplicate).
        Prevents immediate reopening after duplicate closure.
        Returns False if no cooldown tracking (minimal implementation).
        """
        # Cooldown logic can be extended to check execution_history for recently closed pairs
        return False
    
    def open_trade(self, opportunity: Dict, market_state: Dict, record_run: bool = True) -> Optional[ManagedTrade]:
        """Open trade with execution mode enforcement and run limits.
        
        When record_run=False (e.g. replace pending order), max_runs check is skipped and
        execution is not recorded, so the same opportunity can place without consuming another run.
        """
        pair = opportunity.get('pair', '')
        direction = opportunity.get('direction', '').upper()
        normalized_pair = self.normalize_pair(pair)
        direction_norm = 'LONG' if direction.upper() in ('BUY', 'LONG') else 'SHORT'

        # Check for existing position (in-memory + OANDA)
        if self.has_existing_position(pair, direction):
            self._last_reject_reason = "duplicate_blocked"
            self.logger.warning(
                f"🚫 BLOCKED DUPLICATE (in-memory): {pair} {direction} - already exists"
            )
            return None

        # Pre-open OANDA check (cursor5 §5.2): fresh fetch to reduce race window
        try:
            oanda_trades = self.executor.get_open_positions()
            for ot in oanda_trades:
                inst = self.normalize_pair(ot.get('instrument', ''))
                units = float(ot.get('currentUnits', 0))
                odir = 'LONG' if units > 0 else 'SHORT'
                if inst == normalized_pair and odir == direction_norm:
                    self._last_reject_reason = "duplicate_blocked"
                    self.logger.warning(
                        f"🚫 BLOCKED DUPLICATE (pre-open OANDA check): {pair} {direction}"
                    )
                    return None
        except Exception as e:
            self.logger.debug(f"Pre-open OANDA check failed (continuing): {e}")

        # Check if can open
        can_open, reason = self.can_open_new_trade()
        if not can_open:
            self._last_reject_reason = "max_trades_limit"
            self.logger.warning(f"⚠️ Cannot open trade: {reason}")
            return None

        # CRITICAL: Get current price for execution directive
        current_price = self._get_current_price(pair)
        if not current_price:
            self._last_reject_reason = "no_price"
            self.logger.error(f"❌ Cannot get current price for {pair}")
            return None
        
        # Get max_runs from opportunity config (applies to ALL opportunities: LLM + Fisher)
        max_runs = opportunity.get('execution_config', {}).get('max_runs', 1)
        
        # CRITICAL: Get execution directive from enforcer
        # When record_run=False (replace path), skip max_runs check so we can place the replacement order
        directive = self.execution_enforcer.get_execution_directive(
            opportunity, current_price, max_runs=max_runs,
            skip_max_runs_check=not record_run
        )
        
        self.logger.info(
            f"📋 Execution directive: {directive.action} ({directive.order_type}) "
            f"- {pair} {direction} - {directive.reason}"
        )
        
        # Handle directive (consol-recommend3 Phase 1.2: max_runs auto-reset when no position)
        if directive.action == "REJECT":
            r = (directive.reason or "").lower()
            if ("max_run" in r or "max run" in r) and not self.has_existing_position(pair, direction):
                # No open/pending for this (pair, direction) — reset run count and re-get directive so we can retry
                opp_id = get_stable_opportunity_id(opportunity)
                self.execution_enforcer.reset_run_count(opp_id)
                directive = self.execution_enforcer.get_execution_directive(
                    opportunity, current_price, max_runs=max_runs, skip_max_runs_check=False
                )
                self.logger.info(
                    f"📋 Execution directive (after max_runs reset): {directive.action} ({directive.order_type}) "
                    f"- {pair} {direction} - {directive.reason}"
                )
                if directive.action in ["EXECUTE_NOW", "PLACE_PENDING"]:
                    # Fall through to execute (handled below)
                    self.logger.info(
                        f"max_runs reset for {opp_id} (no position for pair/direction) - retrying directive"
                    )
                    pass
                else:
                    self._last_reject_reason = "max_runs"
                    self.logger.warning(f"⚠️ Opportunity rejected (after reset): {directive.reason}")
                    return None
            else:
                # Map common directive.reason to reason code for "Trade not opened" log
                if "max_run" in r or "max run" in r:
                    self._last_reject_reason = "max_runs"
                elif "consensus" in r:
                    self._last_reject_reason = "consensus_too_low"
                else:
                    self._last_reject_reason = "reject_directive"
                self.logger.warning(f"⚠️ Opportunity rejected: {directive.reason}")
                return None

        if directive.action == "WAIT_SIGNAL":
            self._last_reject_reason = "wait_signal"
            self._store_pending_signal(opportunity, directive)
            self.logger.info(f"⏳ Stored {pair} {direction}, waiting for {directive.wait_for_signal}")
            return None
        
        elif directive.action in ["EXECUTE_NOW", "PLACE_PENDING"]:
            # Set order_type on opportunity (CRITICAL - prevents rogue MARKET)
            opportunity['order_type'] = directive.order_type
            opportunity['current_price'] = directive.current_price
            
            # Final validation before execution
            valid, reason = self.execution_enforcer.validate_opportunity_before_execution(opportunity)
            if not valid:
                self._last_reject_reason = "validation_failed"
                self.logger.error(f"🚨 BLOCKED ROGUE TRADE: {reason}")
                return None

            # Create managed trade
            trade = self._create_trade_from_opportunity(opportunity, market_state)
            opp_id = get_stable_opportunity_id(opportunity)
            pending_key = f"_pending_{opp_id}"

            # No pending order for a pair that already has an open position
            if directive.order_type in ('LIMIT', 'STOP'):
                if self.has_open_position_for_pair(pair):
                    self._last_reject_reason = "open_exists_no_pending"
                    self.logger.error(
                        f"🚫 BLOCKED: {pair} already has an open position. "
                        f"No pending order allowed until that position is closed or cancelled."
                    )
                    return None

            if self.config.trading_mode == TradingMode.MANUAL:
                self.logger.info(
                    f"📋 MANUAL MODE: Trade ready for approval: {trade.pair} {trade.direction} "
                    f"@ {trade.entry_price} (consensus: {trade.consensus_level})"
                )
                return trade

            # Add to active_trades before send (cursor5 §5.2) so same-loop duplicate check sees it
            trade.state = TradeState.PENDING if directive.order_type in ['LIMIT', 'STOP'] else TradeState.OPEN
            trade.opened_at = datetime.utcnow()
            self.active_trades[pending_key] = trade

            self.logger.info(
                f"Opening {trade.pair} {trade.direction} (has_existing_position=False)"
            )
            # Final gate: never exceed max_trades and never duplicate (pair, direction) on OANDA (open or pending)
            try:
                oanda_trades = self.executor.get_open_positions()
                oanda_count = len(oanda_trades)
                max_trades = self.config.max_open_trades
                if oanda_count >= max_trades:
                    self.active_trades.pop(pending_key, None)
                    self.logger.error(
                        f"🚫 BLOCKED: OANDA has {oanda_count} open positions (max_trades={max_trades}). "
                        f"Not opening {trade.pair} {trade.direction} - would exceed limit."
                    )
                    return None
                # When placing a pending (LIMIT/STOP): no open position for this pair (any direction) is allowed
                if directive.order_type in ('LIMIT', 'STOP'):
                    for ot in oanda_trades:
                        inst = self.normalize_pair(ot.get('instrument', ''))
                        if inst == normalized_pair:
                            self.active_trades.pop(pending_key, None)
                            self.logger.error(
                                f"🚫 BLOCKED (final check): {pair} already has an open position on OANDA. "
                                f"No pending order allowed until it is closed or cancelled."
                            )
                            return None
                for ot in oanda_trades:
                    inst = self.normalize_pair(ot.get('instrument', ''))
                    units = float(ot.get('currentUnits', 0))
                    odir = 'LONG' if units > 0 else 'SHORT'
                    if inst == normalized_pair and odir == direction_norm:
                        self.active_trades.pop(pending_key, None)
                        self.logger.error(
                            f"🚫 BLOCKED DUPLICATE (final check): {pair} {direction} already on OANDA - not sending order."
                        )
                        return None
                # Also check pending orders: do not send a second LIMIT/STOP if (pair, direction) already has one
                pending_orders = self.executor.get_pending_orders()
                for order in pending_orders:
                    inst = self.normalize_pair(order.get('instrument', ''))
                    units = float(order.get('units', 0))
                    odir = 'LONG' if units > 0 else 'SHORT'
                    if inst == normalized_pair and odir == direction_norm:
                        self.active_trades.pop(pending_key, None)
                        self.logger.error(
                            f"🚫 BLOCKED DUPLICATE (final check – pending): {pair} {direction} already has pending order "
                            f"(OANDA order {order.get('id', '')}) - not sending another."
                        )
                        return None
            except Exception as e:
                self.logger.warning(f"Final OANDA check failed (aborting open to be safe): {e}")
                self.active_trades.pop(pending_key, None)
                return None
            # Execute trade
            order_or_trade_id = self.executor.open_trade(trade)
            if order_or_trade_id:
                # Remove placeholder and key by real id
                self.active_trades.pop(pending_key, None)
                if record_run:
                    self.execution_enforcer.record_execution(opp_id)
                trade.trade_id = order_or_trade_id
                trade.state = TradeState.PENDING if directive.order_type in ['LIMIT', 'STOP'] else TradeState.OPEN
                trade.opened_at = datetime.utcnow()
                self.active_trades[order_or_trade_id] = trade
                
                # RL logging (includes Fisher signal tracking for ML/RL enhancement)
                try:
                    from src.scalping_rl_enhanced import ScalpingRLEnhanced
                    from pathlib import Path
                    db_path = '/var/data/scalping_rl.db' if os.path.exists('/var/data') else str(Path(__file__).parent / 'data' / 'scalping_rl.db')
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                    rl_db = ScalpingRLEnhanced(db_path=db_path)
                    rl_db.log_signal(
                        pair=trade.pair,
                        direction=trade.direction,
                        entry_price=trade.entry_price,
                        stop_loss=trade.stop_loss,
                        take_profit=trade.take_profit,
                        llm_sources=trade.llm_sources or [],
                        consensus_level=trade.consensus_level,
                        rationale=trade.rationale or "",
                        confidence=trade.confidence or 0.5,
                        executed=True,
                        trade_id=order_or_trade_id,
                        position_size=trade.units,
                        fisher_signal=opportunity.get('fisher_signal', False)
                    )
                    self.logger.info(f"📊 RL: Logged trade (fisher_signal={opportunity.get('fisher_signal', False)})")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not log trade to RL: {e}")
                
                self._save_state()
                
                self.logger.info(
                    f"✅ AUTO MODE: Created order/trade {order_or_trade_id}: {trade.pair} {trade.direction} "
                    f"{trade.units} units @ {trade.entry_price} (state: {trade.state.value})"
                )
                return trade
            else:
                self.active_trades.pop(pending_key, None)
                self._last_reject_reason = getattr(self.executor, '_last_reject_reason', None) or "oanda_reject"
                self.logger.warning(
                    f"⚠️ Trade rejected by OANDA for {trade.pair} {trade.direction} @ {trade.entry_price}"
                )
                return None

        self._last_reject_reason = "unknown"
        return None
    
    def _get_current_price(self, pair: str) -> Optional[float]:
        """Get current market price from OANDA with retry logic"""
        import time

        from oandapyV20.endpoints.pricing import PricingInfo

        oanda_pair = pair.replace('/', '_').replace('-', '_')

        # Retry logic for transient errors
        max_attempts = 2
        last_exception = None

        for attempt in range(max_attempts):
            try:
                params = {"instruments": oanda_pair}
                r = PricingInfo(accountID=self.executor.account_id, params=params)
                self.executor.request(r, "pricing")
                prices = r.response.get('prices', [])

                if prices:
                    bid = float(prices[0].get('bids', [{}])[0].get('price', 0))
                    ask = float(prices[0].get('asks', [{}])[0].get('price', 0))
                    if bid > 0 and ask > 0:
                        return (bid + ask) / 2

                return None

            except Exception as e:
                last_exception = e
                error_msg = str(e)
                status_code = self._get_http_status(e)

                # Check if this is a retryable error (5xx or 429)
                is_retryable = self._is_retryable_http(status_code)

                if is_retryable and attempt < max_attempts - 1:
                    # Log at debug level for retryable errors
                    self.logger.debug(
                        f"Price fetch for {pair} (HTTP {status_code}): {error_msg}. "
                        f"Retrying (attempt {attempt + 1}/{max_attempts})"
                    )
                    # Exponential backoff
                    time.sleep(1 * (attempt + 1))
                else:
                    # Non-retryable error or last attempt
                    self.logger.error(f"Error getting price for {pair}: {error_msg}")
                    return None

        # Final attempt failed
        if last_exception:
            self.logger.debug(f"Price fetch for {pair} failed after {max_attempts} attempts")
        return None

    def _get_http_status(self, e: Exception) -> Optional[int]:
        """Extract HTTP status code from exception if present"""
        resp = getattr(e, "response", None)
        if resp is not None:
            return getattr(resp, "status_code", None)
        return None

    def _is_retryable_http(self, status: Optional[int]) -> bool:
        """True for 5xx and 429 (transient/server/rate-limit)"""
        if status is None:
            return True  # Unknown - retry once
        return 429 == status or (500 <= status < 600)
    
    def _store_pending_signal(self, opportunity: Dict, directive: ExecutionDirective):
        """Store opportunity waiting for signal (e.g. MACD crossover)"""
        signal_id = f"{opportunity['pair']}_{opportunity['direction']}_{directive.wait_for_signal}"
        self.pending_signals[signal_id] = {
            'opportunity': opportunity,
            'directive': {
                'action': directive.action,
                'order_type': directive.order_type,
                'reason': directive.reason,
                'wait_for_signal': directive.wait_for_signal,
                'current_price': directive.current_price,
                'max_runs': directive.max_runs
            },
            'stored_at': datetime.utcnow().isoformat()
        }
        self._save_pending_signals()
        # Push to config-api so UI shows pending signals (e.g. "1 pending: waiting for 15m crossover")
        self._save_state()
    
    def _to_json_safe(self, obj):
        """Convert numpy/NumPy types to native Python for JSON serialization."""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: self._to_json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._to_json_safe(v) for v in obj]
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            import numpy as np
            if hasattr(obj, 'item'):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except (ImportError, AttributeError, ValueError):
            pass
        return obj

    def _save_pending_signals(self):
        """Save pending signals to disk"""
        try:
            os.makedirs(os.path.dirname(self.pending_signals_file), exist_ok=True)
            with open(self.pending_signals_file, 'w') as f:
                json.dump(self._to_json_safe(self.pending_signals), f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving pending signals: {e}")
    
    def _clear_pending_for_pair_direction(self, pair: str, direction: str) -> int:
        """Remove any pending Fisher (WAIT_SIGNAL) entries for this pair/direction. Returns count removed."""
        if not pair or not direction or getattr(self, 'pending_signals', None) is None:
            return 0
        pair_norm = self.normalize_pair(pair)
        direction_upper = (direction or '').upper()
        removed = []
        for signal_id, data in list(self.pending_signals.items()):
            opp = data.get('opportunity') if isinstance(data, dict) else {}
            if not isinstance(opp, dict):
                continue
            opp_pair = self.normalize_pair(opp.get('pair', ''))
            opp_dir = (opp.get('direction') or '').upper()
            if opp_pair == pair_norm and opp_dir == direction_upper:
                removed.append(signal_id)
        for sid in removed:
            self.pending_signals.pop(sid, None)
        if removed:
            self._save_pending_signals()
            self.logger.info(f"Removed {len(removed)} pending Fisher signal(s) for {pair_norm} {direction_upper}")
        return len(removed)
    
    def _load_pending_signals(self):
        """Load pending signals from disk"""
        try:
            if os.path.exists(self.pending_signals_file):
                with open(self.pending_signals_file, 'r') as f:
                    self.pending_signals = json.load(f)
                self.logger.info(f"📂 Loaded {len(self.pending_signals)} pending signals")
        except Exception as e:
            self.logger.warning(f"Could not load pending signals: {e}")
    
    def _position_units_from_risk(
        self, account_balance: float, risk_pct: float, sl_pips: float, pair: str
    ) -> int:
        """Position size from research formula: (Account × Risk%) / (SL pips × pip value)."""
        if account_balance <= 0 or risk_pct <= 0 or sl_pips <= 0:
            return 0
        pip_size = 0.01 if 'JPY' in (pair or '') else 0.0001
        risk_amount = account_balance * (risk_pct / 100.0)
        # risk_amount = units * sl_pips * pip_size (price move) * (1 unit = 1 quote currency per unit)
        units = risk_amount / (sl_pips * pip_size)
        return max(0, int(units))

    def _create_trade_from_opportunity(self, opp: Dict, market_state: Dict) -> ManagedTrade:
        """Create ManagedTrade from opportunity
        
        opp['entry'] should be the recommended entry price from Trade-Alerts.
        opp['order_type'] should be 'LIMIT' or 'STOP' to place order at recommended price.
        """
        
        # Extract consensus info
        consensus_level = opp.get('consensus_level', 1)
        llm_sources = opp.get('llm_sources', [])
        multiplier = self.config.consensus_multiplier.get(consensus_level, 1.0)
        base_size = self.config.base_position_size
        recommended_entry = opp.get('entry', 0.0)
        pair = opp.get('pair', '')
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        # Preliminary SL for position sizing: from opportunity or 1:1 with TP
        stop_loss_raw = opp.get('stop_loss')
        if stop_loss_raw and recommended_entry:
            sl_pips = abs(recommended_entry - stop_loss_raw) / pip_size
        else:
            sl_pips = 0.0
        # Risk-based position size when config and inputs allow
        account_balance = getattr(self.config, 'account_balance_override', None)
        if account_balance is None and self.executor:
            try:
                summary = self.executor.get_account_summary()
                if summary and summary.get('balance') is not None:
                    account_balance = float(summary['balance'])
            except Exception:
                account_balance = None
        risk_pct = getattr(self.config, 'risk_percent_per_trade', None)
        if risk_pct is None:
            phase = getattr(self.config, 'trading_phase', 'phase_1') or 'phase_1'
            risk_pct = {'phase_1': 0.5, 'phase_2': 1.0, 'phase_3': 2.0}.get(phase, 0.5)
        if account_balance and account_balance > 0 and sl_pips > 0 and risk_pct > 0:
            units = self._position_units_from_risk(account_balance, risk_pct, sl_pips, pair)
            if units <= 0:
                units = base_size * multiplier
            else:
                units = int(units * multiplier)  # apply consensus multiplier to risk-based size
        else:
            units = base_size * multiplier
        
        # Determine SL type: per-opportunity (UI) first, then FT-DMI-EMA default, then global config
        sl_type = self.config.stop_loss_type
        trailing_distance = None
        opportunity_source = opp.get('source', '')
        initial_stop_loss = opp.get('initial_stop_loss') or opp.get('stop_loss')
        per_opp_sl = (opp.get('execution_config') or {}).get('sl_type') or (opp.get('fisher_config') or {}).get('sl_type')
        if per_opp_sl:
            try:
                sl_type = StopLossType(per_opp_sl) if isinstance(per_opp_sl, str) else per_opp_sl
            except (ValueError, TypeError):
                sl_type = getattr(StopLossType, str(per_opp_sl), None) or sl_type
        elif opportunity_source in ('FT_DMI_EMA', 'DMI_EMA'):
            sl_type = StopLossType.STRUCTURE_ATR_STAGED
        if opportunity_source in ('FT_DMI_EMA', 'DMI_EMA') and initial_stop_loss is None and opp.get('stop_loss'):
            initial_stop_loss = opp['stop_loss']
        
        if sl_type == StopLossType.TRAILING:
            trailing_distance = self.config.hard_trailing_pips
        elif sl_type == StopLossType.ATR_TRAILING:
            # Calculate ATR-based distance
            regime = market_state.get('regime', 'NORMAL')
            if regime == 'HIGH_VOL':
                trailing_distance = market_state.get('atr', 20) * self.config.atr_multiplier_high_vol
            else:
                trailing_distance = market_state.get('atr', 20) * self.config.atr_multiplier_low_vol
        
        # Use recommended entry price (opp['entry'] already in recommended_entry)
        order_type = opp.get('order_type', 'LIMIT')  # LIMIT or STOP
        
        # Get stop loss and take profit from opportunity
        # Phase 3.1: ATR-based TP from market_state when available; else Fisher 'take_profit', LLM 'exit'
        take_profit = opp.get('take_profit_atr') or opp.get('tp_atr') or opp.get('take_profit') or opp.get('exit')
        stop_loss = opp.get('stop_loss')
        
        # Validate stop loss - if None or invalid, calculate based on take profit (1:1 risk/reward)
        if not stop_loss or stop_loss <= 0:
            pip_size = 0.01 if 'JPY' in opp['pair'] else 0.0001
            
            if take_profit and take_profit > 0:
                # Calculate 1:1 risk/reward - same distance in pips as take profit
                if opp['direction'].upper() in ['LONG', 'BUY']:
                    # LONG: TP is above entry, SL should be same distance below entry
                    tp_distance_pips = (take_profit - recommended_entry) / pip_size
                    stop_loss = recommended_entry - (tp_distance_pips * pip_size)
                else:  # SHORT or SELL
                    # SHORT: TP is below entry, SL should be same distance above entry
                    tp_distance_pips = (recommended_entry - take_profit) / pip_size
                    stop_loss = recommended_entry + (tp_distance_pips * pip_size)
                
                self.logger.info(
                    f"📊 No stop loss provided for {opp['pair']}, calculated 1:1 risk/reward: "
                    f"SL={stop_loss} ({abs(tp_distance_pips):.1f} pips from entry {recommended_entry}, "
                    f"matching TP distance)"
                )
            else:
                # No take profit either - use default 20 pips
                default_sl_distance_pips = 20
                if opp['direction'].upper() in ['LONG', 'BUY']:
                    stop_loss = recommended_entry - (default_sl_distance_pips * pip_size)
                else:  # SHORT or SELL
                    stop_loss = recommended_entry + (default_sl_distance_pips * pip_size)
                
                self.logger.info(
                    f"⚠️ No stop loss or take profit provided for {opp['pair']}, "
                    f"calculated default: {stop_loss} ({default_sl_distance_pips} pips from entry {recommended_entry})"
                )
            
            # Round stop loss to OANDA precision
            stop_loss = round_price_for_oanda(stop_loss, opp['pair'])
        else:
            # Use recommended stop loss - round to OANDA precision
            stop_loss = round_price_for_oanda(stop_loss, opp['pair'])
            self.logger.debug(
                f"✅ Using recommended stop loss for {opp['pair']}: {stop_loss}"
            )
        
        # Ensure take profit is always set when we have stop_loss (OANDA must have both for display/risk)
        # If opportunity had no TP, use 1:1 risk/reward (same distance as SL from entry)
        if not take_profit or take_profit <= 0:
            pip_size = 0.01 if 'JPY' in opp['pair'] else 0.0001
            if stop_loss and recommended_entry:
                sl_distance_pips = abs(recommended_entry - stop_loss) / pip_size
                if opp['direction'].upper() in ['LONG', 'BUY']:
                    take_profit = recommended_entry + (sl_distance_pips * pip_size)
                else:
                    take_profit = recommended_entry - (sl_distance_pips * pip_size)
                self.logger.debug(
                    f"📊 No take profit provided for {opp['pair']}, using 1:1 with SL: TP={take_profit} ({sl_distance_pips:.1f} pips)"
                )
        # Round take profit to OANDA precision if provided
        if take_profit:
            take_profit = round_price_for_oanda(take_profit, opp['pair'])
        
        return ManagedTrade(
            opportunity_id=opp.get('id', f"{opp['pair']}_{opp['direction']}_{recommended_entry}"),
            pair=opp['pair'],
            direction=opp['direction'],
            entry_price=recommended_entry,  # Use recommended entry price for order
            stop_loss=stop_loss,  # Use calculated stop loss if opportunity had none
            take_profit=take_profit,
            units=units,
            position_size_multiplier=multiplier,
            sl_type=sl_type,
            trailing_distance=trailing_distance,
            consensus_level=consensus_level,
            llm_sources=llm_sources,
            rationale=opp.get('recommendation', ''),
            confidence=opp.get('confidence', 0.5),
            order_type=order_type,  # Store order type (LIMIT or STOP)
            opportunity_source=opportunity_source,
            initial_stop_loss=round_price_for_oanda(initial_stop_loss, opp['pair']) if initial_stop_loss else stop_loss,
        )
    
    def monitor_positions(self, current_prices: Dict[str, float], 
                         market_state: Dict, oanda_client=None):
        """Monitor all open positions and update their state
        
        Args:
            current_prices: Dict of pair -> current price
            market_state: Current market state
            oanda_client: OandaClient instance (optional, needed for MACD_CROSSOVER stop loss)
        """
        
        for trade_id, trade in list(self.active_trades.items()):
            try:
                # Skip pending orders (they haven't filled yet, so no position to monitor)
                if trade.state == TradeState.PENDING:
                    # Pending orders will be cancelled at 6 PM EST
                    continue
                
                current_price = current_prices.get(trade.pair)
                if not current_price:
                    self.logger.debug(
                        f"Skipping {trade.pair} {trade.direction} (trade_id={trade.trade_id}): no current_price"
                    )
                    continue
                
                # Update price tracking
                if trade.highest_price is None or current_price > trade.highest_price:
                    trade.highest_price = current_price
                if trade.lowest_price is None or current_price < trade.lowest_price:
                    trade.lowest_price = current_price
                
                # Calculate unrealized P&L in pips (treat BUY and LONG as long; SELL and SHORT as short)
                pip_size = 0.01 if "JPY" in trade.pair else 0.0001
                is_long = (trade.direction or "").upper() in ("LONG", "BUY")
                if is_long:
                    pnl_pips = (current_price - trade.entry_price) / pip_size
                else:
                    pnl_pips = (trade.entry_price - current_price) / pip_size
                trade.unrealized_pnl = pnl_pips
                
                # Trading hours: close on weekend or Friday 21:30+ UTC (and Mon–Thu 23:00+ if not runner)
                if _TradingHoursManager is not None:
                    now_utc = datetime.now(pytz.UTC)
                    thm = _TradingHoursManager()
                    direction_str = "LONG" if is_long else "SHORT"
                    should_close, reason = thm.should_close_trade(now_utc, pnl_pips, direction_str)
                    if should_close:
                        self.close_trade(trade_id, reason)
                        continue
                
                # Phase 3.3: Time-based max hold - close if hold time exceeded
                max_hold = getattr(self.config, 'max_hold_seconds', None)
                if max_hold is not None and max_hold > 0 and trade.state in (TradeState.OPEN, TradeState.TRAILING, TradeState.AT_BREAKEVEN):
                    opened_at = getattr(trade, 'opened_at', None)
                    if opened_at:
                        now_naive = datetime.utcnow()
                        oa_naive = opened_at.replace(tzinfo=None) if getattr(opened_at, 'tzinfo', None) else opened_at
                        hold_sec = (now_naive - oa_naive).total_seconds()
                        if hold_sec >= max_hold:
                            self.close_trade(trade_id, f"Max hold time exceeded ({hold_sec:.0f}s >= {max_hold}s)")
                            continue
                
                # Phase 3.2: Half-and-run - close 50% at 1.5R, remainder will use normal trailing
                if (
                    getattr(self.config, 'half_and_run_enabled', False)
                    and trade.state == TradeState.OPEN
                    and not getattr(trade, 'partial_profit_taken', False)
                    and trade.sl_type != StopLossType.STRUCTURE_ATR_STAGED
                ):
                    risk_distance = abs(trade.entry_price - (trade.initial_stop_loss or trade.stop_loss or trade.entry_price))
                    if risk_distance and risk_distance > 0:
                        if is_long:
                            r_multiple = (current_price - trade.entry_price) / risk_distance
                        else:
                            r_multiple = (trade.entry_price - current_price) / risk_distance
                        r_threshold = getattr(self.config, 'half_and_run_r_multiple', 1.5)
                        if r_multiple >= r_threshold and trade.trade_id:
                            try:
                                units = 0
                                for t in (self.executor.get_open_positions() or []):
                                    if self.normalize_pair(t.get('instrument', '')) != self.normalize_pair(trade.pair):
                                        continue
                                    u = float(t.get('currentUnits', 0))
                                    if (u > 0) == is_long:
                                        units = int(abs(u))
                                        break
                                if units != 0:
                                    units_to_close = int(abs(units) * 0.5)
                                    if units_to_close > 0 and self.executor.close_trade_partial(
                                        trade.trade_id, units_to_close, is_long, trade.pair, f"Half-and-run at +{r_multiple:.1f}R"
                                    ):
                                        trade.partial_profit_taken = True
                                        self.logger.info(
                                            f"📊 Half-and-run: closed 50% of {trade.pair} {trade.direction} at +{r_multiple:.1f}R"
                                        )
                            except Exception as e:
                                self.logger.debug(f"Half-and-run partial close: {e}")
                
                # Also try to get actual P/L from OANDA if available (for accuracy)
                # This helps catch any discrepancies between our calculation and OANDA's
                try:
                    if trade.trade_id and trade.state == TradeState.OPEN:
                        # Get trade details from OANDA to get actual unrealized P/L
                        from oandapyV20.endpoints.trades import TradeDetails
                        r = TradeDetails(accountID=self.executor.account_id, tradeID=trade.trade_id)
                        self.executor.request(r, "trade_details")
                        oanda_trade = r.response.get('trade', {})
                        if oanda_trade:
                            oanda_unrealized_pl = float(oanda_trade.get('unrealizedPL', 0))
                            # Store OANDA's actual P/L in account currency (for display)
                            trade.oanda_unrealized_pl = oanda_unrealized_pl
                except Exception as e:
                    # If we can't get OANDA P/L, continue with calculated pips
                    # This is expected for pending orders or if API call fails
                    pass
                
                # Check for stop loss transitions
                if trade.sl_type == StopLossType.BE_TO_TRAILING:
                    self._check_be_transition(trade, current_price)
                elif trade.sl_type == StopLossType.ATR_TRAILING:
                    # ATR Trailing: Convert to trailing stop when trade moves in profit
                    self._check_ai_trailing_conversion(trade, current_price, market_state)
                elif trade.sl_type == StopLossType.MACD_CROSSOVER:
                    # MACD_CROSSOVER stop loss: Check for reverse crossover
                    if oanda_client:
                        if self.check_macd_reverse_crossover(trade, oanda_client):
                            # Close trade due to MACD reverse crossover
                            self.close_trade(
                                trade_id,
                                f"MACD reverse crossover stop loss - {trade.pair} {trade.direction}"
                            )
                            continue  # Trade closed, skip further monitoring
                elif trade.sl_type == StopLossType.DMI_CROSSOVER:
                    # DMI_CROSSOVER stop loss: Close on +DI/-DI reverse crossover
                    try:
                        if oanda_client and self.check_dmi_reverse_crossover(trade, oanda_client):
                            self.close_trade(
                                trade_id,
                                f"DMI reverse crossover stop loss - {trade.pair} {trade.direction}"
                            )
                            continue
                    except Exception as dmi_e:
                        self.logger.error(
                            f"❌ Error in DMI_CROSSOVER check for trade {trade_id}: {dmi_e}",
                            exc_info=True
                        )
                elif trade.sl_type == StopLossType.STRUCTURE_ATR:
                    # ATR + structure (LLM/Fisher): structure+ATR at entry, BE at +1R, then trail to 1H EMA 26
                    try:
                        if self._check_structure_atr_simple(trade_id, trade, current_price, oanda_client):
                            continue  # Trade was closed
                    except Exception as st_e:
                        self.logger.error(
                            f"❌ Error in STRUCTURE_ATR check for trade {trade_id}: {st_e}",
                            exc_info=True
                        )
                elif trade.sl_type == StopLossType.STRUCTURE_ATR_STAGED:
                    # Full staged logic for FT_DMI_EMA and DMI_EMA; otherwise use ATR+structure (same as STRUCTURE_ATR)
                    try:
                        if getattr(trade, "opportunity_source", "") in ("FT_DMI_EMA", "DMI_EMA"):
                            if self._check_structure_atr_staged(trade_id, trade, current_price, oanda_client):
                                continue  # Trade was closed
                        else:
                            if self._check_structure_atr_simple(trade_id, trade, current_price, oanda_client):
                                continue
                    except Exception as st_e:
                        self.logger.error(
                            f"❌ Error in STRUCTURE_ATR_STAGED check for trade {trade_id}: {st_e}",
                            exc_info=True
                        )
                
                # Check intelligence validity
                self._check_intelligence_validity(trade, market_state)
                
            except Exception as e:
                self.logger.error(f"❌ Error monitoring trade {trade_id}: {e}", exc_info=True)
        
        self._save_state()
    
    def _find_oanda_trade_by_pair_direction_units(
        self, oanda_trades: List[Dict], pair: str, direction: str, units: float
    ) -> Optional[Dict]:
        """Find an OANDA open trade that matches pair, direction, and units (for order ID → trade ID reconciliation)."""
        if not pair or units <= 0 or not oanda_trades:
            return None
        oanda_instrument = pair.replace('/', '_')
        want_long = (direction or "").upper() in ("LONG", "BUY")
        want_units = int(units)
        matches = []
        for t in oanda_trades:
            inst = (t.get("instrument") or "").replace("-", "_")
            if inst != oanda_instrument:
                continue
            current_units = int(float(t.get("currentUnits", 0)))
            if want_long and current_units <= 0:
                continue
            if not want_long and current_units >= 0:
                continue
            if abs(current_units) != want_units:
                continue
            matches.append(t)
        return matches[0] if len(matches) == 1 else None
    
    def _cleanup_duplicate_positions_and_orders_on_oanda(self) -> None:
        """
        Enforce at most one open position and one pending order per (pair, direction) on OANDA.
        Also enforce: no pending order for a pair that has an open position (cancel any such pending).
        Closes extra open positions and cancels extra pending orders so UI and OANDA never show
        multiple trades for the same pair. Keeps the one we track in active_trades if any;
        otherwise keeps the first (oldest id).
        """
        try:
            oanda_trades = self.executor.get_open_positions()
            pending_orders = self.executor.get_pending_orders() or []
            our_tracked_ids = {str(t.trade_id) for t in self.active_trades.values() if t.trade_id}
            
            # Group open positions by (pair, direction)
            open_by_key = defaultdict(list)  # (pair_norm, direction) -> [trade dicts]
            for t in oanda_trades:
                inst = (t.get('instrument') or '').replace('-', '_')
                pair_norm = self.normalize_pair(inst)
                units = float(t.get('currentUnits', 0))
                direction = "LONG" if units > 0 else "SHORT"
                open_by_key[(pair_norm, direction)].append(t)
            
            # Close duplicate open positions (keep one per pair/direction)
            for (pair_norm, direction), trades_list in open_by_key.items():
                if len(trades_list) <= 1:
                    continue
                # Prefer keeping the one we track; else keep first by id
                ids_in_order = [str(t.get('id', '')) for t in trades_list if t.get('id')]
                keep_id = None
                for tid in ids_in_order:
                    if tid in our_tracked_ids:
                        keep_id = tid
                        break
                if keep_id is None and ids_in_order:
                    keep_id = min(ids_in_order)
                for t in trades_list:
                    tid = str(t.get('id', ''))
                    if not tid or tid == keep_id:
                        continue
                    if self.executor.close_trade(tid, "Cleanup: duplicate (pair, direction) - only one allowed"):
                        self.active_trades.pop(tid, None)
                        self.logger.warning(
                            f"🧹 Cleaned up duplicate open position: {pair_norm} {direction} (closed trade_id={tid}, keeping {keep_id})"
                        )

            # No pending order for a pair that has an open position: cancel any such pending
            pairs_with_open = {pair_norm for (pair_norm, _) in open_by_key.keys()}
            for o in pending_orders:
                inst = (o.get('instrument') or '').replace('-', '_')
                pair_norm = self.normalize_pair(inst)
                if pair_norm not in pairs_with_open:
                    continue
                oid = str(o.get('id', ''))
                if not oid:
                    continue
                if self.executor.cancel_order(oid, "Cleanup: pair has open position - no pending allowed until closed"):
                    self.active_trades.pop(oid, None)
                    self.logger.warning(
                        f"🧹 Cleaned up pending order: {pair_norm} (cancelled order_id={oid}) - pair has open position, no pending allowed"
                    )
            
            # Group pending orders by (pair, direction)
            pending_by_key = defaultdict(list)
            for o in pending_orders:
                inst = (o.get('instrument') or '').replace('-', '_')
                pair_norm = self.normalize_pair(inst)
                units = float(o.get('units', 0))
                direction = "LONG" if units > 0 else "SHORT"
                pending_by_key[(pair_norm, direction)].append(o)
            
            # Cancel duplicate pending orders (keep one per pair/direction)
            for (pair_norm, direction), orders_list in pending_by_key.items():
                if len(orders_list) <= 1:
                    continue
                ids_in_order = [str(o.get('id', '')) for o in orders_list if o.get('id')]
                keep_id = None
                for oid in ids_in_order:
                    if oid in our_tracked_ids:
                        keep_id = oid
                        break
                if keep_id is None and ids_in_order:
                    keep_id = min(ids_in_order)
                for o in orders_list:
                    oid = str(o.get('id', ''))
                    if not oid or oid == keep_id:
                        continue
                    if self.executor.cancel_order(oid, "Cleanup: duplicate (pair, direction) - only one allowed"):
                        self.active_trades.pop(oid, None)
                        self.logger.warning(
                            f"🧹 Cleaned up duplicate pending order: {pair_norm} {direction} (cancelled order_id={oid}, keeping {keep_id})"
                        )
        except Exception as e:
            self.logger.warning(f"⚠️ Cleanup of duplicate OANDA positions/orders failed (non-fatal): {e}")
    
    def sync_with_oanda(self, market_state=None):
        """Sync active_trades with OANDA's actual open positions
        
        This:
        0. Cleanup: enforce at most one open + one pending per (pair, direction) on OANDA (close/cancel extras).
        1. Detects when trades are closed externally (manually in OANDA) and removes them
        2. Detects when trades exist in OANDA but aren't tracked (manually opened) and adds them
        
        Args:
            market_state: Optional market state (for future logic e.g. closing excess trades by relevance)
        """
        try:
            # Enforce single (pair, direction) on OANDA before sync (cleanup orphans/duplicates)
            self._cleanup_duplicate_positions_and_orders_on_oanda()
            
            # Get actual open trades from OANDA (source of truth - engine/UI must match this)
            oanda_trades = self.executor.get_open_positions()
            oanda_trade_ids = {str(trade.get('id', '')) for trade in oanda_trades if trade.get('id')}
            our_tracked_ids = [str(t.trade_id) for t in self.active_trades.values() if t.trade_id]
            self.logger.info(
                f"🔄 Syncing with OANDA: API returned {len(oanda_trades)} open trade(s) (IDs: {sorted(oanda_trade_ids)}); "
                f"we track {len(self.active_trades)} (IDs: {our_tracked_ids})"
            )
            
            # Get OANDA's pending orders once - use this to remove phantoms (orders we have but OANDA doesn't)
            oanda_pending_ids = set()
            pending_list_fetched = False
            try:
                from oandapyV20.endpoints.orders import PendingOrders
                r = PendingOrders(accountID=self.executor.account_id)
                self.executor.request(r, "sync_pending_orders")
                pending_orders = r.response.get('orders', [])
                oanda_pending_ids = {str(o.get('id', '')) for o in pending_orders}
                pending_list_fetched = True
            except Exception as e:
                self.logger.debug(f"Could not fetch PendingOrders from OANDA: {e}")
                pending_orders = []
            
            # Track our known trade IDs (including PENDING orders that might have filled)
            our_trade_ids = {str(t.trade_id) for t in self.active_trades.values() if t.trade_id}
            
            # 1. Find trades/orders in our system that are no longer in OANDA
            trades_to_remove = []
            for trade_id, trade in list(self.active_trades.items()):
                if trade.state == TradeState.PENDING:
                    # PENDING: order not in OANDA's pending list => either cancelled OR filled (now open position)
                    if trade.trade_id:
                        if pending_list_fetched and trade.trade_id not in oanda_pending_ids:
                            # First check if it FILLED: is there an open position for this pair/direction/units?
                            match = self._find_oanda_trade_by_pair_direction_units(
                                oanda_trades, trade.pair, trade.direction, getattr(trade, 'units', 0)
                            )
                            if match:
                                # Order filled: update to OPEN and reconcile trade ID (don't remove)
                                oanda_tid = str(match.get('id', ''))
                                old_key = trade_id
                                trade.trade_id = oanda_tid
                                trade.state = TradeState.OPEN
                                oanda_price = float(match.get('price', 0))
                                if oanda_price > 0:
                                    trade.entry_price = oanda_price
                                del self.active_trades[old_key]
                                self.active_trades[oanda_tid] = trade
                                our_trade_ids.add(oanda_tid)
                                self.logger.info(
                                    f"🔄 PENDING order filled: {trade.pair} {trade.direction} "
                                    f"(was order {old_key}, now open position {oanda_tid}) - updated to OPEN"
                                )
                            else:
                                # Really cancelled/missing: remove
                                trades_to_remove.append((trade_id, trade))
                                self.logger.info(
                                    f"🔄 Detected cancelled/missing order: {trade.pair} {trade.direction} "
                                    f"(Order ID: {trade.trade_id}) - removing from active trades"
                                )
                        # Fallback: if we couldn't fetch pending list, use per-order check
                        elif not pending_list_fetched and not self.executor.check_order_exists(trade.trade_id):
                            # Same: check if filled before removing
                            match = self._find_oanda_trade_by_pair_direction_units(
                                oanda_trades, trade.pair, trade.direction, getattr(trade, 'units', 0)
                            )
                            if match:
                                oanda_tid = str(match.get('id', ''))
                                old_key = trade_id
                                trade.trade_id = oanda_tid
                                trade.state = TradeState.OPEN
                                oanda_price = float(match.get('price', 0))
                                if oanda_price > 0:
                                    trade.entry_price = oanda_price
                                del self.active_trades[old_key]
                                self.active_trades[oanda_tid] = trade
                                our_trade_ids.add(oanda_tid)
                                self.logger.info(
                                    f"🔄 PENDING order filled: {trade.pair} {trade.direction} "
                                    f"(was order {old_key}, now open position {oanda_tid}) - updated to OPEN"
                                )
                            else:
                                trades_to_remove.append((trade_id, trade))
                                self.logger.info(
                                    f"🔄 Detected cancelled order: {trade.pair} {trade.direction} "
                                    f"(Order ID: {trade.trade_id}) - removing from active trades"
                                )
                else:
                    # OPEN: remove if trade is not in OANDA's open trades (compare as string)
                    tid_str = str(trade.trade_id) if trade.trade_id else ""
                    if tid_str and tid_str not in oanda_trade_ids:
                        # Reconcile order ID vs trade ID: we may have stored the order ID; OANDA open trades list uses trade IDs
                        match = self._find_oanda_trade_by_pair_direction_units(
                            oanda_trades, trade.pair, trade.direction, getattr(trade, 'units', 0)
                        )
                        if match:
                            oanda_tid = str(match.get('id', ''))
                            if oanda_tid and oanda_tid not in our_trade_ids:
                                # Update our record to use OANDA's trade ID so future syncs match
                                old_key = trade_id
                                trade.trade_id = oanda_tid
                                del self.active_trades[old_key]
                                self.active_trades[oanda_tid] = trade
                                our_trade_ids.add(oanda_tid)
                                self.logger.info(
                                    f"🔄 Reconciled order ID → trade ID: {trade.pair} {trade.direction} "
                                    f"(was {old_key}, OANDA trade ID: {oanda_tid}) - now in sync"
                                )
                                continue
                        # Grace period: OANDA API can lag after we just opened; don't remove trade we opened this run
                        opened_at = getattr(trade, 'opened_at', None)
                        if opened_at:
                            if isinstance(opened_at, str):
                                try:
                                    opened_at = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                                except Exception:
                                    opened_at = None
                            if opened_at:
                                now_utc = datetime.utcnow()
                                opened_utc = opened_at.astimezone(pytz.UTC).replace(tzinfo=None) if getattr(opened_at, 'tzinfo', None) else opened_at
                                if (now_utc - opened_utc) < timedelta(seconds=90):
                                    self.logger.debug(
                                        f"⏳ Skipping sync remove for {trade.pair} {trade.direction} (ID: {trade_id}) - "
                                        f"opened <90s ago, OANDA API may not list it yet"
                                    )
                                    continue
                        trades_to_remove.append((trade_id, trade))
                        self.logger.info(
                            f"🔄 Detected trade not on OANDA (removing from UI): {trade.pair} {trade.direction} "
                            f"(ID: {trade_id}) - OANDA has {len(oanda_trade_ids)} trade(s), this one not in list"
                        )
            
            # Remove closed trades and cancelled orders
            for trade_id, trade in trades_to_remove:
                if trade.state == TradeState.PENDING:
                    # Cancelled order
                    trade.state = TradeState.CLOSED_MANUAL
                    trade.closed_at = datetime.utcnow()
                else:
                    # Closed trade (e.g. closed on OANDA) — clear pending Fisher signal for this pair/direction
                    trade.state = TradeState.CLOSED_MANUAL
                    trade.closed_at = datetime.utcnow()
                    self._clear_pending_for_pair_direction(getattr(trade, 'pair', ''), getattr(trade, 'direction', ''))
                del self.active_trades[trade_id]
            
            # 2. Add pending orders from OANDA that we don't track (use pending_orders already fetched)
            for order in pending_orders:
                    order_id = str(order.get('id', ''))
                    
                    # Skip if we already track this order
                    if order_id in our_trade_ids:
                        continue
                    
                    # Create a ManagedTrade from pending order
                    try:
                        instrument = order.get('instrument', '')
                        units = float(order.get('units', 0))
                        direction = "LONG" if units > 0 else "SHORT"
                        price = float(order.get('price', 0))  # LIMIT/STOP price
                        
                        # Normalize pair format
                        normalized_pair = self.normalize_pair(instrument)
                        
                        # Get stop loss and take profit from order
                        stop_loss = None
                        if 'stopLossOnFill' in order:
                            stop_loss = float(order['stopLossOnFill'].get('price', 0))
                        elif 'stopLossOrder' in order:
                            stop_loss = float(order['stopLossOrder'].get('price', 0))
                        
                        take_profit = None
                        if 'takeProfitOnFill' in order:
                            take_profit = float(order['takeProfitOnFill'].get('price', 0))
                        elif 'takeProfitOrder' in order:
                            take_profit = float(order['takeProfitOrder'].get('price', 0))
                        
                        # Determine order type
                        order_type = order.get('type', 'LIMIT')
                        if order_type == 'MARKET_IF_TOUCHED':
                            order_type = 'STOP'
                        
                        # Get create time
                        opened_at = None
                        if 'createTime' in order:
                            try:
                                opened_at = datetime.fromisoformat(order['createTime'].replace('Z', '+00:00'))
                            except:
                                opened_at = datetime.utcnow()
                        else:
                            opened_at = datetime.utcnow()
                        
                        # Create ManagedTrade for pending order
                        pending_trade = ManagedTrade(
                            trade_id=order_id,
                            pair=normalized_pair,
                            direction=direction,
                            entry_price=price,
                            stop_loss=stop_loss or 0.0,
                            take_profit=take_profit,
                            current_sl=stop_loss or 0.0,
                            units=abs(units),
                            state=TradeState.PENDING,
                            opened_at=opened_at,
                            order_type=order_type,
                            sl_type=self.config.stop_loss_type,
                            consensus_level=1,
                            llm_sources=[],
                            rationale="Pending order from OANDA",
                            confidence=0.5
                        )
                        
                        self.active_trades[order_id] = pending_trade
                        self.logger.info(
                            f"🔄 Detected pending order from OANDA: {normalized_pair} {direction} "
                            f"(Order ID: {order_id}) - added to active trades"
                        )
                    except Exception as e:
                        self.logger.warning(f"⚠️ Could not add pending order {order_id}: {e}")
            
            # 3. Find trades in OANDA that aren't in our system (opened externally or filled from pending)
            trades_to_add = []
            for oanda_trade in oanda_trades:
                trade_id = str(oanda_trade.get('id', ''))
                
                # Skip if we already track this trade
                if trade_id in our_trade_ids:
                    # Check if this was a PENDING order that filled - update its state and entry price
                    for our_trade_id, our_trade in list(self.active_trades.items()):
                        if our_trade.trade_id == trade_id:
                            # Update entry price from OANDA's actual fill price (important for LIMIT orders)
                            oanda_price = float(oanda_trade.get('price', 0))
                            if oanda_price > 0 and abs(oanda_price - our_trade.entry_price) > 0.00001:
                                old_entry = our_trade.entry_price
                                our_trade.entry_price = oanda_price
                                self.logger.info(
                                    f"📊 Updated entry price from OANDA: {our_trade.pair} {our_trade.direction} "
                                    f"{old_entry} → {oanda_price} (actual fill price)"
                                )
                            
                            # Update state if it was pending
                            if our_trade.state == TradeState.PENDING:
                                our_trade.state = TradeState.OPEN
                                self.logger.info(
                                    f"✅ PENDING order {trade_id} filled - updated to OPEN: "
                                    f"{our_trade.pair} {our_trade.direction}"
                                )
                    continue
                
                # This is a new trade we don't track - add it
                trades_to_add.append((trade_id, oanda_trade))
            
            # Add new trades from OANDA (cursor5 §5.5: two-stage matching so filled pending keeps SL/TP)
            for trade_id, oanda_trade in trades_to_add:
                try:
                    instrument = oanda_trade.get('instrument', '')
                    units = float(oanda_trade.get('currentUnits', 0))
                    pair_od = self.normalize_pair(instrument)
                    direction_od = "LONG" if units > 0 else "SHORT"
                    units_abs = abs(int(units))

                    # Two-stage match: link to in-memory PENDING by (pair, direction, units) to preserve SL/TP
                    matched_pending_key = None
                    for key, t in list(self.active_trades.items()):
                        if t.state != TradeState.PENDING:
                            continue
                        if self.normalize_pair(t.pair) != pair_od:
                            continue
                        td = (t.direction or "").upper()
                        tdir = "LONG" if td in ("LONG", "BUY") else "SHORT"
                        if tdir != direction_od:
                            continue
                        if abs(getattr(t, 'units', 0) or 0) != units_abs:
                            continue
                        matched_pending_key = key
                        break

                    if matched_pending_key is not None:
                        our_trade = self.active_trades.pop(matched_pending_key)
                        our_trade.trade_id = trade_id
                        our_trade.state = TradeState.OPEN
                        oanda_price = float(oanda_trade.get('price', 0))
                        if oanda_price > 0:
                            our_trade.entry_price = oanda_price
                        self.active_trades[trade_id] = our_trade
                        self.logger.info(
                            f"🔄 PENDING filled: linked OANDA position {trade_id} to existing pending "
                            f"({our_trade.pair} {our_trade.direction}) - SL/TP preserved"
                        )
                        continue

                    # Optional orphan detection
                    key_od = (pair_od, direction_od)
                    now_od = time.time()
                    last_od = self._orphan_warning_last_logged.get(key_od, 0)
                    if now_od - last_od >= self._orphan_warning_window_seconds:
                        self.logger.warning(
                            f"Possible orphan: {pair_od} {direction_od} on OANDA not in engine state (adding to track)."
                        )
                        self._orphan_warning_last_logged[key_od] = now_od
                    managed_trade = self._create_trade_from_oanda(oanda_trade)
                    if managed_trade:
                        self.active_trades[trade_id] = managed_trade
                        self.logger.info(
                            f"🔄 Detected existing OANDA trade: {managed_trade.pair} {managed_trade.direction} "
                            f"(ID: {trade_id}) - added to active trades"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Could not add OANDA trade {trade_id}: {e}"
                    )
            
            # Always push current state to config-api so UI never shows phantom trades
            self._save_state()
            if trades_to_remove or trades_to_add:
                removed_count = len(trades_to_remove)
                added_count = len(trades_to_add)
                if removed_count > 0 and added_count > 0:
                    self.logger.info(
                        f"✅ Synced with OANDA: Removed {removed_count} closed trade(s), "
                        f"Added {added_count} existing trade(s)"
                    )
                elif removed_count > 0:
                    self.logger.info(f"✅ Synced with OANDA: Removed {removed_count} externally closed trade(s)")
                elif added_count > 0:
                    self.logger.info(f"✅ Synced with OANDA: Added {added_count} existing trade(s)")
            
        except Exception as e:
            self.logger.error(f"❌ Error syncing with OANDA: {e}", exc_info=True)
    
    def _create_trade_from_oanda(self, oanda_trade: Dict) -> Optional[ManagedTrade]:
        """Create a ManagedTrade from an OANDA trade response
        
        Used when syncing with OANDA to add trades that were opened externally
        """
        try:
            trade_id = str(oanda_trade.get('id', ''))
            instrument = oanda_trade.get('instrument', '')
            units = float(oanda_trade.get('currentUnits', 0))
            direction = "LONG" if units > 0 else "SHORT"
            
            # Get entry price (average price)
            price = float(oanda_trade.get('price', 0))
            
            # Get stop loss and take profit
            stop_loss = None
            if 'stopLossOrder' in oanda_trade:
                stop_loss = float(oanda_trade['stopLossOrder'].get('price', 0))
            
            take_profit = None
            if 'takeProfitOrder' in oanda_trade:
                take_profit = float(oanda_trade['takeProfitOrder'].get('price', 0))
            
            # If no stop loss in order, try to calculate from distance
            if not stop_loss:
                # Try to get from stopLossOrder distance
                if 'stopLossOrder' in oanda_trade and 'distance' in oanda_trade['stopLossOrder']:
                    distance = float(oanda_trade['stopLossOrder'].get('distance', 0))
                    pip_size = 0.01 if 'JPY' in instrument else 0.0001
                    if direction == "LONG":
                        stop_loss = price - (distance / pip_size * pip_size)
                    else:
                        stop_loss = price + (distance / pip_size * pip_size)
                else:
                    # Default stop loss: 20 pips
                    pip_size = 0.01 if 'JPY' in instrument else 0.0001
                    default_sl_pips = 20
                    if direction == "LONG":
                        stop_loss = price - (default_sl_pips * pip_size)
                    else:
                        stop_loss = price + (default_sl_pips * pip_size)
            
            # Round stop loss and take profit to OANDA precision
            if stop_loss:
                stop_loss = round_price_for_oanda(stop_loss, instrument)
            if take_profit:
                take_profit = round_price_for_oanda(take_profit, instrument)
            
            # Get open time
            opened_at = None
            if 'openTime' in oanda_trade:
                try:
                    opened_at = datetime.fromisoformat(oanda_trade['openTime'].replace('Z', '+00:00'))
                except:
                    opened_at = datetime.utcnow()
            else:
                opened_at = datetime.utcnow()
            
                # Create ManagedTrade
            # Normalize pair format (OANDA uses EUR_USD, we want EUR/USD)
            normalized_pair = self.normalize_pair(instrument)
            
            trade = ManagedTrade(
                trade_id=trade_id,
                pair=normalized_pair,
                direction=direction,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                current_sl=stop_loss,
                units=abs(units),
                state=TradeState.OPEN,  # These are open trades from OANDA
                opened_at=opened_at,
                sl_type=self.config.stop_loss_type,
                consensus_level=1,  # Unknown - set to minimum
                llm_sources=[],  # Unknown - empty
                rationale="Trade opened externally or before system tracking",
                confidence=0.5  # Default confidence
            )
            
            return trade
            
        except Exception as e:
            self.logger.error(f"❌ Error creating trade from OANDA data: {e}", exc_info=True)
            return None
    
    def _check_be_transition(self, trade: ManagedTrade, current_price: float):
        """Check if trade should transition from fixed SL to trailing. Research: BE at +be_min_pips, trailing at +trailing_activation_min_pips."""
        pip_size = 0.01 if "JPY" in trade.pair else 0.0001
        be_min_pips = getattr(self.config, 'be_min_pips', 50.0)
        trail_activation_pips = getattr(self.config, 'trailing_activation_min_pips', 100.0)
        is_long = (trade.direction or "").upper() in ("LONG", "BUY")
        
        if trade.state == TradeState.OPEN:
            # Move to breakeven when profit >= be_min_pips (research: 50 pips default)
            min_profit_dist = be_min_pips * pip_size
            if is_long:
                at_be = current_price >= trade.entry_price + min_profit_dist
            else:
                at_be = current_price <= trade.entry_price - min_profit_dist
            if at_be:
                if self.executor.update_stop_loss(trade.trade_id, trade.entry_price, trade.pair):
                    trade.current_sl = trade.entry_price
                    trade.state = TradeState.AT_BREAKEVEN
                    self.logger.info(
                        f"🎯 Trade {trade.trade_id} at breakeven - SL moved to entry (profit >= {be_min_pips} pips)"
                    )
        
        elif trade.state == TradeState.AT_BREAKEVEN:
            # Convert to trailing only when profit >= trailing_activation_min_pips (research: 100 pips default)
            min_profit_dist = trail_activation_pips * pip_size
            in_profit = (current_price >= trade.entry_price + min_profit_dist) if is_long else (current_price <= trade.entry_price - min_profit_dist)
            if not in_profit:
                return
            trailing_pips = self.config.hard_trailing_pips or 20.0
            if self.executor.convert_to_trailing_stop(
                trade.trade_id, trailing_pips, trade.pair
            ):
                trade.state = TradeState.TRAILING
                trade.trailing_distance = trailing_pips
                self.logger.info(
                    f"📈 Trade {trade.trade_id} converted to trailing stop "
                    f"({trailing_pips} pips, profit >= {trail_activation_pips} pips) [trailing verification]"
                )
    
    # Minimum profit (pips) required before converting to trailing stop (avoids activating in loss or before breakeven)
    MIN_PROFIT_PIPS_FOR_TRAILING = 1.0
    # Minimum time (seconds) trade must be OPEN before allowing ATR_TRAILING conversion (avoids first-cycle false in_profit)
    ATR_TRAILING_MIN_AGE_SECONDS = 120

    def _check_ai_trailing_conversion(self, trade: ManagedTrade, current_price: float, market_state: Dict):
        """
        Check if ATR Trailing trade should convert to trailing stop

        ATR Trailing works like BE_TO_TRAILING but uses ATR-based dynamic distance:
        1. Start with fixed stop loss
        2. When trade is in profit by at least MIN_PROFIT_PIPS_FOR_TRAILING, convert to trailing stop
        3. Trailing distance is calculated from ATR and volatility regime

        We require a small profit buffer so trailing is never activated in a losing trade or before breakeven.
        Fix 4 (Phase 0.5): Also require min age (ATR_TRAILING_MIN_AGE_SECONDS) and OANDA unrealized P/L > 0 when available.
        Research Phase 2: use trailing_activation_min_pips (default 100) when set; else MIN_PROFIT_PIPS_FOR_TRAILING.
        Bug fix: Require profit >= trailing distance so the initial trailing stop is never placed below entry (avoids
        tiny cushion on retrace). Default activation to 100 pips when config missing (never convert on 1 pip).
        """
        pip_size = 0.01 if "JPY" in trade.pair else 0.0001
        trail_activation_config = getattr(self.config, 'trailing_activation_min_pips', 100.0)
        if trail_activation_config is None or trail_activation_config <= 0:
            trail_activation_config = 100.0  # Never use 1 pip for ATR_Trailing; default 100 pips
        regime = market_state.get('regime', 'NORMAL')
        if regime == 'HIGH_VOL':
            trailing_pips = market_state.get('atr', 20) * self.config.atr_multiplier_high_vol
        else:
            trailing_pips = market_state.get('atr', 20) * self.config.atr_multiplier_low_vol
        # Require profit >= max(activation config, trailing distance) so stop starts at or above entry
        min_pips_for_conversion = max(trail_activation_config, trailing_pips)
        min_profit_distance = min_pips_for_conversion * pip_size
        
        if trade.state == TradeState.OPEN:
            # Fix 4: Time-based guard — do not convert in first N seconds after open (avoids first-cycle false in_profit)
            opened_at = getattr(trade, "opened_at", None)
            if not opened_at:
                self.logger.debug(
                    f"ATR Trailing: skipping conversion for {trade.trade_id} ({trade.pair} {trade.direction}): no opened_at"
                )
                return
            now_utc = datetime.now(pytz.UTC)
            if getattr(opened_at, "tzinfo", None) is None:
                opened_at_utc = opened_at.replace(tzinfo=pytz.UTC)
            else:
                opened_at_utc = opened_at.astimezone(pytz.UTC)
            time_since_open_seconds = (now_utc - opened_at_utc).total_seconds()
            if time_since_open_seconds < self.ATR_TRAILING_MIN_AGE_SECONDS:
                self.logger.debug(
                    f"ATR Trailing: skipping conversion for {trade.trade_id} ({trade.pair} {trade.direction}): "
                    f"open {time_since_open_seconds:.0f}s < min {self.ATR_TRAILING_MIN_AGE_SECONDS}s"
                )
                return

            # Fix 4: OANDA unrealized P/L gate — when available, require positive P/L so we don't convert on stale price
            oanda_pl = getattr(trade, "oanda_unrealized_pl", None)
            if oanda_pl is not None and isinstance(oanda_pl, (int, float)) and oanda_pl <= 0:
                self.logger.debug(
                    f"ATR Trailing: skipping conversion for {trade.trade_id} ({trade.pair} {trade.direction}): "
                    f"OANDA unrealized P/L = {oanda_pl} (not positive)"
                )
                return

            # Only convert when strictly in profit (at least MIN_PROFIT_PIPS_FOR_TRAILING pips)
            is_long = (trade.direction or "").upper() in ("LONG", "BUY")
            if is_long:
                in_profit = current_price >= trade.entry_price + min_profit_distance
            else:
                in_profit = current_price <= trade.entry_price - min_profit_distance

            if in_profit:
                # Trade is in profit by at least min_pips_for_conversion (>= trailing distance) so stop will be at or above entry
                # Observability (cursor5 §5.3): log before attempting conversion
                self.logger.info(
                    f"ATR Trailing: attempting conversion for {trade.trade_id} ({trade.pair} {trade.direction}) "
                    f"profit >= {min_pips_for_conversion:.1f} pips (activation/distance), trailing distance={trailing_pips:.1f} pips"
                )
                trade.trailing_distance = trailing_pips
                if self.executor.convert_to_trailing_stop(
                    trade.trade_id, trailing_pips, trade.pair
                ):
                    trade.state = TradeState.TRAILING
                    self.logger.info(
                        f"🎯 ATR Trailing: Trade {trade.trade_id} ({trade.pair} {trade.direction}) "
                        f"converted to trailing stop at breakeven/profit "
                        f"({trailing_pips:.1f} pips, regime: {regime})"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Failed to convert ATR Trailing trade {trade.trade_id} to trailing stop"
                    )
        
        elif trade.state == TradeState.TRAILING:
            # Trade is already trailing - check if volatility regime changed and update distance
            regime = market_state.get('regime', 'NORMAL')
            if regime == 'HIGH_VOL':
                new_trailing_pips = market_state.get('atr', 20) * self.config.atr_multiplier_high_vol
            else:
                new_trailing_pips = market_state.get('atr', 20) * self.config.atr_multiplier_low_vol
            
            # Only update if distance changed significantly (more than 10% difference)
            if trade.trailing_distance and abs(new_trailing_pips - trade.trailing_distance) / trade.trailing_distance > 0.1:
                if self.executor.convert_to_trailing_stop(
                    trade.trade_id, new_trailing_pips, trade.pair
                ):
                    trade.trailing_distance = new_trailing_pips
                    self.logger.info(
                        f"🔄 ATR Trailing: Updated trailing distance for trade {trade.trade_id} "
                        f"({trade.pair} {trade.direction}) to {new_trailing_pips:.1f} pips "
                        f"(regime changed to {regime})"
                    )
            else:
                self.logger.debug(
                    f"Trailing SL verified for {trade.trade_id} ({trade.pair} {trade.direction}) "
                    f"distance={trade.trailing_distance} pips [verification]"
                )
    
    def _check_intelligence_validity(self, trade: ManagedTrade, 
                                    market_state: Dict):
        """Check if trade rationale is still valid based on current market state.
        We do NOT close trades due to global bias change (user preference).
        """
        # Check if specific opportunity is still in market_state
        # If removed, it means LLMs changed their mind - close the trade
        opportunities = market_state.get('opportunities', [])
        opp_still_exists = False
        
        # Check if our opportunity ID matches any current opportunity
        for opp in opportunities:
            opp_id = opp.get('id', f"{opp.get('pair', '')}_{opp.get('direction', '')}_{opp.get('entry', '')}")
            if opp_id == trade.opportunity_id:
                opp_still_exists = True
                break
        
        # If opportunity no longer exists in market_state, LLMs changed their mind
        if not opp_still_exists and trade.opportunity_id:
            self.logger.warning(
                f"🔄 Trade {trade.trade_id} ({trade.pair} {trade.direction}) - "
                f"Original opportunity no longer in market_state. "
                f"LLMs may have changed their recommendation. "
                f"Trade will remain open but stop loss will protect it."
            )
            # Note: We don't auto-close here because:
            # 1. Stop loss already protects against adverse moves
            # 2. Price may still move in our favor
            # 3. User may want to manually review before closing
            # If you want auto-close, uncomment below:
            # self.logger.info(f"🔒 Auto-closing trade {trade.trade_id} - opportunity removed from market_state")
            # self.close_trade(trade.trade_id, "Opportunity removed - LLMs changed recommendation")
    
    def cancel_all_pending_orders(self, reason: str = "Daily cleanup at 6 PM EST") -> int:
        """Cancel all pending orders (orders that haven't filled yet)"""
        cancelled_count = 0
        
        # Find all pending orders (trades with state=PENDING)
        pending_trades = [
            (trade_id, trade) 
            for trade_id, trade in list(self.active_trades.items())
            if trade.state == TradeState.PENDING
        ]
        
        for trade_id, trade in pending_trades:
            # If trade_id is actually an order_id (pending order), cancel it
            if trade.trade_id:
                if self.executor.cancel_order(trade.trade_id, reason):
                    cancelled_count += 1
                    # Remove from active trades
                    del self.active_trades[trade_id]
                    self.logger.info(
                        f"🗑️ Removed pending order {trade_id} ({trade.pair} {trade.direction}) "
                        f"from tracking"
                    )
        
        if cancelled_count > 0:
            self._save_state()
            self.logger.info(f"✅ Cancelled {cancelled_count} pending order(s) at 6 PM EST")
        else:
            self.logger.info("ℹ️ No pending orders to cancel at 6 PM EST")

        return cancelled_count

    def _end_of_day_cleanup(self, reason: str = "End-of-day cleanup") -> Dict[str, int]:
        """
        Complete end-of-day cleanup with OANDA verification and orphan detection:
        1. Cancel all pending orders in our system
        2. Verify they're actually cancelled in OANDA
        3. Detect and cancel any orphaned OANDA orders not in our system
        4. Close all open trades
        5. Persist clean state to file

        Args:
            reason: Reason for cleanup (logged in OANDA API calls)

        Returns:
            {
                "pending_cancelled": int,        # Pending orders cancelled in our system
                "orphaned_detected": int,       # Orphaned orders found on OANDA
                "orphaned_cancelled": int,      # Orphaned orders successfully cancelled
                "open_trades_closed": int       # Open trades closed
            }
        """
        result = {
            "pending_cancelled": 0,
            "orphaned_detected": 0,
            "orphaned_cancelled": 0,
            "open_trades_closed": 0
        }

        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🧹 END-OF-DAY CLEANUP STARTING: {reason}")
        self.logger.info(f"{'='*80}")

        # ============================================================
        # Step 1: Cancel all pending orders in our system
        # ============================================================

        self.logger.info("Step 1: Cancelling pending orders in our system...")
        pending_trades = [
            (trade_id, trade)
            for trade_id, trade in list(self.active_trades.items())
            if trade.state == TradeState.PENDING
        ]

        for trade_id, trade in pending_trades:
            try:
                if trade.trade_id:
                    if self.executor.cancel_order(trade.trade_id, reason):
                        result["pending_cancelled"] += 1
                        del self.active_trades[trade_id]
                        self.logger.info(
                            f"  ✅ Cancelled pending order: {trade_id} "
                            f"({trade.pair} {trade.direction})"
                        )
                    else:
                        self.logger.warning(
                            f"  ⚠️ Failed to cancel pending order: {trade_id}"
                        )
            except Exception as e:
                self.logger.error(
                    f"  ❌ Exception cancelling pending order {trade_id}: {e}"
                )

        if result["pending_cancelled"] > 0:
            self.logger.info(
                f"  ✅ Cancelled {result['pending_cancelled']} pending order(s) in our system"
            )
        else:
            self.logger.info("  ℹ️ No pending orders in our system to cancel")

        # ============================================================
        # Step 2: Detect and cancel orphaned orders on OANDA
        # ============================================================

        self.logger.info("Step 2: Detecting orphaned orders on OANDA...")
        try:
            oanda_pending = self.executor.get_pending_orders()
            if oanda_pending is None:
                oanda_pending = []

            # Build set of our tracked pending order IDs
            our_pending_ids = {
                trade.trade_id
                for trade in self.active_trades.values()
                if trade.state == TradeState.PENDING and trade.trade_id
            }

            # Find orphaned orders (on OANDA but not in our system)
            orphaned_orders = [
                order for order in oanda_pending
                if str(order.get('id', '')) not in our_pending_ids
            ]

            if orphaned_orders:
                result["orphaned_detected"] = len(orphaned_orders)
                self.logger.warning(
                    f"  ⚠️ DETECTED {len(orphaned_orders)} ORPHANED ORDER(S) ON OANDA "
                    f"(not in UI system):"
                )

                # Log details of each orphaned order
                for order in orphaned_orders:
                    order_id = order.get('id', '')
                    instrument = order.get('instrument', '')
                    units = order.get('units', '')
                    price = order.get('price', '')
                    created_time = order.get('createTime', '')

                    # Calculate order age
                    try:
                        created_dt = datetime.fromisoformat(
                            created_time.replace('Z', '+00:00')
                        )
                        age_hours = (
                            datetime.now(pytz.utc) - created_dt
                        ).total_seconds() / 3600
                        age_str = f"{age_hours:.1f}h old"
                    except:
                        age_str = "age unknown"

                    self.logger.warning(
                        f"    - {order_id}: {instrument} {units} units @ {price} "
                        f"({age_str}, created: {created_time})"
                    )

                # Step 3: Cancel all orphaned orders
                self.logger.info(
                    f"  Attempting to cancel {len(orphaned_orders)} orphaned order(s)..."
                )
                for order in orphaned_orders:
                    try:
                        order_id = str(order.get('id', ''))
                        if self.executor.cancel_order(
                            order_id,
                            f"{reason} - orphaned order (not in UI)"
                        ):
                            result["orphaned_cancelled"] += 1
                            self.logger.info(
                                f"    ✅ Cancelled orphaned order: {order_id}"
                            )
                        else:
                            self.logger.warning(
                                f"    ⚠️ Failed to cancel orphaned order: {order_id}"
                            )
                    except Exception as e:
                        self.logger.error(
                            f"    ❌ Exception cancelling orphaned order {order_id}: {e}"
                        )

                self.logger.info(
                    f"  ✅ Cancelled {result['orphaned_cancelled']} of "
                    f"{result['orphaned_detected']} orphaned order(s)"
                )
            else:
                self.logger.info("  ✅ No orphaned orders detected on OANDA")

        except Exception as e:
            self.logger.error(
                f"  ❌ Error during orphaned order detection: {e}"
            )

        # ============================================================
        # Step 4: Close all open trades
        # ============================================================

        self.logger.info("Step 4: Closing all open trades...")
        open_trade_ids = [
            tid for tid, trade in self.active_trades.items()
            if trade.state in [
                TradeState.OPEN,
                TradeState.TRAILING,
                TradeState.AT_BREAKEVEN
            ]
        ]

        for trade_id in open_trade_ids:
            try:
                trade = self.active_trades[trade_id]
                if self.executor.close_trade(trade_id, reason):
                    result["open_trades_closed"] += 1
                    trade.state = TradeState.CLOSED_MANUAL
                    trade.closed_at = datetime.utcnow()
                    self.logger.info(
                        f"  ✅ Closed trade: {trade_id} ({trade.pair} {trade.direction})"
                    )
                else:
                    self.logger.warning(f"  ⚠️ Failed to close trade: {trade_id}")
            except Exception as e:
                self.logger.error(f"  ❌ Exception closing trade {trade_id}: {e}")

        if result["open_trades_closed"] > 0:
            self.logger.info(
                f"  ✅ Closed {result['open_trades_closed']} open trade(s)"
            )
        else:
            self.logger.info("  ℹ️ No open trades to close")

        # ============================================================
        # Step 5: Persist clean state to file
        # ============================================================

        self.logger.info("Step 5: Persisting clean state...")
        self._save_state()
        self.logger.info("  ✅ State persisted to file")

        # ============================================================
        # Final Summary
        # ============================================================

        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"✅ END-OF-DAY CLEANUP COMPLETED")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📊 CLEANUP SUMMARY:")
        self.logger.info(f"   • Pending orders cancelled: {result['pending_cancelled']}")
        self.logger.info(f"   • Orphaned orders detected: {result['orphaned_detected']}")
        self.logger.info(f"   • Orphaned orders cancelled: {result['orphaned_cancelled']}")
        self.logger.info(f"   • Open trades closed: {result['open_trades_closed']}")

        # Alert if there were orphaned orders
        if result["orphaned_detected"] > 0:
            self.logger.warning(
                f"\n🚨 ALERT: {result['orphaned_detected']} orphaned order(s) were detected "
                f"and {result['orphaned_cancelled']} were cancelled. "
                f"This indicates UI/OANDA sync issue."
            )

        self.logger.info(f"{'='*80}\n")

        return result

    def _periodic_sync_check(self) -> Dict[str, int]:
        """
        Periodic sync check during trading hours to detect if UI and OANDA drift apart.
        Runs every hour to catch any orphaned orders that appear between end-of-day cleanups.

        Key Feature: Automatically cancels stale orphaned orders (>1 hour old) that likely
        originated from a previous trading session.

        Returns:
            {
                "orphaned_detected": int,       # Orphaned orders found
                "orphaned_cancelled": int,      # Orphaned orders cancelled
                "discrepancies": int            # Total discrepancies found
            }
        """
        result = {
            "orphaned_detected": 0,
            "orphaned_cancelled": 0,
            "discrepancies": 0
        }

        try:
            # Get current pending orders from OANDA
            oanda_pending = self.executor.get_pending_orders()
            if oanda_pending is None:
                oanda_pending = []

            # Build set of our tracked pending order IDs
            our_pending_ids = {
                trade.trade_id
                for trade in self.active_trades.values()
                if trade.state == TradeState.PENDING and trade.trade_id
            }

            # Find orphaned orders (on OANDA but not in our system)
            orphaned_orders = [
                order for order in oanda_pending
                if str(order.get('id', '')) not in our_pending_ids
            ]

            if orphaned_orders:
                result["orphaned_detected"] = len(orphaned_orders)
                result["discrepancies"] = len(orphaned_orders)

                self.logger.warning(
                    f"\n⚠️ SYNC WARNING - Periodic Check: {len(orphaned_orders)} order(s) "
                    f"exist on OANDA but not in UI system!"
                )

                # Log details of each orphaned order
                for order in orphaned_orders:
                    order_id = order.get('id', '')
                    instrument = order.get('instrument', '')
                    units = order.get('units', '')
                    price = order.get('price', '')
                    created_time = order.get('createTime', '')

                    # Calculate order age to determine if it's stale
                    try:
                        created_dt = datetime.fromisoformat(
                            created_time.replace('Z', '+00:00')
                        )
                        now_utc = datetime.now(pytz.utc)
                        if created_dt.tzinfo is None:
                            created_dt = pytz.utc.localize(created_dt)
                        age_hours = (now_utc - created_dt).total_seconds() / 3600
                        age_str = f"{age_hours:.1f}h old"
                    except Exception as e:
                        age_str = "age unknown"
                        age_hours = 0

                    stale_indicator = " [STALE - will cancel]" if age_hours > 1.0 else " [RECENT]"
                    self.logger.warning(
                        f"  - {order_id}: {instrument} {units} units @ {price} "
                        f"({age_str}{stale_indicator}, created: {created_time})"
                    )

                # Step 2: Cancel stale orphaned orders (>1 hour old)
                # These likely originated from a previous trading day/session
                for order in orphaned_orders:
                    try:
                        created_time = order.get('createTime', '')
                        created_dt = datetime.fromisoformat(
                            created_time.replace('Z', '+00:00')
                        )
                        now_utc = datetime.now(pytz.utc)
                        if created_dt.tzinfo is None:
                            created_dt = pytz.utc.localize(created_dt)

                        age_hours = (now_utc - created_dt).total_seconds() / 3600

                        # Cancel if stale (>1 hour old - likely from previous session)
                        if age_hours > 1.0:
                            order_id = str(order.get('id', ''))
                            instrument = order.get('instrument', '')

                            if self.executor.cancel_order(
                                order_id,
                                f"Periodic sync check - stale orphaned order ({age_hours:.1f}h old)"
                            ):
                                result["orphaned_cancelled"] += 1
                                self.logger.info(
                                    f"  ✅ Cancelled stale orphaned order: {order_id} "
                                    f"({instrument}, {age_hours:.1f}h old)"
                                )
                            else:
                                self.logger.warning(
                                    f"  ⚠️ Failed to cancel stale orphaned order: {order_id}"
                                )
                        else:
                            # Recent order (within 1 hour) - don't cancel, might be legitimately pending
                            order_id = order.get('id', '')
                            self.logger.info(
                                f"  ℹ️ Skipping recent orphaned order (within 1h): {order_id}"
                            )

                    except Exception as e:
                        self.logger.error(f"  ❌ Error processing orphaned order: {e}")

                # Log summary
                if result["orphaned_cancelled"] > 0:
                    self.logger.info(
                        f"  ✅ Cancelled {result['orphaned_cancelled']} of "
                        f"{result['orphaned_detected']} stale orphaned order(s)"
                    )

            else:
                # No orphaned orders found - sync is clean
                self.logger.debug("  ✅ Sync check: No orphaned orders detected (UI and OANDA in sync)")

        except Exception as e:
            self.logger.error(f"❌ Error during periodic sync check: {e}")

        return result

    def close_trade(self, trade_id: str, reason: str = "Manual") -> bool:
        """Close a trade"""
        if trade_id not in self.active_trades:
            return False
        
        trade = self.active_trades[trade_id]
        
        if self.executor.close_trade(trade_id, reason):
            trade.state = TradeState.CLOSED_MANUAL
            trade.closed_at = datetime.utcnow()
            trade.realized_pnl = trade.unrealized_pnl
            
            # Record daily P&L for risk controller (account currency)
            if self.risk_controller:
                pl_account_currency = getattr(trade, 'oanda_unrealized_pl', None)
                if pl_account_currency is not None:
                    self.risk_controller.record_trade_close(float(pl_account_currency))
            
            # Remove from active trades
            pair_closed = getattr(trade, 'pair', '')
            direction_closed = getattr(trade, 'direction', '')
            # Optional audit log for quality check: stop loss strategies (suggestions cursor3 §5.1)
            final_pnl = getattr(trade, 'realized_pnl', trade.unrealized_pnl)
            self.logger.info(
                f"📋 Trade closed: {pair_closed} {direction_closed} exit_reason={reason} final_PnL={final_pnl}"
            )
            del self.active_trades[trade_id]
            self._save_state()
            
            # Remove any pending Fisher (WAIT_SIGNAL) entry for this pair/direction so logs stop "Checking N pending"
            self._clear_pending_for_pair_direction(pair_closed, direction_closed)
            
            return True
        
        return False
    
    def get_active_trades_summary(self) -> Dict:
        """Get summary of active trades"""
        total_unrealized = sum(t.unrealized_pnl for t in self.active_trades.values())
        
        by_pair = {}
        for trade in self.active_trades.values():
            if trade.pair not in by_pair:
                by_pair[trade.pair] = []
            by_pair[trade.pair].append({
                'trade_id': trade.trade_id,
                'direction': trade.direction,
                'entry': trade.entry_price,
                'state': trade.state.value,
                'pnl': trade.unrealized_pnl,
                'consensus': trade.consensus_level
            })
        
        open_states = (TradeState.OPEN, TradeState.TRAILING, TradeState.AT_BREAKEVEN)
        open_count = sum(
            1 for t in self.active_trades.values()
            if getattr(t, 'state', None) in open_states
        )
        pending_count = sum(
            1 for t in self.active_trades.values()
            if getattr(t, 'state', None) == TradeState.PENDING
        )
        return {
            'total_trades': len(self.active_trades),
            'open_count': open_count,
            'pending_count': pending_count,
            'total_unrealized_pnl': total_unrealized,
            'by_pair': by_pair,
            'states': {
                state.value: sum(1 for t in self.active_trades.values() if t.state == state)
                for state in TradeState
            }
        }
    
    def calculate_macd(self, candles: List[Dict], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
        """
        Calculate MACD from candle data
        
        Args:
            candles: List of candle dictionaries with 'close' key
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Dict with 'macd', 'signal', 'histogram' values or None if error
        """
        if not PANDAS_AVAILABLE:
            self.logger.error("❌ pandas not available - cannot calculate MACD")
            return None
        
        if not candles or len(candles) < slow + signal:
            self.logger.debug(f"Not enough candles for MACD calculation: {len(candles)}")
            return None
        
        try:
            # Convert candles to DataFrame
            df = pd.DataFrame(candles)
            if 'close' not in df.columns:
                self.logger.error("Candles missing 'close' column")
                return None
            
            closes = df['close']
            
            # Calculate EMAs
            ema_fast = closes.ewm(span=fast, adjust=False).mean()
            ema_slow = closes.ewm(span=slow, adjust=False).mean()
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            # Get current and previous values
            current_macd = float(macd_line.iloc[-1])
            current_signal = float(signal_line.iloc[-1])
            current_hist = float(histogram.iloc[-1])
            
            previous_macd = float(macd_line.iloc[-2]) if len(macd_line) > 1 else current_macd
            previous_signal = float(signal_line.iloc[-2]) if len(signal_line) > 1 else current_signal
            
            return {
                'macd': current_macd,
                'signal': current_signal,
                'histogram': current_hist,
                'macd_above_signal': current_macd > current_signal,
                'previous_macd_above_signal': previous_macd > previous_signal,
                'crossover_detected': (current_macd > current_signal) != (previous_macd > previous_signal)
            }
        except Exception as e:
            self.logger.error(f"❌ Error calculating MACD: {e}", exc_info=True)
            return None
    
    def check_macd_crossover(self, pair: str, direction: str, oanda_client) -> Tuple[bool, Optional[str]]:
        """
        Check if MACD has crossed in the same direction as the trade recommendation
        
        Args:
            pair: Currency pair (e.g., "EUR/USD")
            direction: Trade direction ("LONG", "SHORT", "BUY", "SELL")
            oanda_client: OandaClient instance for fetching candles
            
        Returns:
            Tuple of (should_trigger: bool, reason: str or None)
        """
        if self.config.execution_mode != ExecutionMode.MACD_CROSSOVER:
            return False, None
        
        # Normalize direction
        direction_upper = direction.upper()
        is_long = direction_upper in ['LONG', 'BUY']
        
        # Convert pair to OANDA format
        oanda_pair = pair.replace('/', '_').replace('-', '_')
        
        # Map timeframe to OANDA granularity
        timeframe_map = {
            'M1': 'M1', 'M5': 'M5', 'M15': 'M15', 'M30': 'M30',
            'H1': 'H1', 'H4': 'H4', 'D': 'D', 'W': 'W', 'M': 'M'
        }
        # Use entry timeframe for entry checks
        timeframe = self.config.macd_timeframe.upper()
        granularity = timeframe_map.get(timeframe, 'H1')
        
        # Get enough candles for MACD calculation (need at least slow + signal periods)
        count = max(100, self.config.macd_slow_period + self.config.macd_signal_period + 20)
        
        try:
            candles = oanda_client.get_candles(oanda_pair, granularity=granularity, count=count)
            if not candles:
                return False, f"Could not fetch candles for {pair}"
            
            # Calculate MACD
            macd_data = self.calculate_macd(
                candles,
                fast=self.config.macd_fast_period,
                slow=self.config.macd_slow_period,
                signal=self.config.macd_signal_period
            )
            
            if not macd_data:
                return False, f"Could not calculate MACD for {pair}"
            
            current_above = macd_data['macd_above_signal']
            previous_above = macd_data['previous_macd_above_signal']
            crossover = macd_data['crossover_detected']
            
            # Check if MACD is in the correct direction for the trade
            macd_bullish = current_above  # MACD above signal = bullish
            macd_bearish = not current_above  # MACD below signal = bearish
            
            # Get previous state for this pair
            pair_state = self.macd_state.get(pair, {})
            last_state = pair_state.get('macd_above_signal')
            
            # Update state
            self.macd_state[pair] = {
                'macd_above_signal': current_above,
                'last_check_time': datetime.utcnow()
            }
            
            # If MACD is already in the correct direction and hasn't changed, don't trigger
            if last_state is not None:
                if is_long and current_above and last_state == current_above:
                    return False, f"MACD already bullish (no crossover detected)"
                elif not is_long and not current_above and last_state == current_above:
                    return False, f"MACD already bearish (no crossover detected)"
            
            # Check for crossover in the correct direction
            if is_long:
                # LONG trade: Need bullish crossover (MACD crosses above signal)
                if crossover and current_above and not previous_above:
                    return True, f"MACD bullish crossover detected (MACD: {macd_data['macd']:.5f}, Signal: {macd_data['signal']:.5f})"
                elif current_above:
                    return False, f"MACD already above signal (no crossover)"
                else:
                    return False, f"MACD below signal (waiting for bullish crossover)"
            else:
                # SHORT trade: Need bearish crossover (MACD crosses below signal)
                if crossover and not current_above and previous_above:
                    return True, f"MACD bearish crossover detected (MACD: {macd_data['macd']:.5f}, Signal: {macd_data['signal']:.5f})"
                elif not current_above:
                    return False, f"MACD already below signal (no crossover)"
                else:
                    return False, f"MACD above signal (waiting for bearish crossover)"
                    
        except Exception as e:
            self.logger.error(f"❌ Error checking MACD crossover for {pair}: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def check_macd_reverse_crossover(self, trade: ManagedTrade, oanda_client) -> bool:
        """
        Check if MACD has crossed in the opposite direction (should close trade)
        
        Args:
            trade: ManagedTrade to check
            oanda_client: OandaClient instance for fetching candles
            
        Returns:
            True if trade should be closed due to reverse crossover
        """
        if not self.config.macd_close_on_reverse:
            return False
        
        if self.config.execution_mode != ExecutionMode.MACD_CROSSOVER:
            return False
        
        # Normalize direction
        is_long = trade.direction.upper() in ['LONG', 'BUY']
        
        # Convert pair to OANDA format
        oanda_pair = trade.pair.replace('/', '_').replace('-', '_')
        
        # Map timeframe to OANDA granularity
        timeframe_map = {
            'M1': 'M1', 'M5': 'M5', 'M15': 'M15', 'M30': 'M30',
            'H1': 'H1', 'H4': 'H4', 'D': 'D', 'W': 'W', 'M': 'M'
        }
        # Use stop loss timeframe if specified, otherwise use entry timeframe
        sl_timeframe = self.config.macd_sl_timeframe
        if sl_timeframe:
            timeframe = sl_timeframe.upper()
        else:
            timeframe = self.config.macd_timeframe.upper()
        granularity = timeframe_map.get(timeframe, 'H1')
        
        # Get enough candles for MACD calculation
        count = max(100, self.config.macd_slow_period + self.config.macd_signal_period + 20)
        
        try:
            candles = oanda_client.get_candles(oanda_pair, granularity=granularity, count=count)
            if not candles:
                return False
            
            # Calculate MACD
            macd_data = self.calculate_macd(
                candles,
                fast=self.config.macd_fast_period,
                slow=self.config.macd_slow_period,
                signal=self.config.macd_signal_period
            )
            
            if not macd_data:
                return False
            
            current_above = macd_data['macd_above_signal']
            previous_above = macd_data['previous_macd_above_signal']
            crossover = macd_data['crossover_detected']
            
            # Check for reverse crossover
            if is_long:
                # LONG trade: Close if MACD crosses below signal (bearish crossover)
                if crossover and not current_above and previous_above:
                    self.logger.warning(
                        f"🔄 MACD reverse crossover for {trade.pair} {trade.direction}: "
                        f"Bearish crossover detected - closing trade"
                    )
                    return True
            else:
                # SHORT trade: Close if MACD crosses above signal (bullish crossover)
                if crossover and current_above and not previous_above:
                    self.logger.warning(
                        f"🔄 MACD reverse crossover for {trade.pair} {trade.direction}: "
                        f"Bullish crossover detected - closing trade"
                    )
                    return True
            
            return False
                    
        except Exception as e:
            self.logger.error(f"❌ Error checking MACD reverse crossover for {trade.pair}: {e}", exc_info=True)
            return False

    def check_dmi_reverse_crossover(self, trade: ManagedTrade, oanda_client) -> bool:
        """
        Check if +DI/-DI has crossed in the opposite direction (should close trade).
        LONG: close when +DI crosses below -DI (bearish). SHORT: close when +DI crosses above -DI (bullish).
        """
        is_long = (trade.direction or '').upper() in ('LONG', 'BUY')
        oanda_pair = trade.pair.replace('/', '_').replace('-', '_')
        timeframe_map = {
            'M1': 'M1', 'M5': 'M5', 'M15': 'M15', 'M30': 'M30',
            'H1': 'H1', 'H4': 'H4', 'D': 'D', 'W': 'W', 'M': 'M'
        }
        tf = (getattr(self.config, 'dmi_sl_timeframe', None) or 'H1').upper()
        granularity = timeframe_map.get(tf, 'H1')
        count = 50
        try:
            candles = oanda_client.get_candles(oanda_pair, granularity=granularity, count=count)
            if not candles:
                return False
            from src.indicators.dmi_analyzer import calculate_dmi
            d = calculate_dmi(candles)
            if not d:
                return False
            if is_long and d.get('crossover_bearish'):
                self.logger.warning(
                    f"🔄 DMI reverse crossover for {trade.pair} {trade.direction}: "
                    f"+DI crossed below -DI - closing trade"
                )
                return True
            if not is_long and d.get('crossover_bullish'):
                self.logger.warning(
                    f"🔄 DMI reverse crossover for {trade.pair} {trade.direction}: "
                    f"+DI crossed above -DI - closing trade"
                )
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Error checking DMI reverse crossover for {trade.pair}: {e}", exc_info=True)
            return False

    def _check_structure_atr_simple(
        self,
        trade_id: str,
        trade: ManagedTrade,
        current_price: float,
        oanda_client,
    ) -> bool:
        """
        ATR + structure (LLM/Fisher): structure+ATR at entry (set at open), BE at +1R, then trail to 1H EMA 26.
        No Phase 3 exits (no 4H DMI, spread spike, ADX collapse, EMA breakdown, time stop).
        Returns True if trade was closed (caller should continue).
        """
        try:
            initial_sl = getattr(trade, "initial_stop_loss", None) or trade.stop_loss
            if not initial_sl or initial_sl <= 0:
                return False
            is_long = (trade.direction or "").upper() in ("LONG", "BUY")
            risk_distance = abs(trade.entry_price - initial_sl)
            if risk_distance <= 0:
                return False
            if is_long:
                r_multiple = (current_price - trade.entry_price) / risk_distance
            else:
                r_multiple = (trade.entry_price - current_price) / risk_distance

            be_r = 1.0
            trail_r = 2.0

            if r_multiple >= be_r and not getattr(trade, "breakeven_applied", False):
                self.executor.update_stop_loss(trade_id, trade.entry_price, trade.pair)
                trade.stop_loss = trade.entry_price
                trade.current_sl = trade.entry_price
                trade.breakeven_applied = True
                self.logger.info(f"ATR+structure: {trade.pair} {trade.direction} BE at +{r_multiple:.1f}R")

            if r_multiple >= trail_r and oanda_client:
                oanda_pair = trade.pair.replace("/", "_").replace("-", "_")
                try:
                    candles_1h = oanda_client.get_candles(oanda_pair, "H1", 100)
                except Exception:
                    candles_1h = None
                if candles_1h and len(candles_1h) >= 26:
                    try:
                        import pandas as pd
                        from src.ft_dmi_ema import Indicators as FTIndicators
                        df_1h = pd.DataFrame(candles_1h)
                        for c in ["close"]:
                            if c in df_1h.columns:
                                df_1h[c] = pd.to_numeric(df_1h[c], errors="coerce")
                        df_1h = df_1h.dropna(subset=["close"])
                        if len(df_1h) >= 26:
                            ema26_1h = FTIndicators.ema(df_1h["close"], 26)
                            if len(ema26_1h) > 0:
                                ema_val = float(ema26_1h.iloc[-1])
                                if is_long and ema_val > trade.stop_loss and current_price > ema_val:
                                    self.executor.update_stop_loss(trade_id, ema_val, trade.pair)
                                    trade.stop_loss = ema_val
                                    trade.current_sl = ema_val
                                    trade.trailing_active = True
                                elif not is_long and ema_val < trade.stop_loss and current_price < ema_val:
                                    self.executor.update_stop_loss(trade_id, ema_val, trade.pair)
                                    trade.stop_loss = ema_val
                                    trade.current_sl = ema_val
                                    trade.trailing_active = True
                    except Exception as e:
                        self.logger.debug(f"ATR+structure trail (1H EMA 26): {e}")
            return False
        except Exception as e:
            self.logger.error(f"_check_structure_atr_simple: {e}", exc_info=True)
            return False

    def _check_structure_atr_staged(
        self,
        trade_id: str,
        trade: ManagedTrade,
        current_price: float,
        oanda_client,
    ) -> bool:
        """
        FT-DMI-EMA: Phase 2 staged profit (BE +1R, partial +2R, trail +3R to 1H EMA 26)
        and Phase 3 exits (4H DMI opposite, spread spike, ADX collapse, EMA breakdown, time stop).
        Returns True if trade was closed (caller should continue).
        """
        try:
            from src.ft_dmi_ema import (
                Indicators as FTIndicators,
                ProfitProtectionConfig,
                ExitConfig,
                InstrumentConfig as FTInstrumentConfig,
            )
            from src.ft_dmi_ema.stop_loss_calculator_ft_dmi_ema import TimeStopMonitor
            import pandas as pd
        except ImportError:
            return False
        try:
            initial_sl = getattr(trade, "initial_stop_loss", None) or trade.stop_loss
            if not initial_sl or initial_sl <= 0:
                return False
            is_long = (trade.direction or "").upper() in ("LONG", "BUY")
            risk_distance = abs(trade.entry_price - initial_sl)
            if risk_distance <= 0:
                return False
            if is_long:
                r_multiple = (current_price - trade.entry_price) / risk_distance
            else:
                r_multiple = (trade.entry_price - current_price) / risk_distance

            oanda_pair = trade.pair.replace("/", "_").replace("-", "_")

            # ---------- Phase 3: Exits ----------
            time_monitor = TimeStopMonitor()
            if trade.opened_at and time_monitor.should_exit_on_time(
                trade.opened_at, datetime.utcnow(), r_multiple
            )[0]:
                self.close_trade(trade_id, "FT-DMI-EMA time stop (setup invalidated)")
                return True

            if not oanda_client:
                return False
            try:
                candles_4h = oanda_client.get_candles(oanda_pair, "H4", 50)
                candles_1h = oanda_client.get_candles(oanda_pair, "H1", 100)
            except Exception:
                candles_4h = candles_1h = None
            if candles_4h and len(candles_4h) >= 20:
                df_4h = pd.DataFrame(candles_4h)
                for c in ["open", "high", "low", "close"]:
                    if c in df_4h.columns:
                        df_4h[c] = pd.to_numeric(df_4h[c], errors="coerce")
                df_4h = df_4h.dropna(subset=["high", "low", "close"])
                if len(df_4h) >= 5:
                    plus_di_4h, minus_di_4h, adx_4h = FTIndicators.dmi(df_4h, period=14)
                    if len(plus_di_4h) > 0 and len(minus_di_4h) > 0:
                        p4, m4 = plus_di_4h.iloc[-1], minus_di_4h.iloc[-1]
                        if is_long and m4 > p4:
                            self.close_trade(trade_id, "FT-DMI-EMA 4H DMI crossover (bearish)")
                            return True
                        if not is_long and p4 > m4:
                            self.close_trade(trade_id, "FT-DMI-EMA 4H DMI crossover (bullish)")
                            return True
                    if len(adx_4h) > 0 and adx_4h.iloc[-1] < getattr(ExitConfig, "ADX_COLLAPSE_THRESHOLD", 15):
                        self.close_trade(trade_id, "FT-DMI-EMA ADX collapse")
                        return True
            try:
                price_data = oanda_client.get_current_price(oanda_pair)
                if price_data and "spread" in price_data:
                    current_spread = float(price_data.get("spread", 0) or 0)
                    normal_spread = FTInstrumentConfig.MAX_SPREAD.get(oanda_pair, 2.0)
                    if current_spread > normal_spread * getattr(ExitConfig, "SPREAD_SPIKE_MULTIPLIER", 3.0):
                        self.close_trade(trade_id, f"FT-DMI-EMA spread spike ({current_spread:.1f} pips)")
                        return True
            except Exception:
                pass
            if candles_1h and len(candles_1h) >= 30:
                df_1h = pd.DataFrame(candles_1h)
                for c in ["open", "high", "low", "close"]:
                    if c in df_1h.columns:
                        df_1h[c] = pd.to_numeric(df_1h[c], errors="coerce")
                df_1h = df_1h.dropna(subset=["close"])
                if len(df_1h) >= 26:
                    ema9 = FTIndicators.ema(df_1h["close"], 9)
                    ema26 = FTIndicators.ema(df_1h["close"], 26)
                    if len(ema9) > 0 and len(ema26) > 0:
                        c9, c26 = ema9.iloc[-1], ema26.iloc[-1]
                        if is_long and current_price < c9 and current_price < c26:
                            self.close_trade(trade_id, "FT-DMI-EMA EMA structure breakdown (long)")
                            return True
                        if not is_long and current_price > c9 and current_price > c26:
                            self.close_trade(trade_id, "FT-DMI-EMA EMA structure breakdown (short)")
                            return True

            # ---------- Phase 2: Staged Profit Management ----------
            be_r = getattr(ProfitProtectionConfig, "BREAKEVEN_R_MULTIPLE", 1.0)
            partial_r = getattr(ProfitProtectionConfig, "PARTIAL_PROFIT_R_MULTIPLE", 2.0)
            partial_pct = getattr(ProfitProtectionConfig, "PARTIAL_PROFIT_CLOSE_PERCENT", 0.5)
            trail_r = getattr(ProfitProtectionConfig, "TRAILING_R_MULTIPLE", 3.0)

            # Phase 2.1: At +1R, move SL to breakeven
            if r_multiple >= be_r and not getattr(trade, "breakeven_applied", False):
                self.executor.update_stop_loss(trade_id, trade.entry_price, trade.pair)
                trade.stop_loss = trade.entry_price
                trade.current_sl = trade.entry_price
                trade.breakeven_applied = True
                self.logger.info(
                    f"📍 FT-DMI-EMA Phase 2.1: {trade.pair} {trade.direction} "
                    f"at +{r_multiple:.1f}R - SL moved to breakeven"
                )

            # Phase 2.2: At +2R, close 50% position and move SL to +1R
            if r_multiple >= partial_r and not getattr(trade, "partial_profit_taken", False):
                try:
                    from oandapyV20.endpoints.trades import TradeDetails
                    r = TradeDetails(accountID=self.executor.account_id, tradeID=trade_id)
                    self.executor.request(r, "trade_details")
                    units = int(r.response.get("trade", {}).get("currentUnits", 0))
                    if units != 0:
                        units_to_close = int(abs(units) * partial_pct)
                        if units_to_close > 0 and self.executor.close_trade_partial(
                            trade_id, units_to_close, is_long, trade.pair, "Partial +2R"
                        ):
                            # Move SL to +1R to lock in profit on remaining position
                            one_r_price = (
                                trade.entry_price + risk_distance
                                if is_long
                                else trade.entry_price - risk_distance
                            )
                            self.executor.update_stop_loss(trade_id, one_r_price, trade.pair)
                            trade.stop_loss = one_r_price
                            trade.current_sl = one_r_price
                            trade.partial_profit_taken = True
                            self.logger.info(
                                f"💰 FT-DMI-EMA Phase 2.2: {trade.pair} {trade.direction} "
                                f"at +{r_multiple:.1f}R - Closed {partial_pct*100:.0f}% position, "
                                f"SL locked at +1R ({one_r_price:.5f})"
                            )
                except Exception as e:
                    self.logger.debug(f"FT-DMI-EMA partial close error: {e}")

            # Phase 2.3: At +3R, trail SL to 1H EMA 26
            if r_multiple >= trail_r and not getattr(trade, "trailing_active", False) and candles_1h and len(candles_1h) >= 26:
                try:
                    df_1h = pd.DataFrame(candles_1h)
                    for c in ["close"]:
                        if c in df_1h.columns:
                            df_1h[c] = pd.to_numeric(df_1h[c], errors="coerce")
                    df_1h = df_1h.dropna(subset=["close"])
                    if len(df_1h) >= 26:
                        ema26_1h = FTIndicators.ema(df_1h["close"], 26)
                        if len(ema26_1h) > 0:
                            ema_val = float(ema26_1h.iloc[-1])
                            # Only move SL if EMA is closer to entry than current SL (protects profit)
                            if is_long and ema_val > trade.stop_loss and current_price > ema_val:
                                self.executor.update_stop_loss(trade_id, ema_val, trade.pair)
                                trade.stop_loss = ema_val
                                trade.current_sl = ema_val
                                trade.trailing_active = True
                                self.logger.info(
                                    f"📈 FT-DMI-EMA Phase 2.3: {trade.pair} {trade.direction} "
                                    f"at +{r_multiple:.1f}R - Trailing to 1H EMA 26 ({ema_val:.5f})"
                                )
                            elif not is_long and ema_val < trade.stop_loss and current_price < ema_val:
                                self.executor.update_stop_loss(trade_id, ema_val, trade.pair)
                                trade.stop_loss = ema_val
                                trade.current_sl = ema_val
                                trade.trailing_active = True
                                self.logger.info(
                                    f"📉 FT-DMI-EMA Phase 2.3: {trade.pair} {trade.direction} "
                                    f"at +{r_multiple:.1f}R - Trailing to 1H EMA 26 ({ema_val:.5f})"
                                )
                except Exception as e:
                    self.logger.debug(f"FT-DMI-EMA Phase 2.3 EMA trail error: {e}")

            # Phase 2.3b: Update trailing distance if already trailing (follow EMA closely)
            if getattr(trade, "trailing_active", False) and candles_1h and len(candles_1h) >= 26:
                try:
                    df_1h = pd.DataFrame(candles_1h)
                    for c in ["close"]:
                        if c in df_1h.columns:
                            df_1h[c] = pd.to_numeric(df_1h[c], errors="coerce")
                    df_1h = df_1h.dropna(subset=["close"])
                    if len(df_1h) >= 26:
                        ema26_1h = FTIndicators.ema(df_1h["close"], 26)
                        if len(ema26_1h) > 0:
                            ema_val = float(ema26_1h.iloc[-1])
                            # Continuously update SL to follow EMA 26 upward (LONG) or downward (SHORT)
                            if is_long and ema_val > trade.current_sl:
                                self.executor.update_stop_loss(trade_id, ema_val, trade.pair)
                                trade.stop_loss = ema_val
                                trade.current_sl = ema_val
                                self.logger.debug(
                                    f"🔄 FT-DMI-EMA: Updated trailing to 1H EMA 26 ({ema_val:.5f})"
                                )
                            elif not is_long and ema_val < trade.current_sl:
                                self.executor.update_stop_loss(trade_id, ema_val, trade.pair)
                                trade.stop_loss = ema_val
                                trade.current_sl = ema_val
                                self.logger.debug(
                                    f"🔄 FT-DMI-EMA: Updated trailing to 1H EMA 26 ({ema_val:.5f})"
                                )
                except Exception as e:
                    self.logger.debug(f"FT-DMI-EMA continuous trailing update error: {e}")

            return False
        except Exception as e:
            self.logger.error(f"_check_structure_atr_staged: {e}", exc_info=True)
            return False


class RiskController:
    """Controls risk and validates trades"""
    
    def __init__(self, config: TradeConfig):
        self.config = config
        self.daily_pnl = 0.0
        self.daily_reset_time = datetime.utcnow().date()
        self.consecutive_losses = 0  # Circuit breaker: reset on win
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        import logging
        logger = logging.getLogger('RiskController')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def check_daily_reset(self):
        """Reset daily counters if new day"""
        today = datetime.utcnow().date()
        if today > self.daily_reset_time:
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.daily_reset_time = today
            self.logger.info(f"📅 Daily risk counters reset for {today}")
    
    def validate_opportunity(self, opp: Dict, llm_weights: Dict) -> Tuple[bool, str]:
        """Validate if opportunity meets consensus requirements

        Scanner opportunities (FT, DMI-EMA, etc.) bypass consensus checks since they're
        based on technical analysis, not LLM recommendations.
        LLM opportunities must meet min_consensus_level and required_llms requirements.
        """

        # Scanner opportunities bypass consensus checks
        source = opp.get('source', '').upper()
        scanner_sources = ('FT_DMI_EMA', 'DMI_EMA', 'DMI', 'FISHER', 'FT')
        if any(scanner in source for scanner in scanner_sources):
            return True, "OK (scanner opportunity - no consensus required)"

        # LLM opportunities must meet consensus requirements
        consensus_level = opp.get('consensus_level', 1)
        llm_sources = opp.get('llm_sources', [])

        # Check minimum consensus
        if consensus_level < self.config.min_consensus_level:
            return False, f"Consensus level {consensus_level} < minimum {self.config.min_consensus_level}"

        # Check if any required LLMs are present
        # Safely check required_llms (handle None, empty list, or missing attribute)
        try:
            required_llms = getattr(self.config, 'required_llms', None)
            if required_llms and isinstance(required_llms, list) and len(required_llms) > 0:
                llm_sources_lower = [s.lower() for s in llm_sources] if llm_sources else []
                required_llms_lower = [llm.lower() for llm in required_llms]
                found_required = any(req_llm in llm_sources_lower for req_llm in required_llms_lower)
                if not found_required:
                    return False, f"None of the required LLMs {required_llms} are in consensus (sources: {llm_sources})"
        except (AttributeError, TypeError) as e:
            self.logger.warning(f"Error checking required_llms: {e}, allowing trade")

        return True, "OK"
    
    def can_take_loss(
        self, potential_loss: float, account_balance: Optional[float] = None
    ) -> Tuple[bool, str]:
        """Check if we can afford potential loss. If max_daily_loss_pct is set and account_balance given, also enforce 2% daily limit."""
        self.check_daily_reset()
        max_pct = getattr(self.config, 'max_daily_loss_pct', None)
        if max_pct is not None and account_balance is not None and account_balance > 0:
            daily_loss_pct = abs(self.daily_pnl) / account_balance * 100.0
            if daily_loss_pct >= max_pct:
                return False, (
                    f"Daily loss limit reached ({daily_loss_pct:.2f}% >= {max_pct}% of account)"
                )
        if abs(self.daily_pnl) + potential_loss > self.config.max_daily_loss:
            return False, f"Would exceed daily loss limit (current: {self.daily_pnl:.2f})"
        return True, "OK"

    def circuit_breaker_ok(self) -> Tuple[bool, str]:
        """Return (False, reason) if circuit breaker triggered (e.g. 5 consecutive losses)."""
        self.check_daily_reset()
        max_losses = getattr(self.config, 'consecutive_losses_max', 5)
        if self.consecutive_losses >= max_losses:
            return False, (
                f"Circuit breaker: {self.consecutive_losses} consecutive losses (max {max_losses}). "
                "No new opens until next win or daily reset."
            )
        return True, "OK"
    
    def record_trade_close(self, realized_pnl: float):
        """Record trade closure for daily tracking and consecutive loss count."""
        self.check_daily_reset()
        self.daily_pnl += realized_pnl
        if realized_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        self.logger.info(
            f"💰 Daily P&L updated: {self.daily_pnl:.2f}, consecutive_losses: {self.consecutive_losses}"
        )
