# Emy — AI Chief of Staff

**A fully autonomous AI agent for managing trading systems, job search automation, and personal knowledge management.**

![Status](https://img.shields.io/badge/status-production--ready-green) ![Phase](https://img.shields.io/badge/phase-5/5%20complete-brightgreen) ![Tests](https://img.shields.io/badge/tests-10/10%20passing-brightgreen)

---

## What is Emy?

Emy is an autonomous multi-agent system that runs 24/7, handling:

1. **Trading Monitoring** (Phase 1)
   - Real-time OANDA account monitoring
   - Render service health checks
   - Trading log analysis and anomaly detection

2. **Job Search Automation** (Phase 2)
   - Daily scraping across LinkedIn, Indeed, Glassdoor, ZipRecruiter
   - AI-powered job scoring (0.0-1.0 relevance)
   - Automatic resume tailoring for high-scoring positions

3. **Knowledge Management** (Phase 3)
   - Obsidian dashboard auto-update
   - MEMORY.md persistence across sessions
   - Git-based session logging

4. **Approval Gates & Self-Improvement** (Phase 4)
   - Intelligent approval requests for destructive actions
   - Automatic skill improvement when success rate < 80%
   - Versioned skill definitions with automatic rollback

5. **Conversational CLI** (Phase 5)
   - Natural language queries via Anthropic API
   - Function calling for intelligent task routing
   - Real-time system status and reporting

---

## Quick Start

### Installation

```bash
# Clone or navigate to the repository
cd /c/Users/user/projects/personal/.worktrees/emy

# Install dependencies
pip install -r requirements.txt

# Configure API key
# Copy your key from Emy-Anthropic-Key.txt
# Edit emy/.env and set ANTHROPIC_API_KEY=sk-...
```

### Verify Installation

```bash
# Run end-to-end tests (all 10 should pass)
bash test-e2e.sh

# Check system status
python emy.py status

# List available skills
python emy.py skills

# List available agents
python emy.py agents
```

### Start Interactive Mode

```bash
# Boot main event loop (runs all scheduled jobs)
python emy.py run

# Press Ctrl+C to stop
```

### Conversational Queries (Requires API Credits)

```bash
# Ask Emy to do something
python emy.py ask "What is my current system status?"
python emy.py ask "Run job search for analyst roles"
python emy.py ask "Check render service health"
```

---

## Architecture

### 5 Agents

| Agent | Domain | Responsibility |
|-------|--------|-----------------|
| **TradingAgent** | trading | OANDA monitoring, Render health, log analysis |
| **JobSearchAgent** | job_search | Multi-platform scraping, scoring, resume tailoring |
| **KnowledgeAgent** | knowledge | Obsidian updates, MEMORY.md, git commits |
| **ProjectMonitorAgent** | project_monitor | Monitor all Render services |
| **ResearchAgent** | research | Evaluate new project feasibility |

### 6 Scheduled Jobs (Running 24/7)

| Job | Frequency | Purpose |
|-----|-----------|---------|
| trading_health_check | 15 minutes | Monitor account & services |
| job_search_daily | Daily 9 AM | Search 4 platforms |
| resume_tailor_approved | Daily 10 AM | Tailor top-scoring resumes |
| obsidian_dashboard_update | Daily 8 PM | Update knowledge base |
| memory_persist | 4 hours | Save findings to MEMORY.md |
| skill_improvement_sweep | Daily 11 PM | Auto-improve underperforming skills |

### Technology Stack

- **Orchestration**: Claude Opus 4.6 (AI reasoning)
- **Sub-Agents**: Claude Haiku 4.5, Claude Sonnet 4.6
- **Database**: SQLite (task history, outcomes, spending)
- **Scheduling**: Internal tick-based (no external cron)
- **Tool Use**: Anthropic function calling
- **APIs**: OANDA, Render, LinkedIn, Indeed, Glassdoor, ZipRecruiter

---

## CLI Commands

### `python emy.py run`
Start main event loop (blocking). All 6 scheduled jobs execute autonomously.

```bash
python emy.py run
# [BOOT] Emy booting...
# [OK] Database verified
# [RUN] Emy main loop started. Press Ctrl+C to stop.
# [SCHEDULER] Executed: trading_health_check, job_search_daily, ...
```

### `python emy.py status`
Display system dashboard with metrics.

```bash
python emy.py status
# ============================================================
# Emy - AI Chief of Staff
# ============================================================
#
# [Task Status]
#   COMPLETED: 41
#   PENDING: 2
#
# [Budget]
#   [######------------------------] $0.00 / $5.00 (0.0%)
```

### `python emy.py ask "prompt"`
Execute conversational query via Anthropic API.

```bash
python emy.py ask "run job search for analyst roles"
# [CLI] Processing query: run job search for analyst roles...
#
# Status: Success
# Domain: job_search
# Task: search_daily
# Result: {
#   "jobs_found": 12,
#   "jobs_scored": 8,
#   "high_priority": 3
# }
```

### `python emy.py skills`
List all registered skills by domain.

```bash
python emy.py skills
# ======================================================================
# Emy Skills Registry
# ======================================================================
#
# [TRADING]
#   • trading_monitor — Monitor Render services for Trading
#   • render_health_check — Check Render health status
#
# [JOB_SEARCH]
#   • job_search_daily — Daily job search across platforms
#   • resume_tailor — Tailor resumes for high-scoring jobs
```

### `python emy.py agents`
List all sub-agents with details.

```bash
python emy.py agents
# ======================================================================
# Emy Sub-Agents
# ======================================================================
#
# TradingAgent
#   Domain: trading
#   Role: OANDA monitoring, Render health, Phase 1 logs
```

---

## Configuration

### Environment Variables (emy/.env)

```env
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional but recommended
EMY_DAILY_BUDGET_USD=5.00
EMY_LOG_LEVEL=INFO

# Optional: Trading monitoring
OANDA_ACCESS_TOKEN=...
OANDA_ACCOUNT_ID=...

# Optional: Alerts
PUSHOVER_USER_KEY=...
PUSHOVER_API_TOKEN=...
```

### OANDA Trading Configuration

Enable real trading on OANDA practice account with automatic risk management:

```env
OANDA_ACCESS_TOKEN=<your-token-here>
OANDA_ACCOUNT_ID=<your-account-id>
OANDA_ENV=practice  # Use 'practice' for testing, 'live' for production
```

**Risk Parameters** (enforced automatically):

```env
OANDA_MAX_POSITION_SIZE=10000      # Max units per trade
OANDA_MAX_DAILY_LOSS_USD=100.0     # Stop trading if daily loss exceeds this
OANDA_MAX_CONCURRENT_POSITIONS=5   # Max open trades simultaneously
```

All risk parameters are **hard limits** — trades violating these are automatically rejected and logged.

**Monitoring:**

```bash
python emy.py status  # Shows live account equity, margin, open positions
```

**Alerts:** Pushover notifications sent when trades execute or limits are violated.

### Emergency Kill-Switch

Create `.emy_disabled` file to disable all scheduled tasks:

```bash
touch .emy_disabled    # Disable
rm .emy_disabled       # Enable
```

---

## Production Deployment

### Automated Setup (Windows Task Scheduler)

```powershell
# Run as Administrator
powershell -ExecutionPolicy Bypass -File setup-task-scheduler.ps1
```

This registers Emy to start automatically at system boot and run continuously in the background.

### Manual Setup

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed Windows Task Scheduler configuration.

---

## Monitoring

### View Real-Time Logs

```bash
tail -f emy/data/emy.log
```

### Check Database Tasks

```bash
# Recent completed tasks
sqlite3 emy/data/emy.db "SELECT id, domain, status, description FROM emy_tasks ORDER BY id DESC LIMIT 20;"

# Daily API spend
sqlite3 emy/data/emy.db "SELECT model, COUNT(*) as calls, SUM(cost_usd) as total FROM api_spend WHERE DATE(timestamp) = DATE('now') GROUP BY model;"

# Skill outcomes (for self-improvement tracking)
sqlite3 emy/data/emy.db "SELECT skill_name, COUNT(*) as runs, SUM(success) as wins FROM skill_outcomes WHERE run_timestamp > datetime('now', '-7 days') GROUP BY skill_name;"
```

---

## Development

### Project Structure

```
emy/
├── emy.py                          # CLI entry point
├── main.py                         # Main orchestration loop
├── requirements.txt                # Dependencies
├── .env                            # Configuration (not in git)
│
├── core/                           # Core system components
│   ├── database.py                 # SQLite persistence
│   ├── delegation_engine.py        # Agent spawning
│   ├── task_router.py              # Domain routing
│   ├── approval_gate.py            # Approval mechanism
│   ├── skill_improver.py           # Auto-improvement
│   ├── disable_guard.py            # Kill-switch
│   └── cli_handler.py              # CLI processor
│
├── agents/                         # 5 sub-agents
│   ├── base_agent.py
│   ├── trading_agent.py
│   ├── job_search_agent.py
│   ├── knowledge_agent.py
│   ├── project_monitor_agent.py
│   └── research_agent.py
│
├── scheduler/                      # Job scheduling
│   └── emy_scheduler.py
│
├── skills/                         # Skill definitions (versioned)
│   ├── definitions/                # Markdown skill files
│   │   ├── trading_monitor.md
│   │   ├── job_search_daily.md
│   │   ├── skill_improvement.md
│   │   └── ... (11 total)
│   ├── skill_loader.py
│   ├── skill_registry.py
│   └── outcomes/                   # JSONL execution logs
│
├── tools/                          # External integrations
│   ├── api_client.py               # OANDA, Render APIs
│   ├── notification_tool.py        # Pushover alerts
│   ├── file_ops.py                 # File operations
│   ├── git_tool.py                 # Git operations
│   └── obsidian_tool.py            # Obsidian vault
│
└── data/                           # Runtime data (gitignored)
    ├── emy.db                      # SQLite database
    ├── emy.log                     # Log file
    └── .gitignore
```

### Database Schema

8 tables for complete task tracking:

- `emy_tasks` — All tasks with status and results
- `sub_agent_runs` — Agent execution records
- `skill_outcomes` — Skill success/failure tracking
- `approval_requests` — Approval gate history
- `schedule_runs` — Scheduled job execution
- `job_applications` — Job application tracking
- `api_spend` — API cost tracking
- `config` — System configuration

---

## Performance

### Resource Usage
- CPU: Minimal (mostly idle, CPU spikes only during jobs)
- Memory: ~100-150 MB (Python process)
- Disk: Database grows ~10 KB/day under normal operation
- Network: Periodic API calls (OANDA, job platforms, Anthropic)

### Cost

Default daily budget: **$5.00 USD**

Typical usage:
- TradingAgent: ~$0.10/day (4 calls × 25¢ each)
- JobSearchAgent: ~$1.50/day (2 jobs scraped, scored, tailored)
- KnowledgeAgent: ~$0.05/day (light API use)
- Skill improvements: ~$1.00/day (if triggered)
- Buffer: ~$2.35/day

**Total: ~$5.00/day** (configurable in .env)

---

## Troubleshooting

### "ANTHROPIC_API_KEY not configured"
- Check emy/.env file exists
- Verify ANTHROPIC_API_KEY=sk-... line present
- Restart Python process

### "Your credit balance is too low"
- Log in to https://console.anthropic.com/account/billing/overview
- Add credits to Anthropic account
- Wait 1-2 minutes for activation

### "Task Scheduler task not running"
- Verify setup-task-scheduler.ps1 completed successfully
- Check Windows Task Scheduler for "Emy Chief of Staff" task
- Review Task Scheduler event logs for errors

### Database Locked
- Kill any running `python emy.py run` processes
- Check that multiple instances aren't running
- Database should auto-recover on next start

---

## Roadmap

### Phase 6+ (Future)

Potential enhancements:
- Real-time ML model training on job market data
- Advanced portfolio optimization (trading)
- Multi-user support with role-based permissions
- Cloud deployment (AWS Lambda, Google Cloud)
- Web dashboard for monitoring
- Mobile alerts via SMS

---

## License

Internal project. Not for public distribution.

---

## Support

**Quick Help:**
```bash
python emy.py --help
```

**Detailed Documentation:**
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Production setup
- [CLAUDE.md](./CLAUDE.md) — Development guidelines
- `.env.example` — Configuration template

**Logs & Debugging:**
```bash
tail -f emy/data/emy.log          # Main log
sqlite3 emy/data/emy.db           # Database queries
python emy.py status              # System metrics
```

---

## Summary

Emy is production-ready with:

✅ **5 phases, all complete**
✅ **5 specialized agents**
✅ **6 scheduled jobs (24/7)**
✅ **11 versioned skills**
✅ **Conversational CLI interface**
✅ **Self-improving AI engine**
✅ **Windows Task Scheduler integration**
✅ **Complete monitoring & logging**
✅ **Emergency controls & kill-switch**

**Deploy to production:** Run `setup-task-scheduler.ps1` as Administrator.

**Start development:** Run `python emy.py run` to boot the main loop.

---

**Last Updated:** March 10, 2026
**Status:** Production Ready (All Tests Passing 10/10)
