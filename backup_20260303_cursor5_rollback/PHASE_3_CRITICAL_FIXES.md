# Phase 3: Critical Fixes - Blocks Live Trading

**Status**: IN PLANNING
**Estimated Effort**: 6-8 hours of implementation + testing
**Priority**: CRITICAL - Must complete before ANY live trading

---

## Overview

This phase implements the four critical fixes required before live trading:

1. **100% Stop Loss Coverage** - Enforce on ALL trades
2. **Take Profit Targets** - Close at TP levels
3. **Circuit Breaker Logic** - Prevent revenge trading
4. **Risk-Based Position Sizing** - Control exposure

---

## Analysis: What Exists vs What's Needed

### 1. Stop Loss Coverage

**Current Status**: ✅ PARTIALLY IMPLEMENTED

**What exists**:
- `_create_trade_from_opportunity()` (lines 1273-1392) has SL calculation logic
- Validates if stop_loss is None (line 1329)
- Calculates 1:1 risk/reward from take profit (lines 1332-1347)
- Falls back to default 20 pips if neither SL nor TP provided (lines 1349-1359)
- Rounds to OANDA precision (line 1362, 1365)

**What's missing**:
- ❓ No verification that SL is ACTUALLY SET on OANDA orders
- ❓ No enforcement that SL can NEVER be None after trade creation
- ❓ No validation that SL distance makes sense (e.g., not 0.0001 pips away)
- ❓ No monitoring that SL remains in place (could be accidentally removed)

**Impact on Demo Account**:
- 419 trades with 0% SL coverage suggests:
  - Either SL calculation is failing silently
  - Or SL is set but then removed by mistake
  - Or order placement is bypassing SL requirements

**Fix Required**:
- Add ASSERT that SL is never None before placing order
- Add logging to track SL at each stage (creation, order placement, confirmation)
- Add validation that SL distance > 0

**Files to Modify**:
- `Scalp-Engine/auto_trader_core.py` lines 1273-1392 (add assertions)
- `Scalp-Engine/auto_trader_core.py` line 304 (add SL verification before OANDA call)

---

### 2. Take Profit Targets

**Current Status**: ⚠️ PARTIALLY IMPLEMENTED

**What exists**:
- `_create_trade_from_opportunity()` gets take profit (line 1326)
- Stores in ManagedTrade (line 1380)
- Rounding to OANDA precision (line 1372)

**What's missing**:
- ❓ No code that CLOSES trade when TP is hit
- ❓ No monitoring of TP levels during trade lifecycle
- ❓ No two-tier TP (TP1 partial close, TP2 full close)
- ❓ No automation that executes TP closes

**Impact on Demo Account**:
- 0% TP coverage suggests no closing at TP levels
- Trades that hit TP may not be automatically closed
- Relies on manual closing or SL to exit

**Fix Required**:
- Add TP monitoring in `monitor_positions()` method
- When current price crosses TP level:
  - For LONG: if current_price >= take_profit, close trade
  - For SHORT: if current_price <= take_profit, close trade
- Add separate TP1/TP2 support (optional for Phase 3, but would be useful)

**Files to Modify**:
- `Scalp-Engine/auto_trader_core.py` (add to `monitor_positions()` method around line 1394)

---

### 3. Circuit Breaker Logic

**Current Status**: ❌ NOT IMPLEMENTED

**What's missing**:
- No counter for consecutive losses
- No logic to stop trading after N consecutive losses
- No reset mechanism when win occurs
- No per-pair loss tracking

**Impact on Demo Account**:
- 102 consecutive losses in 10.3 hours (Jan 27)
- 53 consecutive losses over 5 days (Feb 10-16)
- Without circuit breaker, account can be wiped quickly

**What needs to be implemented**:

```python
Circuit Breaker Rules:
  1. Stop ALL new trades after 5 consecutive losses
  2. Stop same pair after 3 consecutive losses (blacklist for 1 hour)
  3. Reset counters on first win
  4. Log all breaker triggers
```

**Implementation Steps**:

1. Add counters to PositionManager:
```python
class PositionManager:
    def __init__(...):
        self.consecutive_losses = 0  # All trades
        self.consecutive_losses_by_pair = {}  # Per pair
        self.circuit_breaker_triggered_at = None
        self.blacklisted_pairs = {}  # pair -> expires_at
```

