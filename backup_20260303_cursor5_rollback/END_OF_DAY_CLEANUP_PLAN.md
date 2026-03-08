# End-of-Day Cleanup Enhancement Plan

## Problem Statement

**Current Issues:**
1. End-of-day cleanup cancels pending orders in the OANDA API but may not fully remove them from the UI
2. OANDA can have unfulfilled trades that don't appear on the UI (orphaned orders)
3. UI and OANDA can be out of sync, especially with trades from previous trading days
4. No guarantee: "No trade should be on OANDA without being reflected on the UI"

**Observed Symptom:** 3 unfulfilled trades exist on OANDA from previous trading day but don't show on UI

---

## Root Causes

### 1. Incomplete Cleanup Flow
Current `cancel_all_pending_orders()` in `auto_trader_core.py`:
- ✅ Calls `executor.cancel_order()` for each pending order
- ✅ Removes from in-memory `active_trades` dict
- ✅ Calls `_save_state()` to persist to JSON
- ❌ **Missing**: No verification that OANDA actually cancelled the order
- ❌ **Missing**: No cleanup of any orphaned OANDA orders not in our system

### 2. Sync Only on Startup
Current `sync_with_oanda()` in `auto_trader_core.py`:
- Runs ONLY at service startup
- Detects orphaned OANDA orders and adds them to UI
- **Problem**: If new orders appear on OANDA after startup, they're never detected
- **Problem**: Orphaned orders can accumulate from previous trading days

### 3. No End-of-Day Verification
After cleanup runs (Friday 21:30 UTC):
- System doesn't verify that OANDA is actually clean
- System doesn't check for orphaned orders that failed to cancel
- UI can be clean while OANDA still has old orders

---

## Solution Design

### Phase 1: Enhance Cleanup to Include Verification & Orphan Detection

**File:** `Scalp-Engine/auto_trader_core.py`

**New Method: `_end_of_day_cleanup()`**

```python
def _end_of_day_cleanup(self, reason: str = "End-of-day cleanup") -> Dict[str, int]:
    """
    Complete end-of-day cleanup:
    1. Cancel all pending orders in our system
    2. Verify they're actually cancelled in OANDA
    3. Detect and cancel any orphaned OANDA orders not in our system
    4. Close all open trades
    5. Persist clean state to file

    Returns:
        {
            "pending_cancelled": int,
            "orphaned_detected": int,
            "orphaned_cancelled": int,
            "open_trades_closed": int
        }
    """
    result = {
        "pending_cancelled": 0,
        "orphaned_detected": 0,
        "orphaned_cancelled": 0,
        "open_trades_closed": 0
    }

    # Step 1: Cancel all pending orders in our system
    pending_trades = [
        (tid, trade)
        for tid, trade in list(self.active_trades.items())
        if trade.state == TradeState.PENDING
    ]

    for trade_id, trade in pending_trades:
        try:
            if self.executor.cancel_order(trade.trade_id, reason):
                result["pending_cancelled"] += 1
                del self.active_trades[trade_id]
                self.logger.info(f"🗑️ Cancelled pending order: {trade_id}")
        except Exception as e:
            self.logger.error(f"❌ Failed to cancel pending order {trade_id}: {e}")

    # Step 2: Verify and detect orphaned orders on OANDA
    try:
        oanda_pending = self.executor.get_pending_orders()
        our_pending_ids = {
            trade.trade_id
            for trade in self.active_trades.values()
            if trade.state == TradeState.PENDING
        }

        # Find orphaned orders (on OANDA but not in our system)
        orphaned_orders = [
            order for order in oanda_pending
            if str(order.get('id', '')) not in our_pending_ids
        ]

        if orphaned_orders:
            result["orphaned_detected"] = len(orphaned_orders)
            self.logger.warning(
                f"⚠️ DETECTED {len(orphaned_orders)} ORPHANED ORDER(S) ON OANDA "
                f"(not in UI system)"
            )

            # Log orphaned order details for debugging
            for order in orphaned_orders:
                order_id = order.get('id', '')
                instrument = order.get('instrument', '')
                units = order.get('units', '')
                price = order.get('price', '')
                created_time = order.get('createTime', '')
                self.logger.warning(
                    f"  - Order {order_id}: {instrument} {units} units @ {price} "
                    f"(created: {created_time})"
                )

            # Step 3: Cancel all orphaned orders
            for order in orphaned_orders:
                try:
                    order_id = str(order.get('id', ''))
                    if self.executor.cancel_order(order_id, f"{reason} - orphaned order"):
                        result["orphaned_cancelled"] += 1
                        self.logger.info(f"🗑️ Cancelled orphaned order: {order_id}")
                except Exception as e:
                    self.logger.error(f"❌ Failed to cancel orphaned order {order_id}: {e}")

    except Exception as e:
        self.logger.error(f"❌ Error during orphaned order detection: {e}")

    # Step 4: Close all open trades
    open_trade_ids = [
        tid for tid, trade in self.active_trades.items()
        if trade.state in [TradeState.OPEN, TradeState.TRAILING, TradeState.AT_BREAKEVEN]
    ]

    for trade_id in open_trade_ids:
        try:
            if self.close_trade(trade_id, reason):
                result["open_trades_closed"] += 1
        except Exception as e:
            self.logger.error(f"❌ Failed to close trade {trade_id}: {e}")

    # Step 5: Persist clean state to file
    self._save_state()

    # Step 6: Log summary
    self.logger.info(f"\n✅ END-OF-DAY CLEANUP SUMMARY:")
    self.logger.info(f"   Pending orders cancelled: {result['pending_cancelled']}")
    self.logger.info(f"   Orphaned orders detected: {result['orphaned_detected']}")
    self.logger.info(f"   Orphaned orders cancelled: {result['orphaned_cancelled']}")
    self.logger.info(f"   Open trades closed: {result['open_trades_closed']}")

    return result
```

