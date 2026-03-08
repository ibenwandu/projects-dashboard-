# Complete Fix Plan: Trade-Alerts & Scalp-Engine

**Purpose:** Single, thorough plan to fix the entire codebase—no piecemeal changes.  
**Scope:** Trade-Alerts repo (including nested Scalp-Engine), market state flow, entry points, duplicates, and operational reliability.

---

## 1. Architecture and Data Flow (Current)

### 1.1 Services (per render.yaml)

| Service            | Type  | Start command                          | Disk        | Role |
|--------------------|-------|----------------------------------------|-------------|------|
| trade-alerts       | worker| `python main.py`                       | /var/data   | Run analysis; export market state (Step 9); optional POST to API |
| scalp-engine       | worker| `cd Scalp-Engine && python scalp_engine.py` | /var/data | Read state; execute trades; POST Fisher/FT-DMI-EMA to API |
| market-state-api   | web   | `cd Scalp-Engine && python market_state_server.py` | /var/data | POST /market-state, GET /market-state, POST /fisher-opportunities, POST /ft-dmi-ema-opportunities |
| config-api         | web   | `cd Scalp-Engine && python config_api_server.py`    | /var/data   | Serve auto_trader_config.json |
| scalp-engine-ui    | web   | `cd Scalp-Engine && streamlit run scalp_ui.py ...`   | /var/data   | Dashboard; load state via API or file |

### 1.2 Market state flow

- **Write:** Trade-Alerts `main.py` Step 9 → `MarketBridge.export_market_state()` → writes to `MARKET_STATE_FILE_PATH` (e.g. `/var/data/market_state.json`) and optionally `_send_to_api(state)` POST to `MARKET_STATE_API_URL`.
- **Read:** Scalp-Engine UI/engine use `MarketStateReader.load_state()`: try API (GET `MARKET_STATE_API_URL`) first, then file at `MARKET_STATE_FILE_PATH`. market-state-api serves GET from same file it writes on POST.
- **Fisher / FT-DMI-EMA:** Scans (`run_fisher_scan.py`, `run_ft_dmi_ema_scan.py`) POST to market-state-api when `MARKET_STATE_API_URL` is set; else write/merge to file.

### 1.3 Key env vars

- `MARKET_STATE_FILE_PATH`: default `/var/data/market_state.json` (all services that touch state).
- `MARKET_STATE_API_URL`: e.g. `https://market-state-api.onrender.com/market-state` (Trade-Alerts POST; Scalp-Engine/UI GET and Fisher/FT-DMI-EMA POST use same base with different paths in fisher_market_bridge).

---

## 2. Issues Identified (Full Review)

### 2.1 Duplicate / legacy entry points

| Location | Issue | Impact |
|----------|--------|--------|
| **Trade-Alerts/run_analysis_now.py** | Old analysis flow: Drive → LLMs → Synthesis → Email only. **Does not call Step 9 or MarketBridge.** | If someone runs this instead of the full workflow, market state is never updated → UI shows stale forever. |
| **Trade-Alerts/run_immediate_analysis.py** | Calls `TradeAlertSystem._run_full_analysis_with_rl()` (includes Step 9). OK. | None. |
| **Trade-Alerts/run_full_analysis.py** | Same as run_immediate_analysis (full workflow). OK. | Two scripts do the same thing; redundant. |
| **Scalp-Engine/src/run_fisher_scan.py** | Legacy Fisher scan: no reversal strategy, no `post_fisher_to_api`, different imports (for cwd=src). | Confusion; wrong entry point used from scripts or docs. |
| **Scalp-Engine/run_fisher_scan.py** (root) | Current, full: reversal + API POST + disk fallback. | **Canonical** entry. |
| **Scalp-Engine/Scalp-Engine/scalp_engine.py** | Minimal engine (state_reader, oanda_client, signal_generator, risk_manager, scalping_rl). Not the enhanced auto-trader. | Duplicate “engine”; render uses root `scalp_engine.py`. Nested copy is dead/legacy. |

### 2.2 Missing / inconsistent flows

