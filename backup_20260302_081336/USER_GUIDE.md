# Trade-Alerts User Guide

## 📖 Table of Contents

1. [Overview](#overview)
2. [What Trade-Alerts Does](#what-trade-alerts-does)
3. [Getting Started](#getting-started)
4. [Configuration](#configuration)
5. [How It Works](#how-it-works)
6. [Features](#features)
7. [Understanding Recommendations](#understanding-recommendations)
8. [Monitoring & Alerts](#monitoring--alerts)
9. [Reinforcement Learning System](#reinforcement-learning-system)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Overview

**Trade-Alerts** is an automated forex trading recommendation system that:

- 📊 Reads market analysis from your Google Drive "Forex tracker" folder
- 🤖 Analyzes data using multiple AI models (ChatGPT, Gemini, Claude)
- 📧 Sends comprehensive trading recommendations via email
- 🔔 Monitors entry points and sends Pushover alerts when prices hit targets
- 🧠 Learns from historical performance to improve recommendation quality

The system runs 24/7, automatically analyzing market data at scheduled times and continuously monitoring for entry opportunities.

---

## What Trade-Alerts Does

### Daily Workflow

1. **Scheduled Analysis** (Multiple times per day)
   - Downloads latest analysis files from Google Drive
   - Formats data for AI analysis
   - Sends data to ChatGPT, Gemini, and Claude for independent analysis
   - Synthesizes recommendations using Gemini
   - Enhances with machine learning insights
   - Sends comprehensive email with all recommendations
   - Logs recommendations for future learning

2. **Continuous Monitoring** (Every 60 seconds)
   - Checks current market prices for all active opportunities
   - Compares prices to entry points
   - Sends Pushover alerts when entry points are hit
   - Prevents duplicate alerts

3. **Daily Learning** (11:00 PM UTC)
   - Evaluates outcomes of recommendations from last 24 hours
   - Updates LLM performance weights based on accuracy
   - Saves learning checkpoints
   - Improves future recommendations

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Google Drive folder with analysis files
- API keys for:
  - OpenAI (ChatGPT)
  - Google (Gemini)
  - Anthropic (Claude)
- Email account (Gmail recommended)
- Pushover account (for alerts)

### Installation

1. **Clone or download the repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (see [Configuration](#configuration))

4. **Run the system:**
   ```bash
   python main.py
   ```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

#### Required Variables

```bash
# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
GOOGLE_DRIVE_CREDENTIALS_JSON={"installed":{"client_id":"...","client_secret":"..."}}
GOOGLE_DRIVE_REFRESH_TOKEN=your-refresh-token-here

# LLM API Keys
OPENAI_API_KEY=your-openai-key
GOOGLE_API_KEY=your-google-key
ANTHROPIC_API_KEY=your-anthropic-key

# Email Configuration
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Pushover (for entry point alerts)
PUSHOVER_API_TOKEN=your-pushover-token
PUSHOVER_USER_KEY=your-pushover-user-key
```

#### Optional Variables

```bash
# Analysis Schedule (comma-separated times in EST/EDT)
ANALYSIS_TIMES=02:00,04:00,07:00,09:00,11:00,12:00,16:00
ANALYSIS_TIMEZONE=America/New_York

# Price Monitoring
CHECK_INTERVAL=60  # seconds between price checks
PRICE_API_URL=https://api.frankfurter.app/latest  # Free forex API

# LLM Models (optional, defaults provided)
OPENAI_MODEL=gpt-4o-mini
GEMINI_MODEL=gemini-1.5-flash
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

### Getting API Keys

#### OpenAI (ChatGPT)
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add credits to your account

#### Google (Gemini)
1. Go to https://aistudio.google.com/app/apikey
2. Create a new API key
3. Enable billing if required

#### Anthropic (Claude)
1. Go to https://console.anthropic.com/
2. Create an API key
3. Add credits to your account

#### Google Drive Setup
1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create OAuth 2.0 credentials
4. Download credentials JSON
5. Generate refresh token (see `GET_CREDENTIALS_FROM_RENDER.md`)

#### Email Setup (Gmail)
1. Enable 2-factor authentication
2. Generate an "App Password" (not your regular password)
3. Use the app password in `SENDER_PASSWORD`

#### Pushover Setup
1. Sign up at https://pushover.net/
2. Create an application to get API token
3. Get your user key from the dashboard

---

## How It Works

### Step-by-Step Process

#### 1. Data Collection
- System connects to Google Drive
- Downloads latest analysis files from "Forex tracker" folder
- Looks for files with "summary" or "report" in the name
- Downloads up to 3 most recent files

#### 2. Data Formatting
- Extracts relevant information from files
- Formats data for LLM consumption
- Includes current date/time context

#### 3. LLM Analysis
- **ChatGPT**: Analyzes data and provides recommendations
- **Gemini**: Analyzes data and provides recommendations
- **Claude**: Analyzes data and provides recommendations
- Each LLM works independently

#### 4. Synthesis
- Gemini synthesizes all three LLM recommendations
- Creates a unified final recommendation
- Resolves conflicts and highlights consensus

#### 5. RL Enhancement
- System loads learned weights from database
- Adds performance insights based on historical data
- Shows which LLM has been most accurate
- Provides consensus analysis

#### 6. Email Delivery
- Formats all recommendations into email
- Includes:
  - Individual LLM recommendations
  - Final synthesis
  - Machine learning insights
  - Performance weights
- Sends to configured recipient

#### 7. Recommendation Logging
- Saves recommendations to database
- Stores in both `.txt` and `.json` formats
- Links to source files
- Ready for outcome evaluation

#### 8. Entry Point Extraction
- Parses recommendations for trading opportunities
- Extracts:
  - Currency pairs
  - Entry prices
  - Stop loss levels
  - Take profit levels
  - Position sizing

#### 9. Continuous Monitoring
- Checks prices every 60 seconds (configurable)
- Compares current price to entry points
- Sends Pushover alert when entry point is hit
- Prevents duplicate alerts

---

## Features

### Multi-LLM Analysis

The system uses three independent AI models to analyze market data:

- **ChatGPT (OpenAI)**: Fast, reliable analysis
- **Gemini (Google)**: Deep market understanding
- **Claude (Anthropic)**: Nuanced reasoning

Each LLM provides independent recommendations, allowing you to:
- Compare different perspectives
- Identify consensus opportunities
- Spot disagreements that may indicate uncertainty

### Synthesis Engine

Gemini synthesizes all three recommendations into a unified view:
- Highlights where all LLMs agree (high confidence)
- Notes disagreements (lower confidence)
- Provides balanced final recommendations

### Reinforcement Learning

The system learns from historical performance:

- **Tracks Outcomes**: Evaluates if recommendations hit TP/SL
- **Calculates Weights**: Determines which LLM is most accurate
- **Updates Daily**: Recalculates weights at 11pm UTC
- **Enhances Recommendations**: Shows performance insights in emails

### Scheduled Analysis

Runs analysis at multiple times per day:
- Default: 2am, 4am, 7am, 9am, 11am, 12pm, 4pm EST
- Customizable via `ANALYSIS_TIMES` environment variable
- Automatically adjusts for timezone changes (EST/EDT)

### Entry Point Monitoring

- Monitors all active opportunities continuously
- Checks prices every 60 seconds
- Sends instant Pushover alerts when entry points are hit
- Prevents duplicate alerts for same entry point

### Email Notifications

Comprehensive email includes:
- All three LLM recommendations
- Final synthesis
- Machine learning insights
- Performance weights
- Consensus analysis

---

## Understanding Recommendations

### Recommendation Format

Each recommendation includes:

```
Currency Pair: EUR/USD
Direction: LONG (Buy) or SHORT (Sell)
Entry Price: 1.0850
Stop Loss: 1.0800
Take Profit 1: 1.0900
Take Profit 2: 1.0950
Position Size: 2% of account
Confidence: High/Medium/Low
Rationale: Explanation of the trade
```

### LLM Weights

The system shows performance weights for each LLM:

- **Higher weight** = More accurate historically
- **Lower weight** = Less accurate historically
- Weights update daily based on actual outcomes

Example:
```
ChatGPT: 35% (Win Rate: 60%, Avg P&L: +15 pips)
Gemini: 30% (Win Rate: 55%, Avg P&L: +12 pips)
Claude: 25% (Win Rate: 50%, Avg P&L: +10 pips)
Synthesis: 10% (Win Rate: 65%, Avg P&L: +18 pips)
```

### Consensus Analysis

The system analyzes performance by consensus level:

- **ALL_AGREE**: All 3 LLMs agree → Highest win rate
- **2_AGREE**: 2 LLMs agree → Medium win rate
- **ALL_DISAGREE**: All 3 LLMs disagree → Lower win rate

Use this to:
- Increase position size when all agree
- Reduce position size when they disagree
- Skip trades when all disagree (optional)

---

## Monitoring & Alerts

### Pushover Alerts

When an entry point is hit, you receive a Pushover notification with:

- Currency pair
- Direction (LONG/SHORT)
- Entry price hit
- Current price
- Target prices
- Stop loss
- Position size
- Brief recommendation summary

### Alert Settings

- **Priority**: High (1) - alerts are important
- **Frequency**: One alert per entry point (no spam)
- **Timing**: Instant when price hits entry point

### Monitoring Status

The system logs status every 10 minutes:
- Current time
- Active opportunities count
- Current LLM weights
- Next scheduled analysis time

---

## Reinforcement Learning System

### How It Works

1. **Recommendation Logging**
   - Every recommendation is saved to database
   - Includes full context (prices, confidence, rationale)
   - Links to source files

2. **Outcome Evaluation**
   - After 4+ hours, system evaluates outcomes
   - Checks if TP1, TP2, or SL were hit
   - Calculates P&L in pips
   - Tracks max favorable/adverse excursions

3. **Weight Calculation**
   - Based on win rate (60%) and profit factor (40%)
   - Normalized to sum to 100%
   - Minimum 5 samples per LLM required

4. **Daily Updates**
   - Runs at 11pm UTC daily
   - Evaluates recent recommendations
   - Updates weights
   - Saves checkpoint

### Historical Backfill

To learn from past recommendations:

```bash
python historical_backfill.py
```

This script:
- Downloads all historical files from Google Drive
- Parses recommendations
- Evaluates outcomes using historical market data
- Calculates initial weights
- Populates database

**Note**: Run this once before deploying to production.

### Viewing Performance

Query the database to see performance:

```sql
-- Recent recommendations
SELECT llm_source, pair, direction, outcome, pnl_pips 
FROM recommendations 
ORDER BY timestamp DESC LIMIT 20;

-- LLM performance summary
SELECT llm_source, 
       COUNT(*) as total,
       AVG(CASE WHEN outcome IN ('WIN_TP1', 'WIN_TP2') THEN 1.0 ELSE 0.0 END) as win_rate,
       AVG(pnl_pips) as avg_pnl
FROM recommendations
WHERE evaluated = 1
GROUP BY llm_source;

-- Latest weights
SELECT * FROM learning_checkpoints ORDER BY timestamp DESC LIMIT 1;
```

---

## Troubleshooting

### Common Issues

#### 1. "No files found" Error

**Problem**: System can't find analysis files in Google Drive

**Solutions**:
- Verify `GOOGLE_DRIVE_FOLDER_ID` is correct
- Check folder name is "Forex tracker"
- Ensure files have "summary" or "report" in name
- Verify Google Drive credentials are valid

#### 2. LLM Analysis Fails

**Problem**: One or more LLMs return no results

**Solutions**:
- Check API keys are valid and have credits
- Verify API keys are set in environment variables
- Check API rate limits (may need to wait)
- Review logs for specific error messages

#### 3. Email Not Sending

**Problem**: Recommendations generated but email not received

**Solutions**:
- Verify `SENDER_EMAIL` and `SENDER_PASSWORD` are correct
- For Gmail, use App Password (not regular password)
- Check SMTP settings (server, port)
- Verify `RECIPIENT_EMAIL` is correct
- Check spam folder

#### 4. Pushover Alerts Not Working

**Problem**: Entry points hit but no alerts received

**Solutions**:
- Verify `PUSHOVER_API_TOKEN` and `PUSHOVER_USER_KEY`
- Check Pushover app is installed and logged in
- Verify price monitoring is running (check logs)
- Check if alert was already sent (one-time per entry)

#### 5. RL System Not Learning

**Problem**: Weights not updating or showing default values

**Solutions**:
- Run `historical_backfill.py` to populate database
- Check if recommendations are being logged (check database)
- Verify daily learning is running (check logs at 11pm UTC)
- Ensure recommendations are at least 4 hours old before evaluation

#### 6. Google Drive Authentication Error

**Problem**: `invalid_grant: Token has been expired or revoked`

**Solutions**:
- Generate new refresh token (see `get_new_refresh_token.py`)
- Verify `GOOGLE_DRIVE_CREDENTIALS_JSON` matches the refresh token
- Ensure credentials JSON has correct `client_id` and `client_secret`
- Check if token was revoked in Google account settings

### Logs

Check logs for detailed error information:

- **Location**: `logs/trade_alerts_YYYYMMDD.log`
- **Format**: Timestamp, level, message
- **Levels**: DEBUG, INFO, WARNING, ERROR

### Getting Help

1. Check logs for error messages
2. Verify all environment variables are set
3. Test individual components (see test scripts)
4. Review documentation files in project

---

## Best Practices

### 1. Regular Monitoring

- Check email for recommendations daily
- Review Pushover alerts promptly
- Monitor system logs for errors

### 2. Database Maintenance

- Periodically backup `trade_alerts_rl.db`
- Review performance metrics monthly
- Adjust position sizing based on RL insights

### 3. API Key Management

- Rotate API keys periodically
- Monitor API usage and costs
- Set up billing alerts for LLM providers

### 4. Position Sizing

- Use RL insights to adjust position sizes
- Increase size when all LLMs agree
- Decrease size when LLMs disagree
- Never risk more than recommended

### 5. Risk Management

- Always use stop losses
- Follow position sizing recommendations
- Don't trade on recommendations alone
- Combine with your own analysis

### 6. System Updates

- Keep dependencies updated
- Review new features in documentation
- Test changes in development first
- Backup before major updates

---

## Additional Resources

- **Technical Documentation**: See `TECHNICAL_DOCUMENTATION.md`
- **RL Setup Guide**: See `RL_SETUP_GUIDE.md`
- **Deployment Guide**: See `RL_DEPLOYMENT_GUIDE.md`
- **Troubleshooting**: See `TROUBLESHOOTING_RENDER.md`

---

## Support

For issues or questions:

1. Check logs for error messages
2. Review troubleshooting section
3. Verify configuration
4. Test individual components

---

**Last Updated**: 2025-01-05
**Version**: 2.0 (with RL System)

