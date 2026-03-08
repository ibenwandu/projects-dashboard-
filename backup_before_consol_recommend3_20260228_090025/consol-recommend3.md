# Consolidated Implementation Plan (v3) — consol-recommend3.md

**Purpose:** Merge recommendations from **Cursor** (`Scalp-Engine/suggestions from cursor2.md`) and **Anthropic** (`suggestions_from_anthropic2.md`) into a single implementation plan that improves the trading system while **avoiding the failures of previous implementations** (see `CLAUDE.md` Sessions Feb 25 and Feb 26).

**Status:** Plan only. No code or config changes until you approve each phase or item.

**References:**
- Cursor: `Scalp-Engine/suggestions from cursor2.md`
- Anthropic: `suggestions_from_anthropic2.md`
- Failure context: `CLAUDE.md` (Session Feb 25, 2026 — rollback; Session Feb 26 — consol-recommend2 and what to avoid)
- Previous plan: `consol-recommend2.md` (already implemented; this plan builds on it)

---

## 1. Comparison: Cursor vs Anthropic (v3)

### 1.1 Where both agree

| Topic | Cursor (cursor2) | Anthropic (anthropic2) | Consolidated stance |
|-------|-------------------|------------------------|----------------------|
| **max_runs blocking** | Verify or add auto-reset when no position for (pair, direction); document when run count resets (5.2) | Reset max_runs when trade closes; or time-based reset; or track per-order (Issue 4) | **Same intent:** Allow retry when there is no open/pending order for that (pair, direction). Implement: when directive is REJECT for `max_runs` and `has_existing_position(pair, direction)` is False, reset run count for that opp_id and re-get directive. **Do not** change consensus or duplicate logic. Document behaviour. |
| **DeepSeek parser** | Extend parser for DeepSeek format or document limitation (5.5) | Parser returns 0 matches; update prompt for JSON or create narrative parser (Issue 2) | **Aligned:** Either (A) prompt DeepSeek for JSON / add DeepSeek-specific parser, or (B) document that DeepSeek is not parsed until format aligned. Fix or document; do not leave broken without visibility. |
| **Claude billing / failure** | Log "API credit/billing issue" when applicable; optional doc (5.6) | Claude API credits exhausted; upgrade credits or disable Claude; formalize error handling (Issue 1, Part 3) | **Aligned:** Log one clear line when failure is billing/credit (e.g. "Claude skipped: API credit/billing issue – check Anthropic account"). Document in USER_GUIDE. No consensus formula change. |
| **Config / Required LLMs** | Document consensus denominator and required_llms; optional validation (5.4) | Config changed to single "gemini"; investigate and document; config validation (Issue 3, Part 4) | **Aligned:** **Investigation + documentation only.** Explain required_llms, min_consensus_level, and denominator (2/3 vs 2/4). Optionally log if config looks unusual (e.g. only one required LLM). **Do not** change required_llms logic or consensus formula in this plan. |
| **Duplicate / replace** | Verify RED FLAG throttle; Tier 3: replace pending only when needed (5.1, 5.10) | Duplicate blocking too aggressive; allow replacement if entry improved (Issue 5) | **Cursor approach for logic:** "Replace only when needed" stays **Phase 3, one-at-a-time** (same as consol-recommend2 §3.2). **Do not** change duplicate-block condition in Phase 1–2. Throttle verification (and longer window if needed) only in Phase 1. Anthropic’s "allow replacement if entry improved" is covered by "replace only when needed" in Phase 3. |
| **Order of work** | One change at a time; verify trades still open; Tier 1 then 2 then 3 | Don’t implement all 5 issues at once; test fixes one at a time (Part 7) | **Aligned:** One item per deployment where behaviour changes; verification after each. |

### 1.2 Cursor-only (included in plan)

- **RED FLAG throttle verification** (5.1): Confirm throttle is deployed; if RED FLAG still every cycle, consider longer window (e.g. 15 min).
- **Stale opportunity price log throttle** (5.3): First per (pair, direction) per window at INFO; subsequent at DEBUG.
- **Config API log ingest volume** (5.7): Routine successful ingest at DEBUG; 0 chars at DEBUG or throttled.
- **UI DB / file handler** (5.8): Document Streamlit rerun behaviour; optional single init + log once.
- **OANDA log 0 chars** (5.9): Document when OANDA log may be 0 chars; verify OANDA logger writes when expected.

