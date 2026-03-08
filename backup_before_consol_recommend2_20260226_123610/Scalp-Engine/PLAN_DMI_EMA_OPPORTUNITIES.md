# Plan: DMI-EMA Opportunities (New Opportunity List)

**Status:** Plan only — no implementation without approval. No piecemeal or dummy features.

---

## 1. Objective

Add a fourth list of opportunities alongside LLM, Fisher, and FT-DMI-EMA: **DMI-EMA opportunities**. The logic is DMI+EMA alignment across 1D/4H/1H with configurable EMA distance; confidence is indicated by optional flags (FT crossover and ADX > 20). Reuse existing FT-DMI-EMA resources for activation, SL, execution, and config; reuse the same env/config variables where possible and avoid introducing new env vars.

---

## 2. Opportunity Definition

### 2.1 Required conditions (gate inclusion and execution)

**Long opportunity** exists when all of the following hold:

- **1D:** +DI > -DI (last bar).
- **4H:** +DI > -DI (last bar).
- **1H:** +DI > -DI (last bar).
- **1H:** EMA9 > EMA26 (last bar).
- **1H EMA distance:** |EMA9 − EMA26| ≥ threshold in pips (configurable; reuse `IndicatorConfig.EMA_INTERTWINED_THRESHOLD`, default 5 pips). Same pip logic as FT-DMI-EMA (JPY vs default).

**Short opportunity** exists when all of the following hold:

- **1D:** -DI > +DI.
- **4H:** -DI > +DI.
- **1H:** -DI > +DI.
- **1H:** EMA9 < EMA26.
- **1H EMA distance:** same threshold (≥ 5 pips) so EMAs are not intertwined.

When these conditions are achieved or persist, the pair/direction is included in the DMI-EMA opportunities list. No additional “trigger” is required for listing; optional execution trigger (e.g. 15m FT) is handled by execution mode (see §5).

### 2.2 Confidence flags (informational only; do not gate listing or execution)

Stored and displayed only; they must not block inclusion or trading:

- **FT crossover 1H:** Fisher Transform bullish (long) or bearish (short) crossover on 1H (same indicator as FT-DMI-EMA).
- **FT crossover 15m:** Fisher Transform bullish (long) or bearish (short) crossover on 15m.
- **ADX > 20:** Last-bar ADX > 20 on 15m, 1H, and 4H (three separate flags).

Each opportunity will carry a small structure, e.g.:

- `confidence_flags`: `{ "ft_1h": bool, "ft_15m": bool, "adx_15m": bool, "adx_1h": bool, "adx_4h": bool }`.

No new env vars or config entries for these; they are derived from existing indicators.

---

## 3. Reuse of existing resources

### 3.1 Variables and config (no new env vars)

- **Pairs:** Reuse `InstrumentConfig.get_monitored_pairs()` (and thus `FT_DMI_EMA_PAIRS`). Same pairs for FT-DMI-EMA and DMI-EMA.
- **Master switch:** Reuse `FT_DMI_EMA_SIGNALS_ENABLED`. When `true`, the engine will populate both `ft_dmi_ema_opportunities` and `dmi_ema_opportunities` (one env var controls both strategies).
- **Max trades cap:** Reuse `FT_DMI_EMA_MAX_TRADES`. The cap applies to the combined count of open trades with `opportunity_source in ("FT_DMI_EMA", "DMI_EMA")` (single pool for “system” trades).
- **Config (AUTO mode):** Add one new key in the auto_trader config (and UI): `auto_trade_dmi_ema` (boolean, default `True`). In AUTO mode, if `auto_trade_dmi_ema` is `False`, the engine will not open new DMI-EMA trades (same pattern as `auto_trade_ft_dmi_ema`). This is the only new config key; no new env vars.

### 3.2 Data and indicators

