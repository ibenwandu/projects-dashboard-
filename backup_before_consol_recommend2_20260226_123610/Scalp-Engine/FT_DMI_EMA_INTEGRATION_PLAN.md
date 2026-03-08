# FT-DMI-EMA-ADX Strategy Integration Plan

**Purpose:** Integrate the standalone FT-DMI-EMA-ADX Multi-Timeframe Strategy (from `Downloads/files`) into the existing Scalp-Engine structure **without replacing** current behavior. New strategy becomes an **optional signal source and/or optional stop/profit logic**.

**Status:** Plan only. Do not implement until permission is given.

---

## 1. Summary of the New Strategy (Downloads/files)

| Component | Role |
|-----------|------|
| **config.py** | OANDA credentials, pairs, indicator params (Fisher 10, DMI 14, EMA 9/26, ATR 14), timeframes (15m, 1H, 4H), sessions (08:00–20:00 GMT), risk (1% per trade, max 3 positions), profit protection (BE +1R, partial +2R, trail +3R), exit rules, filters, execution (paper/live, manual confirm). |
| **oanda_client.py** | OANDA **REST v3** client via **requests** (not oandapyV20). Methods: get_candles, get_current_price, get_spread, create_market_order, create_limit_order, get_open_positions, get_open_trades, close_position, modify_trade, close_trade, position sizing, test_connection. |
| **indicators.py** | Fisher Transform, DMI (+DI/-DI/ADX), EMA, ATR, swing high/low, crossover detection, ADX rising/falling, daily range; **IndicatorValidator** for 4H trend bias and 1H confirmation (long/short). Uses **pandas** DataFrames. |
| **stop_loss_calculator.py** | **Structure + ATR buffer**: 1H swing low (long) or swing high (short) ± (ATR × multiplier). Session-aware multiplier (2.2× at London/NY open, else 2.0×). Fallback simplified ATR. **TimeStopMonitor**: optional exit if open 8+ hours and P/L between -0.3R and +0.3R. |
| **signal_generator.py** | Multi-timeframe entry: (1) Filters (ADX 4H min, ADX not falling 4+ bars, spread, session, etc.), (2) 4H DMI+ADX bias, (3) 1H DMI+EMA+price confirmation; (4) 15m Fisher crossover as **execution trigger** (semi-auto: list when setup ready, trigger trade when 15m met + setup persists). Returns signal dict and/or setup-status (long_setup_ready, short_setup_ready, long_trigger_met, short_trigger_met). Uses **SignalHistory** to avoid duplicate signals within 30 min. |
| **risk_manager.py** | **PositionSizer** (risk %, stop distance → units/lots), **ExposureManager** (max positions, correlation limits), **RiskManager** (validate_new_trade: circuit breakers, daily losses, exposure). Uses config risk/correlation. |
| **trade_manager.py** | **Trade** class (id, instrument, direction, entry, units, stop, R-multiple, MAE/MFE). **ProfitProtectionManager**: BE at +1R, partial 50% at +2R (move remainder SL to +1R), trailing at +3R (trail to 1H EMA 26). **ExitManager**: primary = 4H DMI opposite crossover; emergency = SL hit, spread spike, ADX collapse, EMA structure breakdown. **TradeManager**: add_trade, get_active_trades, update_trades (fetch price/indicators, run profit protection and exit checks, return actions). |
| **trading_engine.py** | Main loop: poll each instrument every 60s → fetch 15m/1H/4H candles → **SignalGenerator.generate_signal** → if signal and filters pass → **StopLossCalculator.calculate_stop_loss** → **RiskManager.validate_new_trade** → manual confirm or **OandaClient.create_market_order** → **TradeManager.add_trade**. Then **TradeManager.update_trades** (profit protection + exits). Uses **requests** OANDA client and **config** classes. |

**Important differences from Scalp-Engine:**

- **OANDA:** New code uses REST v3 with **requests**; Scalp-Engine uses **oandapyV20** (different API shape and error handling).
- **Config:** New code uses Python class-based config (e.g. `InstrumentConfig.MONITORED_PAIRS`); Scalp-Engine uses config API + JSON file and **TradeConfig** dataclass in `auto_trader_core`.
- **Opportunities:** Scalp-Engine gets opportunities from **market_state** (LLM) and **Fisher scan** (daily/hourly); new strategy **generates** its own signals from 4H/1H/15m logic.
- **Trade model:** New strategy has **Trade** (trade_manager) with R-multiple, MAE/MFE, profit stages; Scalp-Engine has **ManagedTrade** (auto_trader_core) with state (PENDING/OPEN/BE/TRAILING), sl_type, etc.
- **Execution:** New strategy can run as standalone (paper/live, manual confirm); Scalp-Engine runs as one process with SEMI_AUTO/AUTO, execution modes (MARKET, RECOMMENDED, FT/DMI/MACD crossover, HYBRID).

