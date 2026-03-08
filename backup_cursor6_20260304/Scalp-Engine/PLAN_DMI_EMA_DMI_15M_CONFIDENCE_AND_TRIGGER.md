# Plan: DMI-EMA +DI/-DI Crossover (15m) – Confidence Flag and Trigger Option

## 1. Scope

Two adjustments to DMI-EMA mode:

1. **Confidence flag:** Add "+DI/-DI crossover (15min)" as one of the confidence flags shown in the UI (alongside FT 1H, FT 15m, ADX 15m/1H/4H>20).
2. **Trigger option:** Add "+DI/-DI crossover (15min)" as a trigger option in the DMI-EMA dropdown, alongside "15min FT-crossover" and "Immediate market". When selected, the trade waits for a 15m +DI/-DI crossover (direction-aligned) before execution, same flow as the existing 15m FT-crossover option.

No piecemeal fixes; all listed changes are done together.

---

## 2. Current Behaviour (Reference)

- **Confidence flags** are computed in `src/ft_dmi_ema/dmi_ema_setup.py` in `get_dmi_ema_setup_status()`. They are: `ft_1h`, `ft_15m`, `adx_15m`, `adx_1h`, `adx_4h`. The UI in `scalp_ui.py` shows them under DMI-EMA as: "FT 1H | FT 15m | ADX 15m/1H/4H>20".
- **Trigger options** for DMI-EMA are defined in `scalp_ui.py`: `EXEC_MODES_DMI_EMA = ['FISHER_M15_TRIGGER', 'IMMEDIATE_MARKET']`, labels "15min FT-crossover" and "Immediate market". The execution path uses `execution_config.mode`: when mode is `FISHER_M15_TRIGGER`, the enforcer returns `WAIT_SIGNAL` with `wait_for_signal="DMI_EMA_M15_TRIGGER"` until `ft_15m_trigger_met` is True; `_check_dmi_ema_activation_signals` in `scalp_engine.py` then checks 15m Fisher crossover (via `get_dmi_ema_setup_status` → `long_trigger_met`/`short_trigger_met`) and executes when met.

---

## 3. Adjustment (1): +DI/-DI Crossover (15m) as Confidence Flag

### 3.1 Definition

- **Flag:** True when, on the 15m timeframe, +DI and -DI have just crossed (bullish: +DI crossed above -DI; bearish: -DI crossed above +DI). Same crossover logic as Fisher (last two bars).
- **Storage key:** `dmi_15m` in `confidence_flags` (or `di_15m_crossover`; plan uses `dmi_15m`).
- **Display:** "+DI/-DI 15m" or "DMI 15m" in the UI confidence line.

### 3.2 Code Changes

| Location | Change |
|----------|--------|
| **`src/ft_dmi_ema/dmi_ema_setup.py`** | In `get_dmi_ema_setup_status()`: After computing `plus_di_15m`, `minus_di_15m`, add 15m +DI/-DI crossover detection using `Indicators.detect_crossover(plus_di_15m, minus_di_15m)` (same signature as Fisher). Set `out["confidence_flags"]["dmi_15m"] = (cross == "bullish" or cross == "bearish")`. Initialize `"dmi_15m": False` in the default `confidence_flags` dict. |
| **`scalp_ui.py`** | In the DMI-EMA confidence caption (where `cf = opp.get('confidence_flags') or {}` and the line with FT 1H, FT 15m, ADX…): Add the new flag, e.g. `DMI 15m: {'✅' if cf.get('dmi_15m') else '❌'}` so the line reads: "FT 1H | FT 15m | DMI 15m | ADX 15m/1H/4H>20" (or equivalent wording). |

### 3.3 Backward Compatibility

- New key `dmi_15m` in `confidence_flags`; old payloads without it will show ❌ until the next run. No migration.

---

## 4. Adjustment (2): +DI/-DI Crossover (15m) as Trigger Option

### 4.1 Definition

- **New mode:** `DMI_M15_TRIGGER`.
- **Semantics:** Same as `FISHER_M15_TRIGGER`, but "trigger met" is defined by 15m +DI/-DI crossover aligned with direction (long: +DI crossed above -DI; short: -DI crossed above +DI), not 15m Fisher crossover.
- **Wait signal:** When waiting, store pending with `wait_for_signal="DMI_EMA_DMI_M15_TRIGGER"`. Activation logic will treat this separately from `DMI_EMA_M15_TRIGGER` (Fisher).

### 4.2 Status / Setup (dmi_ema_setup.py)

