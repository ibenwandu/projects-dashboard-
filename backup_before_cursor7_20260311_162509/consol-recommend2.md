# Consolidated Implementation Plan (v2) — consol-recommend2.md

**Purpose:** Merge recommendations from **Cursor** (`Scalp-Engine/suggestions from cursor1.md`) and **Anthropic** (`suggestions_from_anthropic1.md`) into a single, safe implementation plan that improves the trading system while **avoiding the failures of the Feb 25 implementation** (see `CLAUDE.md` Session Feb 25, 2026).

**Status:** Plan only. No code or config changes until you approve each phase or item.

**References:**
- Cursor: `Scalp-Engine/suggestions from cursor1.md`
- Anthropic: `suggestions_from_anthropic1.md`
- Failure context: `CLAUDE.md` (Session Feb 25, 2026 — consolidated implementation and rollback)

---

## 1. Comparison: Cursor vs Anthropic

### 1.1 Where both agree

| Topic | Cursor | Anthropic | Consolidated stance |
|-------|--------|-----------|----------------------|
| **RL / Enhanced DB init** | Init once per process; log once (Tier 1) | Move DB init outside opportunity loop; single connection per cycle | **Same fix:** init once per process/cycle, reuse connection, log init once. |
| **Duplicate-block behaviour** | Throttle RED FLAG *log* only (first block ERROR, repeats DEBUG); do not change block logic | Duplicate logic “too aggressive”; decide what duplicate *means* before changing logic | **Cursor approach for now:** change only *logging* (throttle). Do **not** change when we block. Anthropic’s “define duplicate strategy” is a **decision gate** before any logic change. |
| **Consensus / config** | Do not change consensus formula or config object in a batch; any “config last updated” must be a separate field, stripped before TradeConfig | 4-LLM mismatch (Claude/Deepseek never in opportunities); clarify architecture before consensus changes | **Aligned:** no consensus or required_llms change in this plan. Investigation (Anthropic) can run in parallel; implementation does not depend on it. |
| **Config object** | Do not add `updated` to object passed to TradeConfig; engine must strip it | (Config breakage noted in CLAUDE.md) | **Aligned:** config “last updated” only via separate API field; engine strips before building TradeConfig. |
| **Order of work** | One change at a time; verify trades still open | Fix DB first, then decide consensus/duplicate; “investigate first” option | **Aligned:** Phase 1 = infrastructure + log-only (DB init + log throttles). No execution-path or consensus changes in Phase 1. |

### 1.2 Cursor-only (included in plan)

- RED FLAG duplicate-block **log** throttle (no logic change).
- “Trade not opened” **reason in same log line only** (no `open_trade` return change).
- Config API routine sync logs at DEBUG.
- ENTRY POINT HIT throttle (log once per opportunity per window, or DEBUG after first).
- UI LogSync success at DEBUG.
- Documentation (UI DB ephemeral, Streamlit session, config timestamp).
- Config “last updated” as separate API field + engine strip + UI display.
- Broker exclude list **at order placement only** (e.g. EXCLUDED_PAIRS).
- ORDER_CANCEL_REJECT state handling (Phase 3, one-at-a-time).
- Replace pending order only when needed (Phase 3, one-at-a-time).
- Claude failure logging / optional skip (Phase 3).
- Log 404 / path alignment (Phase 3).

### 1.3 Anthropic-only (included as investigation / gates, not as code in this plan)

- **4-LLM architecture investigation:** Why Claude & Deepseek never appear in opportunities; are they intentional (secondary) or a bug? This is **not** implemented in consol-recommend2; it is a **recommended investigation** that should inform any future consensus work.
- **Consensus strategy decision:** Explicit choice of consensus model (e.g. min 1 vs min 2, or % of available sources). **Out of scope** for this implementation plan; no consensus formula or required_llms change.
- **Duplicate strategy decision:** What should “duplicate” mean (replace if better price vs block vs skip)? **Out of scope** for logic change here; only log throttle is in scope.
- **Verification steps:** Add logging to understand why Trade-Alerts sends 1–2 LLMs, why DB init was in loop, etc. Can be done as part of Phase 0 or in parallel; not a prerequisite for Phase 1.

