# 📋 Emy Operations Manual

**For**: Production environment (emy-phase1a + emy-brain on Render)
**Updated**: March 15, 2026
**Owner**: Ibe Nwandu

---

## Quick Start: Operating Emy

### Daily Tasks

**Every Morning (9:00 AM EDT)**
```bash
# 1. Check Gateway health
curl https://emy-phase1a.onrender.com/health

# 2. Check agent status
curl https://emy-phase1a.onrender.com/agents/status

# 3. Review workflow count from yesterday
curl "https://emy-phase1a.onrender.com/workflows?limit=1&offset=0"
```

Expected responses:
- Gateway: `{"status":"ok"}`
- Agents: All showing `"status":"healthy"`
- Workflows: Count should be reasonable (5-50/day depending on automation)

**Every Evening (6:00 PM EDT)**
```bash
# Check for any errors in logs
# Via Render Dashboard: emy-phase1a → Logs tab
# Search for: "ERROR" or "CRITICAL"
```

---

## Running Workflows Manually

### TradingAgent: Market Analysis

**When to use**: Check forex market conditions, get trading signals

```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"trading_health","agents":["TradingAgent"],"input":{}}'
```

**Response**: Market analysis with EUR/USD, GBP/USD, USD/JPY, AUD/USD signals

### ResearchAgent: Project Evaluation

**When to use**: Evaluate new project ideas, assess feasibility

```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"research_evaluation","agents":["ResearchAgent"],"input":{"topic":"Your Topic Here"}}'
```

**Response**: Technical feasibility, complexity, risks, recommendations

### KnowledgeAgent: Query Knowledge Base

**When to use**: Get insights from your knowledge base, review priorities

```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"knowledge_query","agents":["KnowledgeAgent"],"input":{"query":"Your question here"}}'
```

**Response**: Synthesis from CLAUDE.md, MEMORY.md, session logs

---

## Monitoring & Alerts

### Weekly Health Check

| Check | Command | Expected |
|-------|---------|----------|
| **Gateway Response** | `curl https://emy-phase1a.onrender.com/health` | `{"status":"ok"}` |
| **Brain Response** | `curl https://emy-brain.onrender.com/health` | `{"status":"ok"}` |
| **Agent Count** | `curl https://emy-phase1a.onrender.com/agents/status \| grep agent_name` | 3 agents listed |
| **Workflow Volume** | `curl "...workflows?limit=1" \| grep total` | Reasonable count |
| **Disk Usage** | Render Dashboard → Disks tab | <500MB used |

### Alert Conditions

**CRITICAL - Act immediately**:
- [ ] Health check returns error (service down)
- [ ] Brain service not responding (orchestration down)
- [ ] Database disk usage >1.8GB (near capacity)
- [ ] Any agent showing status "disabled"
- [ ] API response time >30 seconds consistently

**WARNING - Monitor closely**:
- [ ] More than 3 errors in logs per hour
- [ ] Rate limiting triggered >5 times per day
- [ ] Workflow average execution time >10 seconds
- [ ] Claude API daily budget usage >$8

---

## Database Operations

### Backup Procedure

**Weekly backup** (recommended: Sunday 11:00 PM):

```bash
# Via Render Dashboard:
# 1. Go to https://dashboard.render.com
# 2. Select emy-phase1a service
# 3. Click "Disks" tab
# 4. Find "emy-data" disk
# 5. Click "..." menu → "Download backup"

# File saved: emy_data_backup_YYYY-MM-DD.tar.gz
```

**What's backed up**:
- `/data/emy.db` - All workflows, metadata, status
- `/data/emy_brain.db` - Job queue, execution history

### Checking Database Health

```bash
# Via Render shell (click "Shell" in dashboard)
cd /data
ls -lh *.db              # Check file sizes
sqlite3 emy.db ".tables" # Verify schema
sqlite3 emy.db "SELECT COUNT(*) FROM workflows;" # Count workflows
```

---

## Emergency Procedures

### Shutdown Agents (Emergency Only)

**Method 1: Via GitHub**
```bash
# Locally:
touch /c/Users/user/projects/personal/.emy_disabled
git add .emy_disabled
git commit -m "EMERGENCY: Disable agents"
git push origin master

# Result: Agents disabled within 2 minutes of Render redeploy
```

**Method 2: Via Render Dashboard (Faster)**
1. Go to emy-phase1a → Settings → Environment
2. Add: `EMY_DISABLED=true`
3. Click "Save"
4. Result: Agents disabled immediately (no redeploy needed)

### Restart Services

**Full restart** (both services):
1. Render Dashboard → emy-phase1a → Manual Restart
2. Wait 1 minute
3. Render Dashboard → emy-brain → Manual Restart
4. Wait 1 minute
5. Health check both services

**Expected downtime**: 2-3 minutes total

### Recover from Database Corruption

**If database is corrupted**:
1. Check logs for corruption error
2. Try to backup current database (might fail)
3. Delete corrupted database file
4. Render will auto-reinitialize schema on restart
5. Workflows will be re-created by Gateway on next execution

---

## Performance Optimization

### If workflows are slow (>10s):

**Check 1**: Is job queue backed up?
```bash
curl "https://emy-phase1a.onrender.com/workflows?limit=100&offset=0" | grep total
# If total > 50, queue is backed up
```

**Check 2**: Is Brain service overloaded?
- Render Dashboard → emy-brain → Metrics
- Check CPU usage (should be <50%)
- Check Memory usage (should be <200MB)

**Check 3**: Is Claude API slow?
- Check Anthropic status page
- Review recent API errors in logs

**Solutions**:
- If queue backed up: Reduce polling interval (not recommended)
- If CPU high: Scale to higher plan or split agents to new service
- If API slow: Wait for Anthropic to recover; nothing to do locally

### If budget is approaching limit:

**Current setup**: $10/day for Claude API

**Optimization options**:
1. Reduce agent execution frequency
2. Optimize prompts to use fewer tokens
3. Use cheaper model (Haiku) for some agents
4. Cache responses for repeated queries

---

## Regular Maintenance Schedule

### Daily
- 9:00 AM: Health check both services
- 6:00 PM: Review error logs

### Weekly (Sunday)
- Check database disk usage
- Backup database
- Review cost vs budget
- List any recurring errors

### Monthly
- Full system audit
- Review OpenClaw parity gaps
- Plan next feature release
- Update MEMORY.md with learnings

---

## Support & Documentation

**In-service docs**:
- PRODUCTION_DEPLOYMENT.md - Full technical guide
- EMY_OPERATIONS_MANUAL.md - This file
- emy/README.md - Architecture overview
- Render Dashboard - Real-time logs and metrics

**External resources**:
- Render docs: https://render.com/docs
- Anthropic API: https://docs.anthropic.com
- FastAPI docs: https://fastapi.tiangolo.com

---

## Contact & Escalation

**If service goes down**:
1. Check Render Dashboard (https://dashboard.render.com)
2. Check Anthropic status (https://status.anthropic.com)
3. Review logs in Render dashboard
4. Restart services if needed
5. Document issue in CLAUDE_SESSION_LOG.md

**Production notes**:
- Emy runs on Render (cloud-hosted, not your local machine)
- No manual server maintenance required
- Render handles infrastructure automatically
- You only manage workflows via API

---

**Last Updated**: March 15, 2026, 5:30 PM EDT
**Status**: PRODUCTION READY ✅