- **Candles:** Reuse `FTCandleFetcher` and the same OANDA client path. For DMI-EMA, request one extra granularity: **Daily (OANDA "D")**. So:
  - Extend `fetch_ft_dmi_ema_dataframes` (or add a shared helper in the same module) to optionally return 1D data: e.g. `fetch_dmi_ema_dataframes` returning `(data_1d, data_4h, data_1h, data_15m)` when needed, reusing existing `_candles_to_dataframe` and `get_candles`/`fetch_multi_timeframe` with `granularities=["D", "H4", "H1", "M15"]` for the DMI-EMA path. FT-DMI-EMA path continues to use only M15/H1/H4.
- **Indicators:** Reuse `Indicators` and `IndicatorValidator` from `src.ft_dmi_ema.indicators_ft_dmi_ema`: DMI (plus_di, minus_di, adx), EMA, Fisher Transform, `detect_crossover`. No new indicator modules.
- **Config constants:** Reuse `IndicatorConfig` (DMI_PERIOD, EMA_FAST, EMA_SLOW, EMA_INTERTWINED_THRESHOLD) and `InstrumentConfig.get_pip_value` for the 5-pip (or configurable) EMA distance check.

### 3.3 Stop loss and exit logic

- **At open:** Reuse `StopLossCalculator` from `src.ft_dmi_ema` (1H data, structure+ATR). When `opportunity_source == "DMI_EMA"`, set `initial_stop_loss` and `stop_loss` the same way as for FT-DMI-EMA.
- **In position monitor:** Reuse the same STRUCTURE_ATR_STAGED exit logic as FT-DMI-EMA (BE +1R, partial +2R, trail +3R to 1H EMA 26, time stop, 4H DMI crossover, ADX collapse, spread spike, EMA breakdown). Extend the condition that gates this block from `opportunity_source == 'FT_DMI_EMA'` to `opportunity_source in ('FT_DMI_EMA', 'DMI_EMA')` in `auto_trader_core.py` (`_check_structure_atr_staged` / position monitor). No duplicate exit logic.

### 3.4 Execution and activation

- **Execution enforcer:** Add a branch for `opportunity.get("source") == "DMI_EMA"` in `execution_mode_enforcer.py`, mirroring FT_DMI_EMA:
  - If `trigger_met` (or equivalent) is not true → `WAIT_SIGNAL` with `wait_for_signal="DMI_EMA_M15_TRIGGER"` (or immediate if mode is IMMEDIATE_MARKET; see below).
  - If trigger met → `EXECUTE_NOW` with same order-type logic (MARKET vs LIMIT/STOP at entry) based on `execution_config.mode`.
- **Trigger semantics for DMI-EMA:**
  - **IMMEDIATE_MARKET:** “Trigger” is considered met as soon as the DMI-EMA setup is ready (no second stage). So list entry = executable immediately when mode is IMMEDIATE_MARKET.
  - **FISHER_M15_TRIGGER:** “Trigger” is met when 15m Fisher crossover occurs (reuse same 15m Fisher logic as FT-DMI-EMA). Opportunity is listed when setup is ready, then stored as pending until 15m FT crossover; then execute. Same pattern as FT-DMI-EMA WAIT_SIGNAL / activation.
- **Pending signals:** Reuse `position_manager.pending_signals` and the same persistence. New wait key: `DMI_EMA_M15_TRIGGER` (so activation check only runs for DMI-EMA when that key is set).
- **Activation check:** Add `_check_dmi_ema_activation_signals` in `scalp_engine.py`, analogous to `_check_ft_dmi_ema_activation_signals`: find pending signals with `wait_for_signal == 'DMI_EMA_M15_TRIGGER'`, re-fetch 1D/4H/1H/15m, recompute DMI-EMA setup + 15m Fisher; if setup still ready and 15m FT crossover met, remove pending and call `open_trade` with Structure+ATR stop. Reuse same fetcher and indicators.

### 3.5 Semi-auto and UI

