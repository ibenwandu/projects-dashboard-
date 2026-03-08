# Immediate Action Items
## March 3, 2026 - Post-Analysis

---

## 🚨 CRITICAL: STOP LIVE TRADING

**Status:** DEMO MODE ONLY until critical issues fixed

**Reason:** 0% win rate with multiple simultaneous failures

---

## TODAY'S PRIORITIES (4-6 Hours)

### TASK 1: Investigate Manual Trade Closures (2-3 Hours)
**Why:** 80% of trades closed manually - this is the biggest anomaly

**Search Points:**
```bash
# Find all MARKET_ORDER close calls
grep -r "TRADE_CLOSE\|TradeClose\|close_trade" Scalp-Engine/*.py

# Check UI for close buttons
grep -r "st.button.*[Cc]lose\|close_trade_button" Scalp-Engine/*.py

# Check risk manager for emergency closes
grep -r "emergency\|force.*close\|max.*loss" Scalp-Engine/src/risk_manager.py
```

**Expected Outcome:**
- Identify WHO is calling close
- Add logging to that path
- Understand why 80% manually closed

**Files to Review:**
1. `Scalp-Engine/scalp_ui.py` - Search for "Close" button
2. `Scalp-Engine/auto_trader_core.py` - Search for "close_trade", "TRADE_CLOSE"
3. `Scalp-Engine/src/risk_manager.py` - Search for emergency close logic
4. `Scalp-Engine/config_api_server.py` - Check for close endpoints

---

### TASK 2: Verify max_runs Reset Logic (1-2 Hours)
**Why:** Blocking 50+ trades on Feb 27

**Debug Steps:**
```python
# In Scalp-Engine/auto_trader_core.py, find:
# 1. Where max_runs is checked (REJECT)
# 2. Where reset_run_count() is called
# 3. Verify execution_enforcer.reset_run_count() actually exists

# Add logging:
logger.info(f"[max_runs] Checking: has_open={has_existing_position(pair, dir)}")
if has_open is False:
    logger.info(f"[max_runs] Resetting run count for {opp_id}")
    execution_enforcer.reset_run_count(opp_id)
```

**Verify:**
- [ ] reset_run_count() function exists
- [ ] It's being called when no position exists
- [ ] It's actually updating the counter
- [ ] Next trade for same pair can execute

**Files to Review:**
1. `Scalp-Engine/auto_trader_core.py` - PositionManager.open_trade()
2. `Scalp-Engine/src/execution/execution_enforcer.py` - reset_run_count() method

---

### TASK 3: Add Logging for Trailing SL (1-2 Hours)
**Why:** EUR/JPY loss suggests trailing SL not working

**What to Log:**
```python
# In risk_manager.py or before OANDA order:
logger.info(f"[SL] Creating order with SL={stop_loss}")
logger.info(f"[SL] SL Type: {config.get('stop_loss_type', 'STATIC')}")
logger.info(f"[SL] ATR Multiplier: {config.get('atr_multiplier', 'N/A')}")

# After each price update (if trailing):
logger.info(f"[SL] EUR/JPY: price={current_price}, SL={current_sl} (adjusted from {prev_sl})")
```

**Verify:**
- [ ] Initial SL matches what we set
- [ ] SL moves when price moves (for ATR_TRAILING)
- [ ] EUR/JPY case: SL moved correctly

**Files to Review:**
1. `Scalp-Engine/src/risk_manager.py` - Trailing SL logic
2. `Scalp-Engine/auto_trader_core.py` - OANDA order creation
3. Check OANDA trade details: SL column shows current SL value

---

## THIS WEEK'S PRIORITIES (5-10 Hours)

### TASK 4: Fix Consensus Denominator (1 Hour)
**File:** `Trade-Alerts/src/market_bridge.py`

**Current (Broken):**
```python
base_llms = ['chatgpt', 'gemini', 'claude', 'synthesis']
denominator = len(base_llms)  # Always 4
```

**Fix:**
```python
# Count actual LLMs in opportunities
available_llms = set()
for opp in all_opportunities.values():
    available_llms.update([o['llm_source'] for o in opp])

# Use actual count for denominator
denominator = len(available_llms)
```

---

### TASK 5: Fix max_runs Reset Logic (2-3 Hours)
**File:** `Scalp-Engine/auto_trader_core.py`

**Current (Broken):**
- max_runs checked but reset not working
- Add verification logging

**Fix:**
```python
if directive == "REJECT" and reason == "max_runs":
    if not self.has_existing_position(pair, direction):
        logger.warning(f"[max_runs RESET] No position for {pair} {direction}, resetting...")
        self.execution_enforcer.reset_run_count(opp_id)
        # Re-get directive after reset
        directive = self.execution_enforcer.get_execution_directive(opp_id)
        if directive in ["EXECUTE_NOW", "PLACE_PENDING"]:
            logger.info(f"[max_runs RESET OK] {pair} {direction} can now execute")
        else:
            logger.warning(f"[max_runs RESET] Still rejected after reset: {directive}")
            return None, reason
```

---

### TASK 6: Add Orphan Trade Detection (1-2 Hours)
**File:** `Scalp-Engine/src/execution/execution_enforcer.py` (new method)

