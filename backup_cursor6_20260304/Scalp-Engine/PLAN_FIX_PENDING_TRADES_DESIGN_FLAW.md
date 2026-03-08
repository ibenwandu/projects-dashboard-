# Plan: Fix Pending Trades Design Flaw (Clear Logic Overwriting Enabled State)

## 1. Problem Summary

- **Symptom:** After a refresh (or after the engine runs), enabled pairs that were in pending state show as disabled in the UI. The same pairs still appear in the "new opportunities" list; only their enabled/disabled state is wrong.
- **Root cause:** `_clear_pending_signals_for_disabled_opportunities` removes pending signals when `(pair, direction)` is not in the **allowed set** (current market_state + enabled in config), and **always** calls `set_opportunity_enabled(opp_id, False)` for every removed signal. So when the engine’s market_state snapshot has **fewer or different** opportunities than the UI’s (e.g. 6 vs 8), pairs that aren’t in that snapshot are treated as “user wants disabled” and the engine overwrites the semi-auto config.
- **Design flaw:** The code assumes “not in my allowed set” ⇒ “user wants this disabled.” In reality, “not in allowed set” can mean either (a) user disabled it, or (b) the opportunity is **not in this run’s market_state** (different snapshot). Only in (a) should we ever write disabled; in (b) we must **not** touch the user’s enabled preference.

---

## 2. Fix Principle

- **When removing a pending signal**, call `set_opportunity_enabled(opp_id, False)` **only** when the `(pair, direction)` **is present in the current market_state**.  
  If the opportunity is **not** in the current market_state, **do not** change the semi-auto config; only remove the pending signal.
- **Rationale:** If the pair is in market_state but not enabled, the config already reflects the user’s choice (or we’re syncing to disabled for that visible opportunity). If the pair is **not** in market_state, we must not infer “user wants disabled” — we simply don’t see it this run; the user’s previous enabled state should be preserved when the pair reappears.

---

## 3. Implementation Steps

### Step 3.1 – Build “in market state” set (same file: `scalp_engine.py`)

**Location:** `_clear_pending_signals_for_disabled_opportunities`, right after building `enabled_set` (after the three `for opp in market_state.get(...)` loops, before the “Remove any pending signal” loop).

**Change:**

1. Add a new set: `in_market_state_set`, containing **all** `(pair_norm, dir_key)` that appear in the current `market_state`, **regardless** of enabled/disabled.
2. Populate it by iterating the same three sources:
   - `market_state.get('opportunities', [])`
   - `market_state.get('fisher_opportunities', [])`
   - `market_state.get('ft_dmi_ema_opportunities', [])`  
   For each opportunity, add `(_norm_pair(pair), _norm_dir(direction))` to `in_market_state_set` (no `sac.is_enabled` check).

**Code shape (conceptual):**

```python
# After building enabled_set, before the "Remove any pending signal" loop:

in_market_state_set = set()
for opp in market_state.get('opportunities', []):
    pair = opp.get('pair', '')
    direction = opp.get('direction', '')
    in_market_state_set.add((_norm_pair(pair), _norm_dir(direction)))
for opp in market_state.get('fisher_opportunities', []):
    pair = opp.get('pair', '')
    direction = opp.get('direction', '')
    in_market_state_set.add((_norm_pair(pair), _norm_dir(direction)))
for opp in market_state.get('ft_dmi_ema_opportunities', []):
    in_market_state_set.add((_norm_pair(opp.get('pair')), _norm_dir(opp.get('direction'))))
```

### Step 3.2 – Only set disabled when (pair, direction) is in current market_state

**Location:** Same method, inside the loop that removes pending signals (where we currently always call `sac.set_opportunity_enabled(opp_id, False)` when `not has_open_position`).

**Change:**

1. Keep: remove the pending signal from `pending_signals` when `(pair_norm, dir_key) not in enabled_set`.
2. Keep: the `has_open_position` check — do **not** call `set_opportunity_enabled(..., False)` if there is an open position for that (pair, direction).
3. **New condition:** Only call `set_opportunity_enabled(opp_id, False)` when **in addition** to `not has_open_position` we have `(pair_norm, dir_key) in in_market_state_set`.
4. **Else:** If `(pair_norm, dir_key) not in in_market_state_set`, do **not** call `set_opportunity_enabled`. Optionally log at debug/info that we removed the pending signal but left enabled state unchanged because the opportunity was not in this run’s market state.

**Code shape (conceptual):**

