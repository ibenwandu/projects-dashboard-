# Testing Guide: Step 3 - Validation & Testing ✅

## Overview

This guide provides comprehensive testing procedures for validating Steps 1, 2, and 4 implementations.

---

## 🧪 Pre-Testing Checklist

### Environment Setup
- [ ] OANDA practice account credentials configured in `.env`
- [ ] `OANDA_ENV=practice` set in environment
- [ ] Trade-Alerts is running and generating `market_state.json`
- [ ] Database file `scalping_rl.db` will be created automatically (or exists from previous runs)

### Configuration
- [ ] `config.yaml` has `execution.mode: "manual"` for initial testing
- [ ] Trading pairs configured in `config.yaml`
- [ ] Risk parameters are set appropriately for testing

---

## 📋 Test Suite

### Test 1: Manual Mode Functionality

**Objective:** Verify manual mode prompts work correctly

**Steps:**
1. Set `execution.mode: "manual"` in `config.yaml`
2. Start Scalp-Engine: `python scalp_engine.py`
3. Wait for a signal to be generated

**Expected Output:**
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   [MANUAL] Execute BUY on EUR/USD? (y/n): 
```

**Test Cases:**
- [ ] Type `y` → Trade should execute
- [ ] Type `n` → Trade should be skipped
- [ ] Type `Y` (uppercase) → Should work (case-insensitive)
- [ ] Type anything else → Should be skipped

**Verification:**
- Check console output shows "EXECUTING" when `y` is entered
- Check console output shows "Skipped." when `n` is entered

---

### Test 2: Auto Mode Functionality

**Objective:** Verify auto mode executes without prompts

**Steps:**
1. Set `execution.mode: "auto"` in `config.yaml`
2. Start Scalp-Engine: `python scalp_engine.py`
3. Wait for a signal to be generated

**Expected Output:**
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   ✅ RL CHECK: 62.5% win rate (24 trades) - PASSED
EXECUTING: BUY EUR/USD - Size: 1000 units
```

**Test Cases:**
- [ ] No prompt appears
- [ ] Trade executes automatically
- [ ] Console shows execution messages

**Verification:**
- No `[MANUAL]` prompts should appear
- Trades should execute immediately after RL check passes

---

### Test 3: RL Database Logging

**Objective:** Verify signals are logged to RL database

**Steps:**
1. Start Scalp-Engine in manual mode
2. Execute at least 2-3 trades (approve signals)
3. Stop the engine
4. Check database: `sqlite3 scalping_rl.db "SELECT * FROM signals;"`

**Expected Database Records:**
```
id | timestamp           | pair    | direction | regime   | strength | ema_spread | outcome | pnl  | position_size | hour
1  | 2024-01-15T10:30:00 | EUR/USD | BUY       | TRENDING | 0.75     | 2.5        | PENDING | 0.0  | 1000         | 10
2  | 2024-01-15T10:35:00 | USD/JPY | SELL      | NORMAL   | 0.65     | 1.8        | PENDING | 0.0  | 1000         | 10
```

**Test Cases:**
- [ ] Each signal generates a database record
- [ ] `position_size` is populated (not 0.0)
- [ ] `hour` is populated (0-23)
- [ ] `outcome` is "PENDING" for new signals
- [ ] `pnl` is 0.0 for new signals

**Verification SQL:**
```sql
-- Check all signals
SELECT * FROM signals ORDER BY timestamp DESC;

-- Verify position_size is populated
SELECT COUNT(*) FROM signals WHERE position_size > 0;

-- Verify hour is populated
SELECT COUNT(*) FROM signals WHERE hour IS NOT NULL AND hour BETWEEN 0 AND 23;
```

---

### Test 4: Trade Tracking (Step 1)

**Objective:** Verify trades are tracked and outcomes updated

**Steps:**
1. Start Scalp-Engine in auto mode
2. Execute a trade (wait for signal)
3. Monitor console for trade ID extraction
4. Wait for trade to close (TP or SL hit)
5. Check console for outcome update message
6. Check database for updated outcome

**Expected Console Output:**
```
EXECUTING: BUY EUR/USD - Size: 1000 units
SUCCESS: Order placed (ID: 12345)
         Trade opened (ID: 67890)
   ✅ Trade tracking enabled (Signal ID: 1, Trade ID: 67890)

[... later when trade closes ...]

📊 Trade 67890 closed: PnL = 8.50
✅ RL Update: Trade 1 closed as WIN (8.50)
```

**Test Cases:**
- [ ] Trade ID is extracted from order response
- [ ] `active_trades` dictionary is populated
- [ ] Trade closure is detected (within 30 seconds)
- [ ] PnL is extracted correctly
- [ ] Database outcome is updated (WIN/LOSS)
- [ ] Trade is removed from `active_trades`

