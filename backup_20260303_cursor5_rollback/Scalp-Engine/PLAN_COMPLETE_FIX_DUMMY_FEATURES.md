# Comprehensive Plan: Complete Fix for All Dummy UI Features

This plan fixes every dummy feature identified in `DUMMY_UI_FEATURES_REPORT.md` in one coordinated change. **No piecemeal fixes.** Implementation should only start after explicit go-ahead.

---

## 1. Scope (What Gets Fixed)

| # | Feature | Problem | Outcome After Fix |
|---|--------|---------|-------------------|
| A | **DMI crossover (1h)** execution trigger | Activation monitor never checks `DMI_H1_CROSSOVER` | Pending signals waiting for 1h DMI crossover are evaluated each cycle; when +DI crosses above -DI (bullish) or below (bearish) on the last H1 bar, trade activates. |
| B | **DMI crossover (15m)** execution trigger | Activation monitor never checks `DMI_M15_CROSSOVER` | Same as (A) on M15. |
| C | **DMI crossover exit** stop loss | `DMI_CROSSOVER` not in `StopLossType` enum; branch never runs | New/loaded trades can use DMI exit; position monitor closes trade on +DI/-DI reverse crossover using config `dmi_sl_timeframe`. |
| D | **DMI Stop Loss Timeframe** (Settings) | Only relevant when SL = DMI_CROSSOVER, which was dummy | Becomes effective: used by `check_dmi_reverse_crossover` when SL type is DMI_CROSSOVER. |

---

## 2. Dependencies and Order

- **C and D** (stop loss) are independent of **A and B** (execution triggers).  
- **A and B** share the same activation-monitor change (add DMI triggers alongside Fisher).  
- **Execution order for implementation:**  
  1. **Part I: DMI stop loss (C + D)** — enum + monitor wiring; config already has `dmi_sl_timeframe`.  
  2. **Part II: DMI execution triggers (A + B)** — activation monitor checks for DMI_H1 and DMI_M15.

Doing Part I first avoids loading/saving state with an unknown `DMI_CROSSOVER` and ensures existing `check_dmi_reverse_crossover` is used. Part II then makes “DMI crossover (1h/15m)” execution modes functional.

---

## 3. Part I: DMI Crossover Stop Loss (C + D)

### 3.1 Add `DMI_CROSSOVER` to `StopLossType` enum

**File:** `Scalp-Engine/auto_trader_core.py`

- **Location:** Class `StopLossType` (around line 84).
- **Change:** Add one enum member after `MACD_CROSSOVER`:
  - `DMI_CROSSOVER = "DMI_CROSSOVER"  # Close on +DI/-DI reverse crossover`
- **Result:** `StopLossType.DMI_CROSSOVER` exists; `StopLossType(per_opp_sl)` and `StopLossType(trade_data['sl_type'])` succeed for `"DMI_CROSSOVER"`.

### 3.2 Use `DMI_CROSSOVER` directly in position monitor (remove getattr guard)

**File:** `Scalp-Engine/auto_trader_core.py`

- **Location:** In the position monitor loop where stop loss type is checked (around lines 1313–1327).
- **Change:** Replace:
  - `elif getattr(StopLossType, 'DMI_CROSSOVER', None) is not None and trade.sl_type == StopLossType.DMI_CROSSOVER:`
  with:
  - `elif trade.sl_type == StopLossType.DMI_CROSSOVER:`
- **Result:** The existing `check_dmi_reverse_crossover(trade, oanda_client)` block runs for trades with `sl_type == DMI_CROSSOVER`. No other logic change; `check_dmi_reverse_crossover` already uses `self.config.dmi_sl_timeframe` (or `'H1'` if None).

### 3.3 Config and UI (D)

- **No code change required for Part I.**  
- `TradeConfig` already has `dmi_sl_timeframe: Optional[str] = None` (default H1).  
- UI already shows “DMI Stop Loss Timeframe” when “DMI crossover exit” is selected and persists it.  
- Once the enum and monitor branch are in place, this setting is used by `check_dmi_reverse_crossover`.

### 3.4 Part I verification

- Unit or manual: Create/open a trade with `sl_type='DMI_CROSSOVER'`; confirm no `ValueError` and trade is created with `sl_type == StopLossType.DMI_CROSSOVER`.  
- Load state file containing `"sl_type": "DMI_CROSSOVER"`; confirm load succeeds and monitor runs the DMI exit check.  
- Optional: One manual test with a live/paper trade using DMI exit and Settings `dmi_sl_timeframe` M15 or H1.

---

## 4. Part II: DMI Execution Triggers (A + B)

### 4.1 Extend activation monitor to handle DMI_H1 and DMI_M15

**File:** `Scalp-Engine/src/execution/fisher_activation_monitor.py`

**Current behaviour:** `check_activations` loops only over `(TRIGGER_M15, TRIGGER_H1)` (Fisher), uses `_fetch_candles` (closes only) and `_fisher_crossover_direction`, and never looks at `TRIGGER_DMI_H1` or `TRIGGER_DMI_M15`.

**Required behaviour:** For each of `TRIGGER_DMI_H1` and `TRIGGER_DMI_M15`:

