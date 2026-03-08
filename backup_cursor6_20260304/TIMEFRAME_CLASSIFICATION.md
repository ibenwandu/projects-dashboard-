# Timeframe Classification Feature

## Overview

The Trade-Alerts system now differentiates between **Intraday** and **Swing** trades, applying different entry tolerance rules based on trade type. This solves the "Entry Too Far Away" problem by ensuring Intraday trades have near-market entries while Swing trades can wait for perfect entry levels.

## Problem Solved

Previously, all trades used the same entry tolerance rules, causing:
- ❌ Swing trade entries (which can wait for perfect price) were too close
- ❌ Intraday trade entries (which need to trigger fast) were too far
- ❌ 100% of Intraday recommendations never triggered

## Solution: Timeframe Tagging

The system now classifies each trade as:
- **INTRADAY**: Quick profits, close same day (by 5 PM NY). Entry must be within 15 pips of current price. Target < 40 pips.
- **SWING**: Capture larger moves, hold for 2-5 days. Entry can be further from current price. Target > 80 pips.

## Implementation Details

### 1. LLM Prompts (`src/llm_analyzer.py`)

All LLM prompts now explicitly ask for timeframe classification:

```
**TIMEFRAME CLASSIFICATION**: For EACH trade, classify as either 'INTRADAY' or 'SWING':
  * **INTRADAY**: Quick profits, close same day (by 5 PM NY time). Entry must be within 15 pips of current price. Target < 40 pips.
  * **SWING**: Capture larger moves, hold for 2-5 days. Entry can be further from current price. Target > 80 pips.
```

### 2. Entry Tolerance Rules (`src/price_monitor.py`)

Different ATR multipliers based on timeframe:

| Trade Type | ATR Multiplier | Logic |
|------------|----------------|-------|
| **INTRADAY** | **ATR × 0.5** | Wider tolerance to ensure we get in - don't miss a 30-pip move waiting for 2 pips |
| **SWING** | **ATR × 0.1** | Stricter tolerance - can afford to wait for perfect entry for multi-day hold |

**Example:**
- If ATR = 80 pips (0.0080):
  - INTRADAY tolerance: 80 × 0.5 = **40 pips** (0.0040)
  - SWING tolerance: 80 × 0.1 = **8 pips** (0.0008)

### 3. Database Schema (`src/trade_alerts_rl.py`)

Added `timeframe` column to:
- `recommendations` table
- `llm_performance` table (for separate tracking by timeframe)

**Benefits:**
- Track performance separately: Claude might be great for Swing, ChatGPT better for Intraday
- RL system learns which LLMs are best for each timeframe
- Better weight calculation per timeframe

### 4. Recommendation Parser (`src/recommendation_parser.py`)

Extracts timeframe from:
- JSON fields: `timeframe`, `trade_type`, `classification`
- Text patterns: "timeframe: intraday", "swing trade", "intraday trade"
- Context clues: "hold for days/weeks" → SWING, "close by 5 PM" → INTRADAY

Default: `INTRADAY` if not specified

### 5. Main Application (`main.py`)

- Extracts timeframe from opportunities
- Passes timeframe to price monitor
- Logs timeframe in entry point hit messages

## Usage

### LLM Recommendations

LLMs should now include timeframe in their recommendations:

```
Trade Recommendation: **Long EUR/USD** (INTRADAY)
Entry: 1.0850
Target: 1.0880  (30 pips - intraday target)
Stop Loss: 1.0820
```

Or:

```
Trade Recommendation: **Short GBP/JPY** (SWING)
Entry: 195.50
Target: 193.00  (250 pips - swing target)
Stop Loss: 196.50
Hold for 3-5 days
```

### Price Monitor Behavior

The system automatically applies different rules:

**INTRADAY Trade:**
- Entry tolerance: 40 pips (ATR × 0.5)
- Will trigger if current price is within 40 pips of entry
- Designed to catch fast moves

**SWING Trade:**
- Entry tolerance: 8 pips (ATR × 0.1)
- Will trigger only if current price is very close to entry
- Designed for perfect entry on larger moves

## Expected Results

### Before
- ❌ 100% of Intraday trades never triggered (entry too far)
- ❌ Same tolerance rules for all trades
- ❌ No differentiation between quick vs. long-term setups

### After
- ✅ Intraday trades: Wider tolerance = more triggers
- ✅ Swing trades: Stricter tolerance = better entries
- ✅ RL system learns LLM performance by timeframe
- ✅ Better weight distribution per trade type

## Performance Tracking

The RL system now tracks:
- LLM performance by timeframe
- Win rates separately for INTRADAY vs SWING
- Best LLMs for each timeframe type

Example insights:
- "Claude: 75% win rate on SWING trades (patient, analytical)"
- "ChatGPT: 68% win rate on INTRADAY trades (reactive, news-based)"

## Configuration

No configuration needed - works automatically!

The system:
1. ✅ Extracts timeframe from LLM recommendations
2. ✅ Applies appropriate tolerance rules
3. ✅ Tracks performance separately
4. ✅ Learns which LLMs are best for each timeframe

## Migration Notes

- Existing recommendations without timeframe default to `INTRADAY`
- Database automatically adds `timeframe` column on next run
- Historical recommendations: Will use default `INTRADAY` tolerance
- New recommendations: Will use appropriate tolerance based on classification

## Future Enhancements

Potential improvements:
1. **Timeframe-specific alerts**: Different alert methods for INTRADAY vs SWING
2. **Position sizing**: Different sizing rules per timeframe
3. **Stop loss rules**: Tighter stops for INTRADAY, wider for SWING
4. **Exit timing**: Auto-close INTRADAY trades at 5 PM NY

---

**Status**: ✅ Complete and Ready for Testing