**Verification SQL:**
```sql
-- Check for updated outcomes
SELECT id, pair, outcome, pnl FROM signals WHERE outcome != 'PENDING';

-- Verify WIN/LOSS distribution
SELECT outcome, COUNT(*) as count FROM signals WHERE outcome != 'PENDING' GROUP BY outcome;
```

**Manual Verification:**
```python
# In Python console, check active_trades
# (This would require adding a debug method or checking during runtime)
```

---

### Test 5: RL-Based Filtering (Step 2)

**Objective:** Verify RL filtering skips low-probability signals

**Prerequisites:** Need at least 10 trades in database with low win rate

**Steps:**
1. **Setup:** Execute 10+ trades in same regime (e.g., TRENDING)
   - Manually update some to LOSS in database to create low win rate
   - Or wait for natural losses
2. Generate a new signal in same regime
3. Check console for RL filter message

**Expected Output (Filtered):**
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   ⚠️  RL FILTER: Skipping BUY EUR/USD
      Historical: 35.0% win rate (15 trades)
      Threshold: 50.0% required for TRENDING regime
```

**Expected Output (Passed):**
```
🔔 SIGNAL: BUY EUR/USD (Strength: 0.75)
   ✅ RL CHECK: 62.5% win rate (24 trades) - PASSED
   [MANUAL] Execute BUY on EUR/USD? (y/n):
```

**Test Cases:**
- [ ] Signal with < 10 trades → Executes normally (no filter)
- [ ] Signal with ≥ 10 trades, win rate < threshold → Filtered
- [ ] Signal with ≥ 10 trades, win rate ≥ threshold → Passed
- [ ] Different regimes have different thresholds

**Manual Database Setup (for testing):**
```sql
-- Create test scenario: 15 trades with 35% win rate
-- Update some outcomes to LOSS
UPDATE signals 
SET outcome = 'LOSS', pnl = -5.0 
WHERE id IN (SELECT id FROM signals WHERE outcome = 'PENDING' LIMIT 9);

UPDATE signals 
SET outcome = 'WIN', pnl = 8.0 
WHERE id IN (SELECT id FROM signals WHERE outcome = 'PENDING' LIMIT 6);
```

**Verification:**
```sql
-- Check current win rate
SELECT 
    regime,
    COUNT(*) as total,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY regime;
```

---

### Test 6: Position Size Tracking (Step 4B)

**Objective:** Verify position sizes are tracked correctly

**Steps:**
1. Execute trades with different account balances
2. Check database for position_size values

**Expected Behavior:**
- Position size should match calculated size from risk manager
- Different account balances should result in different position sizes

**Verification SQL:**
```sql
-- Check position sizes
SELECT pair, position_size, outcome, pnl 
FROM signals 
WHERE outcome != 'PENDING'
ORDER BY position_size DESC;

-- Average position size by outcome
SELECT 
    outcome,
    AVG(position_size) as avg_size,
    MIN(position_size) as min_size,
    MAX(position_size) as max_size
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY outcome;
```

---

### Test 7: Time-Based Analysis (Step 4C)

**Objective:** Verify hour tracking works correctly

**Steps:**
1. Execute trades at different times of day
2. Check database for hour values

**Expected Behavior:**
- `hour` column should contain 0-23 values
- Hour should match the time when signal was logged

**Verification SQL:**
```sql
-- Check hour distribution
SELECT 
    hour,
    COUNT(*) as trades,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY hour
ORDER BY hour;

-- Verify hour matches timestamp
SELECT 
    timestamp,
    hour,
    CAST(strftime('%H', timestamp) AS INTEGER) as hour_from_timestamp
FROM signals
LIMIT 10;
-- hour should match hour_from_timestamp
```

---

### Test 8: Pair-Specific Performance Queries (Step 4D)

**Objective:** Verify new query methods work correctly

**Steps:**
1. Execute trades on multiple pairs
2. Use Python to test query methods

**Test Script:**
```python
from src.scalping_rl import ScalpingRL

rl = ScalpingRL("scalping_rl.db")

# Test pair-specific query
perf = rl.get_historical_performance_by_pair("EUR/USD")
print(f"EUR/USD: {perf}")

# Test hour-specific query
perf = rl.get_historical_performance_by_hour(10)  # 10 AM
print(f"10 AM: {perf}")

# Test all hourly stats
hourly = rl.get_all_hourly_performance()
for hour, stats in hourly.items():
    print(f"{hour}:00 - {stats}")
```

**Expected Output:**
```
EUR/USD: {'win_rate': 0.625, 'avg_pnl': 5.2, 'total_trades': 8}
10 AM: {'win_rate': 0.7, 'avg_pnl': 6.5, 'total_trades': 10}
0:00 - {'win_rate': 0.5, 'avg_pnl': 4.0, 'total_trades': 2}
...
```

**Test Cases:**
- [ ] `get_historical_performance_by_pair()` returns correct stats
- [ ] `get_historical_performance_by_hour()` returns correct stats
- [ ] `get_all_hourly_performance()` returns all hours with trades
- [ ] Filters (regime, min_strength) work correctly

---

## 🔍 Comprehensive Database Analysis

### Full Performance Report

```sql
-- Complete performance overview
SELECT 
    'Overall' as category,
    COUNT(*) as total_trades,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(pnl), 2) as total_pnl
