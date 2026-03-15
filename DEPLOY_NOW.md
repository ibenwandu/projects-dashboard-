# Week 7 Deployment — Quick Start (5 minutes)

## Manual Deployment via Render Dashboard

### Step 1: Open Render Dashboard
Visit: https://dashboard.render.com

### Step 2: Navigate to Your Project
- Select your "personal" project (or your Emy project name)
- You should see 4 services listed

### Step 3: Deploy Services
Click the **Deploy** button next to each service in this order:

| Service | Type | Action |
|---------|------|--------|
| emy-celery-beat | Background | Deploy |
| emy-celery-worker | Background | Deploy |
| emy-phase1a | Web | Deploy |
| emy-brain | Web | Deploy |

**Note**: Only the Beat and Worker services are NEW. Gateway and Brain should already be running.

### Step 4: Monitor Deployment
- Watch the service status change: "Deploying" → "Building" → "Live"
- Each service takes 2-5 minutes
- Check logs tab if any service fails

### Step 5: Verify Success

**Option A: Quick Test via Browser**
```
https://emy-phase1a.onrender.com/emails/polling-status
```
Should return JSON with polling status.

**Option B: Check Logs**
For each service, go to **Logs** tab and look for:
- **Beat**: `Scheduler: Sending due task check-inbox-every-10-minutes`
- **Workers**: `[celery] celery@... ready`
- **Gateway**: `Application startup complete`

---

## Deployment via Script

If you have Render API key:

```bash
export RENDER_API_KEY="your-api-key-from-dashboard"
./deploy-week7-render.sh
```

Gets API key here: https://dashboard.render.com/account/api-tokens

---

## What Gets Deployed

✅ **New Services:**
- emy-celery-beat (email polling every 10 minutes)
- emy-celery-worker (2 instances, 4 concurrency each)

✅ **Updated Files:**
- render.yaml (service configuration)
- emy/gateway/api.py (new endpoints: /emails/polling-status, /emails/trigger-polling)
- emy/database/schema.py (polling_log table)
- All agent email response handlers

✅ **Configuration:**
- Environment variables auto-loaded from Render secrets
- Redis broker connectivity
- Gmail API OAuth configuration

---

## Post-Deployment (5 minutes after "Live")

### Verify Email Polling Started

```bash
# Check status endpoint
curl https://emy-phase1a.onrender.com/emails/polling-status

# Expected output:
{
  "status": "active",
  "last_check": "2026-03-15T22:00:00Z",
  "email_count": 0,
  "next_check": "2026-03-15T22:10:00Z"
}
```

### Send Test Email

1. Send email to your configured Gmail address
2. Email arrives → Celery Beat detects it (within 10 minutes)
3. Worker processes → Agent responds → Response sent back
4. Check Render logs for processing flow

### Monitor Logs

```
Render Dashboard → Service → Logs

Look for:
- Beat: "Sending due task check-inbox"
- Worker: "Task ... received"
- Gateway: "POST /emails/process"
```

---

## Troubleshooting

**Services stuck in "Deploying"**
- Check build logs for errors
- Verify Python dependencies in emy/requirements.txt
- Restart service from Render dashboard

**No polling happening**
- Check Beat logs: should see scheduler messages every 10 minutes
- Verify REDIS_URL is set correctly
- Restart Beat service

**Worker errors**
- Check Worker logs for specific error message
- Verify DATABASE_URL and GMAIL_CREDENTIALS_JSON are set
- Restart workers

---

## Full Documentation

For detailed info, see:
- `WEEK7_RENDER_DEPLOYMENT.md` — Complete deployment guide with troubleshooting
- `docs/WEEK7_DEPLOYMENT.md` — Operations and monitoring
- `docs/SANDBOX_GMAIL_SETUP.md` — Setting up test emails

---

**Ready**: All code committed and tested ✅
**Action**: Deploy via Render Dashboard (link above)
**Time**: 5-10 minutes total (including startup time)
