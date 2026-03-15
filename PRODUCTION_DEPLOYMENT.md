# 🚀 Emy Production Deployment Guide

**Status**: ✅ PRODUCTION READY
**Deployment Date**: March 15, 2026
**Uptime Target**: 24/7 autonomous operation
**Budget**: $10.00 USD/day (Claude API calls)

---

## Production Environment

```
Production Infrastructure:

Service 1: emy-phase1a (Gateway)
├─ URL: https://emy-phase1a.onrender.com
├─ Port: 8000
├─ Role: REST API entry point, dashboard UI
├─ Database: SQLite at /data/emy.db (persistent)
└─ Status: ✅ LIVE & HEALTHY

Service 2: emy-brain (Orchestration)
├─ URL: https://emy-brain.onrender.com
├─ Port: 8001
├─ Role: Job queue, agent execution, LangGraph
├─ Database: Job queue at /data/emy_brain.db
└─ Status: ✅ LIVE & HEALTHY

Communication: Gateway → Brain via HTTPS (async HTTP)
Job Polling: 5-second intervals, 60 max attempts (5 min)
Rate Limiting: 100 requests/minute per IP (active)
```

---

## Production Readiness Checklist

### Infrastructure ✅
- [x] Both services deployed on Render (Standard plan, $12/month each)
- [x] Persistent disks configured (/data mount, 2GB each)
- [x] CORS properly configured (Gateway → Brain communication)
- [x] Environment variables set for both services
- [x] Secrets (API keys) stored in Render Secrets Manager

### Code Quality ✅
- [x] All dependencies locked (no floating versions)
- [x] Database schema validated (workflows table operational)
- [x] Error handling implemented (try/catch on all API calls)
- [x] Logging configured (structured JSON logs)
- [x] Rate limiting active (100 req/min per IP)

### Agent Capabilities ✅
- [x] TradingAgent: Market analysis, OANDA integration ready
- [x] ResearchAgent: AI-powered feasibility analysis
- [x] KnowledgeAgent: Documentation, guidelines, insights
- [x] Project monitoring: Status tracking, metric updates

### Testing ✅
- [x] Health checks passing (both services)
- [x] Workflow execution tested (all 3 agents)
- [x] Database persistence verified
- [x] API endpoints validated (CRUD operations)
- [x] End-to-end workflow: Create → Execute → Store → Retrieve

### Monitoring ✅
- [x] Structured logging enabled
- [x] Agent activity tracked
- [x] Workflow lifecycle logged
- [x] Error logging configured

---

## Production API Reference

### Health Checks

**Gateway Health**
```bash
curl https://emy-phase1a.onrender.com/health
# Response: {"status":"ok","timestamp":"..."}
```

### Core Operations

**Submit Workflow (TradingAgent)**
```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"trading_health","agents":["TradingAgent"],"input":{}}'
```

**Get Workflow Status**
```bash
curl https://emy-phase1a.onrender.com/workflows/wf_abc123
```

**List Workflows**
```bash
curl "https://emy-phase1a.onrender.com/workflows?limit=10&offset=0"
```

**Check Agent Status**
```bash
curl https://emy-phase1a.onrender.com/agents/status
```

---

## Daily Monitoring Procedure

**Morning Check (9:00 AM EDT)**:
1. Health check: Both services responding
2. Agent status: All showing "healthy"
3. Workflow volume: Normal execution

**Evening Check (6:00 PM EDT)**:
1. Review error logs
2. Check persistent disk usage
3. Verify rate limiting not triggered

---

## Production Safety Features

### Budget Control
- Daily limit: $10.00 USD (Claude API)
- Set via `EMY_DAILY_BUDGET_USD` environment variable
- Agents stop if limit exceeded

### Emergency Shutdown
- **File-based**: Create `.emy_disabled` to stop agents
- **Environment**: Set `EMY_DISABLED=true`
- Use for emergency shutdown without redeployment

---

## Cost Estimation (Monthly)

| Component | Cost |
|-----------|------|
| Render Gateway (Standard) | $12/month |
| Render Brain (Standard) | $12/month |
| Persistent Disk (2GB × 2) | ~$0.50/month |
| Claude API (Budget: $10/day) | ~$300/month |
| **Total** | **~$325/month** |

---

## Troubleshooting

### Workflows stuck "pending"
- Verify Brain service is running (health check)
- Check Gateway has correct BRAIN_SERVICE_URL env var
- Check network connectivity

### Agent returns "disabled"
- Verify `.emy_disabled` file doesn't exist
- Check `EMY_DISABLED` environment variable not set
- Redeploy from GitHub if needed

### Database errors
- Check persistent disk has free space
- Verify SQLite integrity
- Check file permissions on /data

### High latency (>10s)
- Check if job queue backed up
- Monitor Brain service CPU/memory in Render
- Verify Claude API availability

---

## Next Steps

### Week 1: Stabilization
- Monitor 24/7 for edge cases
- Document issues and workarounds

### Week 2-3: Enhancement
- Review OpenClaw parity gaps
- Plan Weeks 4-8 features

### Week 4+: Expansion
- Add JobSearchAgent
- Implement browser automation
- Expand to additional services

---

**Production Status**: ✅ **LIVE AND OPERATIONAL**

Emy is now running 24/7 as your autonomous AI Chief of Staff.
