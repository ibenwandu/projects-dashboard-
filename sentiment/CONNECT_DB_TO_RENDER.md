# Connect PostgreSQL Database to Render Services

## The Problem

The `render.yaml` file defines the database connection, but if you created the services manually (not via Blueprint), the connection won't be automatic.

## Solution: Manual Connection

### Step 1: Verify Database Exists

1. Go to **Render Dashboard**
2. Check if you see a service named **`sentiment-monitor-db`** (PostgreSQL)
3. If it doesn't exist, create it:
   - **New +** → **PostgreSQL**
   - **Name:** `sentiment-monitor-db`
   - **Database:** `sentiment_monitor`
   - **User:** `sentiment_monitor`
   - **Plan:** Starter
   - Click **"Create Database"**

### Step 2: Get Database Connection String

1. Go to **`sentiment-monitor-db`** service
2. Click on **"Info"** tab
3. Find **"Internal Database URL"** (for Render services)
4. Copy the entire connection string
   - Format: `postgresql://user:password@host:port/database`

### Step 3: Add DATABASE_URL to Web Service

1. Go to **`sentiment-monitor-web`** service
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Add:
   - **Key:** `DATABASE_URL`
   - **Value:** Paste the Internal Database URL from Step 2
5. Click **"Save Changes"**

### Step 4: Add DATABASE_URL to Worker Service

1. Go to **`sentiment-monitor-worker`** service
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Add:
   - **Key:** `DATABASE_URL`
   - **Value:** Paste the **same** Internal Database URL from Step 2
5. Click **"Save Changes"**

### Step 5: Redeploy Services

After adding `DATABASE_URL`, Render will automatically redeploy both services.

**OR** manually trigger:
- Go to each service → **"Manual Deploy"** → **"Deploy latest commit"**

### Step 6: Verify Connection

1. **Check Web Service Logs:**
   - Go to `sentiment-monitor-web` → **"Logs"** tab
   - Look for: `✅ Using PostgreSQL database`

2. **Check Worker Service Logs:**
   - Go to `sentiment-monitor-worker` → **"Logs"** tab
   - Look for: `✅ Using PostgreSQL database`

3. **Test the Connection:**
   - Add a trade via Hugging Face UI
   - Check worker logs - it should see the trade
   - Both services should share the same data

## Alternative: Use Blueprint (Recommended for Future)

If you want to use the `render.yaml` configuration:

1. **Delete existing services** (or create new ones)
2. Go to **Render Dashboard** → **New +** → **Blueprint**
3. Connect your GitHub repository
4. Select the `render.yaml` file
5. Render will automatically create all services with proper connections

## Troubleshooting

### "DATABASE_URL not found"
- Make sure you added it to **both** services (web and worker)
- Check the variable name is exactly `DATABASE_URL` (case-sensitive)

### "Connection refused"
- Verify the database is running (green status)
- Make sure you used **Internal Database URL** (not External)
- Check firewall/network settings

### "Using SQLite database" in logs
- This means `DATABASE_URL` is not set or not being read
- Double-check the environment variable is saved
- Redeploy the service after adding it

### Services still using separate databases
- Make sure both services have the **exact same** `DATABASE_URL` value
- Verify the database name matches: `sentiment_monitor`

## Quick Check Command

You can verify the connection in Render Shell:

1. Go to service → **"Shell"** tab
2. Run: `echo $DATABASE_URL`
3. Should show the PostgreSQL connection string

If it's empty, the environment variable isn't set correctly.






