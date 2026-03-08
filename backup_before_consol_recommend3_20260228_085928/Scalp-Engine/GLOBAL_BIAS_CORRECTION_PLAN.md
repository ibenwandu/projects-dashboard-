# Global Bias Correction Plan

## Problem Summary

The current global bias calculation does not properly handle situations where USD is the base currency versus the quote currency, leading to misleading bias signals and incorrect trade closures.

### Current Issue

**Current Implementation:**
- Simply counts all LONG opportunities vs SHORT opportunities
- Does not consider which currency is being bought/sold
- Treats EUR/USD LONG and USD/JPY LONG the same (both count as "LONG")

**The Problem:**
- **EUR/USD LONG** = Buying EUR, Selling USD = **Bearish USD**
- **USD/JPY LONG** = Buying USD, Selling JPY = **Bullish USD**
- Both count as "LONG" but have opposite USD implications

**Result:**
- Global bias can be "BULLISH" when net USD exposure is actually bearish
- Trades get closed incorrectly based on misleading bias
- System doesn't reflect true market sentiment toward USD

---

## Correction Strategy

### Option 1: USD-Normalized Bias (Recommended)

Convert all opportunities to USD exposure before calculating bias.

**Logic:**
1. For each opportunity, determine USD exposure:
   - If USD is quote currency (EUR/USD, GBP/USD): LONG = bearish USD, SHORT = bullish USD
   - If USD is base currency (USD/JPY, USD/CAD): LONG = bullish USD, SHORT = bearish USD
   - If no USD in pair (EUR/GBP): Skip or handle separately

2. Count USD bullish vs bearish signals:
   - `usd_bullish_count` = opportunities that are bullish on USD
   - `usd_bearish_count` = opportunities that are bearish on USD

3. Calculate bias:
   - If `usd_bullish_count > usd_bearish_count`: `global_bias = "BULLISH"`
   - If `usd_bearish_count > usd_bullish_count`: `global_bias = "BEARISH"`
   - If equal: `global_bias = "NEUTRAL"`

**Advantages:**
- True USD bias representation
- Consistent interpretation across all pairs
- More accurate trade closure decisions

**Disadvantages:**
- Only works for USD-based pairs
- Non-USD pairs (EUR/GBP) need separate handling

### Option 2: Pair-Specific Bias

Calculate bias per currency pair, then aggregate.

**Logic:**
1. Group opportunities by pair
2. For each pair, determine bias (LONG vs SHORT count)
3. Aggregate pair biases to global bias

**Advantages:**
- Handles non-USD pairs
- More granular bias information

**Disadvantages:**
- More complex
- Doesn't solve the USD base/quote issue
- Still doesn't represent true USD sentiment

### Option 3: Dual Bias System

Calculate both USD bias and general market bias.

**Logic:**
1. Calculate USD-normalized bias (Option 1)
2. Calculate general LONG/SHORT bias (current method)
3. Use both for trade decisions

**Advantages:**
- Provides more context
- Backward compatible
- More nuanced decision making

**Disadvantages:**
- More complex logic
- Need to define priority/conflict resolution

---

## Recommended Implementation Plan

### Phase 1: USD-Normalized Bias Calculation

**File:** `src/market_bridge.py`  
**Function:** `export_market_state()`  
**Lines:** 74-84

**Changes:**

1. **Add USD Exposure Calculation Function:**
   ```python
   def _calculate_usd_exposure(self, pair: str, direction: str) -> Optional[str]:
       """
       Calculate USD exposure for a trade opportunity
       
       Returns:
       - "BULLISH" if trade is bullish on USD
       - "BEARISH" if trade is bearish on USD
       - None if USD not in pair
       """
       # Parse pair to get base and quote
       # Check if USD is base or quote
       # Return appropriate USD exposure
   ```

2. **Replace Simple Count Logic:**
   ```python
   # OLD: Simple count
   long_count = sum(1 for op in opportunities if op.get('direction', '').upper() in ['BUY', 'LONG'])
   short_count = sum(1 for op in opportunities if op.get('direction', '').upper() in ['SELL', 'SHORT'])
   
   # NEW: USD-normalized count
   usd_bullish_count = 0
   usd_bearish_count = 0
   non_usd_count = 0
   
   for op in opportunities:
       pair = op.get('pair', '')
       direction = op.get('direction', '').upper()
       usd_exposure = self._calculate_usd_exposure(pair, direction)
       
       if usd_exposure == "BULLISH":
           usd_bullish_count += 1
       elif usd_exposure == "BEARISH":
           usd_bearish_count += 1
       else:
           non_usd_count += 1  # Track non-USD pairs
   
   # Calculate bias based on USD exposure
   if usd_bullish_count > usd_bearish_count:
       global_bias = "BULLISH"
   elif usd_bearish_count > usd_bullish_count:
       global_bias = "BEARISH"
   else:
       global_bias = "NEUTRAL"
   ```

