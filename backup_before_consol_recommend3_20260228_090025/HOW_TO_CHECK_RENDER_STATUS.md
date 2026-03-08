# How to Check if Trade-Alerts is Running Correctly on Render

## Quick Status Check (30 seconds)

### Step 1: Check Service Status
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Find the **`trade-alerts`** service
3. Check the status indicator:
   - ✅ **Green "Live"** = Service is running
   - ⚠️ **Yellow "Stopped"** = Service is stopped (click "Manual Deploy" to restart)
   - ❌ **Red "Failed"** = Service crashed (check logs for errors)

### Step 2: Check Recent Activity
1. Click on **`trade-alerts`** service
2. Go to **"Logs"** tab
3. Look for recent log entries (should be from today)
4. If no recent logs → Service might not be running

---

## Detailed Verification Steps

### 1. Check Service is Live ✅

**Render Dashboard → `trade-alerts` → Status**

**What you should see:**
- Status: **Live** (green)
- Last deployed: Recent timestamp
- Plan: Starter (or your plan)

**If not Live:**
- Click **"Manual Deploy"** → **"Deploy latest commit"** to restart

---

### 2. Check Logs for Continuous Operation ✅

**Render Dashboard → `trade-alerts` → Logs**

**Look for these signs of healthy operation:**

#### ✅ Good Signs (System is Running):

```
🚀 Trade Alert System Starting...
✅ Google Drive client initialized
✅ RL Database initialized
✅ System ready - Monitoring for scheduled times
```

**Continuous monitoring messages:**
```
Status Check - System running normally
Next analysis scheduled for: 2026-01-16 09:00:00 EST
```

**Scheduled analysis runs:**
```
=== Scheduled Analysis Time: 2026-01-16 09:00:00 EST ===
Step 1: Reading data from Google Drive...
Step 2: Formatting data for LLMs...
...
✅ Market state exported to /var/data/market_state.json
```

#### ❌ Bad Signs (Problems):

**Service crashed:**
```
❌ Fatal error: ...
Exception: ...
Service exited with code 1
```

**Service stopped:**
```
No recent log entries (logs are hours/days old)
```

**Google Drive errors:**
```
❌ Error accessing Google Drive
❌ Authentication failed
```

---

### 3. Check Scheduled Analysis Times ✅

**Trade-Alerts runs analysis at these times (EST/EDT):**
- **2:00 AM**
- **4:00 AM**
- **7:00 AM**
- **9:00 AM**
- **11:00 AM**
- **12:00 PM (Noon)**
- **4:00 PM**

**How to verify:**
1. Check logs around these times
2. Look for: `=== Scheduled Analysis Time: ... ===`
3. Should see complete analysis steps (Step 1-9)

**If no scheduled analysis:**
- Check if scheduler is running (should see "Status Check" messages)
- Verify service hasn't crashed
- Check logs for errors preventing analysis

---

### 4. Check Market State File Generation ✅

**Render Dashboard → `trade-alerts` → Shell**

**Run:**
```bash
ls -la /var/data/market_state.json
cat /var/data/market_state.json | head -20
```

**What you should see:**
- File exists with recent timestamp (updated after last analysis)
- File contains JSON with `opportunities`, `global_bias`, `regime`, etc.

**If file doesn't exist or is old:**
- Trade-Alerts might not have run analysis yet
- Check logs for errors during Step 9 (exporting market state)

---

### 5. Check RL Database Updates ✅

**Render Dashboard → `trade-alerts` → Shell**

**Run:**
```bash
ls -la /var/data/scalping_rl.db
```

**What you should see:**
- File exists: `scalping_rl.db`
- File size is growing (each analysis adds entries)
- Recent modification time

**To check database contents:**
```bash
cd /opt/render/project
python -c "
from src.rl.database import ScalpingRLDatabase
db = ScalpingRLDatabase('/var/data/scalping_rl.db')
print(f'Total entries: {len(db.get_all_entries())}')
"
```