| Issue | Detail |
|-------|--------|
| **run_analysis_now.py omits Step 9** | Any manual “run analysis now” that uses this script never exports market state. Stale dashboard unless full workflow is used. |
| **No single documented “run analysis” entry** | run_analysis_now vs run_immediate_analysis vs run_full_analysis is unclear; one is broken (no Step 9). |

### 2.3 Path and environment

| Item | Status |
|------|--------|
| **Trade-Alerts MarketBridge** | Uses `MARKET_STATE_FILE_PATH` for write path; fallback to repo-root `market_state.json` if unset. OK. |
| **Scalp-Engine state_reader** | Complex path logic (Render vs env vs Trade-Alerts sibling). Works but is brittle (many branches). |
| **update_market_state_timestamp.py** | Lives in Trade-Alerts root. UI doc says “Run in Render Shell: python update_market_state_timestamp.py”. On Render, shell cwd is repo root; script and `MARKET_STATE_FILE_PATH` are correct for UI service (same disk). OK. |
| **market-state-api MARKET_STATE_API_URL** | Trade-Alerts must set this to POST; Scalp-Engine/UI set to GET. Base URL same, endpoint /market-state. fisher_market_bridge strips /market-state and appends /fisher-opportunities or /ft-dmi-ema-opportunities. OK. |

### 2.4 Documentation and UX

| Issue | Detail |
|-------|--------|
| **DIAGNOSE_MISSING_MARKET_STATE.md** | Refers to “Step 9 (NEW)” and “Market State exported to `/var/data/market_state.json`”. Correct. |
| **Stale workaround** | “Run python update_market_state_timestamp.py” — doesn’t say which service shell; implied repo root (all services that need it have same disk). Should state “from repo root” explicitly. |
| **No single “how to run analysis” doc** | Unclear which script to use for “run analysis now” (only run_immediate_analysis / run_full_analysis export state). |

### 2.5 Code quality / TODOs

| Location | Issue |
|----------|--------|
| **Scalp-Engine/auto_trader_core.py** | TODOs: daily loss check, total exposure check (enhancements, not blockers). |
| **Scalp-Engine/src/state_reader.py** | Staleness (age > 4h) returns None from load_state(); UI then reads file directly for “stale” message. Consistent. |

### 2.6 Operational (why “Market State is Stale” appears)

- **Root cause:** Trade-Alerts scheduled analysis (e.g. 4pm EST) either doesn’t run or doesn’t complete through Step 9.
- **Code path:** Implemented: main.py → Step 9 → MarketBridge → file + optional API. So the **implementation** is complete; the **data** is old because the workflow isn’t succeeding or isn’t triggered.

---

## 3. Master Fix Plan (Phased, No Piecemeal)

Execute in order; each phase depends on the previous.

---

### Phase 1: Unify and fix Trade-Alerts “run analysis” entry points

**Goal:** One clear, correct way to run analysis; no script that skips Step 9.

1. **Deprecate run_analysis_now.py (or make it call full workflow)**  
   - **Option A (recommended):** Replace body of `run_analysis_now.py` with a call to the same workflow as `run_immediate_analysis.py` (e.g. import and call `run_immediate_analysis()`), plus a short docstring: “Legacy name; runs full workflow including market state export (Step 9). Prefer run_immediate_analysis.py or run_full_analysis.py.”  
   - **Option B:** Delete `run_analysis_now.py` and update any references (docs, Render one-off jobs) to `run_immediate_analysis.py` or `run_full_analysis.py`.  
   - **Do not** leave a script named “run_analysis_now” that does not export market state.

2. **Clarify run_immediate_analysis vs run_full_analysis**  
   - Both call `_run_full_analysis_with_rl()`. Either:  
     - Keep both and add one-line comments/docstrings: “Same workflow as run_full_analysis; use for scripting” vs “Same workflow; use for manual full run,” or  
     - Merge into one script (e.g. keep `run_full_analysis.py` as the single entry) and point the other to it.  
   - Document in a single place (e.g. README or RUN_ANALYSIS.md): “To run analysis manually (including market state export), use: `python run_full_analysis.py` or `python run_immediate_analysis.py`.”

