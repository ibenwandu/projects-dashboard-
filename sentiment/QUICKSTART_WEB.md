# Quick Start - Web UI Version

## Step 1: Install Dependencies

```bash
cd personal/sentiment
pip install -r requirements.txt
```

## Step 2: Create .env File

```bash
cp .env.example .env
# Edit .env with your API keys and email settings
```

## Step 3: Run Web Server

```bash
python app.py
```

Access the UI at: http://localhost:5000

## Step 4: Add Trades via Web UI

1. Open http://localhost:5000 in your browser
2. Click "+ Add Trade"
3. Fill in:
   - Forex Pair (e.g., USD/CAD)
   - Trade Direction (Long/Short)
   - Bias Expectation (optional)
   - Sensitivity (High/Medium/Low)
   - Notes (optional)
4. Click "Save Trade"

## Step 5: Run Background Worker

In a separate terminal:

```bash
python worker.py
```

The worker will check your watchlist every 15 minutes and send alerts.

## Features

- **Web UI** - Manage watchlist without editing files
- **State Tracking** - See last alert time and sentiment per asset
- **Recent Alerts** - View alert history
- **Active Events** - Monitor high-impact events

## Deployment

See `DEPLOY.md` for instructions to deploy to Render.






