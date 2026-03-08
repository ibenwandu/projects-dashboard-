# How to Find Disk Identifier in Render Dashboard

## Problem
The Disk settings page shows mount path (`/var/data`) and size (1 GB) but **not the disk name/identifier** that Render uses to link services to the same physical disk.

## Solution: Check Render Dashboard "Disks" Section

### Step 1: Go to Global Disks View

1. In Render Dashboard, look for **"Disks"** in the left sidebar (top level, not under a service)
   - OR go to: `https://dashboard.render.com/disks`
   - OR click your profile → "Disks" (if available)

2. This shows **ALL disks** across your account with their names/identifiers

### Step 2: Identify Which Disk Each Service Uses

Look for disks named:
- `shared-market-data` (or similar)
- Any disk mounted at `/var/data`

Note which services are attached to each disk.

### Step 3: Verify if `scalp-engine` and `scalp-engine-ui` Share Same Disk

**Expected Result:**
- ✅ Both `scalp-engine` and `scalp-engine-ui` should be attached to the **SAME disk instance**
- ❌ If they're on **different disks** → That's the problem!

### Alternative: Use Shell to Compare

Run this in both Render Shells (one at a time):

```bash
# In scalp-engine-ui Shell
echo "=== UI DISK ==="; df -h /var/data/; echo ""; ls -lh /var/data/auto_trader_config.json 2>&1 | head -2

# In scalp-engine Shell  
echo "=== ENGINE DISK ==="; df -h /var/data/; echo ""; ls -lh /var/data/auto_trader_config.json 2>&1 | head -2
```

**Compare the outputs:**
- If mount info or file details are **DIFFERENT** → They're on different disks
- If mount info or file details are **SAME** → They're on same disk (but file might not exist or not be synced)

## If Services Are on Different Disks

### Fix: Attach `scalp-engine` to `scalp-engine-ui`'s Disk

1. **Identify the disk that `scalp-engine-ui` uses:**
   - From the Disks section, note the disk name/ID
   - OR remember: it's the one that has the correct `auto_trader_config.json` (AUTO/AI_TRAILING)

2. **Attach `scalp-engine` to the same disk:**
   - Go to `scalp-engine` service → **Settings** → **Disk** tab
   - If it shows a different disk → **Detach** it
   - Click **"Attach Existing Disk"** (or similar button)
   - Select the **same disk** that `scalp-engine-ui` uses
   - Mount path: `/var/data`
   - Click **Save**

3. **Restart `scalp-engine`:**
   - Go to `scalp-engine` → **Manual Deploy** → **Deploy latest commit**

4. **Verify fix:**
   - Run the diagnostic script in both Shells
   - Both should now show **SAME file contents** (AUTO/AI_TRAILING)

## Quick Check Script

I've created `check_disk_identity.sh` that you can run in both Shells to compare disk identities.