### 1.3 Anthropic-only (included as doc or optional)

- **LLM architecture clarity** (Part 3): Document Tier 1 (ChatGPT, Gemini), Tier 2 (Synthesis), Tier 3 (Claude, Deepseek optional). Doc only; no consensus change.
- **Error handling formalization** (Part 3): Log format for "2/3 primary LLMs active" with per-LLM status. Log-only; no behaviour change.
- **Config versioning / audit / validation** (Part 4): Document or add optional validation (e.g. "unusual: only Gemini required"). No change to config object passed to TradeConfig.
- **Monitoring & metrics** (Part 5): Document key metrics (LLM availability, consensus distribution, trade execution, error rates). Doc only.
- **Success metrics for next session** (Part 8): Use as verification checklist for this plan.

### 1.4 What caused the Feb 25 failure (from CLAUDE.md)

- **Implemented together:** pair blacklist, ORDER_CANCEL_REJECT, duplicate-block log throttle, "Trade not opened" reason, RL DB init once, **consensus ≥ majority of available sources**, staleness 100 pips/1%, **config last updated in UI** (with `updated` passed into config object), docs.
- **Result:** No trades opened; full rollback.
- **Likely culprits:** (1) **Consensus change** altering which opportunities pass; (2) **Config object change** (`TradeConfig.__init__() got an unexpected keyword argument 'updated'`); (3) **max_runs** behaviour (later fixed with reset when no open/pending); (4) **Batching** many behaviour-changing fixes in one deployment.

**Consol-recommend3 avoids:** Any change to consensus formula or min_consensus_level or required_llms logic; any new field in the config object passed to TradeConfig; any change to open_trade() return signature; and batching of execution-path changes. Duplicate-block **logic** (when we block) is not changed in Phase 1–2; only throttle verification and, in Phase 3, "replace only when needed" as a single, isolated change.

---

## 2. Out of scope for this plan (do not implement here)

- Changing **consensus** calculation, **min_consensus_level** semantics, or **required_llms** logic.
- Adding any field to the **config object** passed to `TradeConfig.__init__`. Only **separate** response fields (e.g. `last_updated`) that are **stripped** before building TradeConfig are in scope.
- Changing **duplicate-block logic** (when we block) in Phase 1 or 2. Only **throttle verification** and **replace-only-when-needed** (Phase 3, one-at-a-time) are in scope.
- Changing **open_trade()** return signature.
- **Staleness** rule changes (e.g. 100 pips/1%) or any change that might block opportunities that currently pass.
- **Pair blacklist in market state or consensus.** (EXCLUDED_PAIRS at placement only is already in consol-recommend2.)

---

## 3. Implementation phases

### Phase 0: Investigation (optional, no code change)

**Goal:** Understand config drift and required_llms intent before changing behaviour. Can run in parallel with Phase 1.

| Step | Action | Output |
|------|--------|--------|
| 0.1 | **Config drift:** Determine why "Required LLMs" appears as "gemini" only in some logs (Render config, manual change, or intended). | Short note: intentional or not; if not, restore to intended value (e.g. synthesis, chatgpt, gemini) via config API/UI, not code. |
| 0.2 | **Consensus denominator:** Document what "2/3" vs "2/4" means (e.g. agreeing base LLMs / base LLMs with opportunities for that pair). | One paragraph in USER_GUIDE or CONFIG_GUIDE. |

**Verification:** Report or doc update. No deployment.

---

### Phase 1: Verification and log-only (no execution-path change)

**Goal:** Verify existing throttles, add log throttles and one operational fix (max_runs reset), improve observability. **No change to consensus, config object, or duplicate-block condition.**

