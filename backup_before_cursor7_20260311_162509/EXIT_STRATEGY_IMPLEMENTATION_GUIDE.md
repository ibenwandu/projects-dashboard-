# Exit Strategy Implementation Guide
## Code Examples & Integration Points for Trade-Alerts

**Date**: March 6, 2026
**For**: Scalp-Engine integration
**Status**: Ready for development

---

## Overview

This document provides specific code examples to implement the recommended exit strategies in Trade-Alerts. Focus areas:

1. ATR-based take profit calculation
2. Half-and-run position splitting
3. Trailing stop implementation
4. EMA-based exit logic
5. Time-based position management
6. Safety checks to prevent early manual closes

---

## 1. ATR-Based Take Profit Calculation

### Location: `src/market_bridge.py`

This module exports opportunities to Scalp-Engine. Add ATR calculation when exporting:

```python
# In market_bridge.py, export_market_state() function

import talib
import numpy as np

def add_atr_to_opportunities(opportunities, price_data):
    """
    Add ATR-based take profit levels to opportunities.

    Args:
        opportunities: List of opportunity dicts with entry/stop_loss
        price_data: Dict with {pair: {'high': [...], 'low': [...], 'close': [...]}}

    Returns:
        opportunities with added fields:
        - atr_value: Current ATR in price units
        - take_profit_atr: Entry + (ATR × 2.0)
        - trailing_stop_distance: ATR × 1.0
    """

    for opp in opportunities:
        pair = opp['pair']  # e.g., "EUR/USD"

        # Skip if no price data available
        if pair not in price_data:
            logger.warning(f"No price data for {pair}, using fixed TP")
            opp['atr_value'] = None
            opp['take_profit_atr'] = opp.get('exit')  # Fall back to existing TP
            opp['trailing_stop_distance'] = 0.0020  # 20 pips default
            continue

        prices = price_data[pair]

        # Ensure we have minimum 14 candles for ATR (standard period)
        if len(prices['high']) < 14:
            logger.warning(f"{pair} insufficient price history for ATR")
            opp['atr_value'] = None
            opp['take_profit_atr'] = opp.get('exit')
            opp['trailing_stop_distance'] = 0.0020
            continue

        try:
            # Calculate ATR(14) - standard period
            atr = talib.ATR(
                np.array(prices['high'], dtype=float),
                np.array(prices['low'], dtype=float),
                np.array(prices['close'], dtype=float),
                timeperiod=14
            )

            # Get latest ATR value (last element)
            current_atr = atr[-1]

            # Convert to pip value (or price units depending on pair)
            # For most pairs: 1 pip = 0.0001 (so 30 pips = 0.0030)
            # For JPY pairs: 1 pip = 0.01 (so 30 pips = 0.30)

            pair_base = pair.split('/')[1]  # Get quote currency
            if 'JPY' in pair_base:
                atr_pips = current_atr / 0.01
                pip_value = 0.01
            else:
                atr_pips = current_atr / 0.0001
                pip_value = 0.0001

            # Store ATR value
            opp['atr_value'] = current_atr
            opp['atr_pips'] = atr_pips

            # Calculate take profit targets
            entry_price = opp['entry']
            direction = opp['direction']  # 'BUY' or 'SELL'

            if direction.upper() == 'BUY':
                # For longs: TP = entry + (ATR × 2.0)
                opp['take_profit_atr'] = entry_price + (current_atr * 2.0)
                opp['take_profit_runner'] = entry_price + (current_atr * 3.5)
            else:
                # For shorts: TP = entry - (ATR × 2.0)
                opp['take_profit_atr'] = entry_price - (current_atr * 2.0)
                opp['take_profit_runner'] = entry_price - (current_atr * 3.5)

            # Trailing stop distance
            opp['trailing_stop_distance'] = current_atr * 1.0
            opp['trailing_stop_distance_pips'] = atr_pips

            logger.info(
                f"ATR calculated for {pair}: "
                f"ATR={atr_pips:.1f} pips, "
                f"TP_PRIMARY={opp['take_profit_atr']:.5f}, "
                f"TRAIL_DIST={atr_pips:.1f} pips"
            )

        except Exception as e:
            logger.error(f"Failed to calculate ATR for {pair}: {e}")
            opp['atr_value'] = None
            opp['take_profit_atr'] = opp.get('exit')
            opp['trailing_stop_distance'] = 0.0020

    return opportunities


# Usage in export_market_state():
def export_market_state(self):
    # ... existing code ...

    # After parsing opportunities from LLMs
    opportunities = self._parse_opportunities_from_llms(...)

    # Add ATR-based TP
    price_data = self._get_current_price_data(opportunities)
    opportunities = add_atr_to_opportunities(opportunities, price_data)

    # Export to market_state.json
    market_state = {
        'opportunities': opportunities,
        'timestamp': datetime.now().isoformat(),
        # ... rest of market state ...
    }

    with open('market_state.json', 'w') as f:
        json.dump(market_state, f, indent=2)
```

