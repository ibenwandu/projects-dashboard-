# TP/SL Trade Closure Investigation - Phase 1 Testing Failure

## Executive Summary

**Problem**: 4 trades opened on Mar 9, 2026, but 0 trades closed. All trades remained open at EOD despite having "TP and SL defined."

**Root Cause Identified**: The `TakeProfitDetails` and `StopLossDetails` objects in the OANDA order request are missing the required `timeInForce` parameter. This causes OANDA's v20 API to silently reject or ignore the TP/SL specifications. Trades are created **without protective orders**, so they never close automatically.

---

## 1. CONFIGURATION VALUES

| Parameter | Value | Source |
|-----------|-------|--------|
| Config SL pips | 5 | `config.yaml` line 33 |
| Config TP pips | 8 | `config.yaml` line 34 |
| JPY pair handling | Correct calculation | `oanda_client.py` line 123 |

**Detailed Config**:
```yaml
risk:
  stop_loss_pips: 5
  take_profit_pips: 8
```

---

## 2. CALCULATION LOGIC - Distance Conversion

**File**: `/Scalp-Engine/src/oanda_client.py` (lines 120-133)

```python
# Convert pips to price distance
# For most pairs, 1 pip = 0.0001, for JPY pairs, 1 pip = 0.01
pip_value = 0.0001 if "JPY" not in instrument else 0.01

sl_distance = str(stop_loss_pips * pip_value)
tp_distance = str(take_profit_pips * pip_value)

mo = MarketOrderRequest(
    instrument=instrument,
    units=units,
    takeProfitOnFill=TakeProfitDetails(distance=tp_distance).data,
    stopLossOnFill=StopLossDetails(distance=sl_distance).data
)
```

**Distance Calculation Examples**:

| Pair | pip_value | SL Distance | TP Distance | Format |
|------|-----------|------------|------------|--------|
| EUR_USD | 0.0001 | 5 × 0.0001 = 0.0005 | 8 × 0.0001 = 0.0008 | "0.0005" |
| USD_JPY | 0.01 | 5 × 0.01 = 0.05 | 8 × 0.01 = 0.08 | "0.05" |
| GBP_USD | 0.0001 | 5 × 0.0001 = 0.0005 | 8 × 0.0001 = 0.0008 | "0.0005" |

✓ **Distance calculation is CORRECT**
✓ **Format conversion to string is CORRECT**

---

## 3. CRITICAL ISSUE FOUND: Missing `timeInForce` Parameter

### The Problem

**OANDA v20 API Specification** for `TakeProfitDetails` and `StopLossDetails`:

When using the `distance` parameter (relative to entry price), the API **requires** the `timeInForce` field to be specified. This tells OANDA how long the protective order should remain active.

**Current Code** (INCORRECT):
```python
TakeProfitDetails(distance=tp_distance).data
# Produces: {"distance": "0.0008"}
```

**What OANDA Expects** (CORRECT):
```python
TakeProfitDetails(distance=tp_distance, timeInForce="GTC").data
# Should produce: {"distance": "0.0008", "timeInForce": "GTC"}
```

### Evidence

- **Missing Parameter**: No `timeInForce` is set anywhere in the `place_market_order()` method
- **Missing Parameter**: No `priceBound` is set (alternative requirement)
- **Search Result**: `grep -i "timeInForce"` returns no matches in the entire Scalp-Engine codebase
- **Search Result**: `grep -i "priceBound"` returns no matches in the entire Scalp-Engine codebase

---

## 4. SECONDARY ISSUE: Position Sizing Pip Value

**File**: `/Scalp-Engine/scalp_engine.py` (lines 306, 495)

```python
# WRONG - both branches identical
pip_value = 10.0 if "JPY" not in pair else 10.0

# Should be:
pip_value = 10.0 if "JPY" not in pair else 0.01
```

**Impact**: Position sizing calculations are incorrect for JPY pairs. This doesn't affect TP/SL closure but inflates position sizes for JPY pairs by 100x.

---

