# Emy Brain Service — Deployment Guide

## Overview

Emy Brain is a FastAPI-based async agent orchestration service. This guide covers local development, Render cloud deployment, and production monitoring.

## Prerequisites

- Python 3.9+
- SQLite3 (included with Python)
- pip or poetry for dependency management
- (Optional) Render account for cloud deployment

## Local Development

### 1. Setup

```bash
# Clone repository and navigate to project
cd emy

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env for local development (optional)
nano .env
```

### 2. Run Service

```bash
# Set environment
export ENV=development
export BRAIN_HOST=localhost
export BRAIN_PORT=8001

# Start service
python -m emy.brain.service

# Service available at:
# - REST API: http://localhost:8001
# - WebSocket: ws://localhost:8001/ws/jobs
# - Swagger UI: http://localhost:8001/docs
```

### 3. Test

```bash
# Run all tests
pytest tests/brain/ -v

# Run specific test
pytest tests/brain/test_integration_full.py -v

# With coverage
pytest tests/brain/ --cov=emy.brain --cov-report=html
```

## Render Deployment

### 1. Prepare Repository

```bash
# Ensure requirements.txt is current
pip freeze > requirements.txt

# Commit changes
git add .env.example requirements.txt emy/
git commit -m "Phase 3 Week 3: Real-time orchestration"
git push origin master
```

### 2. Create Render Service

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect GitHub repository
4. Configure:
   - **Name**: emy-brain-service
   - **Environment**: Python 3.9
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m emy.brain.service`
   - **Plan**: Paid ($7/month) or higher

### 3. Set Environment Variables

In Render dashboard → Environment:

```
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8001
ENV=production
BRAIN_DB_PATH=/data/emy_brain.db
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
CORS_ORIGINS=https://emy-dashboard.onrender.com
```

### 4. Persistent Disk

1. In Render dashboard → Disks
2. Add disk: 1GB at `/data`
3. Update `BRAIN_DB_PATH=/data/emy_brain.db` in env vars

### 5. Deploy

- Render auto-deploys on git push to master
- Monitor deployment in Render dashboard
- Logs available in Render → Logs

## Production Monitoring

### Health Checks

```bash
# Manual health check
curl https://emy-brain-service.onrender.com/health

# Response:
# {"status": "ok", "timestamp": "2026-03-14T..."}
```

### Logs

Logs are JSON formatted for easy parsing:

```json
{
  "timestamp": "2026-03-14T10:30:45.123456",
  "level": "INFO",
  "logger": "EMyBrain.Service",
  "message": "Emy Brain Service starting...",
  "module": "service",
  "function": "startup_event",
  "line": 265
}
```

### Metrics to Monitor

1. **Job Queue Depth**: Number of pending jobs
2. **Execution Time**: Average job completion time
3. **Error Rate**: Percentage of failed jobs
4. **WebSocket Connections**: Active real-time connections
5. **Rate Limit Hits**: API abuse attempts
6. **Database Size**: Growth of SQLite database

### Error Tracking (Optional)

Add Sentry integration:

```bash
# Set in Render environment
SENTRY_DSN=https://key@sentry.io/project-id
SENTRY_ENVIRONMENT=production
```

## Troubleshooting

### Service won't start

- Check logs: `python -m emy.brain.service`
- Verify Python 3.9+: `python --version`
- Verify port available: `lsof -i :8001`

### Database errors

- Check database path exists: `ls -la /data/`
- Verify write permissions: `touch /data/test.txt`
- On Render, ensure persistent disk is mounted

### WebSocket connection refused

- Check CORS origins in config
- Verify WebSocket endpoint: `ws://localhost:8001/ws/jobs`
- Browser console for detailed error

### Rate limiting too aggressive

- Increase limit: `RATE_LIMIT_REQUESTS=500`
- Increase window: `RATE_LIMIT_WINDOW=120`
- Or disable for specific endpoints in future updates

## Scaling

### Single-Instance Limits

Current architecture supports:
- ~100 concurrent connections
- ~1000 jobs per minute
- Database: ~100MB per year

### Multi-Instance Scaling

For higher throughput:

1. **Database**: Migrate to PostgreSQL (shared backend)
2. **Caching**: Add Redis for job result caching
3. **Job Queue**: Use centralized queue service (Celery, RabbitMQ)
4. **Load Balancer**: Render automatically handles this

## Deployment Checklist

Before production deployment:

- [ ] All tests passing locally: `pytest tests/brain/ -v`
- [ ] Environment variables configured in Render
- [ ] Persistent disk mounted at `/data`
- [ ] CORS origins set to actual dashboard URL
- [ ] Health endpoint responding: curl `/health`
- [ ] WebSocket connection working
- [ ] Rate limiting configured appropriately
- [ ] Error logging (Sentry) configured (optional)
- [ ] Database backup plan in place
- [ ] 48-hour monitoring after deployment

## Rollback

If issues occur after deployment:

```bash
# Render automatically keeps previous versions
# In Render dashboard:
1. Go to Deployments
2. Click previous successful deployment
3. Click "Re-deploy"

# Or revert code and push:
git revert HEAD
git push origin master
```

## Support

- Brain Service API Docs: `/docs` (Swagger UI)
- Issues or questions: Check logs or contact team