---

## 2. Position Splitting for Half-and-Run Strategy

### Location: `Scalp-Engine/auto_trader_core.py`

Modify `TradeExecutor.open_trade()` to split position into two halves:

```python
# In TradeExecutor class

class TradeExecutor:

    def open_trade(self, opportunity, position_size, mode='PLACE_PENDING'):
        """
        Open a trade with position splitting for half-and-run strategy.

        Args:
            opportunity: Dict with entry, stop_loss, take_profit, etc.
            position_size: Total position size in units
            mode: 'PLACE_PENDING' or 'MARKET'

        Returns:
            Tuple of (trade_object, success_bool)
        """

        # Calculate split positions
        position_first_half = int(position_size / 2)
        position_runner_half = position_size - position_first_half

        self.logger.info(
            f"Opening {opportunity['pair']} {opportunity['direction']} "
            f"with position split: {position_first_half} + {position_runner_half}"
        )

        try:
            # Get take profit levels
            if opportunity.get('atr_value'):
                # Use ATR-based TP (primary)
                take_profit_1 = opportunity['take_profit_atr']
                trailing_distance = opportunity['trailing_stop_distance']
            else:
                # Fall back to fixed TP
                take_profit_1 = opportunity['exit']
                trailing_distance = 0.0020  # 20 pips default

            entry_price = opportunity['entry']
            stop_loss = opportunity['stop_loss']

            # **IMPORTANT**: Create trade in OANDA with FULL position size
            # We'll manage the split client-side
            trade = self._place_order_oanda(
                instrument=opportunity['pair'],
                units=position_size if opportunity['direction'].upper() == 'BUY'
                      else -position_size,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=None,  # We'll manage TP manually
                type=mode
            )

            if not trade:
                self.logger.error(f"Failed to open trade for {opportunity['pair']}")
                return None, False

            # IMPORTANT: Store split information in trade object for later management
            trade.first_half_size = position_first_half
            trade.runner_half_size = position_runner_half
            trade.first_tp_level = take_profit_1
            trade.trailing_distance = trailing_distance
            trade.has_closed_first_half = False  # Track if first half closed

            self.logger.info(
                f"Trade opened: {trade.id} "
                f"First TP: {take_profit_1:.5f} (size={position_first_half}), "
                f"Runner: Trail distance {trailing_distance:.5f} (size={position_runner_half})"
            )

            return trade, True

        except Exception as e:
            self.logger.error(f"Exception opening trade: {e}", exc_info=True)
            return None, False


    def manage_open_trade(self, trade, current_price):
        """
        Manage open trade based on split position strategy.
        Called on every price update.

        Updates:
        - Close first half at first TP
        - Manage second half with trailing stop
        - Time-based close if max hold exceeded
        """

        # Get direction for comparison
        direction = 'LONG' if trade.units > 0 else 'SHORT'

        # ===== FIRST HALF MANAGEMENT =====
        if not trade.has_closed_first_half:
            first_tp = trade.first_tp_level

            # Check if first TP is hit
            if direction == 'LONG' and current_price >= first_tp:
                self.logger.info(
                    f"First TP hit for {trade.id}: "
                    f"{current_price:.5f} >= {first_tp:.5f}"
                )
                self.close_partial(trade, trade.first_half_size)
                trade.has_closed_first_half = True

                # Move stop loss to breakeven on remaining position
                self.move_stop_to_breakeven(trade)

            elif direction == 'SHORT' and current_price <= first_tp:
                self.logger.info(
                    f"First TP hit for {trade.id}: "
                    f"{current_price:.5f} <= {first_tp:.5f}"
                )
                self.close_partial(trade, trade.first_half_size)
                trade.has_closed_first_half = True

                # Move stop loss to breakeven on remaining position
                self.move_stop_to_breakeven(trade)

        # ===== RUNNER HALF MANAGEMENT =====
        if trade.has_closed_first_half:
            # Update trailing stop
            self.update_trailing_stop(trade, current_price, trade.trailing_distance)

        # ===== TIME-BASED MANAGEMENT =====
        if self._exceeds_max_hold_time(trade, max_hours=4):
            self.logger.warning(
                f"Max hold time (4 hours) exceeded for {trade.id}, closing position"
            )
            if direction == 'LONG':
                if current_price > trade.open_price:
                    self.close_partial(trade, trade.runner_half_size, reason='time_limit_profit')
                else:
                    self.close_partial(trade, trade.runner_half_size, reason='time_limit_loss')
            else:
                if current_price < trade.open_price:
                    self.close_partial(trade, trade.runner_half_size, reason='time_limit_profit')
                else:
                    self.close_partial(trade, trade.runner_half_size, reason='time_limit_loss')


    def close_partial(self, trade, close_size, reason=''):
        """
        Close partial position (half or portion of trade).
        """
        try:
            result = self._close_trade_oanda(
                trade_id=trade.id,
                units=close_size
            )

            if result:
                self.logger.info(
                    f"Partial close: {trade.id}, "
                    f"Closed {close_size} units, "
                    f"Remaining {trade.units - close_size}, "
                    f"Reason: {reason}"
                )
                return True
            else:
                self.logger.error(f"Failed to partially close {trade.id}")
                return False

        except Exception as e:
            self.logger.error(f"Exception in close_partial: {e}")
            return False


    def move_stop_to_breakeven(self, trade):
        """
        Move stop loss to breakeven (entry price) on remaining position.
        This protects capital while allowing runner to continue.
        """
        try:
            result = self._update_stop_loss(
                trade_id=trade.id,
                new_stop_loss=trade.entry_price
            )

            if result:
                self.logger.info(
                    f"Stop loss moved to breakeven for {trade.id}: "
                    f"SL={trade.entry_price:.5f}"
                )
                return True
            else:
                self.logger.error(f"Failed to move stop to breakeven for {trade.id}")
                return False

        except Exception as e:
            self.logger.error(f"Exception moving stop to breakeven: {e}")
            return False


    def update_trailing_stop(self, trade, current_price, trail_distance):
        """
        Update trailing stop: follows price UP but stays PUT on reversal.

        Args:
            trade: Trade object with current stop_loss
            current_price: Current market price
            trail_distance: Distance to trail (e.g., 0.0030 = 30 pips)
        """

        direction = 'LONG' if trade.units > 0 else 'SHORT'

        if direction == 'LONG':
            # For longs: Trail is below current price
            new_trailing_stop = current_price - trail_distance

            # Only move stop UP (tighter), never DOWN (looser)
            if new_trailing_stop > trade.stop_loss:
                try:
                    result = self._update_stop_loss(
                        trade_id=trade.id,
                        new_stop_loss=new_trailing_stop
                    )

                    if result:
                        self.logger.debug(
                            f"Trailing stop updated for {trade.id}: "
                            f"SL {trade.stop_loss:.5f} → {new_trailing_stop:.5f}"
                        )
                        trade.stop_loss = new_trailing_stop
                        return True

                except Exception as e:
                    self.logger.error(f"Exception updating trailing stop: {e}")

        elif direction == 'SHORT':
            # For shorts: Trail is above current price
            new_trailing_stop = current_price + trail_distance

            # Only move stop DOWN (tighter), never UP (looser)
            if new_trailing_stop < trade.stop_loss:
                try:
                    result = self._update_stop_loss(
                        trade_id=trade.id,
                        new_stop_loss=new_trailing_stop
                    )

                    if result:
                        self.logger.debug(
                            f"Trailing stop updated for {trade.id}: "
                            f"SL {trade.stop_loss:.5f} → {new_trailing_stop:.5f}"
                        )
                        trade.stop_loss = new_trailing_stop
                        return True

                except Exception as e:
                    self.logger.error(f"Exception updating trailing stop: {e}")


    def _exceeds_max_hold_time(self, trade, max_hours=4):
        """Check if trade has exceeded maximum hold time."""
        from datetime import datetime, timedelta

        time_held = datetime.now() - trade.open_time
        max_duration = timedelta(hours=max_hours)

        if time_held > max_duration:
            hours = time_held.total_seconds() / 3600
            self.logger.warning(
                f"{trade.id} held for {hours:.1f} hours (max {max_hours})"
            )
            return True

        return False
```

