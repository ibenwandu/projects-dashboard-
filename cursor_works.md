# Cursor Works – Session Notes (Personal Folder)

This file records interactions, plans, and fixes implemented across projects under the personal folder so future sessions have context.

**Last updated:** Part 26 (Mar 17, 2026) — Added Scalp-Engine execution guardrail to block orders when entry price is too far from live OANDA prices, plus full Trade-Alerts backup for rollback.

**Quick reference — Parts:**

| Part | Topic | Summary |
|------|--------|--------|
| 1 | BackupRenderLogs | Render/Oanda log backup to Manual logs; schedule, hygiene, env wrapper, fixes (API/CLI, encoding, Oanda, etc.). |
| 2 | cursor3 (Scalp-Engine) | Log throttles, RED FLAG 30 min, close/orphan logs, USER_GUIDE §§9–11. |
| 3 | Cursor4 / consol-recommend4 | Manual logs review; consolidated plan (Cursor4 + Anthropic4); Phase 0–4; JPY bug; plan only then implementation. |
| 3 (cont.) | consol-recommend4 Implementation | Phase 1.1 (JPY), 1.4, 2.1–2.6, 2.3, 3.x docs; max_runs verified. |
| 5 | EUR/USD ATR + Duplicates | Issues: ATR trailing not updating; two EUR/USD SHORT; proposed fixes (cursor5 addressed these). |
| 6 | cursor5 Implementation | max_trades (open only), pre-open OANDA check, add-before-send, ATR OrderCreate, pending-to-open sync, 5.6–5.9. |
| 7 | cursor6 Plan + Backup | Manual logs review → suggestions from cursor6.md (5.1–5.7); backup_cursor6_20260304; no implementation. |
| 8 | cursor6 Implementation | Plan 5.1–5.6: Open/Pending display, trailing check/ALREADY_EXISTS, stale cooldown, 502 handling, AUD/CHF doc, UI DB DEBUG. |
| 9 | User-Reported Fixes | max_trades final gate (never > UI limit); trailing only when ≥1 pip profit; final duplicate (pair,direction) check; commit 19f15a3. |
| 10 | Multiple pending same pair / UI one row | Final gate checks OANDA **pending orders** (not only open positions); `get_pending_orders()` on TradeExecutor; USER_GUIDE §10(d) UI/store by trade_id. |
| 11 | Indeed-jobs: same results + already-reported filter | days_posted 3; `output/reported_job_ids.txt`; exclude previously reported job IDs from score/report; `--include-reported`; README. |
| 12 | Manual logs + .odt + improvementplan comparison | Manual logs folder; .odt read method; comparison with improvementplan.md; trailing-stop evidence from ODT screenshots and logs (Phase 0.5). |
| 13 | Improvement plan implementation (Fixes 1–3) | max_runs legacy key (Fix 1), MACD guard (Fix 2), JPY MARKET sanity (Fix 3); commit 35e7ec8; Fix 4 blocked. |
| 14 | 3× GBP/USD on OANDA, 1 on UI/logs | Load PENDING trades from state file on startup; USER_GUIDE §10(d) engine-load note. |
| 15 | Orphan/duplicate cleanup; single (pair, direction) | Cleanup on every sync: close extra open positions, cancel extra pending orders per (pair, direction); never allow multiple same pair on OANDA or UI. |
| 16 | ATR_TRAILING immediate activation (Fix 4) | Phase 0.5 complete; min age 120s + OANDA P/L gate in `_check_ai_trailing_conversion()`; improvementplan Fix 4 implemented. |
| 17 | No pending when pair has open | Once a pair has an open position, no pending order allowed until closed/cancelled; block on place, cancel on sync (8dc6d3d); hardening: final gate by pair, replace-pending skip, early skip in loop (560a98c). |
| 18 | Research implementation (Phases 0–3) | Phase 0: USER_GUIDE target exit, research index, safety note. Phase 1: risk-based position size, 2% daily limit, 5-loss circuit breaker, config strip. Phase 2: BE +40 pips, trail +70 pips (defaults now tuned from 50/100), verification logging. Phase 3: ATR TP, half-and-run, max hold, safety doc. Commit aadbddb + tuning commit d3fb27c. |
| 19 | ATR_Trailing conversion fix | Convert only after meaningful profit; default 100 pips when config missing (never 1 pip); require profit >= max(activation, trailing distance) so initial stop never below entry; avoids tiny cushion on retrace. Commit 4d2330b. |
| 20 | Glassdoor-jobs | Replicated Linkedin-jobs pipeline for Glassdoor (search → scrape → score → report → resumes). Search works; job pages hit Cloudflare "Help Us Protect"; all scrapes skipped. See Part 20 for details and next steps. |
| 21 | job-alert-resume | Gmail → Indeed job alerts → scrape → score (Gemini/OpenAI) → report → tailored resumes + PDF + job_links; schedule 7 AM/7 PM EST. Indeed redirect/unwrap fixes; OpenAI option; PDF export; workflow_run.log. See Part 21. |
| 22 | Scalp-Engine: pnl_pips DB migration | Render logs showed sqlite3.OperationalError: no such column: pnl_pips in daily_learning → update_outcome_simulated. Cause: existing DBs created before pnl_pips was in schema; migration list in _init_db() omitted pnl_pips. Fix: add ('pnl_pips', 'REAL') to new_columns in scalping_rl_enhanced.py. Commit dd47b44 (Trade-Alerts). |
| 23 | Manual logs analysis + DeepSeek parser fix + logging | Manual logs review (Mar 9-11): DeepSeek parser failure (0 opportunities parsed), RL learning blocked (0 evaluated recommendations), missing trade close logs, excessive max_trades_limit warnings. Plan: suggestions from cursor7.md. Priority 1: Fix DeepSeek parser (Pattern Set 10, MACHINE_READABLE JSON request, enhanced extraction) - COMPLETE. Priority 2: Improve logging (trade close audit logs, ATR trailing logs verified, max_trades_limit throttle) - COMPLETE. Backup: backup_before_cursor7_20260311_162509. Commits: fb2d8b1 (Priority 1), 83b685b (Priority 2). Verification pending before Priority 3. |
| 24 | Google Drive token + ATR trailing default | Resolved `invalid_grant` and “Drive reader not enabled” by generating a new Google Drive refresh token with the same desktop OAuth client as Render, and by aligning `GOOGLE_DRIVE_CREDENTIALS_JSON` (client_id/client_secret/auth_uri) between local script and Render env. Also lowered ATR_TRAILING fallback activation from 100 pips to 40 pips when `trailing_activation_min_pips` is unset, and updated scalp-engine weekend cleanup to sync with OANDA before closing trades and log open-trade counts. |
| 25 | Consensus config change logging | `config_api_server.update_config()` now logs every config save with `Min Consensus`, `Required LLMs`, and the client IP, so future sessions can see exactly when and from where consensus settings (e.g. `min_consensus_level` flipping 2→1) were changed. |
| 26 | Scalp-Engine execution guardrail + backup | Created `backup_before_execution_guard_20260317_rollback` snapshot of the entire Trade-Alerts repo, then updated Scalp-Engine `TradeExecutor.open_trade` to call OANDA `get_current_price()` and *skip* placing any order when the intended entry price is more than 10 pips or 0.10% away from the current mid price (logs `price_mismatch` and leaves `_last_reject_reason` set for diagnostics). |

---

## Log review checks (expected when reviewing Manual logs)

When asked to **review the logs**, future sessions should perform checks like these (aligned with Manual logs and cross-touchpoint consistency):

- **Max trades:** Never more open positions than UI `max_trades`; logs show "Open: X/Y, Pending: P" (not "Active: 6/4"); ERROR if OANDA > max_trades; BLOCKED when at limit.
- **Consensus config:** `min_consensus_level` (and `required_llms`) is a **config/UI setting**, not a code constant. To change consensus behavior, update it via the Scalp-Engine UI / Config API only; do **not** hard‑code thresholds in engine logic.
- **Trailing stop:** Trailing only activated when trade is in profit (≥1 pip), never in loss or before breakeven; look for "converted to trailing stop" only after profit; USER_GUIDE §17.
- **Duplicate (pair, direction):** No multiple open or **pending** orders for same pair/direction on OANDA; final gate blocks with "BLOCKED DUPLICATE (final check)" or "BLOCKED DUPLICATE (final check – pending)"; has_existing_position and pre-open check include pending orders.
- **No pending when pair has open:** Once a pair has an open position, no pending order (LIMIT/STOP) is allowed for that pair until the open is closed or cancelled. Block on place: "BLOCKED: {pair} already has an open position. No pending order allowed until that position is closed or cancelled." Final gate (before send): "🚫 BLOCKED (final check): {pair} already has an open position on OANDA. No pending order allowed until it is closed or cancelled." Replace-pending path: "🔄 Skipping replace for {pair} {direction}: pair has an open position. No pending allowed until it is closed or cancelled." On sync, cleanup cancels any pending order for a pair that has an open: "🧹 Cleaned up pending order: {pair} (pair has open position, no pending allowed)". Main loop skips opportunities for pairs with an open (DEBUG: "Skipped {pair} {direction} - pair already has an open position (no second open/pending allowed)").
- **UI vs OANDA alignment:** If OANDA shows multiple tickets for same pair (e.g. two USD/JPY SELL LIMIT) but UI shows one row, the list must be one entry per `trade_id`/order ID (store/display by ID, not merge by (pair, direction)); USER_GUIDE §10(d).
- **Stale-order loop:** No cancel-then-replace same level within cooldown (cursor6 §5.3); "Skipping re-place after stale cancel" when applicable.
- **TRAILING_STOP_LOSS_ORDER_ALREADY_EXISTS:** Check before create; ALREADY_EXISTS treated as success; reject count in OANDA transactions should drop (cursor6 §5.2).
- **502/5xx:** No raw HTML in logs; WARNING with truncated message and retry (cursor6 §5.5).
- **Circuit breaker (Part 18):** After 5 consecutive losses, new opens blocked; logs show "Circuit breaker: N consecutive losses (max 5). No new opens until next win or daily reset."; `record_trade_close` logs "consecutive_losses: N".
- **Daily loss % (Part 18):** When `max_daily_loss_pct` set, opens blocked if daily loss ≥ that % of account; "Daily loss limit reached (X% >= Y% of account)".
- **Risk-based position size (Part 18):** When balance and SL pips available, units from formula; optional config: `trading_phase`, `risk_percent_per_trade`, `account_balance_override`.
- **ATR_Trailing conversion (Part 19):** Conversion only when profit >= max(trailing_activation_min_pips, trailing distance); with current defaults `trailing_activation_min_pips = 70` (BE at 40 pips) and a fallback activation of 100 pips only when config is missing. Log: "ATR Trailing: attempting conversion ... profit >= X.X pips (activation/distance), trailing distance=Y.Y pips". Initial trailing stop never below entry.
- **DeepSeek parser (Part 23 Priority 1):** When reviewing logs, confirm DeepSeek extracts >0 opportunities (not "0 opportunities parsed"); DeepSeek appears in consensus; DeepSeek recommendations logged to RL database. Look for: "DeepSeek: X opportunities parsed" where X > 0; DeepSeek in market state; DeepSeek in consensus calculation.
- **Logging improvements (Part 23 Priority 2):** When reviewing logs, confirm max_trades_limit warnings are throttled (first WARNING, subsequent DEBUG per 15 min window); trade close audit logs appear (`📋 Trade closed: {pair} {direction} exit_reason={reason} final_PnL={final_pnl}`); hourly open trades status logs appear (`📊 Open trades status (N open):` with ages and PnL). Look for: `⏭️ Skipped ... (throttled)` at DEBUG; `🔧 close_trade() called:` DEBUG logs; reduced max_trades_limit spam.

---


# Part 1: BackupRenderLogs

---

## Goal

Back up **Render service logs** and **Oanda data** to a local folder (`C:\Users\user\Desktop\Test\Manual logs`) on a schedule (5:00 AM and 5:00 PM EST) with a PowerShell script and Windows Task Scheduler, for an **end-to-end view** of the trading pipeline. Keep the Manual logs folder from growing indefinitely via hygiene (move files older than 7 days to an archive).

---

## Initial Problem

- Script: `C:\Users\user\projects\personal\BackupRenderLogs.ps1`
- Render CLI installed at: `C:\Users\user\render-cli`
- Scheduled task: 5:00 PM and 5:00 AM EST
- **No backup files were being created** in the Manual logs folder.

---

## Fixes Implemented (Chronological)

### 1. API returned 404 / 400 for logs

- **Issue:** Script called Render REST API for logs; got **404 Not Found** or **400 Bad Request** (e.g. "invalid path deployId", "invalid path serviceId").
- **Fix:** Stopped using query params (`?deployId=`, `?serviceId=`). Script now only tries path-based log URLs and treats the API as optional fallback. Primary method is the **Render CLI**, not the API.

### 2. Two different Render CLIs

- **Issue:** User had the **Deno-based** CLI (render-oss/render-cli) with `render services tail --id <serviceId>`. It had no top-level `render logs`; required `--unstable-net` for WebSocketStream and sometimes returned errors.
- **Fix:** Installed the **official Go-based CLI** (render-oss/cli) from GitHub releases and pointed the script at it first. Official CLI uses `render logs -r <serviceId> -o text` and is more reliable.

### 3. Official CLI installation

- **Action:** Downloaded **v2.10** Windows amd64 zip from https://github.com/render-oss/cli/releases, extracted to `C:\Users\user\render-cli-official`, and copied `cli_v2.10.exe` to `render.exe` so the script’s path works.
- **Config:** `$renderExePathOfficial = "C:\Users\user\render-cli-official\render.exe"` (tried first); `$renderExePath = "C:\Users\user\render-cli\render.exe"` (Deno fallback).

### 4. Official CLI required `--id` / `-r` and workspace

- **Issue:** Deno CLI’s `services tail` needs `--id <serviceId>` (not positional). Official CLI’s `logs` needs `-r` / `--resources` in non-interactive mode and a **workspace** set.
- **Fix:**
  - Script now passes `--id` for the Deno CLI and `-r` / `--resources` for the official CLI.
  - Script fetches workspace ID from `GET https://api.render.com/v1/owners` and runs `render workspace set <workspaceId> --confirm` once before fetching logs so the official CLI has an active workspace.

### 5. PowerShell “render not found” suggestion

- **Issue:** When run from `C:\Users\user\render-cli`, script sometimes invoked bare `render`; PowerShell suggested using `.\render`.
- **Fix:** When adding the “render from PATH” candidate, the script now uses the full path from `(Get-Command "render").Source` so it never calls `render` without a path.

### 6. Log limit and file sizes

- **Issue:** User wanted ~24h coverage between 5 PM and 5 AM runs. Script used default 100 lines, then was set to 15,000; file sizes didn’t increase.
- **Cause:** Render API rejects limits above **1000** (“invalid limit: too large”). Using 15,000 caused the request to fail and fall back to default 100.
- **Fix:** Set `$logsLimit = 1000` (Render’s maximum). Each backup now requests up to 1000 lines per service. README updated to state the 1000 cap and that 24h coverage depends on log volume and the two runs per day.

### 7. Strange characters in backup files

- **Issue:** Garbled prefixes in logs (e.g. `=fôè`, `「\1`, `TÜán Å`, `ΓÅ¡nÅ` before “Skipped”) from ANSI color/format codes and encoding.
- **Fix:**
  - Added `Remove-AnsiSequences` to strip ANSI escape sequences (e.g. `ESC [ 32 m`) from log content before writing to file.
  - Set `NO_COLOR=1` when calling the CLI to reduce colored output.
  - Documented in README.

### 8. “Future” dates (2026-03-01) in logs

- **Observation:** Filename says `2026-02-28_1911` but log lines show `2026-03-01 00:03:53`.
- **Explanation:** Log timestamps are in **UTC**. 7:11 PM EST on Feb 28 = 00:11 UTC on March 1, so 2026-03-01 in the file is correct. No code change; optional note at top of backup files could be added later if desired.

### 9. PowerShell parse errors (Oanda block)

- **Issue:** Script failed to parse with "Unexpected token", "Missing closing '}'", "The ampersand (&) character is not allowed".
- **Causes:** (1) Unicode en-dash (–) in string literals parsed as minus; (2) semicolon-heavy one-liner in catch block parsed as pipeline; (3) `&` in URL query string (`&to=`) interpreted as PowerShell call operator.
- **Fix:** Replaced en-dashes with ASCII hyphen in all Oanda-related strings. Split catch block into multiple statements. Built Oanda transaction URL by first assigning `[uri]::EscapeDataString(...)` to variables then using them in the URL string so `&` stays inside the string.

### 10. Render 401 and Oanda 400/403; startup visibility

- **Issue:** User saw 401 Unauthorized for all Render services; Oanda returned 400 "Invalid value specified for 'accountID'" then 403 Forbidden.
- **Fixes:** (1) **Render:** Warn at startup if `RENDER_API_KEY` not set; trim API key. On any 401/Unauthorized, append hint: `[Check RENDER_API_KEY is set and valid.]` (2) **Oanda:** Trim token and account ID; treat empty account ID as "not set". On 400 with "accountID"/"Invalid value", append hint about format `XXX-XXX-XXXXXXX-XXX`. On 403/Forbidden, append hint about token/account access or wrong env. (3) **Startup:** Script prints "Render: API key from env (length N)" or "fallback in script..."; "Oanda: accountID='...' env=practice" or "transactions skipped".

### 11. Oanda: same token as trading system; account ID must match

- **Context:** User could not revoke token (used by Trade-Alerts and Scalp-Engine). Oanda 403 was due to **account ID mismatch**: token was for account `101-002-38030127-001` (Oanda Hub) but script used `101-004-1234567-001`.
- **Resolution:** Use the **same** `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` as in Render env for Scalp-Engine/Trade-Alerts. No revoke needed; backup only reads transactions. Account ID must match the account the token can access. Manage API Access: Hub → Profile settings (or gear) → Personal Token at `https://hub.oanda.com/tpa/personal_token`.

### 12. Oanda app log (oanda_*.txt) vs transactions (oanda_transactions_*.json)

- **Observation:** Two Oanda outputs; one valid data, the other "could not be fetched" despite Config API 200.
- **Clarification:** `oanda_transactions_*.json` = **valid** (Oanda REST API, last 24h). `oanda_*.txt` = **app log** from Config API (Scalp-Engine Oanda component); often **empty** (200 with 0 bytes).
- **Fix:** When Config API returns 200 with empty body, script writes: "(Oanda app log empty - Config API returned 200 with no content...)" instead of "could not be fetched (Config API returned 200)".

### 13. Hygiene: keep Manual logs folder from growing

- **Requirement:** Move files older than 7 days to another folder; leave one file untouched.
- **Implementation:** At end of each run, move all **files** in Manual logs with **LastWriteTime** older than **7 days** to `C:\Users\user\Desktop\Test\Manual Logs Archive`. **Excluded:** `"Additional quality checks to review using the Logs.txt"` (never moved). Config: `$archiveDir`, `$hygieneExcludeFileName`, `$hygieneDaysToKeep` (default 7). Archive created on first move; failures in `error_log.txt`.

### 14. Oanda JSON missing when scheduled task runs (1 PM, 5 AM, etc.)

- **Observation:** At 1 PM (and other task run times), `oanda_*.txt` and Render logs were created but `oanda_transactions_*.json` was not.
- **Cause:** The scheduled task runs in a **different process** and does **not** inherit the user's interactive session environment. So `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` are unset when the task runs, and the script skips Oanda transaction backup.
- **Fix:** Use a **wrapper script** and a **local env file**: (1) `RunBackupRenderLogs.ps1` loads `BackupRenderLogs.env.ps1` (if present) to set env vars, then runs `BackupRenderLogs.ps1`. (2) User copies `BackupRenderLogs.env.ps1.example` to `BackupRenderLogs.env.ps1` and sets `RENDER_API_KEY`, `OANDA_ACCESS_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_ENV`. (3) Scheduled task runs the wrapper: `-File "C:\Users\user\projects\personal\RunBackupRenderLogs.ps1"`. (4) `BackupRenderLogs.env.ps1` is in `.gitignore` so it is not committed.

---

## Current Script Behavior (Summary)

1. **Config:** API key (env `RENDER_API_KEY` or fallback in script), backup dir `C:\Users\user\Desktop\Test\Manual logs`, archive dir `Manual Logs Archive`, hygiene exclude file and days (7), official CLI path, Deno CLI path, `$logsLimit = 1000`.
2. **Startup:** Prints Render key source (env vs fallback) and Oanda accountID/env or "transactions skipped".
3. **Workspace:** Fetches first owner from `GET /v1/owners`, runs `render workspace set <id> --confirm` once if official CLI exists.
4. **Per service:** Gets latest deploy ID from API; then tries (in order): Official CLI, Deno CLI, API. Before writing: strips ANSI, writes UTF-8; on failure, placeholder and `error_log.txt`.
5. **Oanda:** (a) GET Config API `/logs/oanda` → `oanda_YYYY-MM-DD_HHmm.txt` (app log; often empty → friendly message). (b) If `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` set: GET Oanda API transactions (last 24h) → `oanda_transactions_YYYY-MM-DD_HHmm.json`.
6. **Hygiene:** Move files in Manual logs with LastWriteTime older than 7 days to Manual Logs Archive; exclude `"Additional quality checks to review using the Logs.txt"`.

---

## Oanda backup (end-to-end view)

- **Env vars (optional for transactions):** `OANDA_ACCESS_TOKEN`, `OANDA_ACCOUNT_ID` (format `XXX-XXX-XXXXXXX-XXX`; must match account the token can access, e.g. from Oanda Hub). `OANDA_ENV` = `practice` (default) or `live`. `CONFIG_API_BASE_URL` = Config API base (default `https://config-api-8n37.onrender.com`). Use **same** token as Trade-Alerts/Scalp-Engine; no need to revoke.
- **Two outputs:** (1) **oanda_*.txt** = app log from Config API `/logs/oanda` (Scalp-Engine Oanda component); often empty → script writes friendly "app log empty" message. (2) **oanda_transactions_*.json** = last 24h from Oanda REST API (orders, fills, cancels); this is the one with valid broker-side data.

---

## Key Files

| File / path | Purpose |
|-------------|--------|
| `BackupRenderLogs.ps1` | Main backup script (Render + Oanda + hygiene) |
| `BackupRenderLogs-README.md` | Setup, schedule, timeframe, troubleshooting |
| `C:\Users\user\render-cli-official\render.exe` | Official Render CLI (preferred) |
| `C:\Users\user\render-cli\render.exe` | Deno CLI (fallback) |
| `C:\Users\user\Desktop\Test\Manual logs\` | Backup output folder |
| `C:\Users\user\Desktop\Test\Manual Logs Archive\` | Files older than 7 days moved here by hygiene |
| `Manual logs\error_log.txt` | Timestamped failure log |
| `Manual logs\Additional quality checks to review using the Logs.txt` | Excluded from hygiene (never moved) |
| `RunBackupRenderLogs.ps1` | Wrapper: loads env from `BackupRenderLogs.env.ps1` then runs main script (use in scheduled task) |
| `BackupRenderLogs.env.ps1` | Local env vars (not committed); copy from `.env.ps1.example` and fill in keys |
| `BackupRenderLogs.env.ps1.example` | Example env file for Render + Oanda vars |

---

## Scheduled Task

- **Triggers:** Daily at 5:00 AM and 5:00 PM (EST).
- **Action:** Run `powershell.exe` with `-NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\projects\personal\BackupRenderLogs.ps1"`.
- **Environment:** Set `RENDER_API_KEY` for the task (or in user env) so the script doesn’t need the key in the file.

---

## Services in Script

- config-api  
- market-state-api  
- scalp-engine-ui  
- scalp-engine  
- trade-alerts  

