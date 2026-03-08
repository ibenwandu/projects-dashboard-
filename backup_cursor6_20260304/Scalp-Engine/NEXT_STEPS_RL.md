# Next Steps: RL Integration & Trade Tracking

## ✅ Completed

1. **RL Database Created** (`src/scalping_rl.py`)
   - SQLite database for tracking signals and outcomes
   - Signal logging before execution
   - Outcome tracking structure (WIN/LOSS)

2. **Manual Mode Implemented**
   - Execution mode toggle in `config.yaml`
   - Manual confirmation prompts for each signal
   - Auto mode for unattended operation

3. **Enhanced Signal Logging**
   - Regime, strength, and EMA spread tracking
   - Signal ID tracking for outcome updates

---

## 🎯 Immediate Next Steps (Priority Order)

### **Step 1: Trade Tracking & Outcome Updates** ⚠️ CRITICAL

**Problem:** Currently, signals are logged but trade outcomes are never updated in the RL database. The system can't learn from results.

**Solution:** Implement trade monitoring to track when trades close and update RL outcomes.

**Implementation:**

1. **Add Trade Tracking to `scalp_engine.py`:**
   ```python
   # Track active trades: {signal_id: trade_id}
   self.active_trades = {}  # signal_id -> trade_id mapping
   ```

2. **Extract Trade ID from Order Response:**
   ```python
   # In execute_trade(), after successful order:
   if order_response:
       trade_id = order_response.get('orderFillTransaction', {}).get('tradeOpened', {}).get('id')
       if trade_id and sig_id:
           self.active_trades[sig_id] = trade_id
   ```

3. **Add OANDA Methods to `src/oanda_client.py`:**
   ```python
   def get_open_positions(self) -> List[Dict]:
       """Get all open positions"""
       from oandapyV20.endpoints.positions import OpenPositions
       r = OpenPositions(accountID=self.account_id)
       self.client.request(r)
       return r.response.get('positions', [])
   
   def get_trade_details(self, trade_id: str) -> Optional[Dict]:
       """Get details of a specific trade"""
       from oandapyV20.endpoints.trades import TradeDetails
       r = TradeDetails(accountID=self.account_id, tradeID=trade_id)
       self.client.request(r)
       return r.response.get('trade', {})
   ```

4. **Add Trade Monitoring Loop:**
   ```python
   # In run() loop, periodically check for closed trades:
   if loop_count % 60 == 0:  # Check every 30 seconds (60 * 0.5s)
       self._check_closed_trades()
   
   def _check_closed_trades(self):
       """Check for closed trades and update RL outcomes"""
       open_positions = self.oanda_client.get_open_positions()
       open_trade_ids = {pos.get('id') for pos in open_positions}
       
       for sig_id, trade_id in list(self.active_trades.items()):
           if trade_id not in open_trade_ids:
               # Trade closed, get final PnL
               trade_details = self.oanda_client.get_trade_details(trade_id)
               if trade_details:
                   pnl = float(trade_details.get('realizedPL', 0))
                   self.rl_tracker.update_outcome(sig_id, pnl)
               del self.active_trades[sig_id]
   ```

**Files to Modify:**
- `scalp_engine.py` - Add trade tracking
- `src/oanda_client.py` - Add position/trade query methods
- `src/scalping_rl.py` - Already has `update_outcome()` method

---

### **Step 2: Use RL Data to Filter Signals** 🧠 INTELLIGENT FILTERING

**Problem:** RL database is logging data but not using it to make better decisions.

**Solution:** Query historical performance before executing signals and skip low-probability setups.

**Implementation:**

1. **Add RL-Based Signal Filtering:**
   ```python
   # In run() loop, before executing:
   if signal and strength > 0.5:
       # Check RL performance for this setup
       perf = self.rl_tracker.get_historical_performance(
           regime=regime,
           min_strength=strength
       )
       
       # Skip if win rate is too low (need at least 10 trades for confidence)
       if perf['total_trades'] >= 10 and perf['win_rate'] < 0.4:
           print(f"⚠️  Skipping {signal} {pair}: Low win rate ({perf['win_rate']:.1%})")
           continue
   ```

