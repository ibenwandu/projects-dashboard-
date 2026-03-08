# Position Sizing Quick Reference
## Trade-Alerts Risk Management Cheat Sheet

**Use this during live trading.** For full context, see `POSITION_SIZING_RISK_MANAGEMENT.md`.

---

## QUICK CALCULATIONS

### Position Size Formula (Memorize This)

```
Position Units = (Account × Risk %) / (Stop Loss Pips × Pip Value)
```

**Example: $100 account, 0.5% risk, 10 pips SL, EUR/USD**

```
Position = ($100 × 0.005) / (10 × 0.0001)
         = $0.50 / $0.001
         = 500 units
```

### Pip Values by Pair

| Pair Type | Pip Value | Formula |
|-----------|-----------|---------|
| Most pairs (EUR/USD, GBP/USD, etc.) | 0.0001 | Standard |
| JPY pairs (EUR/JPY, GBP/JPY, etc.) | 0.01 | 0.01 for JPY |
| Cryptocurrencies | Varies | Case-by-case |

---

## PHASE-BASED POSITION SIZING

### Phase 1: Recovery (Weeks 1-4) — Current

```
Risk per Trade: 0.5% ($0.50 per $100)
Formula: Position = (Account × 0.005) / (SL Pips × Pip Value)
Take Profit: 2× stop loss distance (1:2 ratio)
Daily Limit: 2% loss = STOP
Circuit Breaker: 5 losses in a row = STOP
```

**Example on $100 account:**
- Stop Loss: 10 pips → Position: 500 units → Risk: $0.50 → Profit: $1.00
- Stop Loss: 20 pips → Position: 250 units → Risk: $0.50 → Profit: $1.00
- Stop Loss: 50 pips → Position: 100 units → Risk: $0.50 → Profit: $1.00

### Phase 2: Proof (Weeks 5-8) — After 40% Win Rate

```
Risk per Trade: 1.0% ($1.00 per $100)
Formula: Position = (Account × 0.01) / (SL Pips × Pip Value)
Take Profit: 1.5-2× stop loss
Daily Limit: 2% loss = STOP
Circuit Breaker: 5 losses in a row = STOP
```

### Phase 3: Growth (Weeks 9+) — After 100+ Trades at 40%

```
Risk per Trade: 2.0% ($2.00 per $100)
Formula: Position = (Account × 0.02) / (SL Pips × Pip Value)
Take Profit: 1.5× stop loss (lower ratio is OK at high win rate)
Daily Limit: 3% loss = STOP
Circuit Breaker: 5 losses in a row = STOP
```

---

## DECISION TABLE: SHOULD I TRADE THIS?

Before placing each trade, check:

| Check | Requirement | Status |
|-------|-------------|--------|
| Stop Loss Set? | EVERY trade must have SL | ✅ Required |
| Consensus Level | ≥ 2 out of 3+ LLMs | ✅ Check market state |
| Stale Price? | Current price ≤ 100 pips from entry | ✅ Check age |
| Margin Available? | Enough for position size? | ✅ Check account |
| Daily Loss Limit? | Not yet hit 2% loss for day? | ✅ Track P&L |
| Consecutive Losses? | Not yet 5 in a row? | ✅ Track losses |
| Trading Hours? | Not weekend/low liquidity? | ✅ Check calendar |

**If ANY item fails → SKIP THE TRADE**

---

## QUICK RISK ASSESSMENT

### Risk per Trade

| Account | 0.5% Risk (Phase 1) | 1% Risk (Phase 2) | 2% Risk (Phase 3) |
|---------|------------------|-----------------|-----------------|
| $100 | $0.50 | $1.00 | $2.00 |
| $150 | $0.75 | $1.50 | $3.00 |
| $250 | $1.25 | $2.50 | $5.00 |
| $500 | $2.50 | $5.00 | $10.00 |
| $1,000 | $5.00 | $10.00 | $20.00 |

### Position Sizing at Different Stop Losses

**$100 Account at 0.5% Risk ($0.50):**