| Location | Change |
|----------|--------|
| **`src/ft_dmi_ema/dmi_ema_setup.py`** | In `get_dmi_ema_setup_status()`: Using the same 15m +DI/-DI crossover as for the confidence flag, add: `long_dmi_15m_trigger = out["long_setup_ready"] and (cross == "bullish")`, `short_dmi_15m_trigger = out["short_setup_ready"] and (cross == "bearish")`. Set `out["long_dmi_15m_trigger_met"] = long_dmi_15m_trigger`, `out["short_dmi_15m_trigger_met"] = short_dmi_15m_trigger`, and `out["dmi_15m_trigger_met"] = long_dmi_15m_trigger or short_dmi_15m_trigger`. Initialize these in the default `out` dict to `False`. |

### 4.3 UI (scalp_ui.py)

| Location | Change |
|----------|--------|
| **`scalp_ui.py`** | Add `DMI_M15_TRIGGER` to `EXEC_MODES_DMI_EMA`: `['FISHER_M15_TRIGGER', 'DMI_M15_TRIGGER', 'IMMEDIATE_MARKET']`. Add to `EXEC_MODE_LABELS_DMI_EMA`: `'DMI_M15_TRIGGER': '15min +DI/-DI crossover'`. Default mode for DMI-EMA can remain `FISHER_M15_TRIGGER` (e.g. in `saved.get('mode', 'FISHER_M15_TRIGGER')` and in the caption that describes the selected trigger). |
| **`scalp_ui.py`** | DMI-EMA trigger caption: When the selected mode is `DMI_M15_TRIGGER`, show "15m +DI/-DI crossover" and "MET" vs "Wait" based on `opp.get('dmi_15m_trigger_met', False)` instead of `ft_15m_trigger_met`. When mode is `FISHER_M15_TRIGGER`, keep current text and `ft_15m_trigger_met`. So: branch on `mode` and display the appropriate trigger label and met flag. |

### 4.4 Execution Enforcer (execution_mode_enforcer.py)

| Location | Change |
|----------|--------|
| **`src/execution/execution_mode_enforcer.py`** | In the DMI_EMA block (where we currently check `ft_15m_trigger_met` and return `WAIT_SIGNAL` with `DMI_EMA_M15_TRIGGER`): Branch on `mode = (opportunity.get("execution_config") or {}).get("mode", "FISHER_M15_TRIGGER")`. If `mode == "DMI_M15_TRIGGER"`: use `opportunity.get("dmi_15m_trigger_met") is not True` to decide WAIT_SIGNAL; set `wait_for_signal="DMI_EMA_DMI_M15_TRIGGER"` and reason e.g. "DMI-EMA: Setup ready, waiting for 15m +DI/-DI crossover". If `mode == "FISHER_M15_TRIGGER"`: keep current logic (ft_15m_trigger_met, DMI_EMA_M15_TRIGGER). When trigger is met (either path), existing EXECUTE_NOW / order_type logic applies unchanged. |

### 4.5 Engine – Injected Opportunities and SEMI_AUTO Processing (scalp_engine.py)

| Location | Change |
|----------|--------|
| **`scalp_engine.py`** | In `_inject_dmi_ema_opportunities`, where opportunities are built from `get_dmi_ema_setup_status`: For each opportunity dict, set `"dmi_15m_trigger_met": status.get("dmi_15m_trigger_met", False)` (and optionally `long_dmi_15m_trigger_met` / `short_dmi_15m_trigger_met` if needed downstream). Ensure `confidence_flags` already includes the new `dmi_15m` from status (from step 3). |
| **`scalp_engine.py`** | In `_check_dmi_ema_opportunities` (SEMI_AUTO), when building `opp_with_order`: For mode `DMI_M15_TRIGGER`, do not set `ft_15m_trigger_met = True` for "trigger met" path; the opportunity already has `dmi_15m_trigger_met` from inject. Only when mode is `IMMEDIATE_MARKET` do we force-execute (current behaviour). So no change to the "if mode == IMMEDIATE_MARKET" block; for `DMI_M15_TRIGGER` the enforcer will see `dmi_15m_trigger_met` on the opportunity and either EXECUTE_NOW or WAIT_SIGNAL. |
| **`scalp_engine.py`** | **`_check_dmi_ema_activation_signals`:** Today it only collects pending items with `wait_for_signal == "DMI_EMA_M15_TRIGGER"` and uses `get_dmi_ema_setup_status` → `long_trigger_met`/`short_trigger_met` (Fisher). Extend to also collect pending with `wait_for_signal == "DMI_EMA_DMI_M15_TRIGGER"`. For each pending item, branch on `wait_for_signal`: if `DMI_EMA_M15_TRIGGER`, keep current logic (trigger_met from long_trigger_met/short_trigger_met). If `DMI_EMA_DMI_M15_TRIGGER`, after calling `get_dmi_ema_setup_status`, set `trigger_met = (want_long and status.get("long_dmi_15m_trigger_met")) or (not want_long and status.get("short_dmi_15m_trigger_met"))`. When trigger_met, remove from pending and call `_maybe_reset_run_count_and_open_trade` as today. Optionally log "15m +DI/-DI crossover" vs "15m Fisher crossover" for clarity. |

