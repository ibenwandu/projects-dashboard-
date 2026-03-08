# Scalp-Engine

Automated scalping program that combines intelligence from Trade-Alerts with high-speed execution via OANDA API.

## Architecture: "The General & The Sniper"

### The General (Trade-Alerts)
- **Role**: Analyzes macro data, news, and generates market regime
- **Frequency**: Every 1-4 hours
- **Output**: `market_state.json` with bias, regime, and approved pairs
- **Location**: `personal/Trade-Alerts/` (separate program)

### The Sniper (Scalp-Engine)
- **Role**: Executes trades based on price action and EMA Ribbon logic
- **Frequency**: Real-time (sub-second execution)
- **Input**: Reads `market_state.json` from Trade-Alerts
- **Execution**: OANDA API for live prices and order execution

## Features

- **EMA Ribbon Strategy**: 9/21/50 EMA with pullback entries
- **Regime-Based Logic**: Adapts to TRENDING/RANGING/HIGH_VOL regimes
- **Spread Filter**: Skips trades if spread > 1.5 pips
- **Risk Management**: 0.25-0.5% per trade, 2% daily max loss
- **RL Integration**: Tracks performance and learns optimal setups
- **OANDA Integration**: Live price streaming and order execution

## Setup

1. **Prerequisites**:
   ```bash
   pip install oandapyV20 pandas numpy python-dotenv
   ```

2. **Configuration**:
   - Copy `.env.example` to `.env`
   - Add your OANDA API token and account ID
   - Configure risk parameters

3. **Run**:
   ```bash
   python scalp_engine.py
   ```

## Entry points (canonical scripts)

Run from **Scalp-Engine** directory (or `cd Scalp-Engine` from Trade-Alerts root):

| Script | Purpose |
|--------|---------|
| `python scalp_engine.py` | Main engine (auto-trader loop). |
| `python run_fisher_scan.py` | Fisher Transform scan (reversal strategy); posts to market-state-api or writes to disk. |
| `python run_ft_dmi_ema_scan.py` | FT-DMI-EMA scan; posts to market-state-api or writes to disk. |

From **Trade-Alerts** repo root:

| Script | Purpose |
|--------|---------|
| `python run_fisher_scan_now.py` | Runs `Scalp-Engine/run_fisher_scan.py` in subprocess. |

Do **not** use `src/run_fisher_scan.py` (removed); use root `run_fisher_scan.py` only.

## File Structure

```
Scalp-Engine/
├── README.md
├── requirements.txt
├── .env.example
├── config.yaml
├── scalp_engine.py          # Main execution engine
├── src/
│   ├── __init__.py
│   ├── oanda_client.py      # OANDA API wrapper
│   ├── signal_generator.py  # EMA Ribbon logic
│   ├── risk_manager.py      # Position sizing & risk
│   ├── state_reader.py      # Reads market_state.json
│   └── rl_integration.py    # RL tracker integration
└── data/
    └── trades.db            # Trade history for RL
```

## Strategy Details

### EMA Ribbon Logic
- **Bullish Setup**: EMA 9 > 21 > 50 (stacked)
- **Entry**: Price pulls back into 9-21 EMA zone
- **Bearish Setup**: EMA 9 < 21 < 50 (inverse stack)
- **Entry**: Price rallies into 9-21 EMA zone

### Risk Parameters
- Risk per trade: 0.25-0.5% of account
- Stop loss: 5-8 pips
- Take profit: 1.5R to 2R
- Daily max loss: 2%
- Stop trading after 3 consecutive losses

### Best Trading Sessions (EST)
- **London Open**: 3:00-5:00 AM
- **London-NY Overlap**: 8:00-11:00 AM (Best liquidity)
- **NY Open**: 9:30-10:30 AM

## Integration

### With Trade-Alerts
- Reads `market_state.json` from Trade-Alerts root directory
- Updates every 60 seconds
- Uses regime and bias to filter signals

### With Fx-engine RL
- Logs trades to `fx_engine.db` (if available)
- Tracks setup types (VWAP_Bounce, EMA_Pullback, etc.)
- Learns optimal conditions for each regime

## Status

🚧 **Under Development** - Initial structure created

