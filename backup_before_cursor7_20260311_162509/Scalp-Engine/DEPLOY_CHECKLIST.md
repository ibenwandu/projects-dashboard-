# Scalp-Engine Deployment Checklist

Use this checklist to ensure a smooth deployment to GitHub and Render.

## Pre-Deployment

- [ ] Scalp-Engine tested locally and working
- [ ] All components tested (`python test_components.py` passes)
- [ ] OANDA credentials verified and working
- [ ] `.env` file has correct OANDA credentials
- [ ] `.gitignore` includes `.env` and sensitive files
- [ ] `requirements.txt` is up to date
- [ ] `render.yaml` is configured correctly
- [ ] `config.yaml` has appropriate settings for production

## GitHub Deployment

- [ ] Git repository initialized
- [ ] All files committed (`git status` shows clean)
- [ ] GitHub repository created
- [ ] Remote origin added
- [ ] Code pushed to GitHub (`git push origin main`)
- [ ] Verified code is on GitHub (check repository)

## Render Deployment

- [ ] Render account created/accessed
- [ ] GitHub account connected to Render
- [ ] Repository selected in Render
- [ ] Service created (Worker type)
- [ ] Environment variables configured:
  - [ ] `OANDA_ACCESS_TOKEN`
  - [ ] `OANDA_ACCOUNT_ID`
  - [ ] `OANDA_ENV` (practice or live)
  - [ ] `PYTHON_VERSION` (3.10.0)
  - [ ] `ENV` (production)
- [ ] Persistent disk configured (if needed)
- [ ] Service deployed successfully
- [ ] Build completed without errors
- [ ] Service status is "Live"

## Post-Deployment Verification

- [ ] Logs show "Scalp-Engine Started"
- [ ] OANDA connection successful (check logs)
- [ ] Market state file path is accessible
- [ ] No error messages in logs
- [ ] Service is running continuously (check uptime)

## Integration with Trade-Alerts

- [ ] Trade-Alerts is deployed (or will be)
- [ ] Market state file location is configured correctly
- [ ] Scalp-Engine can read market state (or will wait for it)
- [ ] Integration path is clear (monorepo, shared disk, or API)

## Testing

- [ ] Service starts without errors
- [ ] OANDA connection works
- [ ] Market state reading works (or waits correctly)
- [ ] No crashes or restarts
- [ ] Logs are clear and informative

## Security

- [ ] `.env` file is in `.gitignore`
- [ ] No credentials in code
- [ ] All secrets in Render environment variables
- [ ] OANDA credentials are secure
- [ ] Using practice account for initial testing

## Monitoring Setup

- [ ] Render logs are accessible
- [ ] Know how to check service status
- [ ] Understand how to view logs
- [ ] Know how to restart service if needed
- [ ] Have plan for monitoring trading activity

## Documentation

- [ ] Deployment guide reviewed
- [ ] Troubleshooting guide available
- [ ] README updated (if needed)
- [ ] Configuration documented

## Final Checks

- [ ] Service is running 24/7
- [ ] No unexpected errors
- [ ] Ready for production use (or testing)
- [ ] Team/self knows how to monitor and maintain

---

## Quick Deploy Commands

```powershell
# 1. Commit and push to GitHub
cd C:\Users\user\projects\personal\Scalp-Engine
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. Deploy on Render
# - Go to Render Dashboard
# - Create new service from repository
# - Configure environment variables
# - Deploy

# 3. Verify
# - Check Render logs
# - Verify service is "Live"
# - Check for any errors
```

---

**Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

