# Scalp-Engine: Dummy UI Features Report

This document lists every UI-exposed feature that is **dummy** (present in the UI and/or config but not actually implemented or wired so it never takes effect). It is based on a full trace through the codebase.

---

## 1. Execution Modes (Trigger / Execution mode)

### 1.1 Dummy: DMI crossover (1h) and DMI crossover (15m)

- **UI labels:** “DMI crossover (1h)”, “DMI crossover (15m)”
- **Values:** `DMI_H1_CROSSOVER`, `DMI_M15_CROSSOVER`
- **Where shown:**  
  - Semi-Auto Approval (per-opportunity): LLM and Fisher opportunity expanders  
  - Fisher tab (per-opportunity): Execution mode dropdown
- **Why dummy:**  
  - The enforcer correctly returns `WAIT_SIGNAL` with `wait_for_signal="DMI_H1_CROSSOVER"` or `"DMI_M15_CROSSOVER"` and the engine stores the opportunity in pending signals.  
  - The activation monitor (`FisherActivationMonitor.check_activations`) only iterates over **Fisher** triggers: `TRIGGER_M15` and `TRIGGER_H1`. It **never** iterates over `TRIGGER_DMI_H1` or `TRIGGER_DMI_M15`.  
  - So no code ever fetches H1/15m candles, computes DMI, or activates a trade when +DI/-DI cross. The trade stays “waiting for DMI crossover” indefinitely.

**Implemented for contrast:**  
- “FT crossover (1h)” and “FT crossover (15m)” (`FISHER_H1_CROSSOVER`, `FISHER_M15_CROSSOVER`) are implemented: the same activation monitor checks them and runs Fisher crossover logic.  
- “MACD crossover” and “HYBRID” execution modes are implemented (MACD checked in the main opportunity loop / hybrid pending-order check).

---

## 2. Stop Loss Types

### 2.1 Dummy: DMI crossover exit (`DMI_CROSSOVER`)

- **UI label:** “DMI crossover exit”
- **Value:** `DMI_CROSSOVER`
- **Where shown:**  
  - Semi-Auto Approval: “Stop loss type” per opportunity  
  - Fisher tab: “Stop loss type” per opportunity  
  - Global Settings: “Stop Loss Strategy” (as “DMI_CROSSOVER” in `sl_options`)
- **Why dummy:**  
  1. **Enum missing:** `StopLossType` in `auto_trader_core.py` does **not** define `DMI_CROSSOVER`. It only has: `FIXED`, `TRAILING`, `BE_TO_TRAILING`, `AI_TRAILING`, `MACD_CROSSOVER`, `STRUCTURE_ATR_STAGED`.  
  2. **Activation never runs:** The monitor uses `getattr(StopLossType, 'DMI_CROSSOVER', None)`; that returns `None`, so the condition `getattr(..., None) is not None and trade.sl_type == StopLossType.DMI_CROSSOVER` is always false. The existing `check_dmi_reverse_crossover` logic is never executed for any trade.  
  3. **New trades:** When opening a trade with per-opportunity `sl_type='DMI_CROSSOVER'`, `StopLossType(per_opp_sl)` raises `ValueError`; the fallback uses `getattr(StopLossType, 'DMI_CROSSOVER', None) or sl_type`, which leaves the trade with the config default (e.g. `BE_TO_TRAILING`), not DMI.  
  4. **Loaded state:** If a trade was ever saved with `sl_type: "DMI_CROSSOVER"`, loading state calls `StopLossType(trade_data['sl_type'])`, which raises; the code then falls back to config `stop_loss_type` and logs “Unknown sl_type”. So DMI is never applied.

**Implemented for contrast:**  
- MACD crossover exit (`MACD_CROSSOVER`) is in the enum and is checked in the position monitor.  
- DMI **exit** logic exists (`check_dmi_reverse_crossover`) and config has `dmi_sl_timeframe`; only the enum and wiring are missing.

---

## 3. Global Settings: DMI Stop Loss Timeframe