- **Semi-auto config:** Reuse the same per-opportunity keys: `enabled`, `mode`, `max_runs`, `sl_type`, `reset_run_count_requested`. Stable opportunity id for DMI-EMA: e.g. `DMI_EMA_{pair}_{LONG|SHORT}` so it matches engine and UI.
- **Semi-Auto Approval tab:** DMI-EMA opportunities appear in the same list as LLM, Fisher, and FT-DMI-EMA, with the same controls: Enable, Trigger/Execution mode (FISHER_M15_TRIGGER and IMMEDIATE_MARKET), Stop loss type, Max runs, Save, Reset run count. No new UI framework; same `render_semi_auto_approval` flow with DMI-EMA merged into `all_opps`.
- **Auto-Trader tab:** One new checkbox: “Trade DMI-EMA opportunities” bound to `auto_trade_dmi_ema` (load/save via existing config API). Same pattern as “Trade FT-DMI-EMA opportunities”.
- **New tab: DMI-EMA Opportunities:** Same structure as “FT-DMI-EMA Opportunities”: load from market state, show count, last updated, and per-opportunity expanders with pair, direction, entry, SL, 15m trigger status (if FISHER_M15_TRIGGER), and **confidence flags** (FT 1H, FT 15m, ADX 15m/1H/4H). No execution controls on this tab; execution is configured in Semi-Auto Approval.

---

## 4. Data flow and state

### 4.1 Market state

- **New keys (same file/API as existing):**
  - `dmi_ema_opportunities`: list of opportunity dicts (see §4.2).
  - `dmi_ema_last_updated`: ISO8601 timestamp.
- **Persistence:** Same as FT-DMI-EMA: when engine runs in SEMI_AUTO/MANUAL, write to `market_state_file` (read-modify-write) and POST to market-state-api. In AUTO, clear or do not populate the list (same pattern as FT-DMI-EMA).

### 4.2 Opportunity document shape

Each item in `dmi_ema_opportunities` (and used internally) will look like:

- `id`: `DMI_EMA_{pair_display}_LONG` or `_SHORT`.
- `pair`, `direction`, `entry`, `current_price`, `source`: `"DMI_EMA"`.
- `reason`: short human-readable summary (e.g. “1D/4H/1H +DI>-DI; 1H EMA9>26, distance ≥5 pips”).
- `execution_config`: `{ "mode": "FISHER_M15_TRIGGER" | "IMMEDIATE_MARKET" }` (and later `max_runs` from semi-auto).
- **Trigger field:** For consistency with enforcer and activation, include a boolean: `dmi_ema_15m_trigger_met` (or reuse `ft_15m_trigger_met` for “15m FT crossover met” so enforcer can branch on one name; recommend reusing `ft_15m_trigger_met` for “15m Fisher trigger met” so no new variable).
- `confidence_flags`: `{ "ft_1h": bool, "ft_15m": bool, "adx_15m": bool, "adx_1h": bool, "adx_4h": bool }`.

Reuse of `ft_15m_trigger_met`: same meaning (“15m Fisher crossover met”); used by execution enforcer and activation. No new variable name.

### 4.3 Market-state API and scan script

- **API:** Extend the same POST body used for FT-DMI-EMA to include `dmi_ema_opportunities` and `dmi_ema_last_updated` (single payload with both `ft_dmi_ema_opportunities` and `dmi_ema_opportunities`), or add a second endpoint `POST /dmi-ema-opportunities` that merges only DMI-EMA. Recommendation: **single payload** so one POST carries both lists and timestamps; market-state-api merge method updates both keys. No new env vars.
- **Merge in market_state_api:** Add `merge_dmi_ema_opportunities` (or extend the existing merge to accept both lists when present) and persist `dmi_ema_opportunities` and `dmi_ema_last_updated` in the same state file.
- **Scan script:** Extend `run_ft_dmi_ema_scan.py` to compute both FT-DMI-EMA and DMI-EMA lists (using shared candle fetch where possible: 15m/1H/4H for FT-DMI-EMA; add 1D for DMI-EMA) and POST both in one payload. No separate `run_dmi_ema_scan.py` unless you prefer a dedicated script later; plan assumes one script, one POST.

