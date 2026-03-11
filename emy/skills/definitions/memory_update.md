---
name: memory_update
domain: knowledge
model: claude-haiku-4-5-20251001
agent: KnowledgeAgent
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Persist Emy's cross-session memory and decision records to MEMORY.md.

Ensures findings, patterns, and decisions are retained across sessions,
allowing future work to build on previous context and avoid re-learning.

## Inputs

- `findings`: List of key findings from recent work
- `decisions`: List of decisions made
- `blockers`: Active blockers or issues to track
- `next_steps`: Planned work for next session

## Steps

1. **Read** current MEMORY.md
2. **Parse** existing sections (findings, decisions, blockers)
3. **Append** new entries with timestamps
4. **Deduplicate** if same finding already recorded
5. **Prune** old entries (>30 days) if needed
6. **Write** updated memory back to file
7. **Verify** updates persisted

## Output Format

```json
{
  "timestamp": "2026-03-10T04:00:00Z",
  "memory_file": "/home/user/.claude/MEMORY.md",
  "entries_added": 3,
  "findings_count": 12,
  "decisions_count": 8,
  "blockers_active": 1,
  "status": "complete"
}
```

## Self-Improvement Hooks

- If entries_added = 0 over 5 runs: ensure decision logging is working
- If memory_file grows > 50KB: implement archival strategy
- If success_rate < 0.80: add backup memory location
