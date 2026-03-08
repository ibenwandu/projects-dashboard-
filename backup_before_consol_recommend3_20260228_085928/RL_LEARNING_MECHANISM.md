# RL System Learning Mechanism - How It Works Going Forward

## Overview

The Trade-Alerts RL system uses **market simulation** to evaluate recommendations and automatically adjust LLM weights based on performance. It learns continuously without requiring actual trade execution.

---

## 🔄 The Learning Cycle

### Daily Learning Schedule

**When**: Every day at **11:00 PM UTC** (automatically triggered)

**What Happens**:
1. ✅ Evaluates recommendations from the last 24 hours (that are 4+ hours old)
2. ✅ Calculates new performance metrics for each LLM
3. ✅ Updates LLM weights based on performance
4. ✅ Saves learning checkpoint
5. ✅ Generates performance report

---

## 📊 Step-by-Step Learning Process

### Step 1: Recommendation Logging (Real-Time)

**When**: During each analysis run (Step 7)

**What Happens**:
- All LLM recommendations are logged to the database:
  - ChatGPT recommendations
  - Gemini recommendations
  - Claude recommendations
  - Synthesis (Gemini Final) recommendations

**Data Stored**:
```python
{
    'timestamp': '2026-01-13T21:01:22',
    'llm_source': 'chatgpt',  # or 'gemini', 'claude', 'synthesis'
    'pair': 'GBPUSD',
    'direction': 'LONG',
    'entry_price': 1.2650,
    'stop_loss': 1.2600,
    'take_profit_1': 1.2700,
    'timeframe': 'INTRADAY',
    'outcome': 'PENDING',  # Initially
    'evaluated': 0  # Not yet evaluated
}
```

---

### Step 2: Outcome Evaluation (Daily at 11pm UTC)

**When**: Daily at 11:00 PM UTC

**Process**:
1. **Fetch Pending Recommendations**:
   - Gets all recommendations that are:
     - Status: `PENDING`
     - Age: 4+ hours old (gives market time to move)
     - Not yet evaluated

2. **Market Simulation**:
   For each recommendation, the system:
   - Fetches historical price data from `yfinance` (5-minute intervals)
   - Simulates what would have happened if the trade was executed
   - Checks if price hit:
     - ✅ **Take Profit 1** → `WIN_TP1`
     - ✅ **Take Profit 2** → `WIN_TP2`
     - ❌ **Stop Loss** → `LOSS_SL`
     - ⚠️ **Never triggered** (price never got close to entry) → `MISSED`
     - ⚪ **Still open** (hit entry but no TP/SL yet) → `NEUTRAL`

3. **Calculate Metrics**:
   - PnL in pips
   - Bars held (time to outcome)
   - Max favorable pips (best price reached)
   - Max adverse pips (worst price reached)

**Example Evaluation**:
```
Recommendation: GBP/USD LONG @ 1.2650, SL: 1.2600, TP: 1.2700

Price Movement:
- Entry: 1.2650
- Lowest: 1.2605 (didn't hit SL)
- Highest: 1.2705 (hit TP1!)
- Outcome: WIN_TP1
- PnL: +50 pips
- Bars held: 12 (1 hour)
```

---

### Step 3: Performance Calculation (Daily at 11pm UTC)

**For Each LLM** (ChatGPT, Gemini, Claude, Synthesis):

1. **Win Rate**:
   ```
   Win Rate = (Wins) / (Wins + Losses)
   ```
   - Excludes `MISSED` and `PENDING` from denominator
   - Only counts `WIN_TP1`, `WIN_TP2`, `LOSS_SL`

2. **Profit Factor**:
   ```
   Profit Factor = Total Profit / Total Loss
   ```
   - Total Profit = Sum of all winning trades (pips)
   - Total Loss = Sum of all losing trades (pips)
   - Higher is better (1.0 = break even, 2.0 = 2x profit vs loss)

3. **Missed Rate**:
   ```
   Missed Rate = (MISSED trades) / (Total recommendations)
   ```
   - Penalizes LLMs that recommend trades that never trigger
   - High missed rate = LLM is picking unrealistic entry prices

