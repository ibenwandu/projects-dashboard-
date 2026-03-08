# Monorepo Migration Guide - Safe Migration Without Breaking Fx-engine

## Overview

This guide shows you how to safely combine first-monitor and Fx-engine into a monorepo structure **without breaking** the currently working Fx-engine.

## Strategy: Zero-Downtime Migration

We'll use a **copy-first, test, then switch** approach:
1. Create monorepo structure (new location)
2. Copy both projects (preserve originals)
3. Test everything works
4. Update Render deployments
5. Keep originals as backup until confirmed working

---

## Step 1: Create Monorepo Structure (Safe - No Changes to Existing)

### Option A: New Directory (Safest)

```powershell
# Create new monorepo directory
cd C:\Users\user\projects\personal
mkdir trading-systems-monorepo
cd trading-systems-monorepo
git init

# Copy both projects (preserves originals)
xcopy ..\first-monitor first-monitor\ /E /I /H
xcopy ..\Fx-engine Fx-engine\ /E /I /H
```

### Option B: Use Existing Directory (If You Prefer)

If you want to use an existing directory, we can convert it, but Option A is safer.

---

## Step 2: Create Monorepo render.yaml

Create a `render.yaml` in the monorepo root that handles both projects:

```yaml
services:
  # First-Monitor Services
  - type: worker
    name: first-monitor-worker
    rootDir: first-monitor
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: python worker.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: ENV
        value: production
      - key: FRED_API_KEY
        sync: false
    disk:
      name: first-monitor-data
      mountPath: /var/data
      sizeGB: 1

  - type: web
    name: first-monitor-app
    rootDir: first-monitor
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.enableXsrfProtection false
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: ENV
        value: production
      - key: FRED_API_KEY
        sync: false
    healthCheckPath: /
    disk:
      name: first-monitor-data
      mountPath: /var/data
      sizeGB: 1

  # Fx-Engine Services (unchanged)
  - type: web
    name: fx-engine-app
    rootDir: Fx-engine
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.enableXsrfProtection false
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: DATABASE_PATH
        value: /var/data/fx_engine.db
      - key: ENV
        value: production
      - key: OPENAI_API_KEY
        sync: false
      - key: GOOGLE_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: OANDA_API_KEY
        sync: false
      - key: OANDA_ACCOUNT_ID
        sync: false
      - key: FRED_API_KEY
        sync: false
    disk:
      name: fx-data
      mountPath: /var/data
      sizeGB: 1
    healthCheckPath: /

  - type: worker
    name: fx-engine-worker
    rootDir: Fx-engine
    runtime: python
    plan: starter
    buildCommand: |
      pip install --upgrade pip setuptools wheel
      pip install -r requirements.txt
    startCommand: python worker.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.0
      - key: DATABASE_PATH
        value: /var/data/fx_engine.db
      - key: ENV
        value: production
      - key: OPENAI_API_KEY
        sync: false
      - key: GOOGLE_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: OANDA_API_KEY
        sync: false
      - key: OANDA_ACCOUNT_ID
        sync: false
      - key: FRED_API_KEY
        sync: false
    disk:
      name: fx-data
      mountPath: /var/data
      sizeGB: 1
```

---

## Step 3: Update first-monitor Integration (No Changes to Fx-engine)

The first-monitor integration code already handles sibling directories, so it should work automatically. But let's verify the path detection works with the monorepo structure.

**No changes needed** - the integration code already checks for sibling directories!

---

## Step 4: Test Locally (Before Deploying)

```powershell
# Test first-monitor
cd C:\Users\user\projects\personal\trading-systems-monorepo\first-monitor
python test_integration.py

# Should show:
# ✅ Base Engine: Successfully initialized
# ✅ RL Tracker: Successfully initialized
# ✅ Integration Status: Integrated (FP + Technical + ML)

# Test Fx-engine still works
cd ..\Fx-engine
python -c "from core.production_engine import ProductionEngine; print('✅ Fx-engine works')"
```

---

## Step 5: Create GitHub Repository

```powershell
cd C:\Users\user\projects\personal\trading-systems-monorepo

# Create .gitignore
@"
# Python
__pycache__/
*.py[cod]
*.so
.Python
env/
venv/
.venv

# Environment
.env
.env.local

# Databases
*.db
*.sqlite
*.sqlite3

# Data
data/
*.csv
*.json

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"@ | Out-File -FilePath .gitignore -Encoding utf8

# Initialize git
git init
git add .
git commit -m "Initial commit: Trading Systems Monorepo"

# Create repository on GitHub, then:
git remote add origin https://github.com/your-username/trading-systems-monorepo.git
git branch -M main
git push -u origin main
```

