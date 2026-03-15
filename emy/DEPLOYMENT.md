# Emy Brain Service Deployment Guide

This document explains how to configure and deploy the Emy Brain service to various environments.

## Quick Start

### Local Development

```bash
# Clone .env template
cp .env.example .env

# Edit .env with your development values
# Key settings for local development:
# - ENV=development
# - BRAIN_PORT=8001
# - BRAIN_DB_PATH=emy_brain.db (local file)
# - LOG_LEVEL=DEBUG

# Install dependencies
pip install -r requirements.txt

# Run the service
python -m emy.brain.service
```

### Render Deployment

1. **Create a new Web Service** in Render dashboard
   - Repository: Your GitHub fork of emy
   - Build command: `pip install -r requirements.txt`
   - Start command: `python -m emy.brain.service`

2. **Set Environment Variables** (Render dashboard → Service → Environment)
   ```
   BRAIN_HOST=0.0.0.0
   BRAIN_PORT=8001
   ENV=production
   BRAIN_DB_PATH=/data/emy_brain.db
   LOG_LEVEL=INFO
   SENTRY_ENVIRONMENT=production
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

3. **Add Persistent Volume** (optional, for data durability)
   - Mount path: `/data`
   - Size: 1 GB minimum

4. **Deploy**
   - Push to your branch on GitHub
   - Render auto-deploys on push

## Configuration Reference

All configuration is managed via environment variables. Copy `.env.example` to `.env` and update values for your environment.

### Service Configuration

```
BRAIN_HOST=0.0.0.0          # Bind address (0.0.0.0 = all interfaces)
BRAIN_PORT=8001             # Port number
ENV=production              # Environment: development or production
```

**Notes:**
- Local development: Use `localhost` or `0.0.0.0`
- Production (Render): Always use `0.0.0.0` (Render sets external hostname separately)

### Database Configuration

```
BRAIN_DB_PATH=/data/emy_brain.db    # Path to SQLite database
```

**Notes:**
- Local: Use relative path (e.g., `emy_brain.db`)
- Render: Use absolute path on persistent volume (e.g., `/data/emy_brain.db`)
- The file is created automatically if it doesn't exist

### Job Queue Configuration

```
QUEUE_BATCH_SIZE=10         # Jobs to process per batch
QUEUE_POLL_INTERVAL=5       # Seconds between queue checks
```

### WebSocket Configuration

```
WS_HEARTBEAT_INTERVAL=30    # Seconds between keepalive pings
```

**Notes:**
- Prevents connection timeouts for long-running jobs
- Adjust based on your network/firewall requirements

### Rate Limiting Configuration

```
RATE_LIMIT_REQUESTS=100     # Max requests per IP per window
RATE_LIMIT_WINDOW=60        # Time window in seconds
```

**Example:** With defaults, clients can make 100 requests per minute.

### Logging Configuration

```
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_FILE=/var/log/emy.log   # Optional: log file path
```

**Notes:**
- Development: Use `DEBUG` for verbose output
- Production: Use `INFO` or `WARNING`
- Console output always enabled (in addition to file)

### Monitoring Configuration

```
SENTRY_DSN=https://...      # Optional: Sentry error tracking
SENTRY_ENVIRONMENT=prod     # Tag for Sentry errors
```

**Setup:**
1. Create a Sentry project at https://sentry.io
2. Copy the DSN into `SENTRY_DSN`
3. Leave empty to disable Sentry

### Security Configuration

```
CORS_ORIGINS=*              # Comma-separated allowed origins
                            # Use * for development
                            # Use specific domains for production
```

**Examples:**
```
# Development
CORS_ORIGINS=*

# Production
CORS_ORIGINS=https://app.example.com,https://dashboard.example.com
```

### Agent Configuration

```
AGENT_TIMEOUT=300           # Agent execution timeout (seconds)
LANGGRAPH_DEBUG=false       # LangGraph debug mode
```

## Deployment Checklist

### Before First Deployment

- [ ] Copy `.env.example` to `.env`
- [ ] Review and update all configuration values
- [ ] Set `ENV=production` for production deployments
- [ ] Set appropriate log level (`INFO` or `WARNING`)
- [ ] Configure CORS_ORIGINS for your domain(s)
- [ ] Verify database path is writable
- [ ] Test locally: `python -m emy.brain.service`

### Render-Specific Setup

- [ ] Create persistent volume mounted at `/data`
- [ ] Set `BRAIN_DB_PATH=/data/emy_brain.db`
- [ ] Set `ENV=production`
- [ ] Configure custom domain (optional)
- [ ] Enable HTTPS (automatic with Render)
- [ ] Set `SENTRY_ENVIRONMENT=production`

### After Deployment

- [ ] Verify service is running: Check Render logs
- [ ] Test health endpoint: `curl https://your-service.onrender.com/health`
- [ ] Monitor error tracking: Check Sentry dashboard
- [ ] Verify database persists: Redeploy and confirm data survives

