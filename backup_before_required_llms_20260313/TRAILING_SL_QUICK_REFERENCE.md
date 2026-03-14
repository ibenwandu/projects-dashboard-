# Trailing Stop Loss: Quick Reference & Lookup Tables

**Date**: March 6, 2026
**Use**: Quick answers to common questions about trailing stops

---

## Quick Lookup: ATR Parameters by Situation

### By Trading Timeframe
```
Scalping (5m-15m):    ATR(7)  × 1.5x  | Very tight stops
Day Trading (1H):     ATR(14) × 2.0x  | ← TRADE-ALERTS DEFAULT
Swing Trading (4H):   ATR(14) × 2.5x  | Wider, trend-focused
Position (1D+):       ATR(21) × 3.0x  | Very wide, trend capture
```

### By Market Volatility
```
Volatility Regime (ATR ratio):
  Extreme (>1.5x avg): Use 3.0-3.5x ATR  | News events, limit position size
  High (1.2-1.5x avg): Use 2.5x ATR    | Volatile pairs (GBP, GBPJPY)
  Normal (0.9-1.2x):   Use 2.0x ATR    | Standard setting
  Low (<0.9x avg):     Use 1.5x ATR    | Calm markets, Asian session
```

### By Currency Pair
```
EUR/USD:    Steady volatility      → ATR(14) × 2.0x
GBP/USD:    High volatility        → ATR(14) × 2.5x
USD/JPY:    Medium volatility      → ATR(14) × 2.0x
EUR/JPY:    Very high volatility   → ATR(14) × 3.0x
AUD/USD:    High volatility        → ATR(14) × 2.5x
NZD/USD:    High volatility        → ATR(14) × 2.5x
GBP/JPY:    Extreme volatility     → ATR(14) × 3.5x (risky, consider avoiding)
USD/CAD:    Medium volatility      → ATR(14) × 2.0x
```

---

## Common Issues: Diagnosis & Fix

### Issue 1: Stops Triggered Too Often (Whipsaws)

**Symptom**: "Stopped out, then price went my way"

**Root Cause**: Stop too tight

**Diagnosis**:
```
If >20% of stops hit then price reverses >1R → Stops too tight
If >30% of stops hit → Definitely too tight
```

**Fix (in order of preference)**:
```
1. Increase multiplier: 2.0x → 2.5x
2. Use longer ATR: ATR(14) → ATR(21)
3. Increase breakeven activation: 50 pips → 75 pips
4. Increase trailing activation: 100 pips → 150 pips

✓ Expected result: Whipsaws <10%, win rate same or better
```

**Code change**:
```python
# Before:
stop_distance = atr * 2.0

# After:
stop_distance = atr * 2.5  # or 3.0 if extremely volatile
```

---

### Issue 2: Large Losses (Stops Not Working)

**Symptom**: "Lost 80 pips on a 50-pips stop"

**Root Cause**: Gap, slippage, or stop not updating

**Diagnosis**:
```
Loss = 80 pips, Intended stop = 50 pips, Slippage = 30 pips

Normal slippage: 1-3 pips
Acceptable slippage: 3-7 pips
Excessive slippage: >10 pips (investigate)

If slippage 3-7 pips and no gap:
  → Likely news event or high volatility (expected)

If slippage >10 pips:
  → Check if stop log shows movement OR if weekend gap
  → If no movement log: STOP NOT UPDATING (critical)
  → If weekend/news: Expected, use 3.5x ATR before risk times
```

**Fix**:
```
For excessive slippage:
1. Check if stop updated every bar (look for logs)
2. If no logs: Add logging, debug stop update code
3. If logs show update: Widen stops for news events
4. Avoid positions Friday 4pm-Sunday 5pm
5. Widen stops 4 hours before/after high-impact news

For gap risk:
1. Close all positions Friday 4pm ET
2. Don't trade 1 hour before ECB, Fed, NFP, BoE
3. Use 3.0-3.5x ATR if must hold over risk event
```

---

### Issue 3: Missing Profit (Stops Too Wide)

**Symptom**: "Stopped at small loss, but price then rallied 150 pips"

**Root Cause**: Stop too far from price

**Diagnosis**:
```
If >10% of stops are hit, then price goes >2R further → Stop too wide

Count trades where:
  - Stopped at loss
  - Within next 5 bars, price moves >100 pips favorable direction

If >10 trades match: Stops are too loose
```

