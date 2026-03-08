# API Setup Guide - Free vs Paid Accounts

## Current Status

From your logs:
- ✅ **ChatGPT**: Working (you have paid account)
- ❌ **Gemini**: 404 errors (all models failing)
- ❌ **Claude**: 404 errors (all models failing)

## Possible Causes

### 1. API Access Setup

**Gemini (Google):**
- Free tier available at: https://aistudio.google.com/
- You need to:
  1. Go to Google AI Studio
  2. Create an API key
  3. Add it to Render as `GOOGLE_API_KEY`
  4. Free tier has rate limits but should work

**Claude (Anthropic):**
- Free tier available at: https://console.anthropic.com/
- You need to:
  1. Sign up for Anthropic account
  2. Get API key from console
  3. Add it to Render as `ANTHROPIC_API_KEY`
  4. Free tier has limited credits

### 2. Model Name Issues

The 404 errors suggest model names might be wrong. Let's verify:

**Gemini Models:**
- `gemini-1.5-flash` - Should work on free tier
- `gemini-1.5-pro` - May require paid tier
- `gemini-pro` - Legacy model, may be deprecated

**Claude Models:**
- `claude-3-5-sonnet-20240620` - Should work
- `claude-3-sonnet-20240229` - Older model
- `claude-3-5-haiku` - Cheaper alternative

### 3. API Key Verification

Check in Render Dashboard → Environment:
- `GOOGLE_API_KEY` - Should start with `AIza...`
- `ANTHROPIC_API_KEY` - Should start with `sk-ant-...`

## Solutions

### Option 1: Set Up Free Accounts (Recommended)

**For Gemini:**
1. Go to https://aistudio.google.com/
2. Sign in with Google account
3. Click "Get API Key"
4. Create new key or use existing
5. Copy key to Render → Environment → `GOOGLE_API_KEY`

**For Claude:**
1. Go to https://console.anthropic.com/
2. Sign up for account
3. Go to API Keys section
4. Create new key
5. Copy key to Render → Environment → `ANTHROPIC_API_KEY`

### Option 2: Use Only ChatGPT (Simpler)

If you want to avoid setting up other accounts:
- System will work with just ChatGPT
- You'll get ChatGPT recommendations
- Gemini synthesis won't work (needs Gemini API)
- Entry points won't be extracted (needs Gemini synthesis)

### Option 3: Use Correct Model Names

The code now has fallback logic, but we can also:
- Try different model names
- Check API documentation for available models
- Use models that work on free tier

## Testing API Keys

To test if your API keys work:

**Test Gemini:**
```python
import google.generativeai as genai
genai.configure(api_key="YOUR_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Hello")
print(response.text)
```

**Test Claude:**
```python
from anthropic import Anthropic
client = Anthropic(api_key="YOUR_KEY")
message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hello"}]
)
print(message.content[0].text)
```

## Next Steps

1. **Verify API Keys:**
   - Check Render Dashboard → Environment
   - Ensure keys are set correctly
   - Keys should not have extra spaces or quotes

2. **Set Up Free Accounts:**
   - Gemini: https://aistudio.google.com/
   - Claude: https://console.anthropic.com/

3. **Test After Setup:**
   - Run `python run_analysis_now.py` in Render Shell
   - Check logs for success

4. **Alternative:**
   - If you prefer to use only ChatGPT, the system will work
   - You'll get ChatGPT recommendations via email
   - Entry point monitoring won't work (needs Gemini synthesis)

## Free Tier Limits

**Gemini:**
- Free tier: 15 requests per minute
- Should be enough for your 7 daily analyses

**Claude:**
- Free tier: Limited credits
- Check console for current quota

Both free tiers should work for your use case!







