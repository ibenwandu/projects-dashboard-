# Market State Stale – Comprehensive Correction Plan

When the UI shows **"Market State is Stale"** (e.g. 768 hours), the market state used by Scalp-Engine is older than 4 hours. This document ties together diagnosis, workarounds, root-cause fixes, and prevention.

---

## 1. What’s Wrong

- **UI/engine** treat state as **stale** when its timestamp is older than **4 hours**.
- **State is produced** by Trade-Alerts **Step 9**: MarketBridge exports to file and/or POSTs to market-state-api.
- If Trade-Alerts doesn’t run, fails before Step 9, or Step 9 fails, the state file/API is not updated and the UI will show stale.

---

## 2. Diagnosis

### 2.1 How does the UI get state?

- **API:** If `MARKET_STATE_API_URL` is set, Scalp-Engine can load state from the market-state API.
- **File:** If using file, it uses `MARKET_STATE_FILE_PATH` (e.g. `/var/data/market_state.json`).

**Action:** Determine whether the UI is configured for **API** or **file**, and that Trade-Alerts writes to the same target (same path or same API).

### 2.2 Did Trade-Alerts run?

- Check Trade-Alerts logs for the scheduled run time (e.g. 4:00 PM EST):
  - `=== Scheduled Analysis Time: ... ===`
  - Step 1 through Step 9 messages.
- Confirm Step 9 ran and succeeded:
  - `Step 9 (NEW): Exporting market state for Scalp-Engine...`
  - `✅ Market State exported to ...` and/or `✅ Market state sent to API successfully`.

### 2.3 Path/API consistency

- **Trade-Alerts:** `MARKET_STATE_FILE_PATH`, `MARKET_STATE_API_URL`, `MARKET_STATE_API_KEY`.
- **market-state-api:** Must serve the same state that Trade-Alerts writes (file or in-memory from POST).
- **Scalp-Engine UI:** `MARKET_STATE_API_URL` vs `MARKET_STATE_FILE_PATH` must point to the same source the API uses, or directly to the file.

---

## 3. Immediate Workarounds

- **Refresh timestamp only (temporary):**  
  From Trade-Alerts repo root:  
  `python update_market_state_timestamp.py`  
  (Only updates timestamp; bias/regime/opportunities stay old.)

- **Minimal valid state (testing):**  
  Write a minimal `market_state.json` with current `timestamp`, `global_bias`, `regime`, `approved_pairs`, `opportunities` as needed. See `DIAGNOSE_MISSING_MARKET_STATE.md` for an example.

- **One full refresh:**  
  Run `python run_immediate_analysis.py` so a full analysis runs and Step 9 exports/POSTs fresh state.

---

## 4. Root-Cause Fixes

1. **Trade-Alerts runs on schedule**  
   - Service is running; no restarts during the 5-minute analysis window.  
   - `ANALYSIS_TIMES` and `ANALYSIS_TIMEZONE` (e.g. `America/New_York`) are correct in scheduler config.

2. **No failure before Step 9**  
   - Fix any failures in Steps 1–8 (Drive, LLMs, email, parser, etc.) so the pipeline reaches Step 9.

3. **Step 9 succeeds**  
   - **File:** Write permissions and path; `MARKET_STATE_FILE_PATH` set and directory exists (e.g. `/var/data`).  
   - **API:** `MARKET_STATE_API_URL` (and `MARKET_STATE_API_KEY` if required) correct; network and API service up.

4. **Path/API alignment**  
   - If using **shared disk:** Trade-Alerts and Scalp-Engine (and market-state-api if used) all use the same `MARKET_STATE_FILE_PATH`.  
   - If using **API only:** Trade-Alerts POSTs to market-state-api; UI/engine use `MARKET_STATE_API_URL` and do not rely on a local file path for that state.

5. **Scheduler configuration**  
   - Verify `ANALYSIS_TIMES` and `ANALYSIS_TIMEZONE` in `src/scheduler.py` and in environment so runs occur at the intended times.

---

## 5. Prevention and Monitoring

- **Health check / alert:**  
  From Trade-Alerts root run: `python check_market_state_age.py` (optionally `--max-age-hours 4` or `--path /var/data/market_state.json`). Exits 0 if state is fresh, 1 if stale or missing. Use in cron or Render health checks to alert when state age > 4 hours.

- **Logging:**  
  - Step 9 and MarketBridge already log success/failure and path/API.  
  - Ensure logs are visible where Trade-Alerts runs (e.g. Render logs) so you can confirm “Market State exported” and “Market state sent to API” when applicable.

---

## 6. Checklist

- [ ] Confirm whether UI loads state from **API** or **file** (`MARKET_STATE_API_URL` vs `MARKET_STATE_FILE_PATH`).
- [ ] Check Trade-Alerts logs for scheduled run and Step 9 success.
- [ ] Fix pipeline so analysis completes and Step 9 runs (permissions, path, API URL/key).
- [ ] Apply workaround if needed (e.g. `update_market_state_timestamp.py` or `run_immediate_analysis.py`).
- [ ] Verify env vars and path/API alignment across Trade-Alerts, market-state-api, and Scalp-Engine.
- [ ] Add or run monitoring (e.g. `check_market_state_age.py`) when state age > 4 hours.

---

## Related Docs

- **Diagnosis and step-by-step checks:** `DIAGNOSE_MISSING_MARKET_STATE.md`
- **Timestamp-only workaround:** `UPDATE_MARKET_STATE_TIMESTAMP.md`
- **Market state delivery (file vs API):** `MARKET_STATE_DELIVERY_EXPLAINED.md`