| SL Distance | EUR/USD Units | GBP/USD Units | USD/JPY Units |
|-------------|---------------|---------------|---------------|
| 5 pips | 1,000 | 1,000 | 50 |
| 10 pips | 500 | 500 | 25 |
| 20 pips | 250 | 250 | 12 |
| 50 pips | 100 | 100 | 5 |
| 100 pips | 50 | 50 | 3 |

---

## DAILY MONEY MANAGEMENT

### Start of Day

```
Account Balance: ________
Risk per Trade: _________ (0.5% Phase 1, 1% Phase 2, 2% Phase 3)
Daily Loss Limit: _________ (2% of account)
Trades Allowed Today: ______ (until daily limit hit)
Consecutive Loss Counter: 0
```

### After Each Trade

```
Trade Result: WIN / LOSS
P&L: $ ________
Daily P&L So Far: $ ________
Consecutive Losses: ____

CHECKS:
□ Below daily loss limit? (YES → Continue, NO → STOP)
□ Under 5 consecutive losses? (YES → Continue, NO → STOP)
□ Above minimum trading hours? (YES → Continue, NO → STOP)
```

### Daily Checklist

- [ ] Checked account balance
- [ ] Confirmed risk percentage (0.5% / 1% / 2%)
- [ ] Set daily loss limit (2-3% of account)
- [ ] Verified consensus for each trade (≥2)
- [ ] Checked stop loss exists (100% requirement)
- [ ] Monitored daily P&L throughout day
- [ ] Stopped after 2% loss
- [ ] Stopped after 5 consecutive losses
- [ ] Logged trades with entry, exit, reason, P&L
- [ ] Updated account balance at end of day

---

## STOP LOSS RULES (NON-NEGOTIABLE)

### Rule 1: Every Trade Gets a Stop Loss

```
NO exceptions. NO "I'll exit manually later." NO "market's fine."

Every. Single. Trade. Must. Have. A. Stop. Loss.

If your system can't place a stop loss, DO NOT TRADE.
```

### Rule 2: Stop Loss at Predefined Distance

**Based on strategy/market:**
- Entry Rejection Trades: 20-50 pips
- EMA Ribbon Trades: 30-100 pips (depends on timeframe)
- Fisher Transform Trades: 15-40 pips
- DMI-EMA Trades: 25-60 pips

**Do NOT pick arbitrary numbers. Use historical data or ATR.**

### Rule 3: Maximum Stop Loss Distance

For $100 account at 0.5% risk:
```
Maximum SL distance = $0.50 / (0.0001 × min_pair_unit)
                   = 50-100 pips for most pairs
```

**If best trade has 200-pips SL → Skip it (too much risk)**

### Rule 4: Trailing Stops for Winning Trades

Once trade is profitable:
- Trail stop at 50% of current profit
- Example: Winning by $1.00 → Trail at -$0.50
- Locks in 50% gain, lets winner run

---

## TAKE PROFIT RULES

### Rule 1: Set Take Profit at Entry

**Do NOT wait for "good entry" then set TP. Set at entry.**

### Rule 2: Risk-Reward Ratios

| Current Win Rate | Min R:R Ratio | Target R:R | Example |
|------------------|---------------|-----------|---------|
| 0% (in recovery) | 1:2 | 1:3 | SL=10p, TP=30p |
| 25-35% | 1:2.5 | 1:3 | SL=10p, TP=30p |
| 40%+ | 1:1.5 | 1:2 | SL=10p, TP=20p |
| 50%+ | 1:1 | 1:1.5 | SL=10p, TP=15p |

### Rule 3: Multiple Take Profit Targets (Optional)

For larger trades:
```
Entry: 1.0850
TP 1: 1.0860 (20% of position, 10 pip target)
TP 2: 1.0880 (30% of position, 30 pip target)
TP 3: 1.0910 (50% of position, 60 pip target)

Average R:R: 1:2.5 (favorable)
```

---

## WHEN TO STOP TRADING

### Stop Signal 1: Daily Loss Limit

