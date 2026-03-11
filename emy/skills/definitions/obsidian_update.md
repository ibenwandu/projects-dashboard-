---
name: obsidian_update
domain: knowledge
model: claude-haiku-4-5-20251001
agent: KnowledgeAgent
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Daily update of Obsidian knowledge base dashboard with project metrics and status.

Maintains 00-DASHBOARD.md as a living document reflecting project progress,
active work streams, and key performance indicators.

## Inputs

- `metrics`: Current project metrics
  - phase_completion (0-5, percentage)
  - tasks_completed (count)
  - budget_used (USD)
  - jobs_applied (count)
  - days_uptime (count)

## Steps

1. **Read** current 00-DASHBOARD.md
2. **Extract** metrics section
3. **Update** with latest data:
   - Phase completion status (Phase 0/1/2/3+)
   - Key statistics (tasks, budget, applications)
   - Last updated timestamp
4. **Write** back to vault
5. **Verify** file updated successfully

## Output Format

```json
{
  "timestamp": "2026-03-10T20:00:00Z",
  "file_updated": true,
  "metrics_updated": {
    "phase_completion": "Phase 3 in progress",
    "tasks_completed": 15,
    "budget_used_usd": 0.47,
    "jobs_applied": 24,
    "active_projects": ["Emy", "Trade-Alerts", "job-search"]
  },
  "status": "complete"
}
```

## Self-Improvement Hooks

- If success_rate < 0.80 over 5 runs: verify Obsidian file path accessibility
- If file update fails repeatedly: fall back to plain text update
