# Scalp-Engine Troubleshooting Guide

## Error: `ModuleNotFoundError: No module named 'oandapyV20'`

### Solution 1: Install Dependencies

Run the installation script:

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
.\install_dependencies.ps1
```

Or manually:

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
pip install -r requirements.txt
```

### Solution 2: Check Python Environment

If you're using a virtual environment (like `(agents)`), make sure you're in the correct environment:

```powershell
# Check which Python you're using
python -c "import sys; print(sys.executable)"

# If it's not the right one, activate the correct environment
# For conda:
conda activate agents  # or your environment name

# Then install again
pip install -r requirements.txt
```

### Solution 3: Verify Installation

Test that the package is installed:

```powershell
python -c "import oandapyV20; print('OK')"
```

If this works, the package is installed correctly.

### Solution 4: Reinstall the Package

If it still doesn't work:

```powershell
pip uninstall oandapyV20
pip install oandapyV20
```

---

## Error: Script "Hangs" or Shows No Output

**This is NORMAL!** Scalp-Engine is waiting for approved pairs.

**What you'll see:**
```
================================================================================
Scalp-Engine Started
================================================================================
Environment: practice
Trading Pairs: EUR/USD, USD/JPY, USD/CAD
Max Spread: 1.5 pips
================================================================================

Market State Updated:
   Regime: NORMAL
   Bias: NEUTRAL
   Approved Pairs: 

PAUSED: No approved pairs. Sleeping...
```

**This means it's working correctly** - it's just waiting for Trade-Alerts to provide trading pairs.

**To get real activity:**
1. Enable LLMs in Trade-Alerts
2. Run `run_immediate_analysis.py` in Trade-Alerts
3. Scalp-Engine will automatically pick up new pairs

---

## Error: OANDA Connection Failed

### Check Credentials

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
Get-Content .env | Select-String "OANDA"
```

Make sure:
- `OANDA_ACCESS_TOKEN` is set (not "your_oanda_token_here")
- `OANDA_ACCOUNT_ID` is set
- `OANDA_ENV` is "practice" or "live"

### Test Connection

Run the test script:

```powershell
python test_components.py
```

Look for "Step 5: Testing OANDA connection" - it should show:
```
[OK] OANDA connection successful
    - Account Balance: [your balance]
```

---

## Error: Market State File Not Found

### Check if File Exists

```powershell
Test-Path ..\Trade-Alerts\market_state.json
```

### Generate Market State

If it doesn't exist:

```powershell
cd ..\Trade-Alerts
python run_immediate_analysis.py
```

This will create `market_state.json`.

---

## Quick Diagnostic

Run the component test:

```powershell
cd C:\Users\user\projects\personal\Scalp-Engine
python test_components.py
```

This will test:
- ✅ All imports
- ✅ Environment variables
- ✅ Config file
- ✅ Market state file
- ✅ OANDA connection
- ✅ All components

If all tests pass, Scalp-Engine should work!

---

## Still Having Issues?

1. **Check Python version:** `python --version` (should be 3.8+)
2. **Check all dependencies:** `pip list`
3. **Check environment:** Make sure you're in the right virtual environment
4. **Check paths:** Make sure you're in the Scalp-Engine directory when running

