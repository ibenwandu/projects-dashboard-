# Architecture Review: Stop Loss Strategy for Auto Mode

## Current Architecture Understanding

### 1. Global Configuration (Auto Mode)
- **Single UI trigger**: "Auto" button enables AUTO mode
- **Global SL type**: `config.stop_loss_type` applies to all opportunities
- **Global execution mode**: `config.execution_mode` (MARKET, RECOMMENDED, HYBRID, etc.)

### 2. Execution Flow Priority

```
opportunity received
  ↓
Check if FT_DMI_EMA (special routing - line 91-110)
  ├─ YES: Wait for 15m trigger → Execute MARKET
  └─ NO: Check DMI_EMA (special routing)
         ├─ YES: Wait for 15m trigger → Execute MARKET
         └─ NO: Check Fisher (special routing)
                ├─ YES: Use Fisher-specific logic
                └─ NO: Check per-opportunity override
                       ├─ YES: Use per_opp_mode (semi-auto)
                       └─ NO: Use global config.execution_mode (Auto mode)
```

### 3. Stop Loss Type Priority (Line 1238-1249)

```python
# Line 1238: Start with global config
sl_type = self.config.stop_loss_type

# Line 1242-1247: Check for per-opportunity override
per_opp_sl = opp.get('execution_config', {}).get('sl_type') or opp.get('fisher_config', {}).get('sl_type')
if per_opp_sl:
    sl_type = per_opp_sl  # ← Override global with per-opportunity

# Line 1248-1249: Force STRUCTURE_ATR_STAGED for FT-DMI-EMA/DMI-EMA if no per_opp_sl
elif opportunity_source in ('FT_DMI_EMA', 'DMI_EMA'):
    sl_type = StopLossType.STRUCTURE_ATR_STAGED  # ← Force special for this source only!
```

### 4. Monitoring Routing (Line 1445-1458)

```python
elif trade.sl_type == StopLossType.STRUCTURE_ATR_STAGED:
    if getattr(trade, "opportunity_source", "") in ("FT_DMI_EMA", "DMI_EMA"):
        # Full staged logic (phases with partial close at +2R)
        self._check_structure_atr_staged(...)
    else:
        # Fallback to simple version (no partial close)
        self._check_structure_atr_simple(...)
```

---

## The Problem

### Current Behavior
1. **Global config sets SL type**: All opportunities use same SL by default
2. **FT-DMI-EMA gets special treatment**: Code forces STRUCTURE_ATR_STAGED on FT-DMI-EMA trades
3. **LLM trades fall back**: Even if STRUCTURE_ATR_STAGED is set, LLM trades use simple version (no partial close)
4. **Result**: LLM trades lack the critical Phase 2.2 partial profit protection

### Why This Matters
- **Auto mode**: Needs reliable, consistent profit protection for ALL opportunity types
- **FT-DMI-EMA in Manual/Semi-Auto**: Can use sophisticated STRUCTURE_ATR_STAGED with all phases
- **LLM in Auto mode**: Should have same profit protection, but currently doesn't

---

## Proposed Solution

### Goal
- **Auto mode**: Unified STRUCTURE_ATR that works for ALL opportunities (LLM + FT-DMI-EMA)
- **Manual/Semi-Auto**: FT-DMI-EMA keeps STRUCTURE_ATR_STAGED with full phases
- **Architecture**: Respect existing execution mode override system

### Design Principle
```
Per-opportunity override (execution_config.sl_type)
  ↓ overrides
Global config (config.stop_loss_type)
  ↓ overrides
Auto-inferred defaults (only FT-DMI-EMA in Manual/Semi-Auto)
```

### Implementation Strategy

#### Phase 1: Create New SL Mode - STRUCTURE_ATR_AUTO

**What it is**:
- Simplified version of STRUCTURE_ATR for Auto mode
- Works consistently for ALL opportunity types
- Provides: BE at +1R, partial close at +2R (NEW!), trail to EMA 26 at +3R

**Implementation**:
```python
class StopLossType(Enum):
    STRUCTURE_ATR_AUTO = "STRUCTURE_ATR_AUTO"  # NEW: For Auto mode - all opportunities
    STRUCTURE_ATR_STAGED = "STRUCTURE_ATR_STAGED"  # Keep existing - FT-DMI-EMA specific
```

#### Phase 2: Implement _check_structure_atr_auto() Method

