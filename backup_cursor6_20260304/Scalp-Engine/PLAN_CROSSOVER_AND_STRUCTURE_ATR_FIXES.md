# Comprehensive Plan: Crossover Logic and STRUCTURE_ATR_STAGED Fixes

This plan addresses (1) crossover triggers firing on stale bars / wrong semantics, (2) STRUCTURE_ATR_STAGED scope and implementation bugs, and (3) consistency of all crossover-based logic across the codebase. **Do not implement until explicit go-ahead.**

---

## Part A: Crossover activation – “next crossover after enable” and bar order

### A.1 Problem summary

- **Fisher 15m/1h and DMI 15m/1h:** Activation runs when the **last bar** in the fetched window has a crossover in the right direction. There is **no** check that this bar is **after** the time the user enabled the trade (`stored_at`). So a crossover that **already happened** before enable can fire on the next engine cycle (“immediate at market”).
- **Bar order:** The activation monitor fetches candles via raw OANDA API and does **not** normalize order. OANDA can return newest-first; if so, `iloc[-1]` is the **oldest** bar, so crossover would be detected on the wrong (old) bar. Candle order must be **oldest-first** so “last bar” = most recent completed bar.
- **MACD (execution mode):** `check_macd_crossover` returns `(False, None)` when `self.config.execution_mode != ExecutionMode.MACD_CROSSOVER`. In SEMI_AUTO, the **per-opportunity** mode can be MACD_CROSSOVER while the **global** config is RECOMMENDED, so the check never runs for that opportunity.

### A.2 Intended behavior (all crossover triggers)

- **FT crossover (15m/1h), DMI crossover (15m/1h):** Trigger only when a crossover is detected on a bar whose **close time is strictly after** the pending signal’s `stored_at`. So we react only to **new** crossovers after the user enabled the trade.
- **Bar order:** All candle lists used for “last bar” crossover detection must be **oldest-first** so that the last element is the most recent completed bar.
- **MACD crossover (execution mode):** The crossover check must run when the **effective** execution mode for that opportunity is MACD_CROSSOVER (e.g. per-opportunity override in SEMI_AUTO), not only when the global config is MACD_CROSSOVER.

### A.3 Files and changes

| File | Change |
|------|--------|
| **`src/execution/fisher_activation_monitor.py`** | (1) **Candle order:** In `_fetch_candles` and `_fetch_candles_hlc`, after building the list, if the API returned newest-first (e.g. compare first and last candle `time` if available), reverse so order is oldest-first. If the raw response does not include `time`, fetch or parse it so we can both normalize order and use last bar time for freshness. (2) **Last bar time:** Extend fetch helpers to return the **last bar’s close time** (ISO or epoch) for the window used in crossover. (3) **Freshness:** In `check_activations`, for each pending item get `stored_at` (ISO). Only treat a crossover as valid if the **last bar’s close time** is **after** `stored_at` (parse both to comparable format, e.g. UTC datetime). If we don’t have last bar time (e.g. fetch doesn’t expose it yet), require that `stored_at` is at least one full bar period in the past (e.g. for M15, require now - stored_at >= 15 minutes) so we never trigger on the same bar that was open when we stored. |
| **`scalp_engine.py`** | No change to where pending is stored; `stored_at` is already set in `_store_pending_signal` in `auto_trader_core`. |
| **`auto_trader_core.py`** | (1) **MACD per-opportunity:** Add an optional parameter to `check_macd_crossover`, e.g. `execution_mode_override: Optional[ExecutionMode] = None`. When provided, use it instead of `self.config.execution_mode` for the early-return check. (2) Call site: when the engine calls `check_macd_crossover` for an opportunity, pass the **effective** execution mode (per-opportunity if SEMI_AUTO, else config). |

**Implementation notes for A.3**

- **Getting last bar time in activation monitor:** OANDA `InstrumentsCandles` response includes `time` per candle. In `_fetch_candles_hlc` / `_fetch_candles`, include `time` in each dict (or keep a separate list of times). After normalizing to oldest-first, last bar time = `times[-1]` or `candles[-1]['time']`. Use that for the freshness check.
- **Freshness check:** Parse `stored_at` (e.g. `datetime.fromisoformat(stored_at.replace('Z', '+00:00'))`) and last bar time (OANDA format). Require `last_bar_time > stored_at` (or `>=` if bar close time is exact). If parsing fails, fall back to “don’t activate this cycle” to avoid stale triggers.
- **Candle order:** When building the list, if we have `time`, compare first and last; if `first_time > last_time`, reverse the list (and any parallel list of times). Ensure Fisher/DMI logic receives oldest-first so `iloc[-1]` / “last bar” is the most recent.

---

## Part B: STRUCTURE_ATR_STAGED – scope and implementation

### B.1 Problem summary

