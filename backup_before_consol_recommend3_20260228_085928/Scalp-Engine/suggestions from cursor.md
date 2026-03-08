# Suggestions from Cursor

**Source:** Review of Manual logs in `Desktop/Test/Manual logs` matched against Scalp-Engine / Trade-Alerts logic and intent.  
**Scope:** Improvement plans only. **No changes have been implemented**; approval required before any code or config changes.

---

## 1. Documents Reviewed

| Document | Content summary |
|----------|-----------------|
| **Oanda-Transaction-history.csv** | OANDA transaction log: LIMIT/MIT orders, cancels, fills, ORDER_CANCEL_REJECT, LIMIT_ORDER_REJECT (USD/CNY), TRADE_CLIENT_EXTENSIONS_MODIFY |
| **Market-state-API Logs.txt** | Market-state API: GET /market-state, POST /ft-dmi-ema-opportunities, POST /fisher-opportunities, merged opportunities (often 0), market state saved |
| **Config-API logs.txt** | Config API: GET /config, POST /trades (trade state sync), high-frequency polling from multiple IPs, log endpoints returning 404 for engine/oanda |
| **Scalp-engine UI Logs.txt** | Streamlit UI: deploy lifecycle, scalping_rl.db create/open, market-state API load, session “already connected” messages |
| **Scalp-engine Logs.txt** | Engine: config load, opportunity checks, RED FLAG duplicate blocks (AUD/JPY), “Trade not opened” warnings, RL DB init repeated, stale order cancel |
| **Trade-Alerts Logs.txt** | Trade-Alerts: Claude analysis errors (“All Claude models failed”) |

---

## 2. Trading System Logic & Intent (Reference)

- **One order per pair:** Only one pending or open order per instrument; duplicates blocked (RED FLAG).
- **Consensus / required LLMs:** Opportunities filtered by `min_consensus` and `required_llms`; sources: e.g. synthesis, chatgpt, gemini.
- **Execution:** MARKET, RECOMMENDED (limit), or HYBRID; stop loss types FIXED, TRAILING, BE_TO_TRAILING, etc.
- **Trading hours:** Weekdays 01:00–21:30 UTC; weekend shutdown; runner rules Mon–Thu.
- **Pair lists:** Fisher uses `FISHER_PAIRS`; FT-DMI-EMA uses `FT_DMI_EMA_PAIRS` (see `docs/PAIR_LISTS.md`). Defaults do not include USD/CNY.
- **Config / state:** Config from Config API; trade state synced via POST /trades; market state from Market-state API.

---

## 3. Improvement Plans

### 3.1 Broker instrument allow-list (USD/CNY and LIMIT_ORDER_REJECT)

**Evidence:** Oanda transaction history shows **many consecutive LIMIT_ORDER_REJECT** for **USD/CNY** (same price 6.94250, ~2 min apart). System kept sending orders for a pair OANDA rejects.

**Intent alignment:** Engine should only place orders for instruments the broker allows and that match strategy pair lists.

**Suggestions:**

1. **Allow-list by broker:** Maintain a list of tradeable instruments for the current broker (e.g. OANDA) — from config, env, or a one-time fetch of OANDA’s tradeable instruments — and **before** placing any order, check that the pair is in that list. If not, skip and log once (e.g. “Pair not tradeable on broker: USD/CNY”).
2. **Block or filter USD/CNY:** If USD/CNY is not tradeable on your OANDA account, ensure it never reaches the execution layer: filter it out in market-state processing or in the engine’s “allowed pairs” for execution. Optionally add a config or env list of **excluded** pairs (e.g. `EXCLUDED_PAIRS=USD/CNY`) and apply it wherever opportunities are converted to orders.
3. **Reaction to LIMIT_ORDER_REJECT:** When the engine (or a sync process) sees an order reject for a given instrument, record it (e.g. “instrument X rejected by broker”) and avoid re-submitting the same opportunity for that instrument for a cooldown period (e.g. 24h or until config change), and log clearly so you can add the pair to an exclude list.

**No implementation:** These are design/plan only; no code or config has been changed.