2. **Add Regime-Specific Thresholds:**
   ```python
   # Different thresholds per regime
   regime_thresholds = {
       'HIGH_VOL': 0.6,  # Need 60% win rate in high volatility
       'TRENDING': 0.5,  # 50% win rate acceptable in trends
       'RANGING': 0.55,  # 55% needed in ranging markets
       'NORMAL': 0.45    # 45% minimum in normal conditions
   }
   ```

**Files to Modify:**
- `scalp_engine.py` - Add RL filtering logic
- `src/scalping_rl.py` - Already has `get_historical_performance()` method

---

### **Step 3: Testing & Validation** 🧪

**Manual Testing:**

1. **Test Manual Mode:**
   ```bash
   # Set mode: "manual" in config.yaml
   python scalp_engine.py
   # Verify prompts appear for each signal
   ```

2. **Test RL Logging:**
   ```bash
   # Run engine, execute a few trades
   # Check database:
   sqlite3 scalping_rl.db "SELECT * FROM signals;"
   ```

3. **Test Auto Mode:**
   ```bash
   # Set mode: "auto" in config.yaml
   # Verify trades execute without prompts
   ```

**Database Inspection:**
```sql
-- View all signals
SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10;

-- View win rate by regime
SELECT regime, 
       COUNT(*) as total,
       SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
       ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY regime;

-- View win rate by strength range
SELECT 
    CASE 
        WHEN strength < 0.6 THEN 'Low (0-0.6)'
        WHEN strength < 0.8 THEN 'Medium (0.6-0.8)'
        ELSE 'High (0.8+)'
    END as strength_range,
    COUNT(*) as total,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
FROM signals 
WHERE outcome != 'PENDING'
GROUP BY strength_range;
```

---

### **Step 4: Enhanced Features** 🚀

#### **A. Trade ID Extraction Fix**

Currently, `execute_trade()` extracts order ID but not trade ID. Fix the extraction:

```python
# In execute_trade(), after order_response:
if order_response:
    # OANDA returns tradeOpened in orderFillTransaction
    fill_trans = order_response.get('orderFillTransaction', {})
    trade_opened = fill_trans.get('tradeOpened', {})
    trade_id = trade_opened.get('id')
    
    if trade_id:
        return trade_id  # Return trade_id instead of True
    return None
```

#### **B. Position Size Tracking**

Store position size in RL database for better analysis:

```python
# Add to signals table:
ALTER TABLE signals ADD COLUMN position_size REAL;
```

#### **C. Time-Based Analysis**

Add time-of-day analysis to RL:

```python
# Add to signals table:
ALTER TABLE signals ADD COLUMN hour INTEGER;  # Hour of day (0-23)

# When logging signal:
hour = datetime.now().hour
```

#### **D. Pair-Specific Performance**

Track which pairs are most profitable:

```python
# Query by pair:
perf = self.rl_tracker.get_historical_performance_by_pair(pair)
```

---

## 📊 Expected Outcomes

After implementing Step 1 (Trade Tracking):

- ✅ RL database will have complete trade history
- ✅ System can analyze which setups are profitable
- ✅ Win rates by regime/strength will be available

After implementing Step 2 (RL Filtering):

- ✅ System will skip historically poor setups
- ✅ Win rate should improve over time
- ✅ Fewer losing trades executed

---

## 🔧 Quick Start: Implement Step 1

**Minimum viable implementation (30 minutes):**

1. Add `active_trades` dict to `ScalpEngine.__init__()`
2. Extract trade_id from order response in `execute_trade()`
3. Store mapping: `self.active_trades[sig_id] = trade_id`
4. Add `get_open_positions()` to `OandaClient`
5. Add `_check_closed_trades()` method to `ScalpEngine`
6. Call `_check_closed_trades()` periodically in main loop

This will close the loop and enable the system to learn from its trades.

---

## 📝 Notes

- **Database Location:** `scalping_rl.db` is created in the current working directory
- **Manual Mode:** Blocks on `input()` - consider async input for production
- **Trade Monitoring:** OANDA API rate limits apply (check every 30-60 seconds)
- **RL Learning:** Need at least 20-30 trades before filtering becomes reliable

---

## 🎓 Learning Path

1. **Week 1:** Implement trade tracking (Step 1)
2. **Week 2:** Collect 20-30 trades, analyze patterns
3. **Week 3:** Implement RL filtering (Step 2)
4. **Week 4:** Tune thresholds based on actual performance
5. **Ongoing:** Monitor and refine based on results
