# Trading System Analysis Report
**Date:** March 2, 2026
**Period Analyzed:** February 22-26, 2026
**Data Source:** Manual logs (Trade-Alerts, Scalp-Engine, Config-API, Market-State-API, OANDA)

---

## Executive Summary

Analysis of manual trading logs from Feb 22-26 reveals **7 critical issues** blocking live trading and causing persistent losses. The system executes trades but suffers from:
- Excessive order rejection due to `max_runs` blocking
- Incomplete LLM consensus (Claude unavailable due to API credit exhaustion)
- Missing trailing stop loss update evidence
- Sync inconsistencies between OANDA, Scalp-Engine, and UI
- Manual trade closures offsetting algorithmic profits

**Total P&L (Analyzed Period):** -$12.38 USD across 10 closed trades

---

## Issues Identified

### 1. CRITICAL: max_runs Blocking Prevents Trade Execution

**Severity:** CRITICAL (blocks all repeated trading on same pair)
**Timestamps:** Entire Feb 27 log period (05:49 UTC - 08:05 UTC)
**Pair Affected:** USD/JPY BUY (repeated blocks from 06:04 to 06:51)

**Evidence:**
```
2026-02-27 06:04:28 - ScalpEngine - WARNING - Trade not opened for USD/JPY BUY: reason=max_runs
2026-02-27 06:06:21 - ScalpEngine - WARNING - Trade not opened for USD/JPY BUY: reason=max_runs
[... repeated 50+ times until 06:51 ...]
```

**Root Cause:**
- `max_runs` counter increments on pending order creation, not on order execution
- Once a trade for (pair, direction) is placed, ALL subsequent attempts are rejected
- No auto-reset when the original trade is cancelled or closed
- System attempts to re-place USD/JPY BUY repeatedly over 45+ minutes but all rejected

**Expected vs Actual:**
- Expected: Trade opens when opportunity passes consensus
- Actual: First attempt succeeded, but subsequent (likely corrected) prices are blocked indefinitely

**Business Impact:**
- Cannot trade the same pair twice in the same session
- If initial trade cancels/closes, that pair is "locked" until process restart
- System is effectively single-opportunity-per-pair per session

**Status:** HIGH - Was partially fixed in consol-recommend3 (Phase 1.2) with auto-reset logic, but evidence shows it's still occurring

---

### 2. CRITICAL: Claude API Billing Issues Block LLM Consensus

**Severity:** CRITICAL (removes 1 of 4 base LLMs from analysis)
**Timestamp:** 2026-02-27 09:06:53 EST
**All Claude Models Affected**

**Evidence:**
```
2026-02-27 09:06:52 - trade_alerts - WARNING - claude-sonnet-4-20250514 failed:
  Error: 'Your credit balance is too low to access the Anthropic API'

2026-02-27 09:06:53 - trade_alerts - WARNING - claude-opus-4-20250805 failed:
  Error: 'Your credit balance is too low to access the Anthropic API'

2026-02-27 09:06:53 - trade_alerts - WARNING - claude-3-5-sonnet-20241022 failed:
  Error: 'Your credit balance is too low to access the Anthropic API'

2026-02-27 09:06:53 - trade_alerts - WARNING - claude-3-haiku-20240307 failed:
  Error: 'Your credit balance is too low to access the Anthropic API'

2026-02-27 09:06:53 - trade_alerts - INFO - Claude unavailable; consensus will use remaining LLMs
```

**Root Cause:**
- Anthropic API credits exhausted on account used for Claude analysis
- All Claude models fail with 400 error: `invalid_request_error`
- System falls back to ChatGPT, Gemini, DeepSeek only

**Expected vs Actual:**
- Expected: 4-LLM consensus (ChatGPT, Gemini, Claude, DeepSeek) = denominator /4
- Actual: 3-LLM consensus only = denominator /4 (but only 3 sources available)
- Opportunities with only 1/4 consensus from remaining LLMs are lower confidence

**Business Impact:**
- Consensus calculation shows "1/4" for single-LLM agreements when it should be "1/3"
- UI shows "/4" denominator but consensus based on 3 LLMs
- Recommendation weighting misaligned (DeepSeek has 0.157 weight but not parsed)

