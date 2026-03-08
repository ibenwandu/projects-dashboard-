# Fix: Market State Not Loading in UI

## ✅ Good News

The UI is **working perfectly**! All import errors are resolved. The only remaining issue is the market state file path.

## Current Status

- ✅ UI loads successfully
- ✅ All imports working
- ✅ Database access working
- ⚠️ Market state file not found (expected on Render)

## The Issue

On Render, Trade-Alerts and Scalp-Engine are likely **separate services/repositories**, so the default path `../Trade-Alerts/market_state.json` won't work.

## Solutions

### Option 1: Shared Disk (Recommended)

If both Trade-Alerts and Scalp-Engine are on Render and use the same disk:

1. **Configure Trade-Alerts** to write `market_state.json` to the shared disk:
   ```python
   # In Trade-Alerts, when exporting market state:
   market_state_path = "/var/data/market_state.json"  # Shared disk path
   ```

2. **Configure Scalp-Engine UI** to read from shared disk:
   - Go to Render Dashboard → `scalp-engine-ui` → **Environment**
   - Add: `MARKET_STATE_FILE_PATH=/var/data/market_state.json`
   - Save and redeploy

### Option 2: Environment Variable

Set the path explicitly in Render:

1. Go to `scalp-engine-ui` → **Environment**
2. Add environment variable:
   - **Key**: `MARKET_STATE_FILE_PATH`
   - **Value**: `/var/data/market_state.json` (or wherever Trade-Alerts writes it)
3. Save and redeploy

### Option 3: If Trade-Alerts is on Different Server

If Trade-Alerts runs elsewhere (local, different service, etc.):

1. **Option A**: Use a webhook/API
   - Trade-Alerts posts market state to an endpoint
   - Scalp-Engine UI fetches from endpoint

2. **Option B**: Use a database
   - Both services write/read from same database
   - More reliable than file sharing

3. **Option C**: Manual upload
   - Upload `market_state.json` to Render disk manually
   - Or use Render Shell to copy file

## Quick Fix for Testing

To test the UI with sample data, you can create a test market state file:

1. Go to Render Dashboard → `scalp-engine-ui` → **Shell**
2. Create test file:
   ```bash
   cat > /var/data/market_state.json << 'EOF'
   {
     "timestamp": "2026-01-09T20:00:00Z",
     "global_bias": "BULLISH",
     "regime": "TRENDING",
     "approved_pairs": ["EUR/USD", "USD/JPY"],
     "opportunities": [],
     "long_count": 2,
     "short_count": 0,
     "total_opportunities": 2
   }
   EOF
   ```

3. Set environment variable:
   - `MARKET_STATE_FILE_PATH=/var/data/market_state.json`

4. Refresh UI - should now show opportunities!

## Verify Configuration

After setting the path, check UI logs for:
- ✅ No "Could not load market state" warning
- ✅ Market state data displayed
- ✅ Approved pairs shown

---

**Status**: UI is working! Just need to configure the market state file path. 🎉
