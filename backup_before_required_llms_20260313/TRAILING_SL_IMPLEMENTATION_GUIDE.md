# Trailing Stop Loss Implementation Guide for Trade-Alerts Scalp-Engine

**Date**: March 6, 2026
**Purpose**: Technical implementation roadmap for improving trailing SL logic based on industry research
**Status**: Ready for Phase 1 implementation

---

## Quick Start: What to Do This Week

### Issue Summary
From `CLAUDE.md` Session 20 (Feb 22, 2026):
- **Problem**: EUR/JPY trade lost -28.22 pips on a 20-pip stop loss (loss exceeded expected maximum)
- **Root Cause**: Unverified trailing stop implementation; no logs showing stop movement
- **Impact**: Can't confirm SL is working; 80% of trades closed manually suggests SL isn't being used/trusted

### Immediate Action Items (2-3 hours)
1. Find where trailing SL is currently calculated in Scalp-Engine
2. Add detailed logging for every SL update
3. Create weekly verification report
4. Review EUR/JPY trade logs to understand the -28.22 pip loss

---

## Part 1: Current State Assessment

### 1.1 Finding the Current Trailing SL Implementation

**Search for these files/functions in Scalp-Engine:**

```bash
# Find where trailing SL is set
grep -r "trailing.*stop" Scalp-Engine/src/ --include="*.py"
grep -r "stop_loss" Scalp-Engine/src/ --include="*.py"
grep -r "TrailingStop\|trailing_stop" Scalp-Engine/ --include="*.py"

# Find OANDA order creation
grep -r "StopLossOnFill\|stopLossOnFill" Scalp-Engine/src/ --include="*.py"
grep -r "class.*Order\|create_trade\|open_trade" Scalp-Engine/src/execution/ --include="*.py"
```

**Key Files to Review:**
- `Scalp-Engine/src/execution/auto_trader_core.py` - Main execution logic
- `Scalp-Engine/src/risk_manager.py` - Risk calculations
- `Scalp-Engine/src/oanda_client.py` - API calls to OANDA
- `Scalp-Engine/src/trade_monitor.py` - Post-trade monitoring (if exists)

**What to Look For:**
```python
# Current implementation likely looks like one of these:

# Pattern 1: Fixed pips
stop_loss = entry_price - (50 * 0.0001)  # 50 pips fixed

# Pattern 2: Percentage-based
stop_loss = entry_price * (1 - 0.005)  # 0.5% fixed

# Pattern 3: ATR-based (research shows this is better)
atr = calculate_atr(...)
stop_loss = entry_price - (atr * 2.0)  # 2× ATR

# OANDA API call likely looks like:
request = {
    "type": "MARKET",
    "instrument": "EUR_USD",
    "units": 100000,
    "stopLossOnFill": {
        "price": "1.08000",
        "triggerMode": "DEFAULT"  # or "BID" for shorts
    }
}
```

### 1.2 Current Gaps (What's Missing)

Based on research in `TRAILING_STOP_LOSS_RESEARCH_REPORT.md`, current implementation is likely missing:

**Missing Element 1: Detailed Logging**
- No log lines showing stop distance calculation
- No log lines showing stop movement (per bar/minute)
- No audit trail of stop updates

**Missing Element 2: Dynamic Adjustment**
- Likely using fixed pips (e.g., 50 pips always)
- Doesn't adapt to market volatility
- No breakeven protection
- No trailing activation

**Missing Element 3: Verification**
- No weekly report comparing intended vs. actual stops
- No slippage tracking
- No gap-risk avoidance

---

## Part 2: Phase 1 Implementation (Verification & Logging)

### 2.1 Add Stop-Movement Logging

**Step 1: Locate trailing SL calculation code**

In the file where `stop_loss` is calculated (likely `auto_trader_core.py`), modify to add logging:

```python
import logging

logger = logging.getLogger('TrailingStopManager')

class TrailingStopManager:
    """Manage dynamic trailing stop loss for open trades."""

    def __init__(self):
        self.open_trades = {}  # {trade_id: {pair, direction, entry, stop_loss, highest_high, atr}}

    def calculate_trailing_stop(self, pair, direction, entry_price, current_price,
                               previous_stop_loss, atr_value, multiplier=2.0):
        """
        Calculate trailing stop based on ATR.

        Args:
            pair: Currency pair (e.g., 'EUR/USD')
            direction: 'LONG' or 'SHORT'
            entry_price: Entry price of the trade
            current_price: Current market price
            previous_stop_loss: Previous stop loss level (to prevent moving unfavorably)
            atr_value: Current ATR value
            multiplier: ATR multiplier (default 2.0x)

        Returns:
            new_stop_loss: Calculated stop loss price
        """

        # Calculate trailing distance
        trailing_distance = atr_value * multiplier

        # Calculate new stop based on direction
        if direction == 'LONG':
            new_stop = current_price - trailing_distance
            # Only move stop UP (favorable), never down
            if new_stop < previous_stop_loss:
                new_stop = previous_stop_loss
        else:  # SHORT
            new_stop = current_price + trailing_distance
            # Only move stop DOWN (favorable for shorts), never up
            if new_stop > previous_stop_loss:
                new_stop = previous_stop_loss

        # Calculate profit so far
        profit_pips = (current_price - entry_price) * 10000 if direction == 'LONG' else (entry_price - current_price) * 10000

        # Log the update
        stop_moved = 'UP' if direction == 'LONG' and new_stop > previous_stop_loss else 'DOWN' if direction == 'SHORT' and new_stop < previous_stop_loss else 'SAME'

        logger.info(
            f"[TrailingStop] {pair} {direction}: "
            f"price={current_price:.5f}, "
            f"profit={profit_pips:+.1f}pips, "
            f"ATR={atr_value:.1f}pips, "
            f"multiplier={multiplier}x, "
            f"distance={trailing_distance:.1f}pips, "
            f"stop {previous_stop_loss:.5f} → {new_stop:.5f} ({stop_moved})"
        )

        return new_stop

    def verify_stop_distance(self, pair, direction, current_price, stop_loss, atr_value, multiplier):
        """Verify actual stop distance matches expected distance."""

        expected_distance = atr_value * multiplier
        actual_distance = abs(current_price - stop_loss)
        variance = abs(actual_distance - expected_distance) / expected_distance if expected_distance > 0 else 0

        if variance > 0.2:  # >20% variance = issue
            logger.warning(
                f"[StopVerification] {pair} {direction}: "
                f"Distance variance {variance:.1%} "
                f"(expected {expected_distance:.1f} pips, actual {actual_distance:.1f} pips)"
            )
            return False

        return True
```

**Step 2: Call this function in main trading loop**

Find where trades are monitored (likely every bar/minute in `scalp_engine.py`):

```python
# In main trading loop (every minute/bar update):

def update_all_trailing_stops():
    """Update trailing stops for all open trades."""

    for trade in self.position_manager.get_open_trades():
        pair = trade['pair']
        direction = trade['direction']
        entry_price = trade['entry_price']
        current_price = self.price_monitor.get_current_price(pair)
        previous_stop = trade['stop_loss']

        # Get current ATR
        atr_value = self.indicator_calculator.get_atr(pair, period=14)

        # Calculate new stop
        new_stop = self.trailing_stop_manager.calculate_trailing_stop(
            pair=pair,
            direction=direction,
            entry_price=entry_price,
            current_price=current_price,
            previous_stop_loss=previous_stop,
            atr_value=atr_value,
            multiplier=2.0  # Use 2.0× ATR for intraday
        )

        # Update in OANDA if changed
        if abs(new_stop - previous_stop) > 0.00001:
            self.oanda_client.update_stop_loss(trade['id'], new_stop)
            trade['stop_loss'] = new_stop

        # Verify stop distance
        self.trailing_stop_manager.verify_stop_distance(
            pair, direction, current_price, new_stop, atr_value, 2.0
        )
```

**Step 3: Add exit logging**

When a trade closes (at stop loss), log details:

```python
def on_trade_closed(trade_id, pair, direction, entry_price, exit_price,
                   intended_stop_loss, actual_exit_price, close_reason):
    """Log trade exit for verification."""

    slippage = abs(actual_exit_price - intended_stop_loss)
    loss_pips = (entry_price - actual_exit_price) * 10000 if direction == 'LONG' else (actual_exit_price - entry_price) * 10000

    logger.info(
        f"[TradeExit] {pair} {direction}: "
        f"entry={entry_price:.5f}, "
        f"exit={actual_exit_price:.5f}, "
        f"loss={loss_pips:.1f}pips, "
        f"intended_stop={intended_stop_loss:.5f}, "
        f"slippage={slippage:.1f}pips, "
        f"reason={close_reason}"
    )

    # Flag excessive slippage
    if slippage > 10:
        logger.warning(
            f"[ExcessiveSlippage] {pair}: "
            f"{slippage:.1f}pips slippage on stop loss exit "
            f"(check if news event or gap)"
        )
```

### 2.2 Create Weekly Verification Report

**Step 4: Add weekly report generation**

Create a new file: `Scalp-Engine/src/trailing_stop_verifier.py`

