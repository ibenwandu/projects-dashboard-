# API-Based Market State Communication - Deployment Guide

## ✅ Implementation Complete

We've successfully implemented **Option 1: API-Based Communication** to solve the disk sharing issue on Render.

## 📋 What Was Changed

### 1. ✅ Added API Service to render.yaml

**New Service:** `market-state-api`
- Type: `web` service
- Location: `Scalp-Engine/market_state_server.py`
- Build: `cd Scalp-Engine && pip install -r requirements.txt`
- Start: `cd Scalp-Engine && python market_state_server.py`
- Disk: `shared-market-data` at `/var/data` (same as other Scalp-Engine services)

### 2. ✅ Modified MarketBridge to Send HTTP POST

**File:** `src/market_bridge.py`

**Changes:**
- Added `requests` import (with graceful fallback if unavailable)
- Added API URL and API key configuration from environment variables
- Added `_send_to_api()` method to send HTTP POST after file export
- Calls `_send_to_api()` after successful file export

**Behavior:**
- Still exports to file first (backup/fallback)
- Then sends HTTP POST to API service
- If API is unavailable, logs warning but doesn't fail
- If API is configured but fails, logs warning but continues

### 3. ✅ Added Environment Variables

**Trade-Alerts Service:**
- `MARKET_STATE_API_URL`: API endpoint URL (set in Dashboard after deployment)
- `MARKET_STATE_API_KEY`: API authentication key (optional, set in Dashboard)

**Market State API Service:**
- `MARKET_STATE_FILE_PATH`: Path to save state (default: `/var/data/market_state.json`)
- `MARKET_STATE_API_KEY`: API authentication key (optional, set in Dashboard)

## 🚀 Deployment Steps

### Step 1: Commit and Push Changes

```bash
cd C:\Users\user\projects\personal\Trade-Alerts
git add render.yaml
git add src/market_bridge.py
git commit -m "Add API-based market state communication"
git push
```

### Step 2: Wait for Deployment

Render will automatically:
1. Deploy the updated Blueprint
2. Create the new `market-state-api` service
3. Redeploy all existing services with updated code

### Step 3: Get API Service URL (After Deployment)

1. Go to Render Dashboard → **market-state-api** service
2. Copy the service URL (e.g., `https://market-state-api-xxxx.onrender.com`)
3. The full API endpoint will be: `https://market-state-api-xxxx.onrender.com/market-state`

### Step 4: Configure Trade-Alerts API URL

1. Go to Render Dashboard → **trade-alerts** service → **Environment**
2. Find `MARKET_STATE_API_URL` (or add it if missing)
3. Set value to: `https://market-state-api-xxxx.onrender.com/market-state`
   - Replace `xxxx` with your actual service URL
4. Click **Save Changes**
5. Service will automatically redeploy

### Step 5: Configure API Key (Optional but Recommended)

1. **Generate a secure API key:**
   ```bash
   # On Windows (PowerShell)
   -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
   
   # Or use any random string generator
   ```

2. **Set in Trade-Alerts:**
   - Go to Render Dashboard → **trade-alerts** → **Environment**
   - Find or add `MARKET_STATE_API_KEY`
   - Set to your generated key
   - Click **Save Changes**

3. **Set in Market State API:**
   - Go to Render Dashboard → **market-state-api** → **Environment**
   - Find or add `MARKET_STATE_API_KEY`
   - Set to the **same key** as Trade-Alerts
   - Click **Save Changes**

### Step 6: Verify Deployment

1. **Check API Service:**
   - Go to API service URL: `https://market-state-api-xxxx.onrender.com/health`
   - Should see: `{"status": "healthy", "service": "market-state-api"}`

2. **Check Trade-Alerts Logs:**
   - Wait for next scheduled analysis (or trigger manually)
   - Look for:
     - `✅ Market State exported to /var/data/market_state.json`
     - `Sending market state to API: https://...`
     - `✅ Market state sent to API successfully`

3. **Check API Service Logs:**
   - Go to **market-state-api** → **Logs**
   - Look for:
     - `✅ Market state received: BULLISH TRENDING - X pairs`
     - `✅ Market state saved to /var/data/market_state.json`

4. **Check Scalp-Engine Services:**
   - Check **scalp-engine** logs for successful state loading
   - Check **scalp-engine-ui** for market state display

## 🔍 How It Works

### Flow Diagram

