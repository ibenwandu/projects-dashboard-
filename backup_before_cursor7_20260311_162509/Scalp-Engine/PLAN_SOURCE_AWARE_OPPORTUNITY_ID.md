# Plan: Source-Aware Opportunity ID (Fix LLM vs DMI-EMA Config Collision)

## 1. Explanation: Why Two USD/JPY Trades Show One as “Enabled” When You Only Enabled the Other

LLM and DMI-EMA are **two distinct lists** from two different scan processes. The UI correctly shows them as separate rows: `[LLM] USD/JPY SELL` and `[DMI-EMA] USD/JPY SHORT`. The bug is not in the list generation but in **how “enabled” is stored and looked up**.

### Root cause: single namespace for (pair, direction)

- **Stable opportunity ID** is defined in `src/execution/opportunity_id.py` as **pair + direction only**:
  - `get_stable_opportunity_id(opportunity)` → e.g. `"USD/JPY_SHORT"`.
  - It does **not** include the source (LLM, Fisher, FT-DMI-EMA, DMI-EMA).
- **Semi-auto config** (enabled/disabled, mode, max_runs, sl_type) is keyed **only** by that ID:
  - Stored in config API and/or `/var/data/semi_auto_config.json` under `opportunities["USD/JPY_SHORT"]`.
- So:
  - When you **enable** `[LLM] USD/JPY SELL`, the UI saves `enabled=True` under key `"USD/JPY_SHORT"`.
  - When the UI renders `[DMI-EMA] USD/JPY SHORT`, it looks up **the same key** `"USD/JPY_SHORT"` and gets the same config → it shows **ENABLED** even though you never enabled the DMI-EMA row.

So the two lists are correct; the **config namespace is shared** across sources for the same (pair, direction). Enabling one source’s USD/JPY SHORT effectively enables every other source’s USD/JPY SHORT for that pair/direction.

### Other subsystems that share the same key

The same `get_stable_opportunity_id(opportunity)` (pair + direction only) is used for:

1. **Semi-auto config** – enable/disable, mode, max_runs, sl_type (UI + engine).
2. **Execution history (run count)** – `execution_mode_enforcer.py` uses `opp_id` for `_has_exceeded_max_runs` and `record_execution`. So one run of LLM USD/JPY SHORT increments count for `"USD/JPY_SHORT"`; DMI-EMA USD/JPY SHORT would then see that count and can be rejected by max_runs.
3. **Clearing pending signals** – `_clear_pending_signals_for_disabled_opportunities` in `scalp_engine.py` uses `opp_id` to decide which pending signals to remove and whether to call `set_opportunity_enabled(opp_id, False)`. Again one namespace for all sources.
4. **Engine filtering** – Fisher, FT-DMI-EMA, and DMI-EMA “enabled” checks all use `semi_auto.is_enabled(get_stable_opportunity_id(o))`, so they all see the same enabled flag for a given (pair, direction).

So the issue is **architectural**: the system was designed when there was effectively one “opportunity” per (pair, direction). Adding a second source (DMI-EMA) that can produce the same (pair, direction) as LLM (or Fisher, or FT-DMI-EMA) without making the config key source-aware caused the collision.

---

## 2. Design goal

- **Enable/disable, mode, max_runs, sl_type, and run count must be per (source, pair, direction).**
- So:
  - `[LLM] USD/JPY SELL` → one config and one run count.
  - `[DMI-EMA] USD/JPY SHORT` → a **different** config and run count, even though pair/direction normalize to the same.

No piecemeal fix (e.g. only changing the UI key) is sufficient: the engine, enforcer, and config storage must all use the same source-aware key.

---

## 3. Proposed approach: source-aware stable opportunity ID

### 3.1 Canonical source labels

Use a single set of canonical source strings everywhere (UI, engine, enforcer, config):

- `LLM`
- `Fisher`
- `FT_DMI_EMA` (internal; UI may display “FT-DMI-EMA”)
- `DMI_EMA` (internal; UI may display “DMI-EMA”)

Opportunity dicts already carry (or can carry) a source:

- LLM: from `market_state['opportunities']` → treat as `LLM` (or add `source: "LLM"` if missing).
- Fisher: from `market_state['fisher_opportunities']` → treat as `Fisher`.
- FT-DMI-EMA: `opportunity.get("source") == "FT_DMI_EMA"` in enforcer → use `FT_DMI_EMA`.
- DMI-EMA: `opportunity.get("source") == "DMI_EMA"` (or from `dmi_ema_opportunities`) → use `DMI_EMA`.