```
Account: $100
Daily Loss Limit: 2% = $2.00

Trade 1: Loss -$0.50 → Daily P&L: -$0.50 (can continue)
Trade 2: Loss -$0.75 → Daily P&L: -$1.25 (can continue)
Trade 3: Loss -$1.00 → Daily P&L: -$2.25 (STOP, exceeded limit)
```

**Action: STOP TRADING for the day. Come back tomorrow.**

### Stop Signal 2: Consecutive Losses

```
Trade 1: LOSS → Counter: 1
Trade 2: LOSS → Counter: 2
Trade 3: LOSS → Counter: 3
Trade 4: LOSS → Counter: 4
Trade 5: LOSS → Counter: 5 ← STOP TRADING

Circuit breaker triggered. System may have issue.
Review and restart next day.
```

**Action: STOP TRADING. Review what went wrong.**

### Stop Signal 3: Technical Issues

```
- Stop loss not executing (test)
- Position size calculations wrong
- OANDA API errors
- Market condition changed (trending vs ranging)
```

**Action: STOP TRADING. Debug before resuming.**

---

## WIN RATE TARGETS BY PHASE

| Phase | Duration | Min Win Rate | Target Win Rate | Profit Target |
|-------|----------|-------------|-----------------|----------------|
| **1. Recovery** | 4 weeks | 25% | 40%+ | 0% (just survive) |
| **2. Proof** | 4 weeks | 35% | 40%+ | +2-5% |
| **3. Growth** | Ongoing | 40%+ | 40%+ | +15-20% annual |

**If you don't achieve target win rate by end of phase → STAY IN CURRENT PHASE**

---

## COMMON MISTAKES TO AVOID

### ❌ Mistake 1: Increasing Position Size After Loss

```
Loss of $0.50 → "Let me double size next trade to recover"
Next trade: Risk $2.00 instead of $0.50 (4× increase)
Result: Another loss of $2.00 (you just doubled your loss)

WRONG. Use FIXED position sizing. Always.
```

### ❌ Mistake 2: Lowering Stop Loss to Avoid Loss

```
Entry: 1.0850
Initial SL: 1.0840 (10 pips)
Price drops to 1.0845
"I'll move SL to 1.0843 (2 pips) to stay in"

WRONG. SL was calculated for risk management.
Moving it increases risk. If trade is bad, take loss.
```

### ❌ Mistake 3: No Take Profit (Hoping for More)

```
TP was 1.0870 (profit $1.00)
Price reaches 1.0870 but you don't close
Hoping for 1.0900, but price reverses to 1.0820
Result: $3.00 loss instead of $1.00 gain

WRONG. Set TP at entry. Let it execute.
```

### ❌ Mistake 4: Trading Low Consensus

```
Consensus: 1/3 (only 1 LLM agrees)
"But this feels like a good trade"

WRONG. Need ≥2 consensus. Single LLM opinions skip.
```

### ❌ Mistake 5: Ignoring Daily Limits

```
Daily loss already: -2% ($2.00)
New opportunity comes up: "Just one more trade"

WRONG. Daily limit exists for reason.
Trading while emotional leads to revenge trading.
STOP. Come back tomorrow.
```

---

## MONTHLY PLANNING

### Week 1-2: Adjust Position Sizing

- Check win rate from last month
- Decide: Stay in phase or move to next phase?
- Update risk percentage in config
- Document adjustment in log

### Week 3: Monitor Progress

- Track daily P&L
- Count wins vs losses
- Calculate win rate so far
- Check max drawdown from peak

### Week 4: Analyze & Plan

- Calculate monthly return
- Identify best pairs (win rate > 50%)
- Identify worst pairs (win rate < 25%)
- Plan next month's focus

---

## QUICK PROFIT PROJECTIONS

### Phase 1 Conservative (0.5% risk, 40% win rate, 1:2 ratio)

```
Base account: $100
Trades per day: 3
Trading days per month: 20
Total monthly trades: 60

60 trades × 40% win rate = 24 wins
24 wins × $1.00 avg profit = $24.00 profit
Monthly return: 24% (very good)

Year 1: $100 → $312 (growth factor 3.1x)
```

