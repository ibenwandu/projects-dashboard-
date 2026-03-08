# RL System Integration Guide for Scalp-Engine

This guide explains how the enhanced RL system integrates with Scalp-Engine to provide continuous learning from both executed trades and simulated opportunities.

## Overview

The RL system tracks:
1. **Executed Trades**: Real trades opened through OANDA
2. **Simulated Opportunities**: Opportunities that weren't executed (for learning what we missed)

## Integration Points

### 1. Trade Opening (Log Signal)

When a trade is opened, log it to the RL database:

**Location**: `auto_trader_core.py` - `PositionManager.open_trade()`

```python
# After trade is successfully opened (around line 924)
if not duplicate_found:
    trade.state = TradeState.PENDING
    trade.opened_at = datetime.utcnow()
    self.active_trades[order_or_trade_id] = trade
    
    # RL LOGGING: Log executed trade
    try:
        from src.scalping_rl_enhanced import ScalpingRLEnhanced
        import os
        from pathlib import Path
        
        # Initialize RL database
        if os.path.exists('/var/data'):
            db_path = '/var/data/scalping_rl.db'
        else:
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'scalping_rl.db')
        
        rl_db = ScalpingRLEnhanced(db_path=db_path)
        signal_id = rl_db.log_signal(
            pair=trade.pair,
            direction=trade.direction,
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            llm_sources=trade.llm_sources or [],
            consensus_level=trade.consensus_level,
            rationale=trade.rationale,
            confidence=trade.confidence,
            executed=True,  # This is an executed trade
            trade_id=order_or_trade_id,
            position_size=trade.units
        )
        # Store signal_id in trade for later outcome update
        trade.rl_signal_id = signal_id
        self.logger.info(f"📊 RL: Logged executed trade signal {signal_id} for {trade.pair} {trade.direction}")
    except Exception as e:
        self.logger.warning(f"⚠️ Could not log trade to RL database: {e}")
    
    self._save_state()
```

### 2. Trade Closing (Update Outcome)

When a trade is closed, update the RL database with the outcome:

**Location**: `auto_trader_core.py` - `PositionManager._monitor_positions()`

```python
# When trade is closed (around where trade.state is set to CLOSED_*)
if trade.state in [TradeState.CLOSED_SL, TradeState.CLOSED_TP, TradeState.CLOSED_MANUAL]:
    # Calculate P&L in pips
    pip_value = 0.01 if 'JPY' in trade.pair else 0.0001
    if trade.direction == 'LONG':
        pnl_pips = (trade.exit_price - trade.entry_price) / pip_value
    else:
        pnl_pips = (trade.entry_price - trade.exit_price) / pip_value
    
    # RL UPDATE: Update outcome for executed trade
    if hasattr(trade, 'rl_signal_id') and trade.rl_signal_id:
        try:
            from src.scalping_rl_enhanced import ScalpingRLEnhanced
            import os
            from pathlib import Path
            
            if os.path.exists('/var/data'):
                db_path = '/var/data/scalping_rl.db'
            else:
                data_dir = Path(__file__).parent.parent / 'data'
                db_path = str(data_dir / 'scalping_rl.db')
            
            rl_db = ScalpingRLEnhanced(db_path=db_path)
            rl_db.update_outcome_real_trade(
                signal_id=trade.rl_signal_id,
                exit_price=trade.exit_price,
                pnl_pips=pnl_pips,
                bars_held=None,  # Can calculate from opened_at to closed_at
                max_favorable_pips=None,  # Can track during monitoring
                max_adverse_pips=None
            )
            self.logger.info(f"📊 RL: Updated outcome for signal {trade.rl_signal_id}: {pnl_pips:.2f} pips")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not update RL outcome: {e}")
```

### 3. Opportunity Simulation (Log Non-Executed Opportunities)

When opportunities are identified but not executed, log them for simulation:

**Location**: `scalp_engine.py` - `ScalpEngine._check_new_opportunities()`