### 3.2 New stable ID format

- **Option A (recommended):** `{source}_{pair}_{direction}`  
  - Examples: `LLM_USD/JPY_SHORT`, `DMI_EMA_USD/JPY_SHORT`.
- **Option B:** Keep a legacy `{pair}_{direction}` and add a separate `source` in the config structure. That would require config schema change and more branching; Option A keeps a single key and minimal schema change.

So:

- Define a **single** function that returns a source-aware ID, e.g.  
  `get_stable_opportunity_id(opportunity, source: Optional[str] = None) -> str`.  
  If `source` is None, derive it from `opportunity.get("source")` or from context (see below).  
  Return `f"{source}_{pair}_{direction}"` with normalized pair/direction (same rules as today).
- **Backward compatibility:** See migration section below.

### 3.3 Where “source” comes from when not on the opportunity

- **UI:** The list is built from four separate lists (LLM, Fisher, FT-DMI-EMA, DMI-EMA); each item has an explicit `source` in the loop. So when calling `get_opportunity_config` / `set_opportunity_config`, the UI must pass the **source-aware** ID (e.g. by calling `get_stable_opportunity_id(opp, source=item['source'])` or a helper that builds `f"{source}_{pair}_{direction}"`).
- **Engine:** When processing LLM opportunities, source is LLM; when processing Fisher/FT-DMI-EMA/DMI-EMA, the opportunity dict already has `source` set (e.g. `FT_DMI_EMA`, `DMI_EMA`) or the code path knows the list (e.g. `dmi_ema_opportunities` → DMI_EMA). So every place that currently calls `get_stable_opportunity_id(opportunity)` must pass the correct source (or the opportunity must always have `source` set and the function derives it).

So the contract is: **every code path that uses the stable ID for config or run count must supply or infer the same canonical source.**

---

## 4. Affected components and required changes

### 4.1 `src/execution/opportunity_id.py`

- Extend `get_stable_opportunity_id(opportunity, source=None)`:
  - Normalize pair and direction as today.
  - If `source` is provided, return `f"{source}_{pair}_{direction}"`.
  - If `source` is None, derive from `opportunity.get('source')` (map `FT_DMI_EMA` → `FT_DMI_EMA`, `DMI_EMA` → `DMI_EMA`); if still missing, default to `LLM` for backward compatibility (or leave as legacy `pair_direction` for migration – see below).
- Document that config and execution history use this ID and that source must be consistent across UI and engine.

### 4.2 UI: `scalp_ui.py`

- When building the semi-auto list, for each item you have `item['source']` (e.g. `'LLM'`, `'DMI-EMA'`). Map display name to canonical: `'FT-DMI-EMA'` → `'FT_DMI_EMA'`, `'DMI-EMA'` → `'DMI_EMA'`, `'LLM'` → `'LLM'`, `'Fisher'` → `'Fisher'`.
- Compute **source-aware** opp_id, e.g. `opp_id = get_stable_opportunity_id(opp, source=canonical_source)` or a helper that uses `canonical_source` and normalized pair/direction.
- Use this `opp_id` for:
  - `semi_auto.get_opportunity_config(opp_id)`
  - `semi_auto.set_opportunity_config(opp_id, ...)`
- No other UI logic need change if the key is the only thing that changes.

### 4.3 Engine: `scalp_engine.py`

- Every call to `get_stable_opportunity_id(opp)` (or fallback) must pass the correct **source** for that code path:
  - LLM opportunities → `get_stable_opportunity_id(opp, source='LLM')`.
  - Fisher → `source='Fisher'`.
  - FT-DMI-EMA → `source='FT_DMI_EMA'` (opp may already have `source='FT_DMI_EMA'`).
  - DMI-EMA → `source='DMI_EMA'` (opp may already have `source='DMI_EMA'`).
- Affected areas (grep for `get_stable_opportunity_id` / `_stable_opp_id_fallback`):
  - LLM enabled count and per-opp config (e.g. around 982, 1012).
  - Fisher filtering and per-opp (1382, 1397, 1422, 1587).
  - FT-DMI-EMA filtering and per-opp (1959, 1983, 1884).
  - DMI-EMA filtering and per-opp (2180, 2203).
  - `_clear_pending_signals_for_disabled_opportunities`: when building `enabled_set` and when calling `set_opportunity_enabled(opp_id, False)`, use source-aware opp_id (2380, 2386, 2390, 2394, 2431).