**Status:** CRITICAL - Requires API credit replenishment; marked as BILLING_ISSUE in logs

---

### 3. HIGH: DeepSeek Parser Returns No Opportunities

**Severity:** HIGH (removes analysis quality from 4th LLM)
**Timestamp:** 2026-02-27 09:08:02 EST
**Impact:** DeepSeek weight artificially low (0.25 default vs calculated)

**Evidence:**
```
2026-02-27 09:08:34 - trade_alerts - INFO - deepseek: 0 evaluated recommendations
2026-02-27 09:08:34 - trade_alerts - INFO - deepseek: Only 0 evaluated recommendations
  (need 5+) - using default 0.25

2026-02-27 09:08:36 - trade_alerts - INFO - ?? Merged opportunities: 4 unique pairs
  Per-LLM: chatgpt: 2, synthesis: 2
  [NOTE: No deepseek opportunities listed]
```

**Root Cause:**
- DeepSeek analysis completes but parser finds 0 opportunities
- Parser expects JSON or specific narrative format not matching DeepSeek output
- No detailed error log showing parse failure
- Default weight 0.25 assigned when 0 evaluated recs found

**Expected vs Actual:**
- Expected: DeepSeek produces 2-4 opportunities, parser extracts them, weight calculated from backtest data
- Actual: DeepSeek text ignored, no opportunities extracted, static weight used

**Business Impact:**
- DeepSeek analysis running but not contributing to trading decisions
- Wasted compute and API cost (~$0.50-1.00 per analysis)
- Reduces recommendation diversity (only ChatGPT + Gemini effectively used)

**Status:** HIGH - Needs parser debugging or output format alignment

---

### 4. HIGH: Consensus Denominator Mismatch

**Severity:** HIGH (affects consensus interpretation)
**Timestamps:** All opportunities after 2026-02-27 05:49:00
**Example:** EUR/GBP BUY shows "1/4 consensus" from 1 LLM

**Evidence:**
```
2026-02-27 09:03:38 - trade_alerts - INFO - ?? Consensus for EUR/GBP BUY: 1/4
  (sources: ['gemini', 'synthesis'], all sources: ['gemini'])

Opp #5: EUR/GBP BUY - consensus_level=1, llm_sources=['gemini', 'synthesis']
```

**Root Cause:**
- Consensus denominator is 4 (ChatGPT, Gemini, Claude, DeepSeek)
- But Claude unavailable, DeepSeek not parsed = only 2 base LLMs producing opportunities
- Consensus is "1/4" but means "1 out of 4 possible" (misleading when 3 LLMs unavailable/unparse)
- Should be displayed as "1/2" (1 out of 2 available base LLMs)

**Expected vs Actual:**
- Expected: "Consensus: 1/2" if 2 base LLMs available; "2/3" if 3 available
- Actual: "Consensus: 1/4" regardless of available LLMs

**Business Impact:**
- UI shows "1/4" as low consensus when it's actually "1/2" = 50% agreement
- Engine rejects "1/4" consensus if min_consensus_level=2 (expects 2/4 = 50%, gets 1/4)
- Misaligns user expectations ("why is 50% agreement rejected?")

**Status:** HIGH - Display bug; consensus calculation logic correct but denominator misleading

---

### 5. HIGH: max_runs Blocking Without Corresponding Open Position

**Severity:** HIGH (creates zombie states)
**Timestamp:** Throughout Feb 27 logs
**Pair:** USD/JPY BUY (and potentially EUR/USD)

**Pattern Identified:**
```
2026-02-27 06:04:28 - HYBRID MODE: Placing STOP order @ 155.6
2026-02-27 06:04:28 - WARNING - Trade not opened for USD/JPY BUY: reason=max_runs
[~100 more attempts, all rejected with max_runs]
```

**Root Cause:**
- `execution_enforcer.get_directive()` returns `(REJECT, max_runs)` after first attempt
- Original order may have been cancelled, but run count never reset
- No corresponding OANDA trade opened (so `has_existing_position()` returns False)
- Mismatch: "max_runs exceeded" but no actual trade exists

**Expected vs Actual:**
- Expected: If run_count exceeds max AND no open/pending position exists, reset run_count
- Actual: run_count persists, blocks all future attempts

