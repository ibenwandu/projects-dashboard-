# Trade-Alerts Improvement Plan
**Date**: March 5, 2026 | **Target**: Today
**Source**: Analysis of suggestions_from_anthropic6.md + codebase exploration
**Status**: Fixes 1–3 **implemented** (see Deployment Order). Fix 4 **implemented** (ATR_TRAILING min age + OANDA P/L gate).

---

## Executive Summary

Codebase exploration confirmed the root causes of the two biggest blockers:

| Issue | Finding | Fix |
|-------|---------|-----|
| **max_runs blocks 97% of trades** | `reset_run_count()` doesn't clear the legacy-format key; reset silently does nothing | Fix `reset_run_count()` to also clear legacy key |
| **80% premature closures** | MACD reverse-crossover check fires on ALL trades every 60s regardless of `sl_type` | Guard MACD close with `sl_type == MACD_CROSSOVER` check |
| **JPY MARKET order unguarded** | Sanity check only applies to LIMIT/STOP orders, skips MARKET | Extend check to MARKET orders |
| **Trailing SL broken in practice** | Code uses correct endpoint (`OrderCreate` with `TRAILING_STOP_LOSS`), but user confirms not working | Investigate via logs before fixing |

---

## Phase 0: Investigation Findings (Completed — No Code Changes)

### Finding 0.2 — Premature Closure Root Cause

**`scalp_engine.py` lines 3155–3162** contains a MACD reverse-crossover check that runs on **all open trades every 60 seconds**, regardless of their configured `sl_type`:

```python
for trade_id, trade in list(self.position_manager.active_trades.items()):
    if trade.state == TradeState.OPEN:
        if self.position_manager.check_macd_reverse_crossover(trade, self.oanda_client):
            self.position_manager.close_trade(
                trade_id, f"MACD reverse crossover - {trade.pair} {trade.direction}"
            )
```

Trades with `ATR_TRAILING`, `BE_TO_TRAILING`, or `STRUCTURE_ATR_STAGED` sl_types are being incorrectly closed by MACD signals intended only for `MACD_CROSSOVER` strategy trades. This is the most likely cause of 80% premature closures.

Other closures that are **by design** and should **not** be changed:
- Trading hours manager: closes non-runners (<25 pip profit) at 21:30 UTC Mon–Thu
- End-of-day cleanup: Friday 21:30 UTC close all
- System restart: Render redeploy closes all active trades

### Finding 0.3 — max_runs Reset Silent Failure

The auto-reset logic IS present in `auto_trader_core.py` (lines 1127–1160). Root cause of failure is in `execution_mode_enforcer.py`:

`reset_run_count()` (lines 485–502) only deletes by the **exact** new-format key (e.g., `LLM_EUR/USD_LONG`). However, `_get_run_count()` has a legacy-key fallback:
```python
# _get_run_count() reads the legacy key if new key has count=0
if count == 0 and '_' in opp_id:
    legacy_key = opp_id.split('_', 1)[-1]   # → "EUR/USD_LONG"
    count = self.execution_history.get(legacy_key, {}).get('count', 0)
```

Execution history entries were recorded under the legacy format (`EUR/USD_LONG`). When reset is called with `LLM_EUR/USD_LONG`, `reset_run_count()` finds nothing to delete, silently exits, and `_get_run_count()` still finds the old entry via the fallback. Trade stays permanently blocked.

### Finding 0.4 — JPY Sanity Check Gap

`round_price_for_oanda()` correctly rounds JPY to 3 decimal places. A JPY price sanity check exists (`TradeExecutor.open_trade()` lines 341–363), but it is inside the `if order_type in ('LIMIT', 'STOP'):` branch — MARKET orders skip it entirely.

### Finding 0.5 — Trailing SL Code Looks Correct But Is Broken in Practice

Code review shows the correct OANDA endpoint (`OrderCreate` with `TRAILING_STOP_LOSS` type, **not** `TradeClientExtensions`). Pre-flight deduplication and error handling are present. However, user confirms trailing SL is not working correctly in live trading.

**Possible causes not visible in code review alone**:
1. Trailing stop created but OANDA silently ignores or rejects it
2. Pre-flight check incorrectly detecting an existing trailing stop and skipping creation
3. Trailing distance calculated in wrong units for certain pairs
4. Race condition between fixed SL cancellation and trailing stop creation
5. `ALREADY_EXISTS` being treated as success when the existing order is a stale/wrong trailing stop

**Must investigate via log files before fixing** (see Phase 0.5 below).

---

## Phase 0.5: ATR_TRAILING Immediate Activation Bug (CRITICAL)

**User Observation**: ATR_TRAILING activates **immediately when trade opens**, not when trade reaches profit/breakeven as code intends.

**Evidence**: GBP/USD SELL trade shows +39.5 pips in UI (chart shows loss), with 10.47 pip trailing stop set immediately at entry.

**Code Intent vs Reality**:
- **Code** (lines 2282–2290): Only convert to trailing when `in_profit` (trade > 1 pip profit)
- **Reality**: Trailing stop activated immediately even when trade opens in loss
- **Symptom**: P&L discrepancy (UI shows historical profit, current snapshot shows loss)

**Root Cause Hypothesis**:
1. `_check_ai_trailing_conversion()` called with stale `current_price` showing profit when actual price is in loss
2. Price sync lag between engine and OANDA creates false "in profit" condition
3. First monitoring cycle after trade open uses entry_price as current_price, triggering conversion incorrectly

**Investigation Steps**:

1. **Find an ATR_TRAILING trade that opened in loss** (via logs)
   - Look for: `created.*ATR_TRAILING`
   - Note the entry_price and timestamp

2. **Check when trailing conversion was triggered**
   - Search logs for: `ATR Trailing: attempting conversion`
   - Note the timestamp and current_price value
   - Compare current_price to OANDA's actual price at that moment

3. **Verify OANDA has the trailing stop**
   - Check `oanda_transactions_*.csv` for that trade
   - Confirm `TRAILING_STOP_LOSS_ORDER` appears
   - Check distance value against code calculation

4. **Check monitoring cycle timing**
   - Was the conversion triggered in the FIRST monitoring cycle after trade opened?
   - What was the price passed to `_check_ai_trailing_conversion()`?
   - Did monitoring run before trade filled completely?

5. **Identify the price sync issue**
   - How often is `current_prices` dict updated?
   - Is it lagging behind OANDA actual prices by multiple cycles?
   - Are PENDING orders using stale prices during their fill period?

**Fix Strategy** (after investigation):
- May need to delay first ATR_TRAILING conversion check by 1-2 monitoring cycles
- May need to fetch current price from OANDA instead of relying on broadcast prices
- May need to add logging: `current_price vs actual_oanda_price` during conversion

---

## Phase 0.6: Trailing SL Log Investigation (Do After Phase 0.5 if needed)

**What to look for in Scalp-Engine logs**:

1. **Is `convert_to_trailing_stop()` being called?**
   - Search logs for: `ATR Trailing`, `convert_to_trailing_stop`, `TRAILING_STOP_LOSS`
   - If absent: function is not being reached (condition check fails before call)

2. **Is the pre-flight check blocking creation?**
   - Search logs for: `already has trailing stop`, `ALREADY_EXISTS`, `skipping`
   - If present: pre-flight check is incorrectly detecting an existing trailing stop

3. **Is there a OANDA API error?**
   - Search logs for: `TrailingStopLoss`, `error`, `failed`, `TRADE_ORDER_NOT_CLOSEABLE`
   - If present: OANDA is rejecting the trailing stop creation

4. **Cross-reference with OANDA transactions**:
   - Find trades that should have trailing SL (ATR_TRAILING or BE_TO_TRAILING sl_type)
   - Check OANDA transaction history for `TRAILING_STOP_LOSS_ORDER` entries
   - If no trailing stop entries exist for these trades, API call is failing

5. **Check the distance value**:
   - Search logs for: `trailing distance`, `distance =`
   - For a 20-pip stop on USD/JPY: should be `0.200` (20 × 0.01)
   - For a 20-pip stop on EUR/USD: should be `0.00200` (20 × 0.0001)
   - If distance is near-zero or very large, calculation is wrong

**Outcome**: Document findings and propose specific code fix based on actual failure mode. Do not implement Fix 4 until this investigation is complete.

---

## Fix 1 — max_runs Legacy Key in reset_run_count()

**File**: `Scalp-Engine/src/execution/execution_mode_enforcer.py`
**Lines**: 485–502
**Risk**: LOW — only changes when reset succeeds; cannot cause trades to fail to open

**Current code**:
```python
def reset_run_count(self, opp_id: str):
    if opp_id in self.execution_history:
        del self.execution_history[opp_id]
        self._save_execution_history()
        self.logger.info(f"🔄 Reset run count for {opp_id}")
```

**Proposed change** — mirror `_get_run_count()` legacy fallback in the delete path:
```python
def reset_run_count(self, opp_id: str):
    deleted = False
    # Clear exact key (new format: LLM_EUR/USD_LONG)
    if opp_id in self.execution_history:
        del self.execution_history[opp_id]
        deleted = True
    # Also clear legacy key (old format: EUR/USD_LONG) — mirrors _get_run_count() fallback
    if '_' in opp_id:
        legacy_key = opp_id.split('_', 1)[-1]
        if legacy_key in self.execution_history:
            del self.execution_history[legacy_key]
            deleted = True
    if deleted:
        self._save_execution_history()
        self.logger.info(f"🔄 Reset run count for {opp_id} (legacy key also cleared)")
    else:
        self.logger.debug(f"Reset run count: no entry found for {opp_id}")
```

