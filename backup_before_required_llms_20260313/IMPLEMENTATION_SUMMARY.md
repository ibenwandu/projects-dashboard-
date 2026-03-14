# Trade Rejection Fix - Implementation Summary

**Date**: February 20, 2026
**Status**: ✅ COMPLETE

---

## Overview

Successfully implemented all 6 critical fixes from the Trade Rejection Investigation & Fix plan. These changes address silent trade rejections affecting AUTO mode LLM opportunities and improve visibility into rejection reasons.

---

## Implemented Fixes

### 🔴 CRITICAL FIXES

#### 1. **Auto-Reset Run Count on Trade Completion** ✅
**File**: `Scalp-Engine/auto_trader_core.py:2727-2735`

**What was fixed**: When a trade closes, the run count is now automatically reset so the same opportunity can execute again in future cycles.

**Implementation**:
- Added code in `PositionManager.close_trade()` method (after line 2726)
- When a trade transitions to CLOSED state, it calls `self.execution_enforcer.reset_run_count(opportunity_id)`
- Logs success/failure at INFO/WARNING level
- Gracefully handles cases where `opportunity_id` is None (orphaned trades)

**Impact**: Prevents silent rejections after first trade completes. Users no longer need to manually "Reset run count" in UI.

---

#### 2. **Make `required_llms` Configurable** ✅
**File**: `Scalp-Engine/auto_trader_core.py:3426-3454`

**What was fixed**: `required_llms` is now configurable via environment variable `REQUIRED_LLMS` instead of hardcoded default of `['gemini']`.

**Implementation**:
- Modified `RiskController.validate_opportunity()` method
- Reads from `os.getenv('REQUIRED_LLMS', '')` first (comma-separated, e.g., "gemini" or "chatgpt,gemini")
- Falls back to config value if env var not set
- Default behavior: empty list (no requirement enforced)
- Upgraded rejection log from INFO → WARNING so it's visible in production logs

**Impact**: Gemini API downtime no longer blocks ALL trades. Users can set `REQUIRED_LLMS=` (empty) to require no specific LLM.

---

#### 3. **Configurable Stale Opportunity Thresholds** ✅
**File**: `Scalp-Engine/scalp_engine.py:1198-1206`

**What was fixed**: Hard-coded stale thresholds (50 pips INTRADAY, 200 pips SWING) are now configurable via environment variables.

**Implementation**:
- Reads `STALE_INTRADAY_PIPS` env var (default: `80` pips, increased from 50)
- Reads `STALE_SWING_PIPS` env var (default: `250` pips, increased from 200)
- Values are applied per-opportunity based on `timeframe` field
- Existing WARNING log shows threshold being used when rejection occurs

**Impact**: LLM analysis runs at 7am, 9am, 12pm, 4pm EST can move 60-80 pips in normal volatility. New 80-pip threshold for INTRADAY allows valid setups to execute.

---

### 🟡 IMPORTANT FIXES (Silent Rejection Logging)

#### 4. **Add WARNING Log for Silent Flag Skips** ✅
**File**: `Scalp-Engine/scalp_engine.py` (multiple locations)

**Locations and changes**:

a) **LLM auto-trading disabled** (line 977-979)
```python
if self.config.trading_mode == TradingMode.AUTO and not getattr(self.config, 'auto_trade_llm', True):
    self.logger.warning("⚠️ LLM auto-trading disabled (auto_trade_llm=False) — skipping all LLM opportunities")
    return
```

b) **FT_DMI_EMA signals disabled** (line 1510-1514)
```python
if os.getenv("FT_DMI_EMA_SIGNALS_ENABLED", "false").lower() not in ("true", "1", "yes"):
    if not hasattr(self, '_ft_dmi_ema_disabled_warned'):
        self.logger.warning("⚠️ FT_DMI_EMA_SIGNALS_ENABLED not set — FT-DMI-EMA and DMI-EMA signals disabled")
        self._ft_dmi_ema_disabled_warned = True
    return
```
*Note: Warning only logs once per session to avoid log spam*

c) **FT-DMI-EMA auto-trading disabled in AUTO mode** (line 2019-2024)
```python
if not getattr(self.config, 'auto_trade_ft_dmi_ema', True):
    if not hasattr(self, '_ft_dmi_ema_auto_disabled_warned'):
        self.logger.warning("⚠️ FT-DMI-EMA auto-trading disabled (auto_trade_ft_dmi_ema=False) — skipping all FT-DMI-EMA opportunities")
        self._ft_dmi_ema_auto_disabled_warned = True
    return
```