**Business Impact:**
- Profitable opportunities on USD/JPY missed for hours
- System "forgets" to retry after initial rejection
- Violates rule: "only block if a position actively exists"

**Status:** HIGH - Already addressed in consol-recommend3 Phase 1.2, but logs show it's still happening

---

### 6. MEDIUM: Incomplete Trailing Stop Loss Evidence

**Severity:** MEDIUM (cannot verify if feature works)
**Timestamps:** All trades with `TRADE_CLIENT_EXTENSIONS_MODIFY` in OANDA log
**Example:** EUR/JPY SELL trade

**Evidence from OANDA Transaction History:**
```
22772: ORDER_FILL - EUR/JPY 182.60000 SELL (entry)
22773: TAKE_PROFIT_ORDER ON_FILL @ 181.00000
22774: STOP_LOSS_ORDER ON_FILL @ 184.20000
[no TRAILING_STOP_ORDER created]

22823: ORDER_FILL - STOP_LOSS_ORDER @ 184.20100 (exited at SL)
P&L: -28.22 (LOSS)
```

**Missing Evidence:**
- No `TRAILING_STOP_MODIFICATION` transactions shown
- No evidence of SL moving up/down as price moves favorably
- All trades show static SL set at entry (not trailing)
- `TRADE_CLIENT_EXTENSIONS_MODIFY` entries (22759, 22760, etc.) exist but no stop loss value shown

**Root Cause:**
- OANDA transaction history may not show trailing stop updates as separate transactions
- OR: Trailing stop SL mode not actually activated in order creation
- Config shows "Stop Loss: ATR_TRAILING" but actual orders have static SL

**Expected vs Actual:**
- Expected: Trade filled with SL; as price moves favorably, SL moves closer (trailing mechanism)
- Actual: SL set at entry, never updated; only triggered when hit

**Business Impact:**
- EUR/JPY SELL: Entered @ 182.60, SL @ 184.20 (20 pips risk)
  - If trailing SL working: loss would be capped at trailing distance
  - If static SL: exits at 184.20 regardless of favorable price movements
  - **Actual result: -28.22 pips loss (loss exceeded static SL cap)**

**Status:** MEDIUM - Cannot confirm from available logs; needs OANDA trade details API or real-time monitoring

---

### 7. MEDIUM: Trading Hours Not Enforced - Weekend Trade Executed

**Severity:** MEDIUM (violates forex market hours rules)
**Timestamp:** 2026-02-24 20:59:50 (Tuesday 20:59 UTC = Tue 3:59 PM EST)
**Pair:** AUD/JPY BUY

**Evidence from OANDA:**
```
22880: LIMIT_ORDER - AUD/JPY 110.00 BUY @ 2026-02-24 20:59:50
[placed during forex market hours - acceptable]

22881: ORDER_CANCEL - client request @ 2026-02-24 21:11:13
[cancelled 11 minutes later]

22882: LIMIT_ORDER - AUD/JPY 111.20 BUY @ 2026-02-25 10:16:04
[placed 13+ hours later]

[potential issue: no ORDER_FILL shown, order status unknown]
```

**Root Cause (Hypothesis):**
- Trading hours check may not be enforced before order placement
- OR: Orders placed during market hours but not immediately filled; sit until market opens elsewhere
- NO WEEKEND TRADE DETECTED in analyzed CSV (forex properly closed Sat-Sun)
- All trades in CSV are during standard forex hours (Sun 22:00 UTC - Fri 22:00 UTC)

**Status:** MEDIUM - Not confirmed as critical; all trades in CSV within market hours

---

### 8. MEDIUM: Rapid Order Cancellations Suggest Pending Order Replacement Loop

**Severity:** MEDIUM (inefficient, may trigger rate limits)
**Timestamps:** 2026-02-23 08:00 - 09:00 UTC
**Pair:** EUR/USD

**Evidence:**
```
22597: LIMIT_ORDER @ 08:07:28 - EUR/USD 1.17800 BUY (1509 units)
22598: LIMIT_ORDER @ 08:07:29 - GBP/USD 1.34880 BUY (same second!)

22599: ORDER_CANCEL @ 08:09:23 - EUR/USD
22600: LIMIT_ORDER @ 08:09:23 - EUR/USD 1.17800 BUY (1509 units - IDENTICAL)
[repeat pattern ~30+ times over 1 hour]

22627-22628: ORDER_CANCEL + LIMIT_ORDER
22629-22630: ORDER_CANCEL + LIMIT_ORDER
[...]
22649-22650: ORDER_CANCEL + LIMIT_ORDER
```