(Service IDs are defined in the `$services` hashtable in the script.)

---

## Changelog (session summary)

- **Oanda backup:** Added (1) Oanda app log from Config API (`oanda_*.txt`), (2) optional Oanda transaction history from Oanda API (`oanda_transactions_*.json`) when `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` set. Same token as Trade-Alerts/Scalp-Engine; account ID must match token (e.g. `101-002-38030127-001` from Hub).
- **PowerShell parse fixes:** Unicode en-dash → ASCII hyphen; catch block split; Oanda URL built with variables to avoid `&` parsed as call operator.
- **401/400/403 handling:** Startup warning if no RENDER_API_KEY; trim keys/account ID; inline hints on 401 (Render key), 400 (account ID format), 403 (token/account access). Startup prints key source and Oanda accountID/env.
- **Oanda app log empty:** When Config API returns 200 with no content, write friendly "app log empty" message instead of "could not be fetched".
- **Hygiene:** Move files in Manual logs older than 7 days to `Manual Logs Archive`; exclude `"Additional quality checks to review using the Logs.txt"`. Config: `$archiveDir`, `$hygieneExcludeFileName`, `$hygieneDaysToKeep`.
- **Oanda JSON when task runs:** Scheduled task does not get session env vars. Use `RunBackupRenderLogs.ps1` as the task script and create `BackupRenderLogs.env.ps1` from the example with Render + Oanda keys so `oanda_transactions_*.json` is created on every run.

*Last updated: session documenting all plans, implementations, and fixes for future context.*

---

# Part 2: Scalp-Engine / Trade-Alerts – Suggestions from Cursor3 Implementation

---

## Goal of This Session

Implement the improvement plan from **`suggestions from cursor3.md`** (Round 4) in the Scalp-Engine folder under **Trade-Alerts** (`personal\Trade-Alerts\Scalp-Engine`), without changing consensus/required_llms logic, config object passed to `TradeConfig`, or `open_trade()` return signature. Context was taken from **CLAUDE.md** (Trade-Alerts) and **cursor_works.md** (BackupRenderLogs / personal).

---

## Plan Source and Constraints

- **Source:** `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor3.md`
- **Context used:** CLAUDE.md (Trade-Alerts), personal/cursor_works.md, and prior suggestion docs (cursor, cursor1, cursor2). Manual logs (Mar 1–2, 2026) and “Additional quality checks to review using the Logs.txt” were referenced in the plan.
- **Explicit “do not do” (from plan):**
  - Do **not** change consensus calculation or required_llms semantics.
  - Do **not** add fields to the config object passed to `TradeConfig` without stripping them before `TradeConfig.__init__`.
  - Do **not** change `open_trade()` return signature.
  - Do **not** implement multiple execution-path or config changes in one deployment; one change at a time for execution logic.
- **Scope:** Log throttles, optional audit/orphan logging, documentation, and RED FLAG window extension only. No change to when duplicates are blocked or to SL/execution logic.

---

## What Was Implemented (Summary Table)

| §  | Area | Suggestion | Implementation |
|----|------|------------|----------------|
| 5.1 | Stop loss (quality check 1) | Optional close-event log (pair, exit reason, P&L) | One INFO log line when a trade is closed: `Trade closed: {pair} {direction} exit_reason={reason} final_PnL={final_pnl}` in `PositionManager.close_trade()`. |
| 5.2 | RL (quality check 2) | Optional doc sentence for RL verification | USER_GUIDE §9: how to verify RL (after 11pm UTC, check Render logs for LEARNING CYCLE START / WEIGHTS UPDATED). |
| 5.3 | Sync / orphan (quality checks 4–5) | Doc how to verify sync; optional orphan-detection log | USER_GUIDE §10: sync verification (GET /trades vs OANDA; candidate orphan = OANDA position with no match). Optional: engine logs WARNING once per (pair, direction) per 15 min when adding an OANDA position it did not track. |
| 5.4 | RED FLAG throttle | Verify deploy; consider longer window | RED FLAG window extended from 15 min to **30 min** (1800 s). Block logic unchanged. |
| 5.5 | REJECTING STALE OPPORTUNITY | Throttle: first per (pair, direction) per window WARNING, rest DEBUG | Throttle added: 10 min window; first at WARNING, subsequent at DEBUG. Rejection logic unchanged. |
| 5.6 | Only one required LLM | Throttle: once per process/hour WARNING, rest DEBUG | Warning logged at WARNING only once per hour; subsequent at DEBUG. |
| 5.7 | Weekend shutdown message | Throttle: first per window WARNING, rest DEBUG | “Weekend shutdown: Cancelled N pending order(s)” first in 15 min at WARNING, rest at DEBUG. |
| 5.8 | Config loaded from API | Optional: DEBUG for routine, INFO on first load or when mode/stop_loss/max_trades change | “Config loaded from API” at INFO only on first load or when (mode, stop_loss, max_trades) changes; routine reloads at DEBUG. |
| 5.9 | Backup error_log | Doc: 401/400/403 from backup script, not engine | USER_GUIDE §11: Manual logs error_log.txt may show Render 401 / Oanda 400/403 from **BackupRenderLogs**; set RENDER_API_KEY and OANDA_ACCOUNT_ID in backup task env if needed. |

---

## Files Modified

### Scalp-Engine

| File | Changes |
|------|--------|
| `Scalp-Engine/scalp_engine.py` | New throttle state: `_stale_reject_log_last`, `_stale_reject_log_window_seconds` (5.5); `_single_required_llm_last_warning`, `_single_required_llm_warning_interval_seconds` (5.6); `_weekend_cancel_last_logged`, `_weekend_cancel_window_seconds` (5.7); `_last_config_snapshot`, `_config_loaded_once` (5.8). RED FLAG window 15→30 min (5.4). REJECTING STALE OPPORTUNITY throttle (5.5). Config load: INFO only on first or change, else DEBUG (5.8). Single required LLM: WARNING once/hour, else DEBUG (5.6). Weekend shutdown cancel message throttle (5.7). |
| `Scalp-Engine/auto_trader_core.py` | Trade close audit log in `PositionManager.close_trade()` (5.1). Orphan warning: `_orphan_warning_last_logged`, `_orphan_warning_window_seconds`; when adding an OANDA trade not previously tracked, log WARNING once per (pair, direction) per 15 min (5.3). |
| `Scalp-Engine/USER_GUIDE.md` | New Troubleshooting subsections: §9 Verifying RL, §10 Sync and orphan verification, §11 Manual logs error_log (backup script 401/400/403). |

### Paths (all under personal)

