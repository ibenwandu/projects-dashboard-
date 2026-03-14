# Position Sizing Visual Guide
## Diagrams, Tables, and Quick-Start Examples

---

## 1. THE POSITION SIZING FORMULA (Visual Breakdown)

```
                    POSITION SIZE CALCULATION

    Account Balance × Risk Percentage
    ────────────────────────────────────────── = Units to Trade
    Stop Loss Distance (pips) × Pip Value

    Example: $100 account, 0.5% risk, 10 pip SL, EUR/USD

    $100 × 0.005       $0.50
    ──────────────── = ────────── = 500 units
    10 × 0.0001        $0.001


    What This Means:
    ✅ If stopped out at 10 pips, you lose $0.50 (0.5% of account)
    ✅ If target hit at 20 pips, you win $1.00 (1% of account)
    ✅ Position size automatically scales as account grows
```

---

## 2. PHASE PROGRESSION (Timeline)

```
    PHASE 1: RECOVERY          PHASE 2: PROOF             PHASE 3: GROWTH
    (Weeks 1-4)                (Weeks 5-8)                (Weeks 9+)

    Risk: 0.5% per trade       Risk: 1% per trade         Risk: 2% per trade
    ↓                          ↓                          ↓
    $0.50 per trade            $1.00 per trade            $2.00 per trade
    ↓                          ↓                          ↓
    Daily limit: $2.00         Daily limit: $2.00         Daily limit: $3.00
    ↓                          ↓                          ↓
    Goal: 40% win rate         Goal: 40% sustained        Goal: 15-20% annual
    ↓                          ↓                          ↓
    Pass: Move to Phase 2       Pass: Move to Phase 3      Pass: Compound
    Fail: Stay in Phase 1       Fail: Stay in Phase 2      Adjust as needed
```

---

## 3. DAILY LOSS CIRCUIT (Stop Trading Decision)

```
    Start of Day: $100 account

    Trade 1: -$0.50 ────→ Daily P&L: -$0.50
                         Below $2 limit? YES ✅ Continue

    Trade 2: -$0.75 ────→ Daily P&L: -$1.25
                         Below $2 limit? YES ✅ Continue

    Trade 3: -$1.00 ────→ Daily P&L: -$2.25
                         Below $2 limit? NO ❌ STOP TRADING

    ┌─────────────────────────────────────────┐
    │  🛑 DAILY LOSS LIMIT HIT               │
    │  Lost $2.25 (2.25% of account)          │
    │  Exceeds 2% limit                       │
    │  ➜ STOP TRADING FOR THE DAY             │
    │  ➜ Come back tomorrow                   │
    │  ➜ Review what happened                 │
    └─────────────────────────────────────────┘
```

---

## 4. CONSECUTIVE LOSS CIRCUIT BREAKER

```
    Trade 1: LOSS    ──→ Counter: 1/5  ✅ Continue
    Trade 2: LOSS    ──→ Counter: 2/5  ✅ Continue
    Trade 3: LOSS    ──→ Counter: 3/5  ✅ Continue
    Trade 4: LOSS    ──→ Counter: 4/5  ✅ Continue
    Trade 5: LOSS    ──→ Counter: 5/5  ❌ CIRCUIT BREAKER TRIGGERED

    ┌─────────────────────────────────────────────┐
    │  🚨 CIRCUIT BREAKER ACTIVATED              │
    │  5 consecutive losses detected              │
    │  This suggests:                             │
    │  • Market regime changed                    │
    │  • Your setup no longer working             │
    │  • System needs review                      │
    │                                             │
    │  ACTION: STOP TRADING & ANALYZE             │
    └─────────────────────────────────────────────┘

    Note: Winning 1 trade resets the counter to 0
    Example: L, L, L, W, L → Counter goes: 1, 2, 3, 0, 1 (starts over)
```

---

## 5. WIN RATE vs PROFITABILITY MATRIX