---

## 3. EMA-Based Exit Logic for Runner Half

### Location: `Scalp-Engine/src/exit_manager.py` (new file)

Create a new module to manage EMA-based exits:

```python
# Scalp-Engine/src/exit_manager.py

import logging
import talib
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class EMAExitManager:
    """
    Manage exits based on EMA crossovers.
    Exit when price crosses key EMA levels.
    """

    def __init__(self, ema_periods: List[int] = None):
        """
        Args:
            ema_periods: List of EMA periods to calculate [e.g., 9, 21, 50, 200]
        """
        self.ema_periods = ema_periods or [9, 21, 50, 200]
        self.ema_cache = {}  # Cache of calculated EMAs


    def calculate_emas(self, close_prices: np.ndarray) -> Dict[int, float]:
        """
        Calculate multiple EMAs.

        Args:
            close_prices: Array of closing prices (most recent at end)

        Returns:
            Dict with {period: current_ema_value}
        """

        if len(close_prices) < max(self.ema_periods):
            logger.warning(
                f"Insufficient prices for EMA calculation. "
                f"Need {max(self.ema_periods)}, have {len(close_prices)}"
            )
            return {}

        emas = {}

        try:
            close_array = np.array(close_prices, dtype=float)

            for period in self.ema_periods:
                ema = talib.EMA(close_array, timeperiod=period)
                emas[period] = ema[-1]  # Get latest EMA value

            return emas

        except Exception as e:
            logger.error(f"Error calculating EMAs: {e}")
            return {}


    def should_exit_on_ema_cross(
        self,
        current_price: float,
        direction: str,
        emas: Dict[int, float],
        primary_ema_period: int = 21
    ) -> bool:
        """
        Check if trade should exit based on EMA crossover.

        Args:
            current_price: Current market price
            direction: 'LONG' or 'SHORT'
            emas: Dict of {period: ema_value}
            primary_ema_period: Which EMA to use for exit (default 21)

        Returns:
            True if should exit, False otherwise
        """

        if primary_ema_period not in emas:
            logger.warning(f"EMA {primary_ema_period} not in calculated EMAs")
            return False

        primary_ema = emas[primary_ema_period]

        if direction.upper() == 'LONG':
            # For long trades: Exit if price closes BELOW 21-EMA
            if current_price < primary_ema:
                logger.info(
                    f"EMA exit signal for LONG: "
                    f"Price {current_price:.5f} < EMA {primary_ema:.5f}"
                )
                return True

        elif direction.upper() == 'SHORT':
            # For short trades: Exit if price closes ABOVE 21-EMA
            if current_price > primary_ema:
                logger.info(
                    f"EMA exit signal for SHORT: "
                    f"Price {current_price:.5f} > EMA {primary_ema:.5f}"
                )
                return True

        return False


    def get_next_ema_level(
        self,
        current_price: float,
        direction: str,
        emas: Dict[int, float]
    ) -> Optional[float]:
        """
        Get the next EMA level that price will likely hit.
        Useful for setting dynamic TP on runner portion.

        Args:
            current_price: Current price
            direction: 'LONG' or 'SHORT'
            emas: Dict of calculated EMAs

        Returns:
            Next EMA level or None
        """

        # Get relevant EMAs (9, 21, 50) in order
        relevant_emas = [emas.get(p) for p in [9, 21, 50] if p in emas]
        relevant_emas = [e for e in relevant_emas if e is not None]

        if not relevant_emas:
            return None

        if direction.upper() == 'LONG':
            # For longs: Find first EMA above current price
            above = [e for e in relevant_emas if e > current_price]
            return min(above) if above else None

        elif direction.upper() == 'SHORT':
            # For shorts: Find first EMA below current price
            below = [e for e in relevant_emas if e < current_price]
            return max(below) if below else None

        return None


class SupportResistanceExitManager:
    """
    Manage exits based on support/resistance levels.
    Exit at or near key levels where price naturally reverses.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)


    def identify_key_levels(self, recent_prices: Dict) -> Dict:
        """
        Identify support and resistance levels from recent price action.

        Args:
            recent_prices: Dict with {
                'high': [h1, h2, ...],
                'low': [l1, l2, ...],
                'close': [c1, c2, ...]
            }

        Returns:
            Dict with {
                'daily_high': float,
                'daily_low': float,
                'weekly_high': float,
                'weekly_low': float,
                'round_number': float
            }
        """

        levels = {}

        try:
            # Daily high/low (last 24 candles at 1H)
            recent_h = recent_prices['high'][-24:] if len(recent_prices['high']) >= 24 else recent_prices['high']
            recent_l = recent_prices['low'][-24:] if len(recent_prices['low']) >= 24 else recent_prices['low']

            levels['daily_high'] = max(recent_h)
            levels['daily_low'] = min(recent_l)

            # Weekly high/low (last 168 candles at 1H = 7 days)
            week_h = recent_prices['high'][-168:] if len(recent_prices['high']) >= 168 else recent_prices['high']
            week_l = recent_prices['low'][-168:] if len(recent_prices['low']) >= 168 else recent_prices['low']

            levels['weekly_high'] = max(week_h)
            levels['weekly_low'] = min(week_l)

            # Round number (nearest 0.0050 for majors, 0.50 for JPY)
            current_price = recent_prices['close'][-1]
            round_interval = 0.0050 if abs(current_price) < 10 else 0.50
            levels['round_number'] = round(current_price / round_interval) * round_interval

            self.logger.debug(f"Key levels identified: {levels}")
            return levels

        except Exception as e:
            self.logger.error(f"Error identifying key levels: {e}")
            return {}


    def is_at_support_resistance(
        self,
        current_price: float,
        levels: Dict,
        tolerance: float = 0.00010
    ) -> Optional[str]:
        """
        Check if price is at/near support or resistance.

        Args:
            current_price: Current price
            levels: Dict of key levels
            tolerance: How close to count as "at" level (default 1 pip)

        Returns:
            'DAILY_HIGH', 'DAILY_LOW', 'WEEKLY_HIGH', 'WEEKLY_LOW', 'ROUND' or None
        """

        for level_name, level_price in levels.items():
            if abs(current_price - level_price) < tolerance:
                self.logger.info(
                    f"Price at {level_name}: "
                    f"{current_price:.5f} near {level_price:.5f}"
                )
                return level_name

        return None
```