2. Update `record_trade_close()` (line 3448):
```python
def record_trade_close(self, realized_pnl: float, pair: str = None):
    if realized_pnl < 0:
        # Loss
        self.consecutive_losses += 1
        if pair:
            self.consecutive_losses_by_pair[pair] = \
                self.consecutive_losses_by_pair.get(pair, 0) + 1

            # Blacklist pair after 3 consecutive losses
            if self.consecutive_losses_by_pair[pair] >= 3:
                self.blacklisted_pairs[pair] = datetime.utcnow() + timedelta(hours=1)
                self.logger.warning(f"🚫 {pair} blacklisted for 1 hour (3 losses)")
    else:
        # Win - reset counters
        self.consecutive_losses = 0
        self.consecutive_losses_by_pair = {}
```

3. Add circuit breaker check before opening trades:
```python
def can_open_new_trade(self) -> Tuple[bool, str]:
    # Existing checks...

    # Check circuit breaker
    if self.consecutive_losses >= 5:
        return False, f"Circuit breaker: {self.consecutive_losses} consecutive losses"

    # Check per-pair blacklist
    if pair in self.blacklisted_pairs:
        if datetime.utcnow() < self.blacklisted_pairs[pair]:
            return False, f"{pair} blacklisted due to losses"
        else:
            del self.blacklisted_pairs[pair]

    return True, "OK"
```

**Files to Modify**:
- `Scalp-Engine/auto_trader_core.py` - PositionManager class
- Add state tracking for consecutive losses
- Integrate with `can_open_new_trade()` method (line 792)
- Integrate with `record_trade_close()` method (line 3448)

---

### 4. Risk-Based Position Sizing

**Current Status**: ⚠️ PARTIALLY IMPLEMENTED

**What exists**:
- `base_position_size` in TradeConfig (line 146): default 1000 units
- `consensus_multiplier` support (line 1286): size multiplier by consensus
- Dynamic sizing based on confidence/consensus (lines 1285-1287)

**What's missing**:
- ❓ No 2% risk rule enforcement (max 2% of account per trade)
- ❓ No dynamic adjustment for volatility (ATR-based sizing)
- ❓ No maximum position size limit
- ❓ No account balance tracking for 2% calculation

**Impact on Demo Account**:
- Average 3,185 units per trade on $100 CAD account
- With typical pip movement (-$1 to +$2 per trade)
- Uncontrolled risk exposure

**Fix Required** (Phase 3 - Basic):
- Store account balance in PositionManager
- Calculate max units: balance * 0.02 / (SL_distance_in_pips * pip_value)
- Cap actual units to never exceed max
- Log position size at each trade

**Fix Required** (Phase 4+ - Advanced):
- ATR-based position sizing (larger in low volatility, smaller in high volatility)
- Account for multiple open trades
- Reduce size during drawdowns

**Files to Modify**:
- `Scalp-Engine/auto_trader_core.py` - TradeConfig and PositionManager
- Store account balance (from OANDA API)
- Add position size calculation with 2% cap

---

## Implementation Order

### Step 1: Add Logging & Assertions (2 hours)
- **File**: `Scalp-Engine/auto_trader_core.py`
- **Goal**: Verify SL is being set and not being removed
- **Tasks**:
  - Add ASSERT that SL is never None in `_create_trade_from_opportunity()`
  - Add ASSERT that SL distance > 0
  - Add INFO logging when SL is calculated vs provided
  - Add INFO logging when order is placed (include SL value)
  - Add INFO logging when order is filled (verify SL is set on OANDA)

### Step 2: Implement Take Profit Monitoring (2 hours)
- **File**: `Scalp-Engine/auto_trader_core.py`
- **Goal**: Close trades at TP level
- **Location**: `monitor_positions()` method (line 1394)
- **Tasks**:
  - After checking BE transition and SL triggers
  - Add TP check:
    - LONG: `if current_price >= take_profit: close_trade()`
    - SHORT: `if current_price <= take_profit: close_trade()`
  - Log TP hits with pnl
  - Track TP closures in trade statistics

### Step 3: Implement Circuit Breaker (2 hours)
- **File**: `Scalp-Engine/auto_trader_core.py`
- **Goal**: Stop trading after 5 consecutive losses
- **Tasks**:
  - Add state to PositionManager (consecutive losses counter)
  - Update `record_trade_close()` to track losses
  - Update `can_open_new_trade()` to check circuit breaker
  - Log breaker triggers and resets
  - Optional: UI display of breaker status

