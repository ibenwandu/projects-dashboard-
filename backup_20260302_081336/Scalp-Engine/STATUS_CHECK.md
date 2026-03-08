# Scalp-Engine Status Guide

## What You Should See When Running

When you run `python scalp_engine.py`, here's what to expect:

### ✅ Normal Startup (First 5 seconds)

```
================================================================================
Scalp-Engine Started | MODE: MANUAL
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

[DEBUG] Loading market state (loop #1)...
```

### Status Scenarios

#### Scenario 1: Waiting for Market State
```
Waiting for Trade-Alerts to generate market state...
```
**Meaning:** Trade-Alerts hasn't generated `market_state.json` yet  
**Action:** Run Trade-Alerts first, or wait for it to generate the state file

#### Scenario 2: Market State Loaded, No Approved Pairs
```
Market State Updated:
   Regime: NORMAL
   Bias: NEUTRAL
   Approved Pairs: 

PAUSED: No approved pairs. Waiting for Trade-Alerts to provide pairs...
```
**Meaning:** Market state exists but no pairs are approved for trading  
**Action:** This is normal - wait for Trade-Alerts to approve pairs, or check Trade-Alerts configuration

#### Scenario 3: Approved Pairs Available, Scanning for Signals
```
Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY

[DEBUG] Getting account info (loop #20)...
```
**Meaning:** System is active, checking pairs for trading signals  
**Action:** Wait for signals - this is normal operation

#### Scenario 4: Signal Detected (Manual Mode)
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   ✅ RL CHECK: 62.5% win rate (24 trades) - PASSED
   [MANUAL] Execute BUY on EUR/USD? (y/n): 
```
**Meaning:** Signal found, waiting for your input  
**Action:** Type `y` to execute or `n` to skip

#### Scenario 5: Signal Detected (Auto Mode)
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   ✅ RL CHECK: 62.5% win rate (24 trades) - PASSED
EXECUTING: BUY EUR/USD - Size: 1000 units
SUCCESS: Order placed (ID: 12345)
         Trade opened (ID: 67890)
   ✅ Trade tracking enabled (Signal ID: 1, Trade ID: 67890)
```
**Meaning:** Signal found and executed automatically  
**Action:** Monitor for trade closure updates

#### Scenario 6: Signal Filtered by RL
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   ⚠️  RL FILTER: Skipping BUY EUR/USD
      Historical: 35.0% win rate (15 trades)
      Threshold: 50.0% required for TRENDING regime
```
**Meaning:** Signal was filtered due to low historical win rate  
**Action:** This is working correctly - system is learning!

#### Scenario 7: Trade Closed
```
📊 Trade 67890 closed: PnL = 8.50
✅ RL Update: Trade 1 closed as WIN (8.50)
```
**Meaning:** Trade closed and outcome recorded in RL database  
**Action:** System is learning from this trade

---

## Quick Status Check Commands

### Check if it's running
Look for the banner at the top - if you see it, the engine started successfully.

### Check current mode
Look for `MODE: MANUAL` or `MODE: AUTO` in the banner.

### Check if waiting for market state
Look for: `"Waiting for Trade-Alerts to generate market state..."`

### Check if paused
Look for: `"PAUSED: No approved pairs..."`

### Check if active
Look for: `"Market State Updated:"` with approved pairs listed.

### Check for signals
Look for: `"🔔 SIGNAL:"` messages.

### Check for trade execution
Look for: `"EXECUTING:"` and `"SUCCESS:"` messages.

### Check for trade tracking
Look for: `"Trade tracking enabled"` messages.

### Check for closed trades
Look for: `"📊 Trade ... closed:"` messages.

---

## Common Issues & Solutions

### Issue: "Waiting for Trade-Alerts..."
**Solution:** 
1. Check if Trade-Alerts is running
2. Verify `market_state.json` exists in Trade-Alerts folder
3. Check file path in `.env` if using custom path

### Issue: "No approved pairs"
**Solution:**
1. This is normal if Trade-Alerts hasn't found opportunities
2. Check Trade-Alerts logs to see why pairs aren't approved
3. Verify LLMs are enabled in Trade-Alerts if needed

### Issue: No signals appearing
**Solution:**
1. Check if approved pairs match your configured pairs
2. Verify EMA signals are being generated (check signal strength threshold)
3. Check spread - signals won't execute if spread > max_spread_pips

### Issue: "ERROR: Failed to start Scalp-Engine"
**Solution:**
1. Check OANDA credentials in `.env`
2. Verify all required environment variables are set
3. Check Python dependencies are installed

### Issue: Trades not executing
**Solution:**
1. Check mode (manual vs auto)
2. In manual mode, you need to type `y` when prompted
3. Check risk manager - may be blocking trades
4. Check spread - may be too wide

---

## Expected Behavior Timeline

### 0-5 seconds: Startup
- Banner displayed
- Configuration loaded
- Components initialized

### 5-10 seconds: First market state check
- Attempts to load market state
- Either loads or waits

### Every 60 seconds: Market state refresh
- Reloads market state from Trade-Alerts
- Updates regime, bias, approved pairs

### Every 30 seconds: Trade closure check
- Checks for closed trades
- Updates RL database

### Every 0.5 seconds: Signal scanning
- Checks approved pairs for signals
- Processes signals if found

---

## What "Normal" Looks Like

**Normal operation** means you see:
1. ✅ Banner on startup
2. ✅ Market state loading every 60 seconds
3. ✅ "PAUSED" messages if no pairs (this is OK)
4. ✅ Signal detection when conditions are met
5. ✅ Trade execution (manual or auto)
6. ✅ Trade tracking messages
7. ✅ Trade closure updates

**The system is working correctly if:**
- No error messages
- Periodic market state updates
- Signals appear when market conditions are right
- Trades execute when approved (in auto mode) or when you approve (in manual mode)

---

## How to Check Database Status

While the engine is running, you can check the RL database in another terminal:

```powershell
# Check signals logged
sqlite3 scalping_rl.db "SELECT COUNT(*) as total_signals FROM signals;"

# Check pending trades
sqlite3 scalping_rl.db "SELECT COUNT(*) as pending FROM signals WHERE outcome = 'PENDING';"

# Check completed trades
sqlite3 scalping_rl.db "SELECT COUNT(*) as completed FROM signals WHERE outcome != 'PENDING';"

# View recent signals
sqlite3 scalping_rl.db "SELECT id, pair, direction, regime, strength, outcome, pnl FROM signals ORDER BY timestamp DESC LIMIT 5;"
```

---

## Status Indicators Summary

| Indicator | Status | Meaning |
|-----------|--------|---------|
| Banner displayed | ✅ Running | Engine started successfully |
| "Waiting for Trade-Alerts..." | ⏳ Waiting | Need to run Trade-Alerts |
| "PAUSED: No approved pairs" | ⏸️ Paused | Normal - waiting for opportunities |
| "Market State Updated" | ✅ Active | System is scanning for signals |
| "🔔 SIGNAL:" | 🎯 Signal Found | Trading opportunity detected |
| "EXECUTING:" | 🚀 Trading | Trade is being executed |
| "Trade tracking enabled" | 📊 Tracking | Trade is being monitored |
| "Trade ... closed" | ✅ Complete | Trade finished, outcome recorded |
| Error messages | ❌ Problem | Check error details |

---

**If you're seeing the banner and periodic updates, the system is running correctly!** 🎉