```python
"""
Trailing Stop Loss Verification and Reporting.

Generates weekly reports on SL performance to identify issues.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger('TrailingStopVerifier')


class TrailingStopVerifier:
    """Verify trailing stop behavior and generate reports."""

    def __init__(self, db_path='scalping_rl.db'):
        self.db_path = db_path
        self.trades = []

    def load_closed_trades(self, start_date, end_date):
        """Load trades closed in date range."""
        # TODO: Implement based on your database schema
        # Should load trades with: pair, direction, entry, exit, stop_loss,
        # exit_price, close_reason, closed_at
        pass

    def generate_weekly_report(self, week_start_date=None):
        """Generate weekly trailing stop performance report."""

        if week_start_date is None:
            week_start_date = datetime.utcnow() - timedelta(days=7)

        week_end_date = week_start_date + timedelta(days=7)

        # Load trades
        trades = self.load_closed_trades(week_start_date, week_end_date)

        if not trades:
            logger.warning(f"No trades found for week {week_start_date.date()}")
            return

        # Analyze trailing stop exits
        stop_exits = [t for t in trades if t['close_reason'] == 'STOP_LOSS']
        tp_exits = [t for t in trades if t['close_reason'] == 'TAKE_PROFIT']
        manual_exits = [t for t in trades if t['close_reason'] == 'MANUAL']

        # Calculate metrics
        total_trades = len(trades)
        stop_exit_count = len(stop_exits)
        tp_exit_count = len(tp_exits)
        manual_exit_count = len(manual_exits)

        # Stop loss quality metrics
        if stop_exits:
            avg_slippage = sum(abs(t['actual_exit'] - t['stop_loss']) * 10000
                              for t in stop_exits) / len(stop_exits)
            max_slippage = max(abs(t['actual_exit'] - t['stop_loss']) * 10000
                              for t in stop_exits)

            whipsaw_count = sum(
                1 for t in stop_exits
                if self._is_whipsaw(t, next_candle_direction='up')
            )
        else:
            avg_slippage = 0
            max_slippage = 0
            whipsaw_count = 0

        # Generate report
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║  TRAILING STOP LOSS PERFORMANCE REPORT                         ║
║  Week: {week_start_date.date()} to {week_end_date.date()}                     ║
╚════════════════════════════════════════════════════════════════╝

OVERVIEW:
─────────────────────────────────────────────────────────────────
Total Trades:             {total_trades:3d}
  Trailing Stop Exits:    {stop_exit_count:3d} ({stop_exit_count*100/total_trades if total_trades > 0 else 0:5.1f}%)
  Take Profit Exits:      {tp_exit_count:3d} ({tp_exit_count*100/total_trades if total_trades > 0 else 0:5.1f}%)
  Manual Exits:           {manual_exit_count:3d} ({manual_exit_count*100/total_trades if total_trades > 0 else 0:5.1f}%)

STOP LOSS QUALITY (Trailing Stop Exits Only):
─────────────────────────────────────────────────────────────────
Average Slippage:         {avg_slippage:6.2f} pips
Maximum Slippage:         {max_slippage:6.2f} pips
Whipsaw Exits:            {whipsaw_count:3d} ({whipsaw_count*100/stop_exit_count if stop_exit_count > 0 else 0:5.1f}%)

INTERPRETATION:
─────────────────────────────────────────────────────────────────
"""

        if avg_slippage < 3:
            report += "✓ Slippage: Excellent (< 3 pips average)\n"
        elif avg_slippage < 7:
            report += "✓ Slippage: Good (3-7 pips average)\n"
        else:
            report += "⚠ Slippage: High (> 7 pips average) - Check broker, news events\n"

        if whipsaw_count < stop_exit_count * 0.1:
            report += "✓ Whipsaws: Low (< 10%) - Stops are well-tuned\n"
        elif whipsaw_count < stop_exit_count * 0.2:
            report += "⚠ Whipsaws: Moderate (10-20%) - Consider widening stops\n"
        else:
            report += "✗ Whipsaws: High (> 20%) - Stops too tight, increase multiplier\n"

        if manual_exit_count < total_trades * 0.1:
            report += "✓ Manual Exits: Low (< 10%) - Strategy is self-contained\n"
        else:
            report += "⚠ Manual Exits: High (> 10%) - Strategy may need tuning\n"

        report += "\n" + "─" * 65 + "\n"
        report += "ACTION ITEMS:\n"

        if avg_slippage > 7:
            report += "  1. High slippage detected - Check if news events during trading\n"
            report += "     Possible fix: Widen stops to 3× ATR during volatile periods\n"

        if whipsaw_count > stop_exit_count * 0.2:
            report += "  1. Too many whipsaws - Stops are too tight\n"
            report += "     Possible fix: Increase ATR multiplier from 2.0× to 2.5×\n"

        if manual_exit_count > total_trades * 0.1:
            report += "  1. Too many manual exits - Review strategy parameters\n"
            report += "     Possible fix: Adjust entry/exit signals or position sizing\n"

        if whipsaw_count == 0 and avg_slippage < 3 and manual_exit_count == 0:
            report += "  ✓ No action needed - All metrics healthy\n"

        report += "\n" + "─" * 65 + "\n"
        report += "DETAILS:\n\n"

        # Group by pair
        pairs = defaultdict(list)
        for trade in trades:
            pairs[trade['pair']].append(trade)

        for pair in sorted(pairs.keys()):
            pair_trades = pairs[pair]
            pair_stop_exits = [t for t in pair_trades if t['close_reason'] == 'STOP_LOSS']

            report += f"{pair}: {len(pair_trades)} trades, {len(pair_stop_exits)} stop exits\n"

            if pair_stop_exits:
                pair_slippage = sum(abs(t['actual_exit'] - t['stop_loss']) * 10000
                                   for t in pair_stop_exits) / len(pair_stop_exits)
                report += f"  Avg Slippage: {pair_slippage:.2f} pips\n"

        report += "\n" + "═" * 65 + "\n"

        logger.info(report)
        return report

    def _is_whipsaw(self, trade, next_candle_direction):
        """Check if trade was stopped out then reversed."""
        # TODO: Implement based on your data schema
        # Check if price after stop-out move >2R in original trade direction
        pass
```

