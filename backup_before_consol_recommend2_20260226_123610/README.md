# Trade-Alerts - AI-Powered Forex Trading Recommendations

Automated forex trading recommendation system that uses multiple AI models (ChatGPT, Gemini, Claude) to analyze market data and provides intelligent trading recommendations with reinforcement learning capabilities.

## 🚀 Features

- 🤖 **Multi-LLM Analysis**: Uses ChatGPT, Gemini, and Claude for independent analysis
- 📊 **Google Drive Integration**: Reads analysis files from "Forex tracker" folder
- 📧 **Email Notifications**: Sends comprehensive recommendations via email
- 🔔 **Pushover Alerts**: Real-time alerts when entry points are hit
- 🧠 **Reinforcement Learning**: Learns from historical performance to improve recommendations
- ⏰ **Scheduled Analysis**: Runs analysis at multiple times per day
- 💹 **Price Monitoring**: Continuous monitoring of entry points
- 📈 **Performance Tracking**: Tracks LLM accuracy and adjusts weights automatically

## 📖 Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user guide with setup instructions, configuration, and usage
- **[TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)** - Technical documentation for developers
- **[RL_SETUP_GUIDE.md](RL_SETUP_GUIDE.md)** - Reinforcement learning system setup
- **[RL_DEPLOYMENT_GUIDE.md](RL_DEPLOYMENT_GUIDE.md)** - Deployment guide for Render

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with required API keys and credentials. See [USER_GUIDE.md](USER_GUIDE.md#configuration) for detailed instructions.

**Required Variables**:
- `GOOGLE_DRIVE_FOLDER_ID` - Your Google Drive folder ID
- `GOOGLE_DRIVE_CREDENTIALS_JSON` - OAuth credentials
- `GOOGLE_DRIVE_REFRESH_TOKEN` - Refresh token
- `OPENAI_API_KEY` - ChatGPT API key
- `GOOGLE_API_KEY` - Gemini API key
- `ANTHROPIC_API_KEY` - Claude API key
- `SENDER_EMAIL`, `SENDER_PASSWORD` - Email credentials
- `PUSHOVER_API_TOKEN`, `PUSHOVER_USER_KEY` - Pushover credentials

### 3. Run Historical Backfill (One Time)

```bash
python historical_backfill.py
```

This processes all historical files and calculates initial LLM weights.

### 4. Run the System

```bash
python main.py
```

## How It Works

1. **Scheduled Analysis** (Multiple times per day)
   - Downloads latest analysis files from Google Drive
   - Analyzes data using ChatGPT, Gemini, and Claude
   - Synthesizes recommendations using Gemini
   - Enhances with RL insights
   - Sends comprehensive email

2. **Continuous Monitoring** (Every 60 seconds)
   - Checks current prices for all active opportunities
   - Sends Pushover alerts when entry points are hit

3. **Daily Learning** (11:00 PM UTC)
   - Evaluates outcomes of recent recommendations
   - Updates LLM performance weights
   - Improves future recommendations

## Project Structure

```
Trade-Alerts/
├── main.py                          # Main application
├── historical_backfill.py           # One-time historical processing
├── requirements.txt                 # Dependencies
├── Procfile                         # Render deployment config
│
├── src/
│   ├── drive_reader.py              # Google Drive integration
│   ├── llm_analyzer.py             # LLM API integration
│   ├── gemini_synthesizer.py       # Recommendation synthesis
│   ├── email_sender.py             # Email notifications
│   ├── price_monitor.py            # Price monitoring
│   ├── alert_manager.py             # Pushover alerts
│   ├── scheduler.py                # Analysis scheduling
│   ├── trade_alerts_rl.py          # RL system (database, parser, evaluator, engine)
│   └── daily_learning.py           # Daily learning job
│
├── data/
│   └── recommendations/             # Saved recommendation files
│
├── logs/                            # Application logs
├── trade_alerts_rl.db              # RL database
│
└── docs/
    ├── USER_GUIDE.md                # User documentation
    ├── TECHNICAL_DOCUMENTATION.md  # Technical docs
    └── ...
```

## Key Components

### Multi-LLM Analysis
- **ChatGPT**: Fast, reliable analysis
- **Gemini**: Deep market understanding
- **Claude**: Nuanced reasoning

### Reinforcement Learning
- Tracks recommendation outcomes
- Calculates LLM performance weights
- Updates daily based on actual results
- Enhances recommendations with insights

### Monitoring & Alerts
- Continuous price monitoring
- Pushover alerts for entry points
- One-time alerts (no spam)
- Comprehensive logging

## Configuration

See [USER_GUIDE.md](USER_GUIDE.md#configuration) for complete configuration guide.

**Key Settings**:
- `ANALYSIS_TIMES`: Scheduled analysis times (default: 2am, 4am, 7am, 9am, 11am, 12pm, 4pm EST)
- `CHECK_INTERVAL`: Price check interval in seconds (default: 60)
- `ANALYSIS_TIMEZONE`: Timezone for scheduled times (default: America/New_York)

## Deployment

See [RL_DEPLOYMENT_GUIDE.md](RL_DEPLOYMENT_GUIDE.md) for Render deployment instructions.

## Support

- Check logs in `logs/` directory
- Review [USER_GUIDE.md](USER_GUIDE.md#troubleshooting) troubleshooting section
- See [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md) for technical details

## License

See LICENSE file for details.

---

**Version**: 2.0 (with RL System)  
**Last Updated**: 2025-01-05