### 4.6 Clearing Pending and Consistency

| Location | Change |
|----------|--------|
| **`scalp_engine.py`** | `_clear_pending_signals_for_disabled_opportunities` and any other logic that keys off `wait_for_signal` do not need to special-case the new value; they already match on directive.wait_for_signal. No change required unless a list of "DMI-EMA trigger types" is hard-coded somewhere (then add `DMI_EMA_DMI_M15_TRIGGER` to that list). |

### 4.7 Scans and Other Callers (run_ft_dmi_ema_scan.py, etc.)

| Location | Change |
|----------|--------|
| **`run_ft_dmi_ema_scan.py`** | If it builds DMI-EMA opportunity dicts from `get_dmi_ema_setup_status`, add `dmi_15m_trigger_met` and ensure `confidence_flags` includes `dmi_15m` from status (same as inject). |

### 4.8 Default Mode and Backward Compatibility

- Existing saved configs with `mode: FISHER_M15_TRIGGER` or `IMMEDIATE_MARKET` remain valid. New option `DMI_M15_TRIGGER` is additive. Default for new DMI-EMA rows can stay `FISHER_M15_TRIGGER`.

---

## 5. File Checklist (Implementation Order)

1. **`src/ft_dmi_ema/dmi_ema_setup.py`**  
   - Add confidence flag `dmi_15m` (+DI/-DI 15m crossover).  
   - Add `long_dmi_15m_trigger_met`, `short_dmi_15m_trigger_met`, `dmi_15m_trigger_met` to status.

2. **`scalp_ui.py`**  
   - Show `dmi_15m` in DMI-EMA confidence line.  
   - Add `DMI_M15_TRIGGER` to modes and labels.  
   - DMI-EMA trigger caption: branch on mode; show 15m +DI/-DI and `dmi_15m_trigger_met` when mode is `DMI_M15_TRIGGER`.

3. **`src/execution/execution_mode_enforcer.py`**  
   - DMI_EMA block: branch on mode; for `DMI_M15_TRIGGER` use `dmi_15m_trigger_met` and `wait_for_signal="DMI_EMA_DMI_M15_TRIGGER"`.

4. **`scalp_engine.py`**  
   - `_inject_dmi_ema_opportunities`: set `dmi_15m_trigger_met` (and confidence_flags) from status.  
   - `_check_dmi_ema_activation_signals`: handle `DMI_EMA_DMI_M15_TRIGGER` using `long_dmi_15m_trigger_met` / `short_dmi_15m_trigger_met`.

5. **`run_ft_dmi_ema_scan.py`**  
   - If it builds DMI-EMA opportunities, add `dmi_15m_trigger_met` and `confidence_flags.dmi_15m`.

---

## 6. Testing (After Implementation)

- **Confidence:** Run DMI-EMA; open a DMI-EMA opportunity in the UI; confirm the confidence line includes "+DI/-DI 15m" (or "DMI 15m") and that it toggles ✅/❌ as 15m +DI/-DI cross occurs.
- **Trigger option:** Select "15min +DI/-DI crossover" for a DMI-EMA opportunity; enable it; confirm it goes to pending with wait reason for 15m +DI/-DI; when 15m DMI crossover occurs (direction aligned), confirm the trade executes and pending is removed.
- **Existing trigger:** Select "15min FT-crossover"; confirm behaviour unchanged (pending until 15m Fisher crossover).
- **Immediate market:** Unchanged.

---

## 7. Summary

- **Confidence:** One new flag in `get_dmi_ema_setup_status` and one line in the DMI-EMA UI confidence display.
- **Trigger:** New mode `DMI_M15_TRIGGER`, new wait signal `DMI_EMA_DMI_M15_TRIGGER`, new trigger flags in status; enforcer and activation path branch on mode/wait_for_signal and use the new DMI 15m trigger flags. No change to Fisher 15m or Immediate market behaviour.
