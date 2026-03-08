# Phase 4: Strategy Improvements - Implementation Plan

**Date**: February 22, 2026
**Estimated Effort**: 10-12 hours
**Approach**: Fix strategy instead of avoiding it

---

## Overview

Phase 4 implements 4 strategic improvements to fix the root causes of losing trades:

| Step | Focus | Time | Priority |
|------|-------|------|----------|
| 1 | Market Regime Detection | 2-3 hrs | HIGH |
| 2 | Direction Bias Fixes | 2-3 hrs | HIGH |
| 3 | JPY Pair Optimization (Option C) | 3-4 hrs | MEDIUM |
| 4 | Backtest Validation | 2-3 hrs | HIGH |

---

## Step 1: Market Regime Detection (2-3 hours)

### The Problem

**Evidence from demo account**:
```
Jan 27: 102 consecutive losses in 10.3 hours
  - 70 SHORT, 32 LONG (68% SHORT)
  - Market was trending UP
  - System kept shorting (wrong direction)
  - Pattern: NZD_USD 52 consecutive shorts all lost
```

**Root Cause**: System doesn't know if market is trending or ranging
- Takes contrary positions (shorts when market trends up)
- Averages down on losing pair instead of waiting
- No circuit breaker to stop (Phase 3 fixed this, but should prevent entry)

### Solution: Detect Market Trend

**Implementation**:
```python
def get_market_regime(pair: str, market_state: Dict) -> str:
    """
    Determine market regime: TRENDING_UP, TRENDING_DOWN, or RANGING

    Methods:
    1. Check price vs moving averages (1H, 4H)
    2. Calculate slope of recent candles
    3. Check ADX (Average Directional Index) if available
    4. Check if price is making higher highs/higher lows (UP) or lower highs/lower lows (DOWN)
    """
    # Use market_state data (already being calculated by Trade-Alerts)
    regime = market_state.get('regime', 'RANGING')  # TRENDING/RANGING/HIGH_VOL

    return regime

def should_filter_trade_by_regime(opportunity: Dict, market_state: Dict) -> Tuple[bool, str]:
    """
    Check if trade direction conflicts with market regime

    Rules:
    - If market TRENDING_UP and direction is SHORT: SKIP (high risk of loss)
    - If market TRENDING_DOWN and direction is LONG: SKIP (high risk of loss)
    - If market RANGING: Accept any direction (balanced)
    """
    regime = get_market_regime(opportunity['pair'], market_state)
    direction = opportunity['direction'].upper()

    # Get trend direction
    if regime == 'TRENDING':
        trend_direction = market_state.get('trend_direction', 'UNKNOWN')  # UP/DOWN

        # Check for conflicts
        if trend_direction == 'UP' and direction == 'SHORT':
            return True, f"SHORT trade conflicts with UP trend - SKIP"
        if trend_direction == 'DOWN' and direction == 'LONG':
            return True, f"LONG trade conflicts with DOWN trend - SKIP"

    return False, "OK"
```

**Integration Point**: In `open_trade()` method
```python
def open_trade(self, opportunity, market_state):
    # ... existing checks ...

    # NEW: Check market regime conflict
    should_skip, reason = should_filter_trade_by_regime(opportunity, market_state)
    if should_skip:
        self.logger.info(f"⏭️ SKIPPING: {reason}")
        return None

    # ... continue with trade ...
```

**Expected Impact**:
- Prevent 20-30% of losses in trending markets
- Stop Jan 27 102-loss streak much earlier
- Overall win rate improvement: +2-3%

---

## Step 2: Direction Bias Fixes (2-3 hours)

### The Problem

**Observation from demo account**:
```
Loss Streak Analysis:
  Streak #1 (102 losses): 70 SHORT, 32 LONG (68% SHORT bias)
  Streak #2 (53 losses):  48 SHORT, 5 LONG (90% SHORT bias)
  Streak #3 (34 losses):  34 SHORT, 0 LONG (100% SHORT)
  Streak #4 (33 losses):  33 SHORT, 0 LONG (100% SHORT)
```

