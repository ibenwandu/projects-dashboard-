# Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
cd personal/sentiment
pip install -r requirements.txt
```

## Step 2: Create .env File

Create `.env` in the `sentiment` folder:

```env
OPENAI_API_KEY=sk-your-key-here
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your-app-password
EMAIL_RECIPIENT=your_email@gmail.com
```

## Step 3: Set Up Config Files

```bash
# Copy example configs
cp config/watchlist.yaml.example config/watchlist.yaml
cp config/settings.yaml.example config/settings.yaml

# Edit watchlist.yaml with your trades
# Edit settings.yaml to customize (optional)
```

## Step 4: Test Run

```bash
python main.py --once
```

## Step 5: Run Continuously

```bash
python main.py
```

That's it! The system will check your watchlist every 15 minutes and send email alerts when sentiment shifts against your trades.

## Need Help?

See `SETUP.md` for detailed instructions, or `README.md` for full documentation.






