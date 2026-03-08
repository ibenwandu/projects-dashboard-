# Free API Setup Guide - Gemini & Claude

## ✅ You DON'T Need Paid Accounts!

Both Gemini and Claude offer **FREE tiers** that work for your use case.

## 🔍 Why You're Getting 404 Errors

The 404 errors are likely because:
1. **API keys not set up** in Render
2. **API keys invalid** or expired
3. **API keys not activated** (need to create them first)

**NOT because you need paid accounts!**

---

## 📋 Step-by-Step Setup

### Step 1: Set Up Gemini (FREE)

1. **Go to Google AI Studio:**
   - Visit: https://aistudio.google.com/
   - Sign in with your Google account

2. **Get API Key:**
   - Click "Get API Key" button
   - Select "Create API key in new project" or use existing project
   - Copy the API key (starts with `AIza...`)

3. **Add to Render:**
   - Go to Render Dashboard → `trade-alerts` → Environment
   - Add/Update: `GOOGLE_API_KEY`
   - Paste your API key (no quotes)
   - Click "Save Changes"

4. **Verify:**
   - Key should start with `AIza`
   - No spaces or quotes around it

### Step 2: Set Up Claude (FREE)

1. **Go to Anthropic Console:**
   - Visit: https://console.anthropic.com/
   - Sign up for account (free)

2. **Get API Key:**
   - Go to "API Keys" section
   - Click "Create Key"
   - Give it a name (e.g., "Trade Alerts")
   - Copy the API key (starts with `sk-ant-...`)

3. **Add to Render:**
   - Go to Render Dashboard → `trade-alerts` → Environment
   - Add/Update: `ANTHROPIC_API_KEY`
   - Paste your API key (no quotes)
   - Click "Save Changes"

4. **Verify:**
   - Key should start with `sk-ant-`
   - No spaces or quotes around it

### Step 3: Verify in Render

1. **Check Environment Variables:**
   - Render Dashboard → `trade-alerts` → Environment
   - Verify both keys are set:
     - `GOOGLE_API_KEY` = `AIza...`
     - `ANTHROPIC_API_KEY` = `sk-ant-...`

2. **Test:**
   - Go to Render Shell
   - Run: `python run_analysis_now.py`
   - Check logs - should see:
     - `✅ Gemini enabled`
     - `✅ Claude enabled`
     - `✅ Gemini analysis completed`
     - `✅ Claude analysis completed`

---

## 💰 Free Tier Limits

### Gemini (Google):
- **Free tier:** 15 requests per minute
- **Your usage:** 7 analyses per day = well within limits
- **Cost:** FREE

### Claude (Anthropic):
- **Free tier:** Limited credits (check console)
- **Your usage:** 7 analyses per day = should be fine
- **Cost:** FREE (with limited credits)

Both free tiers should work for your 7 daily analyses!

---

## ⚠️ Common Issues

### Issue 1: "404 Model Not Found"
**Cause:** API key not set or invalid
**Fix:** 
- Verify key is in Render Environment
- Check key format (no quotes, no spaces)
- Regenerate key if needed

### Issue 2: "Authentication Failed"
**Cause:** Invalid API key
**Fix:**
- Check key is correct (copy-paste carefully)
- Verify key hasn't expired
- Regenerate new key

### Issue 3: "Rate Limit Exceeded"
**Cause:** Too many requests
**Fix:**
- Wait a few minutes
- Free tier has limits but should be fine for 7/day

---

## 🧪 Test Your API Keys

### Test Gemini:
```python
import google.generativeai as genai
genai.configure(api_key="YOUR_GOOGLE_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Hello")
print(response.text)
```

### Test Claude:
```python
from anthropic import Anthropic
client = Anthropic(api_key="YOUR_ANTHROPIC_API_KEY")
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hello"}]
)
print(message.content[0].text)
```

---

## ✅ After Setup

1. **Keys are set in Render** ✅
2. **Test analysis:** `python run_analysis_now.py`
3. **Check logs:** Should see all 3 LLMs working
4. **Check email:** Should receive all recommendations

---

## 📞 Need Help?

If keys are set correctly but still getting errors:
1. Check API key format (no quotes/spaces)
2. Verify keys are active in their respective consoles
3. Check for rate limits or quota issues
4. Try regenerating keys

**Remember:** Free accounts work! The issue is likely API key setup, not account type.