**Pattern**: When market trends UP, system is heavily SHORT biased

**Possible Root Causes**:
1. **LLM Analysis Inverted**: ChatGPT/Gemini/Claude all producing opposite direction
2. **Entry Price Wrong**: Shorts placed at resistance instead of support
3. **LLM Consensus Broken**: Unanimous agreement but all wrong direction

### Investigation & Fix Strategy

#### Phase 2a: Analyze Trade-Alerts Recommendations

**For each loss streak**:
1. Check Trade-Alerts logs from that date/time
2. What direction did each LLM recommend?
3. What was the actual market direction?
4. Calculate per-LLM accuracy

**Implementation**:
```python
def analyze_llm_direction_accuracy(db, date_range: Tuple[datetime, datetime]):
    """
    For each LLM (ChatGPT, Gemini, Claude, Deepseek, Synthesis):
    - Get recommendations during date range
    - Compare recommended direction vs actual market trend
    - Calculate accuracy per LLM per pair
    """
    results = {}
    for llm in ['chatgpt', 'gemini', 'claude', 'deepseek', 'synthesis']:
        recs = db.get_llm_recommendations(llm, date_range)

        correct = 0
        total = 0

        for rec in recs:
            actual_market_trend = get_actual_market_trend(
                rec['pair'], rec['timestamp']
            )

            if rec['direction'] == actual_market_trend:
                correct += 1

            total += 1

        accuracy = correct / total if total > 0 else 0
        results[llm] = {
            'accuracy': accuracy,
            'total_recs': total,
            'correct': correct
        }

    return results
```

**Expected Finding**: Likely one or more LLMs is consistently wrong on direction

#### Phase 2b: Fix Broken LLM(s)

**For any LLM with low accuracy** (ChatGPT, Gemini, Claude, Deepseek, or Synthesis):
Option A: Disable the LLM entirely (zero weight in consensus)
Option B: Invert direction if it's consistently opposite (if 20% correct, maybe 80% of inversions work?)
Option C: Lower weight in consensus calculation (reduce from 0.2 to 0.1 or 0.05)
Option D: Disable only on certain pairs if problem is pair-specific

**Important Note on Synthesis**:
- Synthesis = consensus of all other LLMs
- If Synthesis accuracy is low: Problem is in the underlying LLMs (fix them first)
- If Synthesis accuracy is high but individual LLMs vary: Synthesis is doing its job

**If all LLMs are wrong on certain pairs**:
Option A: Disable those pairs
Option B: Add manual direction filter (e.g., "don't short USD_JPY")
Option C: Check if entry prices are wrong (maybe LLM says SHORT but places order at resistance instead of support)

#### Phase 2c: Add Confidence-Based Filtering

```python
def should_filter_by_consensus_confidence(opportunity: Dict, min_confidence: float = 0.7) -> Tuple[bool, str]:
    """
    Skip trades with low consensus or low LLM agreement on direction

    Example:
    - If 2 out of 3 LLMs agree, confidence = 2/3 = 67%
    - If 3 out of 3 LLMs agree, confidence = 3/3 = 100%
    - Only take trades with 70%+ confidence
    """
    consensus = opportunity.get('consensus', 1.0)

    if consensus < min_confidence:
        return True, f"Low confidence ({consensus:.0%}) - SKIP"

    return False, "OK"
```

**Expected Impact**:
- Filter out uncertain trades
- Improve direction accuracy by 5-10%
- Reduce overall trade count by 20-30% (but keep winners)

---

## Step 3: JPY Pair Optimization - Option C (Fix Entry Logic) (3-4 hours)

### Why JPY Pairs Are Different

JPY pairs have unique characteristics that require special handling:

**Price Format**:
```
EUR/USD:   1.0850 (5 decimal places, pip = 0.00001)
USD/JPY:   147.50 (2 decimal places, pip = 0.01)
```