```
Trade-Alerts (Analysis Complete)
    ↓
1. Export to file (/var/data/market_state.json on Trade-Alerts disk)
    ↓
2. Send HTTP POST to market-state-api
    ↓
Market State API Service
    ↓
3. Receive POST, validate, save to /var/data/market_state.json (on API service disk)
    ↓
4. Scalp-Engine Worker & UI read from /var/data/market_state.json
   (on their own disk, OR on API service disk if in same Blueprint)
```

### Key Points

- **Trade-Alerts** writes to its own disk (backup)
- **Trade-Alerts** sends HTTP POST to API service (primary method)
- **API Service** receives and saves to its disk
- **Scalp-Engine services** read from their disk (or API service disk if shared)

## 🧪 Testing

### Test 1: Health Check

```bash
# In browser or curl
curl https://market-state-api-xxxx.onrender.com/health

# Expected: {"status": "healthy", "service": "market-state-api"}
```

### Test 2: Manual API Test (From Trade-Alerts Shell)

```bash
# In Trade-Alerts service shell
python << 'PYTHON_SCRIPT'
import requests
import json
from datetime import datetime

# Test payload
state = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "global_bias": "BULLISH",
    "regime": "TRENDING",
    "approved_pairs": ["EUR/USD", "GBP/USD"],
    "opportunities": [],
    "long_count": 2,
    "short_count": 0,
    "total_opportunities": 2
}

# Get API URL from environment
import os
api_url = os.getenv('MARKET_STATE_API_URL', 'https://market-state-api-xxxx.onrender.com/market-state')
api_key = os.getenv('MARKET_STATE_API_KEY', '')

headers = {'Content-Type': 'application/json'}
if api_key:
    headers['X-API-Key'] = api_key

response = requests.post(api_url, json=state, headers=headers, timeout=10)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
PYTHON_SCRIPT
```

### Test 3: Check API Received State

```bash
# Get current state
curl https://market-state-api-xxxx.onrender.com/market-state

# Should return JSON with market state data
```

## 📝 Important Notes

1. **API URL Must Be Set After Deployment:**
   - The default URL in render.yaml won't work
   - You MUST update `MARKET_STATE_API_URL` in Trade-Alerts environment after deployment
   - Use the actual service URL from Render Dashboard

2. **Disk Sharing:**
   - Trade-Alerts has its own disk (cannot share with Scalp-Engine)
   - API service, Worker, and UI share the same disk (if in same Blueprint)
   - If services share the same disk, they can all read the file
   - If not, the API approach works regardless

3. **API Key Authentication:**
   - Optional but recommended for security
   - If not set, API will work but without authentication
   - Both services must use the same key

4. **Graceful Degradation:**
   - If API is unavailable, Trade-Alerts still exports to file
   - Logs warnings but doesn't fail
   - System continues to work (just without cross-service sync)

## 🔧 Troubleshooting

### Issue: API Service Not Receiving Requests

**Check:**
1. Is API service running? (Check service status in Dashboard)
2. Is API URL correct? (Verify in Trade-Alerts environment)
3. Check API service logs for errors
4. Check Trade-Alerts logs for API errors

### Issue: API Service Returns 401 Unauthorized

**Solution:**
- Check that `MARKET_STATE_API_KEY` is set in both services
- Verify keys match exactly (case-sensitive)
- If keys don't match, API will return 401

### Issue: API Service Returns 400 Bad Request

**Check:**
- Verify payload has all required fields: `timestamp`, `global_bias`, `regime`, `approved_pairs`
- Check Trade-Alerts logs for export errors
- Verify state structure is correct

### Issue: Connection Timeout

**Check:**
- Is API service URL correct?
- Is API service running?
- Check API service health endpoint
- Verify network connectivity

## ✅ Success Criteria

After deployment, you should see:

1. ✅ API service is running and healthy
2. ✅ Trade-Alerts sends HTTP POST after analysis
3. ✅ API service receives and saves state
4. ✅ Scalp-Engine services can read state
5. ✅ UI displays market state correctly

## 🎯 Next Steps

1. **Deploy the changes** (commit and push)
2. **Wait for deployment** to complete
3. **Configure API URL** in Trade-Alerts environment
4. **Set API key** (optional but recommended)
5. **Test the flow** (trigger analysis or wait for scheduled run)
6. **Monitor logs** to verify communication works

---

**Status:** ✅ **Ready for Deployment**