- **Plan:** `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor3.md`
- **Codebase:** `personal\Trade-Alerts\` (Scalp-Engine and Trade-Alerts root)
- **Context:** `personal\Trade-Alerts\CLAUDE.md`, `personal\cursor_works.md` (this file)

---

## Verification (for future sessions)

- After deploy: at least one trade still opens when an opportunity passes (consensus, no duplicate block).
- No new fields passed to `TradeConfig.__init__`; no change to `open_trade()` return signature.
- Logs: RED FLAG at most once per 30 min per (pair, direction); REJECTING STALE OPPORTUNITY and weekend shutdown messages throttled; “Config loaded from API” at INFO only on first load or config change; “Only one required LLM” at WARNING at most once per hour.
- Trade close: one INFO line per close with pair, direction, exit_reason, final_PnL.
- Orphan: when engine adds an OANDA position it didn’t track, WARNING once per (pair, direction) per 15 min.
- USER_GUIDE: §9 (RL), §10 (sync/orphan), §11 (backup error_log) present and accurate.

---

## References for Future Sessions

- **Plan document:** `Trade-Alerts\Scalp-Engine\suggestions from cursor3.md`
- **Trade-Alerts context:** `Trade-Alerts\CLAUDE.md` (architecture, Feb 25 rollback, consol-recommend2/3, do-not-do list)
- **Backup / Manual logs context:** This file (Part 1), and “Additional quality checks to review using the Logs.txt” in Manual logs folder
- **Rollback backups (if needed):** e.g. `personal\backup_before_consol_recommend3_20260228_090025` (see CLAUDE.md for full list)

*Part 2 last updated: session implementing suggestions from cursor3 (log throttles, optional close/orphan logs, USER_GUIDE §9–11, RED FLAG 30 min window).*

---

# Part 3: Cursor4 Manual Logs Review and consol-recommend4 (Mar 2, 2026)

---

## Goal of This Session

Review documents in **Manual logs** (`C:\Users\user\Desktop\Test\Manual logs`) for **consistency of logic, business rules, and transactions** across the four touchpoints (Trade-Alerts, Scalp-engine, Scalp-engine UI, OANDA). Produce improvement plans (Cursor4), then **compare with Anthropic’s suggestions** (suggestions_from_anthropic4.md) and create a **consolidated implementation plan** (consol-recommend4.md) that improves the trading system while **avoiding failures from previous implementations** (Feb 25 rollback, consol-recommend2/3 lessons).

**No implementation was performed**; all outputs are plans only. Approval required before any code or config changes.

---

## What Was Done

1. **Manual logs reviewed:** trade-alerts_*.txt, scalp-engine_*.txt, scalp-engine-ui_*.txt, oanda_*.txt, oanda_transactions_*.json, config-api_*.txt, market-state-api_*.txt (Mar 1–2, 2026), plus “Additional quality checks to review using the Logs.txt”.
2. **Context used:** Trade-Alerts `CLAUDE.md`, personal `cursor_works.md`, and prior suggestion docs (`suggestions from cursor.md`, cursor1, cursor2, cursor3) so Cursor4 did not re-suggest already-implemented items and respected the do-not-do list.
3. **Cursor4 output:** `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor4.md` — cross-touchpoint consistency, forex-specific flaws, and improvement plans (no code changes).
4. **Anthropic4 input:** `personal\Trade-Alerts\suggestions_from_anthropic4.md` — 18 issues across CRITICAL/HIGH/MEDIUM (SL, premature closures, max_runs, Claude/DeepSeek, consensus display, etc.).
5. **Consolidated plan:** `personal\Trade-Alerts\consol-recommend4.md` — merged Cursor4 + Anthropic4 into phased plan (Phase 0–4) with explicit “what not to do” and one-change-at-a-time rule.

---

## Key Finding (Critical – Cursor4 Only)

**JPY pair limit order price sent incorrectly to OANDA**

- **Evidence:** In `oanda_transactions_*.json`, USD_JPY LIMIT_ORDER has **entry** `"price": "1.560"` but **takeProfitOnFill** `"price": "157.500"`. USD/JPY trades around 156–158; 1.56 is wrong (e.g. price ÷ 100 applied only to limit price).
- **Impact:** Limit orders for USD/JPY (and possibly other JPY pairs) are placed at wrong price; TP is correct, so execution/risk is inconsistent.
- **Plan:** Phase 1.1 in consol-recommend4 — locate order builder, fix JPY price scale, add sanity check, verify with OANDA transaction log. Single, isolated change; test in MONITOR first.

---

## Consolidated Plan (consol-recommend4) Summary

| Phase | Content |
|-------|--------|
| **Phase 0** | Immediate: Claude API (replenish or disable); investigate what is closing trades (manual closures); verify max_runs reset in code. No execution-path code. |
| **Phase 1** | Critical, one at a time: (1.1) JPY limit order price to OANDA, (1.2) max_runs fix/verify, (1.3) premature closures fix after root cause known, (1.4) trailing SL verify + optional close log. |
| **Phase 2** | High: Consensus **display** as X/available_llm_count (no formula change), parser doc + optional parsed-count log, DeepSeek parser or doc, trading hours verify, replace-threshold verify, market state timestamp doc. |
| **Phase 3** | Medium: Sync/orphan procedure doc, position sizing doc, optional RL/partial-failure log, log spam verify, OANDA request trace doc, AUTO mode doc. |
| **Phase 4** | Monitoring: closure %, win rate, LLM health (ongoing). |

**Safeguards (do not repeat past failures):**

- Do **not** change consensus **formula**, min_consensus_level, or required_llms **logic**; display-only denominator (e.g. “2/3”) is allowed.
- Do **not** add config fields to TradeConfig without stripping before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- Do **not** batch execution-path changes; one fix per deployment, then verify trades still open.
- Premature closures: **investigate first** (Phase 0.2), then single fix (Phase 1.3).

---

## References for Future Sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **suggestions from cursor4.md** | `Trade-Alerts\Scalp-Engine\suggestions from cursor4.md` | Cursor’s Manual-logs review; cross-touchpoint consistency; JPY price bug; quality checks 1–7. |
| **suggestions_from_anthropic4.md** | `Trade-Alerts\suggestions_from_anthropic4.md` | Anthropic’s 18 issues; CRITICAL/HIGH/MEDIUM; phases and success criteria. |
| **consol-recommend4.md** | `Trade-Alerts\consol-recommend4.md` | Consolidated plan v4; Cursor4 vs Anthropic4 comparison; Phase 0–4; verification checklist; what not to do. |
| **CLAUDE.md** | `Trade-Alerts\CLAUDE.md` | Architecture, Feb 25 rollback, consol-recommend2/3, do-not-do list, Session notes. |
| **Manual logs** | `C:\Users\user\Desktop\Test\Manual logs` | trade-alerts_*, scalp-engine_*, scalp-engine-ui_*, oanda_*, oanda_transactions_*.json, config-api_*, market-state-api_*. |
| **Additional quality checks** | `Manual logs\Additional quality checks to review using the Logs.txt` | Seven checks: trailing SL, Structure_ATR, profitable→loss, RL, trading hours, sync, orphans. |

---

## Status

- **Implementation:** None. All of the above is **plan only**; no code or config changes were made.
- **Next steps (for user):** Review consol-recommend4.md; approve phases/items; implement **one change at a time** (starting with Phase 0 and Phase 1.1 JPY price fix); verify after each step.
- **Rollback:** If implementing consol-recommend4 and issues occur, use existing backups and see CLAUDE.md for rollback steps.
- **Backup for consol-recommend4 rollback:** `personal\backup_before_consol_recommend4_20260302` (created Mar 2, 2026; robocopy of Trade-Alerts excluding .git and __pycache__; 4200+ files). Restore by replacing `Trade-Alerts` contents with this backup’s contents (or renaming backup to Trade-Alerts).

*Part 3 (plan) last updated: Mar 2, 2026 — Manual logs review, cursor4, Anthropic4 comparison, consol-recommend4 created; backup_before_consol_recommend4_20260302 taken.*

---

# Part 3 (continued): consol-recommend4 Implementation (Mar 2, 2026)

---

## Goal of This Session

Implement the **consolidated plan** in `personal\Trade-Alerts\consol-recommend4.md` (from Cursor4 + Anthropic4), following the plan’s safeguards: no consensus formula change, no new TradeConfig fields without stripping, no `open_trade()` return signature change, one execution-path change at a time. Context was taken from `Trade-Alerts\CLAUDE.md` and this file (cursor_works.md).

---

## Plan Source and Constraints

- **Plan:** `personal\Trade-Alerts\consol-recommend4.md`
- **Context:** `personal\Trade-Alerts\CLAUDE.md`, `personal\cursor_works.md` (Part 1–3)
- **Explicit “do not do” (from plan):**
  - Do **not** change consensus calculation, min_consensus_level, or required_llms **logic** (display-only denominator allowed).
  - Do **not** add fields to the config object passed to `TradeConfig` without stripping before `TradeConfig.__init__`.
  - Do **not** change `open_trade()` return signature.
  - Do **not** implement multiple execution-path or config changes in one deployment.
- **Scope implemented:** Phase 1.1 (JPY price), Phase 1.4 (trailing SL verify + close log doc), Phase 2.1 (consensus display), Phase 2.2/2.4/2.5/2.6 (docs/verify), Phase 2.3 (DeepSeek parser + doc), Phase 3.1 (sync/orphan doc + optional log), Phase 3.x (USER_GUIDE §§12–17). Phase 0.3/1.2 verified in code (max_runs reset present). Phase 0.1/0.2 (operator), 1.2 fix (only if 0.3 found missing), 1.3 (premature closures after 0.2), Phase 4 (monitoring) not implemented.

---

## What Was Implemented (Summary Table)

| Phase | Item | What was done |
|-------|------|----------------|
| **0.3 / 1.2** | max_runs auto-reset | **Verified in code** (no change): In `auto_trader_core.py`, when directive is REJECT for max_runs and `has_existing_position(pair, direction)` is False, engine calls `reset_run_count(opp_id)`, re-gets directive, proceeds if EXECUTE_NOW/PLACE_PENDING. |
| **1.1** | JPY limit order price to OANDA | **Fix:** In `TradeExecutor.open_trade()` (auto_trader_core.py): For JPY pairs and LIMIT/STOP orders, if entry_price &lt; 10 and take_profit &gt; 10, correct entry scale (×100). If entry &lt; 10 and no TP to infer scale, **reject** with ERROR and do not send. Use `round_price_for_oanda(entry_price, pair)` for order price; use corrected `entry_price` in STOP/LIMIT payloads and pending-fill log. |
| **1.4** | Trailing SL verify + close-event log | **Doc only:** USER_GUIDE §17 added: trailing SL is applied in main monitoring loop (`_check_be_transition`, `_check_ai_trailing_conversion`); direction correct (longs SL up, shorts down). One INFO log per trade close already present: `Trade closed: {pair} {direction} exit_reason=... final_PnL=...`. |
| **2.1** | Consensus denominator display | **Display only:** market_bridge.py computes `available_llm_count` (LLMs that contributed this run), adds to each enhanced opp and to state. scalp_ui.py and scalp_engine.py show consensus as `X/{denom}` (e.g. 2/3). No formula change. |
| **2.2** | Parser failure / consensus doc | USER_GUIDE §13: when LLM returns 0 parsed opportunities, that LLM contributes 0; denominator reflects contributing LLMs. |
| **2.3** | DeepSeek parser | **Parser:** recommendation_parser.py Pattern set 10 (DeepSeek/narrative): `Pair:` / `**Pair:**` X/Y; bullet `- X/Y Long`; inline `X/Y - Long`. main.py: when DeepSeek returns text but 0 opps, log INFO pointing to USER_GUIDE §13. USER_GUIDE §13 updated with DeepSeek structured-output note. |
| **2.4 / 2.5** | Trading hours, replace-threshold | **Verify + doc:** Confirmed `can_open_new_trade()` and `REPLACE_ENTRY_MIN_PIPS` / `REPLACE_SL_TP_MIN_PIPS` in use. USER_GUIDE §14 documents both. |
| **2.6** | Market state timestamp | USER_GUIDE §12: timestamp set when state is written/POSTed; optional warning when state old. |
| **3.1** | Sync/orphan procedure | **Doc:** USER_GUIDE §10 expanded (a) GET /trades vs OANDA by pair/direction, (b) candidate orphan = OANDA position with no match in GET /trades, (c) cross-check with Manual logs (scalp-engine_*.txt, oanda_transactions_*.json). Optional orphan WARNING (once per (pair, direction) per 15 min) already in auto_trader_core.py. |
| **3.2 / 3.5 / 3.6** | Position sizing, OANDA log, AUTO mode | USER_GUIDE §§15, 16: position sizing audit, OANDA app log vs transaction history, AUTO mode and manual close. |

---

## Files Modified

### Trade-Alerts (root)

| File | Changes |
|------|--------|
| `src/market_bridge.py` | `available_llm_count` computed in `_enhance_opportunities_with_consensus`, added to each enhanced opp and to state. |
| `src/recommendation_parser.py` | Pattern set 10 (DeepSeek/narrative): 10a `Pair:` / `**Pair:**` X/Y; 10b bullet `- X/Y Long`; 10c `X/Y - Long`. Direction captured for extractor. Debug log includes P10 count. |
| `main.py` | When `deepseek` returns text but 0 opportunities (text len &gt; 50), log INFO: "DeepSeek: 0 opportunities parsed. If DeepSeek output format differs..." and reference USER_GUIDE §13. |

### Scalp-Engine

| File | Changes |
|------|--------|
| `auto_trader_core.py` | Phase 1.1: JPY entry price scale check and correction for LIMIT/STOP; `round_price_for_oanda` for entry; reject if JPY and entry &lt; 10 with no TP; use `entry_price` variable in STOP/LIMIT and pending-fill log. |
| `scalp_engine.py` | Consensus log lines use `opp.get('available_llm_count', 3)` for denominator (Phase 2.1). |
| `scalp_ui.py` | Market Intelligence and trade card: consensus shown as `X/{denom}` using `available_llm_count` from opp or market_state (Phase 2.1). |
| `USER_GUIDE.md` | New/updated: §10 sync/orphan (3.1), §12 market state timestamp (2.6), §13 parser/DeepSeek (2.2, 2.3), §14 trading hours + replace-threshold (2.4, 2.5), §15 position sizing + AUTO (3.2, 3.6), §16 OANDA app log (3.5), §17 trailing SL verify + close log (1.4). |

### Plan document

| File | Changes |
|------|--------|
| `consol-recommend4.md` | Status line updated to "Partially implemented" and list of implemented phases (1.1, 1.4, 2.1, 2.2–2.6, 2.3, 3.1, 3.x docs; 0.3/1.2 verified). |

---

## Verification (for future sessions)

- After deploy: at least one trade still opens when an opportunity passes (consensus ≥ 2, no duplicate block).
- No `TradeConfig.__init__() got an unexpected keyword argument`.
- OANDA USD_JPY (and other JPY) LIMIT/STOP entry price in correct range (e.g. 156.xxx); if upstream sends 1.56 and TP 157.5, entry is corrected to 156.0 or rejected with ERROR.
- max_runs: same (pair, direction) can be retried after order closed/cancelled (verified in code).
- Consensus display: UI and engine logs show X/available_llm_count (e.g. 2/3).
- DeepSeek: if output matches new patterns or MACHINE_READABLE JSON, opportunities parse; otherwise INFO log and USER_GUIDE §13.
- USER_GUIDE: §§10, 12–17 present and accurate.

---

## References for Future Sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **consol-recommend4.md** | `Trade-Alerts\consol-recommend4.md` | Consolidated plan; implemented vs not implemented; verification checklist; what not to do. |
| **CLAUDE.md** | `Trade-Alerts\CLAUDE.md` | Architecture, Feb 25 rollback, consol-recommend2/3, do-not-do list. |
| **suggestions from cursor4.md** | `Trade-Alerts\Scalp-Engine\suggestions from cursor4.md` | Cursor4 Manual-logs review; JPY bug; quality checks. |
| **suggestions_from_anthropic4.md** | `Trade-Alerts\suggestions_from_anthropic4.md` | Anthropic 18 issues; phases. |
| **Backup (rollback)** | `personal\backup_before_consol_recommend4_20260302` | Full Trade-Alerts copy before consol-recommend4 implementation; restore if needed. |

---

## Changelog (session summary)

- **Phase 1.1:** JPY limit/stop order price scale and sanity check in `auto_trader_core.py`; correct or reject and use rounded entry in order payload.
- **Phase 1.4:** USER_GUIDE §17: trailing SL verification (monitoring loop, direction), trade-close audit log.
- **Phase 2.1:** Consensus display as X/available_llm_count in market_bridge, scalp_ui, scalp_engine (display only).
- **Phase 2.2 / 2.4 / 2.5 / 2.6:** USER_GUIDE §§12–14 (parser, trading hours, replace-threshold, market state timestamp).
- **Phase 2.3:** DeepSeek parser patterns (recommendation_parser.py), main.py INFO when DeepSeek 0 opps, USER_GUIDE §13.
- **Phase 3.1:** USER_GUIDE §10 expanded (GET /trades vs OANDA, candidate orphan, Manual logs); optional orphan WARNING already in code.
- **Phase 3.2 / 3.5 / 3.6:** USER_GUIDE §§15, 16 (position sizing, OANDA log, AUTO mode).
- **Phase 0.3 / 1.2:** Verified max_runs reset logic present in `auto_trader_core.py`; no code change.

*Part 3 (implementation) last updated: Mar 2, 2026 — consol-recommend4 phases 1.1, 1.4, 2.1, 2.2–2.6, 2.3, 3.1, 3.x docs implemented and documented in cursor_works.md.*

---

# Part 5: EUR/USD ATR Trailing SL and Duplicate Positions (Mar 3, 2026)

---

## Context

User-reported issues confirmed via screenshots and backup log review (Manual logs `2026-03-03_0542`, OANDA transactions and scalp-engine logs): (1) ATR trailing stop loss not moving despite 97–102 pips profit on EUR/USD SHORT; (2) two EUR/USD SHORT positions open simultaneously (tickets 24409 and 24412 in OANDA). This section documents the issues in detail and proposes fixes for future sessions. **No implementation was performed** in the documenting session.

---

## Issue 1: ATR Trailing Stop Loss Not Updating on OANDA

### Description

- **Observed behaviour:** Trades configured with **ATR_TRAILING** (config: "Stop Loss Type: ATR_TRAILING") show in the UI as "ATR-Trail" and report ~97–102 pips unrealized profit. On OANDA, the stop loss remains at the **initial fixed level** (e.g. 1.17800 and 1.18300 for two EUR/USD SHORTs entered at 1.17000). The OANDA Positions panel shows "TS:" with no value. A correctly functioning ATR trailing stop would have moved the SL down with price (for shorts) to lock in profit; the SL did not move.
- **Intended behaviour:** For ATR_TRAILING, the engine should:
  1. Open the trade with a **fixed** stop loss (stopLossOnFill at order creation).
  2. When price reaches breakeven or better, call OANDA to **convert** the trade to a **trailing** stop via `TradeClientExtensions` with `trailingStopLoss.distance`.
  3. OANDA then maintains the trailing stop; the engine does not continuously update SL.
- **Evidence from backup logs:**
  - **OANDA transaction history:** No `trailingStopLoss` or trailing-stop order type in the 24h window. All EUR_USD trades show only **STOP_LOSS_ORDER** with a fixed `price`. Multiple **TRADE_CLIENT_EXTENSIONS_MODIFY** events exist for the same trade IDs, but the transaction list does not include request bodies, and no subsequent trailing-stop order appears.
  - **Scalp-engine log:** No "Converted to trailing stop" or "Failed to convert ATR Trailing trade … to trailing stop" messages for EUR/USD. Config correctly shows "Stop Loss Type: ATR_TRAILING".

### Root cause (inferred)

One or more of the following:

1. **Conversion never attempted:** The trade is not present in `position_manager.active_trades` when `monitor_positions()` runs (e.g. after restart or sync gap), so `_check_ai_trailing_conversion()` is never called for it.
2. **No current price for pair:** In `monitor_positions()`, if `current_prices.get(trade.pair)` is missing (e.g. `_get_current_prices(pairs)` failed or omitted the pair), the loop does `continue` and skips ATR conversion for that trade.
3. **Conversion attempted but OANDA call failed:** `convert_to_trailing_stop()` was called but OANDA returned an error; the failure is logged as "Failed to convert …" but that log line did not appear in the captured backup (or conversion is not being called at all).
4. **Wrong API usage:** OANDA v20 may require cancelling the existing STOP_LOSS_ORDER before creating a trailing stop, or the `TradeClientExtensions` payload may be incorrect (e.g. wrong units or format for `trailingStopLoss.distance`).

### Code locations (Trade-Alerts/Scalp-Engine)

| Location | Purpose |
|----------|--------|
| `Scalp-Engine/auto_trader_core.py` | `PositionManager.monitor_positions()` (lines ~1419–1517): iterates `active_trades`, gets `current_price`, calls `_check_ai_trailing_conversion(trade, current_price, market_state)` when `trade.sl_type == StopLossType.ATR_TRAILING`. |
| `Scalp-Engine/auto_trader_core.py` | `_check_ai_trailing_conversion()` (lines ~2001–2065): for SHORT, "at breakeven or profit" = `current_price <= trade.entry_price`; then calls `self.executor.convert_to_trailing_stop(trade.trade_id, trailing_pips, trade.pair)`. Uses `market_state.get('atr', 20)` for distance. |
| `Scalp-Engine/auto_trader_core.py` | `TradeExecutor.convert_to_trailing_stop()` (lines ~578–606): builds `{"trailingStopLoss": {"distance": str(distance)}}` (distance in price units: `distance_pips * pip_size`), sends via `trades.TradeClientExtensions(accountID, tradeID, data)`. |
| `Scalp-Engine/scalp_engine.py` | `_monitor_positions()` (lines ~3104–3136): calls `sync_with_oanda(market_state)` then `position_manager.monitor_positions(current_prices, market_state, self.oanda_client)`. `current_prices` from `_get_current_prices(pairs)` where `pairs` = list from `active_trades`. |

### Proposed fix (for future sessions)

1. **Ensure trades are in scope for monitoring**
   - After `sync_with_oanda()`, ensure every OANDA open position for the account is represented in `active_trades` (including trades opened by UI or another process). Already partially done via "Synced missing trade … into active_trades"; verify sync runs before monitor and that no path clears or skips EUR/USD.
   - Log at DEBUG when a trade is skipped in `monitor_positions()` (e.g. "Skipping {pair} {direction}: no current_price" or "trade not in active_trades") so backup logs can confirm whether conversion was attempted.

2. **Guarantee current price for all monitored pairs**
   - In `_monitor_positions()` (scalp_engine.py), if `_get_current_prices(pairs)` omits a pair, retry or fetch that pair separately before calling `monitor_positions()`. Avoid skipping a trade solely because of a transient price fetch gap.

3. **Log conversion attempt and outcome**
   - In `_check_ai_trailing_conversion()`: before calling `convert_to_trailing_stop()`, log at INFO: e.g. "ATR Trailing: attempting conversion for {trade_id} ({pair} {direction}) at breakeven/profit, distance={trailing_pips} pips".
   - In `TradeExecutor.convert_to_trailing_stop()`: on failure (exception or OANDA error), log at WARNING or ERROR with full error message and trade_id so backup logs show whether conversion was attempted and why it failed.

4. **Verify OANDA v20 trailing-stop semantics**
   - Check OANDA docs: whether `TradeClientExtensions` with `trailingStopLoss` **replaces** an existing stop-loss order or requires the existing STOP_LOSS_ORDER to be cancelled first. If replacement is not automatic, add a step to cancel the existing stop-loss order before sending the trailing-stop extension.
   - Confirm `distance` is in **price units** (e.g. 0.003 for 30 pips on EUR/USD). Current code uses `distance_pips * pip_size` (0.0001 for non-JPY), which is correct for EUR/USD.

5. **Optional: market_state ATR**
   - Trade-Alerts `market_bridge` does not currently export `atr` in market_state. Engine uses `market_state.get('atr', 20)`. Consider having Trade-Alerts include ATR (e.g. from the same source as opportunities) so trailing distance is regime-aware; otherwise keep default 20 and ensure conversion still runs.

---

## Issue 2: Two EUR/USD SHORT Positions Open Simultaneously

### Description

- **Observed behaviour:** UI and OANDA both show **two** active EUR/USD SHORT positions at the same time: ticket **24409** (TP 1.15700, SL 1.18300) and ticket **24412** (TP 1.15500, SL 1.17800). Engine design is **one position per (pair, direction)**; the duplicate check should prevent a second EUR/USD SHORT from being opened.
- **Evidence:** User screenshots (UI list with two "EUR/USD SHORT (TRAILING)" entries; OANDA Positions tab with two EUR/USD 2,000-unit shorts with different ticket numbers and TP/SL). Backup OANDA transactions show at least one EUR_USD SHORT (24409) opened 2026-03-03T01:21:05Z; a second fill for EUR_USD SHORT (24412) appears in the same backup window.
- **Impact:** Double exposure on the same pair/direction, duplicate risk and margin use, and possible confusion in P&amp;L and SL management.

### Root cause (inferred)

The duplicate check `has_existing_position(pair, direction)` (which checks in-memory `active_trades` and OANDA `get_open_positions()`) did not see an existing EUR/USD SHORT at the time the second order was placed. Possible reasons:

1. **Sync timing:** Engine restarted or had just run `sync_with_oanda()` before the first EUR/USD fill was reflected in OANDA’s API; the second order was evaluated and sent before the first position appeared in `get_open_positions()` or in `active_trades`.
2. **Race in same loop:** Two opportunities for EUR/USD SHORT were processed in the same (or consecutive) iteration; the first `open_trade()` was sent to OANDA but the second was evaluated before the first was added to `active_trades` or before the next OANDA fetch.
3. **Different opener:** One position was opened by the engine and one by the UI (or another process); the engine’s `active_trades` did not yet contain the UI-opened position, and either `get_open_positions()` was not called before the engine’s open or OANDA had not yet returned both.
4. **OANDA aggregation:** Unlikely if both tickets are distinct, but if at some moment OANDA returned only one net position for EUR_USD, the engine would have allowed a second open.

### Code locations (Trade-Alerts/Scalp-Engine)

| Location | Purpose |
|----------|--------|
| `Scalp-Engine/scalp_engine.py` | Main opportunity loop (lines ~1089–1146): before opening, calls `already_open = self.position_manager.has_existing_position(pair, direction)`; if True, logs RED FLAG and continues. |
| `Scalp-Engine/auto_trader_core.py` | `PositionManager.has_existing_position()` (lines ~874–970): normalizes pair/direction; checks in-memory `active_trades` (by pair + direction, and for PENDING checks `check_order_exists()`); then calls `executor.get_open_positions()` and matches by instrument and units sign (LONG/SHORT). If an OANDA position is found that is not in `active_trades`, syncs it in and returns True. Also checks pending orders via OANDA PendingOrders. |

### Proposed fix (for future sessions)

1. **Call OANDA immediately before each open**
   - In the path that is about to call `position_manager.open_trade()` (e.g. in `scalp_engine.py` after passing consensus/validation), add a **fresh** call to `get_open_positions()` (or a thin wrapper that returns only pair/direction) and re-check for (pair, direction). If found, skip open and log "BLOCKED DUPLICATE (pre-open OANDA check): {pair} {direction}". This reduces the window where a race or stale cache allows a second open.

2. **Add to active_trades before sending order to OANDA (with state PENDING)**
   - When the decision to open is made, create the `ManagedTrade` (or equivalent) and add it to `active_trades` with state PENDING **before** calling `executor.open_trade()`. Then the next opportunity in the same loop will see `has_existing_position() == True` via in-memory check. When OANDA returns (success or failure), update or remove the entry. This requires ensuring that failed opens are removed from `active_trades` and that sync does not duplicate entries.

3. **Idempotency / unique request key**
   - Optionally send a client request ID (or tag) that includes (pair, direction, timestamp window) so that if the same open is sent twice (e.g. retry or race), OANDA can deduplicate. This is a supplement, not a replacement for the above.

4. **Logging**
   - When opening a trade, log at INFO: "Opening {pair} {direction} (has_existing_position=False, OANDA open count for pair=X)". When blocking a duplicate, log the source: "BLOCKED DUPLICATE (in-memory)" vs "BLOCKED DUPLICATE (OANDA pre-open check)" so future logs can distinguish race vs sync vs other.

---

## Constraints for implementation (same as existing plans)

- Do **not** change consensus formula, min_consensus_level, or required_llms logic.
- Do **not** add fields to the config object passed to `TradeConfig` without stripping before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- Implement **one** fix at a time; verify (e.g. trades still open, no regressions) before the next.

---

## References

| Document / location | Purpose |
|---------------------|--------|
| **CLAUDE.md** (Trade-Alerts) | Architecture, Session 21 (GBP/USD format fix), trailing/conversion logic, do-not-do list. |
| **consol-recommend4.md** | Phase 1.4 (trailing SL verify), USER_GUIDE §17; Phase 0.3/1.2 (max_runs). |
| **Manual logs** (e.g. `2026-03-03_0542`) | scalp-engine_*.txt, oanda_transactions_*.json for conversion and duplicate evidence. |
| **USER_GUIDE.md** §17 | Trailing SL verification (monitoring loop, direction). |

**Implementation:** The fixes proposed above were implemented in **Part 6 (cursor5 Implementation)** from the plan in `suggestions from cursor5.md`.

---

*Part 5 last updated: Mar 3, 2026 — issues described and fixes proposed for future sessions; implementation in Part 6.*

---

# Part 6: cursor5 Implementation (Mar 3, 2026)

---

## Goal of This Session

Implement the improvement and fix **plan** from **`suggestions from cursor5.md`** (Round 6 – cursor5) in the Scalp-Engine under Trade-Alerts. The plan addressed cross-touchpoint consistency, forex-specific flaws, and recurring issues from Manual logs (Mar 3, 2026), cursor_works Part 5 (ATR trailing not updating, duplicate EUR/USD SHORT), and gemini-suggestions1 (TradeClientExtensions vs correct OANDA API). Context was taken from **CLAUDE.md** (Trade-Alerts), **cursor_works.md** (Parts 1–5), and the plan document itself.

---

## Plan Source and Constraints

- **Source:** `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor5.md`
- **Context used:** Manual logs (Mar 3, 2026), CLAUDE.md, cursor_works.md Part 5, gemini-suggestions1.md, consol-recommend4, suggestions from cursor4 and anthropic4/5.
- **Explicit “do not do” (respected):**
  - Do **not** change consensus formula, min_consensus_level, or required_llms **logic**.
  - Do **not** add fields to the config object passed to `TradeConfig` without stripping before `TradeConfig.__init__`.
  - Do **not** change `open_trade()` return signature.
  - Do **not** batch execution-path or config changes; one at a time, verify after each.
- **Implementation order followed:** Phase 0 (verify/log, investigate) then Phase 1 (5.4 API fix → 5.3 → 5.1 → 5.2 → 5.5) then Phase 2 (5.9 doc).

---

## What Was Implemented (Summary Table)

| § | Area | Suggestion | Implementation |
|---|------|------------|----------------|
| **5.1** | Active count exceeds max_trades (5/4) | Clarify active count; enforce max_trades before open; log when count > config | **can_open_new_trade():** Only OPEN, TRAILING, AT_BREAKEVEN count toward max_trades; PENDING excluded. OANDA count = open positions only (no pending orders). If in_memory_total > max_trades, log WARNING with (in_memory_total, open_count, max_trades, OANDA_open). |
| **5.2** | Duplicate positions (same pair/direction) | Pre-open OANDA check; add to active_trades before send; logging | **Pre-open check:** In `PositionManager.open_trade()`, fresh `get_open_positions()` and re-check (pair, direction); if found, return None and log "BLOCKED DUPLICATE (pre-open OANDA check): {pair} {direction}". **Add-before-send:** Placeholder added to `active_trades` with key `_pending_{opp_id}` and state PENDING **before** `executor.open_trade()`; on success re-key by order_or_trade_id, on failure pop placeholder. **has_existing_position:** PENDING trades with no trade_id (placeholder) now return True for same (pair, direction). **Logging:** "BLOCKED DUPLICATE (in-memory)" vs "(pre-open OANDA check)"; "Opening {pair} {direction} (has_existing_position=False)". |
| **5.3** | ATR trailing not updating on OANDA | Verify API; ensure conversion attempted; observability | **Observability:** INFO log before conversion: "ATR Trailing: attempting conversion for {trade_id} ({pair} {direction}) at breakeven/profit, distance={trailing_pips} pips". DEBUG when skipping a trade in `monitor_positions()` due to missing current_price: "Skipping {pair} {direction} (trade_id=…): no current_price". (API fix under 5.4.) |
| **5.4** | Wrong API for SL/trailing (TradeClientExtensions) | Use correct OANDA endpoint (OrderCreate, not TradeClientExtensions) | **convert_to_trailing_stop():** Now uses **OrderCreate** with order type **TRAILING_STOP_LOSS** (tradeID, distance, timeInForce GTC). Optionally cancels existing stop-loss order on the trade before creating trailing stop. **update_stop_loss():** Now uses **OrderCreate** with order type **STOP_LOSS** (tradeID, price, timeInForce GTC); cancels existing SL order first. TradeClientExtensions is metadata-only and does not update actual SL/trailing on OANDA (gemini-suggestions1, cursor5 §5.4). |
| **5.5** | Pending-to-open sync (trade_id = None → naked) | Two-stage matching so filled orders keep SL/TP | In **sync_with_oanda()**, when adding an OANDA position not yet tracked: first try to match by **(pair, direction, units)** to an in-memory **PENDING** trade. If found, update that trade's trade_id to OANDA position id, set state OPEN, set entry from OANDA, re-key active_trades; do **not** create a second ManagedTrade. Log: "PENDING filled: linked OANDA position {id} to existing pending ({pair} {direction}) - SL/TP preserved". |
| **5.6** | max_runs still blocking | Verify deploy; add reset trace log | When max_runs reset is performed (REJECT for max_runs + no position → reset_run_count, re-get directive), log at INFO: "max_runs reset for {opp_id} (no position for pair/direction) - retrying directive". |
| **5.7** | Manual / premature closures | Investigate root cause; fix only after | **Investigation only:** Created **MANUAL_CLOSURES_INVESTIGATION.md** in Scalp-Engine listing all call sites that close trades (trading hours, MACD/DMI/STRUCTURE_ATR/FT-DMI-EMA, shutdown, etc.) and possible causes of "manual" TRADE_CLOSE in OANDA. No code fix; use to identify root cause before any change. |
| **5.8** | Quality checks 1–7 | Map to plans | No new suggestion; 5.1–5.5 and 5.7 fixes verified against quality checks (trailing SL → 5.3/5.4; sync → 5.1, 5.2, 5.5; etc.). |
| **5.9** | OANDA app log empty | Doc; optional log | **USER_GUIDE.md** §16 updated: OANDA app log may be empty; backup script may write "(Oanda app log empty - Config API returned 200 with no content...)"; use oanda_transactions_*.json for broker-side checks. |

---

## Files Modified

### Scalp-Engine

| File | Changes |
|------|--------|
| **auto_trader_core.py** | **5.4:** `convert_to_trailing_stop()` uses OrderCreate + TRAILING_STOP_LOSS; optional cancel of existing SL order first. `update_stop_loss()` uses OrderCreate + STOP_LOSS; cancel existing SL first. **5.1:** `can_open_new_trade()` counts only OPEN/TRAILING/AT_BREAKEVEN; OANDA open only; WARNING when in_memory_total > max_trades. **5.2:** In `open_trade()`: pre-open OANDA check (fresh get_open_positions, re-check pair/direction); add placeholder to active_trades (key `_pending_{opp_id}`) before executor.open_trade(); on success pop placeholder and add by order_or_trade_id; on failure pop placeholder. "Opening … (has_existing_position=False)" log. BLOCKED DUPLICATE (in-memory) vs (pre-open OANDA check). **has_existing_position:** PENDING with no trade_id returns True (block duplicate). **5.6:** INFO log when max_runs reset. **5.3:** INFO before ATR conversion attempt; DEBUG when skipping monitor due to no current_price. **5.5:** In sync_with_oanda(), two-stage matching: before adding new OANDA trade, match by (pair, direction, units) to PENDING; if found, adopt and re-key, preserve SL/TP. |
| **USER_GUIDE.md** | **5.9:** §16 – OANDA app log may be empty; backup message; use oanda_transactions_*.json. |
| **MANUAL_CLOSURES_INVESTIGATION.md** | **5.7:** New file – call sites for close_trade, possible causes of "manual" TRADE_CLOSE, next steps for root-cause analysis. |

### Paths (all under personal)

- **Plan:** `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor5.md`
- **Codebase:** `personal\Trade-Alerts\` (Scalp-Engine)
- **Context:** `personal\Trade-Alerts\CLAUDE.md`, `personal\cursor_works.md` (this file)

---

## Verification (for future sessions)

- After deploy: **active count** never exceeds max_trades (only OPEN/TRAILING/AT_BREAKEVEN counted); if it does, WARNING appears in logs with counts.
- **No duplicate (pair, direction):** Pre-open OANDA check and add-before-send reduce race; logs show "BLOCKED DUPLICATE (in-memory)" or "(pre-open OANDA check)" when blocked.
- **ATR trailing:** OANDA transaction history and engine logs show trailing-stop order creation (OrderCreate TRAILING_STOP_LOSS); engine logs "ATR Trailing: attempting conversion for …" and "Converted to trailing stop" or "Failed to convert …".
- **Pending-to-open:** New fills from pending orders are linked to in-memory PENDING by (pair, direction, units); log "PENDING filled: linked OANDA position … - SL/TP preserved".
- **max_runs:** When retry succeeds after close/cancel, log "max_runs reset for {opp_id} (no position for pair/direction)".
- No change to consensus formula, TradeConfig fields, or open_trade() return signature.

---

## References for Future Sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **suggestions from cursor5.md** | `Trade-Alerts\Scalp-Engine\suggestions from cursor5.md` | Full plan; inconsistencies 5.1–5.9; implementation order; what not to do. |
| **CLAUDE.md** | `Trade-Alerts\CLAUDE.md` | Architecture, Feb 25 rollback, do-not-do list. |
| **cursor_works.md Part 5** | `personal\cursor_works.md` | ATR trailing and duplicate position issues (pre-implementation). |
| **MANUAL_CLOSURES_INVESTIGATION.md** | `Trade-Alerts\Scalp-Engine\MANUAL_CLOSURES_INVESTIGATION.md` | 5.7 investigation; close_trade call sites. |
| **USER_GUIDE.md** | `Trade-Alerts\Scalp-Engine\USER_GUIDE.md` | §16 OANDA app log (5.9). |
| **Manual logs** | `C:\Users\user\Desktop\Test\Manual logs` | scalp-engine_*.txt, oanda_transactions_*.json for post-deploy verification. |

---

## Changelog (session summary)

- **5.1:** can_open_new_trade counts only open states; OANDA open positions only; WARNING when count exceeds config.
- **5.2:** Pre-open OANDA check in open_trade(); add placeholder to active_trades before executor.open_trade(); has_existing_position blocks on PENDING with no trade_id; BLOCKED DUPLICATE and Opening logs.
- **5.3:** INFO before ATR conversion; DEBUG when skipping monitor (no current_price).
- **5.4:** convert_to_trailing_stop and update_stop_loss use OrderCreate (TRAILING_STOP_LOSS, STOP_LOSS); cancel existing SL order before new order where applicable.
- **5.5:** sync_with_oanda two-stage matching: match OANDA position to PENDING by (pair, direction, units), adopt and preserve SL/TP.
- **5.6:** INFO log when max_runs reset.
- **5.7:** MANUAL_CLOSURES_INVESTIGATION.md created (investigation only).
- **5.9:** USER_GUIDE §16 OANDA app log empty note.
- **Commits:** cursor5 implementation committed and pushed (Trade-Alerts repo); later "commit and push all" included additional local changes.

*Part 6 last updated: Mar 3, 2026 — cursor5 plan implemented and documented for future sessions.*

---

# Part 7: cursor6 Manual Logs Review, Plan, and Backup (Mar 4–5, 2026)

---

## Goal of This Session

Review documents in **Manual logs** (`C:\Users\user\Desktop\Test\Manual logs`), match logs for **consistency of logic, business rules and transactions** across the four touchpoints (Trade-Alerts, Scalp-engine, Scalp-engine UI, OANDA), and create a **plan document** (suggestions from cursor6.md) to fix inconsistencies or flaws. **No implementation** was to be carried out without user approval. A **full backup** of Trade-Alerts was taken for rollback if required after any future implementation.

---

## What Was Done

### 1. Context and prior suggestions reviewed

- **CLAUDE.md** (Trade-Alerts): architecture, Feb 25 rollback, do-not-do list, Session notes.
- **cursor_works.md** (personal): Parts 1–6 (BackupRenderLogs; cursor3; consol-recommend4 plan and implementation; Part 5 ATR/duplicate; Part 6 cursor5 implementation).
- **gemini-suggestions1.md** (personal): TradeClientExtensions vs correct API; pending-to-open sync; REPLACE_ENTRY_MIN_PIPS; orphan adopt.
- **Prior suggestion docs:** suggestions from cursor4.md, cursor5.md; suggestions_from_anthropic4.md, suggestions_from_anthropic5.md; consol-recommend4.md.
- **Additional quality checks to review using the Logs.txt** (in Manual logs): seven checks (trailing SL, Structure_ATR, profitable→loss, RL, trading hours, sync, orphans).

### 2. Manual logs reviewed (Mar 3–4, 2026)

- **Sources:** trade-alerts_2026-03-04_1700.txt, scalp-engine_2026-03-04_1700.txt, scalp-engine-ui_2026-03-04_1700.txt, oanda_transactions_2026-03-04_1700.json, oanda_*.txt, config-api, market-state-api.
- **Cross-touchpoint consistency:** Trade-Alerts (opportunities, consensus, DeepSeek AUD/CHF vs AUD/USD); Scalp-engine (Active 6/4 and 5/4, max_trades, stale-order loop, RED FLAG BLOCKED DUPLICATE); Scalp-engine UI (DB init, log sync); OANDA (TRAILING_STOP_LOSS_ORDER success and many TRAILING_STOP_LOSS_ORDER_REJECT with ALREADY_EXISTS, ORDER_FILL, LIMIT_ORDER).

### 3. Plan document created (no implementation)

- **File:** `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor6.md`
- **Content:** Plan-only suggestions for:
  - **5.1 CRITICAL:** "Active: 6/4" and "5/4" — align display with max_trades definition (open only) or show Open vs Pending separately.
  - **5.2 HIGH:** TRAILING_STOP_LOSS_ORDER_ALREADY_EXISTS — check before creating trailing stop or set state after success to avoid repeated attempts.
  - **5.3 HIGH:** Stale-order cancel/replace loop (AUD/USD BUY) — do not re-place same entry after stale cancel; or cooldown; or higher threshold for HYBRID STOP.
  - **5.4 MEDIUM:** DeepSeek pair AUD/CHF vs AUD/USD — document possible confusion; optional log or parser normalisation.
  - **5.5 MEDIUM:** OANDA 502 in logs — handle 502/non-JSON; no raw HTML in log; retry/backoff; doc.
  - **5.6 MEDIUM:** UI DB init many times — verify cached DB; move routine init log to DEBUG; doc.
  - **5.7:** Quality checks 1–7 mapped to cursor6 and prior plans.
- **Constraints:** Same do-not-do list (no consensus formula change, no new TradeConfig fields without stripping, no open_trade() return signature change, one change at a time). Implementation order suggested in document.

### 4. Backup taken for rollback

- **Location:** `c:\Users\user\projects\personal\backup_cursor6_20260304`
- **Method:** robocopy of full Trade-Alerts folder, excluding `.git` and `__pycache__`.
- **File count:** 4,240 files.
- **Purpose:** Restore pre-implementation state if cursor6 (or other) changes require rollback.
- **Rollback:** Stop Trade-Alerts processes; replace Trade-Alerts contents with backup folder contents (or rename backup to Trade-Alerts); retain original `.git` if using version control.

---

## What Was Not Done

- **No code or config changes** were implemented. All cursor6 suggestions remain **plan only**; user approval required before any implementation.
- No modifications to Scalp-Engine, Trade-Alerts root, or config beyond creating the plan document and taking the backup.

---

## Key Findings (cursor6) for Future Sessions

| Finding | Evidence | Plan reference |
|--------|----------|----------------|
| Active count 6/4, 5/4 | scalp-engine logs "Active: 6/4", "Active: 5/4", "Active Trades: 5/4", "Pending Orders: 3" | §5.1 |
| TRAILING_STOP_LOSS_ORDER_ALREADY_EXISTS | oanda_transactions_*.json: one success, many rejects with same reason | §5.2 |
| Stale-order loop | AUD/USD BUY @ 0.7005 cancelled as stale then re-placed every 1–2 min (72+ pips away) | §5.3 |
| DeepSeek AUD/CHF vs AUD/USD | Trade-Alerts "Parsed DEEPSEEK: pairs: [USD/CHF, GBP/USD, AUD/CHF]"; AUD/USD BUY gets 3/4 (deepseek NO MATCH) | §5.4 |
| OANDA 502 | HTML "502 Bad gateway" in scalp-engine / UI log slice | §5.5 |
| UI DB init many times | "Opening existing database: scalping_rl.db" repeated per page load | §5.6 |

---

## References for Future Sessions

| Document / location | Purpose |
|--------------------|--------|
| **suggestions from cursor6.md** (`Trade-Alerts\Scalp-Engine\`) | Full cursor6 plan; inconsistencies 5.1–5.7; implementation order; what not to do. |
| **Backup (rollback)** `personal\backup_cursor6_20260304` | Full Trade-Alerts copy before any cursor6 implementation; restore if needed. |
| **CLAUDE.md** (`Trade-Alerts\`) | Architecture, do-not-do list. |
| **cursor_works.md** (`personal\`) | This file; Parts 1–9. |
| **Manual logs** (`C:\Users\user\Desktop\Test\Manual logs`) | trade-alerts_*, scalp-engine_*, scalp-engine-ui_*, oanda_transactions_*.json for verification. |

---

## Changelog (session summary)

- **Plan:** Created suggestions from cursor6.md from Manual logs review (Mar 4, 2026); cross-touchpoint consistency and forex-focused; no re-suggestion of already-implemented cursor5/consol-recommend4 items.
- **Backup:** Created backup_cursor6_20260304 (robocopy, 4240 files, exclude .git and __pycache__) for rollback.
- **Implementation:** Plan-only in Part 7; implementation carried out in **Part 8** (cursor6 5.1–5.6) and **Part 9** (user-reported fixes: max_trades, trailing, duplicates); commit 19f15a3 pushed.

*Part 7 last updated: Mar 5, 2026 — cursor6 Manual logs review, plan document, and backup; implementation in Parts 8–9.*

---

# Part 8: cursor6 Implementation (Mar 4, 2026)

---

## Goal of This Session

Implement the **plan** in `personal\Trade-Alerts\Scalp-Engine\suggestions from cursor6.md` in the suggested order, respecting the do-not-do list (no consensus formula change, no new TradeConfig fields without stripping, no `open_trade()` return signature change, one change at a time). Context: CLAUDE.md, cursor_works.md Parts 1–7.

---

## What Was Implemented (Summary Table)

| §   | Area                         | Implementation |
|-----|------------------------------|----------------|
| 5.1 | Active 6/4, 5/4 display     | **Display aligned with max_trades:** `get_active_trades_summary()` now returns `open_count` (OPEN/TRAILING/AT_BREAKEVEN only) and `pending_count`. Log line changed from "Active: X/Y" to **"Open: A/4, Pending: P, Unrealized: … pips"**. Status check every 10 checks logs **"Open Trades: open_count/max_trades"** and **"Pending Orders: pending_count"** (no longer "Active Trades: total/max_trades"). |
| 5.2 | TRAILING_STOP_LOSS_ORDER_ALREADY_EXISTS | **Check before create:** In `convert_to_trailing_stop()`, fetch TradeDetails and skip creation if trade already has `trailingStopLossOrder` or `trailingStopLossOrderID`; log at DEBUG. **On ALREADY_EXISTS:** When V20Error contains "ALREADY_EXISTS", return True and log INFO so caller sets state to TRAILING and no further attempts. Error logging truncates long/HTML messages. |
| 5.3 | Stale-order cancel/replace loop | **Stale-cancel cooldown:** When cancelling a pending order as stale in `_review_and_replace_pending_trades`, record `(pair_norm, direction_norm) -> (entry_price, time.time())` in `_stale_cancel_record`. In `_maybe_reset_run_count_and_open_trade`, before opening: purge expired entries (cooldown 600 s); if (pair, direction) has a recent stale cancel and new entry is within REPLACE_ENTRY_MIN_PIPS of cancelled entry, skip open and log "Skipping re-place after stale cancel … (cooldown)". |
| 5.5 | OANDA 502 in logs            | **502/5xx handling in `_request_with_retry`:** Catch V20Error; if code in (502, 503, 504) or >= 500, log WARNING with truncated message (no raw HTML), retry with backoff (delay = REQUEST_RETRY_DELAY_SEC * attempt). **USER_GUIDE §18:** Document that occasional 502 is transient; engine retries; if persistent, check broker and network. |
| 5.4 | DeepSeek AUD/CHF vs AUD/USD  | **Doc only:** USER_GUIDE §13 extended with paragraph "AUD/CHF vs AUD/USD (cursor6 §5.4)": confusion in LLM/parser can lower consensus for AUD/USD; no formula change; how to interpret "deepseek: NO MATCH" when AUD/CHF appears. |
| 5.6 | UI DB init many times        | **scalping_rl.py:** "Opening existing database" and "Database initialized successfully" changed from `print()` to `logger.debug()` so routine opens do not flood INFO. Directory creation and errors use `logger.info` / `logger.warning` / `logger.error`. **USER_GUIDE §5:** Note that multiple DB init/open per page load are expected; routine open at DEBUG; init-once applies to engine side. |

---

## Files Modified

| File | Changes |
|------|--------|
| `Scalp-Engine/auto_trader_core.py` | 5.1: `get_active_trades_summary()` returns `open_count`, `pending_count`. 5.2: `convert_to_trailing_stop()` checks TradeDetails for existing trailing stop; on ALREADY_EXISTS return True; truncate error msg. 5.5: `_request_with_retry()` catches V20Error, retries on 502/5xx with backoff, no raw HTML in log. |
| `Scalp-Engine/scalp_engine.py` | 5.1: Log "Open: X/Y, Pending: P" and status "Open Trades: X/Y", "Pending Orders: P". 5.3: `_stale_cancel_record`, `_stale_cancel_cooldown_seconds`; record on stale cancel; in `_maybe_reset_run_count_and_open_trade` skip re-place within cooldown when entry within REPLACE_ENTRY_MIN_PIPS. |
| `Scalp-Engine/src/scalping_rl.py` | 5.6: Use `logging`; "Opening existing database" and "Database initialized successfully" at DEBUG; "Creating new database" at INFO; directory/error at INFO/WARNING/ERROR. |
| `Scalp-Engine/USER_GUIDE.md` | §5 (UI DB): cursor6 §5.6 note (multiple init per load, DEBUG, init-once engine). §13: AUD/CHF vs AUD/USD (5.4). §18: OANDA 502 / bad gateway (5.5). |
| `Scalp-Engine/suggestions from cursor6.md` | Scope and footer updated to state implementation completed; reference Part 8. |

---

## Verification (for future sessions)

- Logs show **Open: A/4, Pending: P** (not "Active: 5/4" or "6/4") so max_trades semantics are clear.
- OANDA transaction history: TRAILING_STOP_LOSS_ORDER_REJECT with ALREADY_EXISTS should decrease; engine skips create when trailing already exists or treats ALREADY_EXISTS as success.
- Stale-order loop: After cancelling stale AUD/USD BUY @ 0.7005, engine should not re-place same level within 10 min unless entry moved by ≥ REPLACE_ENTRY_MIN_PIPS; log "Skipping re-place after stale cancel" when applicable.
- 502/5xx: No raw HTML in logs; WARNING with truncated message and retry; USER_GUIDE §18 present.
- UI: Multiple "Opening existing database" / "Database initialized" only at DEBUG (set logging to DEBUG for scalping_rl to see them).
- No change to consensus formula, TradeConfig fields, or `open_trade()` return signature.

---

## References

- **Plan:** `Trade-Alerts\Scalp-Engine\suggestions from cursor6.md`
- **Backup (rollback):** `personal\backup_cursor6_20260304`
- **CLAUDE.md:** `Trade-Alerts\CLAUDE.md`

*Part 8 last updated: Mar 4, 2026 — cursor6 plan implemented (5.1–5.6) and documented.*

---

# Part 9: User-Reported Fixes — max_trades, Trailing, Duplicates (Follow-up Session)

---

## Goal of This Session

Address three user-reported issues after cursor6 implementation: (1) **6/4 trade count** — there should never be more open trades than set in the UI (max_trades); (2) **Trailing stop not working properly** — trailing was activating in losing trades or before breakeven; (3) **Multiple trades of the same pair** opened at the same time. User provided Manual logs references (ODT files: "Tailing stop activated in a losing trade.odt", "Tailing stop not working properly. It get activated even before Breakeven.odt", "Multiple trades opened for same pairs.odt"). No new plan document; fixes implemented directly in Scalp-Engine and documented here.

---

## Issues and Root Causes (User Report)

| Issue | User description | Intended behaviour |
|-------|------------------|--------------------|
| 6/4 count | "The 6/4 count of trades is definitely an issue … There should never be more trades than are set in the UI." | Open positions on OANDA must never exceed `max_trades`; no new order sent if OANDA already has ≥ max_trades. |
| Trailing in loss / before BE | "Trailing stop loss is not working properly … get activated even before Breakeven" / "activated in a losing trade." | Trailing should only activate when the trade is **in profit** (at least a small buffer), never at flat breakeven or in loss. |
| Same-pair duplicates | "Multiple trades of the same pair are also being opened at the same time." | One open position per (pair, direction); final check immediately before sending order to OANDA. |

---

## What Was Implemented (Summary)

### 1. Max trades: never exceed UI limit

- **Final gate before send** (in `PositionManager.open_trade()`, in `Scalp-Engine/auto_trader_core.py`): Immediately before calling `executor.open_trade(trade)` we now:
  - Fetch current open positions from OANDA (`get_open_positions()`).
  - If **open count ≥ max_trades** → do **not** send the order; remove the in-memory placeholder; log **ERROR**: "BLOCKED: OANDA has X open positions (max_trades=Y). Not opening … would exceed limit"; return `None`.
  - If **(pair, direction)** already exists on OANDA → do **not** send; remove placeholder; log **ERROR**: "BLOCKED DUPLICATE (final check): … already on OANDA"; return `None`.
  - If the final OANDA check fails (e.g. API error), we abort the open and remove the placeholder (do not send blindly).
- **Visibility in `can_open_new_trade()`:** When `oanda_count > max_trades` we log **ERROR**: "OANDA has more open positions (X) than max_trades (Y). Not opening new trades until count is below limit." so Manual logs show when the cap is hit.

Result: New orders are never sent when OANDA already has ≥ max_trades; if OANDA ends up with more (e.g. from UI or another system), no further opens until count is below the limit.

### 2. Trailing stop: only when in profit (never in loss or before breakeven)

- **`MIN_PROFIT_PIPS_FOR_TRAILING = 1.0`** (class attribute on `PositionManager`): Minimum profit in pips required before converting to trailing stop.
- **ATR_TRAILING (`_check_ai_trailing_conversion`):** Conversion no longer uses "at or past breakeven". We now require **in profit by at least 1 pip**:
  - Long: `current_price >= entry + min_profit_distance` (1 pip).
  - Short: `current_price <= entry - min_profit_distance`.
- **BE_TO_TRAILING (`_check_be_transition`):** When state is AT_BREAKEVEN, we only convert to TRAILING when the trade is **at least 1 pip in profit** (same formula). Moving SL to breakeven still happens at breakeven; only the "convert to trailing" step is delayed until 1 pip profit.
- **USER_GUIDE §17:** Updated to state that trailing is only activated when the trade is at least 1 pip in profit (never in loss or at flat breakeven).

Result: Trailing is never activated in a losing trade or at flat breakeven; only after at least 1 pip profit.

### 3. Duplicate same pair: final check before send

- The **final gate** (same block as max_trades) re-checks **(pair, direction)** on OANDA immediately before `executor.open_trade(trade)`. If that pair/direction already exists, we do not send, remove the placeholder, and log "BLOCKED DUPLICATE (final check)".

Result: Last line of defence against opening a second position in the same (pair, direction) even if an earlier check was missed or a race occurred.

---

## Files Modified (Part 9)

| File | Changes |
|------|--------|
| `Scalp-Engine/auto_trader_core.py` | Final OANDA gate before `executor.open_trade()`: check `len(oanda_trades) >= max_trades` and (pair, direction) on OANDA; abort and remove placeholder if either; on OANDA check failure abort open. In `can_open_new_trade()`: ERROR log when `oanda_count > max_trades`. `MIN_PROFIT_PIPS_FOR_TRAILING = 1.0`; in `_check_ai_trailing_conversion` require 1 pip in profit; in `_check_be_transition` (AT_BREAKEVEN → TRAILING) require 1 pip in profit. |
| `Scalp-Engine/USER_GUIDE.md` | §17: Trailing only activated when at least 1 pip in profit. |

---

## Verification (for future sessions)

- **Max trades:** Manual logs show ERROR when OANDA has more than max_trades; no new order sent when OANDA count ≥ max_trades; "BLOCKED: OANDA has X open positions" when applicable.
- **Trailing:** No "converted to trailing stop" when trade is in loss or at flat breakeven; only after ≥ 1 pip profit; USER_GUIDE §17 reflects this.
- **Duplicates:** No second position for same (pair, direction); if a duplicate attempt occurs, "BLOCKED DUPLICATE (final check)" in logs.

---

## Commit and Push

- **Repo:** `personal/Trade-Alerts` (remote: `https://github.com/ibenwandu/Trade-Alerts`)
- **Branch:** `main`
- **Commit:** `19f15a3` — "Scalp-Engine: cursor6 implementation + max_trades/trailing/duplicate fixes"
- **Pushed:** e45666d..19f15a3 main → main