```
    Can you be profitable with <50% win rate?

    ┌──────────────────────────────────────────────────────────┐
    │ WIN RATE │ RISK:REWARD │ RESULT    │ EXAMPLE            │
    ├──────────────────────────────────────────────────────────┤
    │ 25%      │ 1:3         │ ✅ PROFIT │ Win $3 for loss $1 │
    │ 33%      │ 1:2         │ ✅ PROFIT │ Win $2 for loss $1 │
    │ 40%      │ 1:1.5       │ ✅ PROFIT │ Win $1.50 per loss │
    │ 40%      │ 1:2         │ ✅ GOOD   │ Win $2 per loss    │
    │ 50%      │ 1:1         │ ⚠️  BREAK │ Win equals loss    │
    │ 50%      │ 1:1.5       │ ✅ SMALL  │ Slight profit      │
    │ 60%      │ 1:1         │ ✅ PROFIT │ More wins than loss│
    │  0%      │ ANY         │ ❌ LOSS   │ Always lose        │
    └──────────────────────────────────────────────────────────┘

    ➜ Your Target: 40% win rate with 1:2 risk:reward
    ➜ This equals 5R profit per 10 trades = sustainable
```

---

## 6. POSITION SIZE TABLE BY ACCOUNT SIZE

```
    Quick lookup table for 0.5%, 1%, and 2% risk

    For EUR/USD (most common): Pip value = 0.0001

    ┌─────────────────────────────────────────────────────────┐
    │ ACCOUNT │ 0.5% RISK │ 1% RISK  │ 2% RISK   │ PHASE      │
    ├─────────────────────────────────────────────────────────┤
    │ $100    │ $0.50     │ $1.00    │ $2.00     │            │
    │ $125    │ $0.63     │ $1.25    │ $2.50     │            │
    │ $150    │ $0.75     │ $1.50    │ $3.00     │            │
    │ $200    │ $1.00     │ $2.00    │ $4.00     │            │
    │ $250    │ $1.25     │ $2.50    │ $5.00     │            │
    │ $500    │ $2.50     │ $5.00    │ $10.00    │            │
    │ $1,000  │ $5.00     │ $10.00   │ $20.00    │            │
    └─────────────────────────────────────────────────────────┘

    Position units at 10-pip stop loss (EUR/USD):
    ┌─────────────────────────────────────────────────────────┐
    │ ACCOUNT │ 0.5% RISK │ 1% RISK  │ 2% RISK                │
    ├─────────────────────────────────────────────────────────┤
    │ $100    │ 500 units │ 1K units │ 2K units               │
    │ $200    │ 1K units  │ 2K units │ 4K units               │
    │ $500    │ 2.5K      │ 5K units │ 10K units              │
    └─────────────────────────────────────────────────────────┘

    K = thousands (1K = 1,000 units = 0.01 micro lots)
```

---

## 7. ACCOUNT SURVIVAL CHART (At Different Risk Levels)

```
    How many consecutive losses can you survive?

    Account: $100

    At 0.5% risk per trade ($0.50 loss per trade):
    ├─ Loss 1: $99.50 remaining ✅
    ├─ Loss 2: $99.00 remaining ✅
    ├─ Loss 3: $98.50 remaining ✅
    ├─ Loss 4: $98.00 remaining ✅
    ├─ Loss 5: $97.50 remaining ✅
    ├─ ...
    └─ Loss 20: $90.00 remaining ✅ (Still alive!)

    At 1% risk per trade ($1.00 loss per trade):
    ├─ Loss 1: $99.00 remaining ✅
    ├─ Loss 2: $98.00 remaining ✅
    ├─ Loss 3: $97.00 remaining ✅
    ├─ Loss 4: $96.00 remaining ✅
    ├─ Loss 5: $95.00 remaining ✅
    ├─ ...
    └─ Loss 10: $90.00 remaining ✅

    At 5% risk per trade ($5.00 loss per trade):
    ├─ Loss 1: $95.00 remaining ✅
    ├─ Loss 2: $90.00 remaining ✅
    ├─ Loss 3: $85.00 remaining ✅
    ├─ Loss 4: $80.00 remaining ✅
    ├─ Loss 5: $75.00 remaining ✅ ← Circuit breaker triggers
    ├─ Loss 6: $70.00 remaining (if ignored) ⚠️
    ├─ ...
    └─ Loss 20: $0.00 remaining ❌ ACCOUNT BLOWN UP

    ➜ At 0.5% risk: Can lose $0.50 × 20 = $10 (90% survival)
    ➜ At 1% risk: Can lose $1.00 × 10 = $10 (90% survival)
    ➜ At 5% risk: Can lose $5.00 × 2 = $10 (90% survival) — BUT ONLY 2 TRADES!
```