## Environment-Specific Examples

### Development Environment (.env)

```bash
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8001
ENV=development
BRAIN_DB_PATH=emy_brain.db
LOG_LEVEL=DEBUG
SENTRY_DSN=
CORS_ORIGINS=*
AGENT_TIMEOUT=600
LANGGRAPH_DEBUG=true
```

### Production Environment (Render)

```bash
BRAIN_HOST=0.0.0.0
BRAIN_PORT=8001
ENV=production
BRAIN_DB_PATH=/data/emy_brain.db
LOG_LEVEL=INFO
SENTRY_DSN=https://key@sentry.io/project
SENTRY_ENVIRONMENT=production
CORS_ORIGINS=https://myapp.com,https://api.myapp.com
AGENT_TIMEOUT=300
LANGGRAPH_DEBUG=false
```

## Docker Deployment

If deploying with Docker:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use environment variables at runtime
CMD ["python", "-m", "emy.brain.service"]
```

Build and run:

```bash
# Build
docker build -t emy-brain:latest .

# Run locally
docker run -e ENV=development \
  -e BRAIN_PORT=8001 \
  -e BRAIN_DB_PATH=/data/emy_brain.db \
  -v $(pwd)/data:/data \
  -p 8001:8001 \
  emy-brain:latest

# Run with .env file
docker run --env-file .env \
  -v $(pwd)/data:/data \
  -p 8001:8001 \
  emy-brain:latest
```

## Configuration Validation

The service validates configuration on startup:

```bash
# Check config loads correctly
python -c "from emy.brain.config import *; print(f'ENV={ENV}, PORT={BRAIN_PORT}')"
```

Expected output:
```
ENV=production, PORT=8001
```

## Troubleshooting

### Database Connection Error

**Error:** `Database locked` or `Cannot create database`

**Solution:**
1. Check `BRAIN_DB_PATH` is writable
2. Verify path exists (parent directory)
3. On Render, ensure persistent volume is mounted
4. Check file permissions: `ls -l /data/`

### Port Already in Use

**Error:** `Address already in use` on port 8001

**Solution:**
1. Check what's using the port: `lsof -i :8001`
2. Change `BRAIN_PORT` to an available port
3. Stop existing services on that port

### CORS Errors

**Error:** Browser blocks requests with CORS error

**Solution:**
1. Verify `CORS_ORIGINS` includes your client domain
2. Include protocol in domain: `https://example.com` not `example.com`
3. Use `*` for testing (development only)

### Configuration Not Applied

**Error:** Service ignores env vars in `.env` file

**Solution:**
1. Environment variables only work if they're actually in the environment
2. Use `export $(cat .env | xargs)` before running
3. Or use Docker/systemd to manage env vars
4. Verify: `echo $BRAIN_PORT` before running service

## Monitoring

### Health Endpoint

```bash
curl https://your-service.onrender.com/health
```

Response:
```json
{
  "status": "ok",
  "environment": "production",
  "database": "connected"
}
```

### Logs

**Local Development:**
```bash
# Run with DEBUG logging
ENV=development LOG_LEVEL=DEBUG python -m emy.brain.service
```

**Render:**
- View in Render dashboard → Service → Logs
- Filter by log level or search by message

### Error Tracking (Sentry)

1. Set up Sentry account (free tier available)
2. Create project, copy DSN
3. Set `SENTRY_DSN` in environment
4. Errors automatically reported to Sentry dashboard

## Next Steps

After successful deployment:

1. [Set up monitoring](./DEPLOYMENT.md#monitoring)
2. [Configure alerts](./DEPLOYMENT.md#error-tracking-sentry) (Sentry)
3. [Scale the service](./DEPLOYMENT.md#scaling) (if needed)
4. [Set up CI/CD](./DEPLOYMENT.md#cicd) (GitHub Actions, etc.)

## Support

For questions or issues:
1. Check logs: `tail -f /var/log/emy.log` or Render dashboard
2. Review configuration: `cat .env`
3. Test connectivity: `curl -v https://your-service.onrender.com/health`
4. Check Sentry: https://sentry.io (if configured)

---

**Last Updated:** March 14, 2026
**Version:** 1.0
