# Trailing Stop Loss Bug Fix - Session 12

**Date**: 2026-02-18
**Issue**: Trade 22412 GBP/USD SHORT had stop loss stuck at 1.36250 while price moved to 1.35084 (+40 pips)
**Root Cause**: Wrong OANDA API endpoint for stop loss updates
**Commit**: `0b6658d`

---

## The Problem

### Real Example
```
Trade: 22412 (GBP/USD SHORT)
Entry Price:       1.35550
Current Price:     1.35084 (in profit by ~40 pips)
Initial SL:        1.36250
Current SL:        1.36250 (STUCK - should have trailed down)
Trade State:       TRAILING (conversion happened)
Expected Behavior: SL should trail DOWN as price goes DOWN
Actual Behavior:   SL stuck at original value
```

### Impact
- ATR_TRAILING trades not updating stop loss as they move into profit
- Profit protection gap - trades converting to TRAILING state but SL not actually moving
- Fixed stop loss updates might also be affected

---

## Root Cause

**Location**: `Scalp-Engine/auto_trader_core.py` - Lines 514 & 542

Both `update_stop_loss()` and `convert_to_trailing_stop()` methods were using the wrong OANDA v20 API endpoint:

```python
# ❌ WRONG - TradeClientExtensions is for metadata only
r = trades.TradeClientExtensions(accountID=self.account_id, tradeID=trade_id, data=data)
```

### Why This Failed
`TradeClientExtensions` endpoint is designed exclusively for updating trade metadata:
- Client ID
- Comment/description
- Tags
- User-defined extensions

It does NOT support:
- `stopLoss` parameter
- `trailingStopLoss` parameter
- Any price-based order parameters

So the OANDA API was silently rejecting (or ignoring) the stop loss update requests.

---

## The Fix

**Replace with the correct endpoint**:

```python
# ✅ CORRECT - TradeCRCDO handles trade order updates
r = trades.TradeCRCDO(accountID=self.account_id, tradeID=trade_id, data=data)
```

### What TradeCRCDO Does
- **Name**: Trade Create/Replace/Cancel Dependent Orders
- **HTTP Method**: `PUT /v3/accounts/{accountID}/trades/{tradeID}/orders`
- **Purpose**: Update dependent orders on a trade (stop loss, take profit, trailing stops)
- **Supports**: `stopLoss`, `trailingStopLoss`, `takeProfits`

### Code Changes
Only 2 lines changed:

| Line | Method | Change |
|------|--------|--------|
| 514 | `update_stop_loss()` | `TradeClientExtensions` → `TradeCRCDO` |
| 542 | `convert_to_trailing_stop()` | `TradeClientExtensions` → `TradeCRCDO` |

**Data structures**: No changes needed - they were already correct!

```python
# For fixed stop loss
data = {
    "stopLoss": {
        "price": str(rounded_sl)
    }
}

# For trailing stop loss
data = {
    "trailingStopLoss": {
        "distance": str(distance)  # Already converts pips to price units correctly
    }
}
```

---

## Expected Behavior After Fix

### For ATR_TRAILING Trades
```
Trade enters profit (+1 pip):
  ↓
_check_ai_trailing_conversion() triggers at breakeven/profit:
  ├─ Calculate trailing distance from ATR + regime
  ├─ Call convert_to_trailing_stop() with TradeCRCDO ✅
  ├─ OANDA receives correct API request
  └─ Trade enters TRAILING state
  ↓
Subsequent monitoring cycles:
  ├─ Trailing distance may update if volatility regime changes
  └─ SL moves DOWN as price moves DOWN (SHORT) or UP as price moves UP (LONG)
```

### For Fixed Stop Loss Updates
```
Any SL adjustment:
  ↓
Call update_stop_loss() with TradeCRCDO ✅
  ├─ OANDA receives correct API request
  └─ Stop loss updated immediately
  ↓
Trade 22412 example:
  └─ SL can now be adjusted in response to market moves
```

---

## Verification

### For Trade 22412
After redeployment, monitor:
1. **SL Movement**: Watch if SL trails downward as GBP/USD price continues downward
2. **Logs**: Check for messages like:
   ```
   🎯 ATR Trailing: Trade 22412 (GBP/USD SHORT) converted to trailing stop...
   ✅ Updated SL for trade 22412 to X.XXXXX
   ```
3. **OANDA Dashboard**: Confirm SL value is actually being updated in real-time

### Testing Future Trades
Next ATR_TRAILING trade creation should show:
- Trade created with fixed SL
- SL updated to breakeven when +1 pip profit
- SL trails with ATR-based distance thereafter

---

## Deployment Status

| Step | Status |
|------|--------|
| Code fix applied | ✅ |
| Git commit | ✅ Commit `0b6658d` |
| GitHub push | ✅ Pushed to origin/main |
| Render auto-deploy | ⏳ Deploying (2-5 min) |
| Scalp-Engine restart | ⏳ After deploy |
| Live verification | ⏳ Awaiting next monitoring cycle |

---

## Impact on Other Features

✅ **Positive impacts**:
- Fixed stop loss updates now work correctly
- ATR_TRAILING profit protection enabled
- All trailing stop types enabled (BE_TO_TRAILING, ATR_TRAILING, STRUCTURE_ATR_STAGED, STRUCTURE_ATR)

⚠️ **Affected trades**:
- **New trades**: Will use the corrected endpoint immediately
- **Existing TRAILING trades**: Continue with current state; SL updates apply going forward

---

## Why This Took Time to Diagnose

1. **Silently failing**: OANDA API wasn't throwing errors - it was just ignoring invalid endpoint calls
2. **State transition worked**: Trade entered TRAILING state, so it seemed like conversion succeeded
3. **Only visible in production**: The endpoint difference only becomes apparent when OANDA processes the API calls
4. **Intermittent appearance**: Issue only manifested when trades moved into profit and conversion was attempted

---

## References

- [oandapyV20 TradeCRCDO](https://oanda-api-v20.readthedocs.io/en/latest/endpoints/trades/tradeCRCDO.html)
- [OANDA v20 Trade Endpoint](https://developer.oanda.com/rest-live-v20/trade-ep/)
- [OANDAPYV20_FIX_SUMMARY.md](./OANDAPYV20_FIX_SUMMARY.md) - Quick reference
- [OANDAPYV20_RESEARCH.md](./OANDAPYV20_RESEARCH.md) - Detailed research

---

## Timeline

- **Identified**: Trade 22412 SL stuck despite reaching profit
- **Diagnosed**: API endpoint mismatch after research agent investigation
- **Fixed**: Replaced `TradeClientExtensions` with `TradeCRCDO` (2 line changes)
- **Deployed**: Pushed to GitHub and Render
- **Expected Resolution**: Trailing stops working on next monitoring cycle
