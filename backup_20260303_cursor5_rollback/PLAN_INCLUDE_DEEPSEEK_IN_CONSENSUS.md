# Plan: Include Deepseek (and All Base LLMs) in Trade Opportunity Listings

## Problem Summary

- **Deepseek** is in LLM Performance Weights (16%) and contributes to analysis, but **never appears in "Agreeing LLMs"** on Current Opportunities.
- Consensus is shown as **X/3** (e.g. 1/3, 2/3, 3/3), implying only three models are used for the displayed opportunities, while five models (ChatGPT, Gemini, Claude, Deepseek, Synthesis) are in the system.

## Root Cause

In **Trade-Alerts** `src/market_bridge.py`, consensus is computed in `_analyze_consensus_for_pair()` using a **hardcoded list of base LLMs**:

```python
base_llms = ['chatgpt', 'gemini', 'claude']  # Line 544 — Deepseek is missing
```

- **Method 1** (primary): Iterates only over `base_llms` to see which LLMs have a matching (pair, direction) in `all_opportunities`. Because `deepseek` is not in `base_llms`, Deepseek’s parsed opportunities are **never checked**, so Deepseek never gets added to `llm_sources` or `base_llm_sources`.
- **main.py** already parses and passes **deepseek** in `all_opportunities` (line 509: `['chatgpt', 'gemini', 'claude', 'deepseek']`), so the data is there; only the consensus logic omits it.
- Synthesis is handled separately and is not counted toward the numeric “consensus level”; the level is the count of **base** LLMs agreeing (currently 1–3, intended 1–4).

So the fix is to **include Deepseek in the base LLM list** and align comments, UI labels, and fallbacks with a **4-base-LLM** model (chatgpt, gemini, claude, deepseek) without changing how synthesis or execution filtering works.

---

## Design Principles (No Breaking Changes)

1. **Execution behavior unchanged**
   - Scalp-Engine continues to filter by `min_consensus_level` (e.g. 2) and optional `required_llms`.
   - No change to when trades are opened/closed; only **which** LLMs are shown as “agreeing” and the **denominator** of consensus (3 → 4).

2. **Consensus semantics**
   - **Consensus level** = number of **base** LLMs that agree (1–4). Synthesis does not count toward this number.
   - **Agreeing LLMs** = list of all sources that agree (base LLMs + optionally synthesis). Deepseek will appear here when it has a matching opportunity.

3. **Backward compatibility**
   - Existing opportunities that were 2/3 or 3/3 become 2/4 or 3/4 (or 4/4 if Deepseek also agrees). They still pass the same `min_consensus_level` (e.g. 2).
   - Position sizing uses `consensus_multiplier.get(consensus_level, 1.0)`; adding key `4` where missing keeps level-4 behavior explicit and consistent.

---

## Implementation Plan

### Phase 1: Trade-Alerts — Consensus Logic (Single Source of Truth)

**File: `src/market_bridge.py`**

| Step | Location | Change |
|------|----------|--------|
| 1.1 | Line 544 | Change `base_llms = ['chatgpt', 'gemini', 'claude']` to `base_llms = ['chatgpt', 'gemini', 'claude', 'deepseek']`. |
| 1.2 | Line 778 (comment) | Update comment from “count of base LLMs only (1, 2, or 3)” to “(1, 2, 3, or 4)”. |
| 1.3 | Line 789 (comment) | Update “Ensure consensus_level is between 1 and 3” to “1 and 4” (logic already caps at 4). |
| 1.4 | Line 753 (Method 3 fallback) | When synthesis text suggests “all agree”, set `base_llm_sources` and `sources` to include `'deepseek'`: e.g. `['chatgpt', 'gemini', 'claude', 'deepseek']` so fallback is consistent with 4 base LLMs. |

**Optional:** If the repo has a duplicate `src/src/market_bridge.py`, apply the same edits there or remove the duplicate and use a single `src/market_bridge.py`.

**Verification:** Run one full Trade-Alerts analysis; in logs, confirm for at least one opportunity that when Deepseek has a matching (pair, direction), `base_llm_sources` and `sources` include `'deepseek'` and `consensus_level` can be 4.

