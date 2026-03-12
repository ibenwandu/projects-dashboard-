# ATR_TRAILING Immediate Activation — Detailed Fix Plan

**Date:** March 6, 2026  
**Context:** Phase 0.5 investigation completed; implementation no longer gated.  
**Reference:** `improvementplan.md` Phase 0.5, Fix 4; `cursor_works.md` (personal) Part 12–13.

---

## 1. Problem Statement

**Observed behaviour:** ATR_TRAILING converts to trailing stop **immediately when the trade opens**, instead of only when the trade is in profit by at least 1 pip.

**Evidence:**  
- UI shows e.g. GBP/USD SELL (TRAILING) with +39.5 pips while the chart can show the trade in loss at that moment.  
- Trailing stop is set at entry (e.g. 10.47 pips) right after open.  
- Result: trailing can activate in a losing trade or before breakeven, contradicting the intended rule (“only when ≥1 pip profit”).

**Code intent (current):**  
- `_check_ai_trailing_conversion()` only converts when `in_profit` is true: for SHORT `current_price <= entry_price - min_profit_distance`, for LONG `current_price >= entry_price + min_profit_distance`.  
- `current_price` comes from `current_prices.get(trade.pair)` in `monitor_positions()`, which is filled by `_get_current_prices()` (OANDA PricingInfo mid).  
- There is **no** check for “trade just opened” and **no** use of OANDA’s unrealized P/L for the conversion decision.

---

## 2. Root Cause (Post–Phase 0.5)

1. **First-cycle / timing:** In the first monitoring cycle(s) after a trade opens, the combination of:
   - Our `entry_price` (from fill or sync),
   - OANDA mid from `_get_current_prices()` at that moment,
   - Possible brief favorable tick or spread,
   can satisfy `in_profit` even when the trade is effectively flat or in loss. Conversion then runs in the very first cycle.

2. **Single source of truth for “in profit”:** The decision uses only `current_price` vs `entry_price`. We do **not** use:
   - How long the trade has been OPEN (`opened_at`),
   - OANDA’s `unrealizedPL` (already fetched for OPEN trades in `monitor_positions()` and stored in `trade.oanda_unrealized_pl`).

3. **No stabilization period:** There is no minimum “age” for an OPEN trade before we allow conversion, so we don’t skip the fragile first 1–2 minutes where price can be misleading.

---

## 3. Design Principles

- **One change set:** Implement all of the following together; no piecemeal rollout for this fix.
- **Defence in depth:** Use both a **time-based guard** and an **OANDA P/L gate** so that conversion only happens when:
  - The trade has been OPEN for a minimum time, and  
  - We have confidence the trade is actually in profit (either our pips calculation or OANDA’s unrealized P/L).
- **Preserve existing behaviour where correct:** BE_TO_TRAILING and the TRAILING-state distance update logic stay unchanged. Only the **first conversion from OPEN → TRAILING** for ATR_TRAILING is made stricter.
- **Observability:** Add clear logs when we skip conversion (too new, or not in profit per OANDA) so future debugging is straightforward.

---

## 4. Detailed Fix Design

### 4.1 Time-based guard (minimum age for OPEN trades)

- **Where:** `auto_trader_core.py`, inside `_check_ai_trailing_conversion()`, at the start of the `if trade.state == TradeState.OPEN` block.
- **Logic:**
  - If `trade.opened_at` is missing, treat as “too new” and skip conversion (log at DEBUG and return).
  - Compute `time_since_open_seconds = (now_utc - trade.opened_at).total_seconds()`.  
    Use timezone-aware now (e.g. `datetime.now(pytz.UTC)`) and ensure `opened_at` is interpreted in UTC (e.g. if it’s naive, treat as UTC for the delta).
  - If `time_since_open_seconds < ATR_TRAILING_MIN_AGE_SECONDS`, do **not** convert; log at DEBUG (e.g. “ATR Trailing: skipping conversion for trade_id X (open only Ns, min Ys)”) and return.