---

## 2. Existing Scalp-Engine Structure (Relevant Parts)

- **Entry point:** `scalp_engine.py` → `ScalpEngine` main loop: load config, load market state (LLM opportunities + Fisher opportunities), sync with OANDA, process enabled opportunities (execution mode, open_trade), _check_fisher_activation_signals, _review_and_replace_pending_trades, monitor positions (BE/trailing, MACD/DMI stop, etc.), optional weekend/shutdown logic.
- **Execution:** `auto_trader_core.py` → **TradeExecutor** (oandapyV20), **PositionManager** (active_trades, open_trade, can_open_new_trade, sync_with_oanda, monitor loop), **ManagedTrade**, **TradeConfig** (stop_loss_type, execution_mode, macd_*, dmi_sl_timeframe, etc.).
- **Indicators:** `src/indicators/` → fisher_reversal_analyzer, fisher_transform, dmi_analyzer, multi_timeframe_analyzer. Used by Fisher scan and by activation monitor (FT/DMI crossover).
- **OANDA data:** `src/oanda_client.py` (get_candles returning list of dicts with high/low/close) and raw **oandapyV20** API in TradeExecutor.
- **Config:** Config API + `/var/data/auto_trader_config.json`, loaded into **TradeConfig**; UI (scalp_ui) and config_api_server.
- **State:** market_state.json (or API), trade_states.json, pending_signals.json.

---

## 3. Integration Principles

1. **Do not replace** existing LLM/Fisher flow, config, or execution path.
2. **Reuse** Scalp-Engine’s OANDA access (oandapyV20 + existing get_candles where applicable) so we don’t run two different OANDA clients for the same account.
3. **Map** new strategy concepts into existing ones where possible (e.g. “opportunity” format, pair naming, direction LONG/SHORT).
4. **Add** the new strategy as an **optional** signal source and/or optional stop/profit logic (feature flags or config so it can be disabled).
5. **Keep** deployment and config flow unchanged (Config API, env vars, Render); add new options only where needed.

---

## 4. Phased Implementation Plan

### Phase 1: FT-DMI-EMA as an Optional Signal Source (Opportunities Only)

**Goal:** The new strategy’s **signal_generator** runs periodically and produces **opportunities** in the same shape as LLM/Fisher (pair, direction, entry, stop_loss, take_profit, reason, etc.). These are merged into the opportunity list and processed by the **existing** execution pipeline (Semi-Auto, execution modes, PositionManager.open_trade). No change to how orders are placed or how stops work.

**Semi-Auto two-stage logic:** For semi-auto, the **15m Fisher crossover is the execution trigger**, not a condition for listing. (1) **Opportunity list:** A pair appears in the opportunities list when the higher-timeframe conditions are met and persist (filters + 4H bias + 1H confirmation); the 15m Fisher crossover is **not** required for the pair to appear. (2) **Trigger to trade:** The user can trigger the trade once the 15m condition is met **and** the other conditions still persist. So: list = “setup ready”; execute = “15m trigger met + setup still valid”.

**Steps:**

1. **Place new strategy code under Scalp-Engine**
   - Create a dedicated package, e.g. `src/ft_dmi_ema/` (or `src/strategy_ft_dmi_ema/`), to avoid name clashes with existing `src/indicators`, `src/execution`, etc.
   - Copy and adapt:
     - `config.py` → e.g. `ft_dmi_ema_config.py` (or merge required constants into a single module). Remove OANDA credentials (use env / Scalp-Engine config); keep only strategy params (pairs, indicator periods, timeframes, session times, risk %, filters, profit protection numbers).
     - `indicators.py` → e.g. `indicators_ft_dmi_ema.py`. Keep Fisher, DMI, EMA, ATR, swing, crossover, ADX helpers, **IndicatorValidator**. Change imports to use **pandas** and data coming from Scalp-Engine (list of dicts → DataFrame). Ensure pair naming (e.g. EUR_USD vs EUR/USD) is normalized when calling from engine.
     - `signal_generator.py` → e.g. `signal_generator_ft_dmi_ema.py`. Keep **SignalGenerator** and **SignalHistory**. **Do not** depend on the new strategy’s `oanda_client` or `config` OANDA/account parts. Accept **candle fetcher** and **config** as injected (e.g. get 15m/1H/4H DataFrames and current price/spread from Scalp-Engine).
   - **Candle data:** Implement a thin adapter that uses Scalp-Engine’s existing **OandaClient.get_candles** (or the raw API used in scalp_engine) to fetch 15m, 1H, 4H for a given pair, then convert to pandas DataFrame with columns expected by `indicators.py` / `signal_generator.py` (open, high, low, close, time). Instrument format: normalize to OANDA (e.g. EUR_USD) for API and convert to Scalp-Engine’s pair format (e.g. EUR/USD) in opportunity output.

