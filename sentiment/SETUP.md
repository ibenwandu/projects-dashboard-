# Setup Guide - Sentiment-Aware Forex Monitor

## Quick Start

### 1. Install Dependencies

```bash
cd personal/sentiment
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the `sentiment` folder:

```env
# Choose ONE LLM provider (uncomment the one you want to use)
OPENAI_API_KEY=your-openai-api-key
# OR
# ANTHROPIC_API_KEY=your-anthropic-api-key
# OR
# GOOGLE_API_KEY=your-google-api-key

# Email Configuration (required for alerts)
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your-gmail-app-password
EMAIL_RECIPIENT=your_email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Optional: News API (for additional news sources)
# NEWSAPI_KEY=your-newsapi-key
```

### 3. Configure Watchlist

Copy the example watchlist:

```bash
cp config/watchlist.yaml.example config/watchlist.yaml
```

Edit `config/watchlist.yaml` with your trades:

```yaml
watchlist:
  - asset: "USD/CAD"
    trade_direction: "short"  # short USD, long CAD
    bias_expectation: "Weak USD"
    sensitivity: "high"
    notes: "Watching BoC rate decision"
    
  - asset: "EUR/USD"
    trade_direction: "long"  # long EUR, short USD
    bias_expectation: "Strong EUR"
    sensitivity: "medium"
    notes: ""
```

### 4. Configure Settings

Copy the example settings:

```bash
cp config/settings.yaml.example config/settings.yaml
```

Edit `config/settings.yaml` to customize:
- Check interval (default: 15 minutes)
- LLM provider and model
- Confidence thresholds
- Price signal thresholds

### 5. Test Run

Run a single check to test:

```bash
python main.py --once
```

### 6. Run Continuously

Start the scheduler:

```bash
python main.py
```

This will run checks every 15 minutes (or as configured).

## Gmail App Password Setup

To send email alerts, you need a Gmail App Password:

1. Go to your Google Account settings
2. Security → 2-Step Verification (must be enabled)
3. App passwords → Generate app password
4. Copy the password and use it as `SENDER_PASSWORD` in `.env`

## LLM Provider Setup

### OpenAI

1. Get API key from: https://platform.openai.com/api-keys
2. Add to `.env`: `OPENAI_API_KEY=sk-...`
3. Set in `settings.yaml`: `llm_provider: "openai"`, `llm_model: "gpt-4o-mini"`

### Anthropic (Claude)

1. Get API key from: https://console.anthropic.com/
2. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
3. Set in `settings.yaml`: `llm_provider: "anthropic"`, `llm_model: "claude-3-5-sonnet-20240620"`

### Google Gemini

1. Get API key from: https://makersuite.google.com/app/apikey
2. Add to `.env`: `GOOGLE_API_KEY=...`
3. Set in `settings.yaml`: `llm_provider: "gemini"`, `llm_model: "gemini-1.5-pro"`

## Troubleshooting

### "LLM provider not initialized"
- Check that you have the required package installed
- Verify API key is set in `.env`
- Check that `llm_provider` in `settings.yaml` matches your setup

### "Email alerts disabled"
- Check `SENDER_EMAIL` and `SENDER_PASSWORD` in `.env`
- Verify Gmail App Password is correct
- Test SMTP connection

### "Watchlist is empty"
- Copy `watchlist.yaml.example` to `watchlist.yaml`
- Add your trades to `watchlist.yaml`

### "No price data"
- Check internet connection
- Frankfurter.app API might be down (temporary)

## Next Steps

1. ✅ Set up environment variables
2. ✅ Configure watchlist with your trades
3. ✅ Test with `python main.py --once`
4. ✅ Run continuously with `python main.py`
5. ✅ Monitor your email for alerts!






