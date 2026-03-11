---
name: render_health_check
domain: trading
model: claude-haiku-4-5-20251001
agent: ProjectMonitorAgent
version: 1.0
success_rate: 1.0
invocation_count: 0
---

## Purpose

Monitor health of all Render services (Trade-Alerts, Scalp-Engine, config-api).
Report status and alert if any service is down or degraded.

## Inputs

- `services`: List of Render service IDs to monitor
- `alert_on_down`: Boolean, whether to send Pushover alerts (default: true)

## Steps

1. Fetch status of each Render service via API
2. Check if status is "live", "building", "deploy_in_progress", or "suspended"
3. Log any non-live services with details
4. If alert_on_down and service is down: send Pushover alert
5. Return summary (healthy, degraded, down)

## Output Format

```json
{
  "timestamp": "2026-03-10T17:00:00Z",
  "summary": "healthy|degraded|down",
  "services": {
    "trade-alerts": {
      "status": "live",
      "message": "OK"
    },
    "scalp-engine": {
      "status": "suspended",
      "message": "Service is suspended"
    }
  }
}
```

## Self-Improvement Hooks

- If success_rate < 0.80 over 5 runs: improve API retry logic
- If success_rate < 0.60 over 5 runs: simplify to direct checks instead of API
- If invocation_count > 1000: add caching layer
