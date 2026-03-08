# Deploy to Hugging Face Spaces

## Step 1: Create Hugging Face Account

1. Go to https://huggingface.co
2. Sign up for a free account
3. Verify your email

## Step 2: Create a New Space

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Configure:
   - **Space name:** `sentiment-forex-monitor` (or your choice)
   - **SDK:** `Gradio`
   - **Hardware:** `CPU basic` (free tier)
   - **Visibility:** `Public` or `Private`

## Step 3: Upload Files

You can either:

### Option A: Upload via Web UI
1. In your Space, go to "Files and versions"
2. Upload these files:
   - `app_gradio.py` (rename to `app.py` in the Space)
   - `requirements_hf.txt` (rename to `requirements.txt`)
   - `README_HF.md` (rename to `README.md`)
   - `src/` folder (all Python files)
   - `config/` folder (settings.yaml.example)

### Option B: Use Git (Recommended)
1. Initialize git in your sentiment folder:
   ```bash
   cd personal/sentiment
   git init
   git add app_gradio.py requirements_hf.txt README_HF.md src/ config/
   git commit -m "Initial commit"
   ```

2. Add Hugging Face remote:
   ```bash
   git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
   git push origin main
   ```

## Step 4: Configure Environment Variables

1. In your Space, go to "Settings"
2. Scroll to "Repository secrets"
3. Add these secrets:
   - `OPENAI_API_KEY` = your OpenAI API key
   - `SENDER_EMAIL` = your email
   - `SENDER_PASSWORD` = your Gmail app password
   - `EMAIL_RECIPIENT` = recipient email
   - `SECRET_KEY` = random secret key

## Step 5: Deploy

1. The Space will automatically build and deploy
2. Wait for the build to complete (usually 2-5 minutes)
3. Your app will be live at: `https://YOUR_USERNAME-YOUR_SPACE_NAME.hf.space`

## Step 6: Run Background Worker (Separate)

The Gradio app is for the UI. For 24/7 monitoring, you still need the worker:

1. Deploy `worker.py` to Render (see `DEPLOY.md`)
2. Or run it on another service that supports background workers

## File Structure for HF Space

```
your-space/
├── app.py              # app_gradio.py renamed
├── requirements.txt    # requirements_hf.txt renamed
├── README.md          # README_HF.md renamed
├── src/
│   ├── database.py
│   ├── data/
│   ├── analysis/
│   ├── alerts/
│   └── monitor.py
└── config/
    └── settings.yaml.example
```

## Notes

- Hugging Face Spaces free tier has limitations (sleeps after inactivity)
- For 24/7 operation, consider upgrading or using Render for the worker
- The database file will persist in the Space's storage
- Environment variables are secure and not visible in the UI

## Troubleshooting

- **Build fails:** Check that all files are uploaded correctly
- **App crashes:** Check logs in the Space's "Logs" tab
- **Database errors:** The database will be created automatically on first run
- **Environment variables not working:** Make sure they're set in "Repository secrets", not "Variables"