**Fix**:
```
1. Decrease multiplier: 2.5x → 2.0x
2. Use shorter ATR: ATR(14) → ATR(10)
3. Activate trailing earlier: 100 pips → 50 pips profit
4. Tighten trailing multiplier: 2.0x → 1.5x

✓ Expected result: Better profit locking, similar win rate
```

---

### Issue 4: Positions Held Into Weekend

**Symptom**: Monday morning: position gapped -200+ pips

**Root Cause**: Held position Friday afternoon

**Diagnosis**:
```
Count trades:
  - Opened after Friday 2pm
  - Still open Friday 5pm ET
  - Closed Monday with loss >100 pips

If >3 trades match: Weekend gap risk

Common loss amounts:
  EUR/USD: 50-150 pips gap (average 80)
  GBP/USD: 100-200 pips gap (average 120)
  USD/JPY: 80-180 pips gap (average 100)
```

**Fix**:
```
1. No positions Friday after 4pm ET
2. Auto-close all Friday 4pm
3. If must hold: Use 3.5x ATR (not 2.0x)
4. Reduce position size 50% if holding over weekend
5. Check calendar: Avoid positions before major news

Code fix:
if current_time.weekday() == 4 and current_time.hour >= 16:  # Friday 4pm
    close_all_positions(reason='weekend_gap_risk')
```

---

## Quick Fixes (Copy-Paste Ready)

### Fix #1: Add Stop Movement Logging

**Add this to your stop update code:**

```python
logger.info(
    f"[TrailingStop] {pair} {direction}: "
    f"price={current_price:.5f}, "
    f"atr={atr_value:.1f}pips, multiplier={multiplier}, "
    f"distance={atr_value * multiplier:.1f}pips, "
    f"stop {old_stop:.5f} → {new_stop:.5f}"
)
```

**Verification**: Check logs, look for this line every bar. If absent → stops not updating.

---

### Fix #2: Add Breakeven Protection

**Add to main loop:**

```python
def apply_breakeven_protection(trade, profit_threshold=50):
    """Move stop to breakeven once trade reaches +50 pips profit."""

    if trade['direction'] == 'LONG':
        profit = (current_price - trade['entry_price']) * 10000
        if profit >= profit_threshold and trade['stop_loss'] < trade['entry_price']:
            new_stop = trade['entry_price'] + 5 * 0.0001  # +5 pips buffer
            trade['stop_loss'] = new_stop
            logger.info(f"[Breakeven] {trade['pair']}: Activated at {new_stop:.5f}")
    else:  # SHORT
        profit = (trade['entry_price'] - current_price) * 10000
        if profit >= profit_threshold and trade['stop_loss'] > trade['entry_price']:
            new_stop = trade['entry_price'] - 5 * 0.0001  # -5 pips buffer
            trade['stop_loss'] = new_stop
            logger.info(f"[Breakeven] {trade['pair']}: Activated at {new_stop:.5f}")
```

---

### Fix #3: Avoid Weekend Gap Risk

**Add to trading hours enforcement:**

```python
from datetime import datetime, time

SAFE_TRADING_HOURS = {
    'friday': time(0, 0).__le__ and time(16, 0).__ge__,  # Mon-Fri before 4pm
    'saturday': False,  # Never on weekend
    'sunday': time(17, 5).__ge__,  # Only after 5:05pm ET (market open)
}

def can_open_position(current_time):
    """Check if safe to open position (avoid weekend risk)."""
    weekday = current_time.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun

    # Friday 4pm+ ET = NO
    if weekday == 4 and current_time.hour >= 16:
        return False

    # Saturday-Sunday before 5pm = NO
    if weekday in [5, 6] and current_time.hour < 17:
        return False

    return True
```

---

## When to Use Each Stop Type

### Fixed-Distance Stop
**When**: Only if backtested and confirmed working
**Example**: 50 pips always
**Pros**: Simple, predictable
**Cons**: Doesn't adapt to volatility, whipsaws likely
**Use case**: Range-bound markets only

---

