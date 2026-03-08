# Trading System Improvement Plan
## Based on Research in `personal/research/`

**Created:** March 6, 2026  
**Source:** Review of research folder (Exit Strategy, Trailing SL, Position Sizing)  
**Applies to:** Trade-Alerts / Scalp-Engine  
**Constraints:** Respects cursor_works.md do-not-do list (no consensus formula change, no new TradeConfig fields without stripping, no `open_trade()` signature change, one execution-path change at a time).

---

## 1. Research Summary

The `personal/research/` folder contains three bodies of work:

| Area | Key documents | Main recommendation |
|------|----------------|---------------------|
| **Exit strategy** | EXIT_STRATEGY_IMPLEMENTATION_GUIDE.md, FOREX_PROFIT_TAKING_STRATEGIES.md, EXIT_STRATEGY_QUICK_REFERENCE.md | Half-and-run: close 50% at 1.5× risk, trail 50% with ATR; ATR-based TP; reduce early manual closes. |
| **Trailing stop loss** | TRAILING_SL_IMPLEMENTATION_GUIDE.md, TRAILING_STOP_LOSS_RESEARCH_REPORT.md, TRAILING_SL_EXECUTIVE_SUMMARY.md | ATR(14)×2.0 for distance; breakeven at +50 pips, activate trailing at +100 pips; gap risk (no weekend holds); verification logging. |
| **Position sizing** | POSITION_SIZING_IMPLEMENTATION.md, POSITION_SIZING_RISK_MANAGEMENT.md, POSITION_SIZING_DELIVERY_SUMMARY.txt | Formula: (Account × Risk%) / (SL pips × pip value); Phase 1: 0.5%, Phase 2: 1%, Phase 3: 2%; daily loss limit 2%; circuit breaker 5 consecutive losses. |

**Cross-cutting:** Research states that position sizing does not fix a 0% win rate; fix execution and exits first, then add/refine position sizing. This plan orders work accordingly.

---

## 2. Constraints (from cursor_works.md)

- Do **not** change consensus calculation, min_consensus_level, or required_llms logic.
- Do **not** add fields to the config object passed to `TradeConfig` without stripping before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- Implement **one** execution-path or config change at a time; verify (e.g. trades still open, logs) before the next.

---

## 3. Current State (What Already Exists)

- **Trailing:** ATR_TRAILING with OrderCreate TRAILING_STOP_LOSS; min age 120s + OANDA P/L gate (Fix 4); MIN_PROFIT_PIPS_FOR_TRAILING = 1.0; ALREADY_EXISTS handled (cursor5/6, Part 16).
- **Position size:** `base_position_size` in config; units from config, not yet from risk formula.
- **Exits:** Single TP per trade; no half-and-run or partial close; manual/strategy closes documented in MANUAL_CLOSURES_INVESTIGATION.md; MACD close only for MACD_CROSSOVER (Fix 2).
- **Risk limits:** No daily loss limit or circuit breaker (5 consecutive losses) in code.

---

## 4. Implementation Plan (Phased)

### Phase 0: Prerequisites (no execution-path change)

| Item | Action | Research reference | Notes |
|------|--------|--------------------|--------|
| 0.1 | Confirm ATR in market_state | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §1 | Trade-Alerts exports `atr` for engine; ensure opportunities used for execution have ATR when available. |
| 0.2 | Document target exit behaviour | EXIT_STRATEGY_QUICK_REFERENCE, TRAILING_SL_EXECUTIVE_SUMMARY | Add to USER_GUIDE: target first TP at 1.5× risk, runner trail at ATR×1.0; breakeven at +50 pips, trail activation at +100 pips (for future implementation). |
| 0.3 | Add research index to docs | — | In Trade-Alerts or personal: one short doc linking to `personal/research/` (EXIT_STRATEGY_DOCUMENTATION_INDEX, TRAILING_SL_RESEARCH_INDEX, POSITION_SIZING_INDEX). |

**Exit criteria:** Docs updated; no code change to execution path.

---

### Phase 1: Risk and position sizing (foundation)

**Goal:** Introduce risk-based position sizing and hard risk limits without changing when/how trades open (same opportunities, same consensus).