**Add:**
```python
def check_for_orphan_trades(self, oanda_open_trades):
    """Check if any OANDA trades are not in execution history."""
    execution_pairs = set()
    for trade_id, trade_info in self.execution_history.items():
        if trade_info.get('status') == 'OPEN':
            execution_pairs.add(trade_info['pair'])

    oanda_pairs = set([t['pair'] for t in oanda_open_trades])
    orphans = oanda_pairs - execution_pairs

    if orphans:
        logger.warning(f"[ORPHANS] Found {len(orphans)} orphan trades: {orphans}")

    return orphans
```

---

## NEXT WEEK'S PRIORITIES (10-15 Hours)

### TASK 7: Test 10+ Demo Days
**Criteria:**
- [ ] At least 10 consecutive profitable days
- [ ] max_runs not blocking
- [ ] Manual closures stopped
- [ ] All 7 quality checklist items verified

**Before promoting to small live account (0.01 lots only):**
- [ ] 20+ profitable days
- [ ] >40% win rate
- [ ] All critical issues resolved
- [ ] RL learning verified running

---

## DEMO TEST PLAN

### Day 1-3: Unit Testing
- [ ] Test max_runs reset individually
- [ ] Test trailing SL with demo positions
- [ ] Test close buttons (UI and auto)

### Day 4-13: Live Demo Trading
- [ ] Run full system in DEMO (no real money)
- [ ] Monitor all 7 quality checklist items
- [ ] Verify manual closures stopped
- [ ] Verify RL daily learning running
- [ ] Document results in spreadsheet

**Spreadsheet Columns:**
| Date | Trades | Wins | Losses | Win% | Manual Close? | SL Working? | max_runs Issues? | P&L |
|------|--------|------|--------|------|---------------|----|---|-----|

---

## DETAILED FILES TO INVESTIGATE

### Must Review for Manual Closes
```
Scalp-Engine/scalp_ui.py          # Is there a close button?
Scalp-Engine/auto_trader_core.py  # What calls MARKET_ORDER TRADE_CLOSE?
Scalp-Engine/config_api_server.py # Is there a /close endpoint?
Scalp-Engine/scalp_engine.py      # Any auto-close logic?
Scalp-Engine/src/risk_manager.py  # Emergency close on max loss?
```

### Must Review for Trailing SL
```
Scalp-Engine/src/risk_manager.py  # How is ATR_TRAILING calculated?
Scalp-Engine/auto_trader_core.py  # What SL is sent to OANDA?
Trade-Alerts/src/                 # Any SL overrides?
```

### Must Review for max_runs
```
Scalp-Engine/auto_trader_core.py           # Where is max_runs checked?
Scalp-Engine/src/execution/                # Where is reset_run_count()?
execution_enforcer.py / execution_mode_enforcer.py  # Which one?
```

---

## VERIFICATION CHECKLIST

After implementing fixes, verify:

- [ ] **max_runs** - Run same pair trade 2x in a row: should succeed both times
- [ ] **Trailing SL** - Open EUR/JPY SELL in demo, watch SL column in UI as price moves
- [ ] **Manual Close** - Open a trade, DON'T manually close, verify auto-manages to TP/SL
- [ ] **Consensus** - Check market_state.json, verify denominator is actual LLM count
- [ ] **Trading Hours** - Try placing order on Saturday, verify blocked
- [ ] **Sync** - Compare OANDA open trades vs UI open trades, should match
- [ ] **RL Learning** - Check Render logs for daily_learning() execution
- [ ] **Orphan Trades** - Manually kill Scalp-Engine, restart, verify orphans detected

---

## DEBUGGING COMMANDS

### Find All Close Calls
```bash
cd Scalp-Engine
grep -r "TRADE_CLOSE\|trade_close\|close_trade" --include="*.py" .
```

### Find Manual Close Button
```bash
grep -r "button.*[Cc]lose\|Close.*button\|close.*form" --include="*.py" .
```

### Find All max_runs References
```bash
grep -r "max_runs" --include="*.py" .
```

### Find All SL Setting
```bash
grep -r "stop.loss\|stop_loss\|SL.*=" --include="*.py" . | grep -v comment
```

---

## SUCCESS CRITERIA

### To Resume Small Live Trading (0.01 lots):
1. ✅ 10+ consecutive profitable demo days
2. ✅ 0% manual closures (all auto-managed)
3. ✅ max_runs never blocks legitimate trades
4. ✅ Trailing SL verified working
5. ✅ All 7 quality checklist items passing
6. ✅ RL daily learning running

### To Scale to Normal Lots:
1. ✅ 20+ profitable days at 0.01 lots
2. ✅ 40%+ win rate maintained
3. ✅ All fixes stable and reliable
4. ✅ Consensus working with correct denominator
5. ✅ Trading hours enforcement verified
6. ✅ Sync between touchpoints verified stable

---

## DOCUMENT LOCATIONS

- **Full Analysis:** `/CROSS_TOUCHPOINT_ANALYSIS_MARCH_3.json`
- **Human-Readable:** `/TRADING_SYSTEM_AUDIT_MARCH_3_2026.md`
- **This Document:** `/IMMEDIATE_ACTION_ITEMS_MARCH_3.md`

---

## CONTACT POINTS FOR QUESTIONS

If issues unclear, review these CLAUDE.md sections:
- **Feb 25 Rollback:** Why previous implementation failed
- **Feb 26 consol-recommend2:** What changed and why
- **Feb 28 consol-recommend3:** Latest implementation (some fixes may be incomplete)
- **Session Mar 2:** Cross-touchpoint analysis context

---

**Status:** READY FOR ACTION
**Last Updated:** March 3, 2026
**Next Review:** After Phase 0 completion (today)