2. **Wire signal generation into ScalpEngine**
   - In `scalp_engine.py`, after loading market_state and Fisher opportunities (or in a dedicated “strategy signals” step):
     - If “FT-DMI-EMA” signal source is **enabled** (e.g. config flag or env like `FT_DMI_EMA_SIGNALS_ENABLED=true` and list of pairs or use existing monitored pairs):
       - For each monitored pair (from new strategy config or from existing list), fetch 15m/1H/4H candles (reuse existing OANDA access), build DataFrames.
       - Call a **two-stage** signal helper: (a) "setup ready" = filters + 4H bias + 1H confirmation (no 15m Fisher required); (b) "trigger met" = 15m Fisher crossover in the same direction and setup still valid.
       - **Listing:** If setup is ready for a direction (long or short), add one **opportunity** for that pair+direction: pair (e.g. EUR/USD), direction (LONG/SHORT), entry (current_price or mid), stop_loss/take_profit (Phase 2 or default), source tag (e.g. `FT_DMI_EMA`), reason text (e.g. "Setup ready: 4H bias + 1H confirmation; trigger when 15m Fisher crossover"), and a **trigger status** flag: e.g. `ft_15m_trigger_met: true/false`.
       - **Semi-Auto:** The UI/engine shows the opportunity in the list and allows "trigger trade" only when `ft_15m_trigger_met` is true and setup still persists; when the user triggers, execution proceeds (open_trade, etc.).
     - Append these opportunities to the list that is later filtered by “enabled” and execution mode (e.g. same Semi-Auto approval flow as LLM/Fisher).
   - **Config:** Add minimal config for “enable FT-DMI-EMA signals”, pairs (or “use same as engine”), and strategy params (e.g. ADX threshold, session window). Prefer reading from existing config API / TradeConfig where possible (e.g. max_open_trades, account) and keep strategy-specific params in `ft_dmi_ema_config` or a small extra config section.
   - **Signal generator adaptation:** Extend or add a helper that returns both (1) "setup ready" for a direction (filters + 4H + 1H, no 15m) and (2) "15m Fisher trigger met" for that direction. E.g. a dedicated `get_setup_status(instrument, data_15m, data_1h, data_4h, ...)` that returns `{ long_setup_ready, short_setup_ready, long_trigger_met, short_trigger_met }`.

   **Conditions for a pair to appear in the opportunities list (15m Fisher not required for listing):**
   - **Eligibility:** FT-DMI-EMA signals are enabled, and the pair is in the FT-DMI-EMA monitored pairs list (or default list).
   - **Filters passed:** `signal['filters_passed']` is true, i.e. none of the no-trade filters fail:
     - ADX 4H ≥ minimum threshold (e.g. 25), if filter enabled.
     - ADX 4H has not been falling for 4+ candles, if filter enabled.
     - 1H EMA 9 and EMA 26 are not too close (intertwined), if filter enabled.
     - Current time is within approved session (e.g. 08:00–20:00 GMT; not Friday after cutoff; not Sunday before buffer), if filter enabled.
     - Current spread ≤ max spread for the instrument, if filter enabled.
   - **Trigger:** A 15m Fisher Transform crossover is detected (bullish or bearish).
   - **4H bias:** For long → 4H trend bias long (+DI > -DI and ADX sufficient). For short → 4H trend bias short (-DI > +DI and ADX sufficient).
   - **1H confirmation:** For long → 1H confirmation long (price/EMAs/DMI align). For short → 1H confirmation short.
   - **Result:** `signal['signal']` is `'long'` or `'short'` (then convert to one opportunity and append).
   - **Optional duplicate suppression:** If SignalHistory is used, do not add an opportunity for the same pair + direction if one was already produced in the last 30 minutes.

