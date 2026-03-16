# Trading Hours Logic — Full Description

This document describes how trading hours are defined and enforced across the Scalp-Engine trading system. All times in the main engine are **UTC** unless stated otherwise.

---

## 1. Overview

- **Trading window:** Monday 01:00 UTC through Friday 21:30 UTC (weekdays only).
- **No new entries:** Friday 21:00 UTC through Monday 01:00 UTC (weekend shutdown).
- **Runners (Mon–Thu):** Trades with ≥25 pips profit may be held until 23:00 UTC or an EMA crossover exit; non-runners close at 21:30 UTC.
- **Friday:** All trades close at 21:30 UTC (no weekend exposure, no runner exception).
- **Weekend:** No trading; all open trades are expected to be closed (Saturday/Sunday).

---

## 2. Source of Truth: `TradingHoursManager`

**File:** `personal/Trade-Alerts/Scalp-Engine/trading_hours_manager.py`

The central definition of trading hours and close rules lives in `TradingHoursManager`.

### 2.1 Time Constants (UTC)

| Constant | Value | Meaning |
|----------|--------|---------|
| `DAILY_OPEN` | 01:00 | Monday session start |
| `NO_ENTRY_START` | 21:00 | Friday: no new entries from this time (weekend shutdown) |
| `DAILY_CLOSE` | 21:30 | Friday: all positions must be closed by this time |
| `RUNNER_HARD_CLOSE` | 23:00 | Mon–Thu: hard deadline for any remaining trades |
| `RUNNER_THRESHOLD_PIPS` | 25 | Min profit (pips) to treat trade as “runner” (Mon–Thu only) |

Weekday constants: Monday=0, Friday=4, Saturday=5, Sunday=6 (Python `weekday()`).

### 2.2 `should_close_trade(now_utc, profit_pips, trade_direction, df_m5=None, current_spread_pips=0)`

Used to decide whether an **existing** trade should be closed. Evaluation order (priority):

1. **Weekend**
   - Saturday → close (reason: `SATURDAY_MARKET_CLOSED`).
   - Sunday → close (reason: `SUNDAY_CLOSED`).

2. **Friday after 21:30**
   - Close (reason: `FRIDAY_HARD_CLOSE`). No runner exception on Friday.

3. **Mon–Thu after 23:00**
   - Close (reason: `RUNNER_DEADLINE_23:00`).

4. **Daily close window (21:30–23:00 Mon–Thu)**
   - If Friday → close (`FRIDAY_HARD_CLOSE_21:30`).
   - If Mon–Thu and `profit_pips >= 25` (runner):
     - If spread > 5 pips → do not close (reason: `RUNNER_WAITING_BETTER_SPREAD`).
     - If M5 EMA(9)/EMA(26) crossover exit signal → close (`RUNNER_EMA_EXIT`).
     - Else → do not close (reason: `RUNNER_HOLDING`) until 23:00 or crossover.
   - If Mon–Thu and not a runner → close (`DAILY_CLOSE_21:30`).

5. **Before 01:00 on a weekday**
   - Close (reason: `OUTSIDE_TRADING_HOURS`); in normal operation trades should already be closed by 23:00 or 21:30 Friday.

6. **Otherwise**
   - Do not close (reason: `NORMAL_TRADING_HOURS`).

All comparisons use timezone-aware UTC (`pytz.UTC`).

### 2.3 `can_open_new_trade(now_utc)`

Defines when **new** trades are allowed:

- **Saturday** → not allowed (`SATURDAY_CLOSED`).
- **Sunday** → not allowed (`SUNDAY_CLOSED`).
- **Before 01:00 UTC** (e.g. 00:00–00:59 Monday) → not allowed (`BEFORE_DAILY_OPEN`).
- **Friday ≥ 21:00 UTC** → not allowed (`FRIDAY_WEEKEND_SHUTDOWN_21:00`).
- **Friday ≥ 21:30 UTC** → not allowed (`AFTER_FRIDAY_CLOSE`).
- **Otherwise** (Monday 01:00 – Friday before 21:00) → allowed (`ENTRY_ALLOWED`).