---

## 8. MONTHLY PROFIT PROJECTION (By Phase and Win Rate)

```
    Assumptions: 20 trading days/month, 3 trades/day, 1:2 R:R ratio

    PHASE 1: 0.5% RISK ($0.50 per trade)
    ┌────────────────────────────────────────────┐
    │ Win Rate │ Monthly P&L │ Monthly Return    │
    ├────────────────────────────────────────────┤
    │ 30%      │ -$3.00      │ -3% ❌            │
    │ 40%      │ +$9.00      │ +9% ✅            │
    │ 50%      │ +$15.00     │ +15% ✅           │
    │ 60%      │ +$21.00     │ +21% ✅ Excellent │
    └────────────────────────────────────────────┘

    PHASE 2: 1% RISK ($1.00 per trade)
    ┌────────────────────────────────────────────┐
    │ Win Rate │ Monthly P&L │ Monthly Return    │
    ├────────────────────────────────────────────┤
    │ 30%      │ -$6.00      │ -6% ❌            │
    │ 40%      │ +$18.00     │ +18% ✅           │
    │ 50%      │ +$30.00     │ +30% ✅ Very Good │
    │ 60%      │ +$42.00     │ +42% ✅ Excellent │
    └────────────────────────────────────────────┘

    PHASE 3: 2% RISK ($2.00 per trade)
    ┌────────────────────────────────────────────┐
    │ Win Rate │ Monthly P&L │ Monthly Return    │
    ├────────────────────────────────────────────┤
    │ 40%      │ +$36.00     │ +36% ✅           │
    │ 50%      │ +$60.00     │ +60% ✅ Very Good │
    │ 60%      │ +$84.00     │ +84% ✅ Excellent │
    └────────────────────────────────────────────┘

    ➜ You need 40%+ win rate in Phase 2-3 to be profitable
    ➜ Phase 1 can survive at 30% (but not profitable)
    ➜ Profitability only happens with 40%+ win rate
```

---

## 9. DECISION TREE: SHOULD I PLACE THIS TRADE?

```
    ┌─────────────────────────────────────┐
    │  Is there a STOP LOSS defined?      │
    │  NO ──────────────────┐             │
    └─────────────────────────────────────┘
              │ YES
              ↓
    ┌─────────────────────────────────────┐
    │  Is CONSENSUS ≥ 2/3 (or 2/4)?       │
    │  NO ──────────────────┐             │
    └─────────────────────────────────────┘
              │ YES
              ↓
    ┌─────────────────────────────────────┐
    │  Is current price ≤ 100 pips from   │
    │  recommended entry?                  │
    │  NO ──────────────────┐             │
    └─────────────────────────────────────┘
              │ YES
              ↓
    ┌─────────────────────────────────────┐
    │  Have you lost < 2% today?          │
    │  NO ──────────────────┐             │
    └─────────────────────────────────────┘
              │ YES
              ↓
    ┌─────────────────────────────────────┐
    │  Have you had < 5 consecutive losses?│
    │  NO ──────────────────┐             │
    └─────────────────────────────────────┘
              │ YES
              ↓
         ✅ TRADE IS VALID

         Calculate Position Size:
         Units = (Account × Risk%) / (SL × Pip Value)

         Place order and monitor

    ────────────────────────────────────────

    All "NO" branches lead to: ❌ SKIP THIS TRADE

    Trading is about skipping bad trades, not chasing every signal.
```