3. **Dependencies**
   - New code uses **pandas** and **numpy**. Scalp-Engine already has pandas in some paths (e.g. MACD). Add numpy/pandas to `requirements.txt` if not already present.
   - **No** new `requests`-based OANDA client in the main flow; all market data and execution stay via oandapyV20 and existing `OandaClient`.

4. **Testing**
   - Unit test: build mock DataFrames (15m/1H/4H), call setup-status helper and full signal; assert setup_ready (no 15m required) and trigger_met (15m crossover) separately.
   - Integration: run engine with FT-DMI-EMA enabled on one pair, paper/sim only; confirm opportunities appear when setup is ready (4H+1H+filters), and "trigger trade" is allowed only when 15m Fisher trigger is met and setup persists.

**Deliverables (Phase 1):**
- `src/ft_dmi_ema/` (or chosen name) with config, indicators, signal generator (including setup-status helper for two-stage logic), and candle adapter.
- Integration point in `scalp_engine.py` that produces FT-DMI-EMA opportunities with `ft_15m_trigger_met` flag; semi-auto allows trigger only when flag is true and setup persists.
- Config/env to enable/disable and to choose pairs.
- No change to TradeExecutor, PositionManager, or stop/execution logic.

---

### Phase 2: Structure+ATR Stop and Staged Profit Protection (Optional)

**Goal:** Offer the new strategy’s **stop-loss method** (Structure + ATR buffer) and **staged profit protection** (BE at +1R, partial at +2R, trail at +3R to 1H EMA 26) as **optional** behaviors for trades that came from FT-DMI-EMA (or, later, configurable per trade type).

**Steps:**

1. **Structure+ATR stop**
   - Port **StopLossCalculator** (and session ATR multiplier) into `src/ft_dmi_ema/` (or `src/indicators` if you prefer). It needs 1H OHLC, entry price, direction, optional entry time; returns stop_loss_price and stop_distance_pips.
   - In Scalp-Engine, when an opportunity is tagged as FT-DMI-EMA (or when a new “stop type” is “STRUCTURE_ATR”):
     - Before calling `position_manager.open_trade`, compute stop using **StopLossCalculator.calculate_stop_loss** (using 1H candles from existing OANDA fetch). Set `opportunity['stop_loss']` and, if needed, pass through to ManagedTrade.
   - Option A: Add a new **StopLossType** (e.g. `STRUCTURE_ATR`) in `auto_trader_core` and in the monitoring loop call a small helper that checks “should we update SL for this trade?” (e.g. BE at +1R) and call `executor.update_stop_loss`. Option B: Only use Structure+ATR at **entry** (compute SL at open); subsequent management remains BE_TO_TRAILING or existing type. Recommendation: start with Option B (Structure+ATR at entry only) to avoid overlapping logic with BE/trailing.

2. **Staged profit (BE → partial → trailing to EMA)**
   - **ProfitProtectionManager** and **ExitManager** in the new strategy assume their own **Trade** list and OANDA client. In Scalp-Engine we already have **ManagedTrade** and a monitoring loop.
   - Option A (minimal): For trades that have a “strategy” tag (e.g. FT_DMI_EMA), in the **existing** position monitor loop, add a branch: fetch 1H EMA 26 and current price, compute R-multiple (entry, initial stop, current price). If R >= 1 and not yet at BE → move stop to entry; if R >= 2 and not yet partial → close 50% and move stop to +1R; if R >= 3 → trail stop to 1H EMA 26 (only move in favorable direction). Use existing `executor.update_stop_loss` and `executor.close_trade` (partial close) or equivalent.
   - Option B: Introduce a small **StagedProfitHandler** in `src/ft_dmi_ema/` or in `auto_trader_core` that, given a ManagedTrade and current market data, returns “action” (none, move_to_be, partial_close, update_trailing). The main monitor loop calls this only when the trade’s `sl_type` or source is FT_DMI_EMA (or a new type like `STAGED_PROFIT`).
   - **Partial close:** OANDA supports closing a portion of a trade. TradeExecutor/PositionManager currently may only have full close; add a **close_trade_partial(trade_id, units)** (or reuse existing OANDA API for partial close) and call it when “partial profit” stage triggers.
   - **Trailing to EMA 26:** Each cycle, for trades in “trailing” stage, get 1H EMA 26 for the pair; if long and current_stop < ema26 and price > ema26, set new_stop = ema26 (or similar); if short, symmetric. Update via existing `update_stop_loss`.