---

### 3.2 ORDER_CANCEL_REJECT handling

**Evidence:** Several **ORDER_CANCEL_REJECT** entries in Oanda history (e.g. tickets 22576, 22733, 22741, 22749, 22752, 22761, 22775–22776, 22818, 22850). Broker rejected a cancel (e.g. order already filled, already cancelled, or in a state that cannot be cancelled).

**Intent alignment:** Local state (engine + UI) should stay in sync with broker; no assumption that “cancel” always succeeds.

**Suggestions:**

1. **On cancel request:** When the engine (or UI-triggered flow) sends a cancel, do not assume the order is cancelled until the broker confirms. If the API returns or the transaction stream shows ORDER_CANCEL_REJECT, treat the order as still active (or already filled) in local state.
2. **State update on ORDER_CANCEL_REJECT:** In any component that consumes OANDA transaction history or streaming events, handle ORDER_CANCEL_REJECT explicitly: keep the order in “pending” or “open” (or resolve via fill) so that duplicate logic and UI do not assume the order is gone.
3. **Avoid repeated cancel retries:** If a cancel is rejected, do not immediately retry cancel in a tight loop; back off (e.g. wait and re-sync with OANDA) to avoid log noise and unnecessary API load.

**No implementation:** Logic changes not implemented; only suggested.

---

### 3.3 Reduce cancel/replace churn (fewer cancels and re-places)

**Evidence:** Oanda history shows many **cancel-then-immediate-replace** sequences for the same pair (e.g. EUR/USD, GBP/USD) with the same or very similar parameters, often every ~2 minutes.

**Intent alignment:** One order per pair is correct; repeatedly cancelling and re-placing the same idea adds cost, log volume, and risk of ORDER_CANCEL_REJECT or fill/cancel races.

**Suggestions:**

1. **Replace only when needed:** If there is already a pending order for the same pair and same opportunity (or same “logical” trade):
   - Do **not** cancel and re-place every polling cycle unless:
     - Entry/stop/target have meaningfully changed (e.g. by config or market-state update), or
     - The order is considered stale (e.g. distance from current price &gt; threshold, or age &gt; max pending time).
2. **Staleness only:** If the only reason to cancel is “stale” (e.g. price moved &gt; N pips), then cancel and optionally re-place in one decision step; do not re-place the same levels on the next cycle if market state did not change.
3. **Configurable thresholds:** Make “stale” definition (pips or % from current price, max pending time) configurable so you can tune how often pending orders are replaced without changing code.

**No implementation:** No code or config changed.

---

### 3.4 Duplicate-block log noise (RED FLAG repetition)

**Evidence:** Scalp-engine logs show the same **RED FLAG: BLOCKED DUPLICATE - AUD/JPY BUY** every ~60 seconds while the same opportunity remains in market state and the pair already has an order.

**Intent alignment:** Blocking duplicates is correct; logging every cycle is noisy and can hide other issues.

**Suggestions:**

1. **Log once per “duplicate event”:** When blocking a duplicate for pair X, log at ERROR (RED FLAG) the first time for that pair in a given time window (e.g. 5–15 minutes); for subsequent blocks of the same pair in that window, log at DEBUG or do not log.
2. **Or:** After blocking, mark that “we already logged duplicate for this opportunity id / pair” and do not log again until the existing order is gone or the opportunity id changes.
3. **Keep RED FLAG for first occurrence:** So operational visibility is preserved without flooding.

**No implementation:** No changes made.

---

### 3.5 “Trade not opened” – clearer reason in logs

**Evidence:** Scalp-engine logs: “Trade not opened for GBP/JPY BUY (check above for 'Opportunity rejected' e.g. max_runs, or OANDA API)”. The actual reason is only implied (“check above”).

**Intent alignment:** Easier debugging and ops; one line should state why the trade was not opened.

**Suggestions:**

