# Emy Render Deployment Guide

## Overview

Emy is deployed on Render as **two separate services** following OpenClaw architecture:

1. **emy-phase1a** (Primary) - Gateway & Dashboard UI (port 8000)
2. **emy-brain** (Backend) - LangGraph Orchestration (port 8001)

Gateway calls Brain internally for multi-agent workflow execution.

---

## Deployment Steps

### Step 1: Create New Brain Service in Render Dashboard

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Select your GitHub repository
4. Configure:
   - **Name**: `emy-brain`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m emy.brain.service`
   - **Plan**: Standard ($12/month)
   - **Region**: Choose closest to you (same as gateway)

### Step 2: Set Environment Variables

Add these variables to Render dashboard (Settings → Environment):

**Service Configuration:**
```
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8001
ENV=production
LOG_LEVEL=INFO
```

**Database:**
```
BRAIN_DB_PATH=/data/emy_brain.db
```

**Job Queue:**
```
QUEUE_BATCH_SIZE=10
QUEUE_POLL_INTERVAL=5
```

**WebSocket:**
```
WS_HEARTBEAT_INTERVAL=30
```

**Rate Limiting:**
```
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

**Agents:**
```
AGENT_TIMEOUT=300
LANGGRAPH_DEBUG=false
EMY_LOG_LEVEL=INFO
EMY_HAIKU_MODEL=claude-haiku-4-5-20251001
EMY_SONNET_MODEL=claude-sonnet-4-6
EMY_OPUS_MODEL=claude-opus-4-6
EMY_DAILY_BUDGET_USD=10.00
```

**Security:**
```
CORS_ORIGINS=https://emy-phase1a.onrender.com
SENTRY_ENVIRONMENT=production
```

**Secrets (use Render secrets):**
- `ANTHROPIC_API_KEY=sk-ant-...`
- `OANDA_ACCESS_TOKEN=...`
- `OANDA_ACCOUNT_ID=...`

### Step 3: Add Persistent Volume

1. In Render dashboard → Service → Disks
2. Click "Add Disk"
3. Configure:
   - **Name**: `emy-brain-data`
   - **Size**: 2 GB
   - **Mount Path**: `/data`

This persists SQLite database across deployments.

### Step 4: Update Gateway Service

1. Go to existing **emy-phase1a** service
2. Settings → Environment
3. Add/update:
   ```
   BRAIN_SERVICE_URL=https://emy-brain.onrender.com
   ```

### Step 5: Deploy

1. Push this code to GitHub:
   ```bash
   git add render.yaml RENDER_DEPLOYMENT.md
   git commit -m "feat: Add Render Brain service configuration"
   git push origin master
   ```

2. Render auto-deploys on push to connected branch
3. Wait for both services to deploy (~2-3 minutes)

### Step 6: Verify Deployment

Test both services:

```bash
# Gateway health
curl https://emy-phase1a.onrender.com/health

# Brain health
curl https://emy-brain.onrender.com/health

# Job submission through Gateway
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "test",
    "agents": ["router"],
    "input": {"message": "test"}
  }'

# Job submission directly to Brain
curl -X POST https://emy-brain.onrender.com/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "test",
    "agent_groups": [["router"]],
    "input": {"message": "test"}
  }'
```

---

## Architecture Diagram

```
User Browser
  ↓
https://emy-phase1a.onrender.com (Gateway)
  ├─ Dashboard UI (port 8000)
  └─ REST API
       ↓
https://emy-brain.onrender.com (Brain - internal)
  ├─ Job submission (port 8001)
  ├─ WebSocket updates
  ├─ Checkpoint recovery
  └─ Multi-agent orchestration
       ↓
External APIs (Claude, OANDA, etc.)
```

---

## Monitoring

### Logs
- **Gateway**: Render Dashboard → emy-phase1a → Logs
- **Brain**: Render Dashboard → emy-brain → Logs

### Metrics
- **Response Time**: Monitor in Render dashboard
- **Errors**: Check logs for exceptions
- **Database Size**: Check `/data` disk usage

### Health Checks
Built-in health endpoints:
- `GET /health` - Returns `{"status": "ok", "timestamp": "..."}`

---

## Troubleshooting

### Brain service won't start
1. Check logs: "Render Dashboard → emy-brain → Logs"
2. Common issues:
   - Missing `ANTHROPIC_API_KEY` secret
   - Port already in use (shouldn't happen on Render)
   - Database permission error

### Gateway can't reach Brain
1. Verify `BRAIN_SERVICE_URL=https://emy-brain.onrender.com` on Gateway
2. Check if Brain service is running: `curl https://emy-brain.onrender.com/health`
3. Check CORS: Brain should allow `https://emy-phase1a.onrender.com`

### Database issues
1. Check disk space: Render Dashboard → Service → Disks
2. Verify mount path matches `BRAIN_DB_PATH=/data/emy_brain.db`
3. Restart service if database is locked

---

## Rolling Back

If deployment has issues:

1. **Revert code**: `git revert <commit-hash>`
2. **Redeploy**: `git push origin master`
3. **Or pause service**: Render Dashboard → Service → Settings → Pause

---

## Cost Estimation (Monthly)

| Service | Plan | Cost |
|---------|------|------|
| emy-phase1a | Standard | $12 |
| emy-brain | Standard | $12 |
| Database (Disks) | 3 GB total | Included |
| **Total** | | **~$24** |

---

## Next Steps

After deployment:
1. Run full verification suite in production
2. Test multi-agent workflows through Gateway
3. Monitor logs for errors (1-2 days)
4. Review OpenClaw parity gaps for remaining features
5. Plan Weeks 4-8 (JobSearchAgent with browser automation)