**Pseudocode**:
```python
def _check_structure_atr_auto(self, trade_id, trade, current_price, oanda_client):
    """
    Staged profit protection for Auto mode - works with ALL opportunity types

    Phases:
    1. +1R: Move SL to breakeven
    2. +2R: Close 50% position, lock +1R profit (NEW for LLM!)
    3. +3R: Trail remaining 50% to 1H EMA 26

    No complex Phase 3 exits - just trail to EMA 26 (simpler than STAGED)
    """

    # Calculate R-multiple from entry and initial SL
    r_multiple = calculate_r_multiple(current_price, trade.entry_price, trade.initial_stop_loss)

    # Phase 1: At +1R, move SL to breakeven
    if r_multiple >= 1.0 and not trade.breakeven_applied:
        update_stop_loss(trade.entry_price)
        trade.breakeven_applied = True

    # Phase 2: At +2R, close 50% and lock +1R
    if r_multiple >= 2.0 and not trade.partial_profit_taken:
        close_trade_partial(trade_id, 50%)
        # Move SL to +1R level
        one_r_price = trade.entry_price + risk_distance
        update_stop_loss(one_r_price)
        trade.partial_profit_taken = True

    # Phase 3: At +3R, trail to 1H EMA 26
    if r_multiple >= 3.0 and not trade.trailing_active:
        ema26_1h = fetch_1h_ema_26()
        update_stop_loss(ema26_1h)
        trade.trailing_active = True
```

#### Phase 3: Update SL Type Selection Logic

**Current (lines 1248-1249)**:
```python
elif opportunity_source in ('FT_DMI_EMA', 'DMI_EMA'):
    sl_type = StopLossType.STRUCTURE_ATR_STAGED
```

**New Logic**:
```python
elif opportunity_source in ('FT_DMI_EMA', 'DMI_EMA'):
    # Check if in Manual/Semi-Auto or Auto mode
    if self.trading_mode == TradingMode.AUTO:
        # Auto mode: Use unified STRUCTURE_ATR_AUTO for all opportunities
        sl_type = StopLossType.STRUCTURE_ATR_AUTO
    else:
        # Manual/Semi-Auto: Keep sophisticated STRUCTURE_ATR_STAGED for FT-DMI-EMA
        sl_type = StopLossType.STRUCTURE_ATR_STAGED
```

**Result**:
- **Auto mode**: All opportunities (LLM + FT-DMI-EMA) use STRUCTURE_ATR_AUTO
- **Manual/Semi-Auto**: FT-DMI-EMA uses full STRUCTURE_ATR_STAGED with all Phase 3 exits

#### Phase 4: Update Monitoring Routing

**Current (lines 1445-1458)**:
```python
elif trade.sl_type == StopLossType.STRUCTURE_ATR_STAGED:
    if getattr(trade, "opportunity_source", "") in ("FT_DMI_EMA", "DMI_EMA"):
        self._check_structure_atr_staged(...)
    else:
        self._check_structure_atr_simple(...)  # ← Fallback for LLM
```

**New Routing**:
```python
elif trade.sl_type == StopLossType.STRUCTURE_ATR_AUTO:
    # New mode for Auto: unified handling for all opportunity types
    self._check_structure_atr_auto(...)

elif trade.sl_type == StopLossType.STRUCTURE_ATR_STAGED:
    # Sophisticated mode for Manual/Semi-Auto FT-DMI-EMA trades
    if getattr(trade, "opportunity_source", "") in ("FT_DMI_EMA", "DMI_EMA"):
        self._check_structure_atr_staged(...)
    else:
        # Non-FT-DMI-EMA shouldn't have STRUCTURE_ATR_STAGED in normal flow
        self._check_structure_atr_simple(...)  # ← Safety fallback
```

---

## Detailed Comparison

### Auto Mode Behavior (STRUCTURE_ATR_AUTO)

```
LLM Opportunity in AUTO mode:
├─ Entry: 1.35550, SL: 1.36250 (risk 700 pips, +1R = 700 pips profit)
├─ +1R reached (1.35400 profit):  SL → 1.35550 (breakeven)
├─ +2R reached (1.34850 profit):  Close 50%, lock 350 pips ✅ (NEW!)
├─ +3R reached (1.34400 profit):  Trail remaining 50% to 1H EMA 26 ✅
└─ Sudden reversal:               Already locked 350 pips, remaining protected by EMA

FT-DMI-EMA Opportunity in AUTO mode:
└─ Same behavior as above (unified across all opportunities)
```

### Manual/Semi-Auto Mode Behavior (STRUCTURE_ATR_STAGED)

```
FT-DMI-EMA Opportunity in MANUAL/SEMI-AUTO mode:
├─ Entry: 1.35550, SL: 1.36250
├─ +1R: SL → 1.35550
├─ +2R: Close 50%, lock +1R
├─ +3R: Trail to EMA 26
├─ Phase 3 Exits (sophisticated):
│  ├─ 4H DMI reverse crossover
│  ├─ ADX collapse (<15)
│  ├─ Spread spike (>3x normal)
│  ├─ EMA structure breakdown
│  └─ Time-based stop
└─ Full sophisticated protection
```

---

## Configuration Example

