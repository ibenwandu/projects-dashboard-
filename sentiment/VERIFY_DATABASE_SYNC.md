# Verify Database Sync Between Hugging Face and Render

## Current Status

✅ **Render Worker:** `DATABASE_URL` is set correctly
- Connection: `postgresql://sentiment_monitor_db_user:...@dpg-d5a1cv8gjchc73b1lk10-a/sentiment_monitor_db`
- Database: `sentiment_monitor_db`

❓ **Hugging Face:** Need to verify it's using the **External Database URL** pointing to the same database

## Step 1: Verify Hugging Face Database URL

1. Go to **Hugging Face Space** → **Settings** → **Repository secrets**
2. Check the `DATABASE_URL` value
3. It should be the **External Database URL** from Render

### Get External Database URL from Render:

1. Go to **Render Dashboard** → **`sentiment-monitor-db`** service
2. Click **"Info"** tab
3. Find **"External Database URL"** (different from Internal)
4. Copy it

### Compare the URLs:

**Render Worker (Internal):**
```
postgresql://sentiment_monitor_db_user:...@dpg-d5a1cv8gjchc73b1lk10-a/sentiment_monitor_db
```

**Hugging Face (should be External):**
```
postgresql://sentiment_monitor_db_user:...@dpg-d5a1cv8gjchc73b1lk10-a.oregon-postgres.render.com/sentiment_monitor_db
```

**Key Difference:**
- **Internal:** `dpg-xxx-a` (no domain, for Render services)
- **External:** `dpg-xxx-a.oregon-postgres.render.com` (with domain, for external access)

**Both should point to the same database:** `sentiment_monitor_db`

## Step 2: Test Database Connection

### Option A: Check Hugging Face Logs

1. Go to Hugging Face Space → **"Logs"** tab
2. Look for database connection messages
3. Should see: `✅ Using PostgreSQL database` or `✅ DATABASE_URL is set`

### Option B: Add Test Trade and Verify

1. **Add a test trade via Hugging Face UI**
   - Asset: `TEST/USD`
   - Direction: `long`
   - Click "Add Trade"

2. **Check Render Worker Logs** (wait 1-2 minutes for next check)
   - Should see the trade in watchlist
   - If still "Watchlist is empty" → databases are different

3. **Check Database Directly** (if possible)
   - Use Render Shell or database client
   - Query: `SELECT * FROM watchlist;`
   - Should see trades added from Hugging Face

## Step 3: Common Issues

### Issue 1: Different Database Names
**Symptom:** Both connected but different databases
**Fix:** Ensure both use same database name in connection string

### Issue 2: Hugging Face Using Wrong URL
**Symptom:** Hugging Face can't connect
**Fix:** Use **External Database URL** (not Internal)

### Issue 3: Connection String Format
**Symptom:** Connection errors
**Fix:** Ensure format is: `postgresql://user:password@host:port/database`

## Step 4: Quick Verification Query

If you have database access, run this query to see all trades:

```sql
SELECT asset, trade_direction, created_at FROM watchlist WHERE active = 1;
```

This will show:
- Trades added via Hugging Face
- Trades added via Render worker
- If empty, no trades are being saved

## Next Steps

1. **Verify Hugging Face `DATABASE_URL`** matches External URL
2. **Add a test trade** via Hugging Face
3. **Check Render worker logs** after next scheduled check (15 minutes)
4. **If still empty**, check database directly