- **Scope:** `_check_structure_atr_staged` runs for **every** trade with `sl_type == STRUCTURE_ATR_STAGED`, including LLM/Fisher opportunities where the user simply chose “FT-DMI-EMA Staged” in the UI. That exit logic (4H DMI, spread spike, ADX collapse, EMA breakdown, time stop, BE +1R, partial +2R, trail to 1H EMA 26) is designed for trades that **originate** from the FT-DMI-EMA strategy. Applying it to non–FT-DMI-EMA trades is wrong.
- **Spread spike bug:** Spread is computed as `(ask - bid) * 10000` and treated as “pips.” For JPY pairs (e.g. USD/JPY), 1 pip = 0.01, so correct pips = `(ask - bid) * 100`. Using 10000 yields ~190 “pips” for a normal spread and triggers false “spread spike” closes.

### B.2 Intended behavior

- **Scope:** Run the full FT-DMI-EMA exit logic (`_check_structure_atr_staged`) **only** when `trade.opportunity_source == 'FT_DMI_EMA'`. When `sl_type == STRUCTURE_ATR_STAGED` but `opportunity_source != 'FT_DMI_EMA'`, do **not** run that block; treat the trade with another exit (e.g. run the same branch as `BE_TO_TRAILING` so we don’t leave it with no exit logic).
- **Spread in pips:** All uses of “spread in pips” (spread spike check, any logging or thresholds) must be **pair-aware**: for JPY pairs use `(ask - bid) * 100`, for others use `(ask - bid) * 10000`, or a small helper that takes instrument/pair and returns pips.

### B.3 Files and changes

| File | Change |
|------|--------|
| **`auto_trader_core.py`** | (1) **STRUCTURE_ATR_STAGED scope:** At the start of the position-monitor branch for `trade.sl_type == StopLossType.STRUCTURE_ATR_STAGED`, add: if `getattr(trade, 'opportunity_source', '') != 'FT_DMI_EMA'`, then **don’t** call `_check_structure_atr_staged`; instead run the same path as `BE_TO_TRAILING` (e.g. call `_check_be_transition` for that trade). (2) **Spread in pips (spread spike):** In `_check_structure_atr_staged`, when reading `current_spread` from `price_data`, convert to pips using a pair-aware helper: for pair containing `"JPY"` use `(ask - bid) * 100`, else `(ask - bid) * 10000`. Use that value for both the threshold comparison and the log message (“X.X pips”). |
| **`src/oanda_client.py`** | Add a helper, e.g. `spread_to_pips(ask: float, bid: float, instrument: str) -> float`, that returns spread in pips (JPY: * 100, else * 10000). Use it in `get_current_price` so the returned `spread` is always in pips (and the rest of the codebase can rely on it). Alternatively, keep returning raw (ask-bid) and document it; then every consumer must convert. Prefer **centralizing in the client** so `get_current_price()['spread']` is always pips. |

**Implementation notes for B.3**

- **Ensuring `opportunity_source` is set:** When creating `ManagedTrade` in `create_managed_trade`, `opportunity_source` is already set from `opp.get('source', '')`. So FT-DMI-EMA trades have `source == 'FT_DMI_EMA'`; LLM/Fisher have `source == 'LLM'` or `'Fisher'` or similar. No change needed there.
- **BE_TO_TRAILING fallback:** For STRUCTURE_ATR_STAGED with non–FT_DMI_EMA source, calling `_check_be_transition(trade, current_price)` is a safe default so the trade still gets BE → trailing behavior instead of no exit logic.

---

## Part C: Other crossover logic – verify and align

### C.1 MACD crossover (entry)

- **Current:** `check_macd_crossover` uses `crossover_detected` (current vs previous bar) and updates `macd_state` per pair. It bails out when global `execution_mode != MACD_CROSSOVER`, which breaks per-opportunity MACD in SEMI_AUTO.
- **Change:** Already covered in A.3: add `execution_mode_override` (or equivalent) and pass effective mode from the engine so SEMI_AUTO per-opportunity MACD works.
- **Stale crossover:** MACD is evaluated **inline** in the main opportunity loop (no pending signal with `stored_at`). So the “only after enable” concern is different: we don’t store a MACD pending and then check later; we re-evaluate each cycle. If we want “only trigger on new crossover after this opportunity became enabled,” we’d need to store an “enabled_at” or “wait_for_macd_since” and require crossover on a bar after that. For consistency with Fisher/DMI, consider storing a pending signal for MACD too (with `stored_at`) and running a single “activation” check that uses bar time vs `stored_at`. That’s a larger refactor; at minimum, fix the per-opportunity mode bug so MACD is actually evaluated.

### C.2 MACD crossover (exit / stop loss)

- **Current:** `check_macd_reverse_crossover` uses previous vs current bar; no `stored_at` (exit is for open trades). No change needed for “stale” semantics.
- **Verification:** Ensure it uses correct candle order (oldest-first) so “last bar” is the most recent. If the position manager fetches candles via a path that returns newest-first, reverse or use a consistent order before computing MACD.

