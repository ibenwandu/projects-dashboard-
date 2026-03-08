# Consolidated Recommendations – Implementation Summary

**Backup:** Full backup created at `backup_before_consol_recommend_20260225_095337` for rollback if needed.

**Source:** `consol-recommend.md` (Trade-Alerts folder).

---

## Phase 1 (implemented)

### §2.1 Broker / pair blacklist
- **Config:** Added `excluded_pairs` to `TradeConfig` (default `["USD/CNY"]`), from env `EXCLUDED_PAIRS` or config.
- **Engine:** Skip opportunities whose pair is in `excluded_pairs` at start of opportunity loop (`scalp_engine.py`).
- **Executor:** `PositionManager._is_pair_excluded()` and check before opening trade (`auto_trader_core.py`).
- **API:** Default config and GET/POST config include `excluded_pairs` (`config_api_server.py`).

### §2.2 Order deduplication and replace-only-when-needed
- Existing logic: one order per pair, replace only when entry/size meaningfully changed or order stale (stale thresholds 50/100 pips, 0.5%/1% already in place; §2.5 widened tolerance).
- No change to replace logic; dedup is already enforced.

### §2.3 ORDER_CANCEL_REJECT handling
- **`cancel_order()`** in `auto_trader_core.py`: After `_request_with_retry`, inspect response for `orderCancelTransaction` / `orderCancelRejectTransaction`; if type is `ORDER_CANCEL_REJECT`, return `False` and log (do not assume cancelled).

### §2.6 Duplicate-block log noise
- **`scalp_engine.py`:** When blocking duplicate (already have order for pair), log RED FLAG only the first time per `(pair, direction)` in a 10-minute window; subsequent blocks in that window log at DEBUG.

### §2.7 “Trade not opened” – explicit reason
- **`PositionManager.open_trade()`** now returns `(Optional[ManagedTrade], Optional[str])`; on reject, second value is a reason code (e.g. `max_runs`, `consensus_too_low`, `oanda_reject`, `validation_failed`, `stale_opportunity`, `duplicate_blocked`, `excluded_pair`, `max_trades_limit`, `no_price`, `wait_signal`).
- **`scalp_engine.py`:** All call sites unpack `(trade, reject_reason)`; when trade is `None`, log: `Trade not opened for {pair} {direction}: reason={reason_code}`.

### §2.8 Database init once per process
- **Scalp-Engine RL:** `Scalp-Engine/src/scalping_rl_enhanced.py` – log “Enhanced RL database initialized” only once per process per `db_path` (module-level `_rl_db_init_logged`).
- **UI RL:** `Scalp-Engine/src/scalping_rl.py` – log “Opening existing database” / “Creating new database” and “Database initialized successfully” only once per process per `db_path` (`_ui_db_init_logged`).
- **UI:** `scalp_ui.py` – `@st.cache_resource` for `get_rl_db()` so ScalpingRL is created once per Streamlit session; `load_recent_signals`, `get_performance_stats`, and pair performance use `get_rl_db()`.

---

## Phase 2 (partial)

### §2.4 Consensus / sources
- **`RiskController.validate_opportunity()`:** Require consensus ≥ majority of available sources (or `min_consensus_level`). `effective_min = min(min_consensus_level, majority)` where `majority = max(1, (num_sources+1)//2)`; reject if `consensus_level < effective_min`.

### §2.5 Staleness (data age vs price movement)
- **Price tolerance:** INTRADAY thresholds widened from 50 pips / 0.5% to 100 pips / 1.0% in `scalp_engine.py` so normal intraday moves do not reject valid setups. SWING unchanged (200 pips / 2%).

---

## Phase 3 (partial)

### §2.14 Config “last updated” in UI
- **Config API:** GET /config response includes `updated` (timestamp); set when serving from memory, disk, or default.
- **UI:** Configuration tab shows “Config last updated: &lt;timestamp&gt; UTC” and a note if config is older than 24 hours.

### §2.11 UI DB ephemeral, §2.12 Streamlit session
- **USER_GUIDE.md:** New subsection “6a. UI database (scalping_rl.db) and session behaviour” documents that the UI DB may be recreated on new deploys/restarts, that critical state lives in Config API / POST /trades, and that “Session already connected” can appear with multiple tabs; recommend one tab per session or refresh.

---

## Not implemented in this pass

- **§2.9** Config/trades polling intervals (increase to 60s/30s, DEBUG for “Trade states updated”) – left to deployment/config.
- **§2.10** Log 404 for engine/OANDA – align log paths/patterns and document; optional “Logs not available” in UI.
- **§2.13** Claude/LLM failures – explicit logging/alerting and fallback (Trade-Alerts pipeline).
- **§2.15** Order sync and manual closure – SL/TP sync with OANDA, OANDA trade IDs, optional circuit breaker.
- **§2.16** Execution rate – MARKET/MIT, warmup, dual-mode (after P1 fixes).
- **§2.17–2.18** Testing and monitoring – paper baseline, A/B tests, metrics.

---

## Rollback

To restore pre-implementation state:

```bash
# From Trade-Alerts folder
cp -r backup_before_consol_recommend_20260225_095337/* .
# Or restore only specific dirs (e.g. Scalp-Engine, config_api_server.py, scalp_ui.py, etc.)
```

Then restart services as needed.