---

## 10. THE RISK MANAGEMENT PYRAMID

```
    Risk Management Hierarchy (in order of importance)

              ┌─────────────────────────────┐
              │  STOP LOSS ALWAYS REQUIRED  │ (Layer 1)
              │  100% of trades must have   │
              │  predefined stop loss       │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────────┐
              │  FIXED POSITION SIZING      │ (Layer 2)
              │  Same % risk per trade      │
              │  No emotion-based sizing    │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────────┐
              │  DAILY LOSS LIMITS          │ (Layer 3)
              │  2% daily loss = STOP       │
              │  Prevents revenge trading   │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────────┐
              │  CIRCUIT BREAKER (5 losses) │ (Layer 4)
              │  System needs review        │
              │  Take break & recalibrate   │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────────┐
              │  VOLATILITY ADJUSTMENT      │ (Layer 5)
              │  ATR-based sizing (Phase 2) │
              │  Adapt to market conditions │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────────┐
              │  COMPOUNDING STRATEGY       │ (Layer 6)
              │  Reinvest profits safely    │
              │  Long-term account growth   │
              └─────────────────────────────┘

    Build from bottom up. Don't skip layers.
```

---

## 11. COMMON MISTAKES VISUAL

```
    MISTAKE 1: Increasing Size After Loss
    ╔═══════════════════════════════════════════╗
    ║  Trade 1: -$0.50 (sized 0.5%)             ║
    ║  Trade 2: -$1.00 (sized 1.0% - WRONG!)    ║
    ║  Trade 3: -$2.00 (sized 2% - VERY WRONG!) ║
    ║  Result: Lost $3.50 instead of $1.50      ║
    ║  ❌ This accelerates losses                ║
    ╚═══════════════════════════════════════════╝

    MISTAKE 2: No Stop Loss
    ╔═══════════════════════════════════════════╗
    ║  Entry: 1.0850                            ║
    ║  No SL set "I'll exit manually"           ║
    ║  Market drops to 1.0700                   ║
    ║  Loss: 1,500 pips = $1,500 (15x account)  ║
    ║  ❌ Account blown up in one trade          ║
    ╚═══════════════════════════════════════════╝

    MISTAKE 3: Ignoring Daily Limits
    ╔═══════════════════════════════════════════╗
    ║  Daily loss already: $2.00 (2%)           ║
    ║  New signal appears                       ║
    ║  "Just one more" → -$1.00 more             ║
    ║  Daily loss now: $3.00 (3%)               ║
    ║  ❌ Revenge trading due to emotion        ║
    ╚═══════════════════════════════════════════╝

    MISTAKE 4: Wrong Risk:Reward Ratio
    ╔═══════════════════════════════════════════╗
    ║  Entry: 1.0850                            ║
    ║  SL: 1.0840 (10 pips) = Risk $0.50        ║
    ║  TP: 1.0851 (1 pip) = Profit $0.05        ║
    ║  R:R Ratio: 1:0.1 (terrible!)             ║
    ║  Need 90%+ win rate to profit              ║
    ║  ❌ Math doesn't work                      ║
    ╚═══════════════════════════════════════════╝

    MISTAKE 5: Over-Leveraging
    ╔═══════════════════════════════════════════╗
    ║  Account: $100                            ║
    ║  Using 50:1 leverage = $5,000 exposure    ║
    ║  2% market move = $100 loss = Account gone║
    ║  ❌ One bad move = total loss              ║
    ╚═══════════════════════════════════════════╝
```

---

## 12. WEEKLY CHECKLIST