---

## 5. Engine integration (scalp_engine.py)

### 5.1 Main loop

- After `_inject_ft_dmi_ema_opportunities(market_state)` and before or after `_check_ft_dmi_ema_opportunities`, add:
  - `_inject_dmi_ema_opportunities(market_state)` (populate `dmi_ema_opportunities` when `FT_DMI_EMA_SIGNALS_ENABLED` is true; in AUTO clear list and POST empty list like FT-DMI-EMA).
  - `_check_dmi_ema_opportunities(market_state)` (SEMI_AUTO/MANUAL: process enabled DMI-EMA opps and call `open_trade`; AUTO: call `_check_dmi_ema_opportunities_auto` when `auto_trade_dmi_ema` is true).
  - `_check_dmi_ema_activation_signals(market_state)` (process pending signals with `DMI_EMA_M15_TRIGGER` and open trade when 15m FT crossover met).

Order in loop: inject FT-DMI-EMA → inject DMI-EMA → check FT-DMI-EMA opportunities → check DMI-EMA opportunities → check Fisher activation → check FT-DMI-EMA activation → check DMI-EMA activation → rest unchanged.

### 5.2 Inject DMI-EMA

- **Guard:** If `FT_DMI_EMA_SIGNALS_ENABLED` is not true, set `market_state["dmi_ema_opportunities"] = []` and return.
- **AUTO:** Set `dmi_ema_opportunities` to `[]`, clear on disk and POST empty list (same as FT-DMI-EMA).
- **SEMI_AUTO/MANUAL:** For each pair in `InstrumentConfig.get_monitored_pairs()`:
  - Fetch 1D, 4H, 1H, 15m (reuse fetcher; add “D” for this path).
  - Compute DMI on 1D, 4H, 1H (reuse `Indicators.dmi`); EMA9/26 on 1H; Fisher on 1H and 15m for confidence; ADX on 15m/1H/4H for confidence.
  - Evaluate long/short required conditions; if long (or short) setup ready, append to list with `confidence_flags` and `ft_15m_trigger_met` (15m Fisher crossover) for execution path.
  - Optional: SEMI_AUTO merge of enabled DMI-EMA opps from API when current run didn’t compute them (same pattern as FT-DMI-EMA).
- Persist to `market_state_file` and POST (both lists in one payload if API extended).

### 5.3 Check DMI-EMA opportunities (SEMI_AUTO/MANUAL)

- If `FT_DMI_EMA_SIGNALS_ENABLED` is false, return.
- If AUTO: delegate to `_check_dmi_ema_opportunities_auto` only when `config.auto_trade_dmi_ema` is true; then return.
- Read `market_state["dmi_ema_opportunities"]`; in SEMI_AUTO filter by `semi_auto.is_enabled(opp_id)`.
- For each enabled opportunity: cooldown/position/`can_open_new_trade` checks; get current price; build `opp_with_order` with `execution_config` from saved (mode, max_runs); compute Structure+ATR stop (reuse StopLossCalculator); call `_maybe_reset_run_count_and_open_trade`. Enforcer will return WAIT_SIGNAL or EXECUTE_NOW.

### 5.4 Check DMI-EMA opportunities AUTO

- Cap: `count_ft_dmi_ema + count_dmi_ema` (both sources) ≤ `FT_DMI_EMA_MAX_TRADES`.
- For each pair, fetch 1D/4H/1H/15m, compute setup; if setup ready and (mode is IMMEDIATE_MARKET or 15m FT trigger met), add to list; then for each, same validations and `open_trade` with Structure+ATR stop. Increment combined count for both sources.

