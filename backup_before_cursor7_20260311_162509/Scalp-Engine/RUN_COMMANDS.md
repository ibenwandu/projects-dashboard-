# Scalp-Engine Run Commands

## Current Directory
You're already in: `C:\Users\user\projects\personal\Scalp-Engine`

## Step-by-Step Commands

### Step 1: Verify You're in the Right Directory
```powershell
# You should already be here, but verify:
pwd
# Should show: C:\Users\user\projects\personal\Scalp-Engine
```

### Step 2: Check .env File
```powershell
# Check if .env exists and has OANDA credentials
Get-Content .env | Select-String "OANDA"
```

### Step 3: Check if Trade-Alerts State File Exists
```powershell
# Check if market_state.json exists in Trade-Alerts folder
Test-Path ..\Trade-Alerts\market_state.json
```

**If it returns `False`**, you need to run Trade-Alerts first:
```powershell
cd ..\Trade-Alerts
python main.py
# Wait for it to complete, then come back
cd ..\Scalp-Engine
```

### Step 4: Test OANDA Connection
```powershell
# From Scalp-Engine directory
python -c "from src.oanda_client import OandaClient; import os; from dotenv import load_dotenv; load_dotenv(); client = OandaClient(os.getenv('OANDA_ACCESS_TOKEN'), os.getenv('OANDA_ACCOUNT_ID'), os.getenv('OANDA_ENV', 'practice')); info = client.get_account_info(); print('Account Balance:', info.get('balance') if info else 'FAILED')"
```

### Step 5: Test State Reader
```powershell
# From Scalp-Engine directory
python -c "from src.state_reader import MarketStateReader; reader = MarketStateReader(); state = reader.load_state(); print('State:', 'FOUND' if state else 'NOT FOUND'); print('Regime:', state.get('regime') if state else 'N/A')"
```

### Step 6: Run Scalp-Engine
```powershell
# From Scalp-Engine directory (where you are now)
python scalp_engine.py
```

## Full Diagnostic Script

Run this to check everything at once:

```powershell
# Make sure you're in Scalp-Engine directory
cd C:\Users\user\projects\personal\Scalp-Engine

# Run diagnostic
python -c "
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()

print('=== Scalp-Engine Diagnostic ===')
print()

# Check .env
token = os.getenv('OANDA_ACCESS_TOKEN')
account = os.getenv('OANDA_ACCOUNT_ID')
env = os.getenv('OANDA_ENV', 'practice')
print('1. OANDA Config:')
print(f'   Token: {\"SET\" if token and token != \"your_oanda_token_here\" else \"NOT SET\"}')
print(f'   Account: {account if account else \"NOT SET\"}')
print(f'   Environment: {env}')
print()

# Check state file
state_file = Path('../Trade-Alerts/market_state.json')
print('2. Market State File:')
print(f'   Path: {state_file.absolute()}')
print(f'   Exists: {state_file.exists()}')
if state_file.exists():
    import json
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        print(f'   Regime: {state.get(\"regime\", \"N/A\")}')
        print(f'   Bias: {state.get(\"global_bias\", \"N/A\")}')
        print(f'   Pairs: {state.get(\"approved_pairs\", [])}')
    except Exception as e:
        print(f'   Error reading: {e}')
print()

# Check imports
print('3. Module Imports:')
modules = ['oanda_client', 'state_reader', 'signal_generator', 'risk_manager']
for mod in modules:
    try:
        __import__(f'src.{mod}')
        print(f'   {mod}: OK')
    except Exception as e:
        print(f'   {mod}: FAILED - {str(e)[:50]}')
"
```

## If It Hangs

The program might hang if:
1. **OANDA API is slow** - Wait 10-30 seconds
2. **State file doesn't exist** - Run Trade-Alerts first
3. **OANDA credentials are wrong** - Check `.env` file

**To stop a hanging program:**
Press `Ctrl + C`

## Quick Test (10 second timeout)

```powershell
# This will run for 10 seconds then stop
cd C:\Users\user\projects\personal\Scalp-Engine
$job = Start-Job -ScriptBlock { python scalp_engine.py }
Start-Sleep -Seconds 10
Stop-Job $job
Receive-Job $job
```

