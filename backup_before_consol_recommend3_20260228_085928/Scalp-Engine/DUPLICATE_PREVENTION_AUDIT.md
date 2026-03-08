# Duplicate Order Prevention - Comprehensive Audit

## STRICT RULE: Only ONE order (pending or open) per currency pair is allowed

This document audits all code paths where trades/orders are created to ensure duplicate prevention is in place.

---

## ✅ All Trade Creation Paths - Duplicate Prevention Status

### 1. **State File Loading (`_load_state()`)**
**Location:** `auto_trader_core.py:569-610`

**Protection:**
- ✅ Checks if `trade_id` already exists before adding
- ✅ Checks if pair already exists (one order per pair rule)
- ✅ Logs warnings/errors when duplicates detected
- ✅ Skips duplicates instead of adding them
- ✅ Includes PENDING state in check

**Status:** ✅ PROTECTED

---

### 2. **OANDA Sync - Open Trades (`sync_with_oanda()`)**
**Location:** `auto_trader_core.py:1385-1415`

**Protection:**
- ✅ Checks for existing trades by pair (not just trade_id) before adding
- ✅ Logs RED FLAG errors when duplicates detected
- ✅ Skips adding if trade for that pair already exists
- ✅ Also checks if trade_id already exists

**Status:** ✅ PROTECTED

---

### 3. **OANDA Sync - Pending Orders (`sync_with_oanda()`)**
**Location:** `auto_trader_core.py:1313-1340`

**Protection:**
- ✅ Checks for existing trades by pair before adding
- ✅ Logs RED FLAG errors when duplicates detected
- ✅ Skips adding if order for that pair already exists
- ✅ Also checks if order_id already exists

**Status:** ✅ PROTECTED

---

### 4. **New Trade from Opportunity (`open_trade()` in PositionManager)**
**Location:** `auto_trader_core.py:858-910`

**Protection:**
- ✅ `has_existing_position(pair)` check before opening (line 866)
- ✅ Final duplicate check before adding to active_trades (line 894-920)
- ✅ Closes/cancels trade if duplicate detected after opening
- ✅ Returns None if duplicate found

**Status:** ✅ PROTECTED (Double-checked)

---

### 5. **Opportunity Processing (`_check_new_opportunities()`)**
**Location:** `scalp_engine.py:900-909`

**Protection:**
- ✅ `has_existing_position(pair)` check before processing opportunity (line 901)
- ✅ Logs RED FLAG error when blocking duplicate
- ✅ Skips opportunity if duplicate found

**Status:** ✅ PROTECTED

---

### 6. **HYBRID MACD Trigger (`_check_hybrid_macd_triggers()`)**
**Location:** `scalp_engine.py:1299-1313`

**Protection:**
- ✅ `has_existing_position(pair)` check before opening market trade (line 1299)
- ✅ Duplicate check before adding to active_trades (line 1307-1327)
- ✅ Closes trade if duplicate detected after opening

**Status:** ✅ PROTECTED (Just added)

---

### 7. **Pending Order Replacement (`_review_and_replace_pending_trades()`)**
**Location:** `scalp_engine.py:1217-1236`

**Protection:**
- ✅ Cancels old order FIRST before creating new one (line 1218-1223)
- ✅ Only creates new order after old one is cancelled
- ✅ Logs error if cancellation fails

**Status:** ✅ PROTECTED (Old order cancelled first)

---

### 8. **Duplicate Cleanup (`_cancel_duplicate_pending_orders()`)**
**Location:** `auto_trader_core.py:1390-1606`

**Protection:**
- ✅ Groups all orders by pair
- ✅ Keeps only most recent, cancels rest
- ✅ Handles both pending orders and open trades
- ✅ Logs RED FLAG errors for all violations
- ✅ Runs on every sync cycle

**Status:** ✅ PROTECTED (Cleanup mechanism)

---

## 🔒 Defense Layers

The system has **multiple layers of duplicate prevention**:

1. **Prevention Layer 1:** `has_existing_position()` check before opening
   - Used in: `_check_new_opportunities()`, `open_trade()`, `_check_hybrid_macd_triggers()`
   - Checks both `active_trades` and OANDA directly

2. **Prevention Layer 2:** Duplicate check before adding to `active_trades`
   - Used in: `_load_state()`, `sync_with_oanda()`, `open_trade()`, `_check_hybrid_macd_triggers()`
   - Checks by pair before adding

3. **Prevention Layer 3:** Duplicate cleanup on every sync
   - `_cancel_duplicate_pending_orders()` runs after every `sync_with_oanda()` call
   - Cancels any duplicates that slip through

4. **Prevention Layer 4:** State file duplicate filtering
   - `_load_state()` filters duplicates when loading from disk
   - Prevents duplicates from persisting across restarts

---

## 🎯 Key Protection Points

### On Service Restart:
1. ✅ `_load_state()` filters duplicates from state file
2. ✅ `sync_with_oanda()` checks for duplicates before adding from OANDA
3. ✅ `_cancel_duplicate_pending_orders()` cleans up any that slip through

### On New Trade Creation:
1. ✅ `_check_new_opportunities()` checks `has_existing_position()` first
2. ✅ `open_trade()` checks `has_existing_position()` again
3. ✅ `open_trade()` checks for duplicates before adding to `active_trades`
4. ✅ If duplicate detected after opening, trade is closed/cancelled

### On HYBRID MACD Trigger:
1. ✅ Checks `has_existing_position()` before opening market trade
2. ✅ Checks for duplicates before adding to `active_trades`
3. ✅ Closes trade if duplicate detected

### On Every Sync Cycle:
1. ✅ `sync_with_oanda()` checks for duplicates before adding
2. ✅ `_cancel_duplicate_pending_orders()` cleans up any duplicates

---

## 📊 Summary

**Total Protection Points:** 8
**All Protected:** ✅ YES
**Multiple Defense Layers:** ✅ YES (4 layers)
**Automatic Cleanup:** ✅ YES

**Conclusion:** The system is now comprehensively protected against duplicate orders for the same pair. Multiple layers of defense ensure that even if one check fails, others will catch it.

---

## 🚨 What Happens If Duplicate Is Detected

1. **Before Opening:** Trade is blocked, logged as RED FLAG error
2. **After Opening (before adding):** Trade is closed/cancelled, logged as RED FLAG error
3. **During Sync:** Duplicate is skipped, logged as RED FLAG error
4. **During Cleanup:** Duplicate is cancelled/closed, logged as RED FLAG error

All violations are logged at ERROR level with RED FLAG prefix for maximum visibility.