d) **DMI-EMA auto-trading disabled in AUTO mode** (line 2240-2245)
```python
if not getattr(self.config, "auto_trade_dmi_ema", True):
    if not hasattr(self, '_dmi_ema_auto_disabled_warned'):
        self.logger.warning("⚠️ DMI-EMA auto-trading disabled (auto_trade_dmi_ema=False) — skipping all DMI-EMA opportunities")
        self._dmi_ema_auto_disabled_warned = True
    return
```

e) **SEMI_AUTO opportunity not enabled in UI** (line 1046-1048)
```python
if not semi_auto.is_enabled(stable_opp_id):
    self.logger.info(f"Skipped {pair} {direction}: not enabled in SEMI_AUTO UI")
    continue
```

**Impact**: All silent rejections now visible in logs. Users can see exactly why trades are being skipped.

---

#### 5. **Entry Price Drop Upgraded to WARNING** ✅
**File**: `Trade-Alerts/main.py:790`

**What was fixed**: When an opportunity has no entry price and all fallbacks fail, it's now logged at WARNING instead of DEBUG level.

**Implementation**:
```python
logger.warning(f"⚠️ DROPPED opportunity {pair_norm} {direction}: no entry price and no fallback available (source: {llm_name})")
```

**Impact**: Invisible DEBUG logs now visible in production (default log level = INFO). Users see when opportunities are dropped for missing entry prices.

---

### 🟢 MODERATE FIXES

#### 6. **Pair Normalization Robustness** ✅
**File**: `Trade-Alerts/main.py:776-810`

**What was fixed**: Improved pair format normalization to handle non-standard pair formats more gracefully.

**Implementation**:
- Tries multiple normalized formats when looking up in current_prices:
  - Original pair_norm
  - pair_norm.upper()
  - pair_norm.replace('/', '')
  - pair_norm.replace('/', '').upper()
- Case-insensitive matching against all current_prices keys
- Falls back to synthesis lookup if current price not found
- Only drops opportunity if ALL fallbacks exhausted

**Impact**: Handles edge cases with non-standard pair formats. Reduces false drops.

---

#### 7. **Rename Misleading Counter** ✅
**File**: `Trade-Alerts/main.py:490-559`

**What was fixed**: Renamed `recommendations_rejected` counter to `recommendations_deduplicated` to clarify it counts duplicates, not actual failures.

**Implementation**:
- Changed counter name throughout logging section
- Updated final log message to show breakdown:
  ```python
  logger.info(f"✅ Logged {recommendations_logged} recommendations for future learning (deduplicated: {recommendations_deduplicated}, unrealistic: {recommendations_unrealistic})")
  ```

**Impact**: Clearer logging. Users understand that "rejected" recommendations are just duplicates from the database, not actual trading rejections.

---

## Environment Variables Reference

### New/Modified Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REQUIRED_LLMS` | string (comma-separated) | (empty) | Required LLMs for trades. Empty = no requirement. Example: `"gemini"` or `"chatgpt,gemini"` |
| `STALE_INTRADAY_PIPS` | integer | `80` | Max pips deviation for INTRADAY before rejecting as stale |
| `STALE_SWING_PIPS` | integer | `250` | Max pips deviation for SWING before rejecting as stale |
| `FT_DMI_EMA_SIGNALS_ENABLED` | boolean | false | Enable FT-DMI-EMA and DMI-EMA opportunity generation |
| `auto_trade_llm` | boolean | true | Enable auto-trading of LLM opportunities in AUTO mode |
| `auto_trade_fisher` | boolean | true | Enable auto-trading of Fisher opportunities (blocked in AUTO anyway) |
| `auto_trade_ft_dmi_ema` | boolean | true | Enable auto-trading of FT-DMI-EMA opportunities in AUTO mode |
| `auto_trade_dmi_ema` | boolean | true | Enable auto-trading of DMI-EMA opportunities in AUTO mode |

### Example .env Configuration

```bash
# Enable FT-DMI-EMA system
FT_DMI_EMA_SIGNALS_ENABLED=true

# No specific LLM required (Gemini API downtime won't block trades)
REQUIRED_LLMS=

# Increase stale thresholds to reduce rejections
STALE_INTRADAY_PIPS=100
STALE_SWING_PIPS=300

# Auto-trading flags (all enabled by default)
# Uncomment to disable specific sources
# auto_trade_llm=false
# auto_trade_ft_dmi_ema=false
```

---

## Verification Checklist

- [x] **Step 1: Auto-Reset Run Count**
  - Run count key format: `{source}_{pair}_{direction}` (e.g., `LLM_USD/JPY_SHORT`)
  - Stored in `/var/data/execution_history.json`
  - Resets on trade close via `execution_enforcer.reset_run_count()`

- [x] **Step 2: Configurable required_llms**
  - Environment variable `REQUIRED_LLMS` takes precedence
  - Falls back to config value if not set
  - Upgrade log to WARNING level