- **Constant:** Add a single constant, e.g. `ATR_TRAILING_MIN_AGE_SECONDS = 120` (2 minutes), at class or module level next to `MIN_PROFIT_PIPS_FOR_TRAILING`. This can be made configurable later if needed; for this plan, a constant is enough.
- **Rationale:** Monitoring runs roughly every 60s. A 2-minute delay skips the first 1–2 cycles so we avoid converting on the first tick after open.

### 4.2 OANDA unrealized P/L gate (when available)

- **Where:** Same function, same OPEN block, **after** the time-based guard and **before** the existing `in_profit` check.
- **Context:** In `monitor_positions()`, for `trade.state == TradeState.OPEN` we already call TradeDetails and set `trade.oanda_unrealized_pl`. So when `_check_ai_trailing_conversion()` runs, that value is already populated for the current cycle.
- **Logic:**
  - If `trade.oanda_unrealized_pl` is set and is a number:
    - If `trade.oanda_unrealized_pl <= 0`, do **not** convert. Log at DEBUG (e.g. “ATR Trailing: skipping conversion for trade_id X (OANDA unrealized P/L not positive: Y)”). Return.
    - Only if `trade.oanda_unrealized_pl > 0` (or not available) proceed to the existing `in_profit` check.
  - If `trade.oanda_unrealized_pl` was never set (e.g. API failed this cycle), rely only on the existing `current_price` vs `entry_price` check (no change to that formula).
- **Rationale:** OANDA’s unrealized P/L is the broker’s view of the same position. Using it when available prevents converting when our mid-price calculation says “in profit” but the actual position is not (e.g. spread, execution price vs our stored entry).

### 4.3 Keep existing in_profit check

- **No change** to the formula:  
  `in_profit = current_price >= entry_price + min_profit_distance` (long) or  
  `current_price <= entry_price - min_profit_distance` (short).  
- This remains the primary condition; the time and OANDA gates only **add** extra requirements before we are allowed to convert.

### 4.4 TRAILING-state branch (distance updates)

- **No change** to the `elif trade.state == TradeState.TRAILING` block.  
- Distance updates when volatility regime changes stay as they are; they do not cause “immediate activation” and are not in scope.

### 4.5 Logging

- When conversion is **skipped** due to:
  - **Too new:** DEBUG: e.g. `"ATR Trailing: skipping conversion for {trade_id} ({pair} {direction}): open {time_since_open_seconds:.0f}s < min {ATR_TRAILING_MIN_AGE_SECONDS}s"`.
  - **OANDA P/L not positive:** DEBUG: e.g. `"ATR Trailing: skipping conversion for {trade_id} ({pair} {direction}): OANDA unrealized P/L = {oanda_unrealized_pl} (not positive)"`.
- When conversion is **attempted** (existing INFO) and when it **succeeds** or **fails** (existing INFO/WARNING): keep as-is.  
- Optional: when we **do** convert, log once at DEBUG the values used (e.g. `time_since_open_seconds`, `oanda_unrealized_pl`, `current_price`, `entry_price`) for audit. Not required for correctness.

---

## 5. Files and Code Changes

### 5.1 `Scalp-Engine/auto_trader_core.py`

1. **Constant (near `MIN_PROFIT_PIPS_FOR_TRAILING`):**
   - Add: `ATR_TRAILING_MIN_AGE_SECONDS = 120`

2. **Imports:**  
   - Ensure `pytz` is available for `datetime.now(pytz.UTC)`. (Already used elsewhere in the file.)

