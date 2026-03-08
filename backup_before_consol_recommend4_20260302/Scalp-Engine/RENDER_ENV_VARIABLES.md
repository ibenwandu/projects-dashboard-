# How to Configure Environment Variables in Render

## Important: Environment Variables are Set at the SERVICE Level, Not Blueprint Level

When you deploy from a Blueprint (`render.yaml`), Render creates **services** (like the worker service). Environment variables are configured on those **services**, not on the Blueprint itself.

---

## Step-by-Step: Where to Set Environment Variables

### Step 1: Navigate to the Service (Not Blueprint)

1. In Render Dashboard, go to **"Resources"** (left sidebar)
2. You should see a service named **"scalp-engine"** (the worker service)
3. **Click on "scalp-engine"** (the service, not the blueprint)

### Step 2: Go to Environment Tab

1. Once you're on the `scalp-engine` service page
2. Click on **"Environment"** tab (in the top navigation of the service page)
3. This is where you configure environment variables

### Step 3: Add Environment Variables

In the Environment tab, you'll see:
- Existing variables (if any from `render.yaml`)
- An **"Add Environment Variable"** button

Add these variables:

```
OANDA_ACCESS_TOKEN=your-token-here
OANDA_ACCOUNT_ID=your-account-id-here
OANDA_ENV=practice
```

---

## Alternative: If Service Doesn't Exist Yet

If the Blueprint hasn't been applied yet and no service exists:

### Option 1: Apply Blueprint First

1. Go back to the Blueprint page
2. Click **"Apply"** or **"Manual sync"** to create the service
3. Then navigate to the service to add environment variables

### Option 2: Add to render.yaml (But Still Need to Set in Dashboard)

You can add environment variables to `render.yaml`, but for sensitive values like API keys, you should:
1. Set them in the Render dashboard (more secure)
2. Use `sync: false` in `render.yaml` so they're not overwritten

---

## Visual Guide

```
Render Dashboard
├── Blueprints (Settings page - where you are now)
│   └── Scalp-Engine Blueprint
│       ├── Settings ← You are here (no env vars here)
│       ├── Resources ← Go here!
│       │   └── scalp-engine (service) ← Click this!
│       │       ├── Logs
│       │       ├── Environment ← Environment variables go HERE!
│       │       ├── Settings
│       │       └── ...
│       └── Syncs
```

---

## Quick Navigation

**From Blueprint Settings:**
1. Click **"Resources"** in the left sidebar
2. Click on **"scalp-engine"** service
3. Click **"Environment"** tab
4. Add your variables

---

## What You'll See in Environment Tab

Once you're in the service's Environment tab, you'll see:

- **Existing variables** (from `render.yaml` with default values)
- **Add Environment Variable** button
- Fields for:
  - **Key**: Variable name (e.g., `OANDA_ACCESS_TOKEN`)
  - **Value**: Variable value (your actual token)
  - **Sync**: Whether to sync from `render.yaml`

---

## Important Notes

1. **Blueprint vs Service**: 
   - Blueprint = Configuration template
   - Service = Actual running instance
   - Environment variables = Set on the Service

2. **Security**:
   - Never commit API keys to GitHub
   - Always set sensitive values in Render dashboard
   - Use `sync: false` in `render.yaml` for sensitive vars

3. **OANDA_ENV**:
   - If not set, defaults to `practice` (safe)
   - You can add it manually in the Environment tab
   - Or leave it unset - code will use `practice` by default

---

## Troubleshooting

**"I don't see a service yet"**
- Apply the Blueprint first (click "Apply" or "Manual sync")
- Wait for the service to be created
- Then navigate to the service

**"I don't see Environment tab"**
- Make sure you're on the **service** page, not the Blueprint page
- Look for "scalp-engine" in Resources
- Click on it to go to the service page

**"Variables from render.yaml aren't showing"**
- Variables with `sync: false` won't auto-populate
- You need to add them manually in the Environment tab
- This is by design for security

---

## Summary

✅ **Go to**: Resources → scalp-engine service → Environment tab
✅ **Add**: OANDA_ACCESS_TOKEN, OANDA_ACCOUNT_ID, OANDA_ENV
✅ **Save**: Click "Save Changes"
✅ **Deploy**: Service will restart with new variables

**Remember**: Environment variables are configured on the **service**, not the **blueprint**! 🎯

