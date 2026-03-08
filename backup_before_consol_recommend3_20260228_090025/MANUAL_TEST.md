# How to Manually Test the Trade-Alerts System

## Quick Test Methods

### Method 1: Using the Test Script (Easiest!)

1. **Go to Render Shell:**
   - Render Dashboard → `trade-alerts` → **Shell**

2. **Navigate to project:**
   ```bash
   cd ~/project
   ```

3. **Run the test script:**
   ```bash
   python test_analysis.py
   ```

This will:
- Initialize the system
- Run a full analysis cycle
- Get recommendations from all 3 LLMs
- Synthesize final recommendations
- Send email with all results
- Extract entry/exit points

---

### Method 2: Python Interactive Mode

1. **Go to Render Shell:**
   - Render Dashboard → `trade-alerts` → **Shell**

2. **Navigate to project:**
   ```bash
   cd ~/project
   ```

3. **Start Python:**
   ```bash
   python
   ```

4. **Run these commands:**
   ```python
   from main import TradeAlertSystem
   system = TradeAlertSystem()
   system._run_full_analysis()
   ```

5. **Exit Python:**
   ```python
   exit()
   ```

---

### Method 3: Import in Python Script

1. **Go to Render Shell:**
   - Render Dashboard → `trade-alerts` → **Shell**

2. **Navigate to project:**
   ```bash
   cd ~/project
   ```

3. **Create a test file:**
   ```bash
   nano test_now.py
   ```

4. **Add this code:**
   ```python
   from main import TradeAlertSystem
   system = TradeAlertSystem()
   system._run_full_analysis()
   ```

5. **Run it:**
   ```bash
   python test_now.py
   ```

---

## What Happens During Test

1. **Reads Data:**
   - Downloads files from Google Drive "Forex tracker" folder
   - Formats data for LLM analysis

2. **LLM Analysis:**
   - ChatGPT analysis
   - Gemini analysis
   - Claude analysis

3. **Synthesis:**
   - Gemini synthesizes all recommendations
   - Creates final unified recommendations

4. **Email:**
   - Sends email with all recommendations
   - Includes entry/exit points

5. **Extraction:**
   - Extracts trading opportunities
   - Sets up price monitoring

---

## Expected Output

You should see:
- ✅ Initialization messages
- ✅ "Step 1: Reading data from Google Drive..."
- ✅ "Step 2: Formatting data..."
- ✅ "Step 3: Running LLM analysis..."
- ✅ "Step 4: Synthesizing final recommendations..."
- ✅ "Step 5: Sending email..."
- ✅ "Step 6: Extracting entry/exit points..."
- ✅ "Full analysis workflow completed"

---

## Troubleshooting

### If you see errors:

1. **Check logs:**
   - Look for specific error messages
   - Check which step failed

2. **Verify API keys:**
   - Render Dashboard → Environment
   - Ensure all API keys are set

3. **Check Google Drive:**
   - Verify folder ID is correct
   - Ensure files are in the folder

4. **Verify email settings:**
   - Check SMTP credentials
   - Verify recipient email

---

## Notes

- Manual tests don't affect scheduled analyses
- Scheduled analyses will still run at their set times
- Each test triggers a full analysis cycle
- You'll receive an email for each test run