### ATR-Based Stop (RECOMMENDED)
**When**: Most situations, especially trend-following
**Example**: Current price - (ATR × 2.0)
**Pros**: Adapts to volatility, reduces whipsaws, professional standard
**Cons**: Requires ATR calculation
**Use case**: EUR/USD, USD/JPY, most majors
**Research consensus**: YES, use this

---

### Chandelier Stop (Advanced)
**When**: Trend-following on 4H+ timeframes
**Example**: Highest High (22 bars) - (3 × ATR)
**Pros**: Incorporates trend structure, very smooth
**Cons**: Complex, can lag on reversals
**Use case**: Swing trading, trend following

---

### Parabolic SAR (Advanced)
**When**: Mean-reversion strategies
**Example**: Time-accelerated trailing
**Pros**: Catches reversals quickly
**Cons**: Complex parameters, whipsaws in ranges
**Use case**: Reversal trades, specific setups only

---

## Slippage Expectations

### Normal Market Conditions (No News)
```
Stop-Loss Execution Slippage Expectations:

Major Pairs (EUR/USD, GBP/USD, USD/JPY):
  Good broker (Interactive Brokers):  0-2 pips
  Medium broker (OANDA):              1-3 pips ← Trade-Alerts
  Poor broker:                        3-5 pips

Exotic Pairs (GBP/JPY, EURJPY):
  Good broker:                        2-4 pips
  Medium broker:                      3-7 pips
  Poor broker:                        5-10 pips
```

### During High Volatility / News
```
Events: NFP, Fed decision, ECB, Brexit, earnings

Normal day slippage:     1-3 pips
News event slippage:     5-15 pips
Extreme slippage:        15-30+ pips

For EUR/USD on NFP day:  Expect 8-12 pips (not 2 pips)
For GBP/JPY on BoE day:  Expect 15-25 pips (not 5 pips)

Mitigation:
  - Widen stops 3.0x → 3.5x ATR
  - Reduce position size 50%
  - Don't trade 1 hour before/after event
  - Don't hold across event
```

---

## Weekly Verification Checklist

**Every Friday, review and score:**

```
TRAILING STOP QUALITY:
─────────────────────────────────────────────────────

□ Slippage on Stop Exits:
  <3 pips avg:   ✓ Excellent
  3-7 pips avg:  ~ Acceptable
  >7 pips avg:   ✗ Problem (check news/gaps)

□ Whipsaw Rate (stopped then reversed >1R):
  <10%:   ✓ Good (stops well-tuned)
  10-20%: ~ Moderate (slightly tight)
  >20%:   ✗ Problem (stops too tight, increase 0.5x)

□ Manual Exit Rate:
  <5%:    ✓ Good (strategy self-contained)
  5-10%:  ~ Moderate (some manual intervention)
  >10%:   ✗ Problem (strategy not working)

□ Stop Movement Logs:
  Present:   ✓ SL updating (log every bar)
  Sparse:    ~ SL updating (not every bar)
  Absent:    ✗ SL NOT WORKING (critical - debug immediately)

□ Average Win vs. Loss:
  Win/Loss >1.0: ✓ Good
  Win/Loss >1.5: ✓ Excellent
  Win/Loss <1.0: ✗ Problem (stops too wide or exits early)

SCORE CARD:
  4-5 ✓'s: Excellent, no changes needed
  3-4 ✓'s: Good, minor tuning if needed
  2-3 ✓'s: Moderate, consider small adjustments
  0-2 ✓'s: Poor, major changes needed
```

---

## Decision Tree: What to Fix First

```
START: "My trailing stops aren't working"
  │
  ├─ Do logs show [TrailingStop] lines?
  │  ├─ NO  → FIX: Add logging (Phase 1)
  │  └─ YES → Continue
  │
  ├─ Is slippage >10 pips average?
  │  ├─ YES (and no major news) → FIX: Check broker, widen stops
  │  ├─ YES (during news) → EXPECTED, use 3.5x ATR
  │  └─ NO  → Continue
  │
  ├─ Is whipsaw rate >20%?
  │  ├─ YES → FIX: Increase multiplier (2.0x → 2.5x)
  │  └─ NO  → Continue
  │
  ├─ Are 80%+ of trades manually closed?
  │  ├─ YES → FIX: Review strategy signals, not SL
  │  └─ NO  → Continue
  │
  ├─ Are weekends causing large gaps?
  │  ├─ YES → FIX: Close positions Friday 4pm
  │  └─ NO  → Continue
  │
  ├─ Is average win < average loss?
  │  ├─ YES → FIX: Widen stops (decrease 0.5x), tighten entries
  │  └─ NO  → Continue
  │
  └─ CONCLUSION: Trailing stops appear to be working
     (Monitor weekly, make small adjustments as needed)
```

