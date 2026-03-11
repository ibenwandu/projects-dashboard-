---
name: approval_gate
domain: system
model: claude-opus-4-6
agent: Emy
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Emy requests human approval before executing destructive operations (deletes, resets, disables).

Uses Pushover notifications with 24-hour timeout. Auto-rejects if no response.
Provides a transparent audit trail of all approval requests and outcomes.

## Inputs

- `action`: Type of destructive action (delete_file, reset_database, disable_agent, etc.)
- `description`: What will be deleted/modified
- `reason`: Why this action is necessary
- `agent`: Which agent is requesting the action

## Steps

1. **Log Request**: Create approval_requests record with status='pending'
2. **Send Notification**: Pushover alert to user with action details
3. **Wait for Response**: Poll approval_requests table for status change
4. **Auto-Timeout**: After 24 hours, auto-reject if still pending
5. **Record Decision**: Log user's approval/rejection with timestamp
6. **Return Result**: Bool indicating whether action approved

## Output Format

```json
{
  "request_id": 1,
  "action": "delete_file",
  "agent": "KnowledgeAgent",
  "status": "approved",
  "timestamp": "2026-03-10T20:15:00Z",
  "timeout_hours": 24
}
```

## Database Schema

```sql
CREATE TABLE approval_requests (
  id INTEGER PRIMARY KEY,
  action_type TEXT NOT NULL,
  domain TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT,  -- 'pending' | 'approved' | 'rejected' | 'auto_rejected'
  resolution_notes TEXT,
  requested_at TIMESTAMP,
  resolved_at TIMESTAMP
)
```

## Self-Improvement Hooks

- If success_rate < 1.0: Review Pushover delivery; add retry logic
- If timeout_hours too low: Consider increasing to 48h for safety-critical actions
- If auto_rejection rate > 10%: Prompt user about approval backlog