3. **Config**
   - Add options (e.g. in config API or TradeConfig) to enable “Structure+ATR stop for FT-DMI-EMA trades” and “Staged profit (BE/partial/trail) for FT-DMI-EMA trades”. Default off so existing behavior is unchanged.

**Deliverables (Phase 2):**
- Structure+ATR stop used at entry for FT-DMI-EMA opportunities (and optionally for others if config says so).
- Staged profit logic (BE at +1R, partial at +2R, trail to 1H EMA 26 at +3R) for designated trades, using existing executor and state.
- Partial-close support in TradeExecutor/PositionManager if not already present.
- No change to LLM/Fisher execution path except where they opt in to new stop/profit behavior.

---

### Phase 3: Exits and Time Stop (Optional)

**Goal:** Use the new strategy’s **primary exit** (4H DMI opposite crossover) and **emergency exits** (spread spike, ADX collapse, EMA structure breakdown) and **time stop** (exit if open 8+ hours and between -0.3R and +0.3R) for trades that are tagged as FT-DMI-EMA (or when a “exit mode” config is set).

**Steps:**

1. **Primary exit: 4H DMI opposite**
   - In the position monitor loop, for FT-DMI-EMA (or “strategy exit”) trades: fetch 4H candles, compute +DI/-DI (reuse existing DMI or `indicators_ft_dmi_ema`), check opposite crossover (long → -DI > +DI; short → +DI > -DI). If true, call **close_trade** with reason “4H DMI crossover”.
   - This can live beside existing MACD_CROSSOVER and DMI_CROSSOVER stop logic; distinguish by trade source or a dedicated exit_type so we don’t double-close.

2. **Emergency exits**
   - **Spread spike:** In monitor loop, get current spread; if > 3× normal for the pair, close trade (reason: spread spike). Normal spread can come from config or a short rolling average.
   - **ADX collapse:** Fetch 4H, compute ADX; if ADX < 15, close (reason: ADX collapse).
   - **EMA structure breakdown:** For long: price closes below both EMA 9 and EMA 26 on 1H; for short: above both. Close with reason “EMA structure breakdown”.
   - Implement as small helpers called only for trades that use “strategy exits”; avoid affecting non–FT-DMI-EMA trades.

3. **Time stop**
   - Port **TimeStopMonitor.should_exit_on_time** (open 8+ hours and -0.3R <= P/L <= +0.3R). In monitor loop, for tagged trades, compute R-multiple and time since entry; if true, close with reason “Time stop (setup invalidated)”.

4. **Config**
   - Enable/disable primary exit (4H DMI), emergency exits, and time stop per strategy or globally (e.g. in ft_dmi_ema_config or TradeConfig).

**Deliverables (Phase 3):**
- 4H DMI opposite crossover closes FT-DMI-EMA trades (when enabled).
- Emergency exit conditions (spread, ADX, EMA) and time stop (optional) for those trades.
- Clear logging and reason strings for each exit type.

---

## 5. File and Module Mapping

| New strategy file | Location in Scalp-Engine | Notes |
|-------------------|--------------------------|--------|
| config.py | `src/ft_dmi_ema/ft_dmi_ema_config.py` (or similar) | Strategy params only; no OANDA creds. Pairs, periods, thresholds, session, risk %, profit stages. |
| indicators.py | `src/ft_dmi_ema/indicators_ft_dmi_ema.py` | Fisher, DMI, EMA, ATR, swing, crossover, validators. Input: DataFrame from adapter. |
| signal_generator.py | `src/ft_dmi_ema/signal_generator_ft_dmi_ema.py` | SignalGenerator + SignalHistory. Injected candle fetcher and config. |
| stop_loss_calculator.py | `src/ft_dmi_ema/stop_loss_calculator_ft_dmi_ema.py` | Structure+ATR + TimeStopMonitor. Used at entry (Phase 2) and for time stop (Phase 3). |
| risk_manager.py | Reuse **RiskController** in auto_trader_core where possible. New strategy’s PositionSizer/ExposureManager can be used only for **FT-DMI-EMA** position sizing if desired; else keep using existing consensus/size logic. | Optional: port correlation and exposure checks into a small module under `src/ft_dmi_ema/` and call from signal/entry path only for FT-DMI-EMA. |
| trade_manager.py (Trade, ProfitProtection, Exit) | **Do not** add a second trade store. Map: Trade → ManagedTrade for execution. Profit protection and exit logic ported into **Scalp-Engine’s monitor loop** or a small **StagedProfitHandler** / **StrategyExitHandler** called from it. | See Phase 2 and 3. |
| oanda_client.py | **Do not** integrate. Scalp-Engine keeps using oandapyV20 and `src/oanda_client.py`. New strategy gets candles via an **adapter** that calls existing OANDA access. | Adapter in `src/ft_dmi_ema/candle_adapter.py` or similar. |
| trading_engine.py | **Do not** run as separate main. Its loop is replaced by “call signal generator from scalp_engine and append opportunities; execution is existing open_trade + monitor loop.” | See Phase 1. |