Part 9 fixes were included in the same commit as the cursor6 implementation (single push). No separate backup was taken for Part 9; rollback would use `personal\backup_cursor6_20260304` if needed.

---

## References

- **Plan (cursor6):** `Trade-Alerts\Scalp-Engine\suggestions from cursor6.md`
- **Backup (rollback):** `personal\backup_cursor6_20260304`
- **CLAUDE.md:** `Trade-Alerts\CLAUDE.md`
- **Manual logs (user evidence):** `C:\Users\user\Desktop\Test\Manual logs\` — user referenced ODTs: "Tailing stop activated in a losing trade.odt", "Tailing stop not working properly. It get activated even before Breakeven.odt", "Multiple trades opened for same pairs.odt" (binary; content not read by session).

*Part 9 last updated: session documenting user-reported fixes (max_trades, trailing, duplicates) and commit/push for future context.*

---

# Part 10: Multiple Pending Same Pair / UI Shows One Row (Follow-up)

---

## Goal of This Session

Address **multiple pending orders for the same pair** on OANDA (e.g. two USD/JPY SELL LIMIT with different ticket IDs) and the **UI showing them as one** pending trade. User provided: OANDA screenshot (two USD/JPY 2000 SELL LIMIT @ 157.800, tickets 26306 and 26302); Scalp-Engine Dashboard showing "Loaded 2 trades from API" but expectation that each OANDA ticket should appear as its own row when same pair has multiple orders.

---

## Root Cause

1. **Duplicate pending orders created:** The **final gate** before send only checked **open positions** (`get_open_positions()`). It did not check **pending orders**. So we could have 0 open USD/JPY positions but 1 pending USD/JPY SELL LIMIT; the gate allowed a second pending order for the same (pair, direction).
2. **UI showing one row for multiple tickets:** The engine sends one list entry per trade/order (each with `trade_id`). If the server that stores the trades list (e.g. Config API POST /trades) **keys or merges by (pair, direction)**, only one entry is kept and the UI displays one row for multiple OANDA tickets.

---

## What Was Implemented

### 1. Final gate: check OANDA pending orders before send

- In `PositionManager.open_trade()`, after checking open positions (count and duplicate pair/direction), we now **fetch pending orders** via `executor.get_pending_orders()` and, if any pending order has the same **(pair, direction)**, we **do not send** and log:  
  `BLOCKED DUPLICATE (final check – pending): {pair} {direction} already has pending order (OANDA order …) - not sending another.`
- **`TradeExecutor.get_pending_orders()`** added: uses OANDA `PendingOrders` endpoint, returns `response.get('orders', [])`. Used in the final gate and by existing sync/orphan logic (which now calls this method instead of inline PendingOrders).

### 2. One entry per trade/order in state and API payload

- **Comment in `_save_state()`:** The trades list is one entry per trade/order (keyed by trade_id/order_id in memory) and must **not** be merged by (pair, direction), or the UI will show one row for multiple OANDA orders.
- **USER_GUIDE §10(d)** added: Explains that the engine sends one list entry per `trade_id`; if the UI shows one row for multiple OANDA tickets, the server that stores the trades list should keep one entry per `trade_id`/order ID and the UI should show one row per list item.

---

## Files Modified (Part 10)

| File | Changes |
|------|--------|
| `Scalp-Engine/auto_trader_core.py` | `TradeExecutor.get_pending_orders()` added. Final gate: after open-positions check, call `get_pending_orders()` and block if (pair, direction) already has a pending order. Comment in `_save_state()` re one entry per trade_id. |
| `Scalp-Engine/USER_GUIDE.md` | §10(d): Multiple pending same pair – UI shows one row; store/display by trade_id; engine blocks second pending in final gate. |

---

## Verification (for future sessions)

- No second **pending** order sent for same (pair, direction); logs show "BLOCKED DUPLICATE (final check – pending)" when applicable.
- Config API / UI: If multiple OANDA tickets for same pair, store and display one row per `trade_id` so each ticket is visible (fix is on server/UI side if they currently merge by pair/direction).

---

## Log review expectation (user request)

User asked that **when reviewing logs**, the same type of checks as in this session be done: cross-touchpoint consistency (Trade-Alerts, Scalp-engine, Scalp-engine UI, OANDA), max_trades vs display, trailing only in profit, duplicate (open + **pending**) same pair, UI vs OANDA alignment (one row per ticket). A **"Log review checks"** subsection was added near the top of cursor_works.md (after the Quick reference table) so future sessions know what to verify.

---

*Part 10 last updated: multiple pending same pair; final gate pending-orders check; get_pending_orders(); USER_GUIDE §10(d); log review checks documented.*

---

# Part 11: Indeed-jobs — Same Results Over Days; Already-Reported Filter

---

## Goal of This Session

User was **getting the same Indeed job search results over the past two days**. They asked to review report folders and then to (1) increase the date window to 3 days and (2) **ensure jobs that have been selected/reported before do not appear in future selection**.

---

## What Was Reviewed

- **Reports:** `personal/Indeed-jobs/reports/2026-03-05_1415/report.md`, `2026-03-04_1104/report.md`, `2026-03-03_2358/report.md`.
- **Finding:** All three contained the **same 25 job IDs** (only score/order differed). So either the workflow was reusing cache without a fresh fetch, or Indeed was returning the same postings because `days_posted: 1` (last 24h) keeps many listings in the window for 2–3 days.

---

## Implementations and Fixes

### 1. Increase window to 3 days

- **File:** `personal/Indeed-jobs/config/indeed_search.json`
- **Change:** `"days_posted": 1` → `"days_posted": 3` (Indeed `fromage`: last 3 days).
- **Reason:** Broader window so each fetch can include newer postings and more turnover.

### 2. Already-reported filter (exclude previously reported jobs)

- **Purpose:** Jobs that have already been included in a report are excluded from **future** score/report runs, so the same job does not keep appearing run after run.
- **Persistence:** Job IDs (Indeed `jk`) are stored in **`output/reported_job_ids.txt`** (one ID per line; lines starting with `#` ignored).
- **Config:** `src/config.py` — added `REPORTED_JOB_IDS_PATH = OUTPUT_DIR / "reported_job_ids.txt"`.
- **Job cache:** `src/job_cache.py` — added:
  - **`load_reported_job_ids(path=None)`** — returns `set[str]` of IDs already reported.
  - **`append_reported_job_ids(job_ids, path=None)`** — appends IDs to the file after a report.