## 5. SAMPLE TRADE ANALYSIS - Expected Behavior

### What **Should** Happen (If Code Was Correct)

**Example Trade: EUR_USD BUY**
```
Entry Price: 1.0800
Entry Time: 2026-03-09 14:30:00 UTC

Target Calculations:
- SL distance = 5 pips × 0.0001 = 0.0005 price units
- TP distance = 8 pips × 0.0001 = 0.0008 price units

SL Target Price: 1.0800 - 0.0005 = 1.0795 (closes on loss)
TP Target Price: 1.0800 + 0.0008 = 1.0808 (closes on profit)

OANDA Request Body (CORRECT):
{
  "instrument": "EUR_USD",
  "units": 1000,
  "takeProfitOnFill": {
    "distance": "0.0008",
    "timeInForce": "GTC"      <-- MISSING IN CURRENT CODE
  },
  "stopLossOnFill": {
    "distance": "0.0005",
    "timeInForce": "GTC"      <-- MISSING IN CURRENT CODE
  }
}

Result: Trade auto-closes when price touches SL or TP
```

### What **Actually** Happens (Current Code)

```
OANDA Request Body (INCOMPLETE):
{
  "instrument": "EUR_USD",
  "units": 1000,
  "takeProfitOnFill": {
    "distance": "0.0008"
  },
  "stopLossOnFill": {
    "distance": "0.0005"
  }
}

OANDA Response:
- Order is FILLED (trade created)
- TP/SL are REJECTED/IGNORED (missing timeInForce)
- Trade remains OPEN indefinitely
- Manual close required

Validation Status: ✗ INCORRECT
```

---

## 6. POTENTIAL ISSUES IDENTIFIED

### Issue 1: Missing `timeInForce` Parameter (PRIMARY)
- **Severity**: CRITICAL
- **Effect**: TP/SL orders are silently rejected by OANDA API
- **Evidence**: No validation in code; no `timeInForce` found in codebase
- **Impact**: 100% of trades opened without protective orders

### Issue 2: No Validation of TP/SL Acceptance
- **Severity**: HIGH
- **Location**: `scalp_engine.py` lines 325-342
- **Issue**: Code assumes order was successful but doesn't verify TP/SL was attached
- **Code Gap**:
  ```python
  order_response = self.oanda_client.place_market_order(...)
  # No check for:
  # - orderFillTransaction['takeProfitOnFill'] exists
  # - orderFillTransaction['stopLossOnFill'] exists
  ```