### 5.5 Clear pending for disabled opportunities

- Extend `_clear_pending_signals_for_disabled_opportunities` so that when an opportunity is removed or disabled, pending signals with `DMI_EMA_M15_TRIGGER` for that pair/direction are also removed (same pattern as FT-DMI-EMA).

---

## 6. Execution enforcer and open_trade

- In `get_execution_directive`, add a block for `opportunity.get("source") == "DMI_EMA"`:
  - If `opportunity.get("ft_15m_trigger_met")` is not true and mode is FISHER_M15_TRIGGER → `WAIT_SIGNAL`, `wait_for_signal="DMI_EMA_M15_TRIGGER"`.
  - If trigger met (or mode is IMMEDIATE_MARKET) → `EXECUTE_NOW` with same order-type logic as FT_DMI_EMA (MARKET vs LIMIT/STOP at entry).
- In `create_managed_trade` (auto_trader_core): when `opportunity_source == 'DMI_EMA'`, same as FT_DMI_EMA — default `sl_type` STRUCTURE_ATR_STAGED, set `initial_stop_loss` from opp if present, set `opportunity_source` on `ManagedTrade`.
- In position monitor: where STRUCTURE_ATR_STAGED exit logic is gated by `opportunity_source == 'FT_DMI_EMA'`, change to `opportunity_source in ('FT_DMI_EMA', 'DMI_EMA')` so DMI-EMA trades get the same BE/partial/trail/time/DMI/ADX/spread/EMA exit logic.

---

## 7. UI (scalp_ui.py)

- **Load:** Add `load_dmi_ema_opportunities()` (same pattern as `load_ft_dmi_ema_opportunities`): read from market state, return `(opps, len(opps), last_updated)`.
- **Semi-Auto Approval:** When building `all_opps`, append DMI-EMA opportunities from `market_state.get('dmi_ema_opportunities', [])` with `source: 'DMI-EMA'`, `opp_id` stable (e.g. `DMI_EMA_{pair}_LONG/SHORT`). Execution modes for DMI-EMA: `['FISHER_M15_TRIGGER', 'IMMEDIATE_MARKET']` (same labels as FT-DMI-EMA). Default mode for DMI-EMA: `FISHER_M15_TRIGGER`. Same row controls: Enable, Mode, SL type, Max runs, Save, Reset run count.
- **New tab “DMI-EMA Opportunities”:** Header, caption, metrics (count, last updated), load from market state; list expanders with pair, direction, entry, SL, trigger status, **confidence flags** (FT 1H, FT 15m, ADX 15m/1H/4H), and note to configure in Semi-Auto Approval.
- **Auto-Trader:** Add checkbox “Trade DMI-EMA opportunities” → `auto_trade_dmi_ema`, default True; include in config save; warning “At least one source…” if all (LLM, Fisher, FT-DMI-EMA, DMI-EMA) are unchecked in AUTO.
- **Tabs order:** Add a fourth tab so order is: Opportunities, Fisher Opportunities, FT-DMI-EMA Opportunities, **DMI-EMA Opportunities**, then existing tabs (Recent Signals, etc.).

---

## 8. New / modified code locations (no implementation yet)