3. **Verification**  
   - Run `python run_analysis_now.py` (after fix) or `python run_immediate_analysis.py` from Trade-Alerts root and confirm logs show “Step 9 (NEW): Exporting market state…” and “Market State exported to …” (or API success).  
   - Confirm `market_state.json` (or API GET) timestamp updates.

---

### Phase 2: Remove or redirect Scalp-Engine duplicate/legacy code

**Goal:** Single canonical entry per concern; no legacy duplicates.

1. **Remove Scalp-Engine/src/run_fisher_scan.py**  
   - Root `Scalp-Engine/run_fisher_scan.py` is the canonical Fisher scan (reversal + API POST + disk fallback).  
   - Delete `Scalp-Engine/src/run_fisher_scan.py`.  
   - Search repo for references to `src/run_fisher_scan` or “run_fisher_scan” from `src/` and update to “run from Scalp-Engine root: python run_fisher_scan.py” or use Trade-Alerts `run_fisher_scan_now.py` (which invokes root script).

2. **Nested Scalp-Engine/scalp_engine.py**  
   - **Option A:** Delete `Scalp-Engine/Scalp-Engine/scalp_engine.py` and the empty `Scalp-Engine/Scalp-Engine/` directory if nothing else references it.  
   - **Option B:** If you want to keep a “minimal” engine for reference, move it to e.g. `Scalp-Engine/legacy_minimal_engine.py` and add a top comment: “Legacy minimal engine; production uses scalp_engine.py (root) with auto_trader_core.”  
   - Render and all docs should reference only root `scalp_engine.py`.

3. **Verification**  
   - From Scalp-Engine root: `python run_fisher_scan.py` runs and posts/updates Fisher opportunities.  
   - No imports point to `src.run_fisher_scan` or the nested `Scalp-Engine/scalp_engine.py`.

---

### Phase 3: Harden market state path and API usage

**Goal:** Consistent, predictable paths and API usage; fewer branches.

