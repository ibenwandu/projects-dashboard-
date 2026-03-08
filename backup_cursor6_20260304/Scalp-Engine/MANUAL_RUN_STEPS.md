# Manual Run Steps for Scalp-Engine

## Prerequisites Check

### Step 1: Verify OANDA Credentials
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
Get-Content .env | Select-String "OANDA"
```

You should see:
- `OANDA_ACCESS_TOKEN=your_token`
- `OANDA_ACCOUNT_ID=your_account_id`
- `OANDA_ENV=practice` (or `live`)

### Step 2: Verify Trade-Alerts State File
```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
Test-Path market_state.json
```

If it returns `False`, you need to run Trade-Alerts first to generate the state file.

## Running the Scalp-Engine

### Option 1: Run Directly
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python scalp_engine.py
```

### Option 2: Run with Error Output
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python scalp_engine.py 2>&1 | Tee-Object -FilePath output.log
```

This will:
- Show output in console
- Save output to `output.log` file

### Option 3: Run in Background (if needed)
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
Start-Process python -ArgumentList "scalp_engine.py" -NoNewWindow
```

## What to Expect

### Normal Startup
```
================================================================================
Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

Waiting for Trade-Alerts to generate market state...
```

### After State File is Available
```
Market State Updated:
   Regime: TRENDING
   Bias: BULLISH
   Approved Pairs: EUR/USD, USD/JPY

SIGNAL: BUY EUR/USD (Strength: 0.75)
EXECUTING: BUY EUR/USD - Size: 1000 units
SUCCESS: Order placed: 12345
```

## Troubleshooting

### If it hangs on "Waiting for Trade-Alerts..."
1. Check if Trade-Alerts is running
2. Verify `market_state.json` exists in Trade-Alerts folder
3. Check file timestamp (should be < 4 hours old)

### If you get OANDA API errors
1. Verify credentials in `.env`
2. Check OANDA account is active
3. Verify environment matches (practice vs live)

### To Stop the Engine
Press `Ctrl + C` in the terminal

## Quick Test Commands

### Test OANDA Connection
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python -c "from src.oanda_client import OandaClient; import os; from dotenv import load_dotenv; load_dotenv(); client = OandaClient(os.getenv('OANDA_ACCESS_TOKEN'), os.getenv('OANDA_ACCOUNT_ID'), os.getenv('OANDA_ENV', 'practice')); info = client.get_account_info(); print('Account Balance:', info.get('balance') if info else 'Failed')"
```

### Test State Reader
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python -c "from src.state_reader import MarketStateReader; reader = MarketStateReader(); state = reader.load_state(); print('State:', 'Found' if state else 'Not Found'); print('Regime:', state.get('regime') if state else 'N/A')"
```

### Test Signal Generator
```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python -c "from src.signal_generator import SignalGenerator; import pandas as pd; gen = SignalGenerator(); test_data = pd.Series([1.0, 1.01, 1.02, 1.03, 1.04] * 20); emas = gen.calculate_emas(test_data); print('EMAs:', emas)"
```