1. **Explicit reason in the same or next line:** When a trade is not opened, set a single reason code or short string (e.g. `max_runs`, `consensus_too_low`, `oanda_reject`, `validation_failed`, `stale_opportunity`, `duplicate_blocked`) and log it in the same message or the immediate next line, e.g. “Trade not opened for GBP/JPY BUY: reason=max_runs”.
2. **Avoid “check above” as the only hint:** Keep “check above” only as extra context; the primary reason should be in the “Trade not opened” line (or the line right after it).

**No implementation:** No code changed.

---

### 3.6 RL database init repeated every cycle

**Evidence:** “Enhanced RL database initialized: /var/data/scalping_rl.db” appears many times per minute in Scalp-engine logs, once per opportunity or per check.

**Intent alignment:** DB should be initialized once per process (or per worker), not on every opportunity evaluation.

**Suggestions:**

1. **Lazy singleton or process-level init:** Initialize the RL (or “Enhanced RL”) DB connection or helper once per process (or once per worker if multi-worker), and reuse it for all opportunity checks.
2. **Log init once:** Log “Enhanced RL database initialized” only at first use (or at startup), not on every read/write.

**No implementation:** No code changed.

---

### 3.7 Config API and POST /trades polling volume

**Evidence:** Config-API logs show GET /config and POST /trades very frequently (about every minute) from multiple client IPs, and many “Trade states saved to disk” / “Trade states updated in memory” lines.

**Intent alignment:** Config and trade state should stay in sync without unnecessary load or log volume.

**Suggestions:**

1. **Polling interval:** Consider increasing the interval for GET /config and POST /trades (e.g. 60s for trades, 30s for config) if the current interval is lower, to reduce requests and log lines while still keeping UI and engine in sync.
2. **Single source of truth:** Ensure only one type of client (e.g. UI) is responsible for POST /trades at a given time, or that multiple clients do not poll at the same high frequency from different IPs unless intended.
3. **Log level for routine sync:** Consider logging “Trade states updated in memory” at DEBUG so normal operation does not dominate logs; keep INFO for config changes or errors.

**No implementation:** No config or code changed.

---

### 3.8 Log endpoints 404 (engine and oanda logs)

**Evidence:** Config-API logs: “No log files found for engine in /var/data/logs with patterns ['scalp_engine_*.log']” and “No log files found for oanda …” → GET /logs/engine and GET /logs/oanda return 404.

**Intent alignment:** UI or ops expect to read engine and OANDA logs from the API; 404 suggests log paths or file names do not match.

**Suggestions:**

1. **Align log paths and patterns:** Ensure the engine and any OANDA logger write to `/var/data/logs` (or the path the API uses) with filenames that match the patterns the API looks for (e.g. `scalp_engine_*.log`, `oanda_*.log`). Document the expected paths and patterns in one place (e.g. deployment or ops doc).
2. **Or adjust API patterns:** If logs are written elsewhere or with different names, change the log-serving API to look in the actual directory and use the actual naming pattern.
3. **Graceful 404:** If logs are optional (e.g. not deployed in some environments), keep 404 but document that engine/oanda logs may be unavailable; UI could show “Logs not available” instead of a generic error.

**No implementation:** No path or code changed.

---

### 3.9 UI database ephemeral (scalping_rl.db recreated)

**Evidence:** Scalp-engine UI logs: “Creating new database: scalping_rl.db” on new instances/deploys; “Opening existing database” on later requests. On Render (or similar), instances are ephemeral, so the DB is recreated when the instance is new.

**Intent alignment:** If RL or other state in that DB is important across restarts, it should persist; otherwise it should be clear that it is ephemeral.

**Suggestions:**

1. **Document behavior:** In USER_GUIDE or deployment docs, state that `scalping_rl.db` (or the UI DB) is created on first use and may be recreated on new deploys/restarts if there is no persistent volume; any critical state should not rely on it unless persistence is configured.
2. **Optional persistent volume:** If you need RL or UI state across restarts, configure a persistent volume (e.g. Render disk) for the path that contains the DB and document it.
3. **Avoid “critical” state in ephemeral DB:** Do not store the only copy of trade state or config in this DB if the process is ephemeral; keep trade state in Config API / POST /trades and config in Config API.