**Integration note:** `TradingHoursManager.can_open_new_trade(now_utc)` is **not** called by `PositionManager.can_open_new_trade()`. The engine’s “can we open?” check only uses risk (circuit breaker, daily loss) and max open trades. So time-based entry restriction (Friday 21:00, weekend) is **not** currently enforced at open; it is enforced indirectly by scheduled cleanups and by closing existing trades via `should_close_trade`.

---

## 3. Where Closing Is Enforced

### 3.1 Position Monitoring (Continuous)

**File:** `auto_trader_core.py` — `PositionManager.monitor_positions()`

- Runs every main-loop iteration when in auto-trading mode (after sync and opportunity checks).
- For each open trade (OPEN / TRAILING / AT_BREAKEVEN):
  - Computes unrealized P&L in pips.
  - Instantiates `TradingHoursManager` and calls `should_close_trade(now_utc, pnl_pips, direction_str)`.
  - If `should_close` is True, calls `close_trade(trade_id, reason)`.

So weekend, Friday 21:30, Mon–Thu 21:30/23:00 and runner rules are applied **continuously** via monitoring, as long as the engine is running.

### 3.2 Friday 21:30 UTC — End-of-Week Cleanup

**File:** `scalp_engine.py` — main loop

- **Condition:** `weekday == 4` (Friday) and `current_hour_utc == 21` and `current_minute_utc >= 30` and `last_end_of_day_cleanup_date != current_date_utc`.
- **Action:** Calls `position_manager._end_of_day_cleanup(reason="Friday 21:30 UTC - End of trading week")` once per Friday.
- **Inside cleanup (`auto_trader_core.py`):**
  1. Sync with OANDA so in-memory state matches broker.
  2. Cancel all pending orders (in-memory and on OANDA, including orphan handling).
  3. Close **all** open trades present in `active_trades` (OPEN/TRAILING/AT_BREAKEVEN).
  4. Persist state.

This guarantees that by Friday 21:30 UTC the engine attempts to flatten everything, independent of runner logic.

### 3.3 Weekend (Saturday / Sunday)

**File:** `scalp_engine.py` — main loop

- **Condition:** `weekday in [5, 6]` (Saturday or Sunday).
- **Action:**
  - Log “WEEKEND SHUTDOWN - No trading allowed”.
  - Call `position_manager.cancel_all_pending_orders(reason="Weekend shutdown - cancel all pending orders")`.
  - **Open trades:** Not closed in this block. Comment states: “Close all open trades (monitoring will handle this via should_close_trade)”. So any remaining open trades are closed by the **monitoring** path when `should_close_trade` returns True for Saturday/Sunday.

So weekend enforcement is: cancel pendings in the main loop; rely on `monitor_positions()` + `should_close_trade()` to close any open positions.

### 3.4 Monday 01:00 UTC — Start-of-Week Safety

**File:** `scalp_engine.py` — main loop

- **Condition:** `weekday == 0` (Monday) and `current_hour_utc == 1` and `current_minute_utc < 2` and `last_start_of_day_cleanup_date != current_date_utc`.
- **Action:** Cancel any remaining pending orders (`reason="Start of trading week - cancel stale pending orders (safety check)"`). No explicit “open trade” close; any stragglers would still be closed by monitoring if they fall outside trading hours.

---

## 4. “In Trading Hours” in the Main Loop

**File:** `scalp_engine.py` — used for Fisher scan and periodic sync

```text
in_trading_hours =
  (weekday in (1,2,3))   # Tue, Wed, Thu: full day
  OR (weekday == 0 and (hour > 1 or (hour == 1 and minute >= 0)))   # Mon from 01:00
  OR (weekday == 4 and (hour < 21 or (hour == 21 and minute <= 30))) # Fri until 21:30
```

- **Hourly Fisher scan:** Runs when `in_trading_hours` and `current_minute_utc < 2` and not already run for `(current_date_utc, current_hour_utc)`.
- **Hourly periodic sync check:** Same time condition (or when manual sync is requested via UI trigger file).