- **Workflow:** `run_workflow.py` — in **`run_score_and_report()`**:
  - Before scoring: load cache, load `reported_job_ids`, **filter out** jobs whose `jk` is in that set.
  - If no jobs remain: print that all jobs were already reported; suggest running fetch again or clearing the file; return.
  - Score and report only the **filtered** list.
  - After writing the report: **append** the job IDs from this run to `reported_job_ids.txt`.
- **Override:** **`--include-reported`** — when set, the filter is skipped (score and report all jobs in cache; do not append to the file).
- **Resumes:** Unchanged. Resumes still use `config/approved_jobs.txt` and the cache; the filter only affects which jobs appear in **reports**.

### 3. Create `reported_job_ids.txt` so it exists from the start

- **Issue:** The file was only created when the first report run appended IDs, so `output/reported_job_ids.txt` did not exist until after the first score/report.
- **Fix:** Created **`personal/Indeed-jobs/output/reported_job_ids.txt`** with a short comment header. Comment lines are ignored when loading; IDs are appended below after each report.

### 4. README and docs

- **README.md:**
  - **days_posted:** Documented as `1` = last 24h, `3` = last 3 days, `7` = last 7 days; note that `1` often repeats for 2–3 days.
  - **Same jobs / already-reported:** Explained that reports use the cache; that job IDs in `output/reported_job_ids.txt` are excluded from future reports; that `--include-reported` bypasses the filter; and that deleting/editing the file resets the list.

---

## Files Modified (Part 11)

| File | Changes |
|------|--------|
| `Indeed-jobs/config/indeed_search.json` | `days_posted`: 1 → 3. |
| `Indeed-jobs/src/config.py` | `REPORTED_JOB_IDS_PATH` added. |
| `Indeed-jobs/src/job_cache.py` | `load_reported_job_ids()`, `append_reported_job_ids()` added. |
| `Indeed-jobs/run_workflow.py` | Filter by reported IDs in `run_score_and_report()`; append IDs after report; `--include-reported` flag. |
| `Indeed-jobs/README.md` | days_posted options; "Same jobs every day?" replaced with explanation of reported filter and `--include-reported`. |
| `Indeed-jobs/output/reported_job_ids.txt` | Created with comment header (file exists from the start). |

---

## Verification (for future sessions)

- After a report run, **`output/reported_job_ids.txt`** contains the job IDs from that run (appended).
- A later run (same or new cache) **excludes** those IDs from the report; only jobs not in the file are scored and reported.
- If all jobs in cache are already in the file, the run prints that all were already reported and suggests fetch or clearing the file.
- **`--include-reported`** causes all jobs in cache to be scored and reported, and no append to the file.

---

## Other job-pipeline context (same timeframe)

- **Scoring-criteria and profile_loader** changes were made in **Indeed-jobs**, **Indeed-jobs-cs**, **Linkedin-jobs**, **Linkedin-jobs-cs** (e.g. remove key_differentiators, required_skills, industries; add weights to location/salary; profile_loader no longer references removed fields). See each project’s `config/scoring-criteria.json` and `src/profile_loader.py`.
- **Indeed-jobs-cs** and **Linkedin-jobs-cs** were completed as customer-success mirrors of Indeed-jobs and Linkedin-jobs (same pipeline; CS-focused config and keywords).

---

*Part 11 last updated: Indeed-jobs same results; days_posted 3; already-reported filter (reported_job_ids.txt); --include-reported; create reported_job_ids.txt in output.*

---

# Part 12: Manual logs folder and .odt files (session prep)

---

## Location and contents

- **Folder:** `C:\Users\user\Desktop\Test\Manual logs`
- **Log files:** Many timestamped backups: `trade-alerts_*.txt`, `scalp-engine_*.txt`, `scalp-engine-ui_*.txt`, `config-api_*.txt`, `market-state-api_*.txt`, `oanda_*.txt`, `oanda_transactions_*.json` (Feb 28 – Mar 5, 2026). Also `error_log.txt`, `Additional quality checks to review using the Logs.txt` (never moved by hygiene).
- **.odt files (user evidence):** At least two present:
  - **Tailing stop activated in a losing trade.odt** — content is mostly **two embedded PNG screenshots**; no substantive text in `content.xml`. Information is visual (logs/dashboard).
  - **Tailing stop not working properly. It get activated even before Breakeven.odt** — has **text** in `content.xml`: *"Tailing stop not working properly. It get activated even before Breakeven thereby reducing the original SL cushion and increasing the risk of the trade being stopped out."* Plus two embedded PNGs.
- **Reference:** cursor_works Part 9 also mentioned **Multiple trades opened for same pairs.odt**; if present, same reading method applies.

## Reading .odt files

- **Confirmed:** .odt can be read by treating the file as **ZIP**, extracting it, and reading **`content.xml`** (OpenDocument XML).
- **Method:** Copy the .odt to a `.zip` file, then `Expand-Archive` (PowerShell) or any ZIP extractor; open `content.xml`. Paragraph text is in `<text:p>` and `<text:span>` elements.
- **Limitation:** When the ODT is mainly **screenshots**, the only “content” is embedded images (e.g. under `Pictures/` in the ODT). Text in those images is not in the XML; for image content, use the extracted PNGs (e.g. Read tool on the image path) in a future session if needed.

## Quality checks (reference)

The file **Additional quality checks to review using the Logs.txt** lists seven checks: (1) trailing stop loss, (2) Structure_ATR Stages SL, (3) profitable trades with trailing stops closing as losses, (4) RL runs, (5) trading hours, (6) sync Open/Pending (OANDA, UI, engine), (7) orphan trades. Align with the “Log review checks” section near the top of this document.

---

## Comparison with improvementplan.md (Trade-Alerts)

**File:** `Trade-Alerts/improvementplan.md` (Mar 5, 2026; source: suggestions_from_anthropic6.md + codebase).

| improvementplan.md finding / fix | cursor_works / prior findings | Comparison |
|----------------------------------|-------------------------------|------------|
| **Fix 1 — max_runs blocks 97%:** `reset_run_count()` doesn’t clear **legacy** key; reset silently does nothing. Fix: clear legacy key in `execution_mode_enforcer.reset_run_count()`. | Part 3 cont. / Part 6: max_runs **reset logic verified present** in auto_trader_core (REJECT + no position → reset_run_count, re-get directive). | **New root cause:** Prior notes said reset exists; improvement plan shows it **fails** because execution_history uses legacy keys (`EUR/USD_LONG`) and reset only deletes new key (`LLM_EUR/USD_LONG`). Fix 1 is the correct next step. |
| **Fix 2 — 80% premature closures:** MACD reverse-crossover check runs on **all** open trades every 60s regardless of `sl_type`. Fix: guard with `trade.sl_type == StopLossType.MACD_CROSSOVER`. | Part 6 (5.7): MANUAL_CLOSURES_INVESTIGATION.md — list of close_trade call sites (MACD, DMI, trading hours, etc.); **investigation only**, no code fix. | **Specific cause and fix:** Improvement plan identifies the exact block (scalp_engine.py 3155–3162) and restricts MACD close to MACD_CROSSOVER trades. Aligns with quality check 3 (profitable→loss). |
| **Fix 3 — JPY MARKET unguarded:** JPY sanity check only in LIMIT/STOP branch; MARKET orders skip it. Fix: apply JPY check to all order types. | Part 3 cont. Phase 1.1: JPY **limit/stop** entry price scale fixed (scale or reject). | **Gap closed:** cursor_works did not mention MARKET; improvement plan adds MARKET to the same sanity logic. |
| **Fix 4 — Trailing SL (BLOCKED):** Code uses OrderCreate TRAILING_STOP_LOSS correctly; user confirms still not working. No code change until Phase 0.5 log investigation. | Part 5/6/8/9: ATR trailing OrderCreate, observability, ALREADY_EXISTS handling, **trailing only when ≥1 pip profit** (Part 9). ODTs: “activated in losing trade” / “before Breakeven”. | **Aligned:** 1-pip rule (Part 9) already addresses “activated in loss/before BE”. Improvement plan adds: investigate logs (Phase 0.5 checklist) before any further trailing fix; possible causes listed (pre-flight skip, distance units, ALREADY_EXISTS stale, etc.). |
| **Phase 0.5 — Trailing SL log investigation:** Search logs for ATR Trailing, convert_to_trailing_stop, pre-flight skip, OANDA errors; cross-check oanda_transactions for TRAILING_STOP_LOSS_ORDER; check distance value. | Part 12: Manual logs folder and .odt content; log review checks (trailing, ALREADY_EXISTS, etc.). | **Reinforces:** Phase 0.5 checklist is the right next step using Manual logs (and extracted ODT screenshots if needed). |

**Not in improvementplan (still from cursor_works / quality checks):** Structure_ATR (quality check 2), RL (4), trading hours (5 — plan says “by design”), sync (6), orphans (7). Duplicate/max_trades fixes (Parts 6, 9, 10) are unchanged; plan does not reopen them.

**Deployment order (improvementplan):** Fix 1 → Fix 2 → Fix 3 → Phase 0.5 investigation → Fix 4 (trailing, after investigation).

---

## Trailing stop: evidence from .odt screenshots and Manual logs

The following was derived by extracting and viewing the **ODT embedded images** and searching **scalp-engine_*.txt** and **oanda_transactions_*.json** in Manual logs.

### 1. ODT screenshots — what they show

| ODT | Screenshot | What it shows |
|-----|------------|----------------|
| **Tailing stop activated in a losing trade** | 1. GBP/JPY 15m chart (OANDA) | TRAILING STOP line at ~210.816; current price ~210.456; second line at ~210.301 (-3.13, 2000). |
| | 2. Scalp-engine UI dashboard | **Sync status: UNKNOWN**, Last Sync: Never. **2 active trades:** EUR/GBP BUY (TRAILING) ATR-Trail **+1.8 pips** (green); **GBP/JPY SELL (TRAILING) ATR-Trail -17.9 pips** (red). |
| **Tailing stop not working properly / before Breakeven** | 1. GBP/USD 1h chart | **TRAILING STOP 2000** at **1.34075** (above price); current price **1.33502**; TAKE PROFIT 2000 at 1.32950. Short position: trailing stop is above price and not moving down with price. |
| | 2. Scalp-engine UI | 4 trades loaded; all **(TRAILING)** ATR-Trail: EUR/GBP BUY +11.9, GBP/JPY SELL +51.9, GBP/USD SELL +5.8, EUR/JPY SELL +14.7 pips (all green). |

**Interpretation:**

- **“Activated in a losing trade”:** UI shows **GBP/JPY SELL (TRAILING)** at **-17.9 pips**. So the system had already marked this trade as TRAILING while it was in loss — either (a) conversion happened when it was briefly in profit and then price moved against it, or (b) state was set to TRAILING without the ≥1 pip profit check (e.g. before Part 9 fix, or ALREADY_EXISTS path setting state without re-checking profit).
- **“Before breakeven”:** User text says trailing activates before breakeven and reduces the original SL cushion. GBP/USD screenshot shows trailing stop **above** current price for a short — consistent with a stop placed near entry that never moved down as price moved in favour.
- **Sync status UNKNOWN / Never:** UI had not run a sync check; possible mismatch between engine state and OANDA (e.g. engine thinks TRAILING, OANDA may have different order state).

### 2. Scalp-engine logs — conversion path

- **Searched for:** `ATR Trailing: attempting conversion`, `Converted to trailing`, `Failed to convert`, `already exists`, `ALREADY_EXISTS`, `converted to trailing`.
- **Result:** **No matches** in any `scalp-engine_*.txt` in Manual logs.
- **Implications:** Either (a) in the backup windows there were no OPEN ATR_TRAILING trades (e.g. recent logs show Open: 0/4, Pending: 3–4), so the conversion block was never entered; (b) `current_price` was missing for those trades and they were skipped (DEBUG “Skipping … no current_price” would not appear in INFO logs); or (c) conversion runs only when there are open trades in profit, and the backup timeframe didn’t capture that.

Config lines **Stop Loss Type: ATR_TRAILING** and **Open: X/4, Pending: P** appear regularly; no INFO-level conversion success/failure logs.

### 3. OANDA transactions — trailing stop creates and rejects

- **TRAILING_STOP_LOSS_ORDER** (success): Present in `oanda_transactions_2026-03-05_1700.json` and `_2100.json` (multiple `type` and `reason` entries). So trailing stops **are** being created successfully in some cases.
- **TRAILING_STOP_LOSS_ORDER_REJECT** with **TRAILING_STOP_LOSS_ORDER_ALREADY_EXISTS**: In `oanda_transactions_2026-03-05_1500.json` (and similar), **same trade IDs** (e.g. 24968, 25085, 25292) get repeated rejects at 20:00:34, 20:02:32, 20:04:27… with `distance`: `"0.003"` (non-JPY) or `"0.3"` (JPY). So the engine is **repeatedly** sending “create trailing stop” for trades that already have one; OANDA correctly rejects with ALREADY_EXISTS.
- **Possible causes:** (1) Pre-flight check (trade already has `trailingStopLossOrder`) does not see the existing order, so we call the API every cycle. (2) On ALREADY_EXISTS we return True and set `trade.state = TRAILING`, but state is not persisted before restart or next run, so we try again. (3) Multiple engine instances or restarts so in-memory state is lost and we retry.

### 4. Summary for Phase 0.5 / Fix 4

| Finding | Source | Suggestion |
|--------|--------|------------|
| Trailing can appear on losing or pre-BE trades in UI | ODT “losing trade” + “before Breakeven” | Ensure 1-pip rule is enforced everywhere we set TRAILING (including when handling ALREADY_EXISTS). |
| No “attempting conversion” / “Converted to trailing” in logs | scalp-engine_*.txt | Confirm backup window includes periods with OPEN ATR_TRAILING trades in profit; if yes, add or raise log level for conversion attempt so Phase 0.5 can see it. |
| Repeated ALREADY_EXISTS rejects for same trades | oanda_transactions_*.json | Fix pre-flight: when TradeDetails shows `trailingStopLossOrderID` / trailing already present, skip create and set state to TRAILING without calling API. And/or ensure ALREADY_EXISTS → set TRAILING and persist state so we don’t retry next cycle. |
| Trailing stop line not moving (e.g. GBP/USD short) | ODT chart | After conversion, OANDA holds the trailing order; if the line doesn’t move, either the order wasn’t created correctly (distance/units) or the UI/chart is not reflecting OANDA’s trailing order. Cross-check with OANDA position/order details. |

---

*Part 12 last updated: Manual logs folder reviewed; .odt read method confirmed; comparison with improvementplan.md; trailing-stop evidence from ODT screenshots and logs added for Phase 0.5 / Fix 4.*

---

# Part 13: Improvement Plan Implementation Session (Mar 5, 2026)

---

## Goal of this session

Provide context for future sessions by (1) reviewing cursor_works.md, (2) reviewing Manual logs and .odt files, (3) comparing findings with improvementplan.md, (4) gathering evidence on trailing-stop issues from ODTs and logs, (5) implementing improvement plan Fixes 1–3, and (6) committing and pushing changes. All of this is documented here so the next session has full context.

---

## Session flow (what was done)

| Step | User request | Action taken |
|------|--------------|--------------|
| 1 | Review cursor_works.md for next session context | Read `personal/cursor_works.md` and `personal/job-alert-resume/cursor_works.md`; summarized quick-reference table and key areas (BackupRenderLogs, Scalp-Engine/Trade-Alerts Parts 2–10, Indeed-jobs Part 11). |
| 2 | Review Manual logs; confirm .odt can be read | Listed `C:\Users\user\Desktop\Test\Manual logs`; extracted .odt as ZIP, read `content.xml`; confirmed text in `<text:p>`/`<text:span>`; noted first ODT = images, second ODT = text + images. Added **Part 12** with location, .odt read method, quality checks reference. |
| 3 | Compare improvementplan.md with findings | Added **Comparison with improvementplan.md** table to Part 12 (Fix 1–4 vs cursor_works; deployment order). |
| 4 | Use .odt and logs to shed light on trailing stop | Extracted ODT images; read all four PNGs (dashboard: GBP/JPY -17.9 pips TRAILING; GBP/USD chart trailing stop above price; etc.). Searched scalp-engine_*.txt (no conversion logs); oanda_transactions_*.json (TRAILING_STOP_LOSS_ORDER + repeated ALREADY_EXISTS). Added **Trailing stop: evidence from .odt screenshots and Manual logs** to Part 12 with interpretation and Phase 0.5 suggestions. |
| 5 | Implement the fixes | Implemented **Fix 1** (reset_run_count legacy key), **Fix 2** (MACD close only for MACD_CROSSOVER), **Fix 3** (JPY sanity for all order types). Fix 4 left **blocked** per plan. Updated improvementplan.md with status and changelog. |
| 6 | Commit and push changes | Staged Scalp-Engine and improvementplan.md; committed; pushed to origin main. |

---

## What was implemented (Fixes 1–3)

| Fix | File | Change |
|-----|------|--------|
| **Fix 1** | `Scalp-Engine/src/execution/execution_mode_enforcer.py` | **reset_run_count(opp_id):** Now clears both new-format key (e.g. `LLM_EUR/USD_LONG`) and legacy key (e.g. `EUR/USD_LONG`) using same legacy-key logic as `_get_run_count()`. Logs "Reset run count for {opp_id} (legacy key also cleared)" or DEBUG when no entry found. Prevents max_runs from permanently blocking after reset. |
| **Fix 2** | `Scalp-Engine/scalp_engine.py` | **MACD reverse-crossover close:** Wrapped in `if trade.sl_type == StopLossType.MACD_CROSSOVER:` so only MACD_CROSSOVER trades are closed on MACD signal. ATR_TRAILING, BE_TO_TRAILING, STRUCTURE_ATR (and other sl_types) are no longer closed by this check. Addresses ~80% premature closures. |
| **Fix 3** | `Scalp-Engine/auto_trader_core.py` | **JPY sanity check:** Moved before `order_type` branch; applies to **MARKET**, LIMIT, and STOP. For JPY pairs: if `0 < entry_price < 10`, correct with TP scale or reject; if `entry_price <= 0`, reject. Closes gap where MARKET orders skipped the check. |

**Fix 4 (Trailing SL):** Not implemented. Blocked until Phase 0.5 log investigation is completed and a specific failure mode is documented (see improvementplan.md Phase 0.5 and Part 12 trailing-stop evidence).

---

## Files modified (this session)

| File | Purpose |
|------|--------|
| `personal/cursor_works.md` | Part 12 (Manual logs, .odt, comparison, trailing evidence); Part 13 (this session summary); quick-reference table updated. |
| `Trade-Alerts/improvementplan.md` | Added to repo; status line (Fixes 1–3 implemented, Fix 4 blocked); changelog (implementation notes). |
| `Trade-Alerts/Scalp-Engine/src/execution/execution_mode_enforcer.py` | Fix 1. |
| `Trade-Alerts/Scalp-Engine/scalp_engine.py` | Fix 2. |
| `Trade-Alerts/Scalp-Engine/auto_trader_core.py` | Fix 3. |

---

## Commit and push

