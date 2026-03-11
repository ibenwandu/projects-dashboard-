---
name: project_monitor
domain: project_monitor
model: claude-haiku-4-5-20251001
agent: ProjectMonitorAgent
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Monitor all deployed Render services for health, uptime, and anomalies.

Checks Trade-Alerts, Scalp-Engine, job-search-api, and sends alerts on downtime.

## Monitored Services

- **trade-alerts** (Market state monitoring)
- **scalp-engine** (Trading execution)
- **job-search-api** (Job search pipeline)

## Steps

1. **Query Render API**: Get status of each service
2. **Check Health**: Verify service is 'live' / running
3. **Log Status**: Record uptime, region, last deployment
4. **Alert on Down**: Send Pushover if service not live
5. **Report Summary**: Return all service statuses

## Status Codes

| Code | Meaning |
|------|---------|
| live | Service running and healthy |
| suspended | Service paused by user |
| unknown | API query failed |
| error | Exception during check |

## Output Format

```json
{
  "timestamp": "2026-03-10T10:15:00Z",
  "services_checked": 3,
  "all_healthy": true,
  "alerts_sent": 0,
  "services": {
    "trade-alerts": {
      "name": "trade-alerts",
      "healthy": true,
      "status": "live",
      "region": "us-east-1",
      "last_updated": "2026-03-10T10:00:00Z"
    }
  }
}
```

## Self-Improvement Hooks

- If false_alarm_rate > 5%: Increase sampling frequency to reduce noise
- If detection_lag > 30min: Consider more aggressive polling
- If Render API errors > 3%: Add retry logic with backoff

