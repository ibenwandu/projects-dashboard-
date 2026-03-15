# Week 7: Email Polling Deployment Guide

## Prerequisites
- Redis instance (for Celery broker)
- Render account with emy-phase1a and emy-brain services
- Gmail API credentials configured
- All Week 6 tests passing

## Deployment Steps

### 1. Verify Redis is Running
```bash
redis-cli ping
# Response: PONG
```

### 2. Deploy Celery Services
```bash
# Render automatically deploys via render.yaml
# Verify both are running:
curl https://api.render.com/services | grep celery
```

### 3. Verify Polling is Running
```bash
curl https://emy-phase1a.onrender.com/emails/polling-status

# Expected response:
{
  "status": "active",
  "last_check": "2026-03-16T10:30:00Z",
  "email_count": 2,
  "next_check": "2026-03-16T10:40:00Z",
  "uptime": "0:45:30"
}
```

### 4. Verify Email Processing
Send test email to configured inbox. Polling should detect within 10 minutes, agent should respond within 5 minutes.

## Troubleshooting

### Polling not triggering
1. Verify Redis running: `redis-cli ping`
2. Verify Celery Beat running: `celery inspect active_queues`
3. Check logs: `celery inspect logs`

### Tasks not processing
1. Verify Workers running: `celery inspect stats`
2. Check task queue: `celery inspect active`

### Emails not being sent
1. Verify Gmail credentials valid
2. Check email_log table for failed sends
3. Review EmailClient logs

## Rollback
Remove Celery services from render.yaml and push to redeploy.
