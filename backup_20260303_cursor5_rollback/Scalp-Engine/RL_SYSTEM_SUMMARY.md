# Scalp-Engine RL System - Implementation Summary

## Overview

The enhanced RL system for Scalp-Engine replicates the reinforcement learning functionality from Trade-Alerts, enabling continuous learning from both executed trades and simulated opportunities.

## What Was Created

### 1. Enhanced RL Database (`src/scalping_rl_enhanced.py`)

**ScalpingRLEnhanced Class**:
- Enhanced database schema with LLM source tracking
- Tracks both executed trades and simulated opportunities
- Stores consensus level, rationale, confidence
- Records execution status (executed vs simulated)

**Key Methods**:
- `log_signal()`: Log trading signals (executed or opportunity)
- `update_outcome_real_trade()`: Update outcome from executed trade
- `update_outcome_simulated()`: Update outcome from simulation
- `get_pending_signals()`: Get signals ready for evaluation
- `get_llm_performance()`: Get performance metrics per LLM
- `get_historical_performance()`: Get historical stats

### 2. Outcome Evaluator (`src/scalping_rl_enhanced.py`)

**OutcomeEvaluator Class**:
- Evaluates signal outcomes using market data (yfinance)
- Simulates trade outcomes without actual execution
- Calculates P&L, bars held, max favorable/adverse pips
- Handles WIN, LOSS, and MISSED outcomes

**Key Methods**:
- `evaluate_signal()`: Evaluate single signal using market data
- `_check_outcome()`: Check if TP/SL was hit

### 3. LLM Learning Engine (`src/scalping_rl_enhanced.py`)

**LLMLearningEngine Class**:
- Calculates performance-based weights for each LLM
- Analyzes consensus performance (when LLMs agree)
- Generates comprehensive performance reports

**Key Methods**:
- `calculate_llm_weights()`: Calculate weights based on win rate, profit factor, missed rate
- `analyze_consensus()`: Analyze performance by consensus level
- `generate_performance_report()`: Generate full performance report

### 4. Daily Learning Cycle (`src/daily_learning.py`)

**run_daily_learning() Function**:
- Runs daily at 11pm UTC (can be scheduled)
- Evaluates pending signals (4+ hours old)
- Updates LLM weights based on performance
- Saves learning checkpoints
- Generates performance reports

## How It Works

### 1. Signal Logging

**When trades are opened**:
```python
rl_db.log_signal(
    pair="EUR/USD",
    direction="LONG",
    entry_price=1.1000,
    stop_loss=1.0980,
    take_profit=1.1020,
    llm_sources=["gemini", "synthesis"],
    consensus_level=2,
    executed=True,  # Real trade
    trade_id="12345"
)
```

**When opportunities are identified but not executed**:
```python
rl_db.log_signal(
    pair="GBP/USD",
    direction="SHORT",
    entry_price=1.2500,
    stop_loss=1.2520,
    executed=False,  # Simulated opportunity
    trade_id=None
)
```

### 2. Outcome Tracking

**For executed trades** (when trade closes):
```python
rl_db.update_outcome_real_trade(
    signal_id=123,
    exit_price=1.1010,
    pnl_pips=10.0,
    bars_held=12
)
```

**For simulated opportunities** (daily learning cycle):
```python
# Evaluator simulates outcome using market data
result = evaluator.evaluate_signal(signal)
rl_db.update_outcome_simulated(
    signal_id=456,
    outcome=result['outcome'],
    exit_price=result['exit_price'],
    pnl_pips=result['pnl_pips']
)
```

### 3. Weight Calculation

**Daily at 11pm UTC**:
1. Get all pending signals (4+ hours old)
2. Evaluate outcomes (simulate if needed)
3. Calculate performance metrics per LLM:
   - Win rate (60% weight)
   - Profit factor (40% weight)
   - Missed rate (penalty)
4. Normalize weights across all LLMs
5. Save checkpoint

**Example weights**:
```
gemini: 30% (75% win rate, 2.0 profit factor)
synthesis: 28% (70% win rate, 1.8 profit factor)
chatgpt: 24% (60% win rate, 1.5 profit factor)
claude: 18% (55% win rate, 1.2 profit factor)
```