| Area | Action |
|------|--------|
| **Candle adapter / fetcher** | Add Daily support: either extend `fetch_ft_dmi_ema_dataframes` to optionally return 1D, or add `fetch_dmi_ema_dataframes(get_candles_fn, instrument)` returning (data_1d, data_4h, data_1h, data_15m). FTCandleFetcher: use `granularities=["D","H4","H1","M15"]` for DMI-EMA. |
| **DMI-EMA setup logic** | New function `get_dmi_ema_setup_status(instrument, data_1d, data_4h, data_1h, data_15m, current_price, current_spread, now)` in `src.ft_dmi_ema` (e.g. in `signal_generator_ft_dmi_ema.py` or new `dmi_ema_setup.py`). Returns long_setup_ready, short_setup_ready, confidence_flags dict, and ft_15m_trigger_met (15m Fisher). Reuse Indicators + IndicatorValidator; no ADX/FT in required conditions. |
| **scalp_engine.py** | Add _inject_dmi_ema_opportunities, _check_dmi_ema_opportunities, _check_dmi_ema_opportunities_auto, _check_dmi_ema_activation_signals; call from main loop; extend _clear_pending_signals_for_disabled_opportunities for DMI_EMA_M15_TRIGGER. |
| **execution_mode_enforcer.py** | Add branch for source == "DMI_EMA" (same as FT_DMI_EMA: trigger_met → EXECUTE_NOW; else WAIT_SIGNAL DMI_EMA_M15_TRIGGER). |
| **auto_trader_core.py** | create_managed_trade: when source == "DMI_EMA", same sl_type/initial_stop_loss/opportunity_source as FT_DMI_EMA. Position monitor: allow STRUCTURE_ATR_STAGED for opportunity_source in ('FT_DMI_EMA', 'DMI_EMA'). |
| **Config (TraderConfig / config-api)** | Add `auto_trade_dmi_ema: bool = True`. |
| **scalp_ui.py** | load_dmi_ema_opportunities; merge DMI-EMA into all_opps in render_semi_auto_approval; new tab DMI-EMA Opportunities with confidence flags; Auto-Trader checkbox auto_trade_dmi_ema. |
| **fisher_market_bridge.py** | Extend POST payload to include dmi_ema_opportunities and dmi_ema_last_updated (single POST with both lists). |
| **market_state_api.py** | Add merge for dmi_ema_opportunities (or one merge method that accepts both lists); persist dmi_ema_opportunities and dmi_ema_last_updated. |
| **market_state_server.py** | Either extend /ft-dmi-ema-opportunities to accept optional dmi_ema_opportunities in body, or add POST /dmi-ema-opportunities; implement merge for DMI-EMA state. |
| **run_ft_dmi_ema_scan.py** | Compute DMI-EMA list (fetch 1D+4H+1H+15m, call get_dmi_ema_setup_status); include dmi_ema_opportunities and dmi_ema_last_updated in POST payload together with ft_dmi_ema_opportunities. |

---

## 9. Testing and validation (after implementation)

- Unit-style: `get_dmi_ema_setup_status` returns long/short setup and confidence flags; required conditions (1D/4H/1H +DI>-DI, 1H EMA, distance) gate correctly; confidence flags do not gate.
- Integration: With `FT_DMI_EMA_SIGNALS_ENABLED=true`, both lists appear in market state and in API; AUTO respects `auto_trade_dmi_ema` and combined max trades; SEMI_AUTO enables/disables per opp; WAIT_SIGNAL then activation opens trade; STRUCTURE_ATR_STAGED exit runs for DMI_EMA trades.
- UI: DMI-EMA tab shows opportunities and confidence flags; Semi-Auto shows DMI-EMA rows with same controls; config save/load includes auto_trade_dmi_ema.

---

## 10. Summary

- **New list:** `dmi_ema_opportunities` with required conditions (1D/4H/1H DMI alignment + 1H EMA alignment + 5-pip distance) and confidence flags (FT 1H/15m, ADX 15m/1H/4H).
- **Reuse:** Pairs, FT_DMI_EMA_SIGNALS_ENABLED, FT_DMI_EMA_MAX_TRADES, InstrumentConfig/IndicatorConfig, candle fetcher (+ 1D), Indicators/Validator, StopLossCalculator, execution enforcer pattern, pending_signals, semi-auto config keys, UI patterns. One new config key: `auto_trade_dmi_ema`.
- **No new env vars.** Single implementation pass, no piecemeal or dummy features.

If you approve this plan, implementation can proceed in one coherent pass along the sections above.
