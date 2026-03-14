# Comprehensive Plan: Review-and-Replace Pending Trades Bug Fix

**Context:** The trade was set up on OANDA as a **LIMIT** pending order. The engine’s “review and replace” logic cancelled that pending LIMIT to replace it with a “better” entry; the replacement order was then rejected by `max_runs`, so the user ended up with **no** order (cancelled, nothing new placed).

**Scope:** Single comprehensive plan. No piecemeal changes. Implementation only after your approval.

---

## Part 1: Codebase Review – Where Review-and-Replace Logic Is Used

### 1.1 Primary usage: `_review_and_replace_pending_trades`

| Location | File | Line(s) | Role |
|----------|------|---------|------|
| **Definition** | `scalp_engine.py` | 2151–2372 | Defines the full review-and-replace logic (stale cancel + replace with better price/size). |
| **Single call site** | `scalp_engine.py` | 954–955 | Called from `_check_new_opportunities(market_state)` at the start of the opportunity check, before any opportunity is processed. |

**Call chain:**

1. Main loop: `run_once()` (or equivalent) → `_check_new_opportunities(market_state)`.
2. `_check_new_opportunities`:
   - First calls `self._review_and_replace_pending_trades(opportunities)` (line 955).
   - Then iterates over `opportunities` and, for each, may call `_maybe_reset_run_count_and_open_trade` → `position_manager.open_trade(...)`.

**Order of operations in the main loop (scalp_engine, ~904–928):**

1. `sync_with_oanda(market_state)` – syncs active_trades with OANDA (open positions + pending orders).
2. `_check_new_opportunities(market_state)` – which runs **review-and-replace** then processes LLM opportunities.
3. `_check_fisher_opportunities`, `_check_ft_dmi_ema_opportunities`, activation checks, HYBRID MACD, `_monitor_positions`, etc.

So **review-and-replace runs once per cycle**, inside `_check_new_opportunities`, and **before** the loop that opens new trades for each opportunity.

### 1.2 What `_review_and_replace_pending_trades` does (current behavior)

- **Input:** `opportunities` (list of current market-state opportunities).
- **Steps:**
  1. Builds `pending_trades` = all entries in `position_manager.active_trades` with `trade.state == TradeState.PENDING` (i.e. LIMIT/STOP orders not yet filled).
  2. For each pending trade:
     - **Stale check:** If entry price is too far from current market (e.g. >50 pips for non-JPY, >100 for JPY), **cancels** the order and removes it from `active_trades`. Does **not** place a new order.
     - **Replace check:** Otherwise, finds “best” opportunity for the **same pair** (any direction) in `opportunities`. If a better entry (≥1 pip) and/or different position size is found, sets `should_replace = True`.
  3. When `should_replace`:
     - **Cancels** the existing pending order via `position_manager.executor.cancel_order(...)`.
     - **Removes** the trade from `position_manager.active_trades`.
     - **Does not place** the new order itself; the docstring says “new order will be created” by “normal opportunity processing.”
  4. Later in the same cycle, the **for opp in opportunities** loop runs; for that pair, `open_trade(opp, ...)` is called. The enforcer’s `get_execution_directive` runs and checks `max_runs`; **run_count was already incremented when the original LIMIT was placed**, so the directive is **REJECT** (“Exceeded max_runs (1)”). So **no** new order is created.

**Result:** Pending LIMIT is cancelled, replacement is never placed → user has no order.

### 1.3 Other places that cancel pending orders (for completeness)

| Location | File | When | Purpose |
|----------|------|------|---------|
| `_review_and_replace_pending_trades` | scalp_engine.py | Every opportunity check | Stale cancel + replace (cancel only; replace relies on main loop). |
| `_check_hybrid_macd_triggers` | scalp_engine.py | When MACD crossover detected for HYBRID | Cancel pending order and open at market. |
| `sync_with_oanda` | auto_trader_core.py | Every sync | Does **not** cancel; removes from `active_trades` if order not in OANDA pending list (and now: if not filled → see filled-handling below). |
| `cancel_all_pending_orders` | auto_trader_core.py | Weekend / Friday EOD / Monday safety | Cancels all tracked PENDING orders. |
| `phase2_cleanup.py` | scripts/ | Manual script | Cancels all pending orders. |

Only **review-and-replace** both cancels and intends to “replace” with a new order in the same cycle; that replacement is broken by `max_runs`.

### 1.4 How `max_runs` interacts with replace

- **When run_count is incremented:** In `auto_trader_core.open_trade`, **as soon as** `self.executor.open_trade(trade)` succeeds (line 983–988), the code calls `self.execution_enforcer.record_execution(opp_id)`. So **placing** a LIMIT (or any order) counts as one “run” for that `opp_id` (stable key: e.g. `GBP/JPY_SHORT`).
- **Replace flow:** Same pair/direction → same `opp_id`. After cancel, run_count for that `opp_id` is still 1. The main loop then tries to open the same opportunity again → enforcer sees run_count >= max_runs (e.g. 1 >= 1) → REJECT. So the “replace” never becomes a new order.

### 1.5 Sync fix (already in codebase)

- In `auto_trader_core.sync_with_oanda`, when a PENDING trade’s order ID is **not** in OANDA’s pending list, the code now checks for a **matching open position** (same pair/direction/units). If found, the trade is updated to OPEN and re-keyed by position ID; it is **not** removed. So a **filled** LIMIT is no longer treated as “cancelled.” This is correct and stays as-is.

---

## Part 2: Root Cause Summary

1. **Review-and-replace** cancels a pending LIMIT and then **relies on the main opportunity loop** to place the new order.
2. **Run count** is consumed when the **original** LIMIT is placed, so the same opportunity is already at max_runs.
3. The main loop therefore **rejects** opening the “replacement” trade, and **no** new order is created.
4. Net effect: pending LIMIT is removed, user is left with no order for that pair.

---

## Part 3: Comprehensive Fix (Single Plan)

### 3.1 Design principle

- **Replace = same “run” as the original order.** Replacing a pending order with a better price/size should not consume an extra run. So when we cancel and replace, we must **place the new order inside the replace path** and **not** increment run_count again (or equivalently, treat the replace as the same run).

### 3.2 Option A (recommended): Place new order inside replace path without recording run

- **In `_review_and_replace_pending_trades`:** When we decide to **replace** (better entry and/or size, **not** just stale cancel):
  1. Cancel the existing pending order and remove it from `active_trades` (as today).
  2. **Immediately** create and place the new order using the **best_opp** we already computed, by calling into the same execution path as the main loop (e.g. build trade from `best_opp`, call `position_manager.executor.open_trade(trade)`), but **do not** call `execution_enforcer.record_execution(opp_id)` for this placement.
  3. If the new order is placed successfully, add the new trade to `active_trades` and save state (same as `open_trade` does). If it fails, log and leave the user with no order for that pair (current behavior), but at least we tried.

- **Implementation requirements:**
  - **`position_manager.open_trade`** (auto_trader_core): Add an optional parameter, e.g. `record_run: bool = True`. When `record_run=False`, do **not** call `self.execution_enforcer.record_execution(opp_id)` after a successful `open_trade`; still perform all other steps (create trade, executor.open_trade, add to active_trades, RL log, _save_state).
  - **`_review_and_replace_pending_trades`** (scalp_engine): After cancelling the old order and removing it from `active_trades`, build the opportunity dict for the **best_opp** (pair, direction, entry, units, execution_config, etc.) and call `position_manager.open_trade(best_opp, market_state, record_run=False)`. Use the same `market_state` as the rest of the cycle (e.g. pass it into `_check_new_opportunities` if not already available, or ensure `_review_and_replace_pending_trades` has access to it). Only call when we actually replaced (same pair; better price or size); do not call for stale-only cancels.

- **Stale-only path:** When we only **cancel** because the order is stale (too far from market), we do **not** place a new order (current behavior). No change.

### 3.3 Option B: Decrement run_count when cancelling for replace

- When we cancel an order **for replace** (not for stale), decrement run_count for that opportunity’s `opp_id` (e.g. `execution_enforcer.decrement_run_count(opp_id)` or “undo last execution”). Then the main loop can place the new order and will record execution again (run_count goes back to 1).
- **Downside:** Requires a new “decrement” or “undo” in execution history; slightly more stateful and error-prone (e.g. double-decrement if logic is wrong). Option A keeps “run” semantics clearer: one run = one order placement, and replace is the same run.

### 3.4 Recommendation

- **Use Option A:** Place the new order inside `_review_and_replace_pending_trades` with `record_run=False`. No change to run_count semantics elsewhere; only the replace path avoids recording a second run.

---

## Part 4: Concrete Implementation Steps (Option A)