**Pip Value Difference**:
```
EUR/USD: 1 pip = 0.0001 = roughly $1 per 10,000 units
USD/JPY: 1 pip = 0.01 = roughly $1 per 1,000 units
```

**Volatility**:
```
EUR/USD: Typical spread 2-3 pips
USD/JPY: Typical spread 1-2 pips
GBP/JPY: Typical spread 2-5 pips
```

### The Problem Analysis

**Current Performance**:
```
USD/JPY:   56 trades, 21.4% WR, +$21.04 P&L  ← PROFITABLE
EUR/JPY:    5 trades,  0% WR, -$317.02 P&L   ← CATASTROPHIC
GBP/JPY:   ~20 trades, low WR, large losses   ← FAILING
```

**Hypothesis**: Entry logic or volatility handling is breaking for EUR_JPY and GBP_JPY

### Investigation Points

#### Point 1: Entry Price Accuracy

**Check**: Are LLM entry prices realistic?

```python
def validate_jpy_entry_prices(db):
    """
    For all JPY pair trades in demo account:
    1. Get LLM recommended entry price
    2. Get actual market price at recommendation time (from OANDA logs)
    3. Calculate deviation: |recommended - actual| / actual

    If deviation > 5%: Entry is probably wrong
    If deviation < 1%: Entry is accurate
    """
    jpy_pairs = ['EUR/JPY', 'GBP/JPY', 'USD/JPY', 'AUD/JPY']

    for pair in jpy_pairs:
        recs = db.get_recommendations_for_pair(pair)

        avg_deviation = 0
        for rec in recs:
            actual_price = get_actual_price_at_time(pair, rec['timestamp'])
            deviation = abs(rec['entry_price'] - actual_price) / actual_price
            avg_deviation += deviation

        avg_deviation /= len(recs)
        print(f"{pair}: Avg entry deviation: {avg_deviation:.2%}")
```

#### Point 2: Volatility Handling

**Check**: Does position sizing account for JPY pair volatility?

```python
# Current position sizing doesn't adjust for volatility
# JPY pairs might need:
# - Smaller position size (higher volatility = higher pip value)
# - Wider stops (more room to breathe)
# - Different consensus multipliers
```

#### Point 3: Spread Adjustment

**Check**: Are entries far from current price?

```python
# For JPY pairs, if entry is 10+ pips away from current price:
# - LIMIT order might never fill
# - Trade misses the setup
# - Or fills much worse than intended
```

### Fix Strategy - Option C

**Phase 3a: Diagnosis** (1 hour)
1. Run validation check on all JPY pair trades
2. Identify which problem is causing losses:
   - Entry prices wrong?
   - Volatility not handled?
   - Spreads too wide?
   - Direction bias on JPY pairs?

**Phase 3b: Implement Fixes** (2-3 hours)

**If Entry Prices Wrong**:
```python
# Tighten entry price tolerance
# Use only LLM recommendations with <1% deviation from market
def filter_jpy_entries_by_accuracy(opportunity: Dict) -> Tuple[bool, str]:
    if 'JPY' not in opportunity['pair']:
        return False, "Not JPY pair"

    # Only accept if entry is very accurate
    # Reject if >2% away from market
    entry_distance = opportunity.get('entry_distance_pct', 0)

    if entry_distance > 0.02:
        return True, "JPY entry too far from market - SKIP"

    return False, "OK"
```

**If Volatility Not Handled**:
```python
# Adjust position sizing for JPY pairs
def get_jpy_position_multiplier(pair: str, base_volatility: float) -> float:
    if 'JPY' not in pair:
        return 1.0

    # JPY pairs: higher volatility = smaller position
    # EUR/JPY high vol: 0.8x multiplier
    # USD/JPY normal vol: 1.0x multiplier
    # GBP/JPY extreme vol: 0.6x multiplier

    if 'EUR/JPY' in pair:
        return 0.8
    elif 'GBP/JPY' in pair:
        return 0.6
    else:
        return 1.0
```