```python
# After checking if opportunity should be executed
for opp in opportunities:
    # ... existing opportunity processing ...
    
    # If opportunity is NOT executed (skipped due to risk limits, trading hours, etc.)
    if not executed:
        # RL LOGGING: Log non-executed opportunity for simulation
        try:
            from src.scalping_rl_enhanced import ScalpingRLEnhanced
            import os
            from pathlib import Path
            
            if os.path.exists('/var/data'):
                db_path = '/var/data/scalping_rl.db'
            else:
                data_dir = Path(__file__).parent.parent / 'data'
                data_dir.mkdir(exist_ok=True)
                db_path = str(data_dir / 'scalping_rl.db')
            
            rl_db = ScalpingRLEnhanced(db_path=db_path)
            signal_id = rl_db.log_signal(
                pair=opp['pair'],
                direction=opp['direction'],
                entry_price=opp.get('entry', 0.0),
                stop_loss=opp.get('stop_loss', 0.0),
                take_profit=opp.get('exit'),
                llm_sources=opp.get('llm_sources', []),
                consensus_level=opp.get('consensus_level', 1),
                rationale=opp.get('recommendation', ''),
                confidence=opp.get('confidence', 0.5),
                executed=False,  # This is a simulated opportunity
                trade_id=None,
                position_size=0.0
            )
            self.logger.debug(f"📊 RL: Logged simulated opportunity {signal_id} for {opp['pair']} {opp['direction']}")
        except Exception as e:
            self.logger.debug(f"Could not log opportunity to RL database: {e}")
```

### 4. Daily Learning Cycle

Schedule the daily learning cycle to run automatically:

**Location**: `scalp_engine.py` - `ScalpEngine.run()`

```python
# In the main loop, check if it's time for daily learning (11pm UTC)
from datetime import datetime, time
import pytz

last_learning_date = None

while True:
    current_time = datetime.utcnow()
    current_time_utc = current_time.time()
    
    # Daily learning at 11:00 PM UTC
    if current_time_utc >= time(23, 0) and current_time.date() != last_learning_date:
        try:
            from src.daily_learning import run_daily_learning
            self.logger.info("🧠 Starting daily RL learning cycle...")
            run_daily_learning()
            last_learning_date = current_time.date()
            self.logger.info("✅ Daily RL learning cycle complete")
        except Exception as e:
            self.logger.error(f"❌ Error running daily learning cycle: {e}", exc_info=True)
    
    # ... rest of main loop ...
```

## Database Schema

The enhanced database includes:

### `signals` table:
- Basic trade info (pair, direction, entry, SL, TP)
- LLM context (llm_sources, consensus_level, rationale, confidence)
- Execution info (executed, trade_id, position_size)
- Outcome tracking (outcome, exit_price, pnl_pips, bars_held, etc.)

### `llm_performance` table:
- Performance metrics per LLM
- Updated daily after learning cycle

### `learning_checkpoints` table:
- Historical snapshots of weights and performance
- Used for tracking improvement over time

## Usage

### Get LLM Weights

```python
from src.scalping_rl_enhanced import ScalpingRLEnhanced, LLMLearningEngine

db = ScalpingRLEnhanced('/var/data/scalping_rl.db')
learning_engine = LLMLearningEngine(db)
weights = learning_engine.calculate_llm_weights()

# Use weights to prioritize LLM recommendations
# Higher weight = better historical performance
```

### Get Historical Performance

```python
# Get performance for specific LLM
perf = db.get_historical_performance(llm_source='gemini')
print(f"Gemini win rate: {perf['win_rate']:.1%}")
print(f"Gemini avg P&L: {perf['avg_pnl']:.2f} pips")

# Get performance for specific pair
perf = db.get_historical_performance(pair='EUR/USD')
```

### Generate Performance Report

```python
report = learning_engine.generate_performance_report()
print(f"Overall win rate: {report['overall_win_rate']:.1%}")
print(f"LLM weights: {report['recommended_weights']}")
print(f"Consensus analysis: {report['consensus_analysis']}")
```

## Benefits

1. **Continuous Learning**: System learns from every trade and opportunity
2. **LLM Weight Optimization**: Automatically identifies best-performing LLMs
3. **Simulation Learning**: Learns from opportunities that weren't executed
4. **Consensus Analysis**: Understands when LLM agreement leads to better outcomes
5. **Performance Tracking**: Comprehensive metrics for all LLMs and pairs

## Next Steps

1. Integrate RL logging into trade opening/closing
2. Add opportunity simulation logging
3. Schedule daily learning cycle
4. Use LLM weights to prioritize recommendations
5. Monitor performance reports to track improvement