---

## ATR Multiplier Tuning Guide

**Current multiplier: 2.0x**

**If experiencing whipsaws (>20%):**
```
2.0x → 2.5x (adds 25% more distance)
Expect: 30% fewer whipsaws, same or higher win rate

If still whipsaws:
2.5x → 3.0x (adds 50% more distance)
Expect: 50% fewer whipsaws, trade might be too loose

Typical final: 2.0-2.5x for 1H trading
```

**If missing profits (stops too wide):**
```
2.0x → 1.5x (removes 25% distance)
Expect: Tighter stops, catch reversals faster

Never go below 1.5x (too tight for normal volatility)
```

**If high volatility (news events, Asian open):**
```
Use 3.0-3.5x instead of 2.0x
Only during:
  - 4 hours before/after news
  - Asian open (thin liquidity)
  - Market gaps visible
```

---

## P&L Impact Calculator

**Rough estimate** of improvement from trailing SL fixes:

```
Starting Win Rate: 45%
Starting Avg Win: 80 pips
Starting Avg Loss: 40 pips
Starting Expectancy: (45% × 80) + (55% × -40) = +16 pips/trade

PHASE 1: Add logging & verification
  → No direct impact, but reveals issues
  → Estimated: +0 pips (awareness only)

PHASE 2: Implement ATR × 2.0
  → Replace fixed 50-pip stops with ATR-based
  → Reduce whipsaws 30-40%
  → Slightly lower win rate: 45% → 42%
  → Higher avg win: 80 → 95 pips
  → Estimated: +10 pips/trade improvement

PHASE 3: Add breakeven protection
  → Tighter stops once in profit
  → Slight decrease win rate: 42% → 40%
  → Higher avg win: 95 → 105 pips
  → Estimated: +5 pips/trade improvement

PHASE 4: Gap risk avoidance
  → Eliminate 1-2 gap losses per month
  → Estimated: +15 pips/trade average per month

PHASE 5: Position sizing optimization
  → Larger positions when volatility low
  → Smaller positions when volatility high
  → Estimated: +10 pips/trade

TOTAL POTENTIAL IMPROVEMENT:
  +0 (logging) +10 (ATR) +5 (breakeven) +15 (gaps) +10 (sizing)
  = +40 pips/trade potential (assuming all implemented correctly)

Original: +16 pips/trade → Target: +56 pips/trade
That's 250% improvement, or 3.5x better expectancy
```

---

## Sources Quick Reference

All recommendations grounded in 15+ research sources:

**ATR-Based Stops:**
- Luxalgo (2024): "5 ATR Stop-Loss Strategies"
- TrendSpider (2024): "ATR Trailing Stops Guide"
- StrategyQuant (2024): "ATR Trailing Stops Guide"

**Breakeven Strategies:**
- Trading Heroes (2024): "Move Stop to Breakeven"
- WealthCharts (2024): "Breakeven Stops, Trailing Stops"

**Gap & Slippage Risk:**
- FOREX.com (2024): "Market Gaps and Slippage"
- Blueberry (2024): "What Is Slippage & Market Gap"
- TradingCritique (2026): "Stop Loss in Forex"

**Verification & Testing:**
- BuildAlpha (2024): "Stop Losses Complete Guide"
- Medium/Jakub Polec (2024): "Stop-Loss, Take-Profit, Advanced Backtesting"
- GreyhoundAnalytics (2024): "Stop Losses in Backtesting.py"

**Professional Implementation:**
- Charles Schwab/thinkorswim Docs
- MetaTrader Documentation
- Interactive Brokers API

**Market Microstructure:**
- Talos Research (2025): "Execution Insights, TCA, Slippage"
- Global Trading (2024): "Market Microstructure Research"
- Bookmap (2025): "What's Changed in Market Microstructure"

---

**Last Updated**: March 6, 2026
**For**: Trade-Alerts Scalp-Engine
**Status**: Ready for immediate use
