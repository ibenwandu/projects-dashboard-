# Render Deployment Quick Reference

## Overview
Deploy Emy Phase 3 Week 3 to Render staging:
- **Service 1**: emy-brain (NEW - Backend orchestration)
- **Service 2**: emy-phase1a (EXISTING - Update with Brain URL)

---

## STEP 1: Create emy-brain Service (5 min)

### In Render Dashboard:
1. Click **"New +"** → **"Web Service"**
2. Connect to your GitHub repository (ibenwandu/Emy)
3. Configure:
   - **Name**: `emy-brain`
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m emy.brain.service`
   - **Plan**: Standard ($12/month)
   - **Region**: Same as emy-phase1a (probably us-east-1 or us-west-1)

4. Click **"Create Web Service"**

### What happens:
- Render creates service at `https://emy-brain.onrender.com`
- Initial deployment will fail (missing env vars) - that's OK, we'll add them next

---

## STEP 2: Add Environment Variables to emy-brain (3 min)

### In Render Dashboard → emy-brain → Settings → Environment:

**Copy & paste each group below** (or add individually):

### Group 1: Service Configuration
```
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8001
ENV=production
LOG_LEVEL=INFO
```

### Group 2: Database
```
BRAIN_DB_PATH=/data/emy_brain.db
```

### Group 3: Job Queue
```
QUEUE_BATCH_SIZE=10
QUEUE_POLL_INTERVAL=5
```

### Group 4: WebSocket
```
WS_HEARTBEAT_INTERVAL=30
```

### Group 5: Rate Limiting
```
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Group 6: Agents & Models
```
AGENT_TIMEOUT=300
LANGGRAPH_DEBUG=false
EMY_LOG_LEVEL=INFO
EMY_HAIKU_MODEL=claude-haiku-4-5-20251001
EMY_SONNET_MODEL=claude-sonnet-4-6
EMY_OPUS_MODEL=claude-opus-4-6
EMY_DAILY_BUDGET_USD=10.00
```

### Group 7: Security & Monitoring
```
CORS_ORIGINS=https://emy-phase1a.onrender.com
SENTRY_ENVIRONMENT=production
```

### Group 8: SECRETS (Use "Add Secret" button for these)

**Click "Add Secret" for each:**
1. `ANTHROPIC_API_KEY` = `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`

2. `OANDA_ACCESS_TOKEN` = `116f1cbe94410b0243cd32937034704d-a61ea14db95d2ae9f33c06f85c7b5ce6`

3. `OANDA_ACCOUNT_ID` = `101-002-38030127-001`

---

## STEP 3: Add Persistent Disk (2 min)

### In Render Dashboard → emy-brain → Disks:

1. Click **"Add Disk"**
2. Configure:
   - **Name**: `emy-brain-data`
   - **Mount Path**: `/data`
   - **Size**: 2 GB

3. Click **"Create Disk"**

### Why:
Persists SQLite database across deployments so data survives service restarts.

---

## STEP 4: Update Gateway Service (2 min)

### In Render Dashboard → emy-phase1a → Settings → Environment:

Add one new variable:
```
BRAIN_SERVICE_URL=https://emy-brain.onrender.com
```

### Why:
Gateway calls Brain service at this URL when executing workflows.

---

## STEP 5: Wait for Deployment (5-10 min)

1. Both services will automatically deploy on next push to GitHub
2. Check Render Dashboard → each service → Events for deployment logs
3. Wait for both services to show **"Active"** status with green checkmark

---

## STEP 6: Verify Deployment (5 min)

Run these commands to verify both services are working:

### Test Brain health:
```bash
curl https://emy-brain.onrender.com/health
```
**Expected output:**
```json
{"status":"ok","timestamp":"2026-03-15T..."}
```

### Test Brain job submission:
```bash
curl -X POST https://emy-brain.onrender.com/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "test",
    "agent_groups": [["router"]],
    "input": {"message": "test from Render"}
  }'
```
**Expected output:**
```json
{"job_id":"job_...","workflow_type":"test","status":"pending","created_at":"..."}
```

### Test Gateway health:
```bash
curl https://emy-phase1a.onrender.com/health
```
**Expected output:**
```json
{"status":"ok","timestamp":"2026-03-15T..."}
```

### Test Gateway calling Brain:
```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "test",
    "agents": ["router"],
    "input": {"message": "test through gateway"}
  }'
```
**Expected output:**
```json
{"workflow_id":"wf_...","type":"test","status":"completed","output":"..."}
```

---

## 🚨 Troubleshooting

### Service won't start
- Check logs: Render Dashboard → Service → Logs
- Common issues:
  - Missing `ANTHROPIC_API_KEY` secret
  - Disk mount path mismatch
  - Environment variable syntax error

### Gateway can't reach Brain
- Verify `BRAIN_SERVICE_URL=https://emy-brain.onrender.com` on Gateway
- Check if Brain service shows as "Active" (green checkmark)
- Brain logs should show incoming requests from Gateway

### Health check returns 404
- Wait a few seconds for service to fully start
- Refresh Render dashboard
- Check service logs for startup errors

---

## ✅ Checklist

- [ ] Created emy-brain service in Render
- [ ] Added all environment variables (8 groups)
- [ ] Added 3 secrets (ANTHROPIC_API_KEY, OANDA tokens)
- [ ] Added persistent disk (/data, 2GB)
- [ ] Updated Gateway with BRAIN_SERVICE_URL
- [ ] Both services show "Active" status
- [ ] Brain health check: 200 OK ✅
- [ ] Gateway health check: 200 OK ✅
- [ ] Brain job submission: Works ✅
- [ ] Gateway calling Brain: Works ✅

---

## Next Steps After Verification

1. **Monitor logs**: Watch both services for errors (1-2 days)
2. **Test workflows**: Submit multi-agent workflows through Gateway
3. **Check WebSocket**: Verify real-time updates work in production
4. **Review OpenClaw parity**: Identify gaps for Weeks 4-8
5. **Plan next phase**: JobSearchAgent with browser automation

---

## Quick Links

- **Render Dashboard**: https://dashboard.render.com
- **Emy GitHub**: https://github.com/ibenwandu/Emy
- **Deployment Guide**: RENDER_DEPLOYMENT.md (full reference)
- **Local Testing** (if needed): `python -m emy.brain.service` (localhost:8001)

---

**Estimated Total Time: 20-25 minutes**
- Create service: 5 min
- Add env vars: 3 min
- Add disk: 2 min
- Update Gateway: 2 min
- Deployment: 5-10 min
- Verification: 5 min