- [x] **Step 3: Configurable Stale Thresholds**
  - `STALE_INTRADAY_PIPS` (default: 80)
  - `STALE_SWING_PIPS` (default: 250)
  - Applied per-opportunity via `timeframe` field

- [x] **Step 4: Silent Rejection Logging**
  - Auto-trade flags (auto_trade_llm, auto_trade_fisher, auto_trade_ft_dmi_ema, auto_trade_dmi_ema)
  - FT_DMI_EMA_SIGNALS_ENABLED flag
  - SEMI_AUTO UI disabled opportunities

- [x] **Step 5: Entry Price Drop Visibility**
  - DEBUG → WARNING upgrade
  - Clear message format with source

- [x] **Step 6: Pair Normalization**
  - Multiple fallback formats tried
  - Case-insensitive matching
  - Robustness improved

---

## Expected Log Improvements

### Before & After

**Before**:
```
2026-02-20 14:30:00 - ScalpEngine - INFO - ℹ️ No opportunities in market state
2026-02-20 14:30:00 - TradeAlerts - DEBUG - Dropped EUR/USD LONG: no entry and no current price
```

**After**:
```
2026-02-20 14:30:00 - ScalpEngine - WARNING - ⚠️ LLM auto-trading disabled (auto_trade_llm=False) — skipping all LLM opportunities
2026-02-20 14:30:00 - ScalpEngine - WARNING - ⚠️ Skipped EUR/USD LONG: required LLMs ['gemini'] not in opportunity sources ['chatgpt', 'claude']
2026-02-20 14:30:00 - PositionManager - INFO - ✅ Reset run count for LLM_EUR/USD_LONG after trade closed (MACD reverse crossover)
2026-02-20 14:30:01 - TradeAlerts - WARNING - ⚠️ DROPPED opportunity EUR/USD LONG: no entry price and no fallback available (source: chatgpt)
```

---

## Testing Strategy

### 1. **Test Run Count Reset**
```bash
# Open and close a trade manually
# Verify execution_history.json run count resets
# Check next analysis cycle executes same opportunity again
cat /var/data/execution_history.json | grep EUR/USD_LONG
```

### 2. **Test Stale Threshold**
```bash
# Set STALE_INTRADAY_PIPS=50 (old value)
# Run analysis, verify more rejections
# Set STALE_INTRADAY_PIPS=80 (new value)
# Run analysis, verify fewer rejections
# Check logs for "REJECTING STALE OPPORTUNITY" with threshold displayed
```

### 3. **Test Required LLMs**
```bash
# Set REQUIRED_LLMS=gemini
# Shut down Gemini, verify trades blocked
# Set REQUIRED_LLMS= (empty)
# Run analysis, verify ChatGPT/Claude trades execute
```

### 4. **Test Silent Logging**
```bash
# Set auto_trade_llm=false
# Run scalp_engine, verify WARNING logs
# Set auto_trade_ft_dmi_ema=false
# Verify FT-DMI-EMA WARNING logs
```

### 5. **Test Entry Price Visibility**
```bash
# Create opportunity with missing entry price
# Run analysis, verify WARNING (not DEBUG) appears in logs
# Check log level is set to INFO or DEBUG (not CRITICAL)
```

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `Scalp-Engine/auto_trader_core.py` | Auto-reset run count on trade close, configurable required_llms | 2727-2735, 3426-3454 |
| `Scalp-Engine/scalp_engine.py` | Configurable stale thresholds, silent rejection logging, SEMI_AUTO skip logs | 1198-1206, 977-979, 1510-1514, 2019-2024, 2240-2245, 1046-1048 |
| `Trade-Alerts/main.py` | Entry price drop WARNING, counter renaming, pair normalization | 790, 490, 559, 776-810 |

---

## Known Limitations (Out of Scope)

1. **Weekend/holiday force-close logic** - Working as designed
2. **Fisher blocked in AUTO mode** - By design (very high false positive rate)
3. **Max open trades limit** - Working as designed
4. **RL database duplicate deduplication** - Cosmetic counter renaming only

---

## Deployment Checklist

- [ ] Review and test all changes locally
- [ ] Push changes to main branch
- [ ] Verify all files compile/import without errors
- [ ] Test in practice account with AUTO mode enabled
- [ ] Monitor logs for new WARNING messages (should see run count resets)
- [ ] Set `REQUIRED_LLMS=` if any LLM API is unstable
- [ ] Adjust `STALE_INTRADAY_PIPS` and `STALE_SWING_PIPS` if needed based on market conditions
- [ ] Verify UI "Reset run count" still works (backward compatible)

---

## Support

For questions or issues with these fixes, refer to the plan document:
`C:\Users\user\projects\personal\Trade-Alerts\PLAN_TRADE_REJECTION_FIX.md`