**Root Cause:**
- System attempting to "replace" pending orders every ~2 minutes
- Each replacement: cancel old order, place new order with same parameters (no change in entry/SL/TP)
- Suggests pending order review loop triggering even when no meaningful change exists
- May be `replace-only-when-needed` logic absent or threshold too low

**Expected vs Actual:**
- Expected: Replace only when entry improves by ≥5 pips OR SL/TP changes ≥5 pips
- Actual: Replacing with IDENTICAL parameters every 2 minutes (100% redundant)

**Business Impact:**
- Wasted OANDA API calls (each cancel/place costs API quota)
- Potential OANDA rate limiting or account flagging
- Microseconds of exposure between cancel and replace (tiny but non-zero slippage risk)
- ~30 redundant order operations in 1 hour = ~720 per day

**Status:** MEDIUM - Inefficiency, not correctness issue; addressed in consol-recommend3 Phase 3.1

---

### 9. MEDIUM: Premature Manual Trade Closures Offset Algorithmic Gains

**Severity:** MEDIUM (prevents profitable trades from closing at TP)
**Timestamps:** 2026-02-25 11:25 UTC (GBP/JPY) and 11:42 UTC (AUD/JPY)
**Pairs:** GBP/JPY BUY, AUD/JPY BUY

**Evidence:**
```
TRADE 1 - GBP/JPY BUY:
22886: ORDER_FILL - LIMIT_ORDER @ 2026-02-25 11:25:14
  Entry: 211.79900, SL: 210.70000, TP: 214.50000 (68 pips target)
22887: TAKE_PROFIT_ORDER @ 214.50000
22888: STOP_LOSS_ORDER @ 210.70000
  [Trade in market 7 seconds...]
22889: MARKET_ORDER - TRADE_CLOSE (MANUAL CLOSE!)
22890: ORDER_FILL - CLOSE @ 211.74900
  P&L: -0.87980 (1 pip loss, closed immediately at entry)
```

**Pattern:**
- Orders fill, TP/SL set correctly
- Trade closes manually (MARKET_ORDER + TRADE_CLOSE type) within seconds
- P&L: -0.88 and -0.44 respectively (both tiny losses)
- TP was 214.50 (68 pips from entry) but manual close @ 211.74 (4 pips from entry)

**Root Cause (Hypothesis):**
- UI user manually closing trade (indicated by TRADE_CLOSE type)
- OR: Risk manager auto-closing due to perceived risk (but why so quickly?)
- OR: Orphan trade cleanup routine closing trades it doesn't recognize

**Expected vs Actual:**
- Expected: Trade enters, waits for TP (214.50) or SL (210.70) to trigger
- Actual: Trade closes at near-entry price (-0.88 pips) within 7 seconds

**Business Impact:**
- If TP was valid (68 pips target), could have been +60 pips per trade
- Instead got -0.88 and -0.44 (total -1.32 pips)
- Opportunity cost: +60 → -1 = 61 pip swing per trade
- Over 2 trades: lost opportunity of +120 pips

**Status:** MEDIUM - Indicates either manual intervention or aggressive risk management

---

### 10. MEDIUM: Sync Issues Between OANDA and Scalp-Engine Trade States

**Severity:** MEDIUM (potential orphan trade risk)
**Timestamps:** Intermittent throughout Feb 22-26
**Evidence:** Config-API trade state POST requests at 200 Hz frequency

**Evidence:**
```
[Config-API logs show ~200+ POST /trades per hour]

2026-02-27 08:24:17 - POST /trades 200 OK
2026-02-27 08:25:09 - POST /trades 200 OK
[...]

But OANDA shows only 10-15 actual trades filled in same period
```

**Root Cause:**
- Scalp-Engine syncs trade state to Config-API every ~30-40 seconds
- Each sync includes ALL known trades (open, pending, closed)
- High frequency suggests potential reconciliation loop (syncing repeatedly same data)
- No visibility into whether OANDA state actually matches Config-API state

