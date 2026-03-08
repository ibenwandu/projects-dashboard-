# Consolidated Implementation Plan (v4) — consol-recommend4.md

**Purpose:** Merge recommendations from **Cursor** (`Scalp-Engine/suggestions from cursor4.md`) and **Anthropic** (`suggestions_from_anthropic4.md`) into a single implementation plan that improves the trading system while **avoiding the failures of previous implementations** (see `CLAUDE.md` Sessions Feb 25–28 and `personal/cursor_works.md`).

**Status:** Plan only. **No implementation** without explicit approval. Implement one change at a time; verify trades still open after each.

**References:**
- Cursor: `Scalp-Engine/suggestions from cursor4.md`
- Anthropic: `suggestions_from_anthropic4.md`
- Failure context: `CLAUDE.md` (Feb 25 rollback; consol-recommend2/3; do-not-do list)
- Backup/context: `personal/cursor_works.md`

---

## 1. Comparison: Cursor4 vs Anthropic4

### 1.1 Where both agree (aligned recommendations)

| Topic | Cursor4 | Anthropic4 | Consolidated stance |
|-------|---------|------------|---------------------|
| **Stop loss / trailing SL** | Verify from logs + OANDA; optional close-event log; no SL logic change here (5.5) | Trailing SL unverified; EUR/JPY loss exceeds SL; verify implementation (1.1, 1.3) | **Verify first:** Confirm trailing SL is called and modifies OANDA orders; document. Optional: one INFO log per trade close (pair, direction, exit_reason, final P&L). **Do not** change SL logic in same batch as other execution changes. |
| **Sync / orphan** | Doc verification procedure; optional orphan WARNING log (5.4) | Full position reconciliation audit; orphan detection (3.1, Part 5) | **Doc + optional check:** Document how to verify GET /trades vs OANDA; optional periodic orphan check (log WARNING if OANDA has position not in engine). No auto-correction. |
| **max_runs blocking** | Already implemented (cursor3); verify (—) | Verify consol-recommend3 Phase 1.2; still failing in logs (2.1) | **Verify only:** Confirm max_runs auto-reset is in execution path when `has_existing_position()` is False; trace and test retry after close/cancel. If not working, fix as single, isolated change. |
| **Parser / consensus visibility** | Document parser failure impact; optional parsed-count log (5.2) | DeepSeek parser 0 opportunities; consensus denominator wrong "X/4" (2.3, 2.5) | **Display + doc:** (1) Show consensus as "X / available_llm_count" (display only; do **not** change formula or min_consensus_level logic). (2) Document parser failure impact. (3) Optional: log "Parsed opportunities: chatgpt=N, gemini=M, …". (4) DeepSeek: fix parser or document; do not change consensus formula. |
| **Trading hours** | Document enforcement and how to verify (5.7) | Verify TradingHoursManager in execution path (4.1) | **Verify + doc:** Confirm `can_open_new_trade()` is called before placing orders; document hours and how to verify in logs. |
| **RL visibility** | Already in cursor3; verify from Render logs (5.6) | RL efficacy uncertain with LLM failures (3.3) | **Verify + optional:** Check Render logs for LEARNING CYCLE / WEIGHTS UPDATED; document. Optional: daily_learning handling of missing LLMs (log only; no formula change in Phase 1–2). |
| **Replace-only-when-needed** | Already implemented (consol-recommend3) (—) | Verify REPLACE_ENTRY_MIN_PIPS / REPLACE_SL_TP_MIN_PIPS (2.6) | **Verify only:** Confirm thresholds are used in _review_and_replace_pending_trades(); no change if working. |
| **One change at a time** | Do not batch execution-path changes (4) | Test one fix at a time (Part 10) | **Aligned:** One behaviour-changing fix per deployment; verify trades still open after each. |

### 1.2 Cursor-only (included in plan)

| Topic | Cursor4 | Consolidated action |
|-------|--------|---------------------|
| **JPY limit order price to OANDA** | CRITICAL: entry "1.560" vs TP "157.500" for USD_JPY (5.1) | **Phase 1 critical:** Locate order builder; fix JPY price scale so entry and TP use same convention (e.g. 156.xxx); add sanity check before send; verify with OANDA transaction log. Single, isolated change. |
| **Market state timestamp** | Document when timestamp updates (5.3) | Phase 2 or 3: USER_GUIDE sentence on market state timestamp and staleness. |
| **OANDA app log empty** | Document; optional per-request log (5.8) | Phase 3: Document; optional one log line per order request for traceability. |

### 1.3 Anthropic-only (included as investigation, doc, or optional)