---

## 4. Integration into Main Loop

### Location: `Scalp-Engine/scalp_engine.py`

Add exit management to the main trading loop:

```python
# In scalp_engine.py main loop (around line 300-400)

from src.exit_manager import EMAExitManager, SupportResistanceExitManager

class ScalpEngine:

    def __init__(self):
        # ... existing init code ...
        self.ema_exit_manager = EMAExitManager(ema_periods=[9, 21, 50, 200])
        self.sr_exit_manager = SupportResistanceExitManager()


    def update_open_trades(self):
        """
        Update all open trades:
        - First half: Check if TP hit
        - Runner half: Check trailing stop and EMA exit
        - Time limit: Check if max hold exceeded
        """

        active_trades = self.position_manager.get_open_trades()

        for trade in active_trades:
            try:
                # Get current price
                current_price = self.price_monitor.get_current_price(trade.pair)

                if not current_price:
                    self.logger.warning(f"No price available for {trade.pair}")
                    continue

                # Manage trade based on strategy
                if hasattr(trade, 'first_half_size'):  # Half-and-run strategy

                    # ===== FIRST HALF MANAGEMENT =====
                    if not trade.has_closed_first_half:
                        if self._check_first_tp_hit(trade, current_price):
                            self.executor.close_partial(
                                trade,
                                trade.first_half_size,
                                reason='first_tp_hit'
                            )
                            trade.has_closed_first_half = True
                            self.executor.move_stop_to_breakeven(trade)

                    # ===== RUNNER HALF MANAGEMENT =====
                    if trade.has_closed_first_half:

                        # Option 1: Check EMA exit
                        if self._should_exit_on_ema(trade, current_price):
                            self.executor.close_partial(
                                trade,
                                trade.runner_half_size,
                                reason='ema_exit'
                            )

                        # Option 2: Update trailing stop
                        else:
                            self.executor.update_trailing_stop(
                                trade,
                                current_price,
                                trade.trailing_distance
                            )

                    # Check time limit
                    if self.executor._exceeds_max_hold_time(trade, max_hours=4):
                        self.executor.close_partial(
                            trade,
                            trade.runner_half_size,
                            reason='time_limit'
                        )

            except Exception as e:
                self.logger.error(f"Error updating trade {trade.id}: {e}")
                continue


    def _check_first_tp_hit(self, trade, current_price) -> bool:
        """Check if first take profit level is hit."""

        direction = 'LONG' if trade.units > 0 else 'SHORT'
        first_tp = trade.first_tp_level

        if direction == 'LONG':
            return current_price >= first_tp
        else:
            return current_price <= first_tp


    def _should_exit_on_ema(self, trade, current_price) -> bool:
        """
        Check if EMA exit condition is met for runner portion.
        """

        try:
            # Get recent price history
            prices = self.price_monitor.get_recent_prices(
                pair=trade.pair,
                bars=200,  # Get 200 candles for EMA
                timeframe='H1'  # Use hourly
            )

            if not prices or len(prices['close']) < 50:
                return False

            # Calculate EMAs
            emas = self.ema_exit_manager.calculate_emas(
                np.array(prices['close'], dtype=float)
            )

            if not emas:
                return False

            # Check EMA exit signal
            direction = 'LONG' if trade.units > 0 else 'SHORT'
            return self.ema_exit_manager.should_exit_on_ema_cross(
                current_price=current_price,
                direction=direction,
                emas=emas,
                primary_ema_period=21
            )

        except Exception as e:
            self.logger.error(f"Error checking EMA exit: {e}")
            return False
```

