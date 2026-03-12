# Solution for Different Blueprints - API-Based Sync

## ✅ Problem Confirmed

**Trade-Alerts and Scalp-Engine are in DIFFERENT Blueprints**, which means:
- ❌ They **CANNOT share the same disk** (even with same disk name)
- ❌ File-based sync won't work
- ✅ **Solution: API/Webhook sync** works perfectly!

## 🚀 Solution: API-Based Market State Sync

### Architecture

```
Trade-Alerts (Blueprint 1)
    ↓
MarketBridge.export_market_state()
    ↓
HTTP POST to Scalp-Engine API
    ↓
scalp-engine-api (in Scalp-Engine Blueprint)
    ↓
Saves to /var/data/market_state.json (shared disk)
    ↓
    ├─→ scalp-engine (worker) reads from disk
    └─→ scalp-engine-ui (web) reads from disk
```

**Key Benefits**:
- ✅ Works across different Blueprints
- ✅ No restructuring needed
- ✅ Simple HTTP POST request
- ✅ File still saved to disk (for Scalp-Engine services to read)

---

## 📦 What Was Created

### 1. Market State API Server (`market_state_server.py`)
- Flask API endpoint: `POST /market-state`
- Receives market state from Trade-Alerts
- Saves to shared disk (`/var/data/market_state.json`)
- Scalp-Engine worker and UI read from same disk

### 2. Updated MarketBridge (`Trade-Alerts/src/market_bridge.py`)
- Saves file locally (for backup)
- **NEW**: Also sends HTTP POST to Scalp-Engine API
- Fallback: If API fails, file-based sync still works

### 3. Market State API Module (`src/market_state_api.py`)
- Handles saving and loading market state
- Used by API server and Scalp-Engine

---

## 🔧 Setup Steps

### Step 1: Deploy Scalp-Engine API

The updated `render.yaml` includes a new service: `scalp-engine-api`

1. **Push changes to GitHub**:
   ```powershell
   cd C:\Users\user\projects\personal\Scalp-Engine
   git add -A
   git commit -m "Add API endpoint for receiving market state from Trade-Alerts"
   git push
   ```

2. **Render will auto-deploy**:
   - New service: `scalp-engine-api` will be created
   - It will receive market state from Trade-Alerts

3. **Get API URL**:
   - Go to Render Dashboard → `scalp-engine-api` service
   - Copy the URL (e.g., `https://scalp-engine-api.onrender.com`)

4. **Set API Key** (optional but recommended):
   - Go to Render Dashboard → `scalp-engine-api` → Environment
   - Add: `MARKET_STATE_API_KEY` = `your-secret-api-key` (generate a random string)

### Step 2: Configure Trade-Alerts

1. **Push updated Trade-Alerts code**:
   ```powershell
   cd C:\Users\user\projects\personal\Trade-Alerts
   git add -A
   git commit -m "Add API sync to Scalp-Engine for cross-Blueprint communication"
   git push
   ```

2. **Set environment variables in Trade-Alerts**:
   - Go to Render Dashboard → `trade-alerts` service → Environment
   - Add: `SCALP_ENGINE_API_URL` = `https://scalp-engine-api.onrender.com/market-state`
   - Add: `SCALP_ENGINE_API_KEY` = `your-secret-api-key` (same as Step 1)

### Step 3: Verify Setup

1. **Check Scalp-Engine API is running**:
   - Go to Render Dashboard → `scalp-engine-api` → Logs
   - Should see: `Running on 0.0.0.0:10000`

2. **Test API endpoint**:
   - Go to: `https://scalp-engine-api.onrender.com/health`
   - Should return: `{"status": "healthy", "service": "market-state-api"}`

3. **Trigger Trade-Alerts analysis**:
   - Wait for scheduled run OR trigger manually
   - Check Trade-Alerts logs:
     ```
     ✅ Market State exported to /var/data/market_state.json
     ✅ Market State sent to Scalp-Engine API: https://scalp-engine-api.onrender.com/market-state
     ```

4. **Check Scalp-Engine API logs**:
   - Should see: `✅ Market state received: BULLISH TRENDING - 3 pairs`

5. **Verify file on Scalp-Engine disk**:
   - Go to Render Dashboard → `scalp-engine` → Shell
   - Run: `cat /var/data/market_state.json`
   - Should show market state JSON

6. **Check Scalp-Engine UI**:
   - Should show market state without errors
   - No yellow warning banner

---

## 🔐 Security (Optional but Recommended)

### API Key Authentication

1. **Generate a secret API key**:
   - Use a random string generator
   - Example: `sk_live_abc123xyz789_secret_key`

2. **Set in Scalp-Engine API**:
   - Render Dashboard → `scalp-engine-api` → Environment
   - `MARKET_STATE_API_KEY` = `sk_live_abc123xyz789_secret_key`

3. **Set in Trade-Alerts**:
   - Render Dashboard → `trade-alerts` → Environment
   - `SCALP_ENGINE_API_KEY` = `sk_live_abc123xyz789_secret_key` (same value)

4. **Without API key**: API will accept requests but log warnings

---

## 📊 How It Works

### Trade-Alerts Side

1. Analysis runs (7 times per day)
2. `MarketBridge.export_market_state()` is called
3. Market state is saved to local file (backup)
4. **NEW**: Market state is POSTed to Scalp-Engine API
5. Logs show success or failure

### Scalp-Engine API Side

1. Receives POST request from Trade-Alerts
2. Validates payload (checks required fields)
3. Saves to `/var/data/market_state.json` (shared disk)
4. Returns success response
5. Logs the received state

### Scalp-Engine Worker Side

1. Reads `/var/data/market_state.json` from disk
2. Uses market state to filter signals
3. Executes trades based on regime and approved pairs

### Scalp-Engine UI Side

1. Reads `/var/data/market_state.json` from disk
2. Displays market state in dashboard
3. Shows opportunities, regime, bias, etc.

---

## 🐛 Troubleshooting

### Issue: API returns 404

**Cause**: API URL is incorrect

**Solution**: 
- Verify API URL in Trade-Alerts environment: `SCALP_ENGINE_API_URL`
- Should be: `https://scalp-engine-api.onrender.com/market-state`
- Check API service is deployed and running

### Issue: API returns 401 Unauthorized

**Cause**: API key mismatch

**Solution**:
- Verify `MARKET_STATE_API_KEY` is set in both services
- Values must match exactly
- Check for extra spaces or quotes

### Issue: API returns 400 Bad Request

**Cause**: Invalid payload format

**Solution**:
- Check Trade-Alerts logs for payload structure
- Verify required fields: `timestamp`, `global_bias`, `regime`, `approved_pairs`
- Check JSON format is valid

### Issue: File not appearing in Scalp-Engine disk

**Cause**: API didn't save file or disk isn't shared

**Solution**:
- Check API logs for save errors
- Verify API service has disk mounted
- Check file permissions: `ls -la /var/data/market_state.json`

### Issue: Scalp-Engine UI still shows "Could not load market state"

**Cause**: File not found or path incorrect

**Solution**:
- Verify `MARKET_STATE_FILE_PATH=/var/data/market_state.json` in UI environment
- Check file exists: `cat /var/data/market_state.json` in UI Shell
- Verify file was created recently (after API received data)

---

## ✅ Expected Behavior After Setup

1. **Trade-Alerts logs** (after analysis):
   ```
   ✅ Market State exported to /var/data/market_state.json
   ✅ Market State sent to Scalp-Engine API: https://scalp-engine-api.onrender.com/market-state
   ```

2. **Scalp-Engine API logs**:
   ```
   ✅ Market state received: BULLISH TRENDING - 3 pairs
   ✅ Market state saved to /var/data/market_state.json
   ```

3. **Scalp-Engine logs**:
   ```
   ✅ Market state loaded: BULLISH, TRENDING, 3 pairs
   ```

4. **Scalp-Engine UI**:
   - Shows market state without errors
   - Displays bias, regime, approved pairs
   - No yellow warning banner

---

## 📝 Summary

**Problem**: Different Blueprints cannot share disks

**Solution**: API-based sync with HTTP POST

**Benefits**:
- ✅ Works across different Blueprints
- ✅ No restructuring needed
- ✅ Simple and reliable
- ✅ File still saved to disk (for Scalp-Engine services)

**Cost**: 
- Free tier for API service (sufficient for receiving POST requests)
- No additional cost beyond existing services

**Next Steps**:
1. Deploy updated Scalp-Engine (includes API service)
2. Configure Trade-Alerts with API URL
3. Test and verify
4. Enjoy seamless market state sync! 🎉