---

## Step 6: Deploy to Render (Update Existing Services)

### Option A: Update Existing Services (Recommended)

1. **In Render Dashboard**:
   - Go to each service (fx-engine-app, fx-engine-worker, first-monitor-app, first-monitor-worker)
   - Click **Settings** → **Build & Deploy**
   - Update **Repository**: Change to new monorepo repository
   - Update **Root Directory**:
     - Fx-engine services: `Fx-engine`
     - first-monitor services: `first-monitor`
   - Click **Save Changes**
   - Services will rebuild automatically

2. **Verify**:
   - Check logs for each service
   - Ensure they start correctly
   - Test both dashboards

### Option B: Use Blueprints (Clean Slate)

1. **In Render Dashboard**:
   - Click **"New +"** → **"Blueprints"**
   - Select your monorepo repository
   - Render will detect `render.yaml`
   - Click **"Apply"**
   - Set environment variables for each service
   - Services will be created automatically

2. **After Blueprint Deployment**:
   - Delete old services (if you want)
   - Or keep them as backup until new ones are confirmed working

---

## Step 7: Verify Integration Works

1. **Check first-monitor Dashboard**:
   - Should show: "Mode: Integrated (FP + Technical + ML)"
   - Technical Engine: Active ✅
   - ML Tracker: Active ✅

2. **Check Fx-engine Dashboard**:
   - Should work exactly as before
   - No changes to functionality

3. **Test Integration**:
   - Run a signal calculation in first-monitor
   - Should use technical analysis from Fx-engine
   - Should use ML predictions from SignalTracker

---

## Safety Measures

### Backup Strategy

1. **Keep Original Repositories**:
   - Don't delete original `first-monitor` and `Fx-engine` directories
   - Keep them as backup until monorepo is confirmed working

2. **Keep Original Render Services**:
   - Don't delete old services immediately
   - Run both old and new in parallel for a few days
   - Compare outputs to ensure everything works

3. **Git Tags**:
   - Tag the last working version before migration
   - Easy to rollback if needed

### Rollback Plan

If something breaks:

1. **Revert Render Services**:
   - Change repository back to original
   - Remove `rootDir` setting
   - Services will use original configuration

2. **Or Use Original Services**:
   - Original services are still running
   - Just switch back to using them

---

## Directory Structure After Migration

```
trading-systems-monorepo/
├── first-monitor/
│   ├── app.py
│   ├── worker.py
│   ├── core/
│   │   ├── fx_engine_integration.py  # Finds ../Fx-engine automatically
│   │   └── ...
│   ├── render.yaml  # Can be removed (using root render.yaml)
│   └── requirements.txt
│
├── Fx-engine/
│   ├── app.py
│   ├── worker.py
│   ├── core/
│   │   ├── production_engine.py
│   │   ├── rl_tracker.py
│   │   └── ...
│   ├── render.yaml  # Can be removed (using root render.yaml)
│   └── requirements.txt
│
├── render.yaml  # Master config for all services
├── README.md
└── .gitignore
```

---

## Key Points

✅ **Fx-engine Unchanged**: No code changes to Fx-engine
✅ **first-monitor Unchanged**: Integration code already handles sibling directories
✅ **Zero Downtime**: Original services keep running during migration
✅ **Easy Rollback**: Can revert to original setup anytime
✅ **Independent Testing**: Test each project separately before deploying

---

## Step-by-Step Checklist

- [ ] Create monorepo directory
- [ ] Copy both projects (preserve originals)
- [ ] Create root render.yaml
- [ ] Test first-monitor integration locally
- [ ] Test Fx-engine still works locally
- [ ] Create GitHub repository
- [ ] Push to GitHub
- [ ] Update Render services (or create new via Blueprints)
- [ ] Verify all services start correctly
- [ ] Test integration in first-monitor dashboard
- [ ] Verify Fx-engine dashboard works
- [ ] Monitor for 24-48 hours
- [ ] Delete old services (if using new ones)
- [ ] Archive original directories (optional)

---

## Troubleshooting

### Issue: Fx-engine not found in monorepo

**Solution**: Check path detection:
```python
# In first-monitor, run:
python test_integration.py

# Should show Fx-engine path as: .../trading-systems-monorepo/Fx-engine
```

### Issue: Render services fail to start

**Solution**: 
1. Check `rootDir` is set correctly in render.yaml
2. Check build logs for errors
3. Verify environment variables are set

### Issue: Import errors

**Solution**: 
1. Check that both projects' `core/` directories exist
2. Verify Python path includes both directories
3. Check debug information in first-monitor dashboard

---

**Last Updated**: 2025-01-06

