---
name: skill_improvement
domain: system
model: claude-opus-4-6
agent: Emy
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Emy automatically improves underperforming skills using AI-driven optimization.

Monitors success rates, identifies skills < 80%, generates improvements, and auto-rolls back failures.
Maintains version history and backup for every improvement.

## Improvement Workflow

1. **Monitor**: Query skill_outcomes table for recent runs
2. **Identify**: Find skills with success_rate < 80% (min 5 runs)
3. **Analyze**: Extract failure patterns and edge cases
4. **Generate**: Call Claude Opus 4.6 to create improved version
5. **Backup**: Archive current version before writing
6. **Hot-Reload**: Reload skill registry without restarting Emy
7. **Test**: Run 3 trials of improved skill
8. **Rollback**: If new version fails, restore backup automatically
9. **Notify**: Send Pushover alert with improvement summary

## Versioning

Version numbers increment as: 1.0 → 1.1 → 1.2 → 2.0 (major bump at 10 minor)

Each version has:
- Timestamp of improvement
- Backup file location
- Success rate before/after
- Improvement notes

## Output Format

```json
{
  "timestamp": "2026-03-10T23:00:00Z",
  "skills_scanned": 15,
  "underperformers_found": 2,
  "improvements_applied": 1,
  "skills": [
    {
      "name": "job_search_daily",
      "old_version": "1.0",
      "new_version": "1.1",
      "old_success_rate": 0.72,
      "new_success_rate": 0.88,
      "status": "success"
    }
  ]
}
```

## Safety Mechanisms

- **Automatic Backup**: Previous version preserved before any improvement
- **Rollback Threshold**: If new version scores < 70% on 3 test runs, auto-revert
- **Hot-Reload**: No system restart required; skill available immediately
- **Versioning**: All versions tracked; any version can be restored manually

## Configuration

```python
# In emy/core/skill_improver.py
MIN_SUCCESS_RATE = 0.80      # Trigger improvement if below
MIN_RUNS_BEFORE_IMPROVE = 5  # Need 5+ runs before improving
ROLLBACK_THRESHOLD = 0.70    # Rollback if new version < 70%
```

## Self-Improvement Hooks

- If improvement_success_rate < 0.60: Review improvement prompt quality
- If rollback_rate > 20%: Use more conservative improvement prompts
- If unimproved_skills > 5: Consider manual review of high-impact skills

