# Stop Loss Bug Analysis & Correction Plan

## Problem Summary
Trades are transitioning from PENDING to OPEN status without stop loss orders being attached.

## Root Cause Analysis

### The Bug Location
**File:** `auto_trader_core.py`  
**Function:** `PositionManager.sync_with_oanda()`  
**Lines:** 1726-1774

### How It Should Work
1. When a LIMIT/STOP order is created, it's stored in `active_trades` with `order_id` as the key
2. The trade object has `state = PENDING` and `trade_id = None` (no trade_id yet)
3. When the order fills, OANDA creates a new trade with a `trade_id`
4. The sync function should:
   - Detect that a pending order has filled
   - Match the new trade_id to the existing pending order
   - Update the trade's `trade_id` and state to OPEN
   - **Set the stop loss** (this is what's failing)

### The Actual Bug
**Line 1732:** `if trade_id in our_trade_ids:`
- This check only passes if the trade_id is already in `our_trade_ids`
- `our_trade_ids` is built from trades where `trade.trade_id` is already set (line 1374-1375)
- **Pending orders have `trade.trade_id = None`**, so they're NOT in `our_trade_ids`
- Result: The check fails, and the code treats it as a new trade instead of a filled pending order

**Line 1735:** `if our_trade.trade_id == trade_id:`
- This tries to match by `trade_id`, but for pending orders, `our_trade.trade_id` is `None`
- **This match always fails for pending orders**
- Result: The pending order is never found, so it's never updated and stop loss is never set

### Why Stop Loss Isn't Set
The stop loss setting code (lines 1754-1770) is inside the `if our_trade.trade_id == trade_id:` block, which never matches for pending orders. Therefore:
- The pending order's state never changes to OPEN
- The `trade_id` is never updated
- **The stop loss is never set**

## Correction Plan

### Fix Strategy
The matching logic needs to handle two cases:
1. **Already-open trades:** Match by `trade_id` (existing logic works)
2. **Pending orders that just filled:** Match by pair + direction (new logic needed)

### Implementation Steps

#### Step 1: Fix the Matching Logic (Lines 1732-1771)
**Current flow:**
```
if trade_id in our_trade_ids:
    # Try to match by trade_id
    for our_trade_id, our_trade in list(self.active_trades.items()):
        if our_trade.trade_id == trade_id:
            # Update and set stop loss
```

**New flow:**
```
# First, try to match by trade_id (for already-open trades)
matched_trade = None
matched_key = None

if trade_id in our_trade_ids:
    # Match by trade_id (existing logic)
    for our_trade_id, our_trade in list(self.active_trades.items()):
        if our_trade.trade_id == trade_id:
            matched_trade = our_trade
            matched_key = our_trade_id
            break

# If no match, try to match pending orders by pair + direction
if not matched_trade:
    oanda_pair = oanda_trade.get('instrument', '')
    oanda_units = float(oanda_trade.get('currentUnits', 0))
    oanda_direction = "LONG" if oanda_units > 0 else "SHORT"
    
    for our_trade_id, our_trade in list(self.active_trades.items()):
        if our_trade.state == TradeState.PENDING:
            # Normalize pair for comparison
            normalized_pair = self.normalize_pair(our_trade.pair)
            normalized_oanda_pair = self.normalize_pair(oanda_pair)
            
            # Match by pair and direction
            if (normalized_pair == normalized_oanda_pair and 
                our_trade.direction.upper() in [oanda_direction.upper(), 
                                                 "BUY" if oanda_direction == "LONG" else "SELL"]):
                matched_trade = our_trade
                matched_key = our_trade_id
                break

# If we found a match (either by trade_id or pair+direction), update it
if matched_trade:
    # Update trade_id if it was a pending order
    if matched_trade.state == TradeState.PENDING:
        matched_trade.trade_id = trade_id
        # Update the key in active_trades if needed
        if matched_key != trade_id:
            self.active_trades[trade_id] = matched_trade
            if matched_key in self.active_trades:
                del self.active_trades[matched_key]
    
    # Update entry price, state, and set stop loss (existing logic)
    # ... (rest of the update code)
```

#### Step 2: Update Entry Price Logic
Move the entry price update logic outside the `if our_trade.trade_id == trade_id:` check so it applies to both matched cases.

#### Step 3: Ensure Stop Loss is Set for All Filled Orders
The stop loss setting code (lines 1757-1770) should execute for:
- Pending orders that just filled (LIMIT/STOP orders)
- Any trade that transitions from PENDING to OPEN

#### Step 4: Add Logging
Add detailed logging to track:
- When a pending order is matched by pair+direction
- When trade_id is updated
- When stop loss is successfully set
- When stop loss setting fails (with retry mechanism)

### Code Changes Required

**File:** `personal/Trade-Alerts/Scalp-Engine/auto_trader_core.py`

**Location:** `PositionManager.sync_with_oanda()` method, starting at line 1726

**Changes:**
1. Replace the matching logic (lines 1732-1771) with the new two-stage matching approach
2. Ensure `trade_id` is updated when a pending order is matched
3. Ensure the key in `active_trades` is updated from `order_id` to `trade_id`
4. Ensure stop loss is set for all filled pending orders

### Testing Checklist
After implementation, verify:
- [ ] Pending LIMIT orders that fill get stop loss set
- [ ] Pending STOP orders that fill get stop loss set
- [ ] Trade state correctly transitions from PENDING to OPEN
- [ ] Trade_id is correctly updated when order fills
- [ ] active_trades dictionary key is updated from order_id to trade_id
- [ ] No duplicate trades are created
- [ ] Logging shows successful stop loss attachment
- [ ] Retry mechanism works if stop loss setting fails initially

### Risk Assessment
**Low Risk:** This is a bug fix that adds missing functionality. The change:
- Only affects the matching logic in sync function
- Doesn't change order creation logic
- Adds fallback matching for pending orders
- Preserves all existing functionality for already-open trades

### Rollback Plan
If issues occur:
1. The bug fix can be reverted by restoring the original matching logic
2. No data loss risk (only affects in-memory state)
3. OANDA trades remain unaffected (stop loss can be set manually if needed)

## Summary
The bug prevents pending orders from being matched to their filled trades, causing stop loss to never be set. The fix adds pair+direction matching for pending orders, ensuring they're properly updated when they fill and stop loss is attached.