### 2.3 Review EUR/JPY Trade (Debug the Loss)

**Step 5: Investigate the EUR/JPY -28.22 pips loss**

Create diagnostic script: `scripts/analyze_trade_loss.py`

```python
"""
Analyze specific trade that lost more than expected.

EUR/JPY trade from manual logs: -28.22 pips loss on 20-pip stop
"""

import json
from datetime import datetime

# From manual logs, reconstruct the trade:
eurjpy_trade = {
    'pair': 'EUR/JPY',
    'direction': 'LONG',  # Assume, verify from logs
    'entry_price': 130.50,  # Verify from logs
    'entry_time': datetime(2026, 2, 27),  # Verify from logs
    'intended_stop_loss': 130.30,  # 20 pips = 0.20 yen
    'actual_exit_price': 130.22,  # Result: -28 pips loss (0.28 yen)
    'close_reason': 'STOP_LOSS',  # Assume
}

print("EUR/JPY Trade Analysis")
print("=" * 50)
print(f"Entry: {eurjpy_trade['entry_price']}")
print(f"Intended Stop: {eurjpy_trade['intended_stop_loss']}")
print(f"Actual Exit: {eurjpy_trade['actual_exit_price']}")
print()

# Calculate slippage
slippage_yen = abs(eurjpy_trade['actual_exit_price'] - eurjpy_trade['intended_stop_loss'])
slippage_pips = slippage_yen * 100  # JPY pairs: 1 pip = 0.01 yen, so × 100

print(f"Expected Loss: {abs(eurjpy_trade['entry_price'] - eurjpy_trade['intended_stop_loss']) * 100:.1f} pips")
print(f"Actual Loss:   {abs(eurjpy_trade['entry_price'] - eurjpy_trade['actual_exit_price']) * 100:.1f} pips")
print(f"Slippage:      {slippage_pips:.1f} pips")
print()

# Possible causes
print("POSSIBLE CAUSES:")
print("─" * 50)
print()
print("1. SLIPPAGE during high volatility")
print(f"   - Expected: {abs(eurjpy_trade['entry_price'] - eurjpy_trade['intended_stop_loss']) * 100:.0f} pips")
print(f"   - Actual:   {abs(eurjpy_trade['entry_price'] - eurjpy_trade['actual_exit_price']) * 100:.0f} pips")
print(f"   - Extra loss: {slippage_pips:.0f} pips (gap or liquidity issue)")
print()

print("2. NO TRAILING STOP UPDATE")
print("   - Stop set at entry time but never moved up")
print("   - If price had rallied to +50 pips, stop should trail")
print("   - Check logs: Did stop movement logs exist? If not, trailing stop NOT WORKING")
print()

print("3. WRONG STOP PRICE SENT TO OANDA")
print("   - Stop calculated as 130.30 but sent as 130.20?")
print("   - Check OANDA order confirmation vs. intended stop")
print()

print("4. MULTIPLE FACTORS")
print("   - Stop sent as 130.30, but price gapped to 130.18 (on news)")
print("   - Execution at next price 130.22 (4 pips beyond stop)")
print()

print("VERIFICATION CHECKLIST:")
print("─" * 50)
print("[ ] Check Scalp-Engine logs for 2026-02-27 EUR/JPY trades")
print("[ ] Look for '[TrailingStop]' log lines - if none, SL not updating")
print("[ ] Check OANDA order history: What stop was actually sent?")
print("[ ] Check price chart: Was there a gap or spike at close time?")
print("[ ] Calculate: (actual_exit - intended_stop) × 100 = slippage in pips")
print()

print("EXPECTED RESULTS:")
print("─" * 50)
print("If trailing SL is working: Should see '[TrailingStop]' logs every bar")
print("If slippage < 3 pips: Normal execution")
print("If slippage 3-10 pips: Volatile market or news event (expected)")
print("If slippage > 10 pips: Gap, spike, or execution issue (investigate)")
```