```
    Every Friday, answer these questions:

    ┌──────────────────────────────────────────┐
    │ WEEKLY PERFORMANCE CHECKLIST              │
    ├──────────────────────────────────────────┤
    │ □ Win rate ≥ 40%?                         │
    │   ├─ YES → On track                       │
    │   └─ NO → System needs improvement        │
    │                                           │
    │ □ Followed position sizing every trade?   │
    │   ├─ YES → Good discipline                │
    │   └─ NO → Review emotion/manual sizing    │
    │                                           │
    │ □ Respected daily loss limits?            │
    │   ├─ YES → Good risk management           │
    │   └─ NO → Implement automatic stops       │
    │                                           │
    │ □ Max drawdown < 20%?                     │
    │   ├─ YES → Account healthy                │
    │   └─ NO → Consider reducing risk %        │
    │                                           │
    │ □ All trades had stop losses?             │
    │   ├─ YES → 100% coverage                  │
    │   └─ NO → Never skip this requirement     │
    │                                           │
    │ □ Logged all trades with P&L?             │
    │   ├─ YES → Data for analysis              │
    │   └─ NO → Start this week                 │
    │                                           │
    │ □ Calculated profit factor?               │
    │   (Gross Profit / Gross Loss)              │
    │   ├─ > 1.5 → Good                         │
    │   ├─ 1.2-1.5 → OK                         │
    │   └─ < 1.2 → Review setup quality         │
    └──────────────────────────────────────────┘

    Score:
    7/7 ✅ Excellent - Ready to scale up
    6/7 ✅ Good - Stay in current phase
    5/7 ⚠️  Fair - Tighten discipline
    <5 ❌ Needs work - Don't scale yet
```

---

## 13. POSITION SIZING FORMULA CHEAT SHEET

```
    Copy this formula in your trading platform notes:

    ┌──────────────────────────────────────────────────────┐
    │ POSITION SIZE = (ACCOUNT × RISK%) / (SL × PIP_VAL)  │
    │                                                      │
    │ Example:                                            │
    │ ($100 × 0.005) / (10 × 0.0001)                     │
    │ = $0.50 / $0.001                                   │
    │ = 500 units                                         │
    │                                                      │
    │ What this means:                                    │
    │ • If stopped: Lose $0.50                           │
    │ • If target (2×SL): Win $1.00                      │
    │ • R:R Ratio = 1:2 ✅                                │
    └──────────────────────────────────────────────────────┘

    PIP VALUES (Don't forget!):
    • EUR/USD, GBP/USD, AUD/USD, etc. = 0.0001
    • All JPY pairs (EUR/JPY, GBP/JPY, etc.) = 0.01
```

---

## 14. PHASE TRANSITION CRITERIA

```
    PHASE 1 → PHASE 2 Transition:

    ✅ REQUIRED (all must be true):
    ├─ 50+ trades completed
    ├─ Win rate ≥ 40%
    ├─ 100% stop loss coverage
    ├─ Max drawdown ≤ 15%
    ├─ Account still ≥ $95 (lost <5%)
    └─ Circuit breaker triggered ≤ 1 time

    ✅ RECOMMENDED (nice to have):
    ├─ Profit factor > 1.3
    ├─ Win rate ≥ 45%
    ├─ 100+ trades (more data)
    └─ 5+ winning days (psychology boost)

    ═══════════════════════════════════════════

    PHASE 2 → PHASE 3 Transition:

    ✅ REQUIRED (all must be true):
    ├─ 100+ trades completed
    ├─ Win rate ≥ 40% sustained
    ├─ Profit factor ≥ 1.5
    ├─ Account ≥ $120 (20%+ growth)
    ├─ Max drawdown ≤ 20%
    └─ 0 account blowups in Phase 2

    ✅ RECOMMENDED (nice to have):
    ├─ Win rate ≥ 45%
    ├─ Profit factor ≥ 1.7
    ├─ 200+ trades (strong track record)
    └─ Consistent monthly returns
```