### 1.4 What caused the Feb 25 failure (from CLAUDE.md)

- Implementation included: pair blacklist, ORDER_CANCEL_REJECT handling, duplicate-block log throttle, “Trade not opened” reason, **RL DB init once**, **consensus ≥ majority of available sources**, staleness 100 pips/1%, **config last updated in UI** (with `updated` passed into config object), docs.
- **Result:** No trades opened; full rollback.
- **Likely culprits:** (1) **Consensus change** (e.g. “majority of available sources”) altering which opportunities pass; (2) **Config object change** (`TradeConfig.__init__() got an unexpected keyword argument 'updated'`); (3) **max_runs** behaviour (fixed later with “reset run count when no open/pending order”); (4) implementing many behaviour-changing fixes in one deployment.

**Consol-recommend2 avoids:** Any change to consensus formula or required_llms; any new field in the config object the engine maps to TradeConfig; any change to `open_trade()` return signature; and batching of execution-path changes.

---

## 2. Out of scope for this plan (do not implement here)

- Changing **consensus** calculation, **min_consensus_level** semantics, or **required_llms** logic.
- Adding any field to the **config object** that is passed into `TradeConfig.__init__` (e.g. `updated`). Only **separate** response fields (e.g. `meta.updated`) that are **stripped** before building TradeConfig are in scope.
- Changing **duplicate-block logic** (when we block). Only **log throttling** for the same duplicate event is in scope.
- Changing **open_trade()** return signature (e.g. adding a second return value for reject reason). Only adding the reason to the **log message** is in scope.
- **Staleness** rule changes (e.g. 100 pips/1%) or any change that might block opportunities that currently pass.
- **Pair blacklist in market state or consensus.** Only an **exclude list at order placement** (skip + log) is in scope.

---

## 3. Implementation phases

### Phase 0: Investigation (optional, non-blocking)

**Goal:** Understand root causes before touching consensus or duplicate logic. Can run in parallel with Phase 1.

| Step | Action | Owner / note |
|------|--------|----------------|
| 0.1 | **4-LLM architecture:** Confirm whether Claude & Deepseek are meant to be in opportunities. Check Trade-Alerts: `main.py`, `llm_analyzer.py`, `market_bridge.py` — are all 4 base LLMs called and included in market_state? | Investigation only; no code change to consensus in this plan. |
| 0.2 | **Consensus strategy:** Document intended model (e.g. min 1 vs min 2, or % of available sources). Decision only; no implementation in consol-recommend2. | Informs future work. |
| 0.3 | **Duplicate strategy:** Document intended behaviour (replace if better price vs block vs skip). Decision only; no logic change in this plan. | Informs future work. |

**Verification:** Report or doc update. No deployment.

---

### Phase 1: Infrastructure and log-only (no execution-path change)

**Goal:** Fix DB init, reduce log noise, improve observability. **No change to when or how trades are opened.**