### Auto Mode (Global)
```python
# User sets in UI: "Auto Mode"
trading_mode = TradingMode.AUTO
execution_mode = ExecutionMode.RECOMMENDED  # Or MARKET, HYBRID, etc.
stop_loss_type = StopLossType.STRUCTURE_ATR_AUTO  # ← NEW unified mode
```

### Manual Mode (Global)
```python
trading_mode = TradingMode.MANUAL
stop_loss_type = StopLossType.STRUCTURE_ATR  # Or BE_TO_TRAILING, ATR_TRAILING
# Note: FT-DMI-EMA will override to STRUCTURE_ATR_STAGED if not per_opp_sl
```

### Per-Opportunity Override (Semi-Auto)
```python
# LLM opportunity in UI with custom SL
opp = {
    'source': 'text_parsing',
    'pair': 'EUR/USD',
    'execution_config': {
        'mode': 'HYBRID',  # Per-opp execution mode
        'sl_type': 'ATR_TRAILING'  # Per-opp SL type (overrides global)
    }
}
```

---

## Benefits of This Approach

### Maintains Separation of Concerns
- ✅ **Auto mode**: Simple, unified, consistent (STRUCTURE_ATR_AUTO)
- ✅ **Manual/Semi-Auto**: Sophisticated, strategy-specific (STRUCTURE_ATR_STAGED for FT-DMI-EMA)
- ✅ **Per-opportunity override**: Still works for custom configurations

### Solves User's Problem
- ✅ **LLM in Auto**: Now has Phase 2.2 partial close protection
- ✅ **Unified behavior**: All opportunities use same proven logic in Auto mode
- ✅ **Breathing room**: Still trails to EMA 26 after partial close

### Respects Existing Architecture
- ✅ **Execution enforcer**: No changes needed (already routes by source)
- ✅ **SL priority**: Maintains per_opp_sl > source-based > global config
- ✅ **Backward compatible**: Existing STRUCTURE_ATR_STAGED unchanged for Manual mode

### Simplicity in Auto Mode
- ✅ **Three clear phases** (BE, Partial, Trail)
- ✅ **No complex exits** (no 4H DMI, ADX, spread checks)
- ✅ **Works for all sources** (LLM, FT-DMI-EMA, Fisher, etc.)

---

## Implementation Checklist

### Step 1: Code Changes
- [ ] Add `STRUCTURE_ATR_AUTO` to `StopLossType` enum
- [ ] Implement `_check_structure_atr_auto()` method (copy from simple + add Phase 2.2)
- [ ] Update SL selection logic (check trading_mode, choose AUTO vs STAGED)
- [ ] Update monitoring router (add route for STRUCTURE_ATR_AUTO)

### Step 2: Configuration
- [ ] Set global `stop_loss_type = StopLossType.STRUCTURE_ATR_AUTO` for Auto mode
- [ ] Document: "STRUCTURE_ATR_AUTO for Auto mode, STRUCTURE_ATR_STAGED for Manual FT-DMI-EMA"

### Step 3: Testing
- [ ] Auto mode: LLM trade hits +2R, partial close executes ✅
- [ ] Auto mode: Remaining 50% trails to EMA 26 ✅
- [ ] Manual mode: FT-DMI-EMA still uses full STRUCTURE_ATR_STAGED ✅
- [ ] Per-opp override: Custom SL types still work ✅

### Step 4: Documentation
- [ ] Update PROFIT_PROTECTION_STRATEGIES.md with new option
- [ ] Document STRUCTURE_ATR_AUTO phases
- [ ] Create migration guide for users

---

## Migration Path

### For Users Currently Using STRUCTURE_ATR_STAGED in Auto Mode
```
Before: stop_loss_type = STRUCTURE_ATR_STAGED
        ├─ LLM trades: Falls back to simple (no partial close)
        └─ FT-DMI-EMA: Full STRUCTURE_ATR_STAGED

After:  stop_loss_type = STRUCTURE_ATR_AUTO (default in Auto mode)
        ├─ LLM trades: Uses STRUCTURE_ATR_AUTO (with partial close!) ✅
        └─ FT-DMI-EMA: Uses STRUCTURE_ATR_AUTO (same as LLM) ✅

To keep old behavior:
        └─ Set per_opp_sl = STRUCTURE_ATR_STAGED on FT-DMI-EMA in semi-auto
```

---

## Next Steps

1. **Clarify**: Is this architecture understanding correct?
2. **Validate**: Does STRUCTURE_ATR_AUTO meet your needs?
3. **Decide**: Should we proceed with implementation?
4. **Timeline**: Can implement in ~4-6 hours (1 method + routing + testing)

Would you like me to:
- Refine the STRUCTURE_ATR_AUTO implementation details?
- Review Phase 2.2 (partial close) logic specifics?
- Proceed with implementation?