3. **`_check_ai_trailing_conversion()` — OPEN branch:**
   - Right after entering `if trade.state == TradeState.OPEN:`:
     - **Time guard:**  
       - Resolve `opened_at` (handle naive vs aware; treat naive as UTC).  
       - If no `opened_at`, log DEBUG “skipping … (no opened_at)” and return.  
       - Compute `time_since_open_seconds`.  
       - If `time_since_open_seconds < ATR_TRAILING_MIN_AGE_SECONDS`, log DEBUG and return.
     - **OANDA P/L gate:**  
       - If `getattr(trade, 'oanda_unrealized_pl', None)` is a number and `trade.oanda_unrealized_pl <= 0`, log DEBUG and return.
     - Then run the existing logic: `min_profit_distance`, `is_long`, `in_profit`, regime, trailing_pips, `convert_to_trailing_stop()`, state update, existing logs.

4. **No changes** to:
   - `monitor_positions()` (it already fetches TradeDetails and sets `trade.oanda_unrealized_pl` for OPEN trades).
   - `convert_to_trailing_stop()` in the executor.
   - BE_TO_TRAILING or TRAILING-state handling.

### 5.2 `Trade-Alerts/improvementplan.md`

- **Status line (top):** Change “Fix 4 remains BLOCKED until Phase 0.5” to “Fix 4 **implemented** (ATR_TRAILING min age + OANDA P/L gate).”
- **Fix 4 section:**  
  - Set status to **Implemented** with a short note: “Phase 0.5 complete; implemented time-based guard (min 120s open) and OANDA unrealized P/L gate in `_check_ai_trailing_conversion()`.”
- **Changelog:** Add entry: “Fix 4 implemented: ATR_TRAILING conversion only after min 120s open and (when available) OANDA unrealized P/L > 0; see ATR_TRAILING_FIX_PLAN.md.”

### 5.3 `personal/cursor_works.md`

- Add a short **Part 16** (or append to an existing “Scalp-Engine” part): “ATR_TRAILING immediate activation fix (Fix 4): Phase 0.5 complete; implemented min age 120s and OANDA P/L gate in `_check_ai_trailing_conversion()`; improvementplan Fix 4 unblocked.”

---

## 6. Verification

- **Unit / manual code check:**  
  - Time guard: with `opened_at` set to “now” or “now - 60s”, conversion is skipped; with “now - 130s”, time gate passes.  
  - OANDA gate: with `oanda_unrealized_pl = -10` or `0`, conversion skipped when we’re in OPEN; with `> 0` and in profit by price, conversion allowed (subject to existing in_profit check).

- **Logs:**  
  - After deploy, trigger an ATR_TRAILING trade and watch logs: in the first 2 minutes you should see DEBUG “skipping … open Ns < min 120s” (and optionally “OANDA unrealized P/L not positive” if OANDA shows loss).  
  - After 2+ minutes and when the trade is actually in profit (and OANDA P/L > 0 if available), you should see “ATR Trailing: attempting conversion …” and “converted to trailing stop”.

- **UI / OANDA:**  
  - New ATR_TRAILING trades should not show “(TRAILING)” in the UI until they have been open for at least 2 minutes **and** are in profit.  
  - OANDA should show the trailing stop order only after that point.

---

## 7. Rollback

- Single cohesive change set: one commit (or a small number of commits) for `auto_trader_core.py`, `improvementplan.md`, and `cursor_works.md`.  
- Rollback: `git revert <commit(s)>` and redeploy. No schema or config changes; no migration.

---

## 8. Summary Table

| Item | Action |
|------|--------|
| **Root cause** | First-cycle conversion using only mid price vs entry; no min age; OANDA P/L not used for the decision. |
| **Time guard** | In `_check_ai_trailing_conversion()`, skip conversion if OPEN and `time_since_open < 120` seconds. |
| **OANDA gate** | Skip conversion if `trade.oanda_unrealized_pl` is set and ≤ 0. |
| **Constant** | `ATR_TRAILING_MIN_AGE_SECONDS = 120` in `auto_trader_core.py`. |
| **Logging** | DEBUG when skipping (too new or OANDA P/L not positive). |
| **Docs** | improvementplan.md: Fix 4 implemented; cursor_works: Part 16 (or equivalent); this plan in ATR_TRAILING_FIX_PLAN.md. |

This plan is intended to be implemented in full as one non-piecemeal change set.