**No implementation:** No code or infra changed; documentation suggestions only.

---

### 3.10 Streamlit “Session already connected”

**Evidence:** UI logs: “Session with id … is already connected! Connecting to a new session.”

**Intent alignment:** Clean session handling; avoid duplicate or confusing connections.

**Suggestions:**

1. **Document:** In USER_GUIDE or troubleshooting, note that this message can appear when multiple tabs or reconnects use the same session id; recommend one tab per session or refresh if behaviour is odd.
2. **Optional:** If Streamlit APIs allow, consider session affinity or a single connection per session to reduce “already connected” events; implement only if you see real UX issues.

**No implementation:** No code changed.

---

### 3.11 Claude analysis failures (Trade-Alerts)

**Evidence:** Trade-Alerts logs: “Error with Claude analysis: All Claude models failed” (multiple times).

**Intent alignment:** Consensus and required_llms depend on LLM sources; when one source (Claude) is down, the system should degrade gracefully and operators should be aware.

**Suggestions:**

1. **Fallback or skip Claude:** In Trade-Alerts, when Claude fails, either skip Claude for that run and use other LLMs only (with a clear log line like “Claude unavailable; using other LLMs”), or mark “Claude” as temporarily unavailable so consensus is not incorrectly reduced.
2. **Alerting:** Optionally add a simple alert (e.g. log at WARNING/ERROR and/or send to a channel) when “All Claude models failed” so you can fix API keys or quotas.
3. **Do not silently treat as “no opinion”:** Avoid treating repeated Claude failures as “Claude says nothing” without logging; that can make consensus look different from reality.

**No implementation:** No code changed in Trade-Alerts.

---

### 3.12 Config “last updated” visibility

**Evidence:** Config-API logs show “Config served from memory (Mode: AUTO, updated: 2026-02-24T23:42:00.075759)” while logs are from 2026-02-25 — config may be unchanged for a long time.

**Intent alignment:** Users should know when config was last updated so they can tell if their changes were applied.

**Suggestions:**

1. **Show in UI:** In the Configuration tab (or footer), display “Config last updated: &lt;timestamp&gt;” from the Config API response so users see when the running config was last changed.
2. **Optional warning:** If “last updated” is older than e.g. 24 hours, show a low-severity notice (“Config has not been updated in 24h”) so users know they might be on an old snapshot (e.g. after a deploy that did not reload config).

**No implementation:** No UI or API changed.

---

## 4. Summary Table

| # | Area | Main suggestion | Implemented? |
|---|------|------------------|--------------|
| 3.1 | Broker allow-list / USD/CNY | Filter or block non-tradeable pairs (e.g. USD/CNY); cooldown after reject | No |
| 3.2 | ORDER_CANCEL_REJECT | Update state when cancel is rejected; no assume-cancelled; backoff retries | No |
| 3.3 | Cancel/replace churn | Replace only when params or staleness require it; configurable thresholds | No |
| 3.4 | Duplicate RED FLAG noise | Log duplicate block once per pair per time window (or per opportunity id) | No |
| 3.5 | “Trade not opened” | Log explicit reason (max_runs, oanda_reject, etc.) in same/next line | No |
| 3.6 | RL DB init | Init once per process; log init once | No |
| 3.7 | Config/trades polling | Consider longer intervals; DEBUG for routine sync logs | No |
| 3.8 | Log 404 (engine/oanda) | Align log paths/patterns with API; document or adjust API | No |
| 3.9 | UI DB ephemeral | Document; optional persistent volume; don’t rely on it for critical state | No |
| 3.10 | Streamlit session | Document “already connected”; optional session handling | No |
| 3.11 | Claude failures | Fallback or skip Claude + alerting; don’t silently degrade consensus | No |
| 3.12 | Config last updated | Show in UI; optional staleness warning | No |

---

## 5. Next Steps

- Review each suggestion and decide which to adopt.
- For each approved item, implement in small steps and test (e.g. one improvement per PR).
- Re-run with Manual logs after changes to confirm behaviour and log volume.

**No changes to the system have been implemented without your approval.**