---

## 5. Safety Check: Prevent Manual Closure of Winners

### Location: `Scalp-Engine/config_api_server.py`

Add validation to API endpoint that handles trade closure:

```python
# In config_api_server.py, add this validation

@app.route('/trades/close/<trade_id>', methods=['POST'])
def close_trade(trade_id):
    """
    API endpoint to close a trade.

    SAFETY: Prevents manual closure of profitable trades in AUTO mode
    """

    request_data = request.get_json() or {}
    reason = request_data.get('reason', 'manual')

    try:
        # Get the trade
        trade = position_manager.get_trade(trade_id)

        if not trade:
            return {'error': f'Trade {trade_id} not found'}, 404

        # SAFETY CHECK 1: Check if trade is profitable
        current_price = price_monitor.get_current_price(trade.pair)

        if current_price:
            pnl = calculate_pnl(trade, current_price)

            # Block manual close of winning trades (except in MONITOR mode)
            if pnl > 0 and TRADING_MODE != 'MONITOR':
                return {
                    'error': 'Cannot manually close profitable trades in AUTO/MANUAL mode',
                    'trade_id': trade_id,
                    'pnl': pnl,
                    'trading_mode': TRADING_MODE
                }, 403

        # SAFETY CHECK 2: Verify reason is documented
        if reason == 'manual' and TRADING_MODE == 'AUTO':
            logger.warning(
                f"SAFETY: Manual close attempted on {trade_id} in AUTO mode. "
                f"PnL={pnl}. Denying unless explicitly approved."
            )
            return {
                'error': 'Manual closes not allowed in AUTO mode. Use MANUAL mode or MONITOR mode.',
                'allowed_reasons': ['time_limit', 'ema_exit', 'first_tp_hit']
            }, 403

        # All checks passed, close the trade
        result = position_manager.close_trade(trade_id, reason=reason)

        return {
            'success': result,
            'trade_id': trade_id,
            'reason': reason
        }, 200

    except Exception as e:
        logger.error(f"Error closing trade {trade_id}: {e}")
        return {'error': str(e)}, 500
```