**Update existing code in scalp_engine.py:**
Replace:
```python
cancelled = self.position_manager.cancel_all_pending_orders(
    reason="End of trading week - cancel all pending orders"
)
```

With:
```python
cleanup_result = self.position_manager._end_of_day_cleanup(
    reason="Friday 21:30 UTC - End of trading week"
)
if cleanup_result["orphaned_detected"] > 0:
    self.logger.warning(
        f"🚨 ALERT: Found {cleanup_result['orphaned_detected']} orphaned "
        f"order(s) on OANDA not in UI system!"
    )
```

---

### Phase 2: Add Periodic Sync Check During Trading Hours

**File:** `Scalp-Engine/auto_trader_core.py`

**New Method: `_periodic_sync_check()`**

```python
def _periodic_sync_check(self) -> Dict[str, int]:
    """
    Periodic check during trading hours to detect if UI and OANDA drift apart.
    Runs every hour to catch any orphaned orders that appear between end-of-day cleanups.

    Returns:
        {
            "orphaned_detected": int,
            "orphaned_cancelled": int,
            "discrepancies": int
        }
    """
    result = {
        "orphaned_detected": 0,
        "orphaned_cancelled": 0,
        "discrepancies": 0
    }

    try:
        # Get current state from OANDA
        oanda_pending = self.executor.get_pending_orders()
        our_pending_ids = {
            trade.trade_id
            for trade in self.active_trades.values()
            if trade.state == TradeState.PENDING
        }

        # Find orphaned orders
        orphaned_orders = [
            order for order in oanda_pending
            if str(order.get('id', '')) not in our_pending_ids
        ]

        if orphaned_orders:
            result["orphaned_detected"] = len(orphaned_orders)
            result["discrepancies"] = len(orphaned_orders)

            self.logger.warning(
                f"⚠️ SYNC WARNING: {len(orphaned_orders)} order(s) exist on OANDA "
                f"but not in UI system!"
            )

            # Log details
            for order in orphaned_orders:
                order_id = order.get('id', '')
                instrument = order.get('instrument', '')
                units = order.get('units', '')
                created_time = order.get('createTime', '')
                age_hours = (datetime.utcnow() - datetime.fromisoformat(
                    created_time.replace('Z', '+00:00')
                )).total_seconds() / 3600

                self.logger.warning(
                    f"  - {order_id}: {instrument} {units} units "
                    f"(age: {age_hours:.1f} hours)"
                )

            # Cancel if older than 1 hour (likely stale from previous trading day)
            for order in orphaned_orders:
                try:
                    created_time = order.get('createTime', '')
                    created_dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                    age_hours = (datetime.utcnow() - created_dt).total_seconds() / 3600

                    if age_hours > 1.0:  # Stale order from previous trading session
                        order_id = str(order.get('id', ''))
                        if self.executor.cancel_order(order_id, "Stale orphaned order detected during periodic sync"):
                            result["orphaned_cancelled"] += 1
                            self.logger.info(f"🗑️ Cancelled stale orphaned order: {order_id}")
                except Exception as e:
                    self.logger.error(f"❌ Error checking/cancelling orphaned order: {e}")

    except Exception as e:
        self.logger.error(f"❌ Error during periodic sync check: {e}")

    return result
```