---

## Part 3: Phase 2 Implementation (ATR-Based Trailing)

### 3.1 Implement ATR-Based Stop

**File**: `Scalp-Engine/src/risk_manager.py` (or create new file `trailing_stop_calculator.py`)

```python
"""
ATR-based trailing stop loss calculation.

Reference: TRAILING_STOP_LOSS_RESEARCH_REPORT.md Section 3
Implements volatility-adjusted stops using Average True Range.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple

logger = logging.getLogger('ATRTrailingStop')


class ATRTrailingStopCalculator:
    """Calculate ATR-based trailing stops with volatility adjustment."""

    # Research-based parameters (Section 2 of TRAILING_STOP_LOSS_RESEARCH_REPORT.md)
    DEFAULT_PARAMS = {
        'atr_period': 14,
        'base_multiplier': 2.0,
        'volatility_tiers': {
            'low': {'multiplier': 1.5, 'volatility_threshold': 0.005},
            'normal': {'multiplier': 2.0, 'volatility_threshold': 0.010},
            'high': {'multiplier': 2.5, 'volatility_threshold': 0.015},
            'extreme': {'multiplier': 3.0, 'volatility_threshold': 1.0},  # News events
        },
    }

    def __init__(self, atr_period=14, base_multiplier=2.0):
        self.atr_period = atr_period
        self.base_multiplier = base_multiplier
        self.price_history = {}  # {pair: [prices]}

    def add_price(self, pair: str, price: float):
        """Add price to history for ATR calculation."""
        if pair not in self.price_history:
            self.price_history[pair] = []
        self.price_history[pair].append(price)
        # Keep only last 100 bars
        if len(self.price_history[pair]) > 100:
            self.price_history[pair] = self.price_history[pair][-100:]

    def calculate_atr(self, pair: str, period: int = 14) -> float:
        """Calculate ATR for pair."""
        prices = self.price_history.get(pair, [])
        if len(prices) < period:
            return 0

        # TODO: Calculate from OHLC data
        # For now, use simplified version
        returns = np.diff(prices) / prices[:-1]
        atr = np.std(returns) * prices[-1]
        return max(atr, 0.0001)  # Minimum ATR

    def detect_volatility_regime(self, atr_current: float, atr_sma: float) -> str:
        """Detect current volatility regime."""
        ratio = atr_current / atr_sma if atr_sma > 0 else 1.0

        if ratio > 1.5:
            return 'extreme'
        elif ratio > 1.2:
            return 'high'
        elif ratio > 0.9:
            return 'normal'
        else:
            return 'low'

    def calculate_trailing_stop(self,
                               pair: str,
                               direction: str,
                               entry_price: float,
                               current_price: float,
                               previous_stop: float,
                               atr_value: float,
                               volatility_regime: str = 'normal') -> float:
        """
        Calculate trailing stop based on ATR and volatility.

        Args:
            pair: Currency pair (e.g., 'EUR/USD')
            direction: 'LONG' or 'SHORT'
            entry_price: Entry price of the trade
            current_price: Current market price
            previous_stop: Previous stop level (to avoid moving unfavorably)
            atr_value: Current ATR value
            volatility_regime: 'low', 'normal', 'high', or 'extreme'

        Returns:
            float: New trailing stop price
        """

        # Get multiplier for volatility regime
        multiplier = self.DEFAULT_PARAMS['volatility_tiers'][volatility_regime]['multiplier']

        # Calculate trailing distance
        trailing_distance = atr_value * multiplier

        # Calculate new stop
        if direction == 'LONG':
            new_stop = current_price - trailing_distance
            # Don't move down (only trail upward)
            new_stop = max(new_stop, previous_stop)
        else:  # SHORT
            new_stop = current_price + trailing_distance
            # Don't move up (only trail downward)
            new_stop = min(new_stop, previous_stop)

        # Log calculation
        logger.debug(
            f"[ATRTrailingStop] {pair} {direction}: "
            f"volatility={volatility_regime}, multiplier={multiplier}, "
            f"atr={atr_value:.1f}pips, distance={trailing_distance:.1f}pips, "
            f"stop={previous_stop:.5f} → {new_stop:.5f}"
        )

        return new_stop

    def calculate_breakeven_stop(self, entry_price: float, direction: str, breakeven_buffer: float = 5) -> float:
        """
        Calculate breakeven stop (entry price + buffer).

        Args:
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            breakeven_buffer: Buffer in pips (default 5, to cover spread + commission)

        Returns:
            float: Breakeven stop price
        """

        if direction == 'LONG':
            return entry_price + (breakeven_buffer * 0.0001)
        else:  # SHORT
            return entry_price - (breakeven_buffer * 0.0001)

    def should_activate_trailing(self, entry_price: float, current_price: float,
                                direction: str, activation_profit_pips: float = 100) -> bool:
        """
        Check if trailing stop should activate based on profit.

        Args:
            entry_price: Entry price
            current_price: Current price
            direction: 'LONG' or 'SHORT'
            activation_profit_pips: Profit threshold to activate trailing (default 100 pips)

        Returns:
            bool: True if trailing should activate
        """

        if direction == 'LONG':
            profit_pips = (current_price - entry_price) * 10000
        else:  # SHORT
            profit_pips = (entry_price - current_price) * 10000

        return profit_pips >= activation_profit_pips
```