### Step 4: Implement Position Sizing (1-2 hours)
- **File**: `Scalp-Engine/auto_trader_core.py`
- **Goal**: Enforce 2% risk per trade
- **Tasks**:
  - Get account balance from OANDA API
  - Calculate max units for each trade
  - Cap actual units: `units = min(calculated_units, max_units)`
  - Log position sizing at each trade

---

## Testing Strategy

### Unit Testing
```python
# Test SL is never None
def test_create_trade_has_stop_loss():
    trade = create_trade_from_opportunity(opp_without_sl)
    assert trade.stop_loss is not None
    assert trade.stop_loss != 0

# Test TP is closed
def test_tp_closes_trade():
    trade = create_long_trade(entry=1.0850, tp=1.0900, sl=1.0800)
    current_price = 1.0901  # Above TP
    assert should_close_trade_at_tp(trade, current_price)

# Test circuit breaker
def test_circuit_breaker_stops_after_5_losses():
    pm = PositionManager()
    for i in range(5):
        pm.record_trade_close(-10)  # Loss
    can_open, reason = pm.can_open_new_trade()
    assert not can_open
    assert "circuit breaker" in reason.lower()
```

### Integration Testing
1. **100% SL Coverage**:
   - Place 10 test trades, verify each has SL on OANDA
   - Cancel each trade, verify SL was in place

2. **TP Closes**:
   - Open long trade at 1.0850, set TP 1.0900
   - Simulate price movement to 1.0901
   - Verify trade auto-closes

3. **Circuit Breaker**:
   - Place 5 losing trades in a row
   - Verify 6th trade is blocked
   - Place 1 winning trade
   - Verify circuit resets

4. **Position Sizing**:
   - Set account to $100
   - Place trade with 10 pip SL
   - Verify units = 2% * $100 / (10 pips * value)

---

## Verification Checklist

Before proceeding to live trading:

```
STOP LOSS COVERAGE:
  [ ] 100% of trades have SL on OANDA (verify via OANDA API)
  [ ] SL distance makes sense (at least 1 pip, at most 100 pips)
  [ ] SL is NOT removed during trade lifecycle
  [ ] Logs show SL at creation, placement, and fill

TAKE PROFIT:
  [ ] Trades close when current price hits TP level
  [ ] TP closures are logged with pnl
  [ ] No trades remain open past TP level for >1 hour

CIRCUIT BREAKER:
  [ ] After 5 consecutive losses, new trades are blocked
  [ ] Breaker is reset after 1 winning trade
  [ ] Can manually reset if needed (for testing)
  [ ] Logs show all breaker triggers

POSITION SIZING:
  [ ] Each trade has units calculated as max 2% risk
  [ ] Position size scales with account balance
  [ ] Confidence/consensus still applies as multiplier (e.g., 1.0x, 1.25x)
  [ ] Logs show position size calculation

DEMO TESTING:
  [ ] Run for 10+ profitable days with new fixes
  [ ] No 102-loss streaks occur
  [ ] No catastrophic single-trade losses (>$10)
  [ ] Overall P&L improves vs baseline 15.5% WR
```

---

## Known Risks

1. **SL Implementation May Fail**: If OANDA doesn't accept the SL we set, trades will be unprotected
   - **Mitigation**: Verify SL immediately after order fill

2. **TP Closing Too Aggressive**: May close trades that would have gone further
   - **Mitigation**: Use TP1 (partial) and TP2 (full) in future phases

3. **Circuit Breaker May Be Too Strict**: 5 losses may be too low or too high
   - **Mitigation**: Make it configurable, track statistics

4. **Position Sizing Complexity**: Interaction with leverage, spreads, and commissions
   - **Mitigation**: Test thoroughly, use conservative defaults

---

## Files Summary

| File | Lines | Changes | Complexity |
|------|-------|---------|------------|
| `Scalp-Engine/auto_trader_core.py` | 3452 | SL assertion, TP monitoring, circuit breaker, position sizing | HIGH |

---

## Next Steps After Phase 3

- **Phase 4**: Strategy Improvements (market regime detection, direction bias fixes)
- **Phase 5**: Testing & Validation (backtest, demo test, live trading prep)
- **Phase 6**: Live Trading ($100 CAD account)

---

**Last Updated**: February 22, 2026
**Created by**: Claude Code
**Status**: Planning Complete, Ready for Implementation