3. **Update Market State Dictionary:**
   - Add `usd_bullish_count` and `usd_bearish_count` to state
   - Add `non_usd_pairs_count` for transparency
   - Keep `long_count` and `short_count` for backward compatibility (deprecated)

### Phase 2: Update Trade Closure Logic

**File:** `auto_trader_core.py`  
**Function:** `_check_intelligence_validity()`  
**Lines:** 2672-2690

**Changes:**

1. **Update Bias Interpretation:**
   - Current: BULLISH = more LONG trades, BEARISH = more SHORT trades
   - New: BULLISH = bullish on USD, BEARISH = bearish on USD

2. **Update Trade Closure Logic:**
   ```python
   # For EUR/USD LONG trade:
   # - Trade is LONG EUR/USD = bearish USD
   # - If bias is BEARISH (bearish USD), trade aligns with bias
   # - Should NOT close the trade
   
   # For USD/JPY LONG trade:
   # - Trade is LONG USD/JPY = bullish USD
   # - If bias is BEARISH (bearish USD), trade conflicts with bias
   # - SHOULD close the trade
   ```

3. **Add USD Exposure Check:**
   ```python
   def _get_trade_usd_exposure(self, trade: ManagedTrade) -> Optional[str]:
       """Get USD exposure for a trade (BULLISH, BEARISH, or None)"""
       # Check if USD is in pair
       # Determine if trade is bullish or bearish on USD
       # Return exposure
   ```

4. **Update Closure Conditions:**
   ```python
   # Get USD exposure for this trade
   trade_usd_exposure = self._get_trade_usd_exposure(trade)
   current_bias = market_state.get('global_bias', 'NEUTRAL')
   
   # Only check conflicts if trade has USD exposure
   if trade_usd_exposure:
       if trade_usd_exposure == "BULLISH" and current_bias == "BEARISH":
           # Trade is bullish USD but bias is bearish USD - close
           self.close_trade(...)
       elif trade_usd_exposure == "BEARISH" and current_bias == "BULLISH":
           # Trade is bearish USD but bias is bullish USD - close
           self.close_trade(...)
   ```

### Phase 3: Handle Non-USD Pairs

**Consideration:**
- What happens with pairs like EUR/GBP, AUD/NZD?
- Options:
  1. Skip them in bias calculation (only USD pairs count)
  2. Calculate separate bias for each currency
  3. Use general LONG/SHORT count for non-USD pairs

**Recommended:** Option 1 (Skip non-USD pairs)
- Simplest and most accurate
- Global bias represents USD sentiment
- Non-USD pairs can use pair-specific validation

### Phase 4: Backward Compatibility

**Considerations:**
1. Existing trades may have been opened with old bias logic
2. State files may have old bias format
3. UI may display old bias values

**Solution:**
- Keep old fields in market state for compatibility
- Add new fields alongside old ones
- Gradually migrate to new fields
- Add migration logic if needed

---

## Implementation Details

### USD Exposure Calculation Function

```python
def _calculate_usd_exposure(self, pair: str, direction: str) -> Optional[str]:
    """
    Calculate whether a trade opportunity is bullish or bearish on USD
    
    Args:
        pair: Currency pair (e.g., "EUR/USD", "USD/JPY")
        direction: Trade direction ("LONG", "SHORT", "BUY", "SELL")
    
    Returns:
        "BULLISH" if trade is bullish on USD
        "BEARISH" if trade is bearish on USD
        None if USD not in pair
    """
    # Normalize pair format
    pair = pair.replace('/', '').replace('-', '').upper()
    
    # Check if USD is in pair
    if 'USD' not in pair:
        return None  # Non-USD pair
    
    # Determine if USD is base or quote
    if pair.startswith('USD'):
        # USD is base currency (e.g., USDJPY, USDCAD)
        # LONG = buying USD = bullish USD
        # SHORT = selling USD = bearish USD
        if direction in ['LONG', 'BUY']:
            return "BULLISH"
        elif direction in ['SHORT', 'SELL']:
            return "BEARISH"
    else:
        # USD is quote currency (e.g., EURUSD, GBPUSD)
        # LONG = buying base, selling USD = bearish USD
        # SHORT = selling base, buying USD = bullish USD
        if direction in ['LONG', 'BUY']:
            return "BEARISH"
        elif direction in ['SHORT', 'SELL']:
            return "BULLISH"
    
    return None
```

### Trade USD Exposure Function

```python
def _get_trade_usd_exposure(self, trade: ManagedTrade) -> Optional[str]:
    """
    Get USD exposure for an open trade
    
    Returns:
        "BULLISH" if trade is bullish on USD
        "BEARISH" if trade is bearish on USD
        None if USD not in pair
    """
    pair = trade.pair.replace('/', '').replace('-', '').upper()
    direction = trade.direction.upper()
    
    if 'USD' not in pair:
        return None
    
    if pair.startswith('USD'):
        # USD is base
        return "BULLISH" if direction in ['LONG', 'BUY'] else "BEARISH"
    else:
        # USD is quote
        return "BEARISH" if direction in ['LONG', 'BUY'] else "BULLISH"
```