### 3.2 Integrate into Main Loop

**In `scalp_engine.py` or `auto_trader_core.py`:**

```python
class ScalpEngineWithATRTrailing:
    """Scalp engine enhanced with ATR-based trailing stops."""

    def __init__(self, config):
        # ... existing init code ...
        self.trailing_calc = ATRTrailingStopCalculator(
            atr_period=14,
            base_multiplier=2.0
        )

    def update_trailing_stops(self):
        """Update all trailing stops every bar."""

        for trade in self.get_open_trades():
            pair = trade['pair']
            direction = trade['direction']
            entry_price = trade['entry_price']
            current_price = self.price_monitor.get_latest_price(pair)
            previous_stop = trade['stop_loss']

            # Get ATR
            atr = self.indicator_calculator.get_atr(pair, period=14)
            volatility = self.indicator_calculator.detect_volatility_regime(pair)

            # Calculate breakeven stop if profit threshold reached
            if self.should_use_breakeven(entry_price, current_price, direction):
                new_stop = self.trailing_calc.calculate_breakeven_stop(entry_price, direction)
                logger.info(f"[BreakevenStop] {pair}: Activated at {new_stop:.5f}")
            else:
                # Calculate ATR-based trailing stop
                new_stop = self.trailing_calc.calculate_trailing_stop(
                    pair=pair,
                    direction=direction,
                    entry_price=entry_price,
                    current_price=current_price,
                    previous_stop=previous_stop,
                    atr_value=atr,
                    volatility_regime=volatility
                )

            # Update in OANDA if significantly changed (>0.5 pips)
            if abs(new_stop - previous_stop) * 10000 > 0.5:
                try:
                    self.oanda_client.update_stop_loss(trade['id'], new_stop)
                    trade['stop_loss'] = new_stop
                    logger.info(f"[StopUpdate] {pair}: {previous_stop:.5f} → {new_stop:.5f}")
                except Exception as e:
                    logger.error(f"[StopUpdateFailed] {pair}: {e}")

    def should_use_breakeven(self, entry_price, current_price, direction, threshold_pips=50):
        """Check if breakeven protection should activate."""
        if direction == 'LONG':
            profit = (current_price - entry_price) * 10000
        else:
            profit = (entry_price - current_price) * 10000
        return profit >= threshold_pips and profit < 100  # Breakeven zone: 50-100 pips
```

---

## Part 4: Gap Risk Mitigation

### 4.1 Trading Hours Enforcement

**Add to Scalp-Engine:**

```python
from datetime import datetime, time

class TradingHoursManager:
    """Restrict trading during high-risk hours."""

    # High risk for gaps: Friday evening (weekend risk), before news
    AVOID_TIMES = {
        'friday': (time(17, 0), time(23, 59)),  # Friday 5pm+ ET (gap risk)
        'sunday': (time(0, 0), time(17, 5)),     # Sunday 12am-5pm ET (pre-open, thin liquidity)
    }

    @staticmethod
    def can_open_new_trade(current_time: datetime) -> bool:
        """Check if current time is safe for opening new trades."""

        weekday_name = current_time.strftime('%A').lower()
        current_t = current_time.time()

        if weekday_name == 'friday':
            start, end = TradingHoursManager.AVOID_TIMES['friday']
            if start <= current_t <= end:
                return False

        if weekday_name == 'sunday':
            start, end = TradingHoursManager.AVOID_TIMES['sunday']
            if start <= current_t <= end:
                return False

        return True

    @staticmethod
    def should_close_position_end_of_day(current_time: datetime) -> bool:
        """Check if positions should be closed (end of Friday)."""
        weekday_name = current_time.strftime('%A').lower()
        if weekday_name == 'friday' and current_time.hour >= 16:  # 4pm ET
            return True
        return False


# Usage in scalp_engine.py:
def check_and_execute_trade(opportunity):
    """Execute trade only if within safe trading hours."""

    if not TradingHoursManager.can_open_new_trade(datetime.utcnow()):
        logger.warning(f"Trade blocked: Outside trading hours for {opportunity['pair']}")
        return False

    # ... execute trade ...
    return True

def cleanup_end_of_day():
    """Close all positions at end of Friday."""
    if TradingHoursManager.should_close_position_end_of_day(datetime.utcnow()):
        self.close_all_positions(reason='end_of_week_gap_protection')
```

