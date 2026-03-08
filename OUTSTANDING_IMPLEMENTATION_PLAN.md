# Implementation Plan: All Outstanding Issues
## From Research (`personal/research/`) and Trading System Improvement Plan

**Created:** March 6, 2026  
**Source:** `personal/research/` (Exit Strategy, Trailing SL, Position Sizing), `TRADING_SYSTEM_IMPROVEMENT_PLAN.md`, `Trade-Alerts/improvementplan.md`  
**Constraints:** cursor_works.md (no consensus/formula/required_llms change; no new TradeConfig fields without stripping; no `open_trade()` signature change; one execution-path change at a time).

---

## 1. Current State vs Research (What’s Done vs Outstanding)

### Already implemented (do not re-implement)

| Area | Status | Where |
|------|--------|--------|
| ATR_TRAILING with OrderCreate TRAILING_STOP_LOSS | Done | cursor5/6, Part 16 |
| Min profit for trailing (1 pip) | Done | Part 9 |
| Fix 4: ATR_TRAILING min age 120s + OANDA P/L gate | Done | Part 16, improvementplan Fix 4 |
| ALREADY_EXISTS for trailing stop | Done | cursor6 |
| max_runs reset (legacy key) | Done | improvementplan Fix 1 |
| MACD close guarded (sl_type == MACD_CROSSOVER) | Done | improvementplan Fix 2 |
| JPY MARKET sanity check | Done | improvementplan Fix 3 |
| No pending when pair has open | Done | Part 17 + hardening (560a98c) |
| Duplicate cleanup (pair, direction) + final gate | Done | Parts 10, 15 |
| max_daily_loss check (absolute) | Exists | auto_trader_core: max_daily_loss, check before open |
| base_position_size / units from config | Exists | auto_trader_core: base_size × multiplier |
| RiskManager in src/risk_manager.py | Exists | Different API; used in legacy_minimal_engine, not main scalp path |

### Outstanding (to implement)

- **Phase 0 (docs):** ATR in market_state confirmation; document target exit behaviour in USER_GUIDE; add research index link.
- **Phase 1 (risk/sizing):** Position size from research formula in main open path; daily loss as 2% of account; circuit breaker (5 consecutive losses) in main open path.
- **Phase 2 (trailing/breakeven):** Breakeven at +50 pips (configurable); activate trailing at +100 pips (configurable); ATR multiplier from volatility (optional); gap risk (Friday PM); trailing verification logging.
- **Phase 3 (exit strategy):** ATR-based TP in market_state; half-and-run (50% at 1.5× risk, 50% trail); optional time-based max hold; optional safety (limit manual close of winners).

---

## 2. Constraints (from cursor_works.md)

- Do **not** change consensus calculation, min_consensus_level, or required_llms logic.
- Do **not** add fields to the config object passed to `TradeConfig` without **stripping** them before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- **One** execution-path or config change at a time; verify (logs, behaviour) before the next.

---

## 3. Outstanding Implementation Plan (Step-by-Step)

### Phase 0: Prerequisites (no execution-path change)

| ID | Action | Research reference | Verification |
|----|--------|--------------------|--------------|
| **0.1** | Confirm ATR is in market_state / opportunities where execution runs | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §1 | Grep Trade-Alerts for `atr` in market_state/opportunities; ensure engine receives ATR when available. |
| **0.2** | Document target exit behaviour in USER_GUIDE | EXIT_STRATEGY_QUICK_REFERENCE, TRAILING_SL_EXECUTIVE_SUMMARY | Add short section: first TP at 1.5× risk, runner trail ATR×1.0; breakeven at +50 pips, trail activation at +100 pips (target for future implementation). |
| **0.3** | Add research index link to docs | — | In USER_GUIDE or README: one paragraph + link to `personal/research/` (EXIT_STRATEGY_DOCUMENTATION_INDEX, TRAILING_SL_RESEARCH_INDEX, POSITION_SIZING_INDEX). |

**Exit criteria:** Docs updated; no code change to execution path.

---

### Phase 1: Risk and position sizing (foundation)

