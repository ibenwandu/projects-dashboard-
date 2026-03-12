# Manual / Premature Trade Closures – Investigation (cursor5 §5.7)

**Context:** OANDA transaction history shows many closes as `MARKET_ORDER` / `TRADE_CLOSE`; ~80% of closed trades were reported as "manually closed". This doc records where `close_trade` (or equivalent) is invoked so root cause can be identified before any fix.

**No code changes in this document; investigation only.**

---

## Call sites that close trades

| Location | Trigger | Notes |
|----------|---------|------|
| **auto_trader_core.py** | | |
| `monitor_positions()` | `TradingHoursManager.should_close_trade()` | Weekend / Friday 21:30 UTC; optional Mon–Thu 23:00 for non-runner. |
| `monitor_positions()` | MACD_CROSSOVER: `check_macd_reverse_crossover` | Strategy exit. |
| `monitor_positions()` | DMI_CROSSOVER: `check_dmi_reverse_crossover` | Strategy exit. |
| `monitor_positions()` | STRUCTURE_ATR / STRUCTURE_ATR_STAGED | FT-DMI-EMA and LLM/Fisher structure+ATR exits. |
| `_check_intelligence_validity()` | Opportunity removed from market_state | **Commented out** in code (no auto-close). |
| FT-DMI-EMA logic | Time stop, 4H DMI crossover, ADX collapse, spread spike, EMA structure breakdown | Multiple `close_trade(...)` calls. |
| **scalp_engine.py** | | |
| `_monitor_positions()` | MACD reverse crossover | Calls `position_manager.close_trade(...)`. |
| Shutdown path | System shutdown | `position_manager.close_trade(trade_id, "System shutdown")`. |
| Replace/review flow | After cancel replace | May call `open_trade` (not close). |
| **TradeExecutor (auto_trader_core)** | | |
| `close_trade()` | OANDA `TradeClose` API | Used by all of the above. |

---

## Possible causes of "manual" TRADE_CLOSE in OANDA

1. **User closed in OANDA UI** – OANDA records as TRADE_CLOSE; engine did not call close.
2. **Trading hours manager** – Engine closes when `should_close_trade()` returns true (weekend / Friday 21:30 / runner rules).
3. **Strategy exits** – MACD, DMI, STRUCTURE_ATR, FT-DMI-EMA (time stop, DMI crossover, ADX, spread spike, EMA breakdown).
4. **Orphan / sync** – Not a direct close; sync removes from engine state when position no longer on OANDA (e.g. closed elsewhere).
5. **UI "Close" or risk-manager auto-close** – If present in Scalp UI or a risk module, would show as engine-initiated close.

**Next step:** Confirm whether Scalp UI or any risk-manager code calls `close_trade` (or OANDA TradeClose). Then narrow by comparing close timestamps in `oanda_transactions_*.json` with engine log lines for "Closed trade" / "System shutdown" / trading hours / strategy exit reasons.

---

*Reference: suggestions from cursor5.md §5.7; consol-recommend4 Phase 0.2.*