---

### Phase 2: Scalp-Engine — UI Consistency

**File: `Scalp-Engine/scalp_ui.py`**

| Step | Location | Change |
|------|----------|--------|
| 2.1 | ~Line 1613 (Market Intelligence / Current Opportunities) | Change display from `Consensus: {consensus}/3` to `Consensus: {consensus}/4` so it matches the expander header (already “Consensus: X/4”). |
| 2.2 | ~Line 1492 (Pending signals / trade row) | Change `Consensus: …/3` to `…/4` for consistency. |

No change to filtering logic or execution; only display text.

---

### Phase 3: Scalp-Engine — Default Config (Optional but Recommended)

**File: `Scalp-Engine/auto_trader_core.py`**

| Step | Location | Change |
|------|----------|--------|
| 3.1 | Default `consensus_multiplier` (~lines 173–176) | Add key `4: 2.0` (e.g. “All 4 base LLMs agree = 200% position”) so that when config is built from defaults, level-4 consensus gets an explicit multiplier. Engine already uses `.get(consensus_level, 1.0)`, so 4 would otherwise fall back to 1.0. |

**File: `Scalp-Engine/config_api_server.py` / `scalp_api.py` / `run_ui_with_api.py`**

| Step | Location | Change |
|------|----------|--------|
| 3.2 | Where `consensus_multiplier` is defined | Ensure the structure includes key `4` (e.g. `'4': 2.0` or `4: 2.0`) so API/default configs stay aligned with 4-level consensus. |

This keeps position sizing for “4 LLMs agree” explicit and consistent across UI table (“4 LLMs Agree (ALL_AGREE)” → 2.0x) and engine.

---

### Phase 4: Testing and Rollout

| Step | Action |
|------|--------|
| 4.1 | **Unit / smoke:** If tests exist for `MarketBridge._analyze_consensus_for_pair`, add a case where `all_opportunities['deepseek']` contains a matching pair/direction and assert Deepseek is in `sources` and consensus_level can be 4. |
| 4.2 | **Integration:** Run one full Trade-Alerts analysis with Deepseek enabled; confirm market state has opportunities with `llm_sources` containing `deepseek` where expected. |
| 4.3 | **UI:** Load Scalp-Engine UI; confirm “Agreeing LLMs” can show deepseek and consensus displays as X/4. |
| 4.4 | **Execution:** Leave `min_consensus_level` and trading mode unchanged; confirm no new unintended trades (filtering unchanged) and that existing behavior for 2/3 and 3/3 opportunities is preserved (now 2/4, 3/4). |
| 4.5 | **Rollout:** Deploy Trade-Alerts first (consensus fix), then Scalp-Engine (UI/config). No need to change execution logic or env vars. |

---

## Files Summary

| Repo / Area | File | Change |
|-------------|------|--------|
| Trade-Alerts | `src/market_bridge.py` | Add `deepseek` to `base_llms`; update comments and Method 3 “all agree” fallback to 4 base LLMs. |
| Trade-Alerts | `src/src/market_bridge.py` | Same as above if this copy is still in use; otherwise remove or ignore. |
| Scalp-Engine | `scalp_ui.py` | Display “Consensus: X/4” in both places that currently show “X/3”. |
| Scalp-Engine | `auto_trader_core.py` | Add `4: 2.0` to default `consensus_multiplier`. |
| Scalp-Engine | `config_api_server.py`, `scalp_api.py`, `run_ui_with_api.py` | Ensure `consensus_multiplier` includes level 4 where applicable. |

---

## Risk Mitigation

- **No change to:** `min_consensus_level` semantics, `required_llms`, execution mode, or when trades open/close.
- **Only additions:** One more LLM in the consensus list; one more key in default multiplier; denominator 3→4 in display.
- **Rollback:** Revert `base_llms` to `['chatgpt', 'gemini', 'claude']` and revert UI to “/3”; leave config multiplier as-is (level 4 would still get fallback 1.0).

This plan includes Deepseek in the opportunity listings and aligns the system with a 4-base-LLM consensus without breaking the current trading behavior.