4. **Combined Score**:
   ```
   accuracy_score = (win_rate * 0.6) + (min(profit_factor / 2, 0.5) * 0.4)
   missed_penalty = 1.0 - (missed_rate * 0.5)
   final_score = accuracy_score * missed_penalty
   ```
   - 60% weight on win rate
   - 40% weight on profit factor
   - Penalty for missed trades (up to 50% reduction)

---

### Step 4: Weight Calculation (Daily at 11pm UTC)

**Formula**:
```python
# For each LLM:
if evaluated_recommendations < 5:
    weight = 0.25  # Equal weight (not enough data)
else:
    # Calculate score (see Step 3)
    score = calculate_performance_score(llm)
    
    # Normalize across all LLMs
    total_score = sum(all_llm_scores)
    weight = score / total_score
```

**Minimum Requirements**:
- Need **5+ evaluated recommendations** per LLM to calculate weights
- If less than 5, LLM gets equal weight (25%)

**Example Weight Calculation**:
```
ChatGPT: 15 evaluated, 60% win rate, 1.5 profit factor → Score: 0.65
Gemini:  12 evaluated, 75% win rate, 2.0 profit factor → Score: 0.80
Claude:  10 evaluated, 50% win rate, 1.2 profit factor → Score: 0.52
Synthesis: 8 evaluated, 70% win rate, 1.8 profit factor → Score: 0.73

Total Score: 0.65 + 0.80 + 0.52 + 0.73 = 2.70

Weights:
- ChatGPT: 0.65 / 2.70 = 24.1%
- Gemini: 0.80 / 2.70 = 29.6%
- Claude: 0.52 / 2.70 = 19.3%
- Synthesis: 0.73 / 2.70 = 27.0%
```

---

### Step 5: Weight Application (Next Day)

**When**: During next analysis run

**How**:
- System loads latest weights from database
- Uses weights to:
  1. **Prioritize recommendations** in synthesis
  2. **Enhance final recommendations** with RL insights
  3. **Display confidence** based on historical performance

**Example**:
```
If Gemini has 30% weight (best performer):
- Gemini's recommendations get more emphasis in synthesis
- System shows: "Gemini has 75% win rate historically"
- User sees: "Based on historical performance, prioritize Gemini recommendations"
```

---

## 📈 Learning Timeline

### Week 1: Initial Learning
- **Day 1-2**: System logs recommendations (all equal weight: 25%)
- **Day 3**: First evaluation cycle (if 4+ hours old recommendations exist)
- **Day 4-7**: More evaluations, weights start to differentiate

### Week 2-4: Active Learning
- **Daily**: New recommendations logged
- **Daily at 11pm**: Evaluations and weight updates
- **Result**: Weights reflect actual performance

### Month 2+: Continuous Improvement
- **Ongoing**: System learns from every recommendation
- **Adaptive**: Weights adjust as market conditions change
- **Self-Correcting**: Poor performers get lower weights automatically

---

## 🎯 Key Learning Features

### 1. Market Simulation (No Real Trades Needed)
- Uses `yfinance` to fetch historical price data
- Simulates trade outcomes based on entry/SL/TP
- Works for all timeframes (Intraday, Swing)

### 2. Automatic Evaluation
- No manual intervention required
- Runs daily at 11pm UTC automatically
- Evaluates all recommendations 4+ hours old

### 3. Performance-Based Weighting
- Better performing LLMs get higher weights
- Poor performers get penalized
- Missed trades reduce weight (unrealistic entries)

### 4. Consensus Analysis
- Tracks when all LLMs agree vs disagree
- Learns that consensus trades perform better
- Uses this in future recommendations

### 5. Historical Context
- Tracks performance by:
  - Currency pair
  - Timeframe (Intraday vs Swing)
  - Market session
  - Day of week

---

## 📊 Performance Metrics Tracked

### Per LLM:
- **Total Recommendations**: All recommendations logged
- **Evaluated**: Recommendations with outcomes
- **Win Rate**: % of trades that hit TP1 or TP2
- **Average PnL**: Average pips per trade
- **Profit Factor**: Total profit / Total loss
- **Missed Rate**: % of trades that never triggered
- **Average Bars Held**: Time to outcome

### Overall:
- **Overall Win Rate**: Across all LLMs
- **Total Evaluated**: All evaluated recommendations
- **Best Performing LLM**: Highest weight LLM
- **Consensus Performance**: When all LLMs agree

---

## 🔍 Example Learning Scenario