- **Repo:** `personal/Trade-Alerts` (remote: https://github.com/ibenwandu/Trade-Alerts)
- **Branch:** `main`
- **Commit:** `35e7ec8` — "Scalp-Engine: improvement plan Fixes 1-3 (max_runs legacy key, MACD guard, JPY MARKET sanity)"
- **Pushed:** 35260f4..35e7ec8 main → main

Not committed (left local/untracked): `.claude/settings.local.json`, `suggestions_from_anthropic6.md`.

---

## Verification (for future sessions)

- **Fix 1:** After deploy, look for log "Reset run count for … (legacy key also cleared)"; previously blocked pairs (e.g. after position closed) should open within 2 cycles; `reason=max_runs` rejections should drop from ~97% toward <20%.
- **Fix 2:** Trades with ATR_TRAILING or BE_TO_TRAILING should no longer close on MACD signals; only MACD_CROSSOVER trades close on reverse crossover; premature closure rate should drop.
- **Fix 3:** JPY MARKET orders with valid entry (e.g. 156.xxx) open normally; wrongly scaled JPY entry (e.g. 1.56 without TP to infer scale) rejected with "JPY price sanity check failed".

---

## References for future sessions

| Document / location | Purpose |
|---------------------|--------|
| **improvementplan.md** | `Trade-Alerts/improvementplan.md` — Full plan; Fixes 1–3 implemented; Fix 4 blocked; Phase 0.5 checklist; deployment order. |
| **Part 12 (cursor_works.md)** | Manual logs path; .odt read method; improvementplan comparison; trailing-stop evidence (ODT screenshots, scalp-engine logs, oanda_transactions). |
| **Log review checks** | Top of cursor_works.md — Max trades, trailing, duplicate, UI/OANDA, stale-order, ALREADY_EXISTS, 502. |
| **Manual logs** | `C:\Users\user\Desktop\Test\Manual logs` — Timestamped backups; .odt user evidence; Additional quality checks to review using the Logs.txt. |

---

*Part 13 last updated: Session plan, implementations (Fixes 1–3), commit 35e7ec8, and references documented for future context.*

---

# Part 14: 3× GBP/USD on OANDA, Only 1 on UI/Logs (Mar 2026)

---

## User report

OANDA showed **3 instances** of GBP/USD (e.g. three STOP LOSS lines on the chart, plus SELL LIMIT, SELL ENTRY, TAKE PROFIT), but the **Scalp-Engine UI** showed only **1** GBP/USD row (“Loaded 4 trades from API” with one GBP/USD SELL PENDING), and the **logs** showed one placed order and one blocked duplicate (RED FLAG BLOCKED DUPLICATE – only one order per pair allowed).

---

## Root cause

- The engine stores one entry per **trade_id** / order ID in `active_trades` and POSTs that list to the Config API; the Config API stores the payload as-is (no merge by pair/direction). So the UI shows whatever list the engine last POSTed.
- On **engine startup**, state was loaded from disk but **only** trades with state OPEN, AT_BREAKEVEN, or TRAILING were added to `active_trades`. **PENDING** trades in the state file were **skipped**, so after a restart the engine had fewer entries than before (all PENDING dropped). It would then repopulate from OANDA on the next sync, but until sync ran (and if sync ran before the next POST), the engine could POST a list with only one GBP/USD (e.g. the single open or the single one that was in memory from the last run). So the UI could show 1 row even when OANDA had 3.

---

## Fix implemented

**Load PENDING trades from state file on startup** (`Scalp-Engine/auto_trader_core.py`, `_load_state`):

- When restoring from the state file, include **TradeState.PENDING** in the allowed states so that every trade with a valid `trade_id` (including order IDs for pending orders) is restored into `active_trades`.
- The engine then POSTs the full list (one entry per trade/order ID) to the Config API, so the UI can show one row per OANDA ticket (e.g. 3× GBP/USD when there are 3 orders).

**USER_GUIDE §10(d):** Added a short note that the engine now loads OPEN, AT_BREAKEVEN, TRAILING, and PENDING from disk on startup, so after a restart the full list is restored and the UI can display one row per ticket.

---

## Files modified

| File | Change |
|------|--------|
| `Scalp-Engine/auto_trader_core.py` | In `_load_state()`, allow `TradeState.PENDING` when adding trades from file to `active_trades`. |
| `Scalp-Engine/USER_GUIDE.md` | §10(d): note on engine load (PENDING included on restart). |

---

## Verification (for future sessions)

- After engine restart, if the state file contained multiple entries for the same pair (e.g. 3× GBP/USD with different trade_id/order_id), all of them should appear in the UI (3 rows).
- Logs: “Loaded N active trades from disk” should reflect the full count including PENDING; subsequent POST to Config API sends that list so “Loaded N trades from API” in the UI matches.

---

*Part 14 last updated: 3× GBP/USD on OANDA vs 1 on UI — load PENDING from state file; USER_GUIDE §10(d) updated.*

---

# Part 15: Orphan/Duplicate Cleanup — Single (Pair, Direction) on OANDA and UI

---

## Requirement

The system **must never** allow multiple open positions or multiple pending orders for the same (pair, direction) on OANDA or on the UI. User requested cleanup of orphan/duplicate trades on OANDA and strict enforcement of one-per-pair.

---

## What was implemented

**1. Cleanup on every sync** (`Scalp-Engine/auto_trader_core.py`)

- **`_cleanup_duplicate_positions_and_orders_on_oanda()`** runs at the **start** of `sync_with_oanda()` (before the rest of sync).
- **Open positions:** Group OANDA open positions by (pair, direction). For any group with more than one position, **keep one** (prefer the trade id we have in `active_trades`, else the oldest by id) and **close** the others via `executor.close_trade(tid, "Cleanup: duplicate (pair, direction) - only one allowed")`. Removes closed trade ids from `active_trades`.
- **Pending orders:** Group OANDA pending orders by (pair, direction). For any group with more than one order, **keep one** (same rule) and **cancel** the others via `executor.cancel_order(oid, ...)`. Removes cancelled order ids from `active_trades`.
- Logs: `🧹 Cleaned up duplicate open position: {pair} {direction} (closed trade_id=…, keeping …)` and `🧹 Cleaned up duplicate pending order: …` when extras are closed/cancelled. Cleanup failures are logged as warning and do not abort sync.

**2. Enforcement**

- **Existing:** Final gate before placing an order already blocks if (pair, direction) exists in OANDA open positions or pending orders (Parts 6, 9, 10). No second order is sent.
- **New:** Every sync **removes** any existing duplicates on OANDA (close/cancel extras), so OANDA and the engine/UI stay aligned with at most one open and one pending per (pair, direction).

---

## Files modified

| File | Change |
|------|--------|
| `Scalp-Engine/auto_trader_core.py` | `from collections import defaultdict`; `_cleanup_duplicate_positions_and_orders_on_oanda()` added; called at start of `sync_with_oanda()`. |
| `Scalp-Engine/USER_GUIDE.md` | §10(d): paragraph on duplicate (pair, direction) cleanup on OANDA (close/cancel extras each sync; logs). |
| `personal/cursor_works.md` | Quick reference Part 15; this section. |

---

## Verification (for future sessions)

- After sync, OANDA should have at most one open position and one pending order per (pair, direction). If duplicates were present, logs show `🧹 Cleaned up duplicate open position` or `🧹 Cleaned up duplicate pending order`.
- UI shows at most one row per (pair, direction) when engine state is POSTed (one entry per trade_id/order_id; cleanup ensures OANDA has no extras).

---

*Part 15 last updated: Orphan/duplicate cleanup; single (pair, direction) enforced on OANDA and UI.*

---

## Session summary (Parts 14–15 implementation)

| User request | Response |
|--------------|----------|
| 3× GBP/USD on OANDA, only 1 on UI/logs | **Part 14:** Load PENDING trades from state file on engine startup so the full list (one per trade_id/order_id) is restored and POSTed to Config API; UI can show one row per ticket. |
| Clean up orphan trades on OANDA; system must NEVER allow multiple trades of same pair (open or pending) on UI and OANDA | **Part 15:** On every sync, run `_cleanup_duplicate_positions_and_orders_on_oanda()`: close extra open positions and cancel extra pending orders per (pair, direction); keep one (prefer tracked, else oldest). Final gate already blocks placing a second order; cleanup removes any existing duplicates. |

**Commit:** Changes for Parts 14 and 15 (auto_trader_core.py, USER_GUIDE.md, cursor_works.md) committed and pushed in same session as this summary.

---

# Part 16: ATR_TRAILING Immediate Activation Fix (Fix 4) — Mar 6, 2026

## Session flow (what was done this session)

| Step | User request | Action taken |
|------|--------------|--------------|
| 1 | Check cursor_works.md for context for next assignment | Read `personal/cursor_works.md` and `job-alert-resume/cursor_works.md`; user clarified they meant the **personal folder** cursor_works. |
| 2 | Review the cursor_works.md file in the personal folder | Reviewed full structure: Quick reference (Parts 1–15), Log review checks, Part 1 (BackupRenderLogs) through Part 15; summarized table and noted no explicit "next assignment" section. |
| 3 | Check improvementplan.md for Trailing stop updates and recommendations | Summarized improvementplan.md: Phase 0.5 (ATR_TRAILING immediate activation), Phase 0.6 (trailing SL log investigation), Fix 4 (BLOCKED), Fix 5 (BLOCKED); placeholder fix (delay 120s); deployment order; Fix 4 status BLOCKED until Phase 0.5. |
| 4 | Phase 0.5 completed — create detailed plan to fix ATR_TRAILING (no piecemeal); user provided GBP/USD UI screenshot | Created **`Trade-Alerts/Scalp-Engine/ATR_TRAILING_FIX_PLAN.md`**: root cause (first-cycle conversion, single source for "in profit", no stabilization); design (time guard 120s, OANDA P/L gate, keep in_profit check); exact code changes; verification; rollback. Single non-piecemeal plan. |
| 5 | Implement, commit and push changes | Implemented Fix 4 in code and docs; committed both repos; pushed Trade-Alerts (personal has no remote). See "Commits and push" below. |

## Context

Phase 0.5 investigation completed; user confirmed implementation should no longer be gated. ATR_TRAILING was converting to trailing stop **immediately when trade opened** instead of only when in profit (e.g. GBP/USD SELL showing +39.5 pips in UI while chart showed loss; trailing set at entry).

## What was implemented

- **Time-based guard:** In `Scalp-Engine/auto_trader_core.py`, `_check_ai_trailing_conversion()`: for OPEN trades, require `trade.opened_at` and `time_since_open >= ATR_TRAILING_MIN_AGE_SECONDS` (120s). Otherwise skip conversion (DEBUG log).
- **OANDA unrealized P/L gate:** When `trade.oanda_unrealized_pl` is set and ≤ 0, skip conversion (DEBUG log). Conversion only when OANDA shows positive unrealized P/L or value unavailable.
- **Constant:** `ATR_TRAILING_MIN_AGE_SECONDS = 120` added next to `MIN_PROFIT_PIPS_FOR_TRAILING`.
- **Docs:** `Trade-Alerts/improvementplan.md` — Fix 4 status set to implemented; changelog and Fix 4 section updated. `Scalp-Engine/ATR_TRAILING_FIX_PLAN.md` — detailed plan (already created in same session).

## Files modified

| File | Change |
|------|--------|
| `Trade-Alerts/Scalp-Engine/auto_trader_core.py` | `ATR_TRAILING_MIN_AGE_SECONDS`; time guard and OANDA P/L gate in `_check_ai_trailing_conversion()` OPEN branch. |
| `Trade-Alerts/improvementplan.md` | Fix 4 implemented; status, Fix 4 section, Files to Modify table, Changelog. |
| `Trade-Alerts/Scalp-Engine/ATR_TRAILING_FIX_PLAN.md` | Created earlier in session (detailed plan). |
| `personal/cursor_works.md` | Quick reference Part 16; this section (including session flow and commit/push notes). |

## Commits and push

| Repo | Branch | Commit | Message | Push |
|------|--------|--------|---------|------|
| **Trade-Alerts** | `main` | `84d71b0` | Scalp-Engine: Fix 4 ATR_TRAILING - min age 120s + OANDA P/L gate to prevent immediate activation | Pushed to `origin/main` (https://github.com/ibenwandu/Trade-Alerts) |
| **personal** | `master` | `7111a91` | cursor_works: Part 16 ATR_TRAILING Fix 4 (Phase 0.5 complete, min age + OANDA P/L gate) | Not pushed — no `git remote` configured for personal folder |

## Verification (for future sessions)

- New ATR_TRAILING trades should not show “(TRAILING)” in UI until open ≥2 minutes **and** actually in profit (and OANDA unrealized P/L > 0 when available). Logs: DEBUG “skipping … open Ns < min 120s” or “OANDA unrealized P/L … not positive” in first minutes; then “ATR Trailing: attempting conversion” and “converted to trailing stop” when conditions met.

## References for future sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **ATR_TRAILING_FIX_PLAN.md** | `Trade-Alerts/Scalp-Engine/ATR_TRAILING_FIX_PLAN.md` | Full fix plan: root cause, design, code changes, verification, rollback. |
| **improvementplan.md** | `Trade-Alerts/improvementplan.md` | Fix 4 status (implemented); Phase 0.5/0.6; deployment order; changelog. |
| **Log review checks** | Top of this file (cursor_works.md) | Max trades, trailing, duplicate, UI/OANDA, etc. |

---

*Part 16 last updated: Session flow, implementation, commits/push, and references documented for future context.*

---

# Part 17: No Pending Order for Pair with Open Position — Mar 6, 2026

## Goal

Enforce the rule: **once a pair has an open position, there must never be a pending order for that same pair until the open is closed or cancelled.** So at any time a pair may have either (a) at most one open position and no pending, or (b) no open and at most one pending per (pair, direction).

## What was implemented

### 1. New helper: `has_open_position_for_pair(pair)`

- **File:** `Scalp-Engine/auto_trader_core.py` (PositionManager)
- **Behaviour:** Returns `True` if there is any **open** position (state OPEN, TRAILING, or AT_BREAKEVEN) for that pair, **any direction**. Checks in-memory `active_trades` and OANDA `get_open_positions()`.
- **Use:** Decides whether placing a pending order for that pair is allowed.

### 2. Block placing a pending order when the pair has an open

- **File:** `Scalp-Engine/auto_trader_core.py`, in `PositionManager.open_trade()`
- **When:** After creating the managed trade and before adding the placeholder, when `directive.order_type` is `LIMIT` or `STOP` (i.e. we are placing a **pending** order).
- **Check:** If `has_open_position_for_pair(pair)` is True → do not add placeholder, do not send order; set `_last_reject_reason = "open_exists_no_pending"`; log at ERROR and return `None`.
- **Log message:** `🚫 BLOCKED: {pair} already has an open position. No pending order allowed until that position is closed or cancelled.`

### 3. Cleanup: cancel pending orders for pairs that have an open

- **File:** `Scalp-Engine/auto_trader_core.py`, in `_cleanup_duplicate_positions_and_orders_on_oanda()`
- **After:** Closing duplicate open positions per (pair, direction).
- **Step:** Build set `pairs_with_open` = { pair_norm for each (pair_norm, direction) in open_by_key }. For each **pending** order, if its pair is in `pairs_with_open`, **cancel** that order and remove from `active_trades` if present.
- **Log message:** `🧹 Cleaned up pending order: {pair_norm} (cancelled order_id=…) - pair has open position, no pending allowed`
- **Docstring:** Cleanup docstring updated to state that we also enforce “no pending for a pair that has an open” and cancel any such pending.

### 4. USER_GUIDE §10(d)

- **File:** `Scalp-Engine/USER_GUIDE.md`
- **Change:** In the “Duplicate (pair, direction) cleanup on OANDA” paragraph: added the rule “Once a pair has an open position, no pending order is allowed for that pair until the open is closed or cancelled”; described cleanup step (2) “cancels any pending order for a pair that has an open position”; noted that no pair may have both an open and a pending; documented the block log and the new cleanup log.

## Files modified

| File | Change |
|------|--------|
| `Trade-Alerts/Scalp-Engine/auto_trader_core.py` | `has_open_position_for_pair()`; in `open_trade()` block pending when pair has open (LIMIT/STOP); in `_cleanup_duplicate_positions_and_orders_on_oanda()` cancel pending for pairs with open; updated cleanup docstring. |
| `Trade-Alerts/Scalp-Engine/USER_GUIDE.md` | §10(d): rule “no pending when pair has open”, cleanup step (2), block and cleanup log messages. |

## Part 17 hardening (Mar 6, 2026) — commit 560a98c

Three additional layers so OANDA never shows open + pending for the same pair:

1. **Final gate (auto_trader_core.py):** Before sending a LIMIT/STOP order to OANDA, block if **any** open position exists for that pair (any direction). Log: `🚫 BLOCKED (final check): {pair} already has an open position on OANDA. No pending order allowed until it is closed or cancelled.`
2. **Replace-pending path (scalp_engine.py):** In `_review_and_replace_pending_trades`, after cancelling the old order, if `has_open_position_for_pair(pair)` then do **not** place the replacement pending; log and skip. Log: `🔄 Skipping replace for {pair} {direction}: pair has an open position. No pending allowed until it is closed or cancelled.`
3. **Early skip in main loop (scalp_engine.py):** After cooldown check, if `has_open_position_for_pair(pair)` then skip the opportunity (continue) with DEBUG log so we never attempt open or pending for that pair in the same cycle.

## Commit and push

| Repo | Branch | Commit | Message | Push |
|------|--------|--------|---------|------|
| **Trade-Alerts** | `main` | `8dc6d3d` | Scalp-Engine: no pending order for pair with open position - block on place, cancel on sync | Pushed to `origin/main` (https://github.com/ibenwandu/Trade-Alerts) |
| **Trade-Alerts** | `main` | `560a98c` | Harden no-pending-when-open: final gate, replace-pending check, early skip in loop | Pushed to `origin/main` |

## Verification (for future sessions)

- **Place path:** Attempting to place a LIMIT or STOP order for a pair that already has an open position is blocked; logs show `BLOCKED: {pair} already has an open position. No pending order allowed until that position is closed or cancelled.`
- **Sync path:** On each sync, any pending order whose pair has an open position is cancelled; logs show `🧹 Cleaned up pending order: {pair} (pair has open position, no pending allowed)` when such orders exist.
- **Result:** No pair ever has both an open position and a pending order; existing duplicate checks (one per (pair, direction), final gate) unchanged.

## References for future sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **USER_GUIDE.md** | `Trade-Alerts/Scalp-Engine/USER_GUIDE.md` | §10(d) duplicate cleanup and “no pending when pair has open” rule. |
| **Log review checks** | Top of this file (cursor_works.md) | Duplicate, no-pending-when-open. |

---

*Part 17 last updated: No pending when pair has open; implementation (8dc6d3d), hardening final gate/replace-pending/early skip (560a98c), cursor_works updated.*

---

# Part 18: Research Implementation (Phases 0–3) — Mar 6, 2026

## Goal

Implement the outstanding items from `personal/research/` and `personal/OUTSTANDING_IMPLEMENTATION_PLAN.md`: Phase 0 (docs), Phase 1 (risk and position sizing), Phase 2 (trailing and breakeven), Phase 3 (exit strategy), without changing consensus formula, `open_trade()` signature, or adding config keys to TradeConfig without stripping.

## Interactions

- User requested implementation of all phases from the research-based improvement plan.
- Implementation was done in one session: Phase 0 (docs only), then Phase 1 (risk/sizing), Phase 2 (BE/trailing), Phase 3 (ATR TP, half-and-run, max hold, safety note).

## Fixes and features applied

### Phase 0 (docs)

- **USER_GUIDE.md:** Added "Target Exit Behaviour (Research)" (first TP 1.5× risk, runner ATR×1.0, BE +50 pips, trail activation +100 pips); "Research Documentation (Index)" with links to `personal/research/` (Exit Strategy, Trailing SL, Position Sizing, Sources) and improvement/outstanding plans; "Safety: Manual Close of Winners (Phase 3.4)" note.

### Phase 1 (risk and position sizing)

- **TradeConfig (auto_trader_core.py):** Added `max_daily_loss_pct`, `trading_phase`, `risk_percent_per_trade`, `account_balance_override`, `consecutive_losses_max`.
- **Config stripping (scalp_engine.py):** When loading config from API or file, only keys that are `TradeConfig` fields are passed to `TradeConfig(**data)` (using `dataclasses.fields(TradeConfig)`).
- **Position size from formula:** `_position_units_from_risk(account_balance, risk_pct, sl_pips, pair)` with formula `(Account × Risk%) / (SL pips × pip value)`. In `_create_trade_from_opportunity`, units use this when balance (config or OANDA) and SL pips are available; else fallback to `base_position_size × consensus_multiplier`.
- **Daily loss 2%:** `RiskController.can_take_loss(potential_loss, account_balance=None)` enforces `max_daily_loss_pct` when account_balance is provided. `can_open_new_trade()` blocks when daily loss already ≥ that % (balance from config or OANDA).
- **Circuit breaker (5 consecutive losses):** `RiskController.consecutive_losses` updated in `record_trade_close` (increment on loss, reset on win); `circuit_breaker_ok()` blocks when `consecutive_losses >= consecutive_losses_max`; `can_open_new_trade()` calls it.

### Phase 2 (trailing and breakeven)

- **TradeConfig:** `be_min_pips` (default 50), `trailing_activation_min_pips` (default 100).
- **Breakeven:** `_check_be_transition` moves SL to breakeven only when profit ≥ `be_min_pips`.
- **Trailing activation:** BE→trailing and ATR trailing use `trailing_activation_min_pips` when set (default 100); else existing 1 pip minimum.
- **Verification logging:** DEBUG log when ATR trailing is verified and distance unchanged ("Trailing SL verified for … [verification]").

### Phase 3 (exit strategy)

- **TradeConfig:** `half_and_run_enabled`, `half_and_run_r_multiple` (default 1.5), `max_hold_seconds`.
- **ATR-based TP (3.1):** In `_create_trade_from_opportunity`, take profit taken from `take_profit_atr` or `tp_atr` when present.
- **Half-and-run (3.2):** In `monitor_positions`, when `half_and_run_enabled` and trade OPEN and not STRUCTURE_ATR_STAGED, at ≥ `half_and_run_r_multiple` R close 50% via `close_trade_partial`, set `partial_profit_taken`.
- **Max hold (3.3):** If `max_hold_seconds` set, close trade when hold time exceeds it.
- **Safety (3.4):** USER_GUIDE note only (manual close of winners).

### Config API

- **config_api_server.py:** Default config extended with new keys (`be_min_pips`, `trailing_activation_min_pips`, `max_daily_loss_pct`, `trading_phase`, `risk_percent_per_trade`, `account_balance_override`, `consecutive_losses_max`, `half_and_run_enabled`, `half_and_run_r_multiple`, `max_hold_seconds`).

## Files modified

| File | Changes |
|------|--------|
| `Trade-Alerts/Scalp-Engine/USER_GUIDE.md` | Target exit (research), research index, safety note. |
| `Trade-Alerts/Scalp-Engine/auto_trader_core.py` | TradeConfig new fields; `_position_units_from_risk`; risk-based units in `_create_trade_from_opportunity`; `RiskController` daily % and circuit breaker; `can_open_new_trade` circuit breaker and daily % check; BE/trailing configurable thresholds; trailing verification log; Phase 3 (ATR TP, half-and-run, max hold). |
| `Trade-Alerts/Scalp-Engine/scalp_engine.py` | Config strip to TradeConfig fields only when loading from API or file. |
| `Trade-Alerts/Scalp-Engine/config_api_server.py` | Default config includes new Part 18 keys. |

## Commit and push

| Repo | Branch | Commit | Message | Push |
|------|--------|--------|---------|------|
| **Trade-Alerts** | `main` | `aadbddb` | Research implementation: Phase 0-3 (docs, risk/sizing, trailing/BE, exit strategy) | Pushed to `origin/main` |

## Verification (for future sessions)

- **Position size:** When account balance and SL pips available, units follow formula; logs can show risk-based size.
- **Daily loss %:** Set `max_daily_loss_pct` (e.g. 2.0); after daily loss ≥ 2% of account, new opens blocked; log "Daily loss limit reached".
- **Circuit breaker:** After 5 consecutive losses (from `record_trade_close`), new opens blocked; log "Circuit breaker: 5 consecutive losses"; resets on win or daily reset.
- **BE/trailing:** `be_min_pips` (default 50) and `trailing_activation_min_pips` (default 100) control when SL moves to BE and when trailing activates.
- **Half-and-run:** With `half_and_run_enabled=True`, at 1.5R (configurable) 50% of position closed; log "Half-and-run: closed 50% of … at +1.5R".

## References for future sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **OUTSTANDING_IMPLEMENTATION_PLAN.md** | `personal/OUTSTANDING_IMPLEMENTATION_PLAN.md` | Step-by-step outstanding items (Phases 0–3). |
| **TRADING_SYSTEM_IMPROVEMENT_PLAN.md** | `personal/TRADING_SYSTEM_IMPROVEMENT_PLAN.md` | Phased plan from research. |
| **USER_GUIDE.md** | `Trade-Alerts/Scalp-Engine/USER_GUIDE.md` | Target exit, research index, safety. |
| **Log review checks** | Top of this file (cursor_works.md) | Circuit breaker, daily loss %, risk-based size. |

---

*Part 18 last updated: Research implementation Phases 0–3; commit aadbddb; cursor_works updated.*

---

# Part 19: ATR_Trailing Conversion Fix — Mar 6, 2026

## Goal

Fix ATR_Trailing converting too early (2 min after open with 1 pip profit), which placed the trailing stop so close to entry that any retrace stopped the trade out. Ensure conversion only after meaningful profit and that the initial trailing stop is never below entry.

## Problem

- All ATR_Trailing trades were converting 2 minutes after open; the trailing stop started very close to entry (effective cushion small).
- When price moved away from entry, trailing looked fine; when price retraced toward entry, the SL cushion had shrunk and trades were stopped out.
- Cause: conversion was allowed at 1 pip profit (fallback when `trailing_activation_min_pips` missing/zero) and no requirement that profit be at least the trailing distance, so the first stop could be below entry.

## Fixes applied

1. **Default 100 pips when config missing:** In `_check_ai_trailing_conversion`, if `trailing_activation_min_pips` is None or ≤ 0, use 100.0 so we never convert on 1 pip.
2. **Profit >= trailing distance:** Require profit (pips) >= **max(trailing_activation_min_pips, trailing_distance_pips)** before converting. That way the initial trailing stop (current_price − distance) is at or above entry; no tiny cushion on retrace.
3. **Single threshold:** Compute `trailing_pips` and regime once at top of the check; use `min_pips_for_conversion = max(trail_activation_config, trailing_pips)` so one consistent condition.
4. **USER_GUIDE:** Updated trailing-SL description to state ATR_Trailing requires profit >= max(activation, trailing distance) and default 100 pips when config missing.

## Files modified

| File | Change |
|------|--------|
| `Trade-Alerts/Scalp-Engine/auto_trader_core.py` | `_check_ai_trailing_conversion`: default activation 100 pips; require profit >= max(activation, trailing_pips); docstring and log updated. |
| `Trade-Alerts/Scalp-Engine/USER_GUIDE.md` | Trailing SL / ATR_Trailing paragraph: activation rule and "profit >= … (activation/distance)" log. |

## Commit and push

| Repo | Branch | Commit | Message | Push |
|------|--------|--------|---------|------|
| **Trade-Alerts** | `main` | `4d2330b` | ATR_Trailing: convert only after meaningful profit, stop never below entry (default 100 pips, profit >= trailing distance) | Pushed to `origin/main` |

## Verification (for future sessions)

- ATR_Trailing conversion only when trade is in profit by at least max(100 or config, trailing distance in pips); min age and OANDA P/L > 0 unchanged.
- Log shows "ATR Trailing: attempting conversion ... profit >= X.X pips (activation/distance), trailing distance=Y.Y pips" when conversion is attempted.
- Initial trailing stop level is at or above entry (for a long), so retraces don’t wipe out the cushion immediately.

## References

| Document | Location |
|----------|----------|
| **USER_GUIDE.md** | `Trade-Alerts/Scalp-Engine/USER_GUIDE.md` — Trailing SL / ATR_Trailing. |
| **Log review checks** | Top of this file — ATR_Trailing conversion (Part 19). |

---

*Part 19 last updated: ATR_Trailing conversion fix; commit 4d2330b; cursor_works updated.*

---

# Part 20: Glassdoor-jobs (Mar 9, 2026)

**Purpose:** Context for the Glassdoor-jobs project under `personal/Glassdoor-jobs` (and variant `Glassdoor-jobs-cs`). Single cursor_works is `personal/cursor_works.md`; project-specific cursor_works files were merged here.

## Project overview

**Goal:** Replicate the **Linkedin-jobs** (and Indeed-jobs) pipeline for **Glassdoor**: fetch job URLs from Glassdoor search → scrape job pages → score with AI → report → user approves → tailored resumes (.md + .pdf) and job_links.md. Same config shape: scoring-criteria, profile, master-resume, approved_jobs, resume-pdf-template.

**Entrypoints:**
- **`main.py`** – Glassdoor search (config/glassdoor_search.json) → scrape → write markdown to output/ (no scoring).
- **`run_workflow.py`** – Full workflow: `fetch` → `score` → `report` → `resumes` (phases: fetch, score, report, resumes, pdf, all).

**Related:** **Glassdoor-jobs-cs** is the same codebase with Customer Success / CX / BD config (different keywords and scoring-criteria); both live under `personal/`.

## What was built

| Component | Location | Notes |
|-----------|----------|--------|
| Config | `Glassdoor-jobs/src/config.py` | Paths, env; `load_glassdoor_search_config()` from `config/glassdoor_search.json`. |
| Search | `Glassdoor-jobs/src/glassdoor_search.py` | Build direct search URL (`jobs.htm?typedKeyword=...&locKeyword=...`); use glassdoor.ca when base is .com; path-style fallback if redirected to index. Collect only URLs with **job-listing** or **JV_** (no category pages). |
| Scraper | `Glassdoor-jobs/src/glassdoor_scraper.py` | `JobDetails`; Playwright + stealth context; selectors for title, company, location, salary, job_type, description, skills. **Blocked-page detection:** Cloudflare, "Help Us Protect Glassdoor", auth; 6s initial wait, 12s re-check if Cloudflare detected. |
| Link extractor | `Glassdoor-jobs/src/link_extractor.py` | `job_key_from_url()` for Glassdoor (JV_ or path slug); supports .com and .ca. |
| Rest | Same as Linkedin-jobs | browser_context, job_cache, resume_output, ai_client, gemini_client, gemini_scorer, report_generator, profile_loader, resume_tailor, md_to_pdf. |

**Config files:** `config/glassdoor_search.json` (keywords, locations, job_types, max_jobs_total), scoring-criteria, profile, master-resume, approved_jobs, resume-pdf-template, cover-letter-template.

## Session context (what we did)

1. **Replicated Linkedin-jobs for Glassdoor** – New project `personal/Glassdoor-jobs` and variant `Glassdoor-jobs-cs`; job source = Glassdoor search instead of LinkedIn.
2. **Initial search:** Form-based search (index page + fill keyword/location) – form never submitted; page stayed on index.htm.
3. **Direct URL:** Switched to navigating to `jobs.htm?typedKeyword=...&locKeyword=...` and using glassdoor.ca; path-style fallback if redirected to index.
4. **page.url() error:** Fixed to `page.url` (property in Playwright Python).
5. **"Not real job URLs":** Some output files were category pages or Cloudflare pages. **Fixes:** (a) Only collect URLs containing **job-listing** or **JV_** in glassdoor_search. (b) Detect list/category pages in scraper; mark as `[Blocked: not a job page]`. (c) In resume_output skip URLs with jobs-srch and titles like "Help Us Protect".
6. **"Help Us Protect Glassdoor" files:** Cloudflare verification page was scraped as if it were a job (title "Help Us Protect Glassdoor"). **Fixes:** (a) BLOCKED_PAGE_MARKERS and BLOCKED_TITLE_MARKERS extended with "help us protect", "cloudflare", "ray id", "just a moment", etc. (b) Set `job.title = "[Blocked: Cloudflare]"` when detected; is_blocked_job and _is_blocked skip these so no file is written. (c) Increased delay between job pages (5s + 3s jitter).
7. **All 5 jobs skipped:** Fetch finds 5 job URLs but every job page hits Cloudflare/verification; all are marked blocked, so "Skipped 5 job(s) (auth/timeout)" and no output files. **Tried:** (a) Longer initial wait (6s) and 12s re-check when Cloudflare detected. (b) User runs without --headless (visible browser). Still no success.

## Current blocker (where we stopped)

- **Symptom:** `python run_workflow.py --phase fetch --max-jobs 5` reports "Found 5 job URL(s)", then "Skipped 5 job(s) (auth/timeout). No jobs could be scraped."
- **Cause:** Every job detail URL loads the **Cloudflare "Help Us Protect Glassdoor"** verification page instead of the real job content. The scraper correctly detects this and marks the job as blocked, so no files are written and no jobs are cached.
- **What's working:** Search step finds real job-listing URLs (job-listing/... or JV_...). Only the **per-job page visit** is blocked by Glassdoor's protection.

## Next steps (for a future session)

1. **Reduce Cloudflare triggers (optional):** Try Playwright's `playwright-stealth` or a persistent browser profile (user data dir); or `--max-jobs 2` with longer delay (e.g. 10s + 5s jitter).
2. **Allow manual verification:** When running with visible browser, wait for a selector that appears on the real job page (e.g. `[data-test='job-title']`) with a long timeout (e.g. 60s) so the user can complete the Cloudflare challenge; then scrape.
3. **Alternative source:** If Glassdoor remains unusable, document and rely on Linkedin-jobs / Indeed-jobs, or add scrape-only mode from a URL list file (user pastes job URLs from a browser where they're already verified).

## Commands (Glassdoor-jobs)

```bash
cd personal/Glassdoor-jobs
python run_workflow.py --phase fetch --max-jobs 5
python run_workflow.py --phase all
python run_workflow.py --phase resumes   # after adding Job IDs to config/approved_jobs.txt
python run_workflow.py --phase fetch --max-jobs 5 --debug
```

## File layout (Glassdoor-jobs)

```
personal/Glassdoor-jobs/
├── main.py
├── run_workflow.py
├── README.md
├── requirements.txt
├── config/ (glassdoor_search.json, scoring-criteria, profile, master-resume, approved_jobs, resume-pdf-template, cover-letter-template)
├── output/
├── reports/
└── src/ (config, glassdoor_search, glassdoor_scraper, link_extractor, browser_context, job_cache, resume_output, ai_client, gemini_client, gemini_scorer, report_generator, profile_loader, resume_tailor, md_to_pdf)
```

---

*Part 20 last updated: Glassdoor-jobs content merged into personal/cursor_works.md; project cursor_works removed.*

---

# Part 21: job-alert-resume (Gmail → Indeed pipeline)

**Purpose:** Context for **`personal/job-alert-resume`**: Gmail → Indeed job alerts → scrape → score with AI → report → tailored resumes. Single cursor_works is `personal/cursor_works.md`; project cursor_works merged here.

## Project overview

**Goal:** Automate reading Indeed job alerts from Gmail, open each job link, extract job details, **score jobs against a candidate profile with Gemini AI**, generate actionable reports (e.g. top 10 matches), and produce **customized resumes** for user-approved jobs using a master resume template.

**Two entrypoints:**
- **`main.py`** – Gmail → extract links → scrape → write markdown (no scoring).
- **`run_workflow.py`** – Full workflow: fetch → **score with Gemini** (using `config/scoring-criteria.json`) → **report** → user approves via **`config/approved_jobs.txt`** → **tailored resumes** (.md + .pdf using **`config/resume-pdf-template.html`**) and **`job_links.md`** in `output/resumes/`. Can be **scheduled twice daily (7 AM and 7 PM EST)** via `run_workflow_scheduled.bat` and Windows Task Scheduler (see `schedule_setup.md`).

## Session context (what we did)

1. **Initial build** – User described receiving Indeed job alerts in Gmail (Primary and Updates), opening each alert to view job descriptions for resume customization. We designed and implemented a full pipeline.
2. **First run** – Gmail auth worked, but "No Indeed job URLs found" when using Gmail; `--skip-gmail --urls-file urls.txt` failed with `FileNotFoundError` because `urls.txt` did not exist.
3. **Fixes for URLs and debugging:** urls_file resolve from project root; clear error if file missing; support `#` comments; sample `urls.txt`; **--debug** for per-email body length and Indeed URL count.
4. **Gmail still 0 URLs** – Indeed emails use **tracking/redirect links** (e.g. `indeed.com/rc/clk?jk=...`) and **Gmail link wrapping** (`google.com/url?q=...`), not direct `viewjob?jk=...`.
5. **Link extractor fixes:** Support **any Indeed URL with `jk=`**; extract `jk`, emit canonical viewjob URL; **unwrap Gmail redirects** (`google.com/url?q=...`).
6. **Full automated workflow:** config/ (scoring-criteria, profile, approved_jobs), Gemini, job cache, report_generator, resume_tailor, run_workflow phases, schedule 7 AM/7 PM EST.
7. **Gemini import error:** Fallback to legacy `google.generativeai` in `gemini_client.py`; requirements include both SDKs.
8. **API key:** User reuses Google API key from Trade-Alerts; `.env` with `GOOGLE_API_KEY`; no code change.
9. **Task Scheduler password error:** Recommend **"Run only when user is logged on"** in schedule_setup.md so no password required.
10. **Task and sleep:** Scheduled tasks run only when Windows is awake; optional "Wake the computer to run this task."
11. **Next steps:** Documented: .env (GEMINI_API_KEY), run `--phase all`, review report, add IDs to approved_jobs.txt, run `--phase resumes`.
12. **Gemini 404 / OpenAI option:** Default model `gemini-1.5-flash`; read `GEMINI_MODEL` from env; **OpenAI support** via `JAR_AI_PROVIDER=openai` and `OPENAI_API_KEY`; `ai_client.py`; gemini_scorer and resume_tailor use ai_client.
13. **Job application links:** `_write_job_links_file()` in resume_tailor → `output/resumes/job_links.md` (table + plain URLs).
14. **Resume .md → .pdf:** `config/resume-pdf-template.html`, `src/md_to_pdf.py` (strip fence, MD→HTML, template, Playwright PDF); `--phase pdf`; convert after writing .md in resume phase.
15. **No report when scheduled task ran at 7 AM:** Load `.env` from project root in config.py; `run_workflow_scheduled.bat` appends to **`output/workflow_run.log`**; schedule_setup.md "When no report appears."
16. **Indeed-jobs (related):** New project `personal/Indeed-jobs` — Indeed search as job source; same pipeline; stealth browser, Cloudflare handling, visible default, max-jobs 25.
17. **Linkedin-jobs (related):** New project `personal/Linkedin-jobs` — LinkedIn search as job source; same pipeline; linkedin_search.json; scroll/regex for URLs; block fix (no "join linkedin" in body); description max_len=0, Show more; --debug.

## Implementation summary (job-alert-resume)

| Component | Location | Notes |
|-----------|----------|--------|
| Config | `job-alert-resume/src/config.py` | Gmail query, max messages, paths (credentials.json, token.json, output/), scopes; JAR_AI_PROVIDER, GEMINI_MODEL, OPENAI_MODEL. |
| Gmail | `src/gmail_fetcher.py` | OAuth2 via credentials.json + token.json; list messages by query, fetch body; decode base64. |
| Link extraction | `src/link_extractor.py` | Any Indeed URL with jk=; unwrap google.com/url?q=...; canonical viewjob URLs. |
| Indeed scraper | `src/indeed_scraper.py` | Playwright; selectors for title, company, location, salary, description, skills. |
| Output | `src/resume_output.py` | One .md per job + jobs_combined.md. |
| CLI | `main.py` | Gmail or --urls-file → scrape → output. Args: --gmail-query, --max-emails, --max-jobs, --urls-file, --skip-gmail, --debug, --no-headless, --output-dir. |
| Config | `config/` | scoring-criteria.json, profile.md, master-resume.md, approved_jobs.txt, resume-pdf-template.html. |
| Job cache | `src/job_cache.py` | output/jobs_cache.json. |
| AI | `src/ai_client.py` | generate(), parse_score_and_reasoning(); Gemini or OpenAI. |
| Gemini | `src/gemini_client.py` | New + legacy SDK fallback. |
| Scoring | `src/gemini_scorer.py` | Via ai_client.generate(). |
| Report | `src/report_generator.py` | reports/<run_id>/report.md, top_job_ids.txt. |
| Resume tailor | `src/resume_tailor.py` | approved_jobs.txt → tailored .md + job_links.md + PDF. |
| MD → PDF | `src/md_to_pdf.py` | Template wrap, Playwright PDF. |
| Workflow | `run_workflow.py` | Phases: fetch, score, report, resumes, pdf, all. run_workflow_scheduled.bat, schedule_setup.md. |

## Fixes and where they live

- **urls_file:** main.py – resolve with PROJECT_ROOT; strip # comments; clear error if missing. Sample urls.txt at project root.
- **--debug:** main.py – per-email body_len and indeed_urls.
- **Indeed tracking/redirect:** src/link_extractor.py – jk= extraction, canonical viewjob; Gmail unwrap (parse_qs/unquote).
- **Gemini import:** src/gemini_client.py – try new SDK, fallback legacy.
- **Task Scheduler:** schedule_setup.md – "Run only when user is logged on."
- **Gemini 404:** src/config.py – default gemini-1.5-flash; GEMINI_MODEL from env.
- **OpenAI:** src/ai_client.py; gemini_scorer and resume_tailor use ai_client.
- **job_links.md:** src/resume_tailor.py – _write_job_links_file().
- **Resume .md → .pdf:** config/resume-pdf-template.html, src/md_to_pdf.py; --phase pdf.
- **No report at 7 AM:** src/config.py load_dotenv(PROJECT_ROOT / ".env"); run_workflow_scheduled.bat → output/workflow_run.log.

## Common commands (job-alert-resume)

```bash
cd personal/job-alert-resume
python main.py
python run_workflow.py --phase all
python run_workflow.py --phase resumes   # after adding Job IDs to config/approved_jobs.txt
python run_workflow.py --phase pdf
python main.py --gmail-query "in:updates" --max-emails 10 --max-jobs 10
python main.py --gmail-query "in:updates" --max-emails 10 --debug
python main.py --skip-gmail --urls-file urls.txt
python main.py --no-headless
```

## Troubleshooting

- **"No Indeed job URLs found"** – Run with --debug; check link format / Gmail unwrap.
- **Empty title/description/skills** – Update selectors in src/indeed_scraper.py.
- **urls.txt not found** – Run from job-alert-resume or use absolute path.
- **Gmail auth** – First run opens browser; token.json created; if revoked, delete token.json and re-run.
- **"cannot import name 'genai'"** – pip install google-generativeai; code falls back automatically.
- **"gemini-2.0-flash no longer available"** – Default is gemini-1.5-flash; set GEMINI_MODEL in .env.
- **Task Scheduler "User account restriction"** – Use "Run only when user is logged on."
- **Use ChatGPT** – JAR_AI_PROVIDER=openai, OPENAI_API_KEY in .env; pip install openai.
- **PDF not generated** – Edit config/resume-pdf-template.html; run --phase pdf; pip install markdown.

## File layout (job-alert-resume)

```
personal/job-alert-resume/
├── main.py
├── run_workflow.py
├── run_workflow_scheduled.bat
├── schedule_setup.md
├── credentials.json
├── token.json
├── urls.txt
├── README.md
├── config/ (scoring-criteria.json, profile.md, master-resume.md, resume-pdf-template.html, approved_jobs.txt)
├── output/ (jobs_cache.json, *.md, resumes/, workflow_run.log)
├── reports/
└── src/ (config, ai_client, gemini_client, gmail_fetcher, link_extractor, indeed_scraper, resume_output, job_cache, profile_loader, gemini_scorer, report_generator, resume_tailor, md_to_pdf)
```

## Related projects (reference)

- **Indeed-jobs:** `personal/Indeed-jobs` — Indeed search; indeed_search.json; browser_context; Cloudflare handling; visible default; max-jobs 25.
- **Linkedin-jobs:** `personal/Linkedin-jobs` — LinkedIn search; linkedin_search.json; job ID numeric; scroll/regex; block detection (no "join linkedin" in body); description max_len=0, Show more; --debug.
- **Glassdoor-jobs:** `personal/Glassdoor-jobs` — Part 20; Cloudflare blocking job scrapes (search works, job pages blocked).

---

*Part 21 last updated: job-alert-resume content merged into personal/cursor_works.md; project cursor_works removed.*

---

# Part 22: Scalp-Engine – pnl_pips DB migration fix (Mar 9, 2026)

**Purpose:** Document the fix for `sqlite3.OperationalError: no such column: pnl_pips` appearing in Scalp-Engine logs (Render) during daily learning.

## What was the error?

- **Logs:** Repeated `sqlite3.OperationalError: no such column: pnl_pips` and "Error evaluating signal &lt;id&gt;: no such column: pnl_pips".
- **Traceback:** `daily_learning.py` line 116 → `db.update_outcome_simulated(...)` → `scalping_rl_enhanced.py` line 321 (`UPDATE signals SET ... pnl_pips = ? ...`).
- **When:** During simulated trade evaluation (daily learning); SIMULATED entries for USD/JPY, AUD/USD, etc. then the error.

## Root cause

- The `signals` table in the **enhanced RL DB** is created with `CREATE TABLE IF NOT EXISTS` including a `pnl_pips` column in the current code.
- On Render, the database file already existed from an **older schema** (or from a code path that did not include `pnl_pips`). So `CREATE TABLE IF NOT EXISTS` did nothing, and the table had no `pnl_pips` column.
- In `scalping_rl_enhanced.py`, `_init_db()` has a **migration loop** that adds missing columns from a `new_columns` list. That list included `exit_price`, `bars_held`, `max_favorable_pips`, etc., but **did not include `pnl_pips`**, so existing DBs never got the column.
- When `update_outcome_simulated()` ran, the `UPDATE signals SET pnl_pips = ?` failed with "no such column: pnl_pips".

## Fix implemented

- **File:** `Trade-Alerts/Scalp-Engine/src/scalping_rl_enhanced.py`
- **Change:** In `_init_db()`, added `('pnl_pips', 'REAL')` to the `new_columns` list (with a short comment) so that existing `signals` tables get the column via `ALTER TABLE signals ADD COLUMN pnl_pips REAL` on next init.
- **Commit:** dd47b44 — "Fix sqlite3.OperationalError: add pnl_pips to DB migration in scalping_rl_enhanced" (Trade-Alerts repo, pushed to origin/main).

## Verification

After deploy, when Scalp-Engine (e.g. daily learning) runs, `_init_db()` runs and adds `pnl_pips` if missing. The try/except in the migration loop ignores "column already exists". Errors in logs should stop.

---

*Part 22 last updated: pnl_pips migration fix documented; commit dd47b44.*

---

# Part 23: Manual Logs Analysis + DeepSeek Parser Fix (Mar 11, 2026)

**Purpose:** Review Manual logs (Mar 9-11, 2026) for cross-touchpoint consistency and DeepSeek LLM performance. Fix critical DeepSeek parser failure preventing RL learning.

## Goal of This Session

Review documents in Manual logs (`C:\Users\user\Desktop\Test\Manual logs`) for consistency of logic, business rules, and transactions across 4 touchpoints (Trade-Alerts, Scalp-engine, Scalp-engine UI, Oanda). Focus on DeepSeek LLM performance in generating trading opportunities and improving through RL.

## What Was Done

1. **Manual logs reviewed:** trade-alerts_*.txt, scalp-engine_*.txt, scalp-engine-ui_*.txt, oanda_*.txt, oanda_transactions_*.json (Mar 9-11, 2026)
2. **Analysis document created:** `personal/MANUAL_LOGS_ANALYSIS_2026-03-11.md` — comprehensive findings and recommendations
3. **Plan document created:** `personal/Trade-Alerts/Scalp-Engine/suggestions from cursor7.md` — implementation plan
4. **Backup created:** `personal/backup_before_cursor7_20260311_162509` (robocopy of Trade-Alerts excluding .git and __pycache__)

## Key Findings

### CRITICAL: DeepSeek Parser Failure

- **Evidence:** Every analysis cycle shows `DeepSeek: 0 opportunities parsed`
- **Root cause:** Pattern Set 10 in `recommendation_parser.py` doesn't match DeepSeek's actual output format (narrative structure: `## Forex Trading Analysis & Recommendations`)
- **Impact:** 
  - DeepSeek contributes 0 to consensus (should be 1/4 or more)
  - DeepSeek has 0 evaluated recommendations (needs 5+ for RL learning)
  - DeepSeek weight stuck at default 0.25 (16%) instead of learning from performance

### RL Learning Statistics

- **chatgpt:** 51 evaluated recommendations (total: 72)
- **gemini:** 3787 evaluated recommendations (total: 3877)
- **claude:** 124 evaluated recommendations (total: 137)
- **synthesis:** 7764 evaluated recommendations (total: 7961)
- **deepseek:** 0 evaluated recommendations (total: 0) ⚠️

### Other Issues Found

- Missing trade close audit logs (no "Trade closed" logs found)
- Missing ATR trailing conversion logs (no "Converted to trailing stop" logs)
- Excessive max_trades_limit warnings (20+ repeated warnings)

## Plan Source and Constraints

- **Plan:** `personal/Trade-Alerts/Scalp-Engine/suggestions from cursor7.md`
- **Context:** `personal/MANUAL_LOGS_ANALYSIS_2026-03-11.md`, `personal/cursor_works.md` (Parts 1-22)
- **Explicit "do not do" (from plan):**
  - Do **not** change consensus formula, min_consensus_level, or required_llms logic
  - Do **not** add fields to TradeConfig without stripping before `TradeConfig.__init__`
  - Do **not** change `open_trade()` return signature
  - Implement **one** fix at a time; verify before next

## What Was Implemented

### Priority 1: Fix DeepSeek Parser — COMPLETE ✅

**Implementation:**
- **Step 1.2:** Updated Pattern Set 10 with 3 new DeepSeek patterns:
  - Pattern 10d: DeepSeek narrative pairs with trading keywords
  - Pattern 10e: DeepSeek structured trade sections ("### Trade 1:", etc.)
  - Pattern 10f: Fallback pairs with direction keywords
- **Step 1.3:** Enhanced extraction patterns for DeepSeek-specific entry/exit/stop loss formats
- **Step 1.4:** Updated `_get_deepseek_prompt()` to explicitly request MACHINE_READABLE JSON format with schema example
- **Step 1.5:** Added enhanced logging: logs full DeepSeek response (first 2000 chars) when parser finds 0 matches

**Files Modified:**
- `src/recommendation_parser.py` (Pattern Set 10, extraction patterns, logging)
- `src/llm_analyzer.py` (DeepSeek prompt enhancement)

**Commit:** `fb2d8b1` — "Fix DeepSeek parser (Priority 1 - cursor7)"

### Priority 2: Improve Logging — COMPLETE ✅

**Implementation:**
- **Issue 2.1:** Enhanced trade close audit logs
  - Added DEBUG log when `TradeExecutor.close_trade()` is called
  - Added hourly periodic status log showing open trades with ages and PnL
  - Audit log already exists in `PositionManager.close_trade()`
- **Issue 2.2:** Verified ATR trailing conversion logs (already implemented correctly)
  - INFO log before conversion attempt
  - INFO log on successful conversion
  - WARNING log on conversion failure
- **Issue 2.3:** Throttled max_trades_limit warnings
  - Added 15-minute throttle window
  - First occurrence per (pair, direction): WARNING level
  - Subsequent occurrences: DEBUG level
  - Reduces log spam from 20+ repeated warnings

**Files Modified:**
- `Scalp-Engine/scalp_engine.py` (max_trades_limit throttle + periodic status logging)
- `Scalp-Engine/auto_trader_core.py` (DEBUG log in close_trade)

**Commit:** `83b685b` — "Priority 2: Improve logging (cursor7)"

## Verification Status

**Pending verification before proceeding to Priority 3:**
- [ ] Priority 1: DeepSeek parser extracts at least 1 opportunity per analysis cycle
- [ ] Priority 1: DeepSeek opportunities appear in market state
- [ ] Priority 1: DeepSeek recommendations logged to RL database
- [ ] Priority 2: Reduced max_trades_limit log spam (throttled)
- [ ] Priority 2: Trade close audit logs appear in logs
- [ ] Priority 2: Hourly open trades status logs appear

**Next steps:** After verification confirms Priority 1 & 2 are working, proceed with Priority 3 (RL Monitoring).

## Note for Future Log Reviews

**When reviewing Manual logs (`C:\Users\user\Desktop\Test\Manual logs`), look for confirmation of Priority 1 & 2 fixes:**

**Priority 1 (DeepSeek Parser) - Look for:**
- `DeepSeek: X opportunities parsed` where X > 0 (not "0 opportunities parsed")
- DeepSeek opportunities in market state exports
- DeepSeek recommendations in RL database logs
- Reduced or no "Parser found 0 pattern matches" warnings for DeepSeek
- DeepSeek contributing to consensus (e.g., "deepseek: 1 parsed opportunities" in consensus calculation)

**Priority 2 (Logging) - Look for:**
- `⏭️ Skipped {pair} {direction} - {reason} (throttled)` at DEBUG level (not repeated WARNING)
- `📋 Trade closed: {pair} {direction} exit_reason={reason} final_PnL={final_pnl}` audit logs
- `📊 Open trades status (N open):` hourly logs showing open trades with ages and PnL
- `🔧 close_trade() called: trade_id=...` DEBUG logs when trades close
- Reduced max_trades_limit warnings (first at WARNING, subsequent at DEBUG per 15 min window)

## Files to Modify

1. **`personal/Trade-Alerts/src/recommendation_parser.py`**
   - Pattern Set 10 (lines ~352-374)
   - `_extract_opportunity_from_text` method (entry/exit/stop patterns)

2. **`personal/Trade-Alerts/src/llm_analyzer.py`**
   - `_get_deepseek_prompt()` method (line ~334)

## Verification (for future sessions)

After deploy:
- DeepSeek parser extracts at least 1 opportunity per analysis cycle
- DeepSeek opportunities appear in market state
- DeepSeek recommendations logged to RL database
- DeepSeek evaluated recommendations count increases over time
- DeepSeek weight changes from default 0.25 once 5+ recommendations evaluated

## References for Future Sessions

| Document | Location | Purpose |
|----------|----------|---------|
| **suggestions from cursor7.md** | `Trade-Alerts\Scalp-Engine\suggestions from cursor7.md` | Implementation plan; Priority 1-4 fixes |
| **MANUAL_LOGS_ANALYSIS_2026-03-11.md** | `personal\MANUAL_LOGS_ANALYSIS_2026-03-11.md` | Comprehensive analysis; findings and evidence |
| **Backup (rollback)** | `personal\backup_before_cursor7_20260311_162509` | Full Trade-Alerts copy before cursor7 implementation; restore if needed |
| **CLAUDE.md** | `Trade-Alerts\CLAUDE.md` | Architecture, do-not-do list, Session notes |

---

## Implementation Summary

**Priority 1 (DeepSeek Parser):** ✅ Complete
- Pattern Set 10 enhanced with 3 new DeepSeek patterns (10d, 10e, 10f)
- DeepSeek prompt updated to request MACHINE_READABLE JSON
- DeepSeek-specific extraction patterns added
- Enhanced logging for parser failures
- **Commit:** `fb2d8b1` (Trade-Alerts)

**Priority 2 (Logging):** ✅ Complete
- Trade close audit logs enhanced (DEBUG + periodic status)
- ATR trailing conversion logs verified (already working)
- max_trades_limit warnings throttled (15 min window)
- **Commit:** `83b685b` (Trade-Alerts)

**Priority 3 (RL Monitoring):** ✅ Implemented
- Added explicit RL monitoring logs in `daily_learning.run_daily_learning()`:
  - `LEARNING CYCLE START: Evaluating recommendations and updating LLM weights...`
  - `WEIGHTS UPDATED: {llm}: {old_weight} -> {new_weight}`
  - `LEARNING CYCLE COMPLETE: evaluated={evaluated_count}, total_evaluated={total_evaluated}, overall_win_rate={overall_win_rate}%`
- Extended `RecommendationDatabase` with `get_latest_learning_checkpoint()` to read prior weights
- Extended `learning_checkpoints` to persist `deepseek_weight` and included it in checkpoints

**Priority 4 (Optimization):** ⏸️ Pending
- Low priority; optional improvements

---

*Part 23 last updated: Priorities 1–3 implemented; Priority 1 verified in logs, Priority 2 logging deployed (awaiting more trade-close evidence), ready for future Priority 4 optimization.*

---

# Part 24: Duplicate USD/CHF Instances & Immediate Pending Cancellation After MARKET Open (Mar 13, 2026)

---

## Context

- **User observation:** OANDA UI showed **multiple instances of the same pair** at the same time, specifically:
  - A **USD/CHF open LONG** (88,679 units, FT-DMI-EMA activation, ATR trailing).
  - A **USD/CHF pending LIMIT** (245,888 units).
  - Additional examples with different unit sizes (e.g., 86,294 units AUD/USD, 2,000 units EUR/USD).
- **Business rule:** For every pair, the system must have **only one instance at a time**, meaning:
  - Either **one OPEN position** for the pair (any direction), or
  - **One PENDING order** for the pair,
  - But **never both open and pending** at the same time, and never multiple opens or multiple pendings.
- Sources used:
  - OANDA screenshots (USD/CHF chart + accounts/trades/positions/activity panels).
  - Manual logs: `scalp-engine_2026-03-13_1100.txt`, `oanda_transactions_2026-03-13_*.json`, `trade-alerts_2026-03-12_2100.txt`, etc.
  - Scalp-Engine code: `Scalp-Engine/auto_trader_core.py`, `Scalp-Engine/scalp_engine.py`, `Scalp-Engine/USER_GUIDE.md`.

---

## Analysis – Multiple USD/CHF Instances

### 1. Existing rules in code (before this session)

- **No pending when pair has open:**
  - `PositionManager.has_open_position_for_pair(pair)` checks in-memory `active_trades` and OANDA `get_open_positions()`.
  - `ScalpEngine._check_new_opportunities()` skips any opportunity for pairs where `has_open_position_for_pair(pair)` is `True`:
    - DEBUG log: `"Skipped {pair} {direction} - pair already has an open position (no second open/pending allowed)"`.
  - `PositionManager.open_trade()`:
    - Early gate: if `directive.order_type in ('LIMIT', 'STOP')` and `has_open_position_for_pair(pair)` is `True`, it blocks with:
      - `"🚫 BLOCKED: {pair} already has an open position. No pending order allowed until that position is closed or cancelled."`
    - Final OANDA gate (before sending any order): again checks `get_open_positions()` and blocks placing a pending if any open exists for that pair (any direction).
- **Single (pair, direction) and cleanup at sync:**
  - `_cleanup_duplicate_positions_and_orders_on_oanda()` (called from `sync_with_oanda()`):
    - Groups OANDA open positions by `(pair_norm, direction)` and:
      - **Closes duplicates** (keeping one) for each `(pair, direction)`.
    - Cancels any pending order for a pair that has an open position (no pending allowed while open).
    - Groups pending orders by `(pair_norm, direction)` and cancels duplicates, keeping one.
  - `ScalpEngine._monitor_positions()` and the main loop both call `position_manager.sync_with_oanda(market_state)` so cleanup runs **every check** (about once per minute).

### 2. Root cause – Why open + pending still appeared

- The USD/CHF example came from a **race window**:
  - Timeline (from logs and transactions):
    - Earlier: a USD/CHF **LIMIT** (245,888 units) was placed by the **LLM/consensus** path when no open existed for USD/CHF.
    - Later: **FT-DMI-EMA activation** opened a **MARKET** USD/CHF LONG (88,679 units) when triggers were met:
      - Log: `"FT-DMI-EMA (AUTO) USD/CHF LONG @ 0.788265 - order placed (15m trigger met)"`.
    - Immediately after the market order filled on OANDA, the engine called `sync_with_oanda()` as usual, but if the OANDA API had not yet reflected the new open in `get_open_positions()`, the cleanup routine did **not** see USD/CHF as “pair with open,” so it did **not** cancel the 245,888 pending in that cycle.
  - Effect:
    - For a short period (until the next sync when OANDA clearly reports the new open), the account can show both:
      - An **open** USD/CHF position (88,679 units), and
      - A **pending** USD/CHF order (245,888 units).
    - This violates the business rule, but only within a small timing window between order fill and OANDA’s API reporting the new state.

### 3. Explanation for varying unit sizes

- Units are **intentionally variable** and come from risk-based sizing plus consensus:
  - In `PositionManager._create_trade_from_opportunity()`:
    - Default base: `config.base_position_size` (e.g. 2,000, 5,000, etc.).
    - **Risk-based formula** when balance and SL pips are available:
      - `units ≈ (account_balance × risk_percent_per_trade) / (sl_pips × pip_size)`.
      - Then multiplied by `consensus_multiplier[consensus_level]` (e.g. 0.5, 1.0, 1.5, 2.0).
    - Otherwise: `units = base_position_size × consensus_multiplier`.
- Consequences:
  - FT-DMI-EMA and LLM paths both call `PositionManager.open_trade()`, but with **different entries/SLs/consensus** → different sizes.
  - This explains why USD/CHF has 88,679 units in one trade and 245,888 units in another, and why EUR/USD and AUD/USD show other sizes (2,000; 86,294; etc.). This is **by design**, not a bug.
  - The bug to fix is **not** unit variation, but the **simultaneous open + pending** for the same pair during the race window.

---

## Fix Implemented – Immediate Pending Cancellation After MARKET Open

### Goal

Ensure that **as soon as a MARKET trade successfully opens for a pair**, the engine **immediately cancels any OANDA pending orders for that pair**, closing the race window where open + pending can coexist.

### Changes in `Scalp-Engine/auto_trader_core.py`

**1. New helper: `PositionManager.cancel_all_pending_for_pair`**

- Signature:
  - `def cancel_all_pending_for_pair(self, pair: str, reason: str = "Cleanup: pair has open position - no pending allowed") -> int`
- Behavior:
  - Normalizes the pair via `normalize_pair`.
  - Calls `self.executor.get_pending_orders()` and iterates all pending OANDA orders.
  - For each order where the normalized instrument matches the pair:
    - Calls `self.executor.cancel_order(order_id, reason)`.
    - Removes the order from `active_trades` if present.
    - Increments a `cancelled` counter.
  - Logging:
    - If `cancelled > 0`:
      - INFO: `🧹 Cancelled {cancelled} pending order(s) for {pair} after market open (no pending allowed while pair has open position)`.
    - If `cancelled == 0`:
      - DEBUG: `No pending orders found to cancel for {pair} after market open`.
    - On error:
      - WARNING: `⚠️ Failed to cancel pending orders for {pair} after market open: {e}` (does **not** roll back the already-open MARKET trade).

**2. Hooked into `PositionManager.open_trade()` after successful order placement**

- In the `open_trade()` method, inside the block:
  - `order_or_trade_id = self.executor.open_trade(trade)`
  - `if order_or_trade_id:`
- After removing the `_pending_{opp_id}` placeholder and **before** recording execution and updating `trade.state`:
  - New logic:
    - If `directive.order_type == 'MARKET'`:
      - Call:
        - `self.cancel_all_pending_for_pair(trade.pair, reason="Cleanup after MARKET open: pair has open position - no pending allowed")`
- This ensures:
  - Any existing **LIMIT/STOP** pending orders for the same pair are cancelled **immediately** after the MARKET order is accepted by OANDA.
  - The fix applies uniformly to:
    - LLM-based MARKET opportunities.
    - FT-DMI-EMA activation MARKET orders.
    - Fisher / DMI-EMA / HYBRID MACD-triggered MARKET opens.

### Files touched in Trade-Alerts repo

- `Scalp-Engine/auto_trader_core.py`:
  - Added `cancel_all_pending_for_pair` method on `PositionManager`.
  - Added call in `PositionManager.open_trade()` after successful MARKET opens.
- `Scalp-Engine/suggestions from cursor7.md`:
  - Minor formatting update (newline) so future sessions can append Priority 5+ items if desired.
- `CLAUDE_SESSION_LOG.md`, `improvementplan.md`, `Phase1-Analysis-Report.md`, `market_state.json`:
  - Updated with broader system state and Phase 1 testing context (not directly related to this fix but included in the same commit).

### Commit

- **Repo:** `personal/Trade-Alerts` (GitHub: `ibenwandu/Trade-Alerts`)
- **Branch:** `main`
- **Commit:** `6a450eb` — `Ensure pending orders are cancelled after market opens`
- Pushed to `origin/main`.

---

## Verification Plan for Future Sessions

When reviewing Manual logs for this behavior (see Part 37 “Log review checks”), confirm:

- **After any MARKET open for a pair**, logs show:
  - `✅ AUTO MODE: Created order/trade {id}: {pair} {direction} {units} units @ {entry} (state: OPEN)`
  - Followed (within the same minute) by either:
    - `🧹 Cancelled N pending order(s) for {pair} after market open (no pending allowed while pair has open position)` (N ≥ 1), or
    - `No pending orders found to cancel for {pair} after market open` (DEBUG) if there were none.
- **On OANDA (transactions + UI)**:
  - For any pair with an open position, there are **no pending orders** for that pair immediately after the MARKET open, not just after the next 1-minute sync.
- The existing **sync cleanup** still enforces:
  - At most **one open** per `(pair, direction)`.
  - At most **one pending** per `(pair, direction)`.
  - **No pair** has both an open and a pending simultaneously; the new hook ensures this is true even inside the short timing window after a MARKET order is filled.

---

## References for Future Sessions

- **Code paths:**
  - `Scalp-Engine/auto_trader_core.py`
    - `PositionManager.cancel_all_pending_for_pair()`
    - `PositionManager.open_trade()` (MARKET open path and new cleanup call)
    - `_cleanup_duplicate_positions_and_orders_on_oanda()` and `sync_with_oanda()`.
  - `Scalp-Engine/scalp_engine.py`
    - `_check_new_opportunities()` (duplicate/pending checks).
    - `_monitor_positions()` (per-minute sync + cleanup).
- **Manual logs:**
  - `C:\Users\user\Desktop\Test\Manual logs\scalp-engine_YYYY-MM-DD_HHmm.txt`
  - `oanda_transactions_YYYY-MM-DD_HHmm.json` for verifying USD/CHF and other pairs’ open vs pending states.
- **Prior context:**
  - Part 5 (EUR/USD ATR trailing + duplicate positions analysis).
  - Part 6 (cursor5 implementation – pre-open OANDA checks, add-before-send, and pending-to-open sync).
  - Part 23 (cursor7 DeepSeek parser + logging + RL monitoring).

*Part 24 last updated: Mar 13, 2026 — Duplicate USD/CHF instances analyzed; race window identified; implemented immediate pending cancellation after MARKET open with commit `6a450eb` in Trade-Alerts.*

---

# Part 25: Configurable Required LLMs UI (Mar 13, 2026)

---

## Goal

Restore a safe, configurable **"Required LLMs"** window in the Scalp-Engine UI so operators can choose which LLMs must participate in consensus, **without changing** the consensus formula or `min_consensus_level` semantics. Wrap this in a full Trade-Alerts backup for easy rollback.

---

## Backup Before Changes

- **Backup folder:** `personal\backup_before_required_llms_20260313`  
  (Created via `robocopy` from `personal\Trade-Alerts`, excluding `.git`, `__pycache__`, and similar; used as a rollback point if UI/config changes cause issues.)
- **Scope:** Full Trade-Alerts tree (Scalp-Engine, Trade-Alerts root, src, UI, docs).
- **Usage (if needed):** Stop services → replace current `Trade-Alerts` contents with the backup → restart.

---

## Design and Constraints

- **Do not change:**
  - Consensus **formula** (how `consensus_level` is computed from base LLMs).
  - `min_consensus_level` semantics.
  - `required_llms` **logic** in the engine (already implemented as a simple filter).
  - `TradeConfig` constructor signature or `open_trade()` return type.
- **Allowed/desired:**
  - Expose `required_llms` as a **UI-configurable list**.
  - Save/load `required_llms` alongside existing config (trading_mode, max_open_trades, min_consensus_level, etc.).
  - Keep safe defaults when config or user input is missing.

Engine side (pre-existing behavior, verified before changes):

- `TradeConfig` in `auto_trader_core.py`:
  - Field: `required_llms: List[str] = None`.
  - `__post_init__` ensures a non-empty list:
    - If `required_llms` is `None` or empty: set to `['gemini']` (default: require Gemini).
- Opportunity validation in `PositionManager.risk_controller.validate_opportunity`:
  - Enforces:
    - `consensus_level >= min_consensus_level`.
    - If `required_llms` is a non-empty list and any required LLM is present in `llm_sources`, trade is allowed.
    - If **none** of the required LLMs appear in `llm_sources`, validation fails with:
      - `"None of the required LLMs [...] are in consensus (sources: [...])"`.
- Config load (`scalp_engine.py`):
  - Reads `required_llms` from config API / file when present.
  - Includes logging to show current `required_llms` and warn when only one LLM is required (unusual).

Conclusion: the **engine already had correct required_llms behavior**; what was missing was a robust **UI** for setting it.

---

## Implementation – Scalp-Engine UI (`scalp_ui.py`)

### 1. Rendering the Required LLMs window

Location: `render_auto_trader_controls()` under the `"🎯 Consensus Filters"` section.

Changes:

- Previously this section only rendered:
  - `Minimum Consensus Level` slider, and
  - A static markdown line for “Required LLMs,” with **no controls**.
- New implementation:
  - Determine **available LLMs** and **weights**:
    - Start with default list: `['chatgpt', 'gemini', 'claude', 'deepseek']`.
    - Try `market_state = load_market_state()` and:
      - If `market_state['llm_weights']` is a non-empty dict, use its keys as `available_llms`.
      - Preserve `llm_weights` for display.
  - Determine current required list:
    - `current_required = config.get('required_llms')`.
    - If missing or invalid, default to `['gemini']` (consistent with `TradeConfig.__post_init__`).
  - For each LLM in `available_llms`:
    - Render a checkbox:
      - Label: `"{llm_name} (weight: 0.xx)"` if a numeric weight is available; otherwise just the name.
      - Default checked state: `True` if `llm_name in current_required`.
      - Key: `required_llm_{llm_name}`.
    - Build `required_llms_selection` as the list of LLMs whose checkboxes are checked.

### 2. Saving Required LLMs into config

Location: same function, in the "Save Configuration" button handling.

- When building `new_config`, added:
  - `'required_llms': required_llms_selection if required_llms_selection else ['gemini'],`
- Behavior:
  - If the user selects **one or more** LLMs, that exact list is saved.
  - If the user selects **none**, the config falls back to `['gemini']` rather than saving an empty list (which would disable the filter and break expectations).
- All other fields (`min_consensus_level`, `base_position_size`, `max_open_trades`, etc.) remain unchanged.

### 3. Defaults and safety

- Defaults are now aligned everywhere:
  - UI fallback for missing/empty `required_llms`: `['gemini']`.
  - Engine fallback in `TradeConfig.__post_init__`: `['gemini']`.
- The UI no longer leaves `required_llms` implicit; it always saves a non-empty list, making configuration more transparent and reducing silent drift.

---

## Verification Plan (for Future Sessions)

After deploying these UI changes, use this checklist:

1. **Config round-trip**
   - In Scalp-Engine UI:
     - Set `Required LLMs` to, for example, `chatgpt` and `gemini` only.
     - Save configuration.
   - In Config API or `auto_trader_config.json`, confirm:
     - `"required_llms": ["chatgpt", "gemini"]` is present.
   - Restart Scalp-Engine (if applicable) and look for startup logs:
     - Should show `Required LLMs: chatgpt, gemini` in config summary.

2. **Functional behavior with required LLMs**
   - Scenario A (strict requirement):
     - `min_consensus_level = 2`, `required_llms = ['gemini']`.
     - An opportunity where only `claude` agrees should be **rejected** with a log reason mentioning required LLMs.
   - Scenario B (looser requirement):
     - `required_llms = ['claude']`.
     - An opportunity where `claude` is in `llm_sources` and consensus ≥ min level should now pass (subject to all other checks).

3. **No change to consensus formula**
   - Verify log lines showing consensus as `X/available_llm_count` still behave as before (Part 18 & Part 23).
   - Confirm that only the **filtering** based on `required_llms` has changed, not the underlying consensus math.

4. **Failure/rollback**
   - If behavior regresses (e.g., no trades open due to overly strict required_llms settings):
     - Adjust via UI first (e.g., include more LLMs or reset to defaults).
     - If code-level rollback is needed:
       - Restore `personal\Trade-Alerts` from `backup_before_required_llms_20260313`.

---

## References

- **UI file:** `Scalp-Engine/scalp_ui.py`
  - `render_auto_trader_controls()` → "🎯 Consensus Filters" section → Required LLMs checkboxes.
  - Save handler for "💾 Save Configuration".
- **Engine behavior:**
  - `Scalp-Engine/auto_trader_core.py`
    - `TradeConfig.__post_init__` (default `required_llms`).
    - Opportunity validation function enforcing required_llms.
  - `Scalp-Engine/scalp_engine.py`
    - Config load / logging of `required_llms`.
- **Docs:**
  - `Scalp-Engine/USER_GUIDE.md` sections on consensus, `min_consensus_level`, and `required_llms` (see §5 / §12+).

*Part 25 last updated: Mar 13, 2026 — Added configurable Required LLMs UI (checkboxes per LLM, persisted to config), wired to existing engine required_llms behavior, and took backup `backup_before_required_llms_20260313` for rollback.*

---

## Next Steps Reminder (Future Session)

- After enough new Manual logs accumulate **post-commit** `fb2d8b1` (DeepSeek parser fix) and the later UI/config changes, explicitly verify that **DeepSeek is still contributing parsed opportunities and RL data**:
  - In `trade-alerts_*.txt`: look for `Parsed DEEPSEEK: X opportunities` and `DeepSeek: X opportunities parsed` with **X > 0** (not stuck at 0).
  - In `market-state-api_*.txt` and `scalp-engine_*.txt`: confirm DeepSeek appears in `llm_sources` and consensus debug logs (`base_llm_sources` includes `deepseek` for at least some pairs).
  - In RL / learning logs: confirm DeepSeek’s evaluated recommendation count and weight are increasing over time (no regression to 0 opportunities / default weight).
- If any regression is detected (DeepSeek back to 0 parsed opportunities), compare current `src/recommendation_parser.py` Pattern Set 10 and `_get_deepseek_prompt()` in `src/llm_analyzer.py` against the versions from commit `fb2d8b1` and use existing backups (`backup_before_cursor7_20260311_162509`, `backup_before_required_llms_20260313`) for targeted rollback.