**Gate before Phase 1:** Confirm at least one trade still opens when an opportunity passes (e.g. consensus ≥ 2, no duplicate block). If not, fix that first.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 1.1 | **RED FLAG throttle verification** | Cursor 5.1 | Verify deployed Scalp-Engine has RED FLAG throttle (first block per (pair, direction) in 10 min at ERROR; rest DEBUG). If throttle is live but RED FLAG still every cycle, lengthen window to 15 min. Do **not** change when we block. | RED FLAG at most once per window per (pair, direction) at ERROR. |
| 1.2 | **max_runs auto-reset when no position** | Cursor 5.2, Anthropic Issue 4 | When directive is REJECT for `max_runs` and `has_existing_position(pair, direction)` is False, reset run count for that opp_id and re-get directive so engine can retry. Document when run count resets (e.g. on new market state, when position closes, or when no open/pending). | After a trade for (pair, direction) closes/cancels, same opportunity can be retried; "Trade not opened … reason=max_runs" not stuck forever when no position. |
| 1.3 | **Stale opportunity price log throttle** | Cursor 5.3 | First "slightly stale current_price … proceeding with live price" per (pair, direction) in 10–15 min at INFO; subsequent in window at DEBUG. No change to using live price. | Log volume reduced; behaviour unchanged. |
| 1.4 | **Claude billing / credit log** | Cursor 5.6, Anthropic Issue 1 | When all Claude models fail with billing/credit error (e.g. "credit balance is too low"), log one line at WARNING: e.g. "Claude skipped: API credit/billing issue – check Anthropic account." Optional: add to USER_GUIDE that "Claude unavailable" can be due to billing. | Operators can distinguish billing from other failures. |
| 1.5 | **Config API log ingest** | Cursor 5.7 | Log routine successful "Log ingest: component -> filename (N chars)" at DEBUG. When body 0 chars, log at DEBUG or once per component per interval. | Config API logs less noisy. |
| 1.6 | **Documentation (consensus, required_llms, UI, OANDA)** | Cursor 5.4, 5.8, 5.9; Anthropic Part 4 | (1) USER_GUIDE: required_llms, min_consensus_level, denominator (2/3 vs 2/4), base LLMs. (2) USER_GUIDE: UI DB and file handler on Streamlit rerun; optional single init. (3) USER_GUIDE or ops: OANDA log may show 0 chars when no OANDA activity; verify logger if needed. | Docs updated; no execution change. |

**Deployment:** Prefer **one item at a time** (e.g. 1.1, then 1.2, then 1.3…). If 1.2 (max_runs reset) is the only logic change, deploy it alone and verify trades still open and retry works.

**Verification after Phase 1:**  
- Trades still open when opportunity passes.  
- max_runs no longer blocks permanently when no open/pending.  
- Logs: RED FLAG throttled, stale price throttled, Claude billing message when applicable, Config API ingest at DEBUG.

---

### Phase 2: Documentation and optional parser/config

**Goal:** Consensus/config docs, LLM architecture doc, DeepSeek parser fix or explicit documentation. No consensus or config-object change.

**Gate:** Phase 1 verified.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 2.1 | **Consensus and required_llms (detailed)** | Cursor 5.4, Anthropic Issue 3 | In USER_GUIDE or CONFIG_GUIDE: (a) required_llms = which LLMs must be among agreeing; (b) min_consensus_level = minimum agreeing base LLMs; (c) denominator in "2/3" = base LLMs that had opportunities for that pair; (d) base LLMs include chatgpt, gemini, claude, deepseek where applicable. Optional: at config load, log warning if only one required_llm (e.g. "⚠️ Only one required LLM (unusual)"). | Docs clear; optional log only. |
| 2.2 | **LLM architecture and error handling** | Anthropic Part 3 | Document Tier 1 (ChatGPT, Gemini), Tier 2 (Synthesis), Tier 3 (Claude, Deepseek optional). Optionally add one log line per analysis: e.g. "LLM Analysis: 2/3 primary LLMs active; Claude: skipped (billing)." | Doc and/or log; no consensus change. |
| 2.3 | **DeepSeek parser** | Cursor 5.5, Anthropic Issue 2 | **Option A (preferred):** Update DeepSeek prompt to request JSON/machine-readable block (or add fallback JSON extraction from markdown). **Option B:** Add DeepSeek-specific narrative parser. **Option C (if deferred):** Document in USER_GUIDE that DeepSeek is not parsed until format aligned; consensus may use fewer than four base LLMs when DeepSeek enabled. | Either parsed DeepSeek opportunities or clear doc. |
| 2.4 | **Config validation / audit (optional)** | Anthropic Part 4 | Document config versioning/audit ideas; optionally log config load with required_llms and min_consensus so drift is visible. Do **not** change config object or TradeConfig. | Doc and/or log only. |

