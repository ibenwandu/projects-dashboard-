# Scalp-Engine Architecture

## System Overview

The Scalp-Engine implements the "General & Sniper" architecture:

### The General (Trade-Alerts)
- **Frequency**: Every 1-4 hours
- **Role**: Macro analysis, news, regime detection
- **Output**: `market_state.json` with bias, regime, approved pairs
- **Technology**: LLMs (ChatGPT, Gemini, Claude)

### The Sniper (Scalp-Engine)
- **Frequency**: Real-time (sub-second)
- **Role**: Price action execution, EMA Ribbon signals
- **Input**: Reads `market_state.json`
- **Technology**: OANDA API, pandas, technical indicators

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Trade-Alerts                         │
│  (LLM Analysis → market_state.json)                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ market_state.json
                       │ (every 1-4 hours)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Scalp-Engine                           │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ State Reader │→ │Signal Gen    │→ │Risk Manager  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                 │                  │          │
│         └─────────────────┴──────────────────┘         │
│                          │                              │
│                          ▼                              │
│              ┌───────────────────┐                      │
│              │  OANDA Client     │                      │
│              └───────────────────┘                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Live Prices & Orders
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    OANDA API                             │
│  (Price Streaming, Order Execution)                     │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Market State Generation (Trade-Alerts)
```
LLM Analysis → Opportunities → Market Bridge → market_state.json
```

**market_state.json structure:**
```json
{
  "timestamp": "2026-01-09T10:00:00Z",
  "global_bias": "BULLISH",
  "regime": "TRENDING",
  "approved_pairs": ["EUR/USD", "USD/JPY"],
  "long_count": 2,
  "short_count": 0,
  "total_opportunities": 2
}
```

### 2. Signal Generation (Scalp-Engine)
```
Market State → Approved Pairs → OANDA Candles → EMA Calculation → Signal
```

**Signal Logic:**
1. Fetch 1-minute candles (last 100)
2. Calculate EMA 9, 21, 50
3. Check ribbon stack (trending?)
4. Check pullback zone (entry trigger?)
5. Filter by regime and bias
6. Return signal + strength

### 3. Risk Management
```
Signal → Risk Check → Position Sizing → Order Execution
```

**Risk Checks:**
- Daily loss limit (2%)
- Consecutive losses (3 max)
- Spread validation (< 1.5 pips)
- Account balance minimum

### 4. Order Execution
```
Signal → OANDA API → Market Order → Stop Loss + Take Profit
```

## Key Components

### `state_reader.py`
- Reads `market_state.json` from Trade-Alerts
- Validates state freshness (< 4 hours)
- Provides regime, bias, approved pairs

### `oanda_client.py`
- OANDA API wrapper
- Live price fetching
- Historical candles for indicators
- Order execution (market orders with SL/TP)

### `signal_generator.py`
- EMA Ribbon calculation
- Signal generation logic
- Pullback zone detection
- Signal strength scoring

### `risk_manager.py`
- Position sizing (fixed risk %)
- Daily loss tracking
- Consecutive loss tracking
- Trading permission checks

### `scalp_engine.py`
- Main orchestration
- State refresh loop
- Signal generation loop
- Order execution coordination

## Strategy Implementation

### EMA Ribbon Logic

**Bullish Setup:**
```python
if ema9 > ema21 > ema50:  # Stacked upward
    if ema21 <= price <= ema9:  # Pullback zone
        return "BUY"
```

**Bearish Setup:**
```python
if ema9 < ema21 < ema50:  # Stacked downward
    if ema9 <= price <= ema21:  # Pullback zone
        return "SELL"
```

### Regime-Based Filtering

- **TRENDING**: Use EMA pullback strategy
- **RANGING**: Skip signals (less reliable)
- **HIGH_VOL**: Use EMA with higher confidence threshold

### Bias Alignment

- Only trade signals that align with global bias
- BULLISH bias → Only BUY signals
- BEARISH bias → Only SELL signals
- NEUTRAL → All signals allowed

## Integration Points

### With Trade-Alerts
- **File**: `market_state.json`
- **Location**: `personal/Trade-Alerts/market_state.json`
- **Update Frequency**: After each Trade-Alerts analysis
- **Format**: JSON with timestamp, bias, regime, pairs

### With Fx-engine RL (Future)
- **Database**: `fx_engine.db`
- **Tables**: `signals`, `outcomes`
- **Tracking**: Setup types, regime, performance
- **Learning**: Optimal thresholds per regime

## Performance Characteristics

### Latency
- State refresh: 60 seconds
- Price polling: 0.5 seconds
- Signal calculation: < 100ms
- Order execution: < 1 second (OANDA)

### Throughput
- Max signals per minute: ~10 (throttled)
- Max orders per minute: 10 (configurable)
- Cooldown between trades: 5 seconds

## Safety Mechanisms

1. **State Validation**: Checks timestamp, required fields
2. **Spread Filtering**: Skips trades if spread too wide
3. **Daily Loss Limit**: Stops trading at 2% loss
4. **Consecutive Loss Limit**: Pauses after 3 losses
5. **Position Sizing**: Fixed risk per trade (0.5%)
6. **Practice Mode**: Default environment for testing

## Future Enhancements

1. **RL Integration**: Connect to Fx-engine RL tracker
2. **VWAP Integration**: Add VWAP-based signals
3. **Session Filtering**: Only trade during optimal hours
4. **Multi-Timeframe**: Use 15m/5m for bias, 1m for entry
5. **Order Management**: Track open positions, trailing stops