**Goal:** Use risk-based position sizing and research-aligned risk limits in the **main** scalp path (auto_trader_core / scalp_engine), without changing consensus or open_trade signature.

| ID | Description | Research reference | Implementation notes |
|----|-------------|--------------------|------------------------|
| **1.1** | RiskManager or equivalent: position size from formula | POSITION_SIZING_IMPLEMENTATION.md | Formula: `(account_balance * risk_pct) / (sl_pips * pip_value)` → units. Either extend `src/risk_manager.py` to match research API (phase, risk %, pip value by pair) or add a small helper in auto_trader_core that uses same formula. |
| **1.2** | Config for phase and risk % | POSITION_SIZING_DELIVERY_SUMMARY, POSITION_SIZING_ONE_PAGE | e.g. TRADING_PHASE=phase_1, RISK_PERCENT_PER_TRADE=0.5. Account balance from config or OANDA (already available in engine). **Strip** any new keys before passing to TradeConfig. |
| **1.3** | Use formula-based units in open path | POSITION_SIZING_IMPLEMENTATION.md | In auto_trader_core where units are decided (e.g. ~line 1500): use RiskManager/formula output when SL pips and pip value are known; fallback to current base_position_size if not. One change, then verify. |
| **1.4** | Daily loss limit = 2% of account | POSITION_SIZING_RISK_MANAGEMENT Part 6 | Replace or complement fixed `max_daily_loss` with daily loss **percentage**: e.g. `max_daily_loss_pct = 2.0`; before open, if `abs(daily_pnl) / account_balance * 100 >= max_daily_loss_pct` → skip and log. Need account_balance in PositionManager (config or OANDA). |
| **1.5** | Circuit breaker: 5 consecutive losses | POSITION_SIZING_DELIVERY_SUMMARY | Before opening: if last 5 closed trades were losses, skip new opens and log. Track consecutive losses in state (e.g. execution_history or small state file); reset on first win or manual reset. |

**Order:** 1.1 → 1.2 → 1.3 (verify after 1.3). Then 1.4, then 1.5, each with verification.

**Exit criteria:** Position size follows formula when inputs available; daily 2% limit and 5-loss circuit breaker block new opens when triggered; logs clear; no change to consensus or open_trade signature.

---

### Phase 2: Trailing and breakeven (align with research)

**Goal:** Make breakeven and trailing activation thresholds configurable and align with research; add gap risk and verification logging.

| ID | Description | Research reference | Implementation notes |
|----|-------------|--------------------|------------------------|
| **2.1** | ATR multiplier from volatility (optional) | TRAILING_SL_EXECUTIVE_SUMMARY, TRAILING_SL_QUICK_REFERENCE | Current atr_multiplier from config; research: 2.0 normal, 2.5 high vol, 1.5 low. Optional: single config or market_state flag; no consensus change. |
| **2.2** | Breakeven at +50 pips (configurable) | TRAILING_SL_IMPLEMENTATION_GUIDE, TRAILING_STOP_LOSS_RESEARCH_REPORT §4 | Move SL to breakeven when unrealized profit ≥ X pips; add config e.g. BE_MIN_PIPS=50; use existing BE logic, add threshold. |
| **2.3** | Activate trailing at +100 pips (configurable) | Same | Research: activate trailing at +100 pips. Add e.g. TRAILING_ACTIVATION_MIN_PIPS=100; only convert to trailing when profit ≥ this (in addition to existing min age and OANDA P/L gate). |
| **2.4** | Gap risk: no new opens / reduce exposure near weekend | TRAILING_SL_EXECUTIVE_SUMMARY, TRAILING_SL_IMPLEMENTATION_GUIDE Part 4 | TradingHoursManager exists; research: no holds Fri 4pm–Sun 5pm; optional: tighten “can_open” or “should_close_trade” for Friday PM. |
| **2.5** | Trailing verification logging | TRAILING_SL_EXECUTIVE_SUMMARY Priority 1–2 | One INFO/DEBUG per trailing update (or per bar) so Manual logs can verify “SL is working”; weekly report optional later. |

