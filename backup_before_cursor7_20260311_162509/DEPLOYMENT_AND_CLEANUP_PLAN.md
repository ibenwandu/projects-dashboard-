# Deployment and Cleanup Plan

## Overview
This plan covers:
1. Committing changes and deploying to Render
2. Clearing stale data from opportunities and deleting pending trades
3. Running immediate analysis to generate fresh recommendations

---

## Phase 1: Commit Changes and Deploy to Render ✅ COMPLETE

### Step 1.1: Verify All Changes Are Committed ✅
```bash
# Check git status
cd c:\Users\user\projects\personal\Trade-Alerts\Scalp-Engine
git status

# Verify changes are staged
git diff --cached
```

### Step 1.2: Commit Any Remaining Changes ✅
```bash
# If there are uncommitted changes
git add .
git commit -m "Fix: Reject stale opportunities and cancel stale pending orders

- Added validation to reject opportunities with stale current_price
- Added logic to cancel pending orders too far from current market price
- Prevents trades from being opened based on outdated market data"
```

### Step 1.3: Push to GitHub (Auto-Deploys on Render) ✅
```bash
git push origin main
```

### Step 1.4: Verify Deployment on Render
1. Go to Render Dashboard → Trade-Alerts service
2. Check "Events" tab for deployment status
3. Wait for deployment to complete (usually 2-5 minutes)
4. Check logs to confirm deployment succeeded

---

## Phase 2: Clear Stale Data and Delete Pending Trades

### Quick Start: Use Provided Scripts

**Scripts have been created in:**
- `Scalp-Engine/scripts/phase2_cleanup.py` - For Scalp-Engine service
- `scripts/phase2_clear_market_state.py` - For Trade-Alerts service

### Step 2.1: Cancel All Pending Orders via Scalp-Engine

**Option A: Using Provided Script (Recommended)**
1. Go to Render Dashboard → Scalp-Engine service
2. Click "Shell" tab
3. Copy and paste the script content from `Scalp-Engine/scripts/phase2_cleanup.py`
4. Or upload the file and run: `python scripts/phase2_cleanup.py`

**Option B: Direct OANDA API Call**
```python
# In Render Shell for Scalp-Engine
from oandapyV20.endpoints import orders
from oandapyV20 import API
import os

account_id = os.getenv('OANDA_ACCOUNT_ID')
api_key = os.getenv('OANDA_API_KEY')
client = API(access_token=api_key, environment='practice')

# Get all pending orders
r = orders.OrdersPending(accountID=account_id)
client.request(r)
pending_orders = r.response.get('orders', [])

# Cancel each pending order
for order in pending_orders:
    order_id = order.get('id')
    cancel_r = orders.OrderCancel(accountID=account_id, orderID=order_id)
    try:
        client.request(cancel_r)
        print(f"✅ Cancelled order {order_id}")
    except Exception as e:
        print(f"❌ Failed to cancel order {order_id}: {e}")

print(f"✅ Cancelled {len(pending_orders)} pending order(s)")
```

### Step 2.2: Clear Stale Market State File

**Option A: Using Provided Script (Recommended)**
1. Go to Render Dashboard → Trade-Alerts service
2. Click "Shell" tab
3. Copy and paste the script content from `scripts/phase2_clear_market_state.py`
4. Or upload the file and run: `python scripts/phase2_clear_market_state.py`

**Option B: Manual Commands**
```bash
# In Render Shell for Trade-Alerts
# Backup existing market state (optional)
cp /var/data/market_state.json /var/data/market_state.json.backup

# Remove stale market state file
rm /var/data/market_state.json

# Verify it's deleted
ls -la /var/data/market_state.json
```

**Option C: Clear via Python**
```python
# In Render Shell for Trade-Alerts
import os
from pathlib import Path

market_state_file = Path('/var/data/market_state.json')
if market_state_file.exists():
    market_state_file.unlink()
    print("✅ Deleted stale market_state.json")
else:
    print("ℹ️ market_state.json does not exist")
```

### Step 2.3: Clear Scalp-Engine Active Trades State

**This is included in the phase2_cleanup.py script, but you can also do it manually:**

```python
# In Render Shell for Scalp-Engine
import os
from pathlib import Path

state_file = Path('/var/data/active_trades.json')
if state_file.exists():
    state_file.unlink()
    print("✅ Cleared active_trades.json")
else:
    print("ℹ️ active_trades.json does not exist")
```

---

## Phase 3: Run Immediate Analysis to Generate Fresh Recommendations

### Step 3.1: Trigger Manual Analysis in Trade-Alerts

**Option A: Using Render Shell (Recommended)**
```python
# In Render Shell for Trade-Alerts
import sys
sys.path.insert(0, '/opt/render/project/src')

from main import TradeAlertSystem

# Initialize system
system = TradeAlertSystem()

# Run full analysis immediately
print("🔄 Starting immediate analysis...")
system._run_full_analysis_with_rl()
print("✅ Analysis completed - fresh market state generated")
```

**Option B: Using Render API (If Available)**
```bash
# If Trade-Alerts has an API endpoint for manual trigger
curl -X POST https://your-trade-alerts-service.onrender.com/trigger-analysis \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Option C: Restart Service to Trigger Analysis**
1. Go to Render Dashboard → Trade-Alerts service
2. Click "Manual Deploy" → "Clear build cache & deploy"
3. This will restart the service and trigger analysis if scheduled

### Step 3.2: Verify Fresh Market State Generated

**Check Market State File:**
```bash
# In Render Shell for Trade-Alerts
cat /var/data/market_state.json | head -20