**Verification after deploy**:
- Look for log line: `🔄 Reset run count for LLM_GBP/JPY_SELL (legacy key also cleared)`
- Previously blocked pair (e.g., GBP/JPY SELL) should open on retry within 2 cycles
- Count of `reason=max_runs` in logs should fall from ~97% to <20% of rejections

---

## Fix 2 — MACD Blanket Close Restricted to MACD_CROSSOVER Trades

**File**: `Scalp-Engine/scalp_engine.py`
**Lines**: 3155–3162 (MACD reverse-crossover block in `_monitor_positions()`)
**Risk**: LOW-MEDIUM — removes an incorrect close trigger; MACD_CROSSOVER trades unaffected

**Current code**:
```python
for trade_id, trade in list(self.position_manager.active_trades.items()):
    if trade.state == TradeState.OPEN:
        if self.position_manager.check_macd_reverse_crossover(trade, self.oanda_client):
            self.position_manager.close_trade(
                trade_id,
                f"MACD reverse crossover - {trade.pair} {trade.direction}"
            )
```

**Proposed change** — add `sl_type` guard so only intended strategy trades close on MACD:
```python
for trade_id, trade in list(self.position_manager.active_trades.items()):
    if trade.state == TradeState.OPEN:
        # Only close on MACD signal for trades whose exit strategy is MACD_CROSSOVER
        if trade.sl_type == StopLossType.MACD_CROSSOVER:
            if self.position_manager.check_macd_reverse_crossover(trade, self.oanda_client):
                self.position_manager.close_trade(
                    trade_id,
                    f"MACD reverse crossover - {trade.pair} {trade.direction}"
                )
```

**Prerequisite**: Verify `StopLossType` is imported in `scalp_engine.py`. If not, add:
```python
from auto_trader_core import StopLossType
```

**Verification after deploy**:
- Trades with `ATR_TRAILING` or `BE_TO_TRAILING` sl_type should no longer close on MACD signals
- Trades with `MACD_CROSSOVER` sl_type should still close correctly
- Monitor premature closure percentage — should drop significantly from 80%

---

## Fix 3 — JPY Sanity Check Extended to MARKET Orders

**File**: `Scalp-Engine/auto_trader_core.py`
**Lines**: 341–363 (`TradeExecutor.open_trade()` sanity check block)
**Risk**: LOW — adds a guard for bad input; correct prices pass through unchanged

**Current code structure**:
```python
def open_trade(self, pair, direction, entry_price, ...):
    ...
    if order_type in ('LIMIT', 'STOP'):
        # JPY sanity check runs here ← only for LIMIT/STOP
        if 'JPY' in pair.upper() and entry_price < 10:
            ...
        # rest of LIMIT/STOP order build
    elif order_type == 'MARKET':
        # No sanity check here ← MARKET orders unprotected
        ...
```

**Proposed change** — move the JPY sanity check before the `if order_type` branch so it applies to all order types:
```python
def open_trade(self, pair, direction, entry_price, ...):
    ...
    # JPY price sanity check — applies to ALL order types
    if 'JPY' in pair.upper() and entry_price > 0 and entry_price < 10:
        if take_profit and take_profit > 10:
            entry_price = round(entry_price * 100, 3)
            self.logger.warning(
                f"JPY price auto-corrected: {pair} entry scaled to {entry_price}"
            )
        else:
            self._last_reject_reason = "validation_failed"
            self.logger.error(
                f"JPY price sanity check failed: {pair} entry={entry_price} (expected 100+)"
            )
            return None

    if order_type in ('LIMIT', 'STOP'):
        # existing LIMIT/STOP logic (remove duplicate JPY check if present)
        ...
    elif order_type == 'MARKET':
        # existing MARKET logic
        ...
```

**Verification after deploy**:
- Normal JPY MARKET orders (entry ~156.xx) open without issue
- A hypothetically wrong-scaled JPY entry (1.56) is rejected with log message
- No regression on non-JPY orders or existing LIMIT/STOP JPY logic

---

## Fix 4 — ATR_TRAILING Immediate Activation

**Status**: **Implemented** (March 6, 2026). Phase 0.5 investigation completed; root cause confirmed (first-cycle conversion on stale/favorable tick; no min age; OANDA P/L not used).