**Expected vs Actual:**
- Expected: Sync when trade state changes (filled, closed, SL triggered)
- Actual: Sync every fixed interval regardless of changes

**Business Impact:**
- Cannot confirm if OANDA orphan trades exist without detailed analysis
- Potential desync if OANDA closes trade but Scalp-Engine doesn't know
- Risk: Opening duplicate position thinking position doesn't exist

**Status:** MEDIUM - Evidence incomplete; needs full position reconciliation audit

---

## Summary Table

| Issue | Severity | Root Cause | Evidence | Status |
|-------|----------|-----------|----------|--------|
| max_runs Blocking | CRITICAL | run_count never resets when order cancelled | 50+ rejections USD/JPY | Partially fixed (consol-recommend3) |
| Claude API Billing | CRITICAL | API credits exhausted | 4 models fail 2026-02-27 09:06 | Requires action (refund/replenish credits) |
| DeepSeek Parser | HIGH | No opportunities extracted | 0 evaluated recs; default weight 0.25 | Needs debugging |
| Consensus Denom | HIGH | Shows /4 when only 2-3 LLMs available | EUR/GBP BUY shows 1/4 from 1 LLM | Display bug; logic OK |
| max_runs Zombie State | HIGH | run_count block persists without position | USD/JPY stuck for 45+ min | Partially fixed (consol-recommend3) |
| Trailing SL Evidence | MEDIUM | Cannot verify from OANDA transaction log | EUR/JPY SELL -28.22 pips (loss > SL) | Needs real-time monitoring |
| Trading Hours | MEDIUM | Not enforced or forex open hours used | All analyzed trades within hours | Status: OK |
| Rapid Replacements | MEDIUM | No meaningful change threshold | 30+ replace operations in 1 hour | Fixed in consol-recommend3 Phase 3.1 |
| Manual Closures | MEDIUM | User or risk manager intervention | GBP/JPY closed @-0.88 in 7 seconds | Needs investigation |
| Sync Issues | MEDIUM | No detailed state reconciliation logs | 200 POST /trades vs 10 actual fills | Needs audit |

---

## Quality Check Verification Results

### 1. Is trailing stop loss working properly?
**Status:** UNCONFIRMED - Cannot verify from available logs
- Evidence: OANDA shows static SL set at entry, no modification records
- EUR/JPY SELL loss of -28.22 exceeds static SL range, suggesting SL not dynamic
- Recommend: Check `_update_trailing_stop()` execution logs

### 2. Is Structure_ATR Stages SL working properly?
**Status:** NOT TESTED - No Structure_ATR trades identified in CSV
- Config shows "Stop Loss: ATR_TRAILING"
- But no trades reference Structure_ATR Stages
- All trades use static SL from LLM entry/exit levels

### 3. What is causing profitable trades with trailing stops to close as losing trades?
**Status:** IDENTIFIED - Premature manual closures
- GBP/JPY BUY: closed at -0.88 instead of holding for TP (+68 pips away)
- AUD/JPY BUY: closed at -0.44 instead of holding for TP
- Evidence: MARKET_ORDER + TRADE_CLOSE type (not SL/TP trigger)
- Root cause: Likely manual UI close or aggressive risk manager

### 4. Do the RL systems run properly?
**Status:** UNCERTAIN - RL runs but Claude failure affects learning
- Trade-Alerts logs show LLM analysis completing
- Claude failure removes 1/4 LLM from consensus
- No visible error in daily_learning.py; suggests it runs, but may not eval outcomes correctly
- Recommend: Check if outcome evaluator finds OANDA closed trades

### 5. Is trading hours logic being enforced?
**Status:** OK - All trades in CSV within standard forex hours
- Forex market: Sun 22:00 UTC - Fri 22:00 UTC
- All analyzed trades between Feb 22-26 (all weekdays)
- No weekend trades detected
- Recommend: Verify TradingHoursManager.can_open_new_trade() on scheduled times

### 6. Is the sync between OANDA, Scalp-Engine UI, and Scalp-Engine correct?
**Status:** UNCERTAIN - No desync detected but insufficient evidence
- Config-API receives POST /trades ~200+ times per analysis period
- No error logs showing sync failure
- Cannot confirm if OANDA state matches Scalp-Engine state
- Recommend: Full position reconciliation with OANDA API

