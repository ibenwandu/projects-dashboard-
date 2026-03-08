# Fisher Transform Activation Logic

This document explains how Fisher opportunities are executed when you choose **FT crossover (15m)** or **FT crossover (1h)** in semi-auto mode: how the system waits for a crossover, detects it, and executes the trade. The logic applies to **all pairs** (e.g. EUR/USD, GBP/USD, USD/JPY, AUD/USD, etc.) and to **both 1-hour and 15-minute** timeframes.

---

## 1. Overview

- **Daily Fisher scan** produces reversal opportunities (e.g. AUD/USD SHORT, USD/CAD LONG) from the **Daily** Fisher/Trigger and extreme-zone logic.
- In **semi-auto** you can enable a Fisher opportunity and set:
  - **Execution mode:** e.g. **FT crossover (15m)** or **FT crossover (1h)**.
  - **Max runs:** e.g. 3 (how many times this same opportunity can be executed).
- If you choose **FT crossover (15m)** or **(1h)**, the system **does not** open the trade immediately. It stores the opportunity as **pending** and waits for a **Fisher Transform crossover** on the chosen timeframe (15m or 1h) **in the same direction** as the opportunity (SHORT → bearish crossover, LONG → bullish crossover).
- When that crossover is detected, the system **executes** the trade (market order) and **removes** it from pending. Each execution counts toward **max runs**; after max runs, the opportunity is no longer executed.

---

## 2. Timeframes: 15 Minutes and 1 Hour

- **FT crossover (15m)**  
  - Uses **M15** candles from OANDA.  
  - Fisher and Trigger are computed on the **last 50** M15 closes (period = 9 for the Fisher calculation).  
  - Crossover is detected on the **last bar** (current vs previous Fisher/Trigger values).  
  - Pending signals waiting for **M15_CROSSOVER** are checked every engine cycle.

- **FT crossover (1h)**  
  - Uses **H1** candles from OANDA.  
  - Same logic: 50 H1 closes, Fisher(9), Trigger = EMA(3) of Fisher, crossover on last bar.  
  - Pending signals waiting for **H1_CROSSOVER** are checked every engine cycle.

Both timeframes are handled in the same code path; the only difference is the **granularity** (M15 vs H1) and the **trigger type** (M15_CROSSOVER vs H1_CROSSOVER) stored with the pending signal.

---

## 3. Pairs: All Pairs, Not Just One

- Pending Fisher signals are stored **per opportunity**: each has a **pair** (e.g. EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY, etc.) and a **direction** (SHORT or LONG).
- The activation monitor loads **all** pending signals from the pending file and, for each trigger type (M15_CROSSOVER, H1_CROSSOVER), iterates over **every** pending entry waiting for that trigger.
- For each entry it:
  - Reads **pair** and **direction** from the stored opportunity.
  - Fetches M15 or H1 candles **for that pair** from OANDA.
  - Computes Fisher/Trigger and crossover direction for **that pair** on the chosen timeframe.
  - Activates only if the crossover **direction** matches the opportunity **direction** (see below).

There is **no** filter by instrument: the same logic runs for every pair that has a pending Fisher signal. AUD/USD is one example; all other pairs in the Fisher scan are treated the same way.

---

## 4. Crossover Direction and Opportunity Direction

- **Crossover direction** (on 15m or 1h):
  - **Bearish:** Fisher crosses **below** Trigger (prev Fisher > prev Trigger, curr Fisher < curr Trigger).
  - **Bullish:** Fisher crosses **above** Trigger (prev Fisher < prev Trigger, curr Fisher > curr Trigger).

- **Opportunity direction:**
  - **SHORT** (or SELL) → may be activated **only** by a **bearish** crossover.
  - **LONG** (or BUY) → may be activated **only** by a **bullish** crossover.

So:

- A **SHORT** opportunity (e.g. AUD/USD SHORT) is activated when the system detects a **bearish** Fisher crossover on the chosen timeframe (15m or 1h) for AUD/USD. A **bullish** crossover on that pair is **ignored** for this SHORT opportunity (no execution, no run count).
- A **LONG** opportunity (e.g. USD/CAD LONG) is activated when the system detects a **bullish** Fisher crossover on the chosen timeframe for USD/CAD. A bearish crossover is ignored for that LONG.

This ensures that execution aligns with the reversal idea: SHORT on bearish crossover from overbought, LONG on bullish crossover from oversold.

---

## 5. Max Runs

