# Diagnose Missing Market State File After 4pm Run

## Issue Summary

Trade-Alerts was scheduled to run at 4:00 PM EST (16:00), but `market_state.json` was either:
- Not generated (file doesn't exist), OR
- Not updated (file exists but is stale - older than 4 hours)

**If you see "Market State is Stale" in the UI:**
- The file EXISTS but is more than 4 hours old
- This means the 4pm scheduled run likely didn't update the file
- The file was probably created at an earlier scheduled time (e.g., 12:21 PM EST / 17:21 UTC)

## Root Causes (In Order of Likelihood)

### 1. Analysis Failed Before Step 9 (Most Likely)

The `market_state.json` file is only created at **Step 9** of the analysis workflow. If the analysis fails at any earlier step, the file won't be created.

**Check Trade-Alerts logs for:**
```
=== Scheduled Analysis Time: 2025-01-10 16:XX:XX EST ===
```

Then look for:
- ✅ `Step 1: Reading data from Google Drive...`
- ✅ `Step 2: Formatting data for LLMs...`
- ✅ `Step 3: Running LLM analysis...`
- ✅ `Step 4: Synthesizing with Gemini...`
- ✅ `Step 5 (NEW): Enhancing recommendations with RL insights...`
- ✅ `Step 6: Sending enhanced recommendations email...`
- ✅ `Step 7 (NEW): Logging recommendations to RL database...`
- ✅ `Step 8: Extracting entry/exit points...`
- ✅ `Step 9 (NEW): Exporting market state for Scalp-Engine...` ← **Must see this**
- ✅ `✅ Market State exported to /var/data/market_state.json` ← **Must see this**

**If you see:**
- `❌ Analysis failed at...` → Analysis crashed before Step 9
- No Step 9 message → Analysis didn't complete
- `⚠️ Failed to export market state...` → Step 9 failed

### 2. Analysis Never Triggered

The scheduler has a 5-minute tolerance window. If Trade-Alerts was:
- Not running at 4:00 PM
- Restarted between 3:55 PM and 4:05 PM
- Checking outside the 5-minute window

It might miss the scheduled time.

**Check logs for:**
```
⏰ Next scheduled analysis: 2025-01-10 16:00 EST
=== Scheduled Analysis Time: 2025-01-10 16:XX:XX EST ===
```

**If you DON'T see the "Scheduled Analysis Time" message:** The analysis never triggered.

### 3. File Write Permission Issue

The file might have been attempted but failed due to permissions.

**Check logs for:**
```
❌ Permission denied exporting market state to /var/data/market_state.json
❌ Error exporting market state to /var/data/market_state.json: [error details]
```

**Verify permissions:**
```bash
# In Render Shell for trade-alerts service
ls -la /var/data/
touch /var/data/test_write.txt
rm /var/data/test_write.txt
```

### 4. Disk Mount Issue

The shared disk might not be properly mounted or accessible.

**Check logs for:**
```
MarketBridge initialized with shared disk path: /var/data/market_state.json
```

**Verify disk mount:**
```bash
# In Render Shell
df -h | grep /var/data
mount | grep /var/data
```

### 5. Environment Variable Not Set

If `MARKET_STATE_FILE_PATH` is not set, MarketBridge will write to a local directory instead.

**Check logs for:**
```
MarketBridge initialized with local path: /opt/render/project/market_state.json
```

Instead of:
```
MarketBridge initialized with shared disk path: /var/data/market_state.json
```

**Verify environment variable:**
```bash
# In Render Dashboard → trade-alerts → Environment
# Should see: MARKET_STATE_FILE_PATH=/var/data/market_state.json
```

---

## Diagnostic Steps

### Step 1: Check if Analysis Ran at 4pm

**In Render Dashboard → `trade-alerts` → Logs**

Search for: `16:00` or `4:00 PM` or `Scheduled Analysis Time`

**Expected log sequence:**
```
=== Scheduled Analysis Time: 2025-01-10 16:00:XX EST ===
Starting analysis workflow with RL integration...
Step 1: Reading data from Google Drive...
Step 2: Formatting data for LLMs...
...
Step 9 (NEW): Exporting market state for Scalp-Engine...
✅ Market State exported to /var/data/market_state.json
✅ Analysis completed successfully at 16:XX:XX EST
```

**If you see this but no file:** Check Step 2 below.

**If you DON'T see this:** The analysis never ran. Check why:
- Is Trade-Alerts service running?
- Check for errors before 4pm
- Verify scheduler configuration

### Step 2: Check for Export Errors

**In Trade-Alerts logs, search for:**
- `Step 9 (NEW): Exporting market state`
- `✅ Market State exported`
- `❌ Error exporting market state`
- `⚠️ Failed to export market state`

**If you see an error message**, note the exact error and check:
- Disk permissions
- Disk mount status
- Environment variables

### Step 3: Verify File Location

**In Render Shell (any service with access to shared disk):**

```bash
# Check if file exists anywhere
find /var/data -name "market_state.json" 2>/dev/null
find /opt/render/project -name "market_state.json" 2>/dev/null

# Check what's in /var/data
ls -la /var/data/

# Check file permissions
stat /var/data/market_state.json 2>/dev/null || echo "File does not exist"
```

### Step 4: Check MarketBridge Initialization

**In Trade-Alerts logs, search for:**
```
MarketBridge initialized with
```

**Should see:**
```
MarketBridge initialized with shared disk path: /var/data/market_state.json
```

**If you see:**
```
MarketBridge initialized with local path: ...
```

Then `MARKET_STATE_FILE_PATH` environment variable is not set correctly.

### Step 5: Check Analysis Completion Status

**In Trade-Alerts logs, look for:**
- `✅ Analysis completed successfully` → Analysis finished, check Step 9
- `❌ Analysis failed` → Analysis crashed, file won't be created
- No completion message → Analysis might still be running or hung

---

## Common Issues & Solutions

### Issue: Analysis Runs But File Not Created

**Possible causes:**
1. **Analysis failed at Step 1-8** → Check error messages in logs
2. **Export failed silently** → Check for `❌ Error exporting` messages
3. **File written to wrong location** → Check fallback path in logs

**Solution:**
- Check logs for the exact error
- Verify disk permissions and mount
- Check environment variables

### Issue: Analysis Never Triggered

**Possible causes:**
1. **Trade-Alerts not running** → Check service status
2. **Scheduler misconfiguration** → Check `ANALYSIS_TIMES` environment variable
3. **Time zone mismatch** → Verify `ANALYSIS_TIMEZONE` is set to `America/New_York`

**Solution:**
- Restart Trade-Alerts service
- Verify environment variables
- Check service logs for initialization errors

### Issue: Permission Denied

**Solution:**
```bash
# In Render Shell
# Check disk mount
df -h | grep /var/data

# Check permissions
ls -la /var/data/
stat /var/data

# Try creating test file
echo "test" > /var/data/test.txt && rm /var/data/test.txt
```

If test file creation fails, there's a disk mount or permission issue. Contact Render support.

---

## Immediate Fix: Manual Trigger

To generate the file immediately without waiting for next scheduled time:

**Option 1: Use run_immediate_analysis.py (if it exists)**

```bash
# In Render Shell for trade-alerts service
cd /opt/render/project
python run_immediate_analysis.py
```

**Option 2: Trigger via Python**

```bash
# In Render Shell for trade-alerts service
python -c "
from src.market_bridge import MarketBridge
bridge = MarketBridge()
state = bridge.export_market_state([], 'Test synthesis text')
print('File created:', bridge.filepath)
"
```

**Real fix (comprehensive):** See **`MARKET_STATE_STALE_CORRECTION_PLAN.md`** for the full correction plan (diagnosis, workarounds, root-cause fixes, prevention, and checklist).

**Option 3: Update Timestamp (Temporary Workaround)**

If the file exists but is stale, use the utility script:

```bash
# In Render Shell (trade-alerts or scalp-engine-ui service)
cd /opt/render/project
python update_market_state_timestamp.py
```

This updates only the timestamp - the market data (bias, regime, opportunities) will still be old.
**This is a temporary workaround only!** The real fix is to ensure Trade-Alerts runs successfully (see `MARKET_STATE_STALE_CORRECTION_PLAN.md`).

**Option 4: Create test file manually (for testing only)**

```bash
# In Render Shell (any service with /var/data access)
python3 << 'PYTHON_SCRIPT'
import json
from datetime import datetime

state = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "global_bias": "NEUTRAL",
    "regime": "NORMAL",
    "approved_pairs": ["EUR/USD", "USD/JPY"],
    "opportunities": [],
    "long_count": 0,
    "short_count": 0,
    "total_opportunities": 0
}

with open('/var/data/market_state.json', 'w') as f:
    json.dump(state, f, indent=4)

print(f"✅ Test file created with timestamp: {state['timestamp']}")
PYTHON_SCRIPT
```

---

## After Fix: Verify Next Scheduled Run

After fixing the issue, verify the next scheduled analysis will work:

1. **Check next scheduled time in logs:**
   ```
   ⏰ Next scheduled analysis: 2025-01-11 02:00 EST
   ```

2. **Monitor logs during next scheduled time**

3. **Verify file is created:**
   ```bash
   ls -la /var/data/market_state.json
   cat /var/data/market_state.json
   ```

---

## Prevention: Enhanced Logging

The updated `market_bridge.py` now includes:
- ✅ Proper logger usage (not print statements)
- ✅ Detailed error messages with stack traces
- ✅ Fallback path logging
- ✅ Initialization logging

This will help diagnose issues in future runs.