| Topic | Anthropic4 | Consolidated action |
|-------|------------|---------------------|
| **Premature / manual trade closures** | CRITICAL: 80% manual closes; identify cause (1.2, 3.2) | **Phase 0 or 1:** Investigate only: search for MARKET_ORDER + TRADE_CLOSE; determine if UI, risk manager, or orphan detection. **No fix** until root cause known. Then single, isolated fix (e.g. disable manual close in AUTO mode). |
| **Claude API credits** | CRITICAL: replenish or disable (2.2) | **Phase 0 (immediate):** Operator action: check Anthropic Dashboard; replenish or disable Claude in config. No code change for replenish; if disabling, config-only. |
| **Position sizing** | MEDIUM: document and audit formula (1.4) | Phase 3: Document position sizing formula (fixed / ATR / account %); audit compliance with risk standards. Doc only unless audit finds bug. |
| **Trade sync frequency** | MEDIUM: reconciliation audit (3.1) | Phase 3: Audit GET /trades vs OANDA positions; document procedure. Optional: event-driven sync (out of scope for initial phases). |
| **Log spam** | MEDIUM: DB init 50+ times (4.2) | Verify consol-recommend2/3 "init once" is deployed; if still spammy, move to DEBUG. |
| **Config drift / manual vs AUTO** | Part 10: clarify manual vs automated | Phase 2 doc: USER_GUIDE note that in AUTO mode manual close should not occur; document how to confirm mode. |

### 1.4 What caused past failures (do not repeat)

From **CLAUDE.md** and **cursor_works.md**:

- **Feb 25 rollback:** Batch implementation (pair blacklist, ORDER_CANCEL_REJECT, duplicate throttle, "Trade not opened" reason, RL DB init once, **consensus ≥ majority**, staleness 100 pips/1%, **config "last updated" with `updated` in config object**). Result: no trades opened. Likely culprits: (1) **Consensus formula change**; (2) **Config object** (`TradeConfig.__init__() got an unexpected keyword argument 'updated'`); (3) **max_runs** behaviour; (4) **Batching** many fixes in one deploy.
- **consol-recommend2/3:** Avoided recurrence by: no consensus formula or required_llms logic change; no new field in config passed to TradeConfig (only separate `last_updated` stripped before TradeConfig); no `open_trade()` return signature change; one execution-path change at a time.

**consol-recommend4 continues to avoid:**
- Changing **consensus calculation**, **min_consensus_level** semantics, or **required_llms** logic (display-only changes allowed, e.g. "X / available_llm_count").
- Adding any field to the **config object** passed to `TradeConfig.__init__` without stripping it first.
- Changing **open_trade()** return signature.
- Implementing multiple execution-path or config changes in one deployment.
- Changing **duplicate-block condition** (when we block); only verification and existing replace-only-when-needed behaviour.

---

## 2. Out of scope for this plan

- Changing **consensus formula** or **required_llms** logic. **Display-only** consensus (e.g. show "2/3" when 3 LLMs available) is in scope.
- Adding fields to the **config object** passed to `TradeConfig` without stripping before `TradeConfig.__init__`.
- Changing **open_trade()** return signature.
- Changing **when** duplicates are blocked (only verify and replace-only-when-needed as already in consol-recommend3).
- **Staleness** rule changes (e.g. 100 pips/1%) that could block opportunities that currently pass.
- Pair blacklist in market state or consensus (EXCLUDED_PAIRS at placement only remains).

---

## 3. Implementation phases

### Phase 0: Immediate actions (no execution-path change)

**Goal:** Operator actions and investigation only. No code that affects when or how trades open.

| # | Item | Source | Action | Verification |
|---|------|--------|--------|--------------|
| 0.1 | **Claude API** | Anthropic 2.2 | Check Anthropic Dashboard → Plans & Billing. Replenish credits **or** disable Claude in config. | Claude either working or disabled; no repeated billing errors in logs. |
| 0.2 | **Premature closures – investigate** | Anthropic 1.2, 3.2 | Search code for MARKET_ORDER + TRADE_CLOSE / manual close. Identify: UI button, risk manager, orphan detection, or bug. Document finding. | Short report: what is closing trades (and from where). No fix yet. |
| 0.3 | **max_runs – verify in code** | Anthropic 2.1 | Confirm consol-recommend3 Phase 1.2 is in codebase: `reset_run_count(opp_id)` when REJECT for max_runs and `has_existing_position()` False; re-get directive. If missing or not in path, note for Phase 1. | Yes/no: reset logic present and on execution path. |

**Deployment:** None. Output: operator decision on Claude; investigation note on closures; yes/no on max_runs.

---

### Phase 1: Critical fixes (one at a time)

**Goal:** Fix critical execution flaws. **One item per deployment;** verify trades still open after each.