# Check timestamp
grep -o '"timestamp": "[^"]*"' /var/data/market_state.json
```

**Check Trade-Alerts Logs:**
1. Go to Render Dashboard → Trade-Alerts service → "Logs" tab
2. Look for:
   - `=== Scheduled Analysis Time: ... ===`
   - `Step 9 (NEW): Exporting market state...`
   - `✅ Market State exported to /var/data/market_state.json`
   - `✅ Full analysis workflow completed`

### Step 3.3: Verify Scalp-Engine Picks Up Fresh State

**Check Scalp-Engine Logs:**
1. Go to Render Dashboard → Scalp-Engine service → "Logs" tab
2. Look for:
   - `✅ Market State Updated`
   - `Checking X opportunities`
   - No "stale" warnings

**Check UI:**
1. Open Scalp-Engine UI
2. Go to "Market Intelligence" tab
3. Verify:
   - Fresh timestamp (should be within last few minutes)
   - Current prices match live market prices
   - Opportunities have realistic entry prices

---

## Phase 4: Verification and Testing

### Step 4.1: Verify No Stale Pending Orders
```python
# In Render Shell for Scalp-Engine
from oandapyV20.endpoints import orders
from oandapyV20 import API
import os

account_id = os.getenv('OANDA_ACCOUNT_ID')
api_key = os.getenv('OANDA_API_KEY')
client = API(access_token=api_key, environment='practice')

r = orders.OrdersPending(accountID=account_id)
client.request(r)
pending_orders = r.response.get('orders', [])

print(f"Pending orders: {len(pending_orders)}")
for order in pending_orders:
    print(f"  - {order.get('instrument')} {order.get('type')} @ {order.get('price')}")
```

### Step 4.2: Verify Fresh Opportunities
```python
# In Render Shell for Trade-Alerts
import json
from pathlib import Path

market_state_file = Path('/var/data/market_state.json')
if market_state_file.exists():
    with open(market_state_file) as f:
        state = json.load(f)
    
    print(f"Timestamp: {state.get('timestamp')}")
    print(f"Opportunities: {len(state.get('opportunities', []))}")
    
    for opp in state.get('opportunities', []):
        pair = opp.get('pair')
        current_price = opp.get('current_price')
        entry = opp.get('entry')
        print(f"  - {pair}: current={current_price}, entry={entry}")
else:
    print("❌ market_state.json not found")
```

### Step 4.3: Test Opportunity Processing
1. Monitor Scalp-Engine logs for next opportunity check (every ~1 minute)
2. Verify:
   - No "REJECTING STALE OPPORTUNITY" warnings
   - No "Cancelling stale pending order" messages (unless actually stale)
   - Opportunities are being processed normally

---

## Quick Reference: All Commands in One Place

### Complete Cleanup Script (Run in Render Shell for Scalp-Engine)
**Use the provided script: `Scalp-Engine/scripts/phase2_cleanup.py`**

Or run this inline:
```python
import sys
sys.path.insert(0, '/opt/render/project/src')

from auto_trader_core import PositionManager, TradeExecutor, TradeConfig
from oandapyV20 import API
import os
from pathlib import Path

# Initialize
account_id = os.getenv('OANDA_ACCOUNT_ID')
api_key = os.getenv('OANDA_API_KEY')
client = API(access_token=api_key, environment='practice')

executor = TradeExecutor(account_id, client)
config = TradeConfig()
position_manager = PositionManager(executor, config)

# 1. Cancel all pending orders
print("Step 1: Cancelling all pending orders...")
cancelled = position_manager.cancel_all_pending_orders(
    reason="Manual cleanup before fresh analysis"
)
print(f"✅ Cancelled {cancelled} pending order(s)")

# 2. Clear state file
print("\nStep 2: Clearing active trades state...")
state_file = Path('/var/data/active_trades.json')
if state_file.exists():
    state_file.unlink()
    print("✅ Cleared active_trades.json")

print("\n✅ Cleanup complete!")
```

### Complete Analysis Trigger Script (Run in Render Shell for Trade-Alerts)
```python
import sys
sys.path.insert(0, '/opt/render/project/src')

from main import TradeAlertSystem

print("🔄 Starting immediate analysis...")
system = TradeAlertSystem()
system._run_full_analysis_with_rl()
print("✅ Analysis completed - fresh market state generated")
```

---

## Troubleshooting

### If Market State Not Generated
1. Check Trade-Alerts logs for errors
2. Verify Google Drive API credentials
3. Check OANDA API credentials
4. Verify all environment variables are set

### If Pending Orders Not Cancelled
1. Check OANDA API credentials
2. Verify account ID is correct
3. Check OANDA logs for API errors
4. Try cancelling manually via OANDA platform

### If Scalp-Engine Not Picking Up Fresh State
1. Verify market_state.json exists and has recent timestamp
2. Check MARKET_STATE_FILE_PATH environment variable
3. Restart Scalp-Engine service
4. Check file permissions on /var/data/

---

## Expected Timeline

- **Phase 1 (Deploy)**: 5-10 minutes ✅ COMPLETE
- **Phase 2 (Cleanup)**: 2-5 minutes
- **Phase 3 (Analysis)**: 3-5 minutes (depends on LLM API response times)
- **Phase 4 (Verification)**: 2-3 minutes

**Total**: ~15-25 minutes

---

## Success Criteria

✅ All changes committed and deployed to Render
✅ All pending orders cancelled from OANDA
✅ Stale market state file removed
✅ Fresh analysis completed with current prices
✅ New market_state.json generated with recent timestamp
✅ Scalp-Engine processing fresh opportunities without stale warnings
✅ UI showing fresh recommendations with accurate current prices