**Expected:**
- Database should have entries from each analysis
- Count should increase over time

---

### 6. Check Email Alerts (If Configured) ✅

**Verify email is being sent:**

1. **Check logs for email messages:**
   ```
   📧 Sending enhanced recommendations email...
   ✅ Email sent successfully
   ```

2. **Check your inbox:**
   - Should receive email after each scheduled analysis
   - Email contains LLM-generated recommendations

**If emails not sending:**
- Check `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAIL` environment variables
- Verify SMTP settings in logs

---

## Common Issues & Solutions

### Issue 1: Service Shows "Stopped"

**Solution:**
1. Render Dashboard → `trade-alerts` → **"Manual Deploy"**
2. Click **"Deploy latest commit"**
3. Wait for deployment to complete
4. Check logs to verify it's running

---

### Issue 2: No Recent Logs (Service Appears Frozen)

**Possible causes:**
- Service crashed silently
- Service was stopped manually
- Render platform issue

**Solution:**
1. Check service status (should be "Live")
2. If "Failed" → Check logs for crash errors
3. If "Live" but no logs → Restart service manually

---

### Issue 3: Scheduled Analysis Not Running

**Symptoms:**
- Service is "Live"
- Logs show "System ready" but no analysis runs
- No `=== Scheduled Analysis Time ===` messages

**Solution:**
1. Check logs for scheduler initialization
2. Verify timezone settings
3. Trigger manual analysis to test (see below)

---

### Issue 4: Analysis Runs But No Market State File

**Symptoms:**
- Logs show analysis running
- But `market_state.json` is missing or not updated

**Solution:**
1. Check logs for Step 9: `Exporting market state for Scalp-Engine...`
2. Look for errors during file write
3. Verify disk permissions: `/var/data/` should be writable

---

## Trigger Manual Analysis (For Testing)

**To verify everything works, trigger an immediate analysis:**

**Render Dashboard → `trade-alerts` → Shell**

```bash
cd /opt/render/project
python -c "
from main import TradeAlertSystem
system = TradeAlertSystem()
system._run_full_analysis_with_rl()
"
```

**Expected output:**
```
Starting immediate analysis...
Step 1: Reading data from Google Drive...
✅ Downloaded X file(s)
Step 2: Formatting data for LLMs...
...
Step 9: Exporting market state for Scalp-Engine...
✅ Market state exported to /var/data/market_state.json
✅ Analysis complete
```

---

## Quick Health Checklist

Use this checklist to quickly verify everything is working:

- [ ] Service status shows **"Live"** (green)
- [ ] Logs show activity from today (not hours/days old)
- [ ] Logs show "Status Check" or "System running normally" messages
- [ ] Scheduled analysis runs are visible in logs (at expected times)
- [ ] `market_state.json` exists and was updated recently
- [ ] `scalping_rl.db` exists and is growing in size
- [ ] No error messages in recent logs
- [ ] Email alerts are being sent (if configured)

**If all checked ✅ → System is running correctly!**

---

## Monitoring Tips

1. **Check logs daily** to ensure scheduled analysis is running
2. **Monitor file timestamps** (`market_state.json`) to confirm updates
3. **Watch for error patterns** in logs (repeated errors indicate problems)
4. **Verify analysis schedule** matches expected times (7 times per day)

---

## When to Worry

**🚨 Immediate attention needed if:**
- Service status is "Failed" (red)
- No logs for > 24 hours
- Repeated error messages
- Analysis not running for > 2 scheduled times
- `market_state.json` not updating

**In these cases:**
1. Check logs for specific error messages
2. Restart the service
3. Verify environment variables are set correctly
4. Check Render service health/status

---

## Support

If issues persist:
1. **Check Render status page**: https://status.render.com
2. **Review logs** for specific error messages
3. **Verify environment variables** are set correctly
4. **Test manual analysis** to isolate the issue