So “trading hours” for these scheduled tasks is Monday 01:00 UTC through Friday 21:30 UTC (inclusive of the 21:30 minute).

---

## 5. Entry Checks in the Engine

**File:** `auto_trader_core.py` — `PositionManager.can_open_new_trade()`

This method does **not** use `TradingHoursManager`. It only checks:

- Circuit breaker (consecutive losses).
- Daily loss limit (e.g. max daily loss %).
- Max open trades (in-memory and OANDA count; only OPEN/TRAILING/AT_BREAKEVEN count toward the limit).

So **time-of-day and day-of-week** (Friday 21:00, weekend) are **not** enforced here. The only time-based prevention of new trades is:

- Friday 21:30 cleanup and weekend behavior (no new positions opened if the engine has already closed/cancelled and no new signals are acted upon), and
- The fact that opportunity checks run in the same loop that does cleanup and sync (so behaviour depends on order and timing).

If the engine were to evaluate an opportunity on Saturday or Friday after 21:00, it would currently rely on other checks (e.g. no signal, or max trades), not on an explicit “within trading hours” gate from `TradingHoursManager.can_open_new_trade(now_utc)`.

---

## 6. FT-DMI-EMA Module (Separate Session Config)

**File:** `src/ft_dmi_ema/signal_generator_ft_dmi_ema.py`, `src/ft_dmi_ema/ft_dmi_ema_config.py`

The FT-DMI-EMA strategy uses its own **SessionConfig**, independent of `TradingHoursManager`:

- `APPROVED_HOURS_START` = 08:00  
- `APPROVED_HOURS_END`   = 20:00  
- `FRIDAY_CUTOFF`        = 16:00  
- `SUNDAY_BUFFER_HOURS`  = 4  

`_is_approved_session(current_time)` returns False if:

- Time is outside 08:00–20:00, or  
- It’s Friday and time ≥ 16:00, or  
- It’s Sunday and time is within the first `SUNDAY_BUFFER_HOURS` hours.

The config does not specify timezone; typically this would be server local or a configured timezone. This is **separate** from the main engine’s UTC-based trading hours.

---

## 7. Summary Table (Main Engine — UTC)

| Period / Rule | New entries | Existing trades | Scheduled actions |
|---------------|-------------|-----------------|-------------------|
| Mon 01:00 – Fri 21:00 | Allowed (by THM; not enforced in `can_open_new_trade()`) | Closed only by SL/TP/trailing/runner/EMA/max hold | Fisher scan, periodic sync when in trading hours |
| Fri 21:00 – 21:30 | No (per THM); engine does not enforce | Close via monitoring (e.g. 21:30 rule) | — |
| Fri 21:30 | No | All closed (cleanup + monitoring) | **End-of-week cleanup** once (sync, cancel pendings, close all opens) |
| Sat / Sun | No | Close (monitoring: weekend reason) | Cancel all pending; monitoring closes any opens |
| Mon 00:00 – 01:00 | No | Close (outside hours) | — |
| Mon 01:00 | — | — | **Start-of-week safety**: cancel stale pendings |
| Mon–Thu 21:30 – 23:00 | — | Non-runners closed; runners until 23:00 or EMA exit | — |
| Mon–Thu 23:00 | — | All closed | — |

---

## 8. File Reference

| File | Role |
|------|------|
| `trading_hours_manager.py` | Defines `TradingHoursManager`: constants, `should_close_trade()`, `can_open_new_trade()` (UTC). |
| `auto_trader_core.py` | Uses `should_close_trade()` in `monitor_positions()`; `can_open_new_trade()` (no time check); `_end_of_day_cleanup()`. |
| `scalp_engine.py` | Main loop: weekend block, Friday 21:30 cleanup, Monday 01:00 safety, `in_trading_hours` for Fisher and periodic sync. |
| `src/ft_dmi_ema/ft_dmi_ema_config.py` | `SessionConfig`: 08:00–20:00, Friday 16:00 cutoff, Sunday buffer (separate from main engine). |
| `src/ft_dmi_ema/signal_generator_ft_dmi_ema.py` | `_is_approved_session()` using `SessionConfig`. |