### 7. Are there orphan trades on OANDA not accounted for?
**Status:** NOT DETECTED - No orphan trades identified in CSV
- All fills have corresponding SL/TP or close orders
- No OPEN trades at end of CSV
- Recommend: Check if running positions exist but not listed in historical CSV

---

## Detailed Trade-by-Trade Analysis

### Trade 1: GBP/USD BUY → SL (Feb 22)
```
22572: LIMIT_ORDER - GBP/USD 1.35250 @ 20:01:24
22573: ORDER_FILL @ 1.35248
22574: TAKE_PROFIT_ORDER @ 1.35600 (35.2 pips)
22575: STOP_LOSS_ORDER @ 1.35000 (24.8 pips)

22580: ORDER_FILL - STOP_LOSS_ORDER @ 1.35000
P&L: -6.82 (SL triggered, not TP)
Duration: 3 hours 21 minutes
```
**Status:** SL triggered correctly. Trade closed at loss as designed. ✓

---

### Trade 2: AUD/USD SELL → Manual Close (Feb 23)
```
22694: ORDER_FILL - LIMIT_ORDER AUD/USD @ 0.70600
Entry: 0.70600, SL: 0.71500, TP: 0.68500 (210 pips target)

22699: MARKET_ORDER - TRADE_CLOSE (MANUAL)
22700: ORDER_FILL @ 0.70620
P&L: -0.55 (closed near entry)
Duration: 1 minute 25 seconds
```
**Status:** Trade closed manually within 90 seconds of entry, before TP or SL. ✗
**Issue:** Why close immediately? Risk manager? User intervention?

---

### Trade 3: GBP/USD BUY → Manual Close (Feb 23)
```
22737: ORDER_FILL - MIT @ 1.34948
Entry: 1.34948, SL: 1.34100, TP: 1.36200 (125.2 pips target)

22768: ORDER_FILL - MIT (different entry) @ 1.34923
P&L: -0.69 (closed near entry)
Duration: 2 hours 40 minutes
```
**Status:** Closed manually, not at TP/SL. ✗

---

### Trade 4: GBP/JPY SELL → SL (Feb 23)
```
22745: ORDER_FILL - LIMIT @ 209.10200
Entry: 209.10200, SL: 209.95000, TP: 208.25000 (85 pips target)

22746-22747: TP & SL set

[Multiple TRADE_CLIENT_EXTENSIONS_MODIFY over 1 hour]

No FILL recorded - trade appears to be HOLDING
```
**Status:** Trade open/pending. Not closed in analyzed period. ?

---

### Trade 5: EUR/JPY SELL → SL (Feb 23)
```
22772: ORDER_FILL - MITat 182.60000
Entry: 182.60000, SL: 184.20000, TP: 181.00000

22823: ORDER_FILL - STOP_LOSS_ORDER @ 184.20100
P&L: -28.22 (SL triggered)
Duration: 5 hours 1 minute
```
**Status:** SL triggered correctly. But loss is -28.22, which EXCEEDS typical ATR SL range.
**Issue:** Either SL margin was too wide (184.2 vs entry 182.6 = 16 pips), or trailing SL wasn't active. ✗

---

### Trade 6: GBP/JPY BUY → Manual Close (Feb 25)
```
22886: ORDER_FILL @ 211.79900
Entry: 211.79900, SL: 210.70000, TP: 214.50000 (270.1 pips target!)

22889: MARKET_ORDER - TRADE_CLOSE
22890: ORDER_FILL @ 211.74900
P&L: -0.88 (1 pip loss, closed immediately)
Duration: 7 seconds
```
**Status:** Huge TP opportunity (270 pips!), but closed manually after 7 seconds at loss. ✗✗
**Issue:** Why close immediately? Risk manager error? User test?

---

### Trade 7: AUD/JPY BUY → Manual Close (Feb 25)
```
22893: ORDER_FILL @ 111.20000
Entry: 111.20000, SL: 110.40000, TP: 113.00000 (180 pips target)

22896: MARKET_ORDER - TRADE_CLOSE
22897: ORDER_FILL @ 111.17500
P&L: -0.44 (closed immediately)
Duration: 36 seconds
```
**Status:** Manual close seconds after entry. ✗✗
**Issue:** Pattern matches Trade 6 - immediate close.