```python
if (pair_norm, dir_key) not in enabled_set:
    self.position_manager.pending_signals.pop(signal_id, None)
    removed_any = True
    self.logger.info(f"🔄 Removed pending signal {signal_id} (no longer enabled or not in market state)")
    # Only set config to disabled when (pair, direction) is in THIS run's market state.
    # When it's not in market state, preserve user's enabled preference for when the pair reappears.
    open_position_states = (...)
    has_open_position = (...)
    if not has_open_position and (pair_norm, dir_key) in in_market_state_set:
        try:
            opp_id = get_stable_opportunity_id(opp) ...
            if opp_id:
                sac.set_opportunity_enabled(opp_id, False)
        except Exception as e:
            ...
    elif not has_open_position and (pair_norm, dir_key) not in in_market_state_set:
        self.logger.debug("Left enabled state unchanged for %s %s (not in this run's market state)", pair_norm, dir_key)
    else:
        self.logger.debug("Skipped setting opportunity to disabled (open position exists for %s %s)", pair_norm, dir_key)
```

### Step 3.3 – Update docstring

**Location:** Top of `_clear_pending_signals_for_disabled_opportunities`.

**Change:** State that we only call `set_opportunity_enabled(opp_id, False)` when the (pair, direction) is present in the current market_state; when it is not in market state we only remove the pending signal and leave the user’s enabled preference unchanged.

---

## 4. Edge Cases and Behavior After Fix

| Scenario | Before fix | After fix |
|--------|------------|-----------|
| Engine sees 6 opps; user had 7 enabled; 2 pending not in the 6 | Pending removed, those 2 set disabled | Pending removed; **enabled state unchanged** for those 2; when UI shows 8, they stay enabled |
| User disables an opp in UI; (pair, dir) in market_state | Pending removed, set disabled (no-op) | Same: pending removed; if we call set disabled it’s still no-op |
| (pair, dir) in market_state, enabled in config | In enabled_set → pending not removed | No change |
| (pair, dir) in market_state, not enabled in config | Pending removed, set disabled | Pending removed; we **do** call set_opportunity_enabled(False) (pair is in in_market_state_set) — redundant but harmless |
| (pair, dir) has open position | We skip set_opportunity_enabled | Same (unchanged) |

---

## 5. Testing / Verification

1. **Unit test (optional but recommended):** In a test, call `_clear_pending_signals_for_disabled_opportunities` with a `market_state` that has only a subset of pairs (e.g. 2 opportunities). Pending signals for pairs **not** in that subset should be removed, but the semi-auto config should **not** have those pairs set to disabled (mock or assert that `set_opportunity_enabled` was not called for those opp_ids).
2. **Integration / manual:** Enable several pairs (e.g. 5), put some in pending (e.g. WAIT_SIGNAL). Trigger a run where the engine gets a market_state with fewer opportunities (e.g. 2). After the run, refresh the UI: the 5 pairs should still show as enabled where you had enabled them; only the pending list may be shorter (signals for pairs not in that run’s snapshot removed).
3. **Logs:** After deploy, confirm in logs that when a pending signal is removed and the (pair, direction) is not in market state, you see the “Left enabled state unchanged” (or equivalent) debug log and **no** config overwrite for that opp_id.

---

## 6. Files to Touch

- **Single file:** `Scalp-Engine/scalp_engine.py`
  - Method: `_clear_pending_signals_for_disabled_opportunities`
  - Add `in_market_state_set` construction.
  - Guard `set_opportunity_enabled(opp_id, False)` with `(pair_norm, dir_key) in in_market_state_set`.
  - Update docstring and optional debug log as above.

---

## 7. Optional Follow-ups

- **Logging:** Add an INFO log when we remove a pending signal **without** setting disabled (e.g. “Removed pending signal X; left enabled state unchanged (not in this run’s market state)”) so operators can see the behavior in production.
- **Docs:** Add a short note in `PLAN_ACTIVE_TRADE_EXCEPTION.md` or a “Semi-auto behavior” doc that the engine never sets an opportunity to disabled solely because it was missing from the current market_state snapshot.
- **Config API:** No changes required; behavior is entirely in the engine’s clear logic.

---

## 8. Summary

- **One behavioral change:** Only call `set_opportunity_enabled(opp_id, False)` when the pending signal’s `(pair, direction)` is in the **current** market_state (`in_market_state_set`). If it’s not in market state, only remove the pending signal and leave the user’s enabled state unchanged.
- **Result:** Pending trades are still cleaned when they’re not in the allowed set, but the engine stops overwriting your enabled state for pairs that simply weren’t in that run’s snapshot; when those pairs reappear in the list, they remain enabled as you set them.
