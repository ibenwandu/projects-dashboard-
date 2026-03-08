# How to Verify Disk Sharing on Render

## Critical Issue: Separate Blueprints Cannot Share Disks

**IMPORTANT**: If Trade-Alerts and Scalp-Engine are deployed in **different Blueprints** on Render, they **CANNOT share the same disk**, even if they have the same disk name!

## Step 1: Check Blueprint Status

### In Render Dashboard:

1. **Check Trade-Alerts service**:
   - Go to Render Dashboard → `trade-alerts` service
   - Look for "Blueprint managed" tag
   - Note the Blueprint name (if any)

2. **Check Scalp-Engine services**:
   - Go to Render Dashboard → `scalp-engine` service
   - Look for "Blueprint managed" tag
   - Note the Blueprint name (if any)

3. **Check if they're in the same Blueprint**:
   - If both show "Blueprint managed" and same Blueprint name → ✅ They CAN share disks
   - If different Blueprint names or one is not Blueprint managed → ❌ They CANNOT share disks directly

## Step 2: Verify Disk Configuration

### For Trade-Alerts:

1. Go to Render Dashboard → `trade-alerts` → **Disk** tab
2. Verify:
   - Disk name: `scalp-engine-data`
   - Mount path: `/var/data`
   - Size: 1GB

### For Scalp-Engine:

1. Go to Render Dashboard → `scalp-engine` → **Disk** tab
2. Verify:
   - Disk name: `scalp-engine-data`
   - Mount path: `/var/data`
   - Size: 1GB

### For Scalp-Engine UI:

1. Go to Render Dashboard → `scalp-engine-ui` → **Disk** tab
2. Verify:
   - Disk name: `scalp-engine-data`
   - Mount path: `/var/data`
   - Size: 1GB

**⚠️ WARNING**: If services are in **different Blueprints**, even with the same disk name, they will have **SEPARATE disks**!

## Step 3: Test File Access (CRITICAL TEST)

### Test 1: Check if Trade-Alerts can write

1. Go to Render Dashboard → `trade-alerts` → **Shell**
2. Run:
   ```bash
   echo "test" > /var/data/test_file.txt
   ls -la /var/data/
   ```

### Test 2: Check if Scalp-Engine can read

1. Go to Render Dashboard → `scalp-engine` → **Shell**
2. Run:
   ```bash
   ls -la /var/data/
   cat /var/data/test_file.txt  # Should show "test"
   ```

**Result**:
- ✅ If Scalp-Engine sees `test_file.txt` → **Disks ARE shared** ✅
- ❌ If Scalp-Engine does NOT see `test_file.txt` → **Disks are NOT shared** ❌

### Test 3: Check if Scalp-Engine UI can read

1. Go to Render Dashboard → `scalp-engine-ui` → **Shell**
2. Run:
   ```bash
   ls -la /var/data/
   cat /var/data/test_file.txt  # Should show "test"
   ```

**Result**:
- ✅ If UI sees `test_file.txt` → **Disks ARE shared** ✅
- ❌ If UI does NOT see `test_file.txt` → **Disks are NOT shared** ❌

## Step 4: Verify Environment Variables

### For Trade-Alerts:

1. Go to Render Dashboard → `trade-alerts` → **Environment**
2. Verify:
   - `MARKET_STATE_FILE_PATH=/var/data/market_state.json` exists
   - Value is correct

### For Scalp-Engine:

1. Go to Render Dashboard → `scalp-engine` → **Environment**
2. Verify:
   - `MARKET_STATE_FILE_PATH=/var/data/market_state.json` exists
   - Value is correct

### For Scalp-Engine UI:

1. Go to Render Dashboard → `scalp-engine-ui` → **Environment**
2. Verify:
   - `MARKET_STATE_FILE_PATH=/var/data/market_state.json` exists
   - Value is correct

## Step 5: Check if Market State File Exists

### In Trade-Alerts Shell:

```bash
ls -la /var/data/market_state.json
cat /var/data/market_state.json  # If exists, shows content
```

**Expected**: File should exist if Trade-Alerts has run at least one analysis

### In Scalp-Engine Shell:

```bash
ls -la /var/data/market_state.json
cat /var/data/market_state.json  # If exists, shows content
```

**Result**:
- ✅ If file exists → **Either disks are shared OR file was created locally**
- ❌ If file does NOT exist → **Either disks are NOT shared OR Trade-Alerts hasn't run analysis yet**

## Step 6: Check Trade-Alerts Logs

1. Go to Render Dashboard → `trade-alerts` → **Logs**
2. Look for:
   ```
   ✅ Market State exported to /var/data/market_state.json
   ```

**If you see this**: Trade-Alerts is writing to the file correctly
**If you DON'T see this**: Trade-Alerts might not have run an analysis yet

## Step 7: Trigger Trade-Alerts Analysis (if needed)

If Trade-Alerts hasn't run analysis yet:

1. Go to Render Dashboard → `trade-alerts` → **Shell**
2. Run:
   ```bash
   python run_immediate_analysis.py
   ```
3. Check logs for:
   ```
   ✅ Market State exported to /var/data/market_state.json
   ```

## Troubleshooting

### Issue: Disks are NOT shared (different Blueprints)

**Solution 1: Combine into Single Blueprint**
- Create unified `render.yaml` with both Trade-Alerts and Scalp-Engine services
- Redeploy from single Blueprint
- Services will now share the same disk

**Solution 2: Use API/Webhook**
- Implement API endpoint in Scalp-Engine
- Modify Trade-Alerts to POST market state to API
- Works across different Blueprints

**Solution 3: Use External Storage**
- Use AWS S3, Google Cloud Storage, etc.
- Trade-Alerts writes to cloud storage
- Scalp-Engine reads from cloud storage

### Issue: Environment variable not set

**Solution**: Set `MARKET_STATE_FILE_PATH=/var/data/market_state.json` in Render Dashboard → Environment for each service

### Issue: File doesn't exist

**Possible causes**:
1. Trade-Alerts hasn't run analysis yet
2. Trade-Alerts analysis failed
3. File is being written to wrong location

**Solution**: Check Trade-Alerts logs and trigger analysis manually

### Issue: File exists but UI can't read it

**Possible causes**:
1. Environment variable not set correctly
2. File permissions issue
3. File path mismatch

**Solution**: 
1. Verify `MARKET_STATE_FILE_PATH` is set correctly
2. Check file permissions: `chmod 644 /var/data/market_state.json`
3. Verify path matches exactly

## Next Steps After Verification

Once you've verified the disk sharing status:

1. **If disks ARE shared**: The issue is likely environment variables or Trade-Alerts not running analysis
2. **If disks are NOT shared**: You need to either combine Blueprints or use API/webhook sync
