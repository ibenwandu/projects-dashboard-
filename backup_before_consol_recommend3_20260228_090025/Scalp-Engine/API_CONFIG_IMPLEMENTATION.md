# API-Based Config Implementation (Like Indicator-Alerts)

## Summary

Updated `scalp-engine` to load configuration from API (primary) with file fallback, matching the `indicator-alerts-worker` pattern. This solves the disk sharing issue by using HTTP API instead of shared disk.

## Changes Made

### 1. `scalp_engine.py` - API Config Loading

- ✅ Added `requests` import
- ✅ Added `config_api_url` from `CONFIG_API_URL` environment variable
- ✅ Added `_load_config_from_api()` method (matches `IndicatorConfig` pattern)
- ✅ Updated `_load_config()` to try API first, then fall back to file
- ✅ Updated `_reload_config_if_changed()` to reload from API if configured

### 2. `config_api_server.py` - New Config API Server

- ✅ Created Flask API server that serves `/api/config` endpoint
- ✅ Reads from `/var/data/auto_trader_config.json`
- ✅ Returns default config if file doesn't exist
- ✅ Can be run as separate service or integrated into `scalp-ui`

### 3. `render.yaml` - Environment Variable

- ✅ Added `CONFIG_API_URL` environment variable to `scalp-engine` service
- ⚠️ **Needs to be set manually** in Render Dashboard to: `https://scalp-engine-ui.onrender.com/api/config`

## How It Works

### Pattern (Same as Indicator-Alerts):

```
┌─────────────────┐
│   scalp-ui      │  Saves config to /var/data/auto_trader_config.json
│  (Streamlit)    │  Exposes /api/config endpoint (needs implementation)
└────────┬────────┘
         │
         │ HTTP GET /api/config
         ▼
┌─────────────────┐
│  scalp-engine   │  Loads config from API (primary)
│   (Worker)      │  Falls back to file if API unavailable
└─────────────────┘
```

### Config Loading Priority:

1. **API** (if `CONFIG_API_URL` is set) - Always gets latest from UI
2. **File** (fallback) - `/var/data/auto_trader_config.json`
3. **Default** - `MANUAL` mode if neither available

## Next Steps

### Step 1: Add Config API Endpoint to `scalp-ui`

**Option A: Add to `scalp_ui.py` (Recommended)**

Add Flask/FastAPI routes to `scalp_ui.py` running on separate port/thread:

```python
# In scalp_ui.py - add at top
from flask import Flask, jsonify
import threading

# Create Flask app for API
api_app = Flask(__name__)

@api_app.route('/api/config', methods=['GET'])
def get_config():
    config_path = "/var/data/auto_trader_config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return jsonify(json.load(f)), 200
    else:
        # Return default
        return jsonify({'trading_mode': 'MANUAL', ...}), 200

# Run Flask in separate thread
def run_api():
    api_app.run(host='0.0.0.0', port=8502, debug=False)

# Start API in background thread
threading.Thread(target=run_api, daemon=True).start()
```

**Option B: Use Separate Config API Service**

Deploy `config_api_server.py` as a separate service in `render.yaml` (similar to `market-state-api`).

### Step 2: Set Environment Variable in Render

1. Go to Render Dashboard → `scalp-engine` service
2. Go to **Environment** tab
3. Add `CONFIG_API_URL` = `https://scalp-engine-ui.onrender.com/api/config`
4. Save and restart `scalp-engine`

### Step 3: Test

1. Update config in `scalp-ui` (change mode from MANUAL to AUTO)
2. Wait 60-180 seconds (config reload interval)
3. Check `scalp-engine` logs - should show:
   - `✅ Config loaded from API`
   - `🔄 Configuration reloaded from API: Mode: MANUAL → AUTO`

## Benefits

- ✅ **No disk sharing required** - Uses HTTP API instead
- ✅ **Real-time updates** - Config changes from UI immediately available to worker
- ✅ **Robust fallback** - Falls back to file if API unavailable
- ✅ **Same pattern** - Matches `indicator-alerts-worker` architecture
- ✅ **Scalable** - Can add authentication, caching, etc. later

## Files Modified

- ✅ `scalp_engine.py` - Added API config loading
- ✅ `config_api_server.py` - New config API server (optional)
- ✅ `render.yaml` - Added `CONFIG_API_URL` env var
- ⚠️ `scalp_ui.py` - **Needs** `/api/config` endpoint (see Step 1 above)

## Status

- ✅ Backend (`scalp-engine`) ready for API config loading
- ⚠️ Frontend (`scalp-ui`) needs `/api/config` endpoint implementation
