# Scalp-Engine: Complete Next Steps Guide

## Current Situation

✅ **What's Working:**
- OANDA credentials are configured
- `market_state.json` file exists
- Scalp-Engine code is ready

⚠️ **What Needs Attention:**
- `market_state.json` has **0 approved pairs** (empty `approved_pairs: []`)
- This means Scalp-Engine will wait but won't find any pairs to trade
- LLMs weren't enabled during the test run, so no real analysis was generated

---

## Step-by-Step Instructions

### STEP 1: Verify Current Setup

Run these commands to confirm everything is in place:

```powershell
# 1. Check OANDA credentials
cd C:\Users\user\projects\personal\Scalp-Engine
Get-Content .env | Select-String "OANDA"

# 2. Verify market_state.json exists
Test-Path ..\Trade-Alerts\market_state.json

# 3. Check what's in the state file
Get-Content ..\Trade-Alerts\market_state.json | ConvertFrom-Json | Select-Object approved_pairs, global_bias, regime
```

**Expected Output:**
- OANDA token and account ID should be visible
- `market_state.json` should return `True`
- `approved_pairs` will likely be empty `[]` (this is OK for testing)

---

### STEP 2: Understand What Scalp-Engine Needs

Scalp-Engine needs:
1. **Approved pairs** in `market_state.json` (from Trade-Alerts analysis)
2. **Market regime** (TRENDING, RANGING, or HIGH_VOL)
3. **Global bias** (BULLISH, BEARISH, or NEUTRAL)

**Current state:** All empty/neutral because LLMs weren't enabled.

---

### STEP 3: Choose Your Path

You have **TWO OPTIONS**:

#### **OPTION A: Test Scalp-Engine with Empty State (Recommended First)**

This lets you verify Scalp-Engine runs without errors, even with no trading pairs:

```powershell
# Navigate to Scalp-Engine
cd C:\Users\user\projects\personal\Scalp-Engine

# Run Scalp-Engine
python scalp_engine.py
```

**What You'll See:**
```
================================================================================
Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

Market State Updated:
   Regime: NORMAL
   Bias: NEUTRAL
   Approved Pairs: 

No approved pairs. Sleeping...
No approved pairs. Sleeping...
```

**This is NORMAL** - Scalp-Engine is waiting for Trade-Alerts to provide approved pairs.

**To Stop:** Press `Ctrl + C`

---

#### **OPTION B: Generate Real Market State (For Actual Trading)**

To get real trading pairs, you need to enable LLMs and run a full analysis:

**2a. Enable at least ONE LLM in Trade-Alerts `.env`:**

```powershell
# Go to Trade-Alerts directory
cd C:\Users\user\projects\personal\Trade-Alerts

# Check current .env (see what's missing)
Get-Content .env | Select-String -Pattern "OPENAI|GOOGLE|ANTHROPIC"
```

**You need at least ONE of these:**
- `OPENAI_API_KEY=sk-...` (for ChatGPT)
- `GOOGLE_API_KEY=...` (for Gemini)
- `ANTHROPIC_API_KEY=sk-ant-...` (for Claude)

**2b. Run immediate analysis again:**

```powershell
# Still in Trade-Alerts directory
python run_immediate_analysis.py
```

**2c. Check the new market_state.json:**

```powershell
Get-Content market_state.json | ConvertFrom-Json | Select-Object approved_pairs, global_bias, regime, total_opportunities
```

**Expected Output (if LLMs worked):**
```
approved_pairs: ["EUR/USD", "USD/JPY"]
global_bias: BULLISH
regime: TRENDING
total_opportunities: 2
```

**2d. Now run Scalp-Engine:**

```powershell
cd ..\Scalp-Engine
python scalp_engine.py
```

**What You'll See (with real pairs):**
```
================================================================================
Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY

[Scalp-Engine will now monitor EUR/USD and USD/JPY for signals]
```

---

### STEP 4: Verify Scalp-Engine is Working

Once Scalp-Engine is running, you should see:

**✅ Good Signs:**
- No error messages
- "Market State Updated" messages every 60 seconds
- "Checking pair: EUR/USD" messages (if pairs are approved)
- "Signal: BUY EUR/USD (Strength: 0.75)" messages (when signals are found)

**❌ Problem Signs:**
- "ERROR: Could not get current price" → OANDA connection issue
- "ERROR: Failed to fetch candles" → OANDA API issue
- "Waiting for Trade-Alerts..." → market_state.json missing or stale

---

### STEP 5: Monitor Scalp-Engine Activity

**What Scalp-Engine Does:**
1. **Every 60 seconds:** Refreshes market state from `market_state.json`
2. **Every 0.5 seconds:** Checks approved pairs for trading signals
3. **When signal found:** Executes trade via OANDA (if spread is acceptable)

**Key Messages to Watch For:**
- `"Signal: BUY EUR/USD (Strength: 0.75)"` → Signal detected
- `"Executing BUY EUR/USD - Size: 1000 units"` → Trade executing
- `"Order placed: 12345678"` → Trade successful
- `"WARNING: Spread too wide"` → Skipping trade (spread > 1.5 pips)

---

## Troubleshooting

### Problem: "No approved pairs. Sleeping..."

**Solution:** 
- Run `run_immediate_analysis.py` in Trade-Alerts with LLMs enabled
- Or wait for scheduled Trade-Alerts run at 09:00 EST

### Problem: "ERROR: Could not get current price"

**Solution:**
- Check OANDA credentials in `.env`
- Verify OANDA account is active
- Check internet connection

### Problem: "ERROR: Failed to fetch candles"

**Solution:**
- OANDA API might be temporarily unavailable
- Check OANDA status page
- Verify pair names match OANDA format (e.g., "EUR_USD" not "EUR/USD")

### Problem: Scalp-Engine hangs or freezes

**Solution:**
- Check if it's waiting for market state (normal behavior)
- Press `Ctrl + C` to stop, then restart
- Check logs for specific error messages

---

## Quick Reference Commands

```powershell
# Start Scalp-Engine
cd C:\Users\user\projects\personal\Scalp-Engine
python scalp_engine.py

# Generate market state (from Trade-Alerts)
cd C:\Users\user\projects\personal\Trade-Alerts
python run_immediate_analysis.py

# Check market state
Get-Content C:\Users\user\projects\personal\Trade-Alerts\market_state.json | ConvertFrom-Json

# Stop Scalp-Engine
# Press Ctrl + C in the terminal where it's running
```

---

## Next Actions

**Right Now:**
1. ✅ Run `python scalp_engine.py` to verify it starts (Option A)
2. ✅ Confirm it reads the market state file
3. ✅ See that it waits for approved pairs (expected behavior)

**For Real Trading:**
1. Enable LLMs in Trade-Alerts `.env`
2. Run `run_immediate_analysis.py` to generate real pairs
3. Restart Scalp-Engine to pick up new pairs
4. Monitor for signals and trades

---

## Questions?

- **"Why no trades?"** → No approved pairs yet, or no signals detected
- **"Is it working?"** → Check for "Market State Updated" messages
- **"How do I stop it?"** → Press `Ctrl + C`
- **"When will it trade?"** → When approved pairs exist AND signals are detected

