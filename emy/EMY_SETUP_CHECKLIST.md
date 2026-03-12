# Emy Phase 1a Setup Checklist

**Goal**: Complete the Emy setup so it's ready for Phase 1b agent integration

---

## ✅ Phase 1a: Complete (March 12, 2026)

### Status
- [x] Code written (SQLiteStore, API, CLI, UI)
- [x] Tests implemented (80+ tests)
- [x] Docker configured and deployed
- [x] Render deployment live (emy-phase1a.onrender.com)
- [x] All API endpoints tested and verified
- [x] Documentation complete

---

## ⏳ Phase 1a Setup: Final Steps (2-3 minutes)

### Step 1: Configure Render Environment Variables

**Go to**: https://dashboard.render.com

**Navigate to**:
1. Services
2. Click **emy-phase1a**
3. Click **Environment** (left sidebar)

**Add these variables**:

| Variable | Value | Source |
|----------|-------|--------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | https://console.anthropic.com/account/keys |
| `ANTHROPIC_MODEL` | `claude-opus-4-6` | (or your preferred model) |
| `EMY_LOG_LEVEL` | `INFO` | (or DEBUG for verbose logs) |

**Steps**:
1. Click "Add Environment Variable"
2. Enter key name (e.g., `ANTHROPIC_API_KEY`)
3. Enter value (your API key)
4. Click "Add"
5. Repeat for each variable
6. **Important**: Click **Save Changes** button at bottom

### Step 2: Wait for Redeploy

After saving, Render will automatically redeploy the service with new environment variables.

**Check status**:
- Visit: https://dashboard.render.com → emy-phase1a → Deploys
- Wait for green checkmark ✅ (usually 1-2 minutes)

**Verify**:
```bash
curl https://emy-phase1a.onrender.com/health
# Should respond with: {"status":"ok","timestamp":"..."}
```

### Step 3: Test Phase 1b Integration

Once redeployed:

```bash
# Test agent workflow
curl -X POST https://emy-phase1a.onrender.com/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "test",
    "agents": ["KnowledgeAgent"],
    "input": {"query": "What is 2+2?"}
  }'

# Response should include workflow_id and status
# {"workflow_id":"wf_...", "type":"test", "status":"pending", ...}
```

---

## 🧪 Local Testing (Optional)

To test locally before deploying:

```bash
# 1. Install dependencies
cd emy
pip install -r requirements.txt

# 2. Set environment variables locally
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_MODEL=claude-opus-4-6

# 3. Start API
python -m uvicorn gateway.api:app --port 8000

# 4. In another terminal, test with CLI
python cli/main.py health
# Or use curl
curl http://localhost:8000/health
```

---

## 📋 Verification Checklist

After completing setup, verify:

- [ ] Render dashboard shows environment variables set
- [ ] Deployment shows green checkmark ✅
- [ ] `curl https://emy-phase1a.onrender.com/health` returns 200
- [ ] `curl https://emy-phase1a.onrender.com/agents/status` returns agent list
- [ ] API key is never logged or shown in browser (secure)

---

## 🚀 Next: What Comes After Setup?

Once environment variables are set, Phase 1b work can begin:

1. **Agent Implementation**: Replace stub agents with real Claude integration
2. **Skill System**: Implement skill versioning and auto-improvement
3. **Domain Integration**: OANDA, job search, Obsidian APIs
4. **Workflow Persistence**: Replace in-memory storage with Redis
5. **Real-time Updates**: WebSocket support for live status

---

## 🆘 Troubleshooting

### Render Deployment Not Starting
```
Check: Render dashboard → Logs tab
Look for: Python errors, missing dependencies
Fix: Push code changes to trigger rebuild
```

### API Returns 401 or 403
```
Check: ANTHROPIC_API_KEY is set in Render environment
Verify: Key is valid (test on console.anthropic.com)
Fix: Update key in Render dashboard
```

### Workflow Returns Empty Response
```
Check: ANTHROPIC_MODEL is set (e.g., claude-opus-4-6)
Check: Anthropic account has available credits
Verify: Model name is correct (no typos)
```

### Can't Connect to API
```
Verify: API is running (check Render Logs)
Check: URL is correct (https://emy-phase1a.onrender.com)
Verify: No firewall/proxy blocking (test with curl)
```

---

## 📚 Documentation

- **Full Setup**: See `README_PHASE_1A.md`
- **Architecture**: See `README.md`
- **API Reference**: See `gateway/api.py` (FastAPI auto-docs at /docs)
- **Completion Status**: See `PHASE_1A_COMPLETION.md`

---

## 💡 Tips

- API keys can be managed at: https://console.anthropic.com/account/keys
- Render environment variables are encrypted and never logged
- You can view logs anytime at: https://dashboard.render.com → emy-phase1a → Logs
- Render will auto-redeploy whenever you push code changes to the repo

---

**Last Updated**: March 12, 2026
**Next Review**: After environment variables are set on Render
**Status**: Ready for Phase 1b setup