---

## 6. Configuration & Tuning Parameters

### Location: `.env` file additions

Add these environment variables to control exit behavior:

```bash
# Take Profit Parameters
ATR_TP_MULTIPLIER=2.0           # TP = Entry + (ATR × 2.0)
ATR_RUNNER_MULTIPLIER=3.5       # Runner TP = Entry + (ATR × 3.5)

# Trailing Stop Parameters
ATR_TRAIL_MULTIPLIER=1.0        # Trail distance = ATR × 1.0
FIXED_TRAIL_PIPS=20             # Fixed trailing distance if ATR unavailable

# Position Split Parameters
POSITION_SPLIT_RATIO=0.5        # 50/50 split (0.5 = 50% / 50%)
FIRST_TP_RATIO=1.5              # First TP = Entry + (Risk × 1.5)

# Time Limits
MAX_HOLD_HOURS=4                # Maximum hold time for intraday (hours)
MAX_HOLD_DAYS=3                 # Maximum hold time for swing (days)

# EMA Exit Parameters
EMA_EXIT_PERIOD=21              # Which EMA to use for exit
EMA_EXIT_ENABLED=true           # Enable EMA-based exits for runners

# Support/Resistance Parameters
SR_EXIT_ENABLED=true            # Enable SR level exits
SR_TOLERANCE=0.00010            # Tolerance for SR level hits (0.0001 = 1 pip)

# Safety Parameters
PREVENT_MANUAL_CLOSE_WINNERS=true  # Prevent manual closes of profitable trades
MAX_EARLY_CLOSES_PER_DAY=3         # Allow max 3 early closes per day
```