### C.3 DMI crossover (exit / stop loss)

- **Current:** `check_dmi_reverse_crossover` uses `dmi_analyzer.calculate_dmi` / crossover on last bar. Same as above: ensure candle order is oldest-first wherever candles are produced for this call.

### C.4 FT-DMI-EMA 15m trigger

- **Current:** `_check_ft_dmi_ema_activation_signals` uses `get_setup_status` (from ft_dmi_ema), which uses its own candle fetcher and logic. Not using the same pending list as Fisher/DMI; it has its own trigger `FT_DMI_EMA_M15_TRIGGER`.
- **Verification:** If `get_setup_status` exposes or uses “last bar” crossover, ensure (1) candle order is oldest-first and (2) if we want “only after enable,” a similar `stored_at` vs last bar time check applies. If the FT-DMI-EMA flow doesn’t store a `stored_at` for that trigger, add it when storing the pending signal and pass last bar time (or equivalent) so we don’t trigger on a stale 15m crossover.

### C.5 Summary table – crossover logic

| Trigger | Where | Stale risk? | Bar order risk? | Action |
|---------|--------|-------------|------------------|--------|
| Fisher 15m/1h | fisher_activation_monitor | Yes | Yes (if API order not normalized) | A.3: freshness + oldest-first |
| DMI 15m/1h | fisher_activation_monitor | Yes | Yes | A.3: same |
| MACD (entry) | position_manager.check_macd_crossover | Per-opp not run | Unclear | A.3: execution_mode_override; verify candle order |
| MACD (exit) | check_macd_reverse_crossover | N/A | Verify | C.2: ensure oldest-first |
| DMI (exit) | check_dmi_reverse_crossover | N/A | Verify | C.3: ensure oldest-first |
| FT-DMI-EMA 15m | get_setup_status / scalp_engine | Possible | Verify | C.4: add stored_at + last bar check if applicable |

---

## Part D: Implementation order and testing

### D.1 Recommended order

1. **OANDA client – spread in pips (B.3)**  
   Implement `spread_to_pips` (or equivalent) and make `get_current_price()['spread']` pips for all pairs. Fixes STRUCTURE_ATR_STAGED spread spike for JPY and any other consumer.

2. **STRUCTURE_ATR_STAGED scope (B.3)**  
   In the position monitor, run full FT-DMI-EMA logic only when `opportunity_source == 'FT_DMI_EMA'`; otherwise use BE_TO_TRAILING path for that trade.

3. **Activation monitor – candle order and last bar time (A.3)**  
   In `_fetch_candles` and `_fetch_candles_hlc`, ensure oldest-first and return (or expose) last bar close time. Use it in `check_activations` for the freshness check (only activate if last bar time > stored_at).

4. **MACD per-opportunity (A.3)**  
   Add execution_mode override to `check_macd_crossover` and pass effective mode from the engine.

5. **Verify MACD/DMI exit and FT-DMI-EMA 15m (C.2–C.4)**  
   Confirm candle order and, for FT-DMI-EMA 15m, add stored_at vs last bar time if that path can fire on a stale crossover.

### D.2 Testing

- **Stale crossover:** Enable a trade with “FT crossover (15m)” when the chart already shows a bearish cross; confirm it does **not** fire until a **new** 15m bar shows a bearish cross after `stored_at`.
- **Bar order:** With a known crossover on the **most recent** completed bar only, confirm activation fires; with crossover only on an older bar, confirm it does not (and that we’re not using the wrong end of the series).
- **STRUCTURE_ATR_STAGED:** Open an LLM trade with SL type “FT-DMI-EMA Staged”; confirm it does **not** get closed by spread spike (and gets BE → trailing behavior). Open an FT-DMI-EMA-sourced trade; confirm full FT-DMI-EMA exits still run.
- **Spread pips:** For USD/JPY, confirm spread is ~1–3 pips in logs/config and spread spike does not fire at normal spread.
- **MACD entry:** In SEMI_AUTO, set one opportunity to “MACD crossover”; when MACD crosses in the right direction, confirm the trade executes (no early return due to global config).

---

## Part E: Files touched (summary)

| File | Parts |
|------|--------|
| `src/execution/fisher_activation_monitor.py` | A.3 (candle order, last bar time, freshness vs stored_at) |
| `auto_trader_core.py` | A.3 (MACD override), B.3 (STRUCTURE_ATR scope, spread pips in _check_structure_atr_staged) |
| `src/oanda_client.py` | B.3 (spread_to_pips and use in get_current_price) |
| `scalp_engine.py` | A.3 (pass execution_mode to check_macd_crossover when calling) |

Optional / follow-up: FT-DMI-EMA 15m path (C.4), and any shared candle-fetch helper to guarantee oldest-first and last-bar time for MACD/DMI exit (C.2, C.3).

---

*Plan complete. No code changes until you give the go-ahead.*