- Ensure opportunity dicts from each path have a consistent `source` when present (e.g. DMI-EMA opportunities already set `"source": "DMI_EMA"` in `_inject_dmi_ema_opportunities`).

### 4.4 Execution mode enforcer: `src/execution/execution_mode_enforcer.py`

- `get_execution_directive` and `record_execution` use `opp_id = get_stable_opportunity_id(opportunity)`. The enforcer does not know the “list” name; it only sees the opportunity dict. So the **opportunity must carry a canonical source** that the enforcer can use:
  - For FT-DMI-EMA and DMI-EMA the code already checks `opportunity.get("source") == "FT_DMI_EMA"` / `"DMI_EMA"`.
  - For LLM and Fisher, the opportunity may not have `source` set; then either:
    - (a) Ensure every opportunity dict passed to the enforcer has `source` set (LLM, Fisher, FT_DMI_EMA, DMI_EMA), and in `opportunity_id.py` derive source from `opportunity.get('source')` when `source` argument is None, or  
    - (b) Pass source from the engine into the enforcer (e.g. enforcer method takes optional `source` and uses it for the ID).  
  Option (a) keeps the enforcer simpler: one place (engine) sets `source` on the dict before calling open_trade/get_execution_directive; then `get_stable_opportunity_id(opportunity)` can derive source from the dict.
- So: ensure **every** opportunity that reaches the enforcer or `open_trade` has `source` set (LLM, Fisher, FT_DMI_EMA, DMI_EMA). Then change `get_stable_opportunity_id(opportunity, source=None)` to use `opportunity.get('source')` when `source` is None, and return `f"{canonical_source}_{pair}_{direction}"`.

### 4.5 Auto-trader core: `auto_trader_core.py`

- `open_trade` (and any path that calls the enforcer or records run count) receives an opportunity dict. If the engine always sets `source` on the opportunity before calling `open_trade`, then the enforcer’s `get_stable_opportunity_id(opportunity)` will automatically become source-aware once the ID function is updated.
- The only place in auto_trader_core that uses `get_stable_opportunity_id` is for `record_execution` (e.g. around 994). That will then use the same source-aware ID as long as the opportunity has `source` set.
- Pending signals: `_clear_pending_for_pair_direction` is pair/direction based; that’s for removing pending by market, not by config. The clearing that respects “disabled” is in scalp_engine `_clear_pending_signals_for_disabled_opportunities`, which must use source-aware opp_id (covered above).

### 4.6 Semi-auto controller: `src/execution/semi_auto_controller.py`

- No API change: it still accepts `opp_id` string and stores under `opportunities[opp_id]`. The only change is that `opp_id` will now be source-prefixed (e.g. `LLM_USD/JPY_SHORT`). No migration inside the class except if we do a one-time migration of existing keys (see below).

### 4.7 Execution history: `src/execution/execution_mode_enforcer.py`

- Execution history is keyed by the same `opp_id` returned by `get_stable_opportunity_id`. Once that becomes source-aware, run count will automatically be per (source, pair, direction). No separate change except ensuring the enforcer gets the ID from the updated function (with `source` on the opportunity or passed in).

### 4.8 Pending signals and clearing logic

- **Storing pending:** Already stores by signal_id (e.g. `pair_direction_wait_for_signal`). No change needed for storage format.
- **Clearing:** `_clear_pending_signals_for_disabled_opportunities` builds an `enabled_set` of (pair_norm, dir_key) and optionally calls `set_opportunity_enabled(opp_id, False)`. Today it uses a single opp_id per (pair, direction). It must be updated so that:
  - `enabled_set` is per (source, pair, direction), and
  - When removing a pending signal, we know the source of that pending (e.g. from the opportunity’s `source` or from the directive’s `wait_for_signal` – e.g. DMI_EMA_M15_TRIGGER → DMI_EMA). So we only clear and call `set_opportunity_enabled` for that source’s opp_id.

So the clearing logic must be updated to use source-aware enabled_set and source-aware opp_id when calling set_opportunity_enabled.

---

## 5. Backward compatibility and migration