**What was implemented** (see `Scalp-Engine/ATR_TRAILING_FIX_PLAN.md`):
1. **Time-based guard:** In `_check_ai_trailing_conversion()`, for OPEN trades we skip conversion if `time_since_open < ATR_TRAILING_MIN_AGE_SECONDS` (120s). Requires `trade.opened_at`; if missing, skip and log at DEBUG.
2. **OANDA unrealized P/L gate:** When `trade.oanda_unrealized_pl` is set and ≤ 0, skip conversion (log at DEBUG). Conversion only when OANDA shows positive unrealized P/L or value is unavailable.
3. Existing `in_profit` check (current_price vs entry_price) unchanged; it runs after both gates pass.

---

## Fix 5 — Trailing SL (Pending Investigation - Phase 0.6)

**Status**: BLOCKED — only after Phase 0.5 & Fix 4 if needed.

**Do not implement until**:
1. Phase 0.5 (ATR_TRAILING) is resolved
2. Phase 0.6 log investigation completed
3. Specific trailing SL failure identified

**Placeholder**: After Phase 0.6, this section will be filled in with the specific code change needed.

---

## Deployment Order

Implement one fix at a time. Verify each before moving to the next.

**CRITICAL**: Complete Phase 0.5 (ATR_TRAILING investigation) BEFORE any other fixes, as it affects trailing behavior system-wide.

| Step | Action | Wait | Verify |
|------|--------|------|--------|
| 0 | **Complete Phase 0.5 investigation** | — | Identify why ATR_TRAILING activates immediately |
| 1 | Deploy Fix 1 (max_runs legacy key) | 2–4 hours | `reason=max_runs` drops; blocked pairs retry |
| 2 | Deploy Fix 2 (MACD blanket close) | 2–4 hours | Premature closures drop; ATR_TRAILING trades hold |
| 3 | Deploy Fix 3 (JPY MARKET sanity) | 1 hour | JPY MARKET orders work; bad-scale orders rejected |
| 4 | Deploy Fix 4 (ATR_TRAILING fix, if needed after 0.5) | 2–4 hours | ATR_TRAILING only activates when actually in profit |
| 5 | Implement Phase 0.6 trailing SL investigation (if needed) | — | Document any remaining trailing SL issues |

---

## Success Criteria

### Phase 0.5 Success (Investigation - HIGHEST PRIORITY)
- ✅ Identified why ATR_TRAILING activates immediately
- ✅ Confirmed price sync issue (or other root cause)
- ✅ Proposed specific fix strategy

### Phase 1+ Success (Fixes - After Phase 0.5 Complete)
| Metric | Before | Target |
|--------|--------|--------|
| max_runs rejections | 97% of attempts | <20% |
| Execution rate | 3% | 20%+ |
| Premature closures | 80% of fills | <30% |
| JPY MARKET safety | Unguarded | Sanity-checked |
| ATR_TRAILING behavior | Activates immediately | Only when in profit |
| Trailing SL | Status TBD | Investigated & working |

---

## Rollback

Each fix is a separate commit. To rollback any fix:
```bash
git revert <commit-hash>
git push origin main
```
Render auto-redeploys. Trading resumes within 5 minutes.

---

## Files to Modify

| File | Fix | Lines |
|------|-----|-------|
| `Scalp-Engine/src/execution/execution_mode_enforcer.py` | Fix 1 — max_runs legacy key | 485–502 |
| `Scalp-Engine/scalp_engine.py` | Fix 2 — MACD blanket close | 3155–3162 |
| `Scalp-Engine/auto_trader_core.py` | Fix 3 — JPY MARKET sanity check | 341–363 |
| `Scalp-Engine/auto_trader_core.py` | Fix 4 — ATR_TRAILING min age + OANDA P/L gate in `_check_ai_trailing_conversion()` | Implemented |

---

## Changelog (implementation)

- **Fix 1 implemented:** `execution_mode_enforcer.py` — `reset_run_count()` now clears both new-format and legacy key; logs "(legacy key also cleared)" or DEBUG when no entry found.
- **Fix 2 implemented:** `scalp_engine.py` — MACD reverse-crossover close guarded with `trade.sl_type == StopLossType.MACD_CROSSOVER`; only those trades are closed on MACD signal.
- **Fix 3 implemented:** `auto_trader_core.py` — JPY sanity check (entry < 10, scale or reject) moved before `order_type` branch; applies to MARKET, LIMIT, and STOP. Invalid JPY entry rejected with "JPY price sanity check failed"; auto-correction when TP > 10.
- **Fix 4 implemented:** `auto_trader_core.py` — ATR_TRAILING conversion only after trade OPEN ≥120s (`ATR_TRAILING_MIN_AGE_SECONDS`) and (when available) OANDA unrealized P/L > 0; time and OANDA gates at start of OPEN branch in `_check_ai_trailing_conversion()`. See `Scalp-Engine/ATR_TRAILING_FIX_PLAN.md`.
