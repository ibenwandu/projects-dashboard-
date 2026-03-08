# Plan: Exception for Active Trades When Clearing Pending Signals

**Date:** 2026-02-11  
**Context:** When a pending signal is removed (opportunity left market state or no longer enabled), we set that opportunity to **disabled** so it reappears as Disabled when it comes back. You requested an **exception**: do **not** set to disabled when that (pair, direction) has an **active trade** (open position).

**Scope:** Single, self-contained change. No piecemeal edits; this plan is the only change.

---

## 1. Current behavior (no exception)

In `_clear_pending_signals_for_disabled_opportunities` (scalp_engine.py):

- For each pending signal whose (pair_norm, dir_key) is **not** in `enabled_set`:
  1. Remove the pending signal.
  2. Call `sac.set_opportunity_enabled(opp_id, False)`.

So every removed pending signal causes that opportunity to be disabled when it reappears. There is **no** check for an active trade on that pair/direction.

---

## 2. Desired behavior

- **Same as now** when (pair, direction) has **no** open position: remove pending signal and set opportunity to disabled.
- **Exception (OPEN only):** When (pair, direction) has an **OPEN** position (filled trade), **do not** call `set_opportunity_enabled(opp_id, False)`.  
  So when that pair reappears, it can stay **Enabled** because the user has a live position from that opportunity.
- **No exception for PENDING:** Pending orders (order placed but not yet filled) **do not** get the exception. When we remove the pending signal, we still set the opportunity to disabled; the pending order can be removed and the opportunity returns to disabled when it reappears.

---

## 3. How to detect “OPEN position” for (pair, direction)

- **Source:** `self.position_manager.active_trades` (in auto_trader_core).
- **Type:** `Dict[str, ManagedTrade]` (trade_id → ManagedTrade).
- **ManagedTrade:** has `.pair`, `.direction`, and `.state` (TradeState enum: PENDING, OPEN, AT_BREAKEVEN, TRAILING, etc.).
- **Normalization:** Use the **same** normalization as in `_clear_pending_signals_for_disabled_opportunities`: `_norm_pair(p)` and `_norm_dir(d)`.
- **Check (OPEN only):** Before calling `sac.set_opportunity_enabled(opp_id, False)`, compute:
  - Only consider trades where **state is OPEN** (filled position). Optionally include AT_BREAKEVEN and TRAILING as they are also filled positions. **Exclude PENDING** (unfilled order).
  - `has_open_position = any(
        (_norm_pair(t.pair), _norm_dir(t.direction)) == (pair_norm, dir_key)
        and getattr(t, 'state', None) in (TradeState.OPEN, TradeState.AT_BREAKEVEN, TradeState.TRAILING)
        for t in (getattr(self.position_manager, 'active_trades', None) or {}).values()
    )`
  - If `has_open_position` is True, **skip** `set_opportunity_enabled(opp_id, False)`.
- **PENDING:** If the only matching trade has state PENDING, we **do not** skip; we call `set_opportunity_enabled(opp_id, False)` so the opportunity reappears as Disabled.

---

## 4. Exact code change (single place)

**File:** `Scalp-Engine/scalp_engine.py`  
**Function:** `_clear_pending_signals_for_disabled_opportunities`

**Current block (after removing the pending signal):**

```python
                self.logger.info(f"🔄 Removed pending signal {signal_id} (no longer enabled or not in market state)")
                # Set semi-auto config to disabled so when this pair reappears it shows Disabled (basis may have changed)
                try:
                    opp_id = get_stable_opportunity_id(opp) if get_stable_opportunity_id else _stable_opp_id_fallback(opp)
                    if opp_id:
                        sac.set_opportunity_enabled(opp_id, False)
                except Exception as e:
                    self.logger.debug("Could not set opportunity to disabled in semi-auto config: %s", e)
```

**New logic:**

1. After removing the pending signal and logging, compute whether (pair_norm, dir_key) has an **OPEN** position (state in OPEN, AT_BREAKEVEN, TRAILING; exclude PENDING):
   - Iterate `self.position_manager.active_trades.values()` (with a safe fallback if `active_trades` is missing).
   - For each `t`, require match on (pair, direction) **and** `t.state` in (TradeState.OPEN, TradeState.AT_BREAKEVEN, TradeState.TRAILING).
2. Only if there is **no** open position for that (pair_norm, dir_key): run the existing `try` block that calls `sac.set_opportunity_enabled(opp_id, False)`.
3. If there **is** an open position: do **not** call `set_opportunity_enabled`; optionally log at debug that we skipped because of open position.

**No other files** are changed. No new functions; only this one block in this one function.

---

## 5. Edge cases

| Case | Handling |
|------|----------|
| `position_manager` is None | Safe: we already return early at the start of the function if not position_manager. No change. |
| `active_trades` missing or not a dict | Use `getattr(self.position_manager, 'active_trades', None) or {}` so we iterate over an empty dict → no active trade → we disable as today. |
| Trade is PENDING (order not filled) | We **do** disable (no exception for PENDING). Correct. |
| Same pair, opposite direction (e.g. BUY pending signal, SHORT active trade) | (pair_norm, dir_key) different; no match → we **do** disable. Correct. |

---

## 6. Verification

- **Unit / manual:** With no active trades, remove a pending signal (e.g. opportunity leaves market state) → opportunity should be set to disabled (unchanged behavior).
- **Exception (OPEN only):** Have an **OPEN** (filled) position on AUD/USD BUY; then let AUD/USD leave the list so the pending signal is removed → we should **not** set AUD/USD BUY to disabled. **PENDING** order only → we **do** set to disabled.
- **Log:** When we skip disabling due to active trade, one debug log line so support can see the reason.

---

## 7. Summary

- **What:** Add a single check in `_clear_pending_signals_for_disabled_opportunities`: if (pair_norm, dir_key) has an **OPEN** position (state in OPEN, AT_BREAKEVEN, TRAILING) in `position_manager.active_trades`, do **not** call `sac.set_opportunity_enabled(opp_id, False)`. PENDING orders do not get the exception.
- **Where:** One block in `Scalp-Engine/scalp_engine.py` only.
- **No other changes:** No new files, no changes to semi_auto_controller or UI.

---

**Permission to proceed:** Please confirm you approve this plan before any code change is made.