### Phase 2 Standard (1% risk, 40% win rate, 1:2 ratio)

```
Base account: $125 (after Phase 1)
Same frequency: 60 trades/month

60 trades × 40% win rate = 24 wins
24 wins × $2.50 avg profit = $60.00 profit
Monthly return: 48% (exceptional)

Year 1: $125 → $1,022 (growth factor 8.2x)
```

### Phase 3 Growth (2% risk, 40% win rate, 1:2 ratio)

```
Base account: $250 (after Phase 2)
Same frequency: 60 trades/month

60 trades × 40% win rate = 24 wins
24 wins × $5.00 avg profit = $120.00 profit
Monthly return: 48%

Year 1: $250 → $2,044 (growth factor 8.2x)
```

**Note**: These assume 40% win rate is maintained. With 0% win rate, projections are negative.

---

## CHECKLIST BEFORE GOING LIVE

Before trading real money:

- [ ] Tested position sizing on demo for 50+ trades
- [ ] Achieved 40%+ win rate on demo
- [ ] All trades have stop losses (100%)
- [ ] Daily loss limits working
- [ ] Circuit breaker working (5 losses stop)
- [ ] Position size calculations verified (no errors)
- [ ] Risk calculations checked (matches formula)
- [ ] Trade logging working (for analysis)
- [ ] Account balance tracking accurate
- [ ] Team notified of position sizing rules
- [ ] Agreed not to exceed 1% risk until 40% win rate proven

**Only proceed to live trading if ALL boxes checked.**

---

## EMERGENCY NUMBERS

Keep these visible during trading:

```
Daily Loss Limit (2% of account): $ _________
Max Consecutive Losses (circuit breaker): 5 losses
Max Drawdown (account review trigger): 20%
Min Consensus Level: 2/3 agreements
Max Position Size: Risk / (SL_pips × pip_value)
Min Take Profit Ratio: 1:2 (SL distance × 2)
```

---

## QUICK REFERENCE BY SITUATION

### "I have a great trade setup"

1. Check consensus: ≥ 2? ✅ Proceed, ❌ Skip
2. Check stop loss: Defined? ✅ Proceed, ❌ Skip
3. Check price age: < 100 pips away? ✅ Proceed, ❌ Skip
4. Check daily limit: Below 2% loss? ✅ Proceed, ❌ Skip
5. Calculate position: Units = (Risk %) / (SL_pips × pip_val)
6. Calculate profit: SL distance × 2 = TP distance
7. Place order: Entry + SL + TP

### "I'm on a losing streak"

1. Count consecutive losses
2. If < 5: Can trade (but be cautious)
3. If ≥ 5: STOP TRADING for the day
4. Review: What changed? Market condition? Setup quality?
5. Log: Write down what happened
6. Restart: Tomorrow, analyze logs first

### "I'm down 2% for the day"

1. STOP TRADING
2. No exceptions
3. Come back tomorrow
4. This prevents revenge trading
5. Let emotions cool overnight

### "Should I increase position size?"

**Phase 1 (40% win rate emerging)**
- Current risk: 0.5%
- Move to 1% ONLY after 100+ trades at 40%+

**Phase 2 (100+ trades at 40%)**
- Current risk: 1%
- Move to 2% ONLY after 40% win rate + positive profit factor

**Phase 3 (200+ trades at 40%)**
- Current risk: 2%
- Stay at 2% for next 100 trades
- Only increase after another 200+ trades of proof

---

## CONTACT & ESCALATION

If unsure about:
- **Position size**: Calculate using formula above, verify with trade log
- **Risk %**: Use phase table (Phase 1 = 0.5%, Phase 2 = 1%)
- **Take profit**: Use 2× stop loss distance (1:2 ratio)
- **When to stop**: Daily loss 2% or 5 consecutive losses

**Document your decision. Check later to improve.**

---

**Last Updated**: March 6, 2026
**For detailed explanations**: See `POSITION_SIZING_RISK_MANAGEMENT.md`
