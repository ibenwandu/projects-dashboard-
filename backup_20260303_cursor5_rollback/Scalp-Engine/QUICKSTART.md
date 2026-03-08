# Scalp-Engine Quick Start

## 5-Minute Setup

### 1. Install Dependencies
```bash
cd personal/Scalp-Engine
pip install -r requirements.txt
```

### 2. Configure OANDA
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OANDA credentials
# OANDA_ACCESS_TOKEN=your_token
# OANDA_ACCOUNT_ID=your_account_id
# OANDA_ENV=practice
```

### 3. Run Trade-Alerts First
```bash
cd ../Trade-Alerts
python main.py
# Wait for it to generate market_state.json
```

### 4. Start Scalp-Engine
```bash
cd ../Scalp-Engine
python scalp_engine.py
```

## What You'll See

```
================================================================================
🚀 Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

📊 Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY

🎯 Signal: BUY EUR/USD (Strength: 0.75)
📈 Executing BUY EUR/USD - Size: 1000 units
✅ Order placed: 12345
```

## Key Files

- `scalp_engine.py` - Main execution engine
- `config.yaml` - Trading configuration
- `.env` - OANDA credentials (create from .env.example)
- `src/` - Core modules (state_reader, oanda_client, signal_generator, risk_manager)

## Default Settings

- **Risk per trade**: 0.5% of account
- **Stop loss**: 5 pips
- **Take profit**: 8 pips
- **Max spread**: 1.5 pips
- **Daily max loss**: 2%
- **Max consecutive losses**: 3

Adjust these in `config.yaml` or `.env`.