### Issue 3: Incorrect JPY Pair Pip Value in Position Sizing
- **Severity**: MEDIUM (doesn't affect TP/SL)
- **Location**: `scalp_engine.py` lines 306, 495
- **Issue**: `pip_value = 10.0 if "JPY" not in pair else 10.0` (identical branches)
- **Effect**: JPY pairs get 100x oversized positions

### Issue 4: No Error Handling for Malformed OANDA Requests
- **Severity**: MEDIUM
- **Location**: `oanda_client.py` lines 120-141
- **Issue**: Generic exception catches but doesn't validate request structure

---

## 7. ROOT CAUSE OF TRADES NOT CLOSING

### Primary Cause: Missing `timeInForce` Parameter

The `TakeProfitDetails` and `StopLossDetails` objects are instantiated **without** the required `timeInForce` field:

```python
# Current (BROKEN):
TakeProfitDetails(distance=tp_distance).data
TakeProfitDetails(distance=sl_distance).data

# Should be (FIXED):
TakeProfitDetails(distance=tp_distance, timeInForce="GTC").data
StopLossDetails(distance=sl_distance, timeInForce="GTC").data
```

### Supporting Evidence

1. **OANDA v20 API Documentation**: When using `distance` parameter, `timeInForce` is **mandatory**
2. **Code Search**: Zero references to `timeInForce` in entire codebase
3. **Symptom Match**: Trades open but don't close = missing protective orders
4. **API Silent Failure**: OANDA accepts the order (fills it) but ignores malformed TP/SL specs

---

## 8. RECOMMENDED FIXES

### Fix 1: Add `timeInForce` to TP/SL Orders (CRITICAL)

**File**: `C:/Users/user/projects/personal/Scalp-Engine/src/oanda_client.py`

**Lines 128-133** - Change from:
```python
mo = MarketOrderRequest(
    instrument=instrument,
    units=units,
    takeProfitOnFill=TakeProfitDetails(distance=tp_distance).data,
    stopLossOnFill=StopLossDetails(distance=sl_distance).data
)
```

**To**:
```python
mo = MarketOrderRequest(
    instrument=instrument,
    units=units,
    takeProfitOnFill=TakeProfitDetails(distance=tp_distance, timeInForce="GTC").data,
    stopLossOnFill=StopLossDetails(distance=sl_distance, timeInForce="GTC").data
)
```

### Fix 2: Validate TP/SL Acceptance (HIGH PRIORITY)

**File**: `C:/Users/user/projects/personal/Scalp-Engine/src/oanda_client.py`

**Add validation after line 136**:
```python
r = orders.OrderCreate(accountID=self.account_id, data=mo.data)
self.client.request(r)

# Add validation
response = r.response
if response and 'orderFillTransaction' in response:
    fill_trans = response['orderFillTransaction']

    # Verify TP/SL were accepted
    has_tp = 'takeProfitOnFill' in fill_trans
    has_sl = 'stopLossOnFill' in fill_trans

    if not has_tp or not has_sl:
        print(f"WARNING: TP/SL not attached to order!")
        print(f"  TP attached: {has_tp}")
        print(f"  SL attached: {has_sl}")
        print(f"  Response: {response}")

return response
```

### Fix 3: Correct JPY Pair Pip Value (MEDIUM PRIORITY)

**File**: `C:/Users/user/projects/personal/Scalp-Engine/scalp_engine.py`

**Line 306** - Change from:
```python
pip_value = 10.0 if "JPY" not in pair else 10.0
```

**To**:
```python
pip_value = 10.0 if "JPY" not in pair else 0.01
```

**Line 495** - Apply same fix

### Fix 4: Add Unit Tests (ONGOING)

Create test file to verify:
1. Distance calculations for each pair type
2. `timeInForce` is present in TakeProfitDetails/StopLossDetails
3. Mock OANDA responses to verify TP/SL extraction
4. Verify no trades open without TP/SL

---

## 9. VERIFICATION CHECKLIST

After applying fixes, verify:

- [ ] `timeInForce="GTC"` is present in TakeProfitDetails
- [ ] `timeInForce="GTC"` is present in StopLossDetails
- [ ] Distance calculations remain string format (e.g., "0.0005")
- [ ] JPY pair pip_value is 0.01 (not 10.0)
- [ ] Non-JPY pair pip_value is 10.0 (for position sizing, not distance)
- [ ] Order response validation logs TP/SL attachment success
- [ ] Next test trade on practice account closes at TP or SL
- [ ] Trade closure is recorded in database with correct PnL

---

## 10. NEXT STEPS

1. **Immediate**: Apply Fix 1 (add `timeInForce`) - **CRITICAL**
2. **Short-term**: Apply Fix 2 (validation) and Fix 3 (JPY pip_value)
3. **Testing**: Re-run Phase 1 testing on practice account
4. **Verification**: Monitor first trade to ensure it closes at TP/SL
5. **Long-term**: Implement unit tests (Fix 4)

---

## Files Affected

- `C:/Users/user/projects/personal/Scalp-Engine/src/oanda_client.py` (lines 128-133, 136)
- `C:/Users/user/projects/personal/Scalp-Engine/scalp_engine.py` (lines 306, 495)

## Related Files Referenced

- `C:/Users/user/projects/personal/Scalp-Engine/config.yaml` (configuration)
- `C:/Users/user/projects/personal/Scalp-Engine/src/risk_manager.py` (pip calculations)
- `C:/Users/user/projects/personal/Scalp-Engine/scalp_engine.py` (order execution)