- **Max runs** (e.g. 3) is the **maximum number of times** this **same** opportunity (same pair, same direction, same opportunity id) can be **executed**.
- Each time the system **executes** a trade for that opportunity (after an allowed crossover), it **records** one execution and increments the run count for that opportunity id.
- When the run count reaches **max runs**, the enforcer **rejects** any further execution for that opportunity (“Exceeded max_runs”). So you get at most **max runs** executions per opportunity (e.g. at most 3 separate trades for AUD/USD SHORT, each on a separate qualifying crossover).

---

## 6. End-to-End Flow (Example: AUD/USD SHORT, FT crossover 15m, Max runs 3)

1. **Daily Fisher scan** produces AUD/USD SHORT (reversal from overbought). You enable it in semi-auto with **FT crossover (15m)** and **Max runs: 3**.
2. Engine merges your config: `fisher_config.activation_trigger = 'M15_CROSSOVER'`.
3. Engine calls `position_manager.open_trade(opp, market_state)`. The execution enforcer sees a Fisher opportunity with `activation_trigger = M15_CROSSOVER` and returns **WAIT_SIGNAL** with `wait_for_signal = M15_CROSSOVER`. The opportunity is **stored** in pending (and to disk); **no** order is placed yet.
4. On **every** engine cycle, `_check_fisher_activation_signals(market_state)` runs:
   - Loads all pending signals from the same file used by the position manager.
   - For **M15_CROSSOVER**, gets all pending entries waiting for M15 (including AUD/USD SHORT).
   - For each such entry: fetches **M15** candles for **that pair** (AUD/USD), computes Fisher/Trigger(9), detects crossover on the last bar.
   - If the crossover is **bearish** and the opportunity is **SHORT**, the entry is **activated**.
5. For the **activated** entry: engine removes it from pending, sets `activation_trigger = 'IMMEDIATE'`, and calls `position_manager.open_trade(opportunity, market_state)`. The enforcer now returns **EXECUTE_NOW**; the trade is placed and **record_execution** is called (run count e.g. 1/3).
6. A **bullish** M15 crossover on AUD/USD is **ignored** for this SHORT opportunity (no execution).
7. A **later** bearish M15 crossover can activate the **same** opportunity again (if it was re-stored or if the design allows multiple pending entries per opportunity), and so on, until the run count reaches **3**; after that, the opportunity is rejected by the enforcer.

(If your design stores only one pending per opportunity and re-enqueues after each run until max_runs, the behaviour is “up to 3 executions per opportunity, each on a qualifying crossover.”)

---

## 7. Where It Is Implemented

- **Execution mode enforcer** (`src/execution/execution_mode_enforcer.py`): Fisher opportunities always use `_handle_fisher_mode` (per-opportunity activation). Returns WAIT_SIGNAL with `wait_for_signal = M15_CROSSOVER` or `H1_CROSSOVER` when you choose FT crossover 15m or 1h.
- **UI mode → activation_trigger** (`scalp_engine.py`): When merging semi-auto config for Fisher opportunities, the engine sets `fisher_config.activation_trigger` from the UI mode (e.g. FISHER_M15_CROSSOVER → M15_CROSSOVER, FISHER_H1_CROSSOVER → H1_CROSSOVER).
- **Fisher activation monitor** (`src/execution/fisher_activation_monitor.py`): Fetches M15/H1 candles for **any** pair, computes Fisher/Trigger(9), detects crossover direction, matches to opportunity direction. Returns list of **activated** items (signal_id, opportunity, directive, stored_at). Does **not** execute; caller executes and removes from pending.
- **Engine** (`scalp_engine.py`): `_check_fisher_activation_signals(market_state)` runs each cycle in semi-auto/manual; calls the monitor, then for each activated item removes from pending, sets `activation_trigger = 'IMMEDIATE'`, and calls `position_manager.open_trade(...)` so the trade is executed and run count is updated.

---

## 8. Summary

| Aspect | Behaviour |
|--------|------------|
| **Timeframes** | Both **1 hour (H1)** and **15 minutes (M15)** are supported; choice is per opportunity (FT crossover 1h vs 15m). |
| **Pairs** | Logic runs for **all pairs** that have a pending Fisher signal; no pair is hard-coded. |
| **Direction** | Only crossovers that **match** the opportunity direction activate: SHORT → bearish, LONG → bullish. Opposite crossovers are ignored. |
| **Max runs** | Each execution increments the run count; after **max runs** executions for that opportunity, further executions are rejected. |

This gives you a single, consistent explanation of the Fisher activation logic for both 1h and 15m and for all pairs.
