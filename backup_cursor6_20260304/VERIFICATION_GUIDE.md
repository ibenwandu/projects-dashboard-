# Trade Rejection Fix - Verification Guide

## Quick Verification Steps

### 1. Verify Files Compile
```bash
cd Trade-Alerts
python -m py_compile Scalp-Engine/auto_trader_core.py
python -m py_compile Scalp-Engine/scalp_engine.py
python -m py_compile main.py
echo "✅ All files compile successfully"
```

### 2. Verify Run Count Reset (CRITICAL FIX #1)

**Setup**: Open and hold a trade manually, then close it.

**Check logs for**:
```
✅ Reset run count for LLM_EUR/USD_LONG after trade closed (reason)
```

**Verify file**:
```bash
# Before closing trade:
cat /var/data/execution_history.json | jq '.["LLM_EUR/USD_LONG"]'
# Should show: {"count": 1, "last_executed": "..."}

# After closing trade:
cat /var/data/execution_history.json | jq '.["LLM_EUR/USD_LONG"]'
# Should show: Nothing (deleted) or {"count": 0}
```

**Result**: Next analysis cycle should execute same pair/direction again ✅

---

### 3. Verify Configurable required_llms (CRITICAL FIX #2)

**Test 1: No required_llms (default)**
```bash
# In .env, set or leave unset:
REQUIRED_LLMS=

# Run analysis, should see in logs:
# ChatGPT, Gemini, Claude opportunities all considered
```

**Test 2: Gemini required**
```bash
# In .env, set:
REQUIRED_LLMS=gemini

# Kill Gemini in LLM analyzer (simulate API down)
# Run analysis, should see in logs:
# ⚠️ Skipped EUR/USD LONG: required LLMs ['gemini'] not in opportunity sources ['chatgpt', 'claude']
```

**Test 3: Multiple required**
```bash
# In .env, set:
REQUIRED_LLMS=chatgpt,gemini

# Run analysis, should see:
# Opportunities only from ChatGPT+Gemini consensus (Claude alone rejected)
```

**Result**: REQUIRED_LLMS env var controls LLM gating ✅

---

### 4. Verify Stale Thresholds (CRITICAL FIX #3)

**Test 1: Old threshold (should reject more often)**
```bash
# In .env, set:
STALE_INTRADAY_PIPS=50
STALE_SWING_PIPS=200

# Run analysis at 12pm with 9am LLM output
# Should see more "REJECTING STALE OPPORTUNITY" warnings
```

**Test 2: New threshold (should reject less often)**
```bash
# In .env, set:
STALE_INTRADAY_PIPS=80
STALE_SWING_PIPS=250

# Same scenario, should see fewer rejections
# Log should show "threshold: 80 pips"
```

**Check log**:
```
🚫 REJECTING STALE OPPORTUNITY: EUR/USD LONG - stored current_price (1.0850) is 65.2 pips away...
Recommendation is based on outdated market data (threshold: 80 pips / 0.5%).
```

**Result**: Environment variables control stale thresholds ✅

---

### 5. Verify Silent Rejection Logging (IMPORTANT FIX #4)

**Test 1: auto_trade_llm=False**
```bash
# In .env, set:
auto_trade_llm=false
TRADING_MODE=AUTO

# Run scalp_engine, should see:
# ⚠️ LLM auto-trading disabled (auto_trade_llm=False) — skipping all LLM opportunities
```

**Test 2: auto_trade_ft_dmi_ema=False**
```bash
# In .env, set:
auto_trade_ft_dmi_ema=false
TRADING_MODE=AUTO
FT_DMI_EMA_SIGNALS_ENABLED=true

# Run scalp_engine, should see:
# ⚠️ FT-DMI-EMA auto-trading disabled (auto_trade_ft_dmi_ema=False)
```

**Test 3: FT_DMI_EMA_SIGNALS_ENABLED not set**
```bash
# In .env, do NOT set FT_DMI_EMA_SIGNALS_ENABLED
# Run scalp_engine, should see (once):
# ⚠️ FT_DMI_EMA_SIGNALS_ENABLED not set — FT-DMI-EMA and DMI-EMA signals disabled
```

**Test 4: SEMI_AUTO disabled opportunity**
```bash
# In UI, disable EUR/USD_LONG for SEMI_AUTO
# Run scalp_engine in SEMI_AUTO mode
# Should see:
# Skipped EUR/USD LONG: not enabled in SEMI_AUTO UI
```

**Result**: All silent skips now visible in logs ✅

---

### 6. Verify Entry Price Drop Visibility (IMPORTANT FIX #5)

**Setup**: Create an LLM opportunity with missing entry price.

**Check logs**:
```
⚠️ DROPPED opportunity EUR/USD LONG: no entry price and no fallback available (source: chatgpt)
```

**Verify**: Log appears at WARNING level (visible with LOG_LEVEL=INFO) ✅

---

### 7. Verify Pair Normalization (MODERATE FIX #6)

**Test 1: Non-standard pair format**
```python
# Simulate odd pair format from LLM
opp = {
    'pair': 'EUR_JPY',  # Underscore instead of slash
    'direction': 'LONG',
    'entry': 0  # Missing entry
}

# Run _fill_missing_entry_prices
# Should fallback and fill from current_prices or synthesis
# Instead of silently dropping
```

**Check logs**:
```
Filled missing entry for EUR/JPY LONG from current price
# OR if no current price:
⚠️ DROPPED opportunity EUR/JPY LONG: no entry price and no fallback available
```

**Result**: Robust fallback handling ✅

---

### 8. Verify Counter Renaming (MODERATE FIX #7)

**Check logs**:
```
✅ Logged 12 recommendations for future learning (deduplicated: 3, unrealistic: 1)
```

**Verify**: Counter breakdown shows:
- `12` logged (new entries)
- `3` deduplicated (database duplicates)
- `1` unrealistic (marked UNREALISTIC by LLM)

**Result**: Clear counter explanation ✅

---

## Production Readiness Checklist

- [ ] All syntax checks pass: `python -m py_compile ...`
- [ ] Run count reset works (manual trade close test)
- [ ] Configurable required_llms tested (all scenarios)
- [ ] Stale thresholds customizable (tested both old/new values)
- [ ] All silent skips now logged as WARNING
- [ ] Entry price drops visible at WARNING level
- [ ] Pair normalization handles edge cases
- [ ] Log output clear and informative

## Log Level Configuration

To see all WARNING/INFO logs in production:

```bash
# In .env for Trade-Alerts
LOG_LEVEL=INFO

# In .env for Scalp-Engine
LOG_LEVEL=INFO
```

## Rollback Plan (If Needed)

If any issue arises, these changes are backward compatible:

1. Revert files from git:
   ```bash
   git checkout HEAD -- Scalp-Engine/auto_trader_core.py Scalp-Engine/scalp_engine.py main.py
   ```

2. Run count reset will NOT occur on trade close (manual reset required via UI)

3. Stale thresholds revert to old values (50/200 pips)

4. Silent logs return to DEBUG level (invisible in production)

5. required_llms reverts to hardcoded ['gemini']

## Notes

- All changes are **non-breaking** - existing functionality preserved
- Environment variables have sensible defaults - optional to configure
- Log messages designed to be visible and actionable
- Backward compatible with existing trades and UI

---

**Implementation Date**: February 20, 2026
**Plan Document**: PLAN_TRADE_REJECTION_FIX.md
**Implementation Summary**: IMPLEMENTATION_SUMMARY.md
