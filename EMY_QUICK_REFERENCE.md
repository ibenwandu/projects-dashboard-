# 📌 Emy Quick Reference Card

**Production URLs** (save these!)
- Gateway: https://emy-phase1a.onrender.com
- Brain: https://emy-brain.onrender.com

---

## ⚡ Quick Commands

### Check Status (30 seconds)
```bash
# Gateway health
curl https://emy-phase1a.onrender.com/health

# Agent status
curl https://emy-phase1a.onrender.com/agents/status
```

### Run TradingAgent (Forex Analysis)
```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"trading_health","agents":["TradingAgent"],"input":{}}'
```

### Run ResearchAgent (Project Evaluation)
```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"research_evaluation","agents":["ResearchAgent"],"input":{"topic":"Your Topic"}}'
```

### Run KnowledgeAgent (Query Knowledge Base)
```bash
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type":"knowledge_query","agents":["KnowledgeAgent"],"input":{"query":"Your Question"}}'
```

### List Workflows
```bash
curl "https://emy-phase1a.onrender.com/workflows?limit=10&offset=0"
```

### Get Workflow Details
```bash
curl https://emy-phase1a.onrender.com/workflows/wf_abc123
```

---

## 🚨 Emergency Commands

### Disable All Agents (Emergency Only)
```bash
touch /c/Users/user/projects/personal/.emy_disabled
git add .emy_disabled
git commit -m "EMERGENCY: Disable agents"
git push origin master
```

### Re-enable Agents
```bash
rm /c/Users/user/projects/personal/.emy_disabled
rm /c/Users/user/projects/personal/emy/.emy_disabled
git add -A
git commit -m "Re-enable agents"
git push origin master
```

---

## 📊 Daily Checklist

- [ ] 9:00 AM: `curl https://emy-phase1a.onrender.com/health`
- [ ] 9:00 AM: `curl https://emy-phase1a.onrender.com/agents/status`
- [ ] Check for errors in Render Dashboard logs
- [ ] 6:00 PM: Review workflow count

---

## 📚 Documentation

- **Full Production Guide**: PRODUCTION_DEPLOYMENT.md
- **Operations Manual**: EMY_OPERATIONS_MANUAL.md
- **This Card**: EMY_QUICK_REFERENCE.md

---

## 💰 Budget

- **Daily limit**: $10.00 USD (Claude API)
- **Monthly**: ~$325 (Render + API budget)
- **Status**: Monitored automatically, stops if exceeded

---

## 🔗 Links

- Render Dashboard: https://dashboard.render.com
- Claude API Status: https://status.anthropic.com
- GitHub: https://github.com/ibenwandu/Emy

---

**Last Updated**: March 15, 2026
**Status**: PRODUCTION LIVE ✅