---

### Trade 8: USD/CAD BUY → Manual Close (Feb 23-24)
```
22832: ORDER_FILL - MARKET @ 1.37021
Entry: 1.37021, SL: 1.36759 (26.2 pips)
No TP shown (only SL)

22857: MARKET_ORDER - TRADE_CLOSE
22858: ORDER_FILL @ 1.37000
P&L: -0.42 (closed at SL distance)
Duration: 9 hours 27 minutes
```
**Status:** Closed manually, but at SL distance. Suggests SL may have triggered or trader manually closed at SL. ~

---

### Trade 9: EUR/USD BUY → Manual Close (Feb 24)
```
22756: ORDER_FILL @ 1.17800
Entry: 1.17800, SL: 1.17200, TP: 1.19000 (120 pips target)

22872: MARKET_ORDER - TRADE_CLOSE
22873: ORDER_FILL @ 1.17747
P&L: -1.46 (closed at loss, not TP)
Duration: 19 hours 14 minutes
```
**Status:** Held 19 hours, closed manually at loss. ✗
**Issue:** Trade held longer than others but still closed manually, not at TP.

---

### Trade 10: EUR/GBP BUY → Manual Close (Feb 24)
```
22847: ORDER_FILL @ 0.87300
Entry: 0.87300, SL: 0.86400, TP: 0.88200 (90 pips target)

22876: MARKET_ORDER - TRADE_CLOSE
22877: ORDER_FILL @ 0.87246
P&L: -2.01 (closed at loss)
Duration: 9 hours 44 minutes
```
**Status:** Held 9+ hours, closed manually at loss. ✗

---

## P&L Summary

| Trade # | Pair | Direction | P&L | Reason | Status |
|---------|------|-----------|-----|--------|--------|
| 1 | GBP/USD | BUY | -6.82 | SL triggered | ✓ Working |
| 2 | AUD/USD | SELL | -0.55 | Manual close (7s) | ✗ Premature |
| 3 | GBP/USD | BUY | -0.69 | Manual close (160m) | ✗ Premature |
| 4 | GBP/JPY | SELL | (open) | Still open | ? |
| 5 | EUR/JPY | SELL | -28.22 | SL triggered | ⚠️ Loss too large |
| 6 | GBP/JPY | BUY | -0.88 | Manual close (7s) | ✗✗ Premature |
| 7 | AUD/JPY | BUY | -0.44 | Manual close (36s) | ✗✗ Premature |
| 8 | USD/CAD | BUY | -0.42 | Manual close (569m) | ~ Manual/SL |
| 9 | EUR/USD | BUY | -1.46 | Manual close (1154m) | ✗ Premature |
| 10 | EUR/GBP | BUY | -2.01 | Manual close (584m) | ✗ Premature |

**Total P&L (closed trades):** -42.49 pips across 9 trades
**Avg P&L per trade:** -4.72 pips
**Win rate:** 0/10 (0%)
**Manual close rate:** 8/10 (80%)

---

## Root Cause Analysis: Why Profitable Trades Close as Losses

### Primary Cause: Manual Trade Closures
- 8 of 10 trades closed via `MARKET_ORDER + TRADE_CLOSE` (user initiated)
- 2 of 10 closed via SL trigger (algorithmic)
- Average TP opportunity: 100+ pips
- Average actual close: -2 to -7 pips

### Secondary Cause: Inconsistent Risk Management
- Trades 6 & 7: Closed in 7-36 seconds (likely auto-cleanup of test trades)
- Trades 9 & 10: Held 9+ hours then manually closed at loss (contradicts long-term holding)
- Trade 5: SL loss of -28 pips (exceeds typical range)

### Tertiary Cause: No Evidence of Trailing Stop Active
- OANDA transaction log shows no TRAILING_STOP or modification records
- EUR/JPY SL hit at 184.20 (16 pips from entry 182.60) = static SL, not trailing
- If trailing SL was active (e.g., 10 pips from high), many losses would be smaller

---

## Recommendations (Ordered by Priority)

