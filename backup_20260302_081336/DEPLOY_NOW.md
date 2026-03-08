# Quick Deploy Guide - Trade Alerts

## 🚀 Deploy to Render in 3 Steps

### Step 1: Commit Changes
```powershell
cd C:\Users\user\projects\personal\Trade-Alerts
git add .
git commit -m "Update EST timezone, custom LLM prompts, enhanced email format, and 7 daily analysis times"
```

### Step 2: Push to GitHub
```powershell
git push origin main
```

### Step 3: Monitor Deployment
1. Go to **Render Dashboard**: https://dashboard.render.com
2. Click on **trade-alerts** service
3. Watch the **Events** tab for deployment progress
4. Check **Logs** tab once deployed

---

## ✅ What Will Deploy

- ✅ EST timezone configuration (7 analysis times per day)
- ✅ Custom LLM prompts (dual source analysis)
- ✅ Enhanced email format (shows missing recommendations)
- ✅ Better logging (detailed LLM success/failure)
- ✅ Model updates (gpt-4o-mini, gemini-pro, claude-3-5-sonnet-20240229)
- ✅ Frankfurter.app price API (free, no API key)

---

## 📅 Analysis Schedule (EST)

After deployment, analysis will run at:
- 2:00 AM EST
- 4:00 AM EST
- 7:00 AM EST
- 9:00 AM EST
- 11:00 AM EST
- 12:00 PM EST (noon)
- 4:00 PM EST

---

## 🧪 Test After Deployment

1. **Check Logs:**
   - Render Dashboard → trade-alerts → Logs
   - Should see: "✅ Trade Alert System initialized"
   - Should see: "Next scheduled analysis: [time] EST"

2. **Test Analysis (Optional):**
   - Render Dashboard → trade-alerts → Shell
   - Run: `python run_analysis_now.py`
   - Check email for recommendations

3. **Verify Email:**
   - Should receive email with all LLM recommendations
   - Email will show which LLMs succeeded/failed

---

## ⚠️ Troubleshooting

### Deployment Fails
- Check Render logs for errors
- Verify all environment variables are set
- Check `requirements.txt` is complete

### Missing LLM Recommendations
- Check Render logs for API errors
- Verify API keys are valid
- Check API quotas/credits

### Email Not Received
- Verify `SENDER_EMAIL` and `SENDER_PASSWORD` are set
- Check Gmail app password is correct
- Check spam folder

---

## 📊 After Deployment

The system will automatically:
- ✅ Run analysis at scheduled EST times
- ✅ Send emails with recommendations
- ✅ Monitor entry points continuously
- ✅ Send Pushover alerts when entry points hit

No further action needed - it runs 24/7!