**If Spreads Too Wide**:
```python
# Use wider stops for JPY pairs
def get_jpy_stop_loss_padding(pair: str, calculated_sl: float) -> float:
    if 'JPY' not in pair:
        return calculated_sl

    # Add 5-10 pips for JPY pairs to account for wider spreads
    pip_size = 0.01  # JPY pip size
    padding = 10 * pip_size  # 10 pips

    # LONG: Add padding below SL
    # SHORT: Add padding above SL
    return calculated_sl + padding
```

**If Direction Bias on JPY**:
```python
# Add JPY-pair-specific direction rules
def apply_jpy_direction_rules(opportunity: Dict) -> Tuple[bool, str]:
    if 'JPY' not in opportunity['pair']:
        return False, "Not JPY pair"

    # Example: GBP/JPY tends to move in certain patterns
    # USD/JPY is the most stable
    # Avoid certain direction/pair combinations that lose money

    pair = opportunity['pair']
    direction = opportunity['direction']

    # Rule: Don't short GBP/JPY (0% win rate)
    if pair == 'GBP/JPY' and direction == 'SHORT':
        return True, "GBP/JPY SHORT has 0% win rate - SKIP"

    return False, "OK"
```

### Expected Outcome

**Before Fix**:
```
EUR/JPY: 0% WR, -$317 loss
GBP/JPY: ~10% WR, -$50+ loss
USD/JPY: 21% WR, +$21 profit
```

**After Fix (Conservative Estimate)**:
```
EUR/JPY: 15-20% WR, +$10-20 profit (or disabled if unfixable)
GBP/JPY: 18-25% WR, +$15-30 profit (or disabled if unfixable)
USD/JPY: 25-30% WR, +$50+ profit (improved)
```

**Or if fundamentally broken**:
```
EUR/JPY: Disabled (too risky)
GBP/JPY: Disabled (too risky)
USD/JPY: Kept and improved
```

---

## Step 4: Backtest Validation (2-3 hours)

### What Gets Backtested

**Test Data**: Demo account trades from Jan 15 - Feb 22 (419 total trades)

**Apply Filters in Order**:
```
Step 1: Original 419 trades
  Win Rate: 15.5%
  P&L: -$1,853

Step 2: + Market regime detection filter
  Removes: Trades against trends
  Expected: 20-30% loss reduction

Step 3: + Direction bias filter
  Removes: Low-confidence trades
  Expected: Additional 10-15% improvement

Step 4: + JPY pair fixes
  Improves: JPY trades accuracy
  Expected: +5-10% improvement

Final: All 3 filters applied
  Estimated Win Rate: 25-30%
  Estimated P&L: -$100 to +$100 (break-even area)
```

### Backtest Implementation

```python
def run_phase4_backtest():
    """
    Backtest Phase 4 improvements on demo account history
    """

    # Load all trades from demo account
    all_trades = load_oanda_trades('2026-01-15', '2026-02-22')

    # For each trade, check if Phase 4 would have taken it
    phases = {
        'original': all_trades,
        'with_regime_filter': [],
        'with_direction_filter': [],
        'with_jpy_fixes': [],
        'with_all_filters': []
    }

    for trade in all_trades:
        # Check regime filter
        if should_skip_by_regime(trade):
            continue
        phases['with_regime_filter'].append(trade)

        # Check direction filter
        if should_skip_by_direction(trade):
            continue
        phases['with_direction_filter'].append(trade)

        # Check JPY fixes
        if should_skip_by_jpy_rules(trade):
            continue
        phases['with_jpy_fixes'].append(trade)

        phases['with_all_filters'].append(trade)

    # Calculate metrics for each phase
    for phase_name, trades in phases.items():
        if len(trades) == 0:
            continue

        wins = len([t for t in trades if t['pnl'] > 0])
        losses = len([t for t in trades if t['pnl'] < 0])
        total_pnl = sum(t['pnl'] for t in trades)
        win_rate = wins / len(trades) if len(trades) > 0 else 0

        print(f"\n{phase_name}:")
        print(f"  Trades: {len(trades)}")
        print(f"  Wins: {wins}, Losses: {losses}")
        print(f"  Win Rate: {win_rate:.1%}")
        print(f"  Total P&L: ${total_pnl:.2f}")
        print(f"  Avg Per Trade: ${total_pnl/len(trades):.2f}")
```

