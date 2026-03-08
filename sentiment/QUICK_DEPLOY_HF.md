# Quick Deploy to Hugging Face Spaces

## Fastest Method (5 minutes)

1. **Create Space:**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: `sentiment-forex-monitor`
   - SDK: `Gradio`
   - Click "Create Space"

2. **Upload Files:**
   - In your Space, click "Files and versions" tab
   - Click "Add file" → "Upload files"
   - Upload:
     - `app_gradio.py` → rename to `app.py`
     - `requirements_hf.txt` → rename to `requirements.txt`
     - `README_HF.md` → rename to `README.md`
     - Upload entire `src/` folder
     - Upload `config/` folder

3. **Set Environment Variables:**
   - Go to "Settings" → "Repository secrets"
   - Add:
     - `OPENAI_API_KEY`
     - `SENDER_EMAIL`
     - `SENDER_PASSWORD`
     - `EMAIL_RECIPIENT`

4. **Wait for Build:**
   - Space will auto-build (2-5 minutes)
   - Check "Logs" tab for progress

5. **Access Your App:**
   - Your app URL: `https://YOUR_USERNAME-sentiment-forex-monitor.hf.space`
   - Accessible 24/7 (free tier may sleep after inactivity)

## Alternative: Use Git

```bash
cd personal/sentiment
git init
git add app_gradio.py requirements_hf.txt README_HF.md src/ config/
git commit -m "Deploy to HF Spaces"
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git push origin main
```

## Notes

- **Free tier:** May sleep after 1 hour of inactivity
- **Upgrade:** For always-on, upgrade to paid tier
- **Worker:** Still deploy `worker.py` to Render for 24/7 monitoring