### Day 1 (Monday):
```
Analysis runs → Logs 8 recommendations:
- ChatGPT: 2 recommendations
- Gemini: 2 recommendations
- Claude: 2 recommendations
- Synthesis: 2 recommendations

Weights: All 25% (equal, not enough data yet)
```

### Day 2 (Tuesday):
```
11pm UTC: Daily learning runs
- Evaluates Day 1 recommendations (now 4+ hours old)
- Results:
  * ChatGPT: 1 WIN, 1 LOSS → 50% win rate
  * Gemini: 2 WINS → 100% win rate
  * Claude: 1 WIN, 1 MISSED → 50% win rate (penalized for missed)
  * Synthesis: 2 WINS → 100% win rate

New Weights:
- ChatGPT: 22%
- Gemini: 28% (best performer)
- Claude: 20% (penalized for missed trade)
- Synthesis: 30% (best performer)
```

### Day 3 (Wednesday):
```
Analysis runs → Uses new weights from Day 2
- Gemini and Synthesis get more emphasis
- System shows: "Gemini has 100% win rate (2/2 trades)"
- Recommendations prioritize Gemini/Synthesis insights

11pm UTC: Evaluates Day 2 recommendations
- Updates weights again based on new outcomes
- Weights continue to refine
```

### Week 2:
```
After 2 weeks of learning:
- Gemini: 30% weight (75% win rate, 2.0 profit factor)
- Synthesis: 28% weight (70% win rate, 1.8 profit factor)
- ChatGPT: 23% weight (60% win rate, 1.5 profit factor)
- Claude: 19% weight (55% win rate, 1.2 profit factor, 15% missed rate)

System now prioritizes Gemini and Synthesis recommendations
```

---

## 🚀 Continuous Improvement

### How It Gets Better Over Time:

1. **More Data = Better Weights**:
   - After 5+ evaluations per LLM: Weights become meaningful
   - After 20+ evaluations: Weights are statistically significant
   - After 100+ evaluations: Weights are highly reliable

2. **Adaptive to Market Conditions**:
   - If market conditions change, weights adjust
   - LLMs that adapt better get higher weights
   - System self-corrects over time

3. **Consensus Learning**:
   - Learns that when all LLMs agree, win rate is higher
   - Uses this to enhance recommendations
   - Shows consensus confidence in final output

4. **Pair-Specific Learning** (Future Enhancement):
   - Can track performance by currency pair
   - "Gemini is best for EUR/USD, ChatGPT is best for GBP/JPY"
   - Applies pair-specific weights

---

## 📝 Learning Checkpoints

**Saved Daily** at 11pm UTC:
- LLM weights
- Performance statistics
- Total recommendations count
- Overall win rate
- Timestamp

**Used For**:
- Historical tracking
- Performance analysis
- Debugging
- Reporting

---

## ⚙️ Configuration

### Minimum Requirements for Learning:
- **5+ evaluated recommendations** per LLM to calculate weights
- **4+ hours old** recommendations to evaluate (gives market time to move)
- **24+ hours old** for MISSED evaluation (if trade never triggered)

### Evaluation Timing:
- **Daily at 11:00 PM UTC**: Automatic evaluation
- **Can run manually**: `python train_rl_system.py --evaluate`
- **Immediate evaluation**: For imported historical data

---

## 🎓 Summary

**The system learns by**:
1. ✅ Logging all LLM recommendations in real-time
2. ✅ Evaluating outcomes daily using market simulation
3. ✅ Calculating performance metrics (win rate, profit factor, missed rate)
4. ✅ Updating LLM weights based on performance
5. ✅ Applying weights to future recommendations

**It improves by**:
- 📈 More data = more accurate weights
- 🔄 Daily updates = adaptive to market changes
- 🎯 Performance-based = best LLMs get prioritized
- ⚠️ Penalties = poor performers get reduced weight

**Result**:
- System automatically identifies best-performing LLMs
- Recommendations improve over time
- No manual intervention required
- Continuous learning from every recommendation

---

## 🔗 Related Files

- `src/daily_learning.py`: Daily learning cycle
- `src/trade_alerts_rl.py`: RL database and evaluation logic
- `train_rl_system.py`: Training script (can run manually)
- `RL_PERFORMANCE_ANALYSIS.md`: Current performance analysis