| Step | Description | Research reference | Files (example) |
|------|-------------|--------------------|----------------|
| 1.1 | Add RiskManager / position size from formula | POSITION_SIZING_IMPLEMENTATION.md | `Scalp-Engine/src/risk_manager.py` (or equivalent); formula: `(account_balance * risk_pct) / (sl_pips * pip_value)`. |
| 1.2 | Config for phase and risk % | POSITION_SIZING_DELIVERY_SUMMARY, POSITION_SIZING_ONE_PAGE | e.g. TRADING_PHASE=phase_1, RISK_PERCENT_PER_TRADE=0.5; account balance from config or OANDA. |
| 1.3 | Integrate position size into open path | POSITION_SIZING_IMPLEMENTATION.md | In `auto_trader_core.py`, where units are decided: use RiskManager output instead of fixed base only; **strip** any new keys from config before passing to TradeConfig. |
| 1.4 | Daily loss limit (2%) | POSITION_SIZING_RISK_MANAGEMENT Part 6 | Before opening: if daily P&L ≤ -2% of account, skip new opens and log. Need daily P&L source (state or OANDA). |
| 1.5 | Circuit breaker (5 consecutive losses) | POSITION_SIZING_DELIVERY_SUMMARY | Before opening: if last 5 closes were losses, skip new opens and log; reset on first win or manual reset. |

**Order:** 1.1 → 1.2 → 1.3 (one change, then verify). Then 1.4, then 1.5, each with verification.

**Exit criteria:** Position size follows formula; daily limit and circuit breaker prevent new opens when triggered; logs clear; no change to consensus or open_trade signature.

---

### Phase 2: Trailing and breakeven (align with research)

**Goal:** Harden ATR trailing and add breakeven/trailing thresholds consistent with research (without changing open_trade signature).

| Step | Description | Research reference | Notes |
|------|-------------|--------------------|--------|
| 2.1 | ATR multiplier from volatility (optional) | TRAILING_SL_EXECUTIVE_SUMMARY, TRAILING_SL_QUICK_REFERENCE | Currently atr_multiplier from config; consider 2.0 normal, 2.5 high vol, 1.5 low (research). Single config or market_state flag only; no formula change. |
| 2.2 | Breakeven at +50 pips (configurable) | TRAILING_SL_IMPLEMENTATION_GUIDE, TRAILING_STOP_LOSS_RESEARCH_REPORT §4 | Move SL to breakeven when unrealized profit ≥ 50 pips (or config); already have BE logic—add threshold from config. |
| 2.3 | Activate trailing at +100 pips (configurable) | Same | Today trailing can activate at 1 pip profit (Part 9); research suggests “activate trailing” at larger profit (e.g. 100 pips). Optional: second threshold (e.g. TRAILING_ACTIVATION_MIN_PIPS=100) so conversion happens only after +100 pips; keep existing min age and OANDA P/L gate. |
| 2.4 | Gap risk: avoid new opens / reduce exposure near weekend | TRAILING_SL_EXECUTIVE_SUMMARY, TRAILING_SL_IMPLEMENTATION_GUIDE Part 4 | TradingHoursManager already exists; research: no holds Friday 4pm–Sunday 5pm; optional: tighten “should_close_trade” or “can_open” for Friday PM. |
| 2.5 | Trailing verification logging | TRAILING_SL_EXECUTIVE_SUMMARY Priority 1–2 | Ensure one INFO/DEBUG per trailing update (or per bar) so Manual logs can verify “SL is working”; weekly report optional later. |

**Order:** 2.1 or 2.5 first (logging/params), then 2.2, 2.3, 2.4 one at a time.

**Exit criteria:** Breakeven and trailing activation thresholds configurable; behaviour consistent with research; no change to consensus or open_trade signature.

---

### Phase 3: Exit strategy (half-and-run, optional)

**Goal:** Optional “half-and-run” behaviour: first TP at 1.5× risk (close part of position), runner with trailing. This is a larger feature; implement only after Phases 1–2 are stable.