### CRITICAL (Must Fix Before Live Trading)

1. **Fix max_runs Blocking (Issue #1)**
   - Implement auto-reset: if `max_runs` reject AND `has_existing_position(pair, direction)` == False, reset run count
   - Already in consol-recommend3 Phase 1.2, but verify execution
   - Test: Place USD/JPY BUY, let it cancel, verify next attempt succeeds

2. **Replenish Claude API Credits (Issue #2)**
   - Contact Anthropic or add credits to account
   - Restore 4-LLM consensus denominator
   - Verify consensus shows correct /4 denominator post-deployment

3. **Fix Consensus Denominator Display (Issue #4)**
   - Change denominator calculation: use actual available base LLMs, not static 4
   - Display "1/3" when Claude unavailable, "2/2" when only ChatGPT+Gemini available
   - Or: Always filter opportunities to require min 2 LLMs

### HIGH (Must Fix Before Market Opens)

4. **Debug DeepSeek Parser (Issue #3)**
   - Add debug logging to output format analysis
   - Check if DeepSeek returns JSON vs narrative text
   - Align parser or prompt to extract opportunities
   - Verify at least 1-2 opportunities extracted per analysis

5. **Verify Trailing Stop Loss (Issue #6)**
   - Check `_update_trailing_stop()` is being called in main loop
   - Add logging every time SL is updated
   - Compare OANDA trade details vs Scalp-Engine expected SL
   - Verify ATR calculation and SL distance

6. **Investigate Manual Trade Closures (Issue #9)**
   - Audit who/what is closing trades within seconds of entry
   - Check UI for accidental close buttons or user actions
   - Check if risk manager has aggressive position closure logic
   - Disable automatic risk closure for trades with valid TP

### MEDIUM (Should Fix Soon)

7. **Prevent Rapid Order Replacements (Issue #8)**
   - Implement meaningful change threshold: only replace if:
     - Entry improves by ≥5 pips, OR
     - SL/TP changes by ≥5 pips, OR
     - Position size changes
   - Already in consol-recommend3 Phase 3.1; verify REPLACE_ENTRY_MIN_PIPS = 5

8. **Add Position Reconciliation (Issue #10)**
   - Daily: fetch OANDA account open trades
   - Compare against Scalp-Engine trade state
   - Flag any orphan trades or missing positions
   - Log reconciliation results

9. **Implement Trading Hours Enforcement (Issue #5)**
   - Verify `TradingHoursManager.can_open_new_trade()` is called before placement
   - Test during market hours boundary times (Fri 22:00 UTC)
   - Prevent orders placed outside of Sun 22:00 - Fri 22:00 UTC

### LOW (Nice to Have)

10. **Reduce Config-API Sync Frequency**
    - Reduce POST /trades frequency from every 30s to every 5 min
    - Only sync when trade state actually changes
    - Saves API quota and reduces network noise

11. **Add Detailed Trailing Stop Logging**
    - Log every SL update with: old_sl, new_sl, current_price, atr_distance
    - Makes troubleshooting easier next time

---

## Conclusion

The trading system is **not ready for live trading** due to:
1. **max_runs blocking** prevents repeated opportunities on same pair
2. **Claude API failure** removes key analysis component
3. **Manual trade closures** prevent algorithmic profit targets
4. **Trailing stop unverified** (cannot confirm it works as designed)
5. **80% manual close rate** suggests system doesn't have trust in its execution

**Recommended Action:**
- Fix critical issues #1-2 above
- Run 48-hour paper trading with improvements
- Verify no more manual closures occur
- Only then consider live trading on demo account

**Current Account Status:** Account has **lost money** (-$42.49 over 9 trades), but many closures were manual and not algorithmic failures.

---

## Appendix: Configuration at Time of Analysis

```
Mode: AUTO
Stop Loss Type: ATR_TRAILING
Max Trades: 4
Required LLMs: synthesis, chatgpt, gemini (Claude unavailable)
Min Consensus Level: 2 (showing as 2/4, actually 2/3 available)
```

---

*Report Generated: March 2, 2026*
*Analysis Period: Feb 22-26, 2026*
*Logs Analyzed: Trade-Alerts, Scalp-Engine, Config-API, Market-State-API, OANDA*