### LLM Tracking Summary

**5 LLMs Being Used**:
1. **ChatGPT** - OpenAI's GPT model
2. **Gemini** - Google's LLM
3. **Claude** - Anthropic's Claude (this one!)
4. **Deepseek** - Deepseek's LLM
5. **Synthesis** - Consensus of all 4 models above

**Default Weights**: 0.2 each (equal weight)

**Diagnosis Task**:
- Calculate accuracy of each LLM on direction prediction
- Identify which LLMs are broken or consistently wrong
- Adjust weights or disable problematic ones

### Success Criteria

**Target Results After Phase 4**:
- ✅ Trade count reduced 30-40% (filtering bad trades)
- ✅ Win rate improved to 25-30%+ (up from 15.5%)
- ✅ P&L improved to break-even or small profit
- ✅ Max loss streak reduced to <20 (down from 102)
- ✅ All 5 LLMs analyzed and optimized

---

## Implementation Timeline

**Day 1-2: Step 1 (Market Regime Detection)**
- Add `get_market_regime()` function
- Add `should_filter_trade_by_regime()` function
- Integrate into `open_trade()` method
- Test with simple cases

**Day 2-3: Step 2 (Direction Bias Fixes)**
- Analyze Trade-Alerts logs for LLM accuracy
- Implement confidence-based filtering
- Optional: Disable worst-performing LLM
- Test direction filter

**Day 3-4: Step 3 (JPY Pair Optimization)**
- Run diagnostic on all JPY pair trades
- Identify root cause (entry price? volatility? spread?)
- Implement appropriate fix (Option C)
- Test with JPY-specific trades

**Day 4-5: Step 4 (Backtest)**
- Run Phase 4 backtest on full demo history
- Compare before/after metrics
- Document improvements
- Identify any remaining issues

**Day 5: Documentation & Commit**
- Write Phase 4 completion summary
- Commit all changes
- Prepare for Phase 5 (demo testing)

---

## Risk Mitigation

**Low Risk Strategies**:
- Market regime filtering: Very safe, just prevents certain trades
- Direction bias: Very safe, filters uncertain trades
- JPY pair fixes: Medium risk, modifies logic but carefully

**Testing Before Committing**:
1. Test each filter individually on synthetic data
2. Test combined filters on historical data
3. Verify no crashes or exceptions
4. Check log output for correct reasoning

**Rollback Plan**:
- All changes committed to git
- Can revert any filter that doesn't work
- Can adjust thresholds if too aggressive

---

## Expected Final Outcome

After Phase 4 + Phase 5:

```
BEFORE PHASE 4:
  Win Rate: 15.5%
  Consecutive Losses: 102
  Daily P&L: -$4.42 average
  Status: Not profitable, high risk

AFTER PHASE 4:
  Win Rate: 25-30%
  Consecutive Losses: 5-10 (stopped by circuit breaker)
  Daily P&L: Break-even to +$2-3
  Status: Close to breakeven, much safer

AFTER PHASE 5 (Demo Test):
  Win Rate: Validated 25-30%
  Demo P&L: +$50-100 over 7 days
  Ready for: Live trading with confidence
```

---

**Phase 4 Status**: Ready to implement
**Next Action**: Start Step 1 (Market Regime Detection)
**Estimated Completion**: 3-4 days of coding + testing