1. **Trade-Alerts MarketBridge**  
   - Already uses `MARKET_STATE_FILE_PATH`; keep. Ensure render.yaml (and any .env.example) documents: “Set MARKET_STATE_FILE_PATH for shared disk; set MARKET_STATE_API_URL to POST full state to market-state-api (e.g. https://…/market-state).”

2. **Scalp-Engine state_reader**  
   - Simplify path resolution where possible: (1) If `MARKET_STATE_FILE_PATH` set, use it (normalize to .json). (2) Else if on Render (`/var/data` exists and writable), use `/var/data/market_state.json`. (3) Else local default (e.g. Trade-Alerts sibling or repo-relative path). Remove redundant “fix .jsc / .jsor” branches if not needed in practice.  
   - Keep API-first load_state(): GET api_url; on failure or unset, read file.

3. **scalp_ui.py stale workaround text**  
   - Change to: “Run from **repo root** (Trade-Alerts) in Render Shell: `python update_market_state_timestamp.py`. Requires same disk as market state file (e.g. scalp-engine-ui or trade-alerts).”

4. **Verification**  
   - With only file (no API): Trade-Alerts writes to /var/data; UI and engine read same path; age/stale logic unchanged.  
   - With API: Trade-Alerts POSTs; market-state-api saves; UI/engine GET; Fisher/FT-DMI-EMA POST to same host, different paths.

---

### Phase 4: Documentation and runbooks

**Goal:** One place for “how to run analysis” and “how to fix stale state.”

1. **Create RUN_ANALYSIS.md (or section in README)**  
   - “Run analysis manually (includes market state export): `python run_full_analysis.py` or `python run_immediate_analysis.py`. Do not use run_analysis_now.py for production (it is deprecated / aliased to full workflow).”  
   - “Scheduled analysis: main.py loop; ensure CHECK_INTERVAL and scheduler times (e.g. 4pm EST) are correct.”

2. **Stale state runbook**  
   - In DIAGNOSE_MISSING_MARKET_STATE.md or a short STALE_STATE_RUNBOOK.md:  
     - Check Trade-Alerts logs for “Scheduled Analysis Time” and “Step 9” and “Market State exported”.  
     - If analysis didn’t run: check service up, scheduler, env.  
     - Temporary workaround: from repo root, `python update_market_state_timestamp.py` (timestamp only; content still old until next full run).

3. **Entry point index**  
   - In Scalp-Engine README or USER_GUIDE: list canonical scripts:  
     - `python run_fisher_scan.py` (from Scalp-Engine root),  
     - `python run_ft_dmi_ema_scan.py` (from Scalp-Engine root),  
     - Trade-Alerts: `run_fisher_scan_now.py` (subprocess to Scalp-Engine run_fisher_scan.py).  
   - Remove or update references to `src/run_fisher_scan.py`.

4. **Verification**  
   - New contributor can run analysis and fix stale state using only the new docs.

---

### Phase 5: Optional cleanups and safety

**Goal:** Less cruft, clearer behavior.

1. **Backups**  
   - Keep backup folders (e.g. backup_skip_stale_crossover_20260212, backup_ft_dmi_ema_20260210) until Phases 1–4 are verified in production. Then delete or archive per your policy.

2. **TODOs in auto_trader_core.py**  
   - Leave as-is for this plan, or add a single “TODO: daily loss check; total exposure check” in a tracked issue. No code change required for “complete fix” of current issues.

3. **render.yaml**  
   - Ensure trade-alerts has `MARKET_STATE_API_URL` and `MARKET_STATE_FILE_PATH` documented (or set in Dashboard) so POST to market-state-api is possible when not using shared disk only.  
   - scalp-engine-ui: MARKET_STATE_API_URL sync: false is fine; document “Set to market-state-api GET URL if you want UI to read from API.”

4. **Verification**  
   - Full deploy: trade-alerts runs on schedule and updates file (and API if configured); UI shows fresh state after next run; Fisher/FT-DMI-EMA scans update state via API or file.

---

## 4. Verification Checklist (After All Phases)

- [ ] Trade-Alerts: Only `run_full_analysis.py` / `run_immediate_analysis.py` (and optionally aliased `run_analysis_now.py`) run full workflow including Step 9.
- [ ] Trade-Alerts: Logs show “Step 9 (NEW): Exporting market state…” and “Market State exported to …” (or API success) on manual run.
- [ ] Scalp-Engine: Single Fisher scan entry is root `run_fisher_scan.py`; `src/run_fisher_scan.py` removed.
- [ ] Scalp-Engine: No production use of nested `Scalp-Engine/scalp_engine.py`; removed or renamed to legacy.
- [ ] Market state: Same path used by Trade-Alerts write and Scalp-Engine/UI read when using file; API URL consistent when using API.
- [ ] Stale workaround: Documented “run from repo root” and “python update_market_state_timestamp.py”.
- [ ] Docs: Single “run analysis” and “stale state” runbook; entry point index for Scalp-Engine scripts.

---

## 5. Rollback

- **Phase 1:** Revert changes to `run_analysis_now.py`; keep using `run_immediate_analysis.py` / `run_full_analysis.py` for correct behavior.
- **Phase 2:** Restore `src/run_fisher_scan.py` and nested `Scalp-Engine/scalp_engine.py` from git history if needed.
- **Phase 3:** Revert state_reader and scalp_ui text changes; restore previous path logic.
- **Phase 4:** Remove or revert new docs only.
- Backups in backup_* folders remain until you explicitly delete them.

---

## 6. Summary Table

| Phase | Focus | Main actions |
|-------|--------|--------------|
| 1 | Trade-Alerts run analysis | Fix/deprecate run_analysis_now; unify run_immediate vs run_full; document single “run analysis” |
| 2 | Scalp-Engine duplicates | Remove src/run_fisher_scan.py; remove or rename nested Scalp-Engine/scalp_engine.py |
| 3 | Paths and API | Simplify state_reader path logic; clarify stale workaround text; document env vars |
| 4 | Docs and runbooks | RUN_ANALYSIS.md; stale state runbook; entry point index |
| 5 | Optional | Backup policy; render.yaml env notes; TODOs as issues |

Implementing Phases 1–4 in order will fix the broken “run analysis” path, remove duplicate/legacy entry points, and align documentation with behavior—giving you a single, consistent way to run analysis and fix stale state without piecemeal fixes.