---

## Part 5: Testing Protocol

### 5.1 Unit Tests

**File**: `Scalp-Engine/tests/test_atr_trailing_stop.py`

```python
"""
Unit tests for ATR-based trailing stop calculator.
"""

import unittest
from src.risk_manager import ATRTrailingStopCalculator


class TestATRTrailingStop(unittest.TestCase):
    """Test ATR trailing stop calculations."""

    def setUp(self):
        self.calc = ATRTrailingStopCalculator(atr_period=14, base_multiplier=2.0)

    def test_long_trailing_up(self):
        """Test that long stops trail upward."""
        # Entry: 1.0850, Current: 1.0900, ATR: 20 pips, Previous stop: 1.0800
        new_stop = self.calc.calculate_trailing_stop(
            pair='EUR/USD',
            direction='LONG',
            entry_price=1.0850,
            current_price=1.0900,
            previous_stop=1.0800,
            atr_value=20 * 0.0001,  # Convert pips to price
            volatility_regime='normal'
        )
        # Expected: 1.0900 - (20pips × 2.0) = 1.0900 - 0.0040 = 1.0860
        self.assertGreaterEqual(new_stop, 1.0800)  # Stop should not move down
        self.assertLess(new_stop, 1.0900)  # Stop should be below current price

    def test_short_trailing_down(self):
        """Test that short stops trail downward."""
        new_stop = self.calc.calculate_trailing_stop(
            pair='EUR/USD',
            direction='SHORT',
            entry_price=1.0900,
            current_price=1.0850,
            previous_stop=1.0950,
            atr_value=20 * 0.0001,
            volatility_regime='normal'
        )
        # Expected: 1.0850 + (20pips × 2.0) = 1.0850 + 0.0040 = 1.0890
        self.assertLessEqual(new_stop, 1.0950)  # Stop should not move up
        self.assertGreater(new_stop, 1.0850)  # Stop should be above current price

    def test_volatility_multiplier(self):
        """Test that high volatility increases stop distance."""
        stop_normal = self.calc.calculate_trailing_stop(
            pair='EUR/USD',
            direction='LONG',
            entry_price=1.0850,
            current_price=1.0900,
            previous_stop=1.0800,
            atr_value=20 * 0.0001,
            volatility_regime='normal'
        )

        stop_high = self.calc.calculate_trailing_stop(
            pair='EUR/USD',
            direction='LONG',
            entry_price=1.0850,
            current_price=1.0900,
            previous_stop=1.0800,
            atr_value=20 * 0.0001,
            volatility_regime='high'
        )

        # High volatility should result in stop moving less (wider distance)
        self.assertGreater(stop_high, stop_normal)

    def test_breakeven_protection(self):
        """Test breakeven stop calculation."""
        breakeven_long = self.calc.calculate_breakeven_stop(
            entry_price=1.0850,
            direction='LONG',
            breakeven_buffer=5
        )
        # Expected: 1.0850 + (5 pips × 0.0001) = 1.0850 + 0.0005 = 1.0855
        self.assertAlmostEqual(breakeven_long, 1.0855, places=4)

    def test_trailing_activation(self):
        """Test when trailing stop should activate."""
        should_activate = self.calc.should_activate_trailing(
            entry_price=1.0850,
            current_price=1.0950,  # +100 pips
            direction='LONG',
            activation_profit_pips=100
        )
        self.assertTrue(should_activate)

        should_not_activate = self.calc.should_activate_trailing(
            entry_price=1.0850,
            current_price=1.0900,  # +50 pips
            direction='LONG',
            activation_profit_pips=100
        )
        self.assertFalse(should_not_activate)


if __name__ == '__main__':
    unittest.main()
```

**Run tests:**
```bash
cd Scalp-Engine
python -m pytest tests/test_atr_trailing_stop.py -v
```