1. Resolve granularity: `'H1'` for DMI_H1, `'M15'` for DMI_M15.
2. Get pending items with `get_pending_for_trigger(trigger)` (same as Fisher).
3. For each item: get `pair`, `direction` from opportunity; fetch **HLC** candles via existing `_fetch_candles_hlc(oanda_client, pair, granularity, count=50)` (already in file).
4. Call existing `_dmi_crossover_direction(hlc_candles)` (already in file; uses `dmi_analyzer.dmi_crossover_direction`).
5. If result is `None`, skip. If direction does not match opportunity (use existing `_direction_matches_opportunity(crossover, direction)`), skip.
6. Log activation (e.g. `"FisherActivationMonitor: ACTIVATED ... DMI crossover on H1"` or M15) and append to `activated` with same structure as Fisher (`signal_id`, `opportunity`, `directive`, `stored_at`).

**Concrete change:**

- In `check_activations`, after the existing `for trigger in (TRIGGER_M15, TRIGGER_H1):` block (which handles Fisher), add a **second** loop (or extend the loop to include four triggers).
- **Recommended structure:** Keep one loop over four triggers. For each trigger:
  - If trigger in `(TRIGGER_M15, TRIGGER_H1)`: granularity = M15 or H1; fetch with `_fetch_candles`; crossover = `_fisher_crossover_direction(closes)` (existing).
  - If trigger in `(TRIGGER_DMI_H1, TRIGGER_DMI_M15)`: granularity = H1 or M15; fetch with `_fetch_candles_hlc`; crossover = `_dmi_crossover_direction(hlc_candles)`.
  - Direction matching and appending to `activated` are the same for all four (reuse `_direction_matches_opportunity`).
- Ensure `TRIGGER_DMI_H1` and `TRIGGER_DMI_M15` are included in the iteration (they are already defined at top of file).

**Semantics (match Fisher):** DMI crossover is detected only on the **last bar** (previous bar +DI vs -DI opposite to current bar). So activation happens the first time the “last completed bar” shows a crossover in the correct direction. No change to `dmi_analyzer` required for this plan.

### 4.2 Engine: no change to pending storage or enforcer

- The engine already stores pending signals with `wait_for_signal="DMI_H1_CROSSOVER"` or `"DMI_M15_CROSSOVER"` when the user selects “DMI crossover (1h)” or “DMI crossover (15m)”.  
- The engine already calls `monitor.check_activations(...)` and processes the returned `activated` list (remove from pending, open trade with activation_trigger=IMMEDIATE).  
- **No change** in `scalp_engine.py` or `execution_mode_enforcer.py` for Part II; only the activation monitor must return DMI activations in `activated`.

### 4.3 Part II verification

- With an opportunity set to “DMI crossover (1h)” or “DMI crossover (15m)” and enabled, confirm pending signal is stored.  
- When the last H1 (or M15) bar has a +DI/-DI crossover in the opportunity direction, confirm on the next engine cycle: log shows “ACTIVATED … DMI crossover on H1/M15”, pending is removed, and trade is opened (or execution path runs as for Fisher activation).  
- Optional: Verify that crossover in the **wrong** direction does not activate (e.g. BUY opportunity with bearish DMI crossover).

---

## 5. Files Touched (Summary)

| File | Part | Changes |
|------|------|--------|
| `Scalp-Engine/auto_trader_core.py` | I | Add `DMI_CROSSOVER` to `StopLossType`; in position monitor, replace getattr guard with `trade.sl_type == StopLossType.DMI_CROSSOVER`. |
| `Scalp-Engine/src/execution/fisher_activation_monitor.py` | II | In `check_activations`, include `TRIGGER_DMI_H1` and `TRIGGER_DMI_M15`; for DMI triggers use `_fetch_candles_hlc` + `_dmi_crossover_direction`; same direction match and append to `activated`. |

No changes to: `scalp_ui.py`, `execution_mode_enforcer.py`, `scalp_engine.py`, `dmi_analyzer.py`, or config API (beyond existing `dmi_sl_timeframe`).

---

## 6. Rollback

- **Part I:** Remove `DMI_CROSSOVER` from enum and restore the `getattr(StopLossType, 'DMI_CROSSOVER', None) is not None and ...` condition. Trades already saved with `sl_type: "DMI_CROSSOVER"` will again fall back to config on load (current behaviour).  
- **Part II:** Remove DMI triggers from the activation loop so only `TRIGGER_M15` and `TRIGGER_H1` (Fisher) are processed; pending DMI signals will again never activate.

---

## 7. Testing Checklist (After Implementation)

- [ ] **Part I – New trade:** Set an opportunity’s stop loss to “DMI crossover exit”, run engine; trade opens with `sl_type == DMI_CROSSOVER` and no error.  
- [ ] **Part I – State load:** Persist a trade with `DMI_CROSSOVER` in state file; restart; trade loads and DMI exit check runs in monitor.  
- [ ] **Part I – Exit:** With a trade using DMI exit, when +DI/-DI reverse crossover occurs on the configured timeframe, trade is closed with the expected reason.  
- [ ] **Part II – 1h:** Enable an opportunity with “DMI crossover (1h)”; when H1 last bar has correct-direction crossover, trade activates and opens.  
- [ ] **Part II – 15m:** Same for “DMI crossover (15m)” and M15.  
- [ ] **Regression:** Fisher H1/M15 activation and MACD/DMI stop loss for existing types still work as before.

---

## 8. Go-Ahead

**Do not implement until you explicitly give the go-ahead.** When you do, implementation will follow this plan in order: Part I (DMI stop loss) then Part II (DMI execution triggers), with verification as above.
