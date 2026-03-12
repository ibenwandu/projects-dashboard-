---
name: task_routing
domain: system
model: claude-opus-4-6
agent: Emy
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Emy routes incoming tasks to appropriate sub-agents based on domain and task type.

Provides intelligent task routing with approval gates for destructive operations.
Maintains extensible domain → agent mappings.

## Domain → Agent Mappings

| Domain | Agent | Responsibilities |
|--------|-------|------------------|
| trading | TradingAgent | OANDA monitoring, Render health, Phase 1 logs |
| job_search | JobSearchAgent | Platform scraping, scoring, resume tailoring |
| knowledge | KnowledgeAgent | Obsidian updates, MEMORY.md, git commits |
| project_monitor | ProjectMonitorAgent | All Render services, downtime alerts |
| research | ResearchAgent | New project evaluation, feasibility analysis |

## Destructive Actions

These actions require approval before execution:

- delete_file
- reset_database
- disable_agent
- clear_cache
- modify_config
- force_reconciliation

## Steps

1. **Validate Domain**: Check if domain is registered
2. **Check Destructive**: Determine if action requires approval
3. **Request Approval**: If destructive, request via approval_gate
4. **Route to Agent**: Call delegation_engine.spawn_registered()
5. **Return Result**: (success, results) tuple

## Output Format

```json
{
  "route_id": "task-123",
  "domain": "trading",
  "agent": "TradingAgent",
  "success": true,
  "duration_seconds": 0.45,
  "results": {}
}
```

## Configuration

Add new domain routing:
```python
task_router.register_domain('blockchain', 'BlockchainAgent')
task_router.mark_destructive('reset_blockchain')
```

## Self-Improvement Hooks

- If routing_errors > 5%: Review domain mappings for accuracy
- If destructive_action_errors > 2: Check approval_gate integration
- If latency > 2s: Consider async routing for heavy tasks

