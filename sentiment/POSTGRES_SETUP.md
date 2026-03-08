# PostgreSQL Setup Guide

## Step 1: Create PostgreSQL Database on Render

1. Go to Render Dashboard → **New +** → **PostgreSQL**
2. Configure:
   - **Name:** `sentiment-monitor-db`
   - **Database:** `sentiment_monitor`
   - **User:** `sentiment_monitor`
   - **Plan:** Starter (free tier available)
3. Click **"Create Database"**
4. Wait for database to be created (1-2 minutes)

## Step 2: Get Database Connection String

1. In Render Dashboard → `sentiment-monitor-db`
2. Go to **"Info"** tab
3. Copy the **"Internal Database URL"** (for services on Render)
   - Format: `postgresql://user:password@host:port/database`
4. Or use **"External Database URL"** (for Hugging Face)

## Step 3: Update Environment Variables

### For Render Services (Web + Worker)

The `render.yaml` is already configured to automatically use the database connection string. Just make sure:

1. The database service name matches: `sentiment-monitor-db`
2. Both services (web and worker) are in the same Render account

### For Hugging Face Space

1. Go to Hugging Face Space → **Settings** → **Repository secrets**
2. Add new secret:
   - **Name:** `DATABASE_URL`
   - **Value:** The External Database URL from Render
   - Format: `postgresql://user:password@host:port/database`

## Step 4: Deploy/Update Services

### Render Services

1. Push updated code to GitHub
2. Render will auto-detect changes and redeploy
3. Both services will automatically get `DATABASE_URL` from the database

### Hugging Face Space

1. After adding `DATABASE_URL` secret, the Space will auto-redeploy
2. Or manually trigger: **Settings** → **Rebuild Space**

## Step 5: Verify It's Working

1. **Add a trade via Hugging Face UI**
2. **Check Render worker logs** - it should see the same trade
3. **Check both services** - they should share the same data

## Database Connection String Format

```
postgresql://user:password@host:port/database
```

Example:
```
postgresql://sentiment_monitor:abc123@dpg-xxxxx-a.oregon-postgres.render.com:5432/sentiment_monitor
```

## Troubleshooting

### "psycopg2 not installed"
- Make sure `psycopg2-binary>=2.9.0` is in `requirements.txt`
- Redeploy the service

### "Connection refused"
- Check that `DATABASE_URL` is set correctly
- Verify database is running (Render Dashboard)
- Check firewall/network settings

### "Database does not exist"
- Make sure database name matches in connection string
- Verify database was created successfully

## Notes

- **Free tier:** Render PostgreSQL free tier has limitations (90 days, then requires upgrade)
- **Shared data:** Both Hugging Face UI and Render worker will use the same database
- **Backup:** Consider setting up automatic backups for production use






