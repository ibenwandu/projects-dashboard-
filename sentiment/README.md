---
title: Sentiment-Aware Forex Monitor
emoji: 🚨
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
---

# Sentiment-Aware Forex Monitor

Monitor your forex trades for sentiment shifts using AI-powered analysis.

## Features

- ✅ Web-based watchlist management
- ✅ Track last alert time per asset
- ✅ Monitor sentiment direction
- ✅ View recent alerts
- ✅ 24/7 operation on Hugging Face Spaces

## Setup

1. Add your environment variables in Hugging Face Spaces settings:
   - `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY`)
   - `SENDER_EMAIL`
   - `SENDER_PASSWORD`
   - `EMAIL_RECIPIENT`

2. The app will automatically create the database on first run.

## Usage

1. Go to the "Watchlist" tab
2. Add trades with:
   - Forex pair (e.g., USD/CAD)
   - Trade direction (Long/Short)
   - Bias expectation
   - Sensitivity level
3. View recent alerts in the "Recent Alerts" tab
