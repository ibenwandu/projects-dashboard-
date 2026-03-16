# Emy Trading Monitoring System — Deployment Guide

**Status:** Production Ready | **Date:** March 16, 2026 | **Version:** 1.0

---

## Architecture Overview

**Three-Service Architecture (Resilient Design):**

```
┌─────────────────────────────────────────────────────┐
│  emy-phase1a (Gateway)                              │
│  • HTTP API endpoints (port 8000)                   │
│  • User dashboard and interaction                   │
│  • External-facing service                          │
└────────────────┬────────────────────────────────────┘
                 │ Internal communication (HTTPS)
┌────────────────┴────────────────────────────────────┐
│  emy-brain (Backend Orchestration)                  │
│  • LangGraph agent orchestration                    │
│  • Workflow execution (port 8001)                   │
│  • Database and state management                    │
└────────────────┬────────────────────────────────────┘
                 │ Celery task coordination (Redis)
         ┌───────┴────────┐
         │                │
    ┌────▼─────┐     ┌────▼──────┐
    │ emy-      │     │  emy-     │
    │ scheduler │     │  worker   │
    │ (Beat)    │     │ (2x)      │
    │           │     │           │
    │ Schedules │     │ Executes  │
    │ monitoring│     │ monitoring│
    │ tasks     │     │ tasks     │
    └───────────┘     └───────────┘
         │                │
         └────────┬───────┘
                  │
          ┌───────▼────────┐
          │   Redis Broker │
          │  (Task queue)  │
          └────────────────┘
```