**Gate:** At least one trade opens when an opportunity passes (consensus ≥ 2, no duplicate block). If not, fix that first.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 1.1 | **JPY limit order price to OANDA** | Cursor4 5.1 | Locate where limit order **price** is set for OANDA (Scalp-Engine order builder / OANDA client). For JPY pairs (e.g. USD_JPY), ensure entry price uses same scale as TP/SL (e.g. 156.xxx not 1.56). Add sanity check (e.g. JPY pair and price &lt; 10 → ERROR and do not send). Verify with oanda_transactions_*.json: new USD_JPY LIMIT_ORDER must show entry in 15x.xx range. | OANDA transaction history shows correct entry price for USD_JPY (and GBP_JPY if used). |
| 1.2 | **max_runs auto-reset (fix or verify)** | Cursor4, Anthropic 2.1 | If Phase 0.3 found reset missing or not on path: implement or fix so that when directive is REJECT for `max_runs` and `has_existing_position(pair, direction)` is False, reset run count for that opp_id and re-get directive. If already correct, verify with test: place then cancel order for a pair, then retry same pair. | Same (pair, direction) can be retried after order is gone; no permanent "reason=max_runs" when no position. |
| 1.3 | **Premature closures – fix (after 0.2)** | Anthropic 1.2, 3.2 | Based on Phase 0.2 finding: single, isolated fix. Examples: (a) If UI: disable or hide manual close in AUTO mode. (b) If risk manager: add config to disable auto-close or narrow conditions. (c) If orphan detection: do not close recent trades (e.g. &lt; 5 min). Do **not** guess; fix only after root cause known. | In AUTO mode, no manual closures; trades close by SL/TP or intended logic. |
| 1.4 | **Trailing SL – verify** | Cursor4 5.5, Anthropic 1.1, 1.3 | Verify `_update_trailing_stop()` (or equivalent) is called in main loop and modifies OANDA orders. Check direction (SL up for longs, down for shorts). If not implemented or wrong, fix as **single** change. Optional: one INFO log per trade close (pair, direction, exit_reason, final P&L) for audit. | Trailing SL updates visible in OANDA or logs; no change to SL logic in same deploy as 1.1–1.3. |

**Order:** Implement 1.1 first (JPY price), verify with transaction log, then 1.2, then 1.3 (after 0.2), then 1.4. Do not combine 1.1 with 1.2/1.3/1.4 in one deploy.

---

### Phase 2: High-priority (display, doc, parser, verify)

**Goal:** Consensus display, documentation, DeepSeek parser or doc, trading hours and replace-threshold verification. No consensus **formula** or config-object change.

**Gate:** Phase 1 critical items verified.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 2.1 | **Consensus denominator display** | Anthropic 2.5, Cursor4 5.2 | Show consensus as "X / available_llm_count" where available_llm_count = LLMs that contributed opportunities (or base_llms count for that pair). **Display only;** do not change min_consensus_level or required_llms logic. Apply in Trade-Alerts, Scalp-Engine, and UI where consensus is shown. | User sees e.g. "2/3" when 3 LLMs available, not "2/4" when Claude/DeepSeek missing. |
| 2.2 | **Parser failure / parsed-count log** | Cursor4 5.2 | Document in USER_GUIDE: when an LLM returns 0 parsed opportunities, that LLM contributes 0 to consensus for that run. Optional: one log line per analysis "Parsed opportunities: chatgpt=N, gemini=M, synthesis=P, deepseek=Q". | Docs and/or log; no formula change. |
| 2.3 | **DeepSeek parser** | Anthropic 2.3, Cursor4 5.2 | **Option A:** Fix parser (prompt for JSON or add narrative parser). **Option B:** Document that DeepSeek is not parsed until format aligned. One change; test other LLMs unaffected. | Either DeepSeek opportunities parsed or clear doc. |
| 2.4 | **Trading hours – verify** | Cursor4 5.7, Anthropic 4.1 | Confirm `TradingHoursManager.can_open_new_trade()` is called before placing orders. Document in USER_GUIDE: hours (e.g. 01:00–21:30 UTC weekdays), weekend shutdown, and how to verify in logs. | Log or doc confirms enforcement; optional test outside hours. |
| 2.5 | **Replace-only-when-needed – verify** | Anthropic 2.6 | Confirm REPLACE_ENTRY_MIN_PIPS and REPLACE_SL_TP_MIN_PIPS are used in _review_and_replace_pending_trades(); no replacement when change &lt; threshold. | No change if already working; otherwise single fix. |
| 2.6 | **Market state timestamp / staleness** | Cursor4 5.3 | Document: market state timestamp updates when Trade-Alerts (or API) POSTs; "no change" means no new POST. Optional: log warning when state older than e.g. 4 hours. | USER_GUIDE updated. |

**Deployment:** 2.1 is display-only (low risk). 2.2, 2.4, 2.6 doc/log. 2.3 one change (parser or doc). 2.5 verify only.

---

### Phase 3: Medium-priority (docs, audit, optional log)

