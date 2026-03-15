# Week 7 Direct Render Deployment Checklist

**Status**: ✅ Ready for Production Deployment
**Date**: March 15, 2026
**Services**: 2 new (Celery Beat + 2 Workers), 2 existing (Gateway + Brain)

---

## Pre-Deployment Verification

- [x] render.yaml configured with Week 7 services (emy-celery-beat, emy-celery-worker)
- [x] All 4 tasks implemented and tested (23 tests passing)
- [x] Code reviewed (spec compliance + code quality approved)
- [x] No breaking changes to existing services
- [x] Email polling interval: 10 minutes (600 seconds)
- [x] Rate limiting: max 10 checks/hour
- [x] Retry logic: 3 attempts with exponential backoff (1s → 2s → 4s)

---

## Render Environment Setup

### Required Secret Variables (Set on Render Dashboard)

Add these to your Render service if not already configured:

| Variable | Value | Scope | Required For |
|----------|-------|-------|--------------|
| `REDIS_URL` | `redis://...` | Secret | Celery message broker (Beat + Workers) |
| `DATABASE_URL` | `sqlite:///emy.db` or postgres URL | Secret | Email polling log storage |
| `ANTHROPIC_API_KEY` | Your Claude API key | Secret | Agent response generation |
| `GMAIL_CREDENTIALS_JSON` | Service account JSON (base64 encoded) | Secret | Gmail API authentication |

**Gmail Setup Required:**
1. Create service account in Google Cloud Console
2. Generate JSON credentials file
3. Base64 encode the JSON: `base64 < credentials.json`
4. Set `GMAIL_CREDENTIALS_JSON` env var to base64 string on Render

---

## Deployment Steps

### Option 1: Render Dashboard (Manual)

1. Go to https://dashboard.render.com
2. Select your "personal" project
3. Click **Deploy** button
4. Confirm deployment of all 4 services:
   - emy-phase1a (Gateway) — existing
   - emy-brain (Brain) — existing
   - emy-celery-beat (NEW)
   - emy-celery-worker (NEW — 2 instances)
5. Wait for all services to build and start (~3-5 minutes)
6. Monitor logs for startup errors

### Option 2: Render CLI (Automated)

```bash
# Install Render CLI (if not already installed)
npm install -g @render-api/cli

# Authenticate
render login

# Deploy from this directory
render deploy --path . --services emy-celery-beat emy-celery-worker emy-phase1a emy-brain
```

### Option 3: Git Push (Webhook Auto-Deploy)

Not applicable for this session (public repo constraint). Use Options 1 or 2.

---

## Post-Deployment Verification

### 1. Check Service Status (Render Dashboard)

All services should show "Live":
- emy-phase1a: https://emy-phase1a.onrender.com/health
- emy-brain: https://emy-brain.onrender.com/health
- emy-celery-beat: Background service (no HTTP endpoint)
- emy-celery-worker: Background service (no HTTP endpoint)

### 2. Verify Email Polling Started

```bash
# Check Gateway status endpoint
curl https://emy-phase1a.onrender.com/emails/polling-status

# Expected response:
{
  "status": "active",
  "last_check": "2026-03-15T21:50:00Z",
  "email_count": 0,
  "next_check": "2026-03-15T22:00:00Z",
  "uptime_minutes": 5,
  "error_message": null
}
```

### 3. Check Celery Beat Logs

On Render dashboard:
- Select `emy-celery-beat` service
- Go to **Logs** tab
- Look for: `Scheduler: Sending due task check-inbox-every-10-minutes`
- Should appear every 10 minutes

### 4. Check Worker Logs

On Render dashboard:
- Select `emy-celery-worker` service
- Go to **Logs** tab
- Look for task execution logs when emails are processed

### 5. Monitor Email Processing

Send test email to configured Gmail account:
- Email arrives → Celery Beat detects it (within 10 minutes)
- Worker processes email (parses, classifies intent, routes to agent)
- Agent generates response
- Response sent via Gmail API
- Check Render logs for processing flow

---

## Troubleshooting

### Celery Beat Not Starting

**Symptom**: Service crashes or `ModuleNotFoundError`

**Solution**:
```bash
# Verify celery_config.py exists in emy/config/
# Verify redis and database URLs are set
# Check Render logs for actual error message
```

### Workers Not Processing Tasks

**Symptom**: Polling happens but no email processing

**Solution**:
1. Verify `REDIS_URL` is set correctly
2. Check worker concurrency: `--concurrency=4` (should process 4 tasks simultaneously)
3. Check database connectivity: verify `DATABASE_URL` works
4. Restart workers from Render dashboard

### Gmail Credentials Error

**Symptom**: `"Invalid service account credentials"`

**Solution**:
1. Regenerate service account JSON in Google Cloud
2. Ensure JSON is base64 encoded properly: `echo -n "$JSON" | base64 | wc -c`
3. Verify `GMAIL_CREDENTIALS_JSON` doesn't have line breaks
4. Test credentials locally first before deploying

### High Error Rate

**Symptom**: Polling errors in logs

**Solutions**:
- Check Gmail inbox quota (Rate limit: 10 checks/hour max)
- Verify Gmail API scopes: `gmail.send`, `gmail.readonly`
- Check network connectivity between Render and Google APIs
- Verify agent API key quota on Claude

---

## Monitoring & Maintenance

### Daily Checks (First Week)

- [ ] Email polling running every 10 minutes
- [ ] No rate limiting errors
- [ ] Worker concurrency at expected level (4 tasks/worker)
- [ ] Agent response generation working
- [ ] Email responses sending successfully

### Weekly Checks

- [ ] Polling log database growing (no blocked insertions)
- [ ] Error rate < 5%
- [ ] Average response time < 30 seconds
- [ ] No memory leaks (check Render memory usage)

### Log Retention

Render keeps logs for 7 days. Archive important logs:
```bash
# Export logs from Render dashboard → Text file
# Save to: emy/logs/production/week7_deployment.log
```

---

## Rollback Procedure

If Week 7 deployment causes issues:

1. **Stop Celery services**: Disable emy-celery-beat and emy-celery-worker from Render
2. **Restart Gateway**: Redeploy emy-phase1a service
3. **Verify existing functionality**: Test email endpoints without polling
4. **Review logs**: Check what failed and why
5. **Fix and redeploy**: Apply fixes to render.yaml and redeploy

---

## Next Steps

After successful deployment:
1. ✅ Email polling active (10-minute intervals)
2. ✅ Agents responding to incoming emails
3. ✅ Sandbox Gmail testing (if configured)
4. **Week 8**: Scheduled digest emails, webhook notifications, memory embeddings

---

**Deployment completed by**: Claude Code
**Ready for**: Production (with Gmail credentials configured)
**Services affected**: +2 new services (Celery Beat + Workers)