**Gate before Phase 1:** Confirm current system opens at least one trade when an opportunity passes (e.g. EUR/GBP with consensus ≥ 2). If not, fix that first before applying Phase 1.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 1.1 | **RL / Enhanced DB init** | Cursor + Anthropic | Initialise RL (or Enhanced RL) DB once per process (or per cycle); reuse same connection for all opportunity checks. Log “Enhanced RL database initialized” only on first use (or at startup). | After deploy: “Enhanced RL database initialized” appears at most once per process start; no init per opportunity. |
| 1.2 | **RED FLAG duplicate-block log** | Cursor | On first block for (pair, direction) in a time window (e.g. 10–15 min), log at ERROR (RED FLAG). For subsequent blocks for same (pair, direction) in that window, log at DEBUG or do not log. Do **not** change the condition that triggers the block. | Same duplicate still blocked; log line appears once per window per pair/direction at ERROR. |
| 1.3 | **“Trade not opened” reason** | Cursor | When a trade is not opened, set a reason code (e.g. `max_runs`, `consensus_too_low`, `duplicate_blocked`, `validation_failed`, `oanda_reject`) and include it in the **same** log line (e.g. “Trade not opened for GBP/JPY BUY: reason=consensus_too_low”). Do **not** change return signature of `open_trade()`. | Log line contains “reason=…”; callers unchanged. |
| 1.4 | **Config API sync logs** | Cursor | Log “Trade states updated in memory” (and optionally “Trade states saved to disk”) at DEBUG for routine successful POST /trades. Keep INFO for config changes, errors, or first load. | Config API logs less noisy; behaviour unchanged. |
| 1.5 | **ENTRY POINT HIT (Trade-Alerts)** | Cursor | After first ENTRY POINT HIT for (pair, direction) in a time window (e.g. until next analysis), log subsequent hits at DEBUG or do not log. Ensure no downstream logic depends on every hit at INFO. | Trade-Alerts logs less noisy; entry logic unchanged. |
| 1.6 | **UI LogSync** | Cursor | Log successful “[LogSync] ui -> config-api OK” at DEBUG (or only on failure / every N-th success). | UI logs less noisy. |
| 1.7 | **Documentation** | Cursor | (1) USER_GUIDE or deployment: UI DB (scalping_rl.db) is created on first use and may be recreated on new deploys/restarts; do not rely on it for critical state. (2) Troubleshooting: Streamlit “Session already connected” can appear with multiple tabs; recommend one tab per session or refresh. (3) Document that config API may expose “last updated” in a separate field; UI can show it; engine must not pass it into TradeConfig. | Docs updated; no code path change. |

**Deployment:** Prefer **one item at a time** (e.g. 1.1 first, then 1.2, etc.), or a single batch of 1.1–1.7 if you accept the combined risk.

**Verification after Phase 1:**  
- Trades still open when an opportunity passes (e.g. EUR/GBP BUY with consensus ≥ 2).  
- Logs readable: DB init once, RED FLAG once per window per pair, “Trade not opened” with reason, less sync/ENTRY/LogSync noise.

---

### Phase 2: Additive, low-risk (isolated changes)

**Goal:** Add config “last updated” visibility and broker exclude list at placement only, without changing consensus or market state.

**Gate:** Phase 1 verified (trades open, logs sane).

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 2.1 | **Config “last updated”** | Cursor | (1) Config API: Include `last_updated` (or `updated`) in the response as a **separate** top-level or nested field (e.g. `meta.updated`), **not** inside the object mapped to TradeConfig. (2) Engine (and any other config consumer): When building TradeConfig from API response, **strip or ignore** `updated` / `last_updated` so it is never passed to `TradeConfig.__init__`. (3) UI: Read the separate field and display “Config last updated: &lt;timestamp&gt;” in Configuration tab or footer. | Engine does not receive `updated` in config object; UI shows timestamp; no TradeConfig errors. |
| 2.2 | **Broker exclude list (placement only)** | Cursor | Immediately before calling the broker to place an order, check the instrument against an exclude list (e.g. env `EXCLUDED_PAIRS` or config). If the pair is in the list, skip placement, log once (e.g. “Pair not tradeable on broker: USD/CNY”), and do not retry for that opportunity in the same cycle. Do **not** filter opportunities out of market state or change consensus. | Orders for excluded pairs are not sent; other opportunities unchanged. |

**Deployment:** One item at a time (2.1 then 2.2, or vice versa).

**Verification after Phase 2:**  
- Trades still open for non-excluded pairs.  
- Config “last updated” visible in UI; engine config load unchanged.  
- Excluded pair (e.g. USD/CNY if in list) never gets an order; one log line per skip.

---

### Phase 3: Defer or one-at-a-time with verification

**Goal:** ORDER_CANCEL_REJECT handling, replace-only-when-needed, Claude failure handling, log 404 alignment. Each item is a **separate** change with verification that trades still open and logs usable.