| Step | Description | Research reference | Notes |
|------|-------------|--------------------|--------|
| 3.1 | ATR-based TP in market_state | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §1 | Trade-Alerts: add ATR and TP_ATR (e.g. entry ± ATR×2.0) to opportunities; engine can use for TP level. |
| 3.2 | Half-and-run: two TP levels (50% at 1.5× risk, 50% trail) | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §2, EXIT_STRATEGY_QUICK_REFERENCE | OANDA may not support “close 50% at limit”; options: (A) one order with TP at 1.5× risk, then convert remainder to trailing after first TP hit; (B) two orders (two half positions) at open. Design decision required; implement one approach. |
| 3.3 | Time-based max hold (e.g. 4h) | EXIT_STRATEGY_QUICK_REFERENCE | Optional: close runner if hold time &gt; 4 hours (config). |
| 3.4 | Safety: limit manual close of winners | EXIT_STRATEGY_IMPLEMENTATION_GUIDE §6 | Optional: in UI or API, block or warn when closing a trade in profit (e.g. &gt; 1 pip); configurable. |

**Order:** 3.1 first (ATR TP available), then 3.2 (design + implement), then 3.3/3.4 if desired.

**Exit criteria:** First TP and runner behaviour match design; no change to consensus formula or open_trade signature; new behaviour behind config flag if possible.

---

## 5. Dependency and Order Summary

```
Phase 0 (docs, no execution change)
    ↓
Phase 1 (position sizing, daily limit, circuit breaker)  ← do first
    ↓
Phase 2 (trailing/breakeven tuning, gap risk, logging)
    ↓
Phase 3 (half-and-run, ATR TP, time exit)  ← optional, after 1–2 stable
```

**Why this order:** Research says position sizing does not fix 0% win rate; fixing execution and exits comes first. Phase 1 still adds essential risk controls (daily limit, circuit breaker) and makes position size formula-driven. Phase 2 improves the existing trailing/BE logic. Phase 3 adds a more advanced exit structure once the base is solid.

---

## 6. What Not to Do

- Do **not** change consensus formula, min_consensus_level, or required_llms logic.
- Do **not** add config fields to the object passed to `TradeConfig` without stripping them before `TradeConfig.__init__`.
- Do **not** change `open_trade()` return signature.
- Do **not** implement multiple execution-path changes in one deploy; one step at a time, verify, then next.
- Do **not** assume position sizing alone will fix profitability; keep fixing execution and exits in parallel with cursor_works / improvementplan items.

---

## 7. Research Document Quick Links

| Topic | Index / entry point | Implementation detail |
|-------|----------------------|------------------------|
| Exit strategy | `research/EXIT_STRATEGY_DOCUMENTATION_INDEX.md` | `research/EXIT_STRATEGY_IMPLEMENTATION_GUIDE.md` |
| Trailing SL | `research/TRAILING_SL_RESEARCH_INDEX.md` | `research/TRAILING_SL_IMPLEMENTATION_GUIDE.md` |
| Position sizing | `research/POSITION_SIZING_INDEX.md` | `research/POSITION_SIZING_IMPLEMENTATION.md` |
| Sources | `research/RESEARCH_SOURCES.md` | — |

---

## 8. Success Criteria (High Level)

- **Phase 1:** Position size = (Account × Risk%) / (SL × pip value); daily loss limit and circuit breaker enforced; logs show blocks when limits hit.
- **Phase 2:** Breakeven and trailing activation thresholds configurable; trailing verification visible in logs; weekend/gap policy documented and enforced where implemented.
- **Phase 3:** If implemented: first TP at 1.5× risk (or ATR-based) and runner with trailing; optional time exit and safety checks.

---

## 9. Next Steps

1. **Review this plan** and confirm phase order and scope (e.g. Phase 3 optional).
2. **Phase 0:** Update USER_GUIDE and add research index link (no execution change).
3. **Phase 1:** Implement RiskManager and position size formula; add daily limit and circuit breaker one step at a time; verify after each step.
4. **Phase 2:** Implement trailing/breakeven and gap-risk steps one at a time; verify with Manual logs.
5. **Phase 3:** Only after 1–2 stable; design half-and-run (one OANDA order vs two), then implement.

---

## 10. Outstanding Issues Checklist

For a **step-by-step checklist of all outstanding issues** (what’s done vs not done, with IDs and verification), see:

**`personal/OUTSTANDING_IMPLEMENTATION_PLAN.md`**

That document lists Phase 0–3 outstanding items with IDs (0.1–0.3, 1.1–1.5, 2.1–2.5, 3.1–3.4), research references, and implementation notes, and respects the same constraints as this plan.

---

*This plan is derived from the contents of `personal/research/` and aligned with `personal/cursor_works.md` and existing Trade-Alerts improvements (cursor5/6, improvementplan Fixes 1–4).*