- **Existing config and execution history** use keys like `USD/JPY_SHORT` (no source prefix). After the change, new keys will look like `LLM_USD/JPY_SHORT`, `DMI_EMA_USD/JPY_SHORT`.
- **Options:**
  - **A. Clean break:** Do not migrate. After deploy, all existing “enabled” state is effectively lost; users re-enable per source. Simple, but existing enabled state is reset.
  - **B. One-time migration:** On first load (or in a small migration script), for each key `K` in `opportunities` (and in execution_history) that does not contain an underscore prefix from the known source list, duplicate config to all sources that could have that pair/direction: e.g. create `LLM_K`, `Fisher_K`, `FT_DMI_EMA_K`, `DMI_EMA_K` with the same config, then remove `K`. That preserves “enabled” but applies it to all sources (current behavior). Then going forward only source-prefixed keys are used.
  - **C. Read fallback:** When looking up config (or run count), if the source-aware key is missing, fall back to legacy key `pair_direction`. So old config still applies until the user re-saves from the UI (at which point we write the new key). Over time we can stop writing the legacy key. Execution history could do the same: if `LLM_USD/JPY_SHORT` is missing, check `USD/JPY_SHORT` for run count.

Recommendation: **C (read fallback)** for both semi-auto config and execution history, with a clear comment that legacy key is only for backward compatibility. When the user saves from the UI, we write only the source-aware key. No need to migrate old files; we just support reading both. Option B is possible if you want to migrate existing config once.

---

## 6. Summary of files to touch (no piecemeal fixes; do together)

| File | Change |
|------|--------|
| `src/execution/opportunity_id.py` | Add source to stable ID: `get_stable_opportunity_id(opportunity, source=None)` returning `{source}_{pair}_{direction}`; derive source from `opportunity.get('source')` when None; document. |
| `scalp_ui.py` | Use canonical source for each list item; compute source-aware opp_id and use it for get/set_opportunity_config. |
| `scalp_engine.py` | Ensure every opportunity dict has `source` set (LLM, Fisher, FT_DMI_EMA, DMI_EMA) before any config or enforcer use; replace all get_stable_opportunity_id calls with the same function (source can come from dict); update _clear_pending_signals_for_disabled_opportunities to use source-aware enabled_set and opp_id. |
| `src/execution/execution_mode_enforcer.py` | Use get_stable_opportunity_id(opportunity) with source from opportunity; ensure execution_history and record_execution use the same ID. Optionally add read fallback for legacy key in _has_exceeded_max_runs and get_opportunity_config (if we centralize config read in enforcer; currently config is in SemiAutoController). |
| `auto_trader_core.py` | Ensure opportunity has source when calling enforcer (already passed from engine); no change if engine always sets source. |
| `src/execution/semi_auto_controller.py` | Optional: in get_opportunity_config(opp_id), if opp_id not found and opp_id does not contain a known source prefix, try legacy key (e.g. strip source prefix and try again) for backward compatibility. Or keep as-is and rely on UI/engine to pass new key only. |

---

## 7. Testing (after implementation)

- **UI:** Enable only `[LLM] USD/JPY SELL`. Refresh. Confirm `[DMI-EMA] USD/JPY SHORT` is DISABLED. Enable only `[DMI-EMA] USD/JPY SHORT`. Confirm `[LLM] USD/JPY SELL` stays DISABLED. Save and reload; state must persist per source.
- **Engine:** With only LLM USD/JPY SELL enabled, run the engine; only LLM opportunity should execute (or wait for trigger). With only DMI-EMA USD/JPY SHORT enabled, only DMI-EMA should be stored/executed.
- **Run count:** Execute LLM USD/JPY SELL once (max_runs=1). Confirm DMI-EMA USD/JPY SHORT can still execute (separate run count). And vice versa.
- **Pending signals:** Enable DMI-EMA USD/JPY SHORT, wait for it to be stored as pending; disable DMI-EMA USD/JPY SHORT; confirm that pending is cleared and LLM USD/JPY SELL (if it were pending) is unaffected.
- **Backward compatibility:** If using read fallback, load an old semi_auto_config.json with only `USD/JPY_SHORT`; expect both LLM and DMI-EMA rows to show that legacy state until user re-saves (then they split). Document that behavior.

---

## 8. Related issues to include in the same pass

- **JSON serialization of pending signals:** Already fixed in a previous change (`_to_json_safe` in auto_trader_core). No further change needed unless we add source to the stored opportunity (already serialized).
- **Consistent `source` on opportunities:** Ensure every place that builds an opportunity dict for LLM, Fisher, FT-DMI-EMA, or DMI-EMA sets `source` to the canonical value so that enforcer and ID logic do not need separate source parameters in every call. This is part of the “ensure opportunity has source” work in scalp_engine and any other builder.

This plan addresses the root cause (single namespace for config and run count) and outlines a single, consistent change set across UI, engine, enforcer, and config so that LLM and DMI-EMA (and Fisher, FT-DMI-EMA) have distinct enabled state and run counts per (source, pair, direction).