### 5.2 Integration Test

**Create test trade with logging:**

```python
def test_trailing_stop_integration(self):
    """Test full trailing stop workflow with logging."""

    # Create a test trade
    trade = {
        'pair': 'EUR/USD',
        'direction': 'LONG',
        'entry_price': 1.0850,
        'stop_loss': 1.0810,  # Initial 40 pips
        'open_price': 1.0850,
    }

    # Simulate price movement and trailing
    prices = [1.0850, 1.0860, 1.0870, 1.0900, 1.0920, 1.0950, 1.1000, 1.0990, 1.0950, 1.0900]

    for i, price in enumerate(prices):
        # Update stop
        new_stop = self.trailing_calc.calculate_trailing_stop(
            pair=trade['pair'],
            direction=trade['direction'],
            entry_price=trade['entry_price'],
            current_price=price,
            previous_stop=trade['stop_loss'],
            atr_value=0.0020,  # 20 pips = 0.0020 in decimal
            volatility_regime='normal'
        )

        trade['stop_loss'] = new_stop

        print(f"Bar {i}: Price {price:.4f}, Stop {new_stop:.4f}, Profit {(price - trade['entry_price']) * 10000:.0f}pips")

        # Check if stopped out
        if trade['direction'] == 'LONG' and price < new_stop:
            print(f"STOPPED OUT at {price:.4f}")
            break

    # Verify final stop is at or above entry price (no loss if we didn't stop)
    self.assertGreaterEqual(trade['stop_loss'], 1.0810)  # Never moved down
```

---

## Part 6: Deployment Checklist

### 6.1 Pre-Deployment Verification

**Code Review:**
- [ ] All logging statements compile without error
- [ ] ATRTrailingStopCalculator has unit tests (all pass)
- [ ] Integration test runs without error (MONITOR mode)
- [ ] No new dependencies added (or properly documented if added)

**Testing:**
- [ ] Backtest 100+ trades with new trailing SL logic
- [ ] Compare P&L to old fixed-stop approach
- [ ] Verify win rate doesn't drop >5%
- [ ] Verify average win increases 10%+

**Documentation:**
- [ ] Update USER_GUIDE.md with ATR parameters used
- [ ] Document weekly verification report format
- [ ] Document how to read trailing stop logs

### 6.2 Deployment Steps

**Step 1: Merge Code**
```bash
git add Scalp-Engine/src/risk_manager.py
git add Scalp-Engine/src/trailing_stop_verifier.py
git add Scalp-Engine/tests/test_atr_trailing_stop.py
git commit -m "Implement Phase 1: ATR-based trailing stops with comprehensive logging"
```

**Step 2: Monitor Mode (1 week)**
- Deploy to Render with TRADING_MODE=MONITOR
- Review logs daily for:
  - Trailing stop updates appearing (if no logs, SL not working)
  - Stop distances matching expected (ATR × 2.0)
  - Slippage within 3 pips (normal conditions)

**Step 3: Manual Mode (1 week)**
- Deploy with TRADING_MODE=MANUAL
- Approve each trade before execution
- Verify stop placement before confirming

**Step 4: Auto Mode (1 week at 25% size)**
- Deploy with TRADING_MODE=AUTO and position_size_multiplier=0.25
- Monitor daily verification report
- Check for red flags (excessive slippage, whipsaws, etc.)

**Step 5: Ramp to Full Size**
- Increase position_size_multiplier to 0.5, then 1.0
- Continue monitoring weekly report
- Adjust parameters if needed based on performance

---

## Summary: Immediate Next Steps

### This Week (2-3 hours of work)
1. **Find current SL implementation** in Scalp-Engine code
2. **Add detailed logging** to track every stop update
3. **Create EUR/JPY diagnostic script** to understand the -28.22 pip loss
4. **Generate first weekly report** to establish baseline

### Next Week (4-6 hours)
5. **Implement ATRTrailingStopCalculator** class with research-based parameters
6. **Integrate into main loop** (update_trailing_stops)
7. **Add unit tests** and verify all pass
8. **Backtest** 100+ trades with new logic

### Following Week (2-3 hours)
9. **Deploy to MONITOR mode** on Render
10. **Review logs daily** for 3-5 days
11. **Generate weekly verification report**
12. **Decision: Is SL working now?**

---

**Reference Documents:**
- `TRAILING_STOP_LOSS_RESEARCH_REPORT.md` - Full research and best practices
- `CLAUDE.md` - Session notes on failures and debugging process
- `consol-recommend3.md` - Consolidated implementation plan

**Contact/Questions:**
Refer to TRAILING_STOP_LOSS_RESEARCH_REPORT.md Section 12 for complete source citations.