---

## 6. Config and Environment

- **Existing:** CONFIG_API_URL, OANDA_ACCESS_TOKEN, OANDA_ACCOUNT_ID, OANDA_ENV, MARKET_STATE_FILE_PATH, etc.
- **New (suggested):**
  - `FT_DMI_EMA_SIGNALS_ENABLED` (bool): Enable FT-DMI-EMA as an opportunity source.
  - `FT_DMI_EMA_PAIRS` (optional): Comma-separated pairs (e.g. EUR_USD,GBP_USD). If unset, use a default list from ft_dmi_ema_config or same as engine.
  - Optional: `FT_DMI_EMA_STRUCTURE_ATR_STOP`, `FT_DMI_EMA_STAGED_PROFIT`, `FT_DMI_EMA_4H_DMI_EXIT`, `FT_DMI_EMA_TIME_STOP_ENABLED` to toggle Phase 2/3 features.
- Strategy-specific constants (ADX 25, ATR 2.0, session 08:00–20:00 GMT, etc.) stay in `ft_dmi_ema_config.py` or a single JSON section; avoid scattering magic numbers.

---

## 7. Risk and Compatibility

- **Conflicts:** Two OANDA clients (requests vs oandapyV20) must not both run for the same account in the same process. Plan uses only existing OANDA access and an adapter.
- **Naming:** Pair format (EUR_USD vs EUR/USD) must be normalized everywhere the new strategy touches the engine (opportunity dict, candle fetch).
- **Execution:** All orders still go through **TradeExecutor** and **PositionManager**; no second execution path.
- **State:** Only one source of truth for open trades (PositionManager.active_trades and trade_states.json). FT-DMI-EMA does not maintain its own trade list in production.
- **Rollback:** With feature flags, FT-DMI-EMA can be disabled and the engine behaves exactly as before.

---

## 8. Implementation Order (Checklist)

- [ ] **Phase 1.1** Create `src/ft_dmi_ema/` and copy/adapt config (strategy params only).
- [ ] **Phase 1.2** Copy/adapt indicators (pandas, DataFrame input); add candle adapter (OANDA → DataFrame).
- [ ] **Phase 1.3** Copy/adapt signal_generator; inject candle fetcher and config; no dependency on new oanda_client.
- [ ] **Phase 1.4** In scalp_engine.py, add “FT-DMI-EMA signal” step: for each enabled pair, fetch 15m/1H/4H, run signal generator, append opportunities with source tag.
- [ ] **Phase 1.5** Add config/env for enable and pairs; test with one pair in paper/sim.
- [ ] **Phase 2.1** Port Structure+ATR stop; use at entry for FT-DMI-EMA opportunities when enabled.
- [ ] **Phase 2.2** Implement staged profit (BE, partial, trail to EMA 26) in monitor loop or StagedProfitHandler; add partial-close to executor if needed.
- [ ] **Phase 3.1** Add 4H DMI opposite exit for FT-DMI-EMA trades.
- [ ] **Phase 3.2** Add emergency exits (spread, ADX, EMA breakdown) and optional time stop.

---

## 9. Out of Scope (For This Plan)

- Running the **standalone** `trading_engine.py` (with its own main loop and requests-based OANDA client) inside Scalp-Engine.
- Replacing LLM or Fisher as signal sources.
- Backtesting framework; this plan is live/forward integration only.
- Changing Render deployment or config API contract; only additive config/env and code under `src/ft_dmi_ema/` and targeted hooks in `scalp_engine.py` and optionally `auto_trader_core.py`.

---

*End of plan. Do not implement until permission is given.*