**Order:** 2.1 or 2.5 first (params/logging), then 2.2, 2.3, 2.4 one at a time.

**Exit criteria:** Breakeven and trailing activation thresholds configurable; behaviour consistent with research; no change to consensus or open_trade signature.

---

### Phase 3: Exit strategy (half-and-run, optional)

**Goal:** Optional half-and-run: first TP at 1.5× risk (close part of position), runner with trailing. Implement only after Phases 1–2 are stable.

| ID | Description | Research reference | Implementation notes |
|----|-------------|--------------------|------------------------|
| **3.1** | ATR-based TP in market_state | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §1 | Trade-Alerts: add ATR and TP_ATR (e.g. entry ± ATR×2.0) to opportunities; engine can use for TP level. |
| **3.2** | Half-and-run: 50% at 1.5× risk, 50% trail | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §2, EXIT_STRATEGY_QUICK_REFERENCE | Design: (A) one order with TP at 1.5× risk, then convert remainder to trailing after first TP hit; or (B) two orders (two half positions) at open. Design decision required; implement one approach. |
| **3.3** | Time-based max hold (e.g. 4h) | EXIT_STRATEGY_QUICK_REFERENCE | Optional: close runner if hold time > 4h (config). |
| **3.4** | Safety: limit manual close of winners | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §6 | Optional: in UI or API, block or warn when closing a trade in profit (e.g. > 1 pip); configurable. |

**Order:** 3.1 first, then 3.2 (design + implement), then 3.3/3.4 if desired.

**Exit criteria:** First TP and runner match design; no change to consensus or open_trade signature; new behaviour behind config flag if possible.

---

## 4. Dependency and Order Summary

```
Phase 0 (docs, no execution change)
    ↓
Phase 1 (position sizing formula, 2% daily limit, 5-loss circuit breaker)  ← do first
    ↓
Phase 2 (trailing/BE thresholds, gap risk, verification logging)
    ↓
Phase 3 (half-and-run, ATR TP, time exit)  ← optional, after 1–2 stable
```

---

## 5. Research Document Quick Links

| Topic | Index / entry point | Implementation detail |
|-------|----------------------|------------------------|
| Exit strategy | `research/EXIT_STRATEGY_DOCUMENTATION_INDEX.md` | `research/EXIT_STRATEGY_IMPLEMENTATION_GUIDE.md` |
| Trailing SL | `research/TRAILING_SL_RESEARCH_INDEX.md` | `research/TRAILING_SL_IMPLEMENTATION_GUIDE.md` |
| Position sizing | `research/POSITION_SIZING_INDEX.md` | `research/POSITION_SIZING_IMPLEMENTATION.md` |
| Sources | `research/RESEARCH_SOURCES.md` | — |

---

## 6. What Not to Do

- Do **not** change consensus formula, min_consensus_level, or required_llms logic.
- Do **not** add config fields to the object passed to `TradeConfig` without stripping them before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- Do **not** implement multiple execution-path changes in one deploy; one step at a time, verify, then next.
- Do **not** assume position sizing alone fixes profitability; keep fixing execution and exits in parallel with cursor_works / improvementplan.

---

## 7. Success Criteria (High Level)

- **Phase 0:** Docs updated; ATR and target exit behaviour documented; research index linked.
- **Phase 1:** Position size = (Account × Risk%) / (SL × pip value) in main path; daily loss limit 2%; circuit breaker 5 consecutive losses; logs show blocks when limits hit.
- **Phase 2:** Breakeven and trailing activation thresholds configurable; trailing verification visible in logs; weekend/gap policy documented and enforced where implemented.
- **Phase 3:** If implemented: first TP at 1.5× risk (or ATR-based) and runner with trailing; optional time exit and safety checks.

---

*This plan lists all outstanding issues from the research folder and TRADING_SYSTEM_IMPROVEMENT_PLAN.md. For full context see `personal/TRADING_SYSTEM_IMPROVEMENT_PLAN.md` and `personal/cursor_works.md`.*