1. **`auto_trader_core.py` – `open_trade`**
   - Add parameter: `record_run: bool = True`.
   - After a successful `order_or_trade_id = self.executor.open_trade(trade)`, only call `self.execution_enforcer.record_execution(opp_id)` when `record_run` is True. All other behavior (trade creation, active_trades update, RL log, _save_state) unchanged.

2. **`scalp_engine.py` – `_check_new_opportunities`**
   - Ensure `_review_and_replace_pending_trades` is called with whatever it needs to place an order. Currently it receives `opportunities`. It needs `market_state` to call `open_trade(opp, market_state, record_run=False)`. So change the signature to `_review_and_replace_pending_trades(self, opportunities, market_state)` and pass `market_state` from `_check_new_opportunities`.

3. **`scalp_engine.py` – `_review_and_replace_pending_trades`**
   - Add parameter: `market_state: Dict` (default `None`). If `market_state` is None, do not attempt to place a new order on replace (fallback: current behavior – cancel only).
   - In the “replace” branch, after cancelling and removing the old trade:
     - Build a single opportunity dict from `best_opp` that matches what `open_trade` expects (pair, direction, entry, execution_config, current_price, order_type from directive, etc.). Reuse the same logic as the main loop for building the opportunity (e.g. entry = best_entry, direction = opp_direction, units = new_units).
     - Get execution directive for this opportunity (same as main path: current_price, get_execution_directive). If directive is REJECT or WAIT_SIGNAL, do not place (log and skip).
     - If directive is PLACE_PENDING or EXECUTE_NOW, create the managed trade (reuse `_create_trade_from_opportunity`-style logic or call into position_manager so we don’t duplicate). Call `position_manager.open_trade(opp, market_state, record_run=False)`.
     - Handle return value: if open_trade returns a trade, the new order is in active_trades; if None, log failure.
   - Ensure we do not double-place: we’ve already removed the old trade from active_trades, so the “one order per pair” check in open_trade will not see a duplicate. Still respect can_open_new_trade() (e.g. max open trades).

4. **Call site**
   - In `_check_new_opportunities`, change to: `self._review_and_replace_pending_trades(opportunities, market_state)`.

5. **Testing**
   - Scenario 1: Place a LIMIT for pair X; next cycle, opportunity for X has a “better” entry (e.g. 1+ pip). Expect: old order cancelled, new order placed at new price, run_count still 1 for that opp_id.
   - Scenario 2: Same but max_runs = 1. Expect: same as above (no REJECT).
   - Scenario 3: Stale only (no better opportunity). Expect: order cancelled, no new order (current behavior).
   - Scenario 4: Replace with different direction for same pair. Then opp_id changes; we’re effectively “replacing” with a new opportunity. We can either allow that (place new order and do **not** record run for the **new** opp_id if we consider it the same “slot”) or treat direction change as a new run. Plan: treat direction change as a new run – i.e. when replacing with a **different** direction, call `open_trade(..., record_run=True)` so the new direction gets its own run. When same direction, `record_run=False`.

Clarification for direction change: if `best_opp` has a different direction than the current pending trade, we are replacing pair X from e.g. SHORT to LONG. That could be considered one “replace” (same pair, one order) and not consume an extra run for the new direction. To keep semantics simple, the plan can state: **on replace, always use `record_run=False`** so that we never double-count; the “run” was the first order (the one we cancelled). So even if direction changes, we do not record again. That way we only ever have one order per pair at a time, and one “run” per replace event. (If you prefer direction change to count as a new run, we can specify that instead.)

---

## Part 5: Summary Table

| Item | Current behavior | After fix (Option A) |
|------|------------------|----------------------|
| Replace (same or different direction) | Cancel old order; rely on main loop to place new; main loop rejects (max_runs). | Cancel old order; **place new order inside replace** with `record_run=False`; run_count unchanged; user has new order. |
| Stale cancel | Cancel, no new order. | Unchanged. |
| Run count | Incremented when any order is placed (including LIMIT). | Same; replace does not increment again. |
| Sync (PENDING not in list) | Now: if matching open position, update to OPEN. | Unchanged. |

---

## Part 6: Files to Touch

| File | Change |
|------|--------|
| `auto_trader_core.py` | Add `record_run: bool = True` to `open_trade`; call `record_execution` only when `record_run` is True. |
| `scalp_engine.py` | (1) Add `market_state` to `_review_and_replace_pending_trades` and pass it from `_check_new_opportunities`. (2) In replace branch: build opp from best_opp, get directive, call `position_manager.open_trade(opp, market_state, record_run=False)` and handle result. |

---

**End of plan. Awaiting your approval before implementation.**