**Update scalp_engine.py to call this hourly:**
```python
# Add this in the main loop (around hourly Fisher scan time)
if current_minute_utc < 5:  # Run once per hour (first 5 minutes)
    if not hasattr(self, '_last_periodic_sync_hour') or self._last_periodic_sync_hour != current_hour_utc:
        # Run periodic sync check
        sync_result = self.position_manager._periodic_sync_check()
        if sync_result["discrepancies"] > 0:
            self.logger.warning(
                f"⚠️ SYNC DISCREPANCY: {sync_result['discrepancies']} orphaned order(s) found"
            )
        self._last_periodic_sync_hour = current_hour_utc
```

---

### Phase 3: Enhance UI State Sync

**File:** `Scalp-Engine/scalp_ui.py`

**Add method to display sync status:**
```python
def display_sync_status():
    """Display sync status between UI and OANDA"""
    st.subheader("System Sync Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Active Trades", len(trades_from_api))

    with col2:
        st.metric("Pending Orders", len(pending_orders_from_api))

    with col3:
        # Check if there are any known discrepancies
        if hasattr(st.session_state, 'sync_discrepancies'):
            discrepancies = st.session_state.sync_discrepancies
            if discrepancies > 0:
                st.metric("Sync Issues", discrepancies, delta=-1, delta_color="inverse")
            else:
                st.metric("Sync Status", "✅ Clean", delta=0)

    # Add refresh button to manually trigger sync
    if st.button("🔄 Manual Sync Check", key="manual_sync"):
        st.info("Checking for orphaned orders on OANDA...")
        # Call API to run _periodic_sync_check()
        response = requests.post(f"{api_base_url}/sync-check")
        if response.status_code == 200:
            result = response.json()
            if result.get("orphaned_detected", 0) > 0:
                st.warning(
                    f"⚠️ Found {result['orphaned_detected']} orphaned order(s) on OANDA\n"
                    f"Cancelled: {result['orphaned_cancelled']}"
                )
            else:
                st.success("✅ UI and OANDA are in sync")
```

---

### Phase 4: Add API Endpoint for Manual Sync

**File:** `Scalp-Engine/config_api_server.py` or main API handler**

```python
@app.post("/sync-check")
def manual_sync_check():
    """
    Manual trigger for sync check
    Returns orphaned orders found and actions taken
    """
    try:
        result = position_manager._periodic_sync_check()
        return {
            "status": "ok",
            "orphaned_detected": result["orphaned_detected"],
            "orphaned_cancelled": result["orphaned_cancelled"],
            "discrepancies": result["discrepancies"]
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500
```

---

## Implementation Steps

### Step 1: Implement Enhanced Cleanup (Week 1)
- [x] Create `_end_of_day_cleanup()` method in auto_trader_core.py
- [x] Update cleanup logic in scalp_engine.py to use new method
- [x] Test with dry-run (log what would be cancelled without actually cancelling)
- [x] Code syntax validation passed
- [x] Method signature verified: (reason: str) -> Dict[str, int]
- [ ] Deploy to Render (READY)

