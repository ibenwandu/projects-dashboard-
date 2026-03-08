# How to View Selected Trading Pairs

## Quick Answer: Check Render Logs

The easiest way to see selected pairs is through **Render Logs**.

### Step 1: View Logs

1. Go to **Render Dashboard** → `scalp-engine` service
2. Click **"Logs"** tab (in the left sidebar)
3. Look for messages like:

```
Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY
```

---

## Understanding the Output

### What You'll See in Logs

**When Scalp-Engine starts:**
```
================================================================================
Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================
```

**When market state is loaded:**
```
Market State Updated:
   Regime: NORMAL
   Bias: NEUTRAL
   Approved Pairs: EUR/USD, USD/JPY
```

**If no pairs are available:**
```
PAUSED: No approved pairs. Waiting for Trade-Alerts to provide pairs...
```

---

## Where Pairs Come From

Scalp-Engine gets approved pairs from **Trade-Alerts** via `market_state.json`.

### Current Status

1. **Scalp-Engine is running** ✅
2. **Waiting for Trade-Alerts** to generate `market_state.json` with approved pairs
3. **Once pairs are available**, Scalp-Engine will automatically pick them up

---

## How to Get Trading Pairs

### Option 1: Wait for Trade-Alerts (Automatic)

If Trade-Alerts is deployed and running:
- It generates `market_state.json` with approved pairs
- Scalp-Engine checks every 60 seconds
- Pairs will appear automatically in logs

### Option 2: Generate Market State Manually

If Trade-Alerts is not deployed yet:

1. **Run Trade-Alerts locally** to generate market state:
   ```powershell
   cd C:\Users\user\projects\personal\Trade-Alerts
   python run_immediate_analysis.py
   ```

2. **This creates** `market_state.json` with approved pairs

3. **Scalp-Engine will pick it up** (if both are on the same system)

### Option 3: Check Current Market State

You can check what's in the market state file:

```powershell
# If Trade-Alerts is local
cd C:\Users\user\projects\personal\Trade-Alerts
Get-Content market_state.json | ConvertFrom-Json | Select-Object approved_pairs, global_bias, regime
```

---

## What to Look For in Logs

### ✅ Good Signs (Pairs Available)

```
Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY

[Scalp-Engine will now monitor these pairs]
```

### ⚠️ Waiting (No Pairs Yet)

```
Market State Updated:
   Regime: NORMAL
   Bias: NEUTRAL
   Approved Pairs: 

PAUSED: No approved pairs. Waiting for Trade-Alerts to provide pairs...
```

This is **NORMAL** if Trade-Alerts hasn't generated pairs yet.

---

## Integration with Trade-Alerts

### How It Works

1. **Trade-Alerts** analyzes market conditions
2. **Generates** `market_state.json` with:
   - Approved pairs (from LLM analysis)
   - Market regime (TRENDING, RANGING, etc.)
   - Global bias (BULLISH, BEARISH, NEUTRAL)
3. **Scalp-Engine** reads this file every 60 seconds
4. **Monitors** approved pairs for trading signals
5. **Executes** trades when signals are detected

### Current Setup

- **Scalp-Engine**: Running on Render ✅
- **Trade-Alerts**: Needs to be running (local or Render)
- **Integration**: Via `market_state.json` file

---

## Next Steps

### 1. Check Current Status

Look at Render logs to see:
- Is Scalp-Engine running? ✅
- Are there approved pairs? (Check logs)
- What's the market state?

### 2. Get Trading Pairs

**If Trade-Alerts is deployed:**
- Wait for scheduled analysis (usually runs at specific times)
- Or trigger manual analysis
- Pairs will appear in Scalp-Engine logs automatically

**If Trade-Alerts is not deployed:**
- Deploy Trade-Alerts to Render
- Or run it locally to generate market state
- Scalp-Engine will pick up pairs when available

### 3. Monitor Trading Activity

Once pairs are available, watch logs for:
- Signal detection: `Signal: BUY EUR/USD (Strength: 0.75)`
- Trade execution: `EXECUTING: BUY EUR/USD - Size: 1000 units`
- Order confirmation: `SUCCESS: Order placed: [order_id]`

---

## Quick Commands

### View Logs in Render
1. Dashboard → `scalp-engine` → Logs tab
2. Real-time log streaming
3. Search for "Approved Pairs" to see current pairs

### Check Market State (Local)
```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
Get-Content market_state.json | ConvertFrom-Json | Select-Object approved_pairs
```

### Generate Market State (Local)
```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
python run_immediate_analysis.py
```

---

## Summary

**To see selected pairs:**
1. ✅ Check Render logs (easiest)
2. ✅ Look for "Approved Pairs:" in log messages
3. ✅ Pairs update every 60 seconds when market state changes

**If no pairs showing:**
- Trade-Alerts needs to generate them first
- This is normal - Scalp-Engine is waiting
- Once Trade-Alerts runs, pairs will appear automatically

**Next:** Get Trade-Alerts running to generate trading pairs! 🚀