**Goal:** Documentation, position sizing, sync/orphan procedure, RL visibility, log volume. No execution logic change unless audit finds a bug.

| # | Item | Source | What to do | Verification |
|---|------|--------|------------|--------------|
| 3.1 | **Sync / orphan procedure** | Cursor4 5.4, Anthropic 3.1 | Document in USER_GUIDE: (a) GET /trades vs OANDA positions by pair/direction; (b) candidate orphan = OANDA position with no match in GET /trades; (c) use Manual logs (scalp-engine Active + oanda_transactions_*.json) to cross-check. Optional: engine logs WARNING once per (pair, direction) per window when OANDA position not in engine state. | Doc and/or optional log; no auto-correction. |
| 3.2 | **Position sizing** | Anthropic 1.4 | Document position sizing formula (fixed / ATR / account %); max size; compliance with e.g. 1–2% risk per trade. Audit only; no code change unless audit finds defect. | USER_GUIDE or CONFIG doc. |
| 3.3 | **RL with partial LLM failure** | Anthropic 3.3 | Optional: in daily_learning or logging, record which LLMs were available when recommendation was made; optional log of outcome evaluation. Do not change weight formula in this phase. | Better visibility; no formula change. |
| 3.4 | **Log spam** | Anthropic 4.2 | Verify "Enhanced RL database initialized" and similar appear only once per process (consol-recommend2/3). If still repeated, move to DEBUG. | Log volume reduced. |
| 3.5 | **OANDA app log / request trace** | Cursor4 5.8 | Document that Oanda app log may be empty; use oanda_transactions_*.json for broker-side checks. Optional: one INFO line per order request (pair, units, price, SL, TP) from OANDA client. | Doc and/or optional log. |
| 3.6 | **AUTO mode / manual close** | Anthropic Part 10 | USER_GUIDE: in AUTO mode, manual close should not occur; how to confirm mode and closure source. | Doc only. |

---

### Phase 4: Monitoring and validation (ongoing)

**Goal:** Continuous checks; no code change required for "plan" beyond what is already agreed.

| # | Item | Source | Action |
|---|------|--------|--------|
| 4.1 | **Closure monitoring** | Anthropic Part 7 | Track % of trades closed by SL/TP vs manual; alert if manual &gt; 5% in AUTO mode. |
| 4.2 | **Win rate / success** | Anthropic Part 9 | Target 40%+ win rate before live; stop if &lt;20% for 5 days. |
| 4.3 | **LLM health** | Anthropic Part 7 | Track which LLMs available each cycle; optional alert if Claude/DeepSeek down &gt;1 hour. |

---

## 4. Verification checklist (after implementation)

- [ ] At least one trade still opens when an opportunity passes (consensus ≥ 2, no duplicate block).
- [ ] No `TradeConfig.__init__() got an unexpected keyword argument`.
- [ ] OANDA USD_JPY (and GBP_JPY if used) LIMIT_ORDER entry price in correct range (e.g. 156.xxx).
- [ ] max_runs: same (pair, direction) can be retried after order closed/cancelled.
- [ ] Premature closures: root cause identified and single fix applied; AUTO mode has no unintended manual closes.
- [ ] Trailing SL: verified in code and/or OANDA; optional close-event log present.
- [ ] Consensus display: shows X / available_llm_count (e.g. 2/3).
- [ ] Trading hours: enforced and documented.
- [ ] Replace-only-when-needed: thresholds verified in use.
- [ ] Docs: USER_GUIDE updated for sync/orphan, market state timestamp, position sizing, AUTO mode.

---

## 5. What not to do (summary)

- Do **not** change consensus **formula**, min_consensus_level semantics, or required_llms **logic** in a batch with other changes. Display-only denominator is allowed.
- Do **not** add fields to the config object passed to `TradeConfig` without stripping before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- Do **not** implement multiple execution-path or config changes in one deployment.
- Do **not** fix premature closures without identifying root cause first.
- Do **not** implement any phase without your approval.

---

## 6. Success criteria (before live trading)

From Anthropic4 Part 9, adapted:

1. 100% stop loss coverage (verify every trade has SL).
2. Premature closures resolved (0% unintended manual closures in AUTO mode).
3. max_runs blocking fixed (same pair can be retried after closure).
4. Trailing SL verified working (or explicitly documented if not used).
5. JPY (and any similar) order price correct at OANDA.
6. Claude API working or properly disabled.
7. DeepSeek parser working or documented as disabled.
8. Win rate ≥40% in demo with new fixes (stretch).
9. 10+ consecutive profitable days in demo (stretch).

---

**Document version:** 4.0  
**Created:** Mar 2, 2026  
**Inputs:** suggestions from cursor4.md, suggestions_from_anthropic4.md, CLAUDE.md, cursor_works.md  
**Status:** Plan only; no implementation without approval.