FROM signals 
WHERE outcome != 'PENDING'

UNION ALL

-- By regime
SELECT 
    'Regime: ' || regime as category,
    COUNT(*) as total_trades,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(pnl), 2) as total_pnl
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY regime

UNION ALL

-- By pair
SELECT 
    'Pair: ' || pair as category,
    COUNT(*) as total_trades,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(pnl), 2) as total_pnl
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY pair

UNION ALL

-- By hour
SELECT 
    'Hour: ' || hour || ':00' as category,
    COUNT(*) as total_trades,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(pnl), 2) as total_pnl
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY hour
ORDER BY category;
```

---

## ⚠️ Troubleshooting

### Issue: Trades not being tracked

**Symptoms:**
- No "Trade tracking enabled" message
- `active_trades` dictionary empty

**Solutions:**
1. Check order response structure - OANDA API may have changed
2. Verify `tradeOpened` key exists in response
3. Add debug logging to see full order response

### Issue: Trade outcomes not updating

**Symptoms:**
- Trades close but database not updated
- No "RL Update" messages

**Solutions:**
1. Check `_check_closed_trades()` is being called (every 30s)
2. Verify `get_open_trades()` returns correct format
3. Check `get_trade_details()` for closed trades (may need transactions endpoint)
4. Add error logging in `_check_closed_trades()`

### Issue: RL filtering not working

**Symptoms:**
- All signals execute regardless of win rate
- No RL filter messages

**Solutions:**
1. Verify database has ≥ 10 trades with outcomes
2. Check win rate calculation: `SELECT ...` query
3. Verify regime matching (case-sensitive)
4. Check threshold values in code

### Issue: Position size is 0.0

**Symptoms:**
- All `position_size` values are 0.0 in database

**Solutions:**
1. Verify position size calculation happens before logging
2. Check `calculate_position_size()` returns valid value
3. Ensure `log_signal()` is called with position_size parameter

---

## ✅ Test Completion Checklist

- [ ] Test 1: Manual mode works
- [ ] Test 2: Auto mode works
- [ ] Test 3: RL database logging works
- [ ] Test 4: Trade tracking works
- [ ] Test 5: RL filtering works
- [ ] Test 6: Position size tracking works
- [ ] Test 7: Time-based analysis works
- [ ] Test 8: Query methods work
- [ ] All database queries return expected results
- [ ] No errors in console output
- [ ] All features integrated and working together

---

## 📊 Success Criteria

The implementation is successful if:

1. ✅ **Manual Mode:** Prompts appear and user input is respected
2. ✅ **Auto Mode:** Trades execute without prompts
3. ✅ **RL Logging:** All signals logged with complete data
4. ✅ **Trade Tracking:** Trades tracked from execution to closure
5. ✅ **Outcome Updates:** Database updated when trades close
6. ✅ **RL Filtering:** Low-probability signals are filtered
7. ✅ **Position Tracking:** Position sizes stored correctly
8. ✅ **Time Tracking:** Hours captured correctly
9. ✅ **Query Methods:** All new query methods work correctly

---

## 🎯 Next Steps After Testing

Once all tests pass:

1. **Production Readiness:**
   - Switch to `mode: "auto"` for live trading
   - Monitor for 1-2 weeks
   - Collect 20-30 trades minimum

2. **Analysis:**
   - Run comprehensive database analysis
   - Identify best pairs, hours, regimes
   - Calculate optimal thresholds

3. **Optimization:**
   - Adjust regime thresholds based on actual performance
   - Implement pair-specific filtering
   - Implement time-based filtering
   - Optimize position sizing

4. **Documentation:**
   - Document findings
   - Create performance reports
   - Update configuration based on learnings

---

## 📝 Test Report Template

After completing tests, document results:

```
Test Date: ___________
Tester: ___________

Test Results:
- Manual Mode: [PASS/FAIL] - Notes: ___________
- Auto Mode: [PASS/FAIL] - Notes: ___________
- RL Logging: [PASS/FAIL] - Notes: ___________
- Trade Tracking: [PASS/FAIL] - Notes: ___________
- RL Filtering: [PASS/FAIL] - Notes: ___________
- Position Tracking: [PASS/FAIL] - Notes: ___________
- Time Tracking: [PASS/FAIL] - Notes: ___________
- Query Methods: [PASS/FAIL] - Notes: ___________

Issues Found: ___________
Recommendations: ___________
```

---

**Status:** Ready for testing! 🚀