---

## 15. YEAR 1 GROWTH PROJECTION

```
    Starting: $100
    Phase 1 (0.5% risk): Months 1-2
    Phase 2 (1% risk): Months 3-8
    Phase 3 (2% risk): Months 9-12

    Assumptions: 40% win rate, 1:2 R:R, 60 trades/month

    Month 1  (Phase 1, 0.5%): $100 → $109  (+9%)
    Month 2  (Phase 1, 0.5%): $109 → $119  (+9%)
    Month 3  (Phase 2, 1%):   $119 → $140  (+18%)
    Month 4  (Phase 2, 1%):   $140 → $165  (+18%)
    Month 5  (Phase 2, 1%):   $165 → $195  (+18%)
    Month 6  (Phase 2, 1%):   $195 → $230  (+18%)
    Month 7  (Phase 2, 1%):   $230 → $272  (+18%)
    Month 8  (Phase 2, 1%):   $272 → $321  (+18%)
    Month 9  (Phase 3, 2%):   $321 → $415  (+29%)
    Month 10 (Phase 3, 2%):   $415 → $536  (+29%)
    Month 11 (Phase 3, 2%):   $536 → $692  (+29%)
    Month 12 (Phase 3, 2%):   $692 → $894  (+29%)

    Year 1 Total: $100 → $894 (8.94× growth! 794% return)

    ⚠️ NOTE: This assumes:
    • No failures during any phase
    • 40% win rate throughout
    • All discipline rules followed
    • No major market disruptions
    • Position sizing 100% correct

    Realistic Scenario (90% execution):
    • Month 1-2: $100 → $115 (hit 35% win rate)
    • Month 3-8: $115 → $220 (achieve 40% target)
    • Month 9-12: $220 → $420 (compound growth)

    Year 1 Real: $100 → $420 (4.2× growth, 320% return)
    Still excellent for a demo account!
```

---

## KEY TAKEAWAYS (One-Pager)

```
    ┌───────────────────────────────────────────────────────┐
    │ POSITION SIZING: THE ONE-PAGE SUMMARY                │
    ├───────────────────────────────────────────────────────┤
    │                                                       │
    │ 1️⃣ FORMULA (Memorize This)                           │
    │    Position = (Account × Risk%) / (SL × Pip_Value)   │
    │                                                       │
    │ 2️⃣ STANDARD RISK AMOUNTS                             │
    │    Phase 1: 0.5%  Phase 2: 1.0%  Phase 3: 2.0%       │
    │                                                       │
    │ 3️⃣ DAILY LOSS LIMIT                                  │
    │    After losing 2% of account → STOP TRADING         │
    │                                                       │
    │ 4️⃣ CIRCUIT BREAKER                                   │
    │    After 5 consecutive losses → STOP & REVIEW        │
    │                                                       │
    │ 5️⃣ PROFITABILITY REQUIREMENT                         │
    │    Need 40%+ win rate with 1:2 risk:reward ratio     │
    │                                                       │
    │ 6️⃣ MANDATORY REQUIREMENT                             │
    │    EVERY TRADE MUST HAVE A STOP LOSS (100%)          │
    │                                                       │
    │ 7️⃣ PHASE TRANSITIONS                                 │
    │    Phase 1→2: 50+ trades at 40% WR                   │
    │    Phase 2→3: 100+ trades at 40% WR + profit         │
    │                                                       │
    │ 8️⃣ YEAR 1 GOAL                                       │
    │    From $100 → $400-900 (by scaling phases correctly)│
    │                                                       │
    └───────────────────────────────────────────────────────┘
```

---

**Last Updated**: March 6, 2026
**For detailed explanations**: See `POSITION_SIZING_RISK_MANAGEMENT.md`
**For code implementation**: See `POSITION_SIZING_IMPLEMENTATION.md`
**For quick reference during trading**: See `POSITION_SIZING_QUICK_REFERENCE.md`
