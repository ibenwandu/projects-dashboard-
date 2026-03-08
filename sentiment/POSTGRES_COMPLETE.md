# PostgreSQL Setup Complete ✅

## What Was Done

1. **Updated `src/database.py`**:
   - Added PostgreSQL support with automatic fallback to SQLite
   - Handles both `?` (SQLite) and `%s` (PostgreSQL) parameter placeholders
   - Uses `RealDictCursor` for PostgreSQL to return dictionary-like rows
   - Automatically detects database type from `DATABASE_URL` environment variable

2. **Updated `requirements.txt`**:
   - Added `psycopg2-binary>=2.9.0` for PostgreSQL support

3. **Updated `render.yaml`**:
   - Added PostgreSQL database service definition
   - Both web and worker services now automatically get `DATABASE_URL` from the database
   - Database name: `sentiment-monitor-db`

4. **Created `POSTGRES_SETUP.md`**:
   - Step-by-step guide for setting up PostgreSQL on Render
   - Instructions for Hugging Face Space configuration

## Next Steps

### 1. Create PostgreSQL Database on Render

1. Go to **Render Dashboard** → **New +** → **PostgreSQL**
2. Configure:
   - **Name:** `sentiment-monitor-db`
   - **Database:** `sentiment_monitor`
   - **User:** `sentiment_monitor`
   - **Plan:** Starter (free tier)
3. Click **"Create Database"**
4. Wait 1-2 minutes for creation

### 2. Update Hugging Face Space

1. Go to your Hugging Face Space → **Settings** → **Repository secrets**
2. Add new secret:
   - **Name:** `DATABASE_URL`
   - **Value:** Copy the **"External Database URL"** from Render PostgreSQL dashboard
   - Format: `postgresql://user:password@host:port/database`

### 3. Deploy Updated Code

**For Render:**
- Push code to GitHub
- Render will auto-detect changes and redeploy
- Both services will automatically connect to PostgreSQL

**For Hugging Face:**
- After adding `DATABASE_URL` secret, the Space will auto-redeploy
- Or manually trigger: **Settings** → **Rebuild Space**

### 4. Verify It's Working

1. **Add a trade via Hugging Face UI**
2. **Check Render worker logs** - it should see the same trade
3. **Both services should share the same data**

## How It Works

- **If `DATABASE_URL` is set:** Uses PostgreSQL
- **If `DATABASE_URL` is not set:** Falls back to SQLite (for local development)

## Database Connection

The database automatically:
- Creates tables on first connection
- Handles both PostgreSQL and SQLite syntax
- Converts parameter placeholders automatically
- Returns dictionary-like rows for easy access

## Troubleshooting

### "psycopg2 not installed"
- Make sure `psycopg2-binary>=2.9.0` is in `requirements.txt`
- Redeploy the service

### "Connection refused"
- Check that `DATABASE_URL` is set correctly
- Verify database is running (Render Dashboard)
- For Hugging Face, use **External Database URL** (not Internal)

### "Database does not exist"
- Make sure database name matches in connection string
- Verify database was created successfully

## Notes

- **Free tier:** Render PostgreSQL free tier has limitations (90 days, then requires upgrade)
- **Shared data:** Both Hugging Face UI and Render worker will use the same database
- **Backup:** Consider setting up automatic backups for production use






