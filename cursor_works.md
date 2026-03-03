# Cursor Works – Session Notes (Personal Folder)

This file records interactions, plans, and fixes implemented across projects under the personal folder so future sessions have context. Sections: **BackupRenderLogs** (Render/Oanda log backup), **Scalp-Engine / Trade-Alerts** (suggestions from cursor3 implementation), **Cursor4 / consol-recommend4** (Manual logs review, consolidated plan v4), and **consol-recommend4 Implementation** (Mar 2, 2026 — phases 1.1, 1.4, 2.1, 2.2–2.6, 2.3, 3.1, 3.x docs).

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
