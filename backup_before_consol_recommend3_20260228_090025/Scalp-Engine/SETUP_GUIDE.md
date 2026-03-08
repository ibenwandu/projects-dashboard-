# Scalp-Engine Setup Guide

## Overview

The Scalp-Engine is an automated scalping system that:
- Reads market intelligence from Trade-Alerts (`market_state.json`)
- Executes trades based on EMA Ribbon strategy
- Uses OANDA API for live prices and order execution
- Integrates with RL system for learning

## Architecture

```
Trade-Alerts (Slow Layer)
    ↓ (generates market_state.json)
Scalp-Engine (Fast Layer)
    ↓ (reads state, generates signals)
OANDA API (Execution)
    ↓ (places orders)
RL System (Learning)
```

## Prerequisites

1. **OANDA Account**: Practice or Live account with API access
2. **Trade-Alerts**: Must be running and generating `market_state.json`
3. **Python 3.8+**: Required for all dependencies

## Installation

### 1. Install Dependencies

```bash
cd personal/Scalp-Engine
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your OANDA credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
OANDA_ACCESS_TOKEN=your_token_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENV=practice  # or "live"
```

### 3. Configure Trading Parameters

Edit `config.yaml` to adjust:
- Trading pairs
- Risk parameters
- EMA periods
- Trading sessions

## Running the System

### Step 1: Start Trade-Alerts

Ensure Trade-Alerts is running and generating `market_state.json`:

```bash
cd personal/Trade-Alerts
python main.py
```

Wait for it to complete at least one analysis cycle.

### Step 2: Start Scalp-Engine

In a separate terminal:

```bash
cd personal/Scalp-Engine
python scalp_engine.py
```

## How It Works

### 1. Market State Reading
- Scalp-Engine reads `market_state.json` from Trade-Alerts every 60 seconds
- Extracts: regime, bias, approved pairs
- Validates state is not stale (< 4 hours old)

### 2. Signal Generation
- Fetches 1-minute candles from OANDA
- Calculates EMA 9, 21, 50
- Checks for EMA Ribbon stack (trending)
- Looks for pullback into 9-21 EMA zone
- Filters by regime and bias

### 3. Risk Management
- Checks daily loss limit (2% default)
- Checks consecutive losses (3 max default)
- Calculates position size based on risk per trade (0.5% default)
- Validates spread is acceptable (< 1.5 pips default)

### 4. Order Execution
- Places market order via OANDA API
- Sets stop loss (5 pips default)
- Sets take profit (8 pips default)
- Records outcome for RL learning

## Strategy Logic

### EMA Ribbon Setup

**Bullish Setup:**
- EMA 9 > 21 > 50 (stacked upward)
- Price pulls back into 9-21 EMA zone
- Signal: BUY

**Bearish Setup:**
- EMA 9 < 21 < 50 (stacked downward)
- Price rallies into 9-21 EMA zone
- Signal: SELL

**No Trade:**
- EMAs are crisscrossed (ranging)
- Price not in pullback zone
- Spread too wide

### Regime-Based Filtering

- **TRENDING**: Uses EMA pullback strategy
- **RANGING**: Skips EMA signals (less reliable)
- **HIGH_VOL**: Uses EMA pullback with higher confidence threshold

## Monitoring

### Console Output

The engine prints:
- Market state updates
- Signal generation
- Order execution
- Risk limit warnings

### Logs

Logs are saved to `logs/scalp_engine.log` (if configured).

## Troubleshooting

### "Waiting for Trade-Alerts to generate market state"
- Ensure Trade-Alerts is running
- Check that `market_state.json` exists in Trade-Alerts root
- Verify Trade-Alerts completed at least one analysis

### "Spread too wide"
- Market may be illiquid
- Wait for better conditions
- Adjust `max_spread_pips` in config.yaml

### "Cannot trade: Daily loss limit reached"
- Daily loss limit (2% default) has been hit
- Engine will resume trading tomorrow
- Adjust `daily_max_loss_pct` if needed

### "Cannot trade: Max consecutive losses reached"
- 3 consecutive losses (default) have occurred
- Engine pauses trading
- Reset by restarting the engine

## Integration with Trade-Alerts

Trade-Alerts automatically exports `market_state.json` after each analysis. The file contains:

```json
{
  "timestamp": "2026-01-09T10:00:00Z",
  "global_bias": "BULLISH",
  "regime": "TRENDING",
  "approved_pairs": ["EUR/USD", "USD/JPY"],
  "opportunities": [...]
}
```

Scalp-Engine reads this file and uses it to:
- Filter which pairs to trade
- Determine market regime
- Align signals with global bias

## Next Steps

1. **Test in Practice Mode**: Run with `OANDA_ENV=practice` first
2. **Monitor Performance**: Watch signals and execution
3. **Tune Parameters**: Adjust risk, spreads, confidence thresholds
4. **Enable RL Integration**: Connect to Fx-engine RL system for learning

## Safety Features

- ✅ Practice mode by default
- ✅ Daily loss limits
- ✅ Consecutive loss limits
- ✅ Spread filtering
- ✅ State validation (stale check)
- ✅ Position sizing based on risk

## Support

For issues or questions:
1. Check logs in `logs/scalp_engine.log`
2. Verify OANDA API credentials
3. Ensure Trade-Alerts is generating state file
4. Review config.yaml settings