- **UI:** Under Settings, when “Stop Loss Strategy” = “DMI crossover exit”, a dropdown “DMI Stop Loss Timeframe (for trade exit)” is shown with options M15 / H1 (`dmi_sl_timeframe`).
- **Why dummy:** This setting is only relevant when stop loss type is `DMI_CROSSOVER`. Because `DMI_CROSSOVER` as a stop loss type is dummy (see above), the DMI stop loss logic never runs, so this timeframe is never used. It is effectively a dead setting until DMI_CROSSOVER is implemented.

---

## 4. Summary Table

| Category              | UI feature                          | Value(s)                    | Status  | Reason |
|------------------------|-------------------------------------|-----------------------------|--------|--------|
| Execution mode         | DMI crossover (1h)                  | `DMI_H1_CROSSOVER`         | Dummy  | Activation monitor never checks DMI triggers; only Fisher H1/M15. |
| Execution mode         | DMI crossover (15m)                 | `DMI_M15_CROSSOVER`        | Dummy  | Same as above. |
| Stop loss type         | DMI crossover exit                  | `DMI_CROSSOVER`            | Dummy  | Not in `StopLossType` enum; condition never true; new/loaded trades don’t get DMI SL. |
| Settings (global)      | DMI Stop Loss Timeframe             | `dmi_sl_timeframe` (M15/H1) | Dummy  | Only used for DMI_CROSSOVER SL, which is not implemented. |

---

## 5. Features Verified as Implemented (Not Dummy)

- **Execution modes:** MARKET, RECOMMENDED, MACD_CROSSOVER, HYBRID, FISHER_H1_CROSSOVER, FISHER_M15_CROSSOVER, MANUAL, RECOMMENDED_PRICE, IMMEDIATE_MARKET, FISHER_M15_TRIGGER (FT-DMI-EMA).
- **Stop loss types:** FIXED, TRAILING, BE_TO_TRAILING, AI_TRAILING, MACD_CROSSOVER, STRUCTURE_ATR_STAGED (all in enum and wired in monitor / open flow).

### 5.1 Stop loss: UI label → internal value (for reference)

| UI label (what you see)     | Internal value        | Implemented? |
|-----------------------------|------------------------|--------------|
| Fixed                       | `FIXED`                | Yes          |
| BE → Trailing                | `BE_TO_TRAILING`       | Yes          |
| **ATR Trailing**            | **`AI_TRAILING`**      | **Yes**      |
| MACD crossover exit          | `MACD_CROSSOVER`       | Yes          |
| DMI crossover exit           | `DMI_CROSSOVER`        | No (dummy)   |
| FT-DMI-EMA Staged (Structure+ATR) | `STRUCTURE_ATR_STAGED` | Yes  |
| (Settings only) Trailing    | `TRAILING`             | Yes          |

**“ATR Trailing”** in the UI is the **AI_TRAILING** stop loss type. It is **implemented**: the engine uses ATR-based distance (from `atr_multiplier_low_vol` / `atr_multiplier_high_vol` and market regime), converts to trailing when the trade moves into profit, and updates the trailing distance in the position monitor (`_check_ai_trailing_conversion`). It is **not** in the dummy list.

- **Global Settings:** Execution mode, stop loss strategy (except DMI_CROSSOVER), MACD timeframes, consensus, position sizing, trailing pips, etc., are read and used where applicable.

---

## 6. Files Involved (for fixes)

- **DMI execution triggers:** `Scalp-Engine/src/execution/fisher_activation_monitor.py` — add a loop (or equivalent) for `TRIGGER_DMI_H1` / `TRIGGER_DMI_M15`, fetch HLC candles, call `dmi_crossover_direction`, match direction, and append to `activated`.
- **DMI stop loss:** `Scalp-Engine/auto_trader_core.py` — add `DMI_CROSSOVER = "DMI_CROSSOVER"` to `StopLossType` enum; ensure new trades and state load map `"DMI_CROSSOVER"` to that member so the existing `check_dmi_reverse_crossover` branch runs.

---

*Report generated from full codebase review. No code changes were made.*
