# Exit Strategy Quick Reference
## One-Page Summary for Trade-Alerts

---

## The Problem
Your trades are identified correctly but **closed too early**, converting winners into losses.

**Evidence**: Trades move in correct direction → closed as losses instead of at take-profit

**Root Cause**: No systematic exit strategy; emotional/manual closures prevent trades from reaching targets

---

## The Solution: Half-and-Run Strategy

### How It Works
```
Position: 100% (e.g., 100k EUR/USD)
├─ 50% Position (50k)  → CLOSE at 1.5x risk (automatic limit order)
└─ 50% Position (50k)  → TRAIL with stop (follow price up, protect capital)
```

### Example Trade
```
EUR/USD LONG
Entry:     1.0850
Risk:      50 pips (SL at 1.0800)

50% Close:  1.0925 (1.5x risk)
50% Trail:  ATR-based trailing stop
            Follows price up, stops at ATR×1.0 distance
            Exit when: EMA crosses OR Max time (4 hours) OR Reverses
```

### Expected Outcome
- **First 50% result**: +75 pips (1.5x return) - **LOCKED IN IMMEDIATELY**
- **Runner 50% result**: Average +100-150 pips (2-3x return) - **CAPTURES BIG MOVES**
- **Average winner**: 1.5x+2.5x = 2.0x return per trade

---

## Key Exit Strategies by Type

| Type | Entry | First TP | Runner Exit | Max Time |
|------|-------|----------|-------------|----------|
| **Intraday** | LLM opportunity | 1.5x risk | Trailing stop or EMA | 4 hours |
| **Swing** | LLM opportunity | 2.0x risk | Trailing stop or SR level | 3 days |
| **Trending** | Breakout/EMA | 1.5x risk | Trailing stop | Unlimited |
| **Ranging** | Support/Resistance | SR level | Tight trail or SL | 2 hours |

---

## Exit Decision Tree

```
Trade Opens
    ↓
Price Reaches First TP (1.5x risk)?
├─ YES → Close 50% (FIRST_HALF) → Profit locked ✓
│        Move stop to breakeven
│        Continue with 50% (RUNNER)
│
└─ NO → Continue to next check
        ↓
        Time Exceeded (4 hours)?
        ├─ YES → Close entire position
        │
        └─ NO → Continue to next check
                ↓
                Stop Loss Hit?
                ├─ YES → Closed at loss (SL)
                │
                └─ NO → Continue managing runner
                        ↓
                        EMA Exit Signal (21-EMA cross)?
                        ├─ YES → Close runner
                        │
                        └─ NO → Update trailing stop and repeat
```

---

## Critical Implementation Details

### 1. ATR-Based Take Profit (Volatility Adaptive)

**Formula**:
```
TP = Entry ± (Current_ATR × Multiplier)
Example: Entry=1.0850, ATR=30 pips, Multiplier=2.0
→ TP = 1.0850 + 0.0030 = 1.0880
```

**Multipliers**:
- `ATR_TP_MULTIPLIER=2.0` (for first 50%)
- `ATR_RUNNER_MULTIPLIER=3.5` (for runner max)

### 2. Trailing Stop (Protect Profits)

**Formula**:
```
Trailing_Stop = Highest_Price - (ATR × 1.0)

Example progression:
Price  1.0850 → Stop 1.0800 (fixed at entry)
Price  1.0870 → Stop 1.0840 (trail up)
Price  1.0890 → Stop 1.0860 (trail up)
Price  1.0875 → Stop 1.0860 (stays, doesn't go down)
Price  1.0859 → HIT STOP (profit locked)
```

### 3. Position Split

**Implementation**:
```python
position_first_half = position_size / 2
position_runner_half = position_size / 2

# Create two sub-positions within same trade
# Track which is which in trade object
trade.first_half_size = position_first_half
trade.runner_half_size = position_runner_half
trade.has_closed_first_half = False
```

### 4. EMA Exit (For Runner)

**Exit When**:
- **Long trade**: Price closes BELOW 21-EMA
- **Short trade**: Price closes ABOVE 21-EMA