### 4. Using Weights

**Prioritize recommendations**:
```python
weights = learning_engine.calculate_llm_weights()

# When processing opportunities, prioritize by weight
for opp in opportunities:
    llm_source = opp['llm_sources'][0]
    weight = weights.get(llm_source, 0.25)
    # Higher weight = more confidence in recommendation
```

## Database Schema

### `signals` Table
- `id`: Primary key
- `timestamp`: When signal was logged
- `pair`, `direction`, `entry_price`, `stop_loss`, `take_profit`
- `llm_sources`: JSON array of LLM sources
- `consensus_level`: Number of LLMs that agreed
- `executed`: 1 if executed, 0 if simulated
- `trade_id`: OANDA trade ID if executed
- `outcome`: WIN, LOSS, MISSED, PENDING
- `pnl_pips`: P&L in pips
- `evaluated`: 1 if outcome evaluated, 0 if pending

### `llm_performance` Table
- Performance metrics per LLM
- Updated daily after learning cycle

### `learning_checkpoints` Table
- Historical snapshots of weights
- Used for tracking improvement over time

## Integration Points

### 1. Trade Opening
**File**: `auto_trader_core.py` - `PositionManager.open_trade()`
**Action**: Log signal when trade is opened

### 2. Trade Closing
**File**: `auto_trader_core.py` - `PositionManager._monitor_positions()`
**Action**: Update outcome when trade closes

### 3. Opportunity Simulation
**File**: `scalp_engine.py` - `ScalpEngine._check_new_opportunities()`
**Action**: Log non-executed opportunities for simulation

### 4. Daily Learning
**File**: `scalp_engine.py` - `ScalpEngine.run()`
**Action**: Schedule daily learning cycle at 11pm UTC

## Benefits

1. **Continuous Learning**: Learns from every trade and opportunity
2. **LLM Optimization**: Automatically identifies best-performing LLMs
3. **Simulation Learning**: Learns from opportunities that weren't executed
4. **Consensus Analysis**: Understands when LLM agreement leads to better outcomes
5. **Performance Tracking**: Comprehensive metrics for all LLMs and pairs

## Next Steps

1. **Integrate RL Logging**: Add logging to trade opening/closing (see `RL_INTEGRATION_GUIDE.md`)
2. **Add Opportunity Simulation**: Log non-executed opportunities
3. **Schedule Daily Learning**: Add daily learning cycle to main loop
4. **Use Weights**: Prioritize recommendations based on LLM weights
5. **Monitor Performance**: Review performance reports regularly

## Files Created

1. `src/scalping_rl_enhanced.py` - Enhanced RL database and learning engine
2. `src/daily_learning.py` - Daily learning cycle
3. `RL_INTEGRATION_GUIDE.md` - Integration instructions
4. `RL_SYSTEM_SUMMARY.md` - This summary document

## Testing

To test the RL system:

```python
from src.scalping_rl_enhanced import ScalpingRLEnhanced, OutcomeEvaluator, LLMLearningEngine

# Initialize
db = ScalpingRLEnhanced('/var/data/scalping_rl.db')

# Log a signal
signal_id = db.log_signal(
    pair="EUR/USD",
    direction="LONG",
    entry_price=1.1000,
    stop_loss=1.0980,
    take_profit=1.1020,
    llm_sources=["gemini"],
    executed=True
)

# Update outcome
db.update_outcome_real_trade(
    signal_id=signal_id,
    exit_price=1.1010,
    pnl_pips=10.0
)

# Calculate weights
learning_engine = LLMLearningEngine(db)
weights = learning_engine.calculate_llm_weights()
print(weights)

# Generate report
report = learning_engine.generate_performance_report()
print(report)
```

## Notes

- Database path: Uses `/var/data/scalping_rl.db` on Render, `data/scalping_rl.db` locally
- Daily learning: Runs at 11pm UTC (can be adjusted)
- Minimum samples: Need 5+ evaluated signals per LLM to calculate weights
- Evaluation age: Signals must be 4+ hours old before evaluation
- Market simulation: Uses yfinance with 5-minute intervals for scalping
