# Fix: run_immediate_analysis.py Not Found on Render

## Problem

When trying to run `python run_immediate_analysis.py` on Render, you get:
```
python: can't open file '/opt/render/project/run_immediate_analysis.py': [Errno 2] No such file or directory
```

## Root Cause

The file exists in the repository but might not be in the Render deployment directory, or you're in the wrong directory.

## Solutions

### Solution 1: Check Current Directory and Navigate Correctly

**In Render Dashboard → `trade-alerts` → Shell:**

```bash
# Check your current directory
pwd

# You're probably in ~/project/src or similar
# Go to the project root
cd /opt/render/project

# Or use relative path
cd ~/project

# Check if file exists
ls -la run_immediate_analysis.py

# If file doesn't exist, check what files are in the root
ls -la
```

**Expected Output (if file exists):**
```
-rw-rw-r-- 1 render render 4523 Jan 10 17:30 run_immediate_analysis.py
```

### Solution 2: Check if File Was Deployed

**If the file doesn't exist on Render:**

1. **Verify the file is committed to Git:**
   ```bash
   # On your local machine
   cd C:\Users\user\projects\personal\Trade-Alerts
   git status run_immediate_analysis.py
   ```

2. **If file is not committed, commit and push:**
   ```bash
   git add run_immediate_analysis.py
   git commit -m "Add run_immediate_analysis.py for manual testing"
   git push
   ```

3. **Wait for Render to redeploy:**
   - Render will automatically detect the change
   - Service will redeploy with the new file
   - Wait for deployment to complete

4. **Then try again:**
   ```bash
   cd /opt/render/project
   python run_immediate_analysis.py
   ```

### Solution 3: Run Analysis Using Python Module Import (Alternative)

**If the file doesn't exist but `main.py` does, you can trigger analysis directly:**

**In Render Dashboard → `trade-alerts` → Shell:**

```bash
cd /opt/render/project
python -c "
from main import TradeAlertSystem
import sys

# Create system instance
system = TradeAlertSystem()

# Run analysis workflow
try:
    system.run_analysis_workflow()
    print('✅ Analysis workflow completed')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
```

**This will:**
- Import `TradeAlertSystem` from `main.py`
- Call `run_analysis_workflow()` which includes the market state export
- Generate `market_state.json` if analysis completes successfully

### Solution 4: Trigger Analysis Through main.py (Simplest)

**In Render Dashboard → `trade-alerts` → Shell:**

```bash
# Make sure you're in the project root
cd /opt/render/project

# Check if main.py exists
ls -la main.py

# Run main.py directly (it will start the scheduler, but you can also trigger manually)
# Actually, main.py starts a scheduler, so let's use the import method instead (Solution 3)
```

**Better approach - Use Python to call the analysis method:**

```bash
cd /opt/render/project
python << 'PYTHON_SCRIPT'
import sys
import os
from datetime import datetime
import pytz

# Add project root to path
sys.path.insert(0, '/opt/render/project')

try:
    from src.market_bridge import MarketBridge
    
    # Create a minimal market state for testing
    print("Creating minimal market state...")
    bridge = MarketBridge()
    
    # Create empty state (for testing)
    state = bridge.export_market_state([], "Manual test - no analysis data available")
    
    print("✅ Market state exported to:", bridge.filepath)
    print(f"   Timestamp: {state.get('timestamp', 'N/A')}")
    print(f"   Bias: {state.get('global_bias', 'N/A')}")
    print(f"   Regime: {state.get('regime', 'N/A')}")
    print(f"   Approved Pairs: {state.get('approved_pairs', [])}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT
```

**This will create a minimal market state file immediately without running full analysis.**

---

## Recommended Solution

**For quick testing, use Solution 4 (Create minimal market state):**

```bash
cd /opt/render/project
python << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/opt/render/project')
from src.market_bridge import MarketBridge
bridge = MarketBridge()
state = bridge.export_market_state([], "Manual test - waiting for scheduled analysis")
print("✅ Market state exported to:", bridge.filepath)
PYTHON_SCRIPT
```

**For full analysis, use Solution 3 (Import and call TradeAlertSystem):**

```bash
cd /opt/render/project
python -c "from main import TradeAlertSystem; system = TradeAlertSystem(); system.run_analysis_workflow()"
```

---

## Verification

**After running any solution, verify the file was created:**

```bash
ls -la /var/data/market_state.json
cat /var/data/market_state.json
```

**Expected Output:**
```json
{
    "timestamp": "2025-01-10T17:30:00.000000Z",
    "global_bias": "NEUTRAL",
    "regime": "NORMAL",
    "approved_pairs": [],
    "opportunities": [],
    "long_count": 0,
    "short_count": 0,
    "total_opportunities": 0
}
```

---

**Last Updated**: 2025-01-10
**Status**: ✅ File exists in repository, needs to be deployed to Render or use alternative method