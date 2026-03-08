# Fisher Transform & Semi-Auto Integration – Root Cause Analysis

**Date:** 2026-01-31  
**Status:** Gaps identified – corrective measures defined below

---

## Executive Summary

The Fisher Transform and Semi-Auto features were only partially implemented. Several critical integration points were never wired, so the engine never processes Fisher opportunities and the UI often does not show them. This analysis traces the full data flow and lists the required fixes.

---

## 1. DATA FLOW AUDIT

### 1.1 Fisher opportunities – write path ✅

| Step | Component | Status | Details |
|------|-----------|--------|---------|
| 1 | `run_fisher_scan.py` | ✅ | Runs scanner, calls FisherMarketBridge |
| 2 | `FisherMarketBridge.add_fisher_opportunities()` | ✅ | Writes to market_state.json (fisher_opportunities, fisher_last_updated, fisher_count) |
| 3 | File location | ✅ | /var/data/market_state.json (or MARKET_STATE_FILE_PATH) |
| 4 | Verification | ✅ | Log confirms: "File contains 1 Fisher opportunities" |

**Conclusion:** The Fisher scan writes Fisher opportunities into the file as intended.

### 1.2 Fisher opportunities – read path (UI) ⚠️

| Step | Component | Issue | Details |
|------|-----------|-------|---------|
| 1 | `load_market_state()` | - | Uses MarketStateReader |
| 2 | MarketStateReader | API first | Tries `_load_from_api()` before file |
| 3 | API source | MARKET_STATE_API_URL | market-state-api GET /market-state |
| 4 | Staleness check | Rejects old state | If `timestamp` > 4 hours → returns None |
| 5 | Required fields | Strict | Needs timestamp, global_bias, regime, approved_pairs |

**Findings:**

- UI prefers API over file; if API fails or is unavailable, it falls back to file.
- 4-hour staleness check can cause the entire state (including Fisher) to be rejected.
- The main `timestamp` comes from Trade-Alerts; if Trade-Alerts has not run recently, Fisher data can be dropped even when it is fresh.
- No dedicated path for Fisher that ignores staleness of the main state.

### 1.3 Fisher opportunities – engine processing ❌ NOT IMPLEMENTED

| Step | Component | Status | Details |
|------|-----------|--------|---------|
| 1 | `_check_new_opportunities()` | ❌ | Only uses `market_state.get('opportunities', [])` |
| 2 | Fisher opportunities | ❌ | Never uses `market_state.get('fisher_opportunities', [])` |
| 3 | SEMI_AUTO mode | ❌ | Enum exists; no logic to process Fisher when mode is SEMI_AUTO |
| 4 | SemiAutoController | ❌ | UI saves config; engine never reads `is_enabled()` for Fisher |

**Conclusion:** The engine never processes Fisher opportunities. Only LLM opportunities (`opportunities`) are considered.

### 1.4 Disk / service layout (Render)

- scalp-engine, market-state-api, scalp-engine-ui, config-api: all use `disk: shared-market-data` at `/var/data`.
- Same blueprint → shared persistent volume.
- Fisher scan (scalp-engine) and market-state-api read/write the same `market_state.json`.

---

## 2. GAP SUMMARY

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 1 | Engine does not process `fisher_opportunities` | Critical | Fisher opportunities never lead to trades |
| 2 | SEMI_AUTO not wired to Fisher execution | Critical | Mode has no effect on Fisher |
| 3 | SemiAutoController not used by engine | Critical | Per-opportunity “enabled” is ignored |
| 4 | UI staleness can hide Fisher data | Medium | Old Trade-Alerts timestamp hides Fisher |
| 5 | No fallback read for Fisher in UI | Medium | If API/file fails, Fisher is not shown |

---

## 3. ROOT CAUSES

### Why Fisher opportunities don’t appear in the UI

1. **Staleness:** If the main `timestamp` is > 4 hours old, `MarketStateReader.load_state()` returns None and the UI shows “Could not load market state” or similar.
2. **API vs file:** If UI uses the API and the API reads from a different or stale copy of the file, Fisher data might not be present.
3. **Timing:** Trade-Alerts POST can overwrite the file; the merge preserves Fisher only when `save_state()` loads the existing file and it already contains Fisher. Order of operations matters.

### Why Semi-Auto has no effect

1. The engine only processes `opportunities` (LLM), not `fisher_opportunities`.
2. `SemiAutoController.is_enabled(opp_id)` is never called by the engine.
3. There is no branch in the engine for `trading_mode == SEMI_AUTO` that handles Fisher opportunities.

---

## 4. REQUIRED CORRECTIVE MEASURES

### 4.1 Engine – process Fisher opportunities (critical)

- In `scalp_engine.py`, add logic (e.g. `_check_fisher_opportunities()`) that:
  - Reads `market_state.get('fisher_opportunities', [])`
  - Runs only when `trading_mode == SEMI_AUTO` or `MANUAL` (never in AUTO)
  - Filters by `SemiAutoController.is_enabled(opp_id)` when in SEMI_AUTO
  - Passes enabled Fisher opportunities into the same execution path used for LLM opportunities (or an equivalent path that respects execution rules)

### 4.2 Engine – wire SEMI_AUTO and SemiAutoController (critical)

- When `trading_mode == SEMI_AUTO`:
  - Only execute opportunities that are enabled via `SemiAutoController.is_enabled(opp_id)`.
- When `trading_mode == MANUAL`:
  - Do not auto-execute; only log/alert.
- Ensure `PositionManager.open_trade()` or equivalent uses `SemiAutoController` for Fisher opportunities.

### 4.3 UI – reliable Fisher display (medium)

- Add a Fisher-specific load path that:
  - Reads `/var/data/market_state.json` directly when the main `load_market_state()` fails or returns None, or
  - Bypasses the 4-hour staleness check for Fisher fields when `fisher_last_updated` is recent.
- Use this path only for the Fisher tab so Fisher data is shown even when the main state is considered stale.

### 4.4 UI – cache and refresh (low)

- On “Refresh Data”, ensure `load_market_state()` cache is cleared so a new read (API or file) is performed.
- Consider shortening cache TTL for the Fisher tab (e.g. 10–15 seconds) so new scans appear sooner.

---

## 5. FILES TO MODIFY

| File | Changes |
|------|---------|
| `scalp_engine.py` | Add `_check_fisher_opportunities()`; call it from the main loop; wire SEMI_AUTO and SemiAutoController |
| `scalp_ui.py` | Add Fisher fallback load; optionally relax staleness for Fisher tab |
| `src/state_reader.py` | Optionally relax staleness when Fisher data is present and recent |
| `auto_trader_core.py` | Ensure PositionManager/open_trade respects SemiAutoController for Fisher |

---

## 6. IMPLEMENTATION ORDER

1. **Phase 1 (critical):** Engine processes Fisher opportunities and respects SEMI_AUTO/SemiAutoController.
2. **Phase 2 (medium):** UI reliably displays Fisher opportunities (fallback load / staleness bypass).
3. **Phase 3 (low):** Cache/refresh tuning for Fisher tab.

---

## 7. VERIFICATION CHECKLIST

After changes:

- [ ] Run Fisher scan in shell; verification log shows “File contains N Fisher opportunities”.
- [ ] Fisher tab shows N opportunities and “Last scan” timestamp.
- [ ] Enable one Fisher opportunity in the UI and save config.
- [ ] With SEMI_AUTO mode, engine logs that it is processing Fisher opportunities.
- [ ] Engine executes (or attempts) the enabled Fisher opportunity and respects `max_runs`.
- [ ] With MANUAL mode, no automatic execution; opportunities appear for manual action only.
