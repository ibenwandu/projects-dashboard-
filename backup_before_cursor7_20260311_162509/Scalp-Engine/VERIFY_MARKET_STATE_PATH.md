# Verify Market State File Path on Render

## Issue

Even after setting `MARKET_STATE_FILE_PATH` in Render, the UI still shows "Could not load market state."

## Debugging Steps

### Step 1: Verify Environment Variable is Set

1. Go to Render Dashboard → `scalp-engine-ui` → **Environment**
2. Check that `MARKET_STATE_FILE_PATH` exists
3. Verify the value is correct (e.g., `/var/data/market_state.json`)

### Step 2: Check if File Actually Exists

Use Render Shell to check:

1. Go to `scalp-engine-ui` → **Shell**
2. Run:
   ```bash
   ls -la /var/data/
   cat /var/data/market_state.json  # If it exists
   ```

### Step 3: Verify Trade-Alerts is Writing to That Path

If Trade-Alerts is also on Render:
1. Check Trade-Alerts service → **Environment**
2. Verify it's configured to write to `/var/data/market_state.json`
3. Check Trade-Alerts logs to see where it's writing the file

### Step 4: Check UI Logs for Path Info

The UI should log the path it's trying to use. Check Render logs for:
- What path is being checked
- File existence errors
- Permission errors

### Step 5: Test with Render Shell

Create a test file to verify path works:

```bash
# In Render Shell for scalp-engine-ui
echo '{"timestamp":"2026-01-09T20:00:00Z","global_bias":"NEUTRAL","regime":"NORMAL","approved_pairs":["EUR/USD"]}' > /var/data/market_state.json
```

Then refresh UI - should now show data.

---

## Common Issues

### Issue 1: File Doesn't Exist
**Solution:** Trade-Alerts needs to generate it first, or create it manually

### Issue 2: Wrong Path
**Solution:** Verify the exact path Trade-Alerts uses and match it

### Issue 3: Permission Issues
**Solution:** Check file permissions on the disk

### Issue 4: Environment Variable Not Applied
**Solution:** Restart the service after setting the variable

---

**Next Step:** Use Render Shell to verify the file exists at the configured path.
