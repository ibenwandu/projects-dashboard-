# Market State Sync Solution

## Problem
Scalp-Engine needs to read `market_state.json` from Trade-Alerts, but they run as separate services on Render without direct connection.

## Solution: Shared Disk on Render

Both services now use the **same shared disk** (`scalp-engine-data`) mounted at `/var/data`:

- **Trade-Alerts** writes `market_state.json` to `/var/data/market_state.json`
- **Scalp-Engine** reads `market_state.json` from `/var/data/market_state.json`
- **Scalp-Engine UI** also reads from `/var/data/market_state.json`

## Configuration

### Trade-Alerts (`render.yaml`)
```yaml
envVars:
  - key: MARKET_STATE_FILE_PATH
    value: /var/data/market_state.json  # Shared with Scalp-Engine
disk:
  name: scalp-engine-data  # Use same disk as Scalp-Engine
  mountPath: /var/data
```

### Scalp-Engine (`render.yaml`)
```yaml
envVars:
  - key: MARKET_STATE_FILE_PATH
    sync: false  # Set to /var/data/market_state.json in Render Dashboard
disk:
  name: scalp-engine-data  # Same disk as Trade-Alerts
  mountPath: /var/data
```

### Scalp-Engine UI (`render.yaml`)
```yaml
envVars:
  - key: MARKET_STATE_FILE_PATH
    sync: false  # Set to /var/data/market_state.json in Render Dashboard
disk:
  name: scalp-engine-data  # Same disk as Trade-Alerts
  mountPath: /var/data
```

## Setup Steps

### 1. Deploy Trade-Alerts with Shared Disk

1. Go to Render Dashboard → `trade-alerts` service
2. Ensure `render.yaml` is deployed (or manually configure):
   - **Disk**: `scalp-engine-data` mounted at `/var/data`
   - **Environment Variable**: `MARKET_STATE_FILE_PATH=/var/data/market_state.json`

### 2. Configure Scalp-Engine Services

1. Go to Render Dashboard → `scalp-engine` service
   - **Environment**: Add `MARKET_STATE_FILE_PATH=/var/data/market_state.json`
   - **Disk**: Should already be configured as `scalp-engine-data` at `/var/data`

2. Go to Render Dashboard → `scalp-engine-ui` service
   - **Environment**: Add `MARKET_STATE_FILE_PATH=/var/data/market_state.json`
   - **Disk**: Should already be configured as `scalp-engine-data` at `/var/data`

### 3. Verify Setup

1. **Check Trade-Alerts logs** after an analysis run:
   ```
   ✅ Market State exported to /var/data/market_state.json
   ```

2. **Check Scalp-Engine logs**:
   ```
   ✅ Market state loaded: BULLISH, TRENDING, 3 pairs
   ```

3. **Check Scalp-Engine UI**:
   - Should show market state without "Could not load market state" warning

## How It Works

1. **Trade-Alerts** runs scheduled analysis (7 times per day)
2. After analysis, `MarketBridge.export_market_state()` writes to `/var/data/market_state.json`
3. **Scalp-Engine** reads the file every loop iteration (checks for updates)
4. **Scalp-Engine UI** reads the file on each page load/refresh

## File Updates

- Trade-Alerts updates `market_state.json` **only** when:
  - Scheduled analysis completes successfully
  - New opportunities are found
  - Analysis runs (typically 7 times per day)

- Scalp-Engine reads the file **continuously** (every loop iteration)
- Scalp-Engine UI reads the file **on demand** (when page loads or refresh button clicked)

## Troubleshooting

### Market state not updating

1. **Check Trade-Alerts is running**:
   - Render Dashboard → `trade-alerts` → Logs
   - Should see scheduled analysis runs

2. **Check file is being written**:
   - Render Dashboard → `trade-alerts` → Shell
   - Run: `ls -la /var/data/market_state.json`
   - Run: `cat /var/data/market_state.json`

3. **Check file permissions**:
   - Both services should have read/write access to `/var/data/`
   - If not, ensure both services use the same disk name

4. **Check environment variables**:
   - Trade-Alerts: `MARKET_STATE_FILE_PATH=/var/data/market_state.json`
   - Scalp-Engine: `MARKET_STATE_FILE_PATH=/var/data/market_state.json`
   - Scalp-Engine UI: `MARKET_STATE_FILE_PATH=/var/data/market_state.json`

### "Could not load market state" in UI

1. **Verify file exists**:
   - Render Dashboard → `scalp-engine-ui` → Shell
   - Run: `ls -la /var/data/market_state.json`

2. **Check environment variable**:
   - Render Dashboard → `scalp-engine-ui` → Environment
   - Ensure `MARKET_STATE_FILE_PATH=/var/data/market_state.json` is set

3. **Check disk is mounted**:
   - Both services must use the same disk name: `scalp-engine-data`

## Benefits

✅ **Real-time sync**: File updates are immediately available to both services
✅ **No API needed**: Simple file-based communication
✅ **Persistent**: File survives service restarts
✅ **Shared storage**: Both services access the same data
✅ **Cost-effective**: Single shared disk for both services
