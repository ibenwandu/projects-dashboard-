# Quick Run Guide for Scalp-Engine

## The Issue: "It's Hanging"

**Scalp-Engine is NOT hanging** - it's working correctly! Here's what's happening:

1. ✅ All components tested successfully
2. ✅ OANDA connection works
3. ✅ Market state file is loaded
4. ⚠️ **No approved pairs** in the state file (empty array)

**This is NORMAL behavior** - Scalp-Engine is waiting for Trade-Alerts to provide trading pairs.

---

## How to Run It (See What's Happening)

### Option 1: Run Directly (Recommended)

Open a **new PowerShell terminal** and run:

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
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

PAUSED: No approved pairs. Sleeping...
PAUSED: No approved pairs. Sleeping...
```

**This is CORRECT** - it's waiting for pairs. Press `Ctrl+C` to stop.

---

### Option 2: Run with PowerShell Script

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
.\run_scalp_engine.ps1
```

---

## Why It Seems to "Hang"

The script has a **main loop** that:
1. Checks market state every 60 seconds
2. If no approved pairs → sleeps for 5 seconds, then repeats
3. This creates the appearance of "hanging" but it's actually **waiting**

---

## To Get Real Trading Activity

You need **approved pairs** in `market_state.json`. To get them:

### Step 1: Enable LLMs in Trade-Alerts

Edit `Trade-Alerts/.env` and add at least ONE of:
- `OPENAI_API_KEY=sk-...`
- `GOOGLE_API_KEY=...`
- `ANTHROPIC_API_KEY=sk-ant-...`

### Step 2: Generate Real Market State

```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
python run_immediate_analysis.py
```

### Step 3: Check the Results

```powershell
Get-Content market_state.json | ConvertFrom-Json | Select-Object approved_pairs
```

Should show something like:
```
approved_pairs: ["EUR/USD", "USD/JPY"]
```

### Step 4: Run Scalp-Engine Again

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python scalp_engine.py
```

Now you'll see:
```
Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY

[Scalp-Engine will now monitor these pairs for signals]
```

---

## Summary

**Current Status:**
- ✅ Scalp-Engine is working correctly
- ✅ All components tested and functional
- ⚠️ Waiting for approved pairs (expected behavior)

**Next Steps:**
1. Run `python scalp_engine.py` to see it working
2. Enable LLMs and generate real market state for actual trading
3. Scalp-Engine will automatically pick up new pairs when available

**To Stop:** Press `Ctrl+C` in the terminal