**Advantages:**
- ✅ Separate gateway from backend (no single point of failure)
- ✅ Monitoring tasks isolated in scheduler/worker (don't block main backend)
- ✅ Independent scaling for each component
- ✅ Clean separation of concerns

---

## Services Summary

| Service | Type | Purpose | Port | Auto-Restart |
|---------|------|---------|------|--------------|
| **emy-phase1a** | Web | User-facing gateway & API | 8000 | Yes |
| **emy-brain** | Web | Agent orchestration & backend | 8001 | Yes |
| **emy-scheduler** | Background | Celery Beat (task scheduling) | — | Yes |
| **emy-worker** | Background | Celery Workers (2x, 4 concurrency) | — | Yes |
| **emy-db** | Database | PostgreSQL (main database) | — | Managed |
| **emy-redis** | Redis | Celery message broker | — | Managed |

---

## Monitoring Tasks Configuration

**Scheduled via Celery Beat (emy-scheduler):**

| Task | Schedule | Purpose | Agent |
|------|----------|---------|-------|
| `trading_hours_enforcement_friday` | Friday 21:30 UTC | Close non-compliant trades at week end | TradingHoursMonitorAgent |
| `trading_hours_enforcement_weekday` | Mon-Thu 23:00 UTC | Close non-compliant trades at day end | TradingHoursMonitorAgent |
| `trading_hours_monitoring` | Every 6h (00:00, 06:00, 12:00, 18:00 UTC) | Monitor compliance continuously | TradingHoursMonitorAgent |
| `log_analysis_daily` | Daily 23:00 UTC | Analyze trading activity & detect anomalies | LogAnalysisAgent |
| `profitability_analysis_weekly` | Sunday 22:00 UTC | Generate optimization recommendations | ProfitabilityAgent |
| `check_inbox_periodically` | Every 10 minutes | Email polling (Week 7) | EmailPollingTask |

---

## Pre-Deployment Checklist

**Before deploying to Render, verify:**

- ✅ **Code committed:** All monitoring system code in git
- ✅ **render.yaml updated:** New scheduler/worker configuration
- ✅ **Environment secrets configured in Render:**
  - `REDIS_URL` — Redis connection string
  - `DATABASE_URL` — PostgreSQL connection string
  - `ANTHROPIC_API_KEY` — Claude API key
  - `OANDA_ACCESS_TOKEN` — OANDA trading account token
  - `OANDA_ACCOUNT_ID` — OANDA account ID
  - `GMAIL_CREDENTIALS_JSON` — Gmail OAuth credentials (for email polling)

**If any secrets missing in Render, the services won't start.**

---

## Deployment Steps

### Step 1: Verify Render Secrets

Go to **Render Dashboard** → **Settings** → **Environment Variables:**

Required secrets for emy-scheduler and emy-worker:
```
REDIS_URL = redis://...
DATABASE_URL = postgresql://...
ANTHROPIC_API_KEY = sk-...
OANDA_ACCESS_TOKEN = 116f1cbe...
OANDA_ACCOUNT_ID = 101-002-...
GMAIL_CREDENTIALS_JSON = {...}
```

✅ **If all present, proceed to Step 2**

❌ **If any missing:**
1. Add the missing secret to Render
2. Re-deploy services that need it
3. Then continue

---

### Step 2: Deploy Services (Render Dashboard)

**Order matters** (dependencies flow downward):

**First, deploy main services:**
1. Go to **emy-phase1a** → Click **Deploy**
   - Wait until status shows "Live" (2-3 min)

2. Go to **emy-brain** → Click **Deploy**
   - Wait until status shows "Live" (2-3 min)

**Then, deploy task services:**
3. Go to **emy-scheduler** → Click **Deploy**
   - Wait until status shows "Live" (2-3 min)
   - Logs should show: `[celery] Scheduler: Sending due task check-inbox-every-10-minutes`

4. Go to **emy-worker** → Click **Deploy**
   - Wait until status shows "Live" (2-3 min)
   - Logs should show: `[celery] celery@... ready`

---

### Step 3: Verify Deployment

**Check gateway health:**
```bash
curl https://emy-phase1a.onrender.com/health
# Should return: {"status": "ok"}
```

**Check backend health:**
```bash
curl https://emy-brain.onrender.com/health
# Should return: {"status": "ok"}
```

**Check scheduler is running:**
- Go to **emy-scheduler** → **Logs** tab
- Look for: `[celery] Scheduler: Sending due task`
- Should see this message every few seconds

**Check workers are ready:**
- Go to **emy-worker** → **Logs** tab
- Look for: `[celery] celery@... ready`

---

### Step 4: Monitor First Execution

**Next scheduled monitoring task:**

1. **If today is Mon-Thu before 23:00 UTC:**
   - Next execution: **Today at 23:00 UTC** (TradingHoursMonitorAgent enforcement)
   - Check logs at emy-scheduler for: `Task trading_hours_enforcement_weekday received`

2. **If today is Friday before 21:30 UTC:**
   - Next execution: **Today at 21:30 UTC** (TradingHoursMonitorAgent Friday close)
   - Check logs at emy-scheduler for: `Task trading_hours_enforcement_friday received`

3. **If after those times:**
   - Next execution: **Tomorrow at first scheduled time**
   - Monitoring every 6 hours runs at: 00:00, 06:00, 12:00, 18:00 UTC
   - Log analysis at: 23:00 UTC daily
   - Profitability at: Sunday 22:00 UTC

**Verify task executed:**
- emy-scheduler logs: `Task X received and started`
- emy-worker logs: `Task X completed`

---

## Post-Deployment Verification

**Test manual trigger (if API endpoint available):**

```bash
# Trigger monitoring check manually (if exposed via gateway)
curl -X POST https://emy-phase1a.onrender.com/api/monitoring/trigger \
  -H "Content-Type: application/json" \
  -d '{"agent": "trading_hours_monitor"}'
```

**Check database for results:**
- Log into emy-db PostgreSQL
- Query `monitoring_reports` table:
  ```sql
  SELECT * FROM monitoring_reports
  ORDER BY timestamp DESC
  LIMIT 5;
  ```
- Query `enforcement_audit` table:
  ```sql
  SELECT * FROM enforcement_audit
  ORDER BY timestamp DESC
  LIMIT 5;
  ```

**Check for Pushover alerts:**
- If monitoring detected issues, you should receive Pushover notifications
- Check your Pushover app for critical alerts from Emy

---

## Troubleshooting

### Services stuck in "Deploying"

**Check build logs:**
1. Go to service → **Logs** tab
2. Look for build errors (usually Python package conflicts)
3. Common fixes:
   - Check `emy/requirements.txt` for version conflicts
   - Verify all imports work locally: `python -c "import emy.tasks.monitoring_tasks"`
   - Restart the service from Render dashboard

### Scheduler not triggering tasks

**Check emy-scheduler logs:**
- Should see: `Scheduler: Sending due task` every 10 seconds
- If missing: Check that REDIS_URL and DATABASE_URL are set in secrets
- Verify Redis is accessible: `redis-cli -u $REDIS_URL ping`

### Worker not executing tasks

**Check emy-worker logs:**
- Should see: `[celery] celery@... ready` at startup
- For each task: `Task monitoring_tasks.* received` → `...succeeded`
- If not executing:
  - Check that Redis broker is reachable
  - Verify DATABASE_URL is set for task persistence
  - Check OANDA credentials are valid (for trading hours monitor)

### Tasks failing silently

**Check monitoring_reports table in database:**
```sql
SELECT report_type, critical, alert_message, created_at
FROM monitoring_reports
ORDER BY created_at DESC;
```

- Look for `critical = true` with error messages in `alert_message`
- This tells you why monitoring failed

### Pushover alerts not sending

**Verify in monitoring_reports:**
- Column `critical` should be `true` for anomalies
- Column `alert_sent` should be `true` after sending
- Check Pushover app settings for Emy service integration

---

## Monitoring System Status Commands

**Check if monitoring is active (local or via API):**

```bash
# Via emy-brain API (if exposed)
GET https://emy-brain.onrender.com/api/monitoring/status
# Returns: {"active": true, "last_check": "2026-03-16T18:00:00Z", ...}

# Via emy-scheduler logs
# Look for task execution logs in Render dashboard
```

---

## Next Steps After Deployment

1. **First 24 hours:** Monitor logs to ensure tasks execute on schedule
2. **First week:** Verify monitoring reports appear in database
3. **First month:** Review profitability recommendations for actionable insights
4. **Ongoing:** Set up alerts via Pushover for critical issues
5. **Monthly:** Review enforcement audit trail for compliance history

---

## Support & Documentation

**Related Documentation:**
- Design spec: `docs/plans/2026-03-16-emy-trading-monitoring-agents-design.md`
- Trading hours logic: `trading_hours_logic.md`
- Celery configuration: `emy/config/celery_config.py`

**Agent Implementation:**
- `emy/agents/trading_hours_monitor_agent.py`
- `emy/agents/log_analysis_agent.py`
- `emy/agents/profitability_agent.py`

**Database Schema:**
- `emy/core/database.py` (monitoring_reports, enforcement_audit tables)

---

## Rollback Procedure

If deployment needs to be rolled back:

1. In Render Dashboard, go to each service
2. Click **Deployment History**
3. Click **Redeploy** next to previous working version
4. Services will restart with previous code

---

**Deployment Ready:** All code committed, render.yaml updated, architecture documented.

**Ready to deploy?** Open https://dashboard.render.com and follow the Deployment Steps above.