**Deployment:** 2.1 and 2.2 are doc/log only. 2.3 is one change (parser or doc); test that other LLM parsing is unaffected if parser changed. 2.4 optional.

**Verification after Phase 2:**  
- Docs and logs align with behaviour.  
- If DeepSeek parser changed: "Parsed N opportunities" for DeepSeek in logs when format matches.

---

### Phase 3: One-at-a-time behaviour changes

**Goal:** Replace pending order only when needed. Each item is a **separate** deployment with verification.

**Gate:** Phase 1 and Phase 2 verified.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 3.1 | **Replace pending order only when needed** | Cursor 5.10, Anthropic Issue 5 | Replace a pending order only when entry/stop/target have meaningfully changed (by config or market state) or order is stale (e.g. distance from current price or age beyond threshold). Make thresholds configurable. Implement as **single, isolated** change. | Valid replaces (e.g. "better entry by N pips") still occur; churn from same-param replace decreases; no duplicate-block logic change that blocks legitimate new opportunities. |

**Deployment:** **One item per deployment.** After 3.1: verify trades still open and replace behaviour is correct (better entry allowed, spam reduced).

**Verification after Phase 3:**  
- Trades still open when they should.  
- Pending orders replaced when entry/stop/target meaningfully change or stale; not replaced every cycle with same params.

---

## 4. Verification checklist (after each phase)

- [ ] At least one trade still opens when an opportunity passes (e.g. consensus ≥ 2, no duplicate block for that pair).
- [ ] No `TradeConfig.__init__() got an unexpected keyword argument` or similar config error.
- [ ] Logs: RED FLAG at most once per window per (pair, direction); "Trade not opened" includes reason=…; max_runs not stuck when no position; Claude billing message when applicable.
- [ ] Config API and UI logs not dominated by ingest/sync at INFO (moved to DEBUG where specified).
- [ ] Documentation updated as per phases; no execution regression.

---

## 5. What not to do (summary)

- Do **not** change consensus calculation, min_consensus_level, or required_llms logic.
- Do **not** add fields to the config object passed to TradeConfig; only separate fields stripped before TradeConfig are allowed.
- Do **not** change open_trade() return signature.
- Do **not** change duplicate-block **condition** (when we block) in Phase 1–2; only throttle verification and Phase 3 "replace only when needed."
- Do **not** implement multiple execution-path changes in one deployment; one item at a time for Phase 1.2, 2.3, 3.1.
- Do **not** implement any of the above without your approval.

---

## 6. Summary table: Cursor vs Anthropic → Phase

| Cursor (cursor2) | Anthropic (anthropic2) | Phase | Notes |
|------------------|------------------------|-------|--------|
| 5.1 RED FLAG verify | — | 1.1 | Verify/lengthen window only |
| 5.2 max_runs reset | Issue 4 max_runs | 1.2 | Reset when no position; document |
| 5.3 Stale price throttle | — | 1.3 | Log throttle |
| 5.6 Claude billing log | Issue 1 Claude credits | 1.4 | One WARNING line + optional doc |
| 5.7 Config API ingest | — | 1.5 | DEBUG |
| 5.4, 5.8, 5.9 Docs | Part 4 config | 1.6, 2.1 | Consensus, UI, OANDA docs |
| 5.4 required_llms doc | Issue 3 config | 2.1 | Doc + optional validation log |
| — | Part 3 LLM architecture | 2.2 | Doc and/or log |
| 5.5 DeepSeek parser | Issue 2 DeepSeek | 2.3 | Parser or doc |
| — | Part 4 config audit | 2.4 | Optional doc/log |
| 5.10 Replace when needed | Issue 5 duplicate | 3.1 | One-at-a-time |

---

## 7. Recommended implementation order

1. **Phase 0** (optional): Investigate config drift; document consensus denominator.
2. **Phase 1.1**: RED FLAG throttle verification (no logic change).
3. **Phase 1.2**: max_runs auto-reset when no position — **single deployment**, then verify trades open and retry works.
4. **Phase 1.3–1.6**: Stale price throttle, Claude billing log, Config API ingest DEBUG, documentation (can batch if desired; all low risk).
5. **Phase 2**: Documentation (2.1, 2.2); then DeepSeek (2.3) as one change; optional 2.4.
6. **Phase 3.1**: Replace only when needed — **single deployment**, then verify.

**No changes to the system have been implemented without your approval.**