**Why**: EMA is "trend support"; crossing below/above signals trend reversal

### 5. Time-Based Exit

**Maximum Hold Times**:
- Intraday: 4 hours max (close by end of NY session)
- Swing: 3 days max (don't hold over weekend)
- Runner: Unlimited IF using trailing stop

---

## Configuration (.env)

```bash
# Required for exit strategy
ATR_TP_MULTIPLIER=2.0
ATR_RUNNER_MULTIPLIER=3.5
ATR_TRAIL_MULTIPLIER=1.0
MAX_HOLD_HOURS=4
EMA_EXIT_PERIOD=21
EMA_EXIT_ENABLED=true
PREVENT_MANUAL_CLOSE_WINNERS=true
```

---

## Safety Rules (CRITICAL)

### ✅ Allowed Actions
- Close at take-profit (automatic limit order)
- Close at stop-loss (automatic stop order)
- Close at EMA signal (automatic, runner only)
- Close after max time (automatic timer)
- Close at support/resistance level (if confluence)
- Close at breakeven after first TP hit

### ❌ NOT Allowed
- ~~Manual early close of profitable trades~~
- ~~Closing at random prices because "it looks good"~~
- ~~Leaving trades open indefinitely~~
- ~~Closing winners on minor pullbacks~~

### Implementation
```python
# API endpoint blocks this
def close_trade(trade_id, manual=True):
    if manual and trade.pnl > 0 and TRADING_MODE == 'AUTO':
        return ERROR("Cannot manually close winners in AUTO mode")
```

---

## Performance Expectations

### Win Rate on First TP
**Target**: 80%+
- If <80%: Entry signals need work (not exit problem)
- If >80%: Exit strategy is working correctly

### Runner Performance
**Target**: Average 1.5-2.5x risk (from first TP)
- 30% runners close at first TP (quick exit)
- 40% runners trail 50+ pips beyond first TP
- 30% runners hit time limit or stop

### Overall P&L Per Trade
**Target**: 1.5x risk average (combining both halves)
- 50% win rate: 1.5x on first half, 1.5x on runner = +1.5x per trade
- 30% lose full: -1.0x per trade
- Net: (50% × 1.5) - (30% × 1.0) = +0.45x per trade

---

## Daily Checklist

### Morning (Before Trading)
- [ ] ATR calculations updating (check logs)
- [ ] TP levels look reasonable (not too tight/loose)
- [ ] Trailing stops configured correctly
- [ ] EMA exits enabled
- [ ] Manual close is disabled in AUTO mode

### During Trading (Every 4 hours)
- [ ] Check trades hitting first TP (50% closing automatically?)
- [ ] Check runners are trailing correctly (stop moving up for longs?)
- [ ] No trades held >4 hours (time limit working?)
- [ ] No manual closes of winners

### End of Day Review
- [ ] Did first TP hits match expected levels? (±5% okay)
- [ ] Did runners capture additional profit? (>20% beyond first TP?)
- [ ] Any early closes that shouldn't have happened?
- [ ] Any trades that would have been better with more time?

---

## Troubleshooting

### Problem: First TP never hit
- **Likely cause**: TP too far away (ATR_TP_MULTIPLIER too high)
- **Fix**: Reduce ATR_TP_MULTIPLIER from 2.0 to 1.5
- **Verify**: Check TP levels in logs, compare to recent price swings

### Problem: Trailing stop hit too fast
- **Likely cause**: Trailing distance too tight (ATR_TRAIL_MULTIPLIER too low)
- **Fix**: Increase ATR_TRAIL_MULTIPLIER from 1.0 to 1.5
- **Verify**: Check stop movements in logs, allow for pullbacks

### Problem: Manual closes still happening
- **Likely cause**: PREVENT_MANUAL_CLOSE_WINNERS not set or not working
- **Fix**: Check if running in MANUAL mode (allows closes), not AUTO
- **Verify**: Set TRADING_MODE=AUTO and check API blocks closes

### Problem: EMA exits triggering too fast
- **Likely cause**: EMA_EXIT_PERIOD too short (9 instead of 21)
- **Fix**: Use EMA_EXIT_PERIOD=21 for stable exits
- **Verify**: Test different periods in MONITOR mode first

### Problem: Runners don't run far enough
- **Likely cause**: ATR_RUNNER_MULTIPLIER too low or max time hitting first
- **Fix**: Increase ATR_RUNNER_MULTIPLIER to 3.5+, or MAX_HOLD_HOURS to 6
- **Verify**: Check logs for "time limit" exits vs "runner closed" exits

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Add ATR calculation to opportunities
- [ ] Implement position splitting (50%/50%)
- [ ] Add first TP (limit order)
- [ ] Add trailing stop to runner

### Phase 2: Smart Exits (Week 2)
- [ ] Add EMA exit logic (21-EMA)
- [ ] Add time-based maximum hold
- [ ] Add move-to-breakeven logic
- [ ] Test in MONITOR mode (24 hours)

### Phase 3: Safety & Refinement (Week 3)
- [ ] Disable manual closes in AUTO mode
- [ ] Add ATR multiplier tuning
- [ ] Add support/resistance detection
- [ ] Add daily performance review

### Phase 4: Optimization (Week 4)
- [ ] Analyze actual vs theoretical exits
- [ ] Tune multipliers based on data
- [ ] Add Fibonacci targets for swings
- [ ] Archive historical performance

---

## Key Metrics to Monitor

| Metric | Target | Action if Miss |
|--------|--------|---|
| Win Rate on First TP | 80%+ | Check entry signals |
| Runner Avg Distance | 1.5-2.5x first TP | Adjust ATR_RUNNER_MULTIPLIER |
| First TP Hit Rate | 60%+ of trades | Widen ATR_TP_MULTIPLIER |
| Early Manual Closes | <5% per week | Verify API blocking |
| Time Limit Exits | <20% of closes | Increase MAX_HOLD_HOURS |
| EMA Exit Accuracy | 70%+ correct direction | Verify EMA calculation |

---

## Common Mistakes to Avoid

1. **❌ Same TP for all pairs**
   - JPY pairs need wider TPs (higher volatility)
   - GBP/JPY might need 3.0x, EUR/USD 2.0x
   - **✅ Use ATR to adapt automatically**

2. **❌ Closing runners on first pullback**
   - Pullbacks are normal in trends
   - Trailing stop should NOT trigger on small moves
   - **✅ Set ATR_TRAIL_MULTIPLIER ≥1.0**

3. **❌ No time limit**
   - Trades can sit open indefinitely
   - Dead money, prevents new opportunities
   - **✅ Set MAX_HOLD_HOURS=4**

4. **❌ Fixed stop distances**
   - 50 pips is too tight in volatile markets
   - 50 pips is too loose in calm markets
   - **✅ Use ATR-based stops**

5. **❌ Manual intervention**
   - "Just close this one early, it looks weak"
   - Destroys discipline, creates losses
   - **✅ Automate everything possible**

---

## Questions to Ask Yourself

### On Every Trade Entry
- [ ] What is the ATR for this pair today?
- [ ] What is the realistic first TP level?
- [ ] How far can this runner realistically go?
- [ ] What is the maximum time I'll hold?

### Before Closing Manually
- [ ] Is this part of the plan, or am I guessing?
- [ ] What would the trader's rules say?
- [ ] Am I closing winners too early again?
- [ ] Should I let the trailing stop handle it?

### In Daily Review
- [ ] Which exits were perfect? Can I replicate?
- [ ] Which exits were too early? Why?
- [ ] Which exits were too late? Why?
- [ ] What's one thing I could improve?

---

## Resources

- **Full Strategy Guide**: `FOREX_PROFIT_TAKING_STRATEGIES.md`
- **Implementation Code**: `EXIT_STRATEGY_IMPLEMENTATION_GUIDE.md`
- **Related CLAUDE.md**: Session references and context
- **Research Sources**: See full guide for academic references

---

**Version**: 1.0
**Date**: March 6, 2026
**For**: Trade-Alerts System
**Status**: Ready to implement