---

## Testing Plan

### Test Cases

1. **USD Quote Currency (EUR/USD, GBP/USD):**
   - EUR/USD LONG → Should be BEARISH USD
   - EUR/USD SHORT → Should be BULLISH USD
   - Verify bias calculation
   - Verify trade closure logic

2. **USD Base Currency (USD/JPY, USD/CAD):**
   - USD/JPY LONG → Should be BULLISH USD
   - USD/JPY SHORT → Should be BEARISH USD
   - Verify bias calculation
   - Verify trade closure logic

3. **Mixed Scenarios:**
   - 2 EUR/USD LONG + 1 USD/JPY LONG → Net: 1 BEARISH, 1 BULLISH → NEUTRAL
   - 3 EUR/USD LONG + 1 USD/JPY LONG → Net: 3 BEARISH, 1 BULLISH → BEARISH
   - 1 EUR/USD LONG + 2 USD/JPY LONG → Net: 1 BEARISH, 2 BULLISH → BULLISH

4. **Non-USD Pairs:**
   - EUR/GBP LONG → Should not affect USD bias
   - Verify it's excluded from calculation

5. **Trade Closure:**
   - EUR/USD LONG with BEARISH bias → Should NOT close (aligned)
   - EUR/USD LONG with BULLISH bias → Should close (conflicts)
   - USD/JPY LONG with BULLISH bias → Should NOT close (aligned)
   - USD/JPY LONG with BEARISH bias → Should close (conflicts)

### Validation Steps

1. **Unit Tests:**
   - Test `_calculate_usd_exposure()` with various pairs
   - Test `_get_trade_usd_exposure()` with various trades
   - Test bias calculation with mixed scenarios

2. **Integration Tests:**
   - Test full market state generation
   - Test trade closure with new bias logic
   - Verify state file format

3. **Manual Testing:**
   - Create test opportunities with known USD exposure
   - Verify bias calculation in logs
   - Verify trade closure behavior
   - Check UI displays correct bias

---

## Migration Strategy

### Step 1: Add New Fields (Non-Breaking)
- Add `usd_bullish_count`, `usd_bearish_count` to market state
- Keep existing `long_count`, `short_count` for compatibility
- Calculate both old and new bias

### Step 2: Update Trade Closure Logic
- Use new USD-normalized bias for trade closure
- Keep old logic as fallback if new fields missing

### Step 3: Update UI/Logging
- Display new bias calculation
- Show USD exposure breakdown
- Deprecate old bias display

### Step 4: Remove Old Logic (After Validation)
- Remove old `long_count`/`short_count` calculation
- Remove old bias calculation
- Clean up deprecated code

---

## Risk Assessment

### Low Risk Areas
- USD exposure calculation (straightforward logic)
- Market state generation (additive changes)
- Logging (new information only)

### Medium Risk Areas
- Trade closure logic (changes behavior)
- State file format (backward compatibility needed)
- UI display (may need updates)

### High Risk Areas
- Existing trades may be affected
- Bias interpretation changes fundamentally
- Need careful testing with real market data

### Mitigation
1. **Gradual Rollout:**
   - Deploy with both old and new bias
   - Monitor for issues
   - Switch to new bias after validation

2. **Feature Flag:**
   - Add config option to enable/disable new bias
   - Allow rollback if issues found

3. **Comprehensive Testing:**
   - Test with historical data
   - Test with current market conditions
   - Verify trade closure decisions

---

## Rollback Plan

If issues occur:
1. **Immediate:** Disable new bias calculation via feature flag
2. **Revert:** Restore old bias calculation code
3. **Data:** Old market state format still supported
4. **No Data Loss:** Only affects in-memory calculations

---

## Success Criteria

After implementation, verify:
- [ ] USD bias correctly reflects USD exposure
- [ ] EUR/USD LONG with BEARISH bias does NOT close (aligned)
- [ ] USD/JPY LONG with BEARISH bias DOES close (conflicts)
- [ ] Mixed scenarios calculate correctly
- [ ] Non-USD pairs excluded from bias
- [ ] Backward compatibility maintained
- [ ] Logs show correct USD exposure
- [ ] UI displays accurate bias

---

## Summary

**Problem:** Global bias doesn't account for USD base vs quote currency differences.

**Solution:** Calculate USD-normalized bias by converting all opportunities to USD exposure before counting.

**Impact:** More accurate bias representation, correct trade closure decisions, better risk management.

**Timeline:** 
- Phase 1: USD-normalized calculation (1-2 days)
- Phase 2: Trade closure logic update (1 day)
- Phase 3: Testing and validation (2-3 days)
- Phase 4: Migration and cleanup (1 day)

**Total Estimated Time:** 5-7 days