**Gate:** Phase 1 and Phase 2 verified.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 3.1 | **ORDER_CANCEL_REJECT** | Cursor | When the engine (or sync) sees ORDER_CANCEL_REJECT from the broker, treat the order as still active (or filled) in local state; do not assume cancelled. Implement in a single, isolated change. | After a rejected cancel, local state and UI do not assume order is cancelled; optional test with a cancel that is rejected. |
| 3.2 | **Replace pending order only when needed** | Cursor | Only replace a pending order when entry/stop/target have meaningfully changed or the order is stale (e.g. distance from current price or age beyond threshold). Make thresholds configurable. Implement as a single change. | Valid replaces (e.g. “better entry”) still occur; churn from same-param replace decreases. |
| 3.3 | **Claude analysis failures (Trade-Alerts)** | Cursor + Anthropic | When Claude fails or returns no opportunities, log clearly (e.g. “Claude unavailable / no opportunities; using other LLMs”). Optionally skip Claude for that run and compute consensus over remaining sources. Do not silently change consensus. Implement in Trade-Alerts only. | Consensus and engine behaviour unchanged or only improved (e.g. no silent “no opinion” for Claude). |
| 3.4 | **Log 404 / paths** | Cursor | Ensure log paths and patterns used by the Config API (e.g. for GET /logs/engine, GET /logs/oanda) match where engine and oanda writers write. Document expected paths. If logs are optional, document and have UI show “Logs not available” on 404. | Log endpoints return 200 when files exist; 404 with clear message when not; docs updated. |

**Deployment:** **One item per deployment** (e.g. 3.1 only, verify, then 3.2, etc.).

**Verification after each item:** Trades still open; no new errors in logs.

---

## 4. Verification checklist (after each phase)

- [ ] At least one trade still opens when an opportunity passes (e.g. EUR/GBP BUY with consensus ≥ 2 and no duplicate block).
- [ ] No new exception in engine or UI (e.g. no `TradeConfig.__init__() got an unexpected keyword argument 'updated'`).
- [ ] Logs are usable: DB init not per-opportunity; RED FLAG not every cycle for same pair; “Trade not opened” includes reason; sync/ENTRY/LogSync noise reduced.
- [ ] Config load and trade state sync unchanged (or improved) from engine perspective.

---

## 5. Summary table

| Phase | Items | Execution path change? | Consensus / config object change? |
|-------|-------|------------------------|-----------------------------------|
| 0 | Investigation (4-LLM, consensus strategy, duplicate strategy) | No | No |
| 1 | DB init once, RED FLAG log throttle, “Trade not opened” reason (log), Config API / ENTRY / LogSync log level, docs | No | No |
| 2 | Config last updated (separate field + strip + UI), broker exclude at placement only | Placement skip for excluded pairs only | No |
| 3 | ORDER_CANCEL_REJECT, replace-only-when-needed, Claude logging/skip, log 404 | Yes, per item | No |

---

## 6. What not to do (reminder)

- Do **not** change consensus calculation or required_llms in this plan.
- Do **not** add fields to the config object that the engine maps to `TradeConfig` without stripping them before `TradeConfig.__init__`.
- Do **not** change the duplicate-block **logic** (only log throttling is in scope).
- Do **not** change `open_trade()` return signature for reject reason (only add reason to log).
- Do **not** implement multiple execution-path or config-structure changes in one deployment without verification gates.
- Do **not** implement any of the above without your approval.

---

## 7. Next steps

1. Review this plan and approve Phase 0 (optional), Phase 1, Phase 2, and/or Phase 3.
2. Run Phase 0 if you want the investigation to inform future consensus/duplicate work.
3. Implement Phase 1 (preferably one item at a time); verify after each item or after the full phase.
4. Implement Phase 2 after Phase 1 is verified; verify after Phase 2.
5. Implement Phase 3 items **one at a time**, with verification that trades still open after each.

**No changes have been implemented without your approval.**