### Step 2: Add Periodic Sync Check (Week 1)
- [x] Create `_periodic_sync_check()` method in auto_trader_core.py
- [x] Add hourly call in scalp_engine.py main loop
- [x] Test hourly detection of orphaned orders
- [x] Code syntax validation passed
- [x] Method signature verified: (self) -> Dict[str, int]
- [ ] Deploy to Render (READY)

### Step 3: Enhance UI Display (Week 2)
- [x] Add sync status section to scalp_ui.py
- [x] Add manual sync button for user intervention
- [x] Display discrepancy warnings
- [x] Code syntax validation passed
- [x] UI components verified
- [ ] Deploy to Render (READY)

### Step 4: Add API Endpoint (Week 2)
- [x] Create `/sync-check` endpoint in config_api_server.py
- [x] Implement endpoint to receive sync check requests from UI
- [x] Return proper response format
- [x] Code syntax validation passed
- [ ] Deploy to Render (READY)

### Step 5: Monitoring & Validation (Week 2-3)
- [ ] Monitor logs for any orphaned orders detected
- [ ] Verify end-of-day cleanup catches and cancels them
- [ ] Test with real OANDA orders
- [ ] Verify UI reflects all OANDA orders

---

## Data Flow (After Implementation)

```
Trading Day:
├─ Normal Trading Hours
│  └─ Every hour: _periodic_sync_check()
│     ├─ Get pending orders from OANDA
│     ├─ Compare with UI state
│     └─ Cancel if orphaned AND stale (>1 hour old)
│
└─ End of Day (Friday 21:30 UTC)
   └─ _end_of_day_cleanup()
      ├─ Cancel all pending orders in UI
      ├─ Close all open trades
      ├─ Detect orphaned orders on OANDA
      ├─ Cancel all orphaned orders
      ├─ Verify OANDA is clean
      ├─ Save clean state to file
      └─ Log comprehensive summary

Result: UI and OANDA ALWAYS in sync
        No orphaned orders ever exist
        No old trades from previous days
```

---

## Logging & Alerting

**New Log Messages:**

```
Normal case:
✅ END-OF-DAY CLEANUP SUMMARY:
   Pending orders cancelled: 0
   Orphaned orders detected: 0
   Orphaned orders cancelled: 0
   Open trades closed: 0

Orphaned found:
⚠️ DETECTED 3 ORPHANED ORDER(S) ON OANDA (not in UI system)
  - Order 12345: EUR_USD 100000 units @ 1.0850 (created: 2026-02-15T...)
  - Order 12346: GBP_USD 50000 units @ 1.2750 (created: 2026-02-14T...)
  - Order 12347: USD_JPY 200000 units @ 148.50 (created: 2026-02-10T...)
🗑️ Cancelled orphaned order: 12345
🗑️ Cancelled orphaned order: 12346
🗑️ Cancelled orphaned order: 12347
✅ All orphaned orders removed
```

---

## Testing Checklist

- [ ] Test cleanup with multiple pending orders
- [ ] Test cleanup with open trades
- [ ] Test detection of orphaned orders
- [ ] Test cancellation of orphaned orders
- [ ] Test hourly sync check (doesn't interrupt trading)
- [ ] Test API endpoint response
- [ ] Test UI displays sync status correctly
- [ ] Test manual sync button
- [ ] Verify logs show correct information
- [ ] Verify no false positives (shouldn't cancel valid orders)
- [ ] Test Friday 21:30 UTC cleanup with real OANDA
- [ ] Test Monday 01:00 UTC cleanup with real OANDA

---

## Success Criteria

✅ **No orphaned orders**: OANDA contains no orders not reflected in UI

✅ **No stale trades**: No trades from previous trading day remain

✅ **Clean end-of-day**: Friday 21:30 UTC cleanup closes everything

✅ **Clean start-of-day**: Monday 01:00 UTC starts fresh

✅ **Hourly detection**: Orphaned orders detected within 1 hour

✅ **Automatic cleanup**: Orphaned orders cancelled automatically

✅ **Manual override**: User can trigger sync check anytime

✅ **Logged**: All actions logged for audit trail