---

## 7. Testing Checklist

Before deploying exit strategy changes:

```markdown
## Pre-Deployment Testing

### Unit Tests
- [ ] ATR calculation returns valid values
- [ ] EMA calculation matches other tools
- [ ] Position split arithmetic is correct
- [ ] TP levels are on correct side of entry
- [ ] Trailing stop only moves tighter, never looser
- [ ] Time limit calculation is accurate

### Integration Tests
- [ ] Open trade with split positions
- [ ] First TP closes exactly 50% at target
- [ ] Remaining 50% gets trailing stop
- [ ] EMA exit closes runner correctly
- [ ] Time limit closes after 4 hours
- [ ] API prevents manual close of winners

### Manual Tests (MONITOR mode)
- [ ] Run for 2 hours, verify no execution
- [ ] Check TP levels in logs (realistic values?)
- [ ] Verify trailing stop movements are reasonable
- [ ] Confirm no manual closes are needed

### Live Test (MANUAL mode)
- [ ] Run for 24 hours with real trades
- [ ] Verify first TP is hit within 10% of target
- [ ] Check that runners actually run (>20 pips beyond first TP)
- [ ] Monitor for unexpected early closes
- [ ] Review actual exit prices vs theoretical

### Success Metrics
- [ ] First TP hit at intended level (>95% accuracy)
- [ ] Runners average 2-3x first TP distance
- [ ] No manual closes of winning trades
- [ ] Win rate on trades reaching first TP >80%
- [ ] Average hold time 1.5-3 hours for intraday
```

---

## Summary

The implementation focuses on:

1. **ATR-based TP calculation** - Adapts to volatility automatically
2. **Position splitting** - 50% at first TP (lock profit), 50% trailing (capture moves)
3. **Trailing stops** - Follows price up, protects capital down
4. **EMA exits** - Uses 21-EMA for runner exits (captures trends)
5. **Time limits** - Maximum 4 hours for intraday (prevents zombie trades)
6. **Safety checks** - Prevents manual closure of profitable trades

**Expected Results**:
- Win rate on first TP: 80%+
- Runner captures additional 0.5-1.5x risk
- Total average per winner: 1.5-2.0x risk
- Reduced early-exit regret
- Improved discipline (automated vs manual)

---

**Document Version**: 1.0
**Status**: Ready for implementation
**Last Updated**: March 6, 2026

