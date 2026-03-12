# Trade-Alerts Technical Documentation

## 📖 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Database Schema](#database-schema)
5. [API Integrations](#api-integrations)
6. [Reinforcement Learning System](#reinforcement-learning-system)
7. [File Structure](#file-structure)
8. [Configuration Management](#configuration-management)
9. [Error Handling](#error-handling)
10. [Performance Considerations](#performance-considerations)
11. [Deployment](#deployment)
12. [Development Guide](#development-guide)

---

## Architecture Overview

Trade-Alerts is a modular Python application designed for 24/7 operation. It follows a component-based architecture where each module handles a specific responsibility.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Trade-Alerts System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  DriveReader │───▶│ DataFormatter│───▶│ LLMAnalyzer  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │         │
│         │                    │                    │         │
│         ▼                    ▼                    ▼         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           GeminiSynthesizer                          │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           RL Enhancement (LLMLearningEngine)        │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ EmailSender  │    │ RL Database  │    │ Rec Parser   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │PriceMonitor  │───▶│AlertManager  │    │AlertHistory  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Modularity**: Each component is independent and testable
2. **Separation of Concerns**: Data fetching, analysis, and alerting are separate
3. **Extensibility**: Easy to add new LLMs or data sources
4. **Resilience**: Error handling and retry logic throughout
5. **Observability**: Comprehensive logging at all levels

---

## System Components

### Core Components

#### 1. `DriveReader` (`src/drive_reader.py`)

**Purpose**: Read analysis files from Google Drive

**Key Methods**:
- `get_latest_analysis_files(pattern)`: Get files matching pattern
- `download_file(file_id, title)`: Download file to local storage

**Dependencies**:
- `PyDrive2`: Google Drive API wrapper
- `oauth2client`: OAuth 2.0 authentication

**Configuration**:
- `GOOGLE_DRIVE_FOLDER_ID`: Target folder ID
- `GOOGLE_DRIVE_CREDENTIALS_JSON`: OAuth credentials
- `GOOGLE_DRIVE_REFRESH_TOKEN`: Refresh token for authentication

**Error Handling**:
- Handles expired tokens gracefully
- Retries on transient errors
- Logs authentication failures

#### 2. `DataFormatter` (`src/data_formatter.py`)

**Purpose**: Format downloaded files for LLM consumption

**Key Methods**:
- `format_files(file_paths)`: Combine and format multiple files

**Features**:
- Extracts relevant content from files
- Removes formatting artifacts
- Adds context (date, time, source)

#### 3. `LLMAnalyzer` (`src/llm_analyzer.py`)

**Purpose**: Analyze data using multiple LLM APIs

**Key Methods**:
- `analyze_with_chatgpt(data_summary)`: ChatGPT analysis
- `analyze_with_gemini(data_summary)`: Gemini analysis
- `analyze_with_claude(data_summary)`: Claude analysis
- `analyze_all(data_summary)`: Run all analyses in parallel

**Features**:
- Automatic model selection (tries multiple models)
- Retry logic with exponential backoff
- Rate limit handling
- Timezone-aware date/time context

**Configuration**:
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `GOOGLE_API_KEY`, `GEMINI_MODEL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`

**Error Handling**:
- Handles quota errors (429) with retries
- Falls back to alternative models
- Continues if one LLM fails

#### 4. `GeminiSynthesizer` (`src/gemini_synthesizer.py`)

**Purpose**: Synthesize multiple LLM recommendations into one

**Key Methods**:
- `synthesize(llm_recommendations)`: Create unified recommendation

**Features**:
- Combines three LLM outputs
- Resolves conflicts
- Highlights consensus
- Provides balanced view

#### 5. `EmailSender` (`src/email_sender.py`)

**Purpose**: Send recommendations via email

**Key Methods**:
- `send_recommendations(llm_recs, gemini_final)`: Send formatted email

**Features**:
- Plain text email format
- Includes all LLM recommendations
- Includes RL insights
- Error handling and logging

**Configuration**:
- `SENDER_EMAIL`, `SENDER_PASSWORD`
- `RECIPIENT_EMAIL`
- `SMTP_SERVER`, `SMTP_PORT`

#### 6. `PriceMonitor` (`src/price_monitor.py`)

**Purpose**: Monitor real-time currency prices

**Key Methods**:
- `get_rate(pair)`: Get current exchange rate
- `check_entry_point(pair, entry, direction)`: Check if entry point hit

**Features**:
- Uses Frankfurter.app (free, no API key)
- Caching (60 seconds TTL)
- Handles cross rates
- Tolerance-based entry detection (0.1% or 10 pips)

**API**:
- Base URL: `https://api.frankfurter.app/latest`
- Supports all major currency pairs

#### 7. `AlertManager` (`src/alert_manager.py`)

**Purpose**: Send Pushover alerts for entry points

**Key Methods**:
- `send_alert(title, message, priority)`: Generic alert
- `send_entry_alert(opportunity, current_price)`: Entry point alert

**Features**:
- High priority alerts (priority=1)
- Includes full trade details
- Error handling and logging

**Configuration**:
- `PUSHOVER_API_TOKEN`
- `PUSHOVER_USER_KEY`

#### 8. `AlertHistory` (`src/alert_history.py`)

**Purpose**: Track sent alerts to prevent duplicates

**Key Methods**:
- `has_alerted(opportunity)`: Check if already alerted
- `record_alert(opportunity, price)`: Record sent alert

**Storage**: JSON file (`data/alerts_history.json`)

#### 9. `AnalysisScheduler` (`src/scheduler.py`)

**Purpose**: Manage scheduled analysis times

**Key Methods**:
- `should_run_analysis(current_time)`: Check if analysis should run
- `get_next_analysis_time(current_time)`: Get next scheduled time

**Features**:
- Configurable times via `ANALYSIS_TIMES`
- Timezone support (default: EST/EDT)
- 5-minute tolerance window
- Handles timezone conversions (UTC ↔ EST/EDT)

**Configuration**:
- `ANALYSIS_TIMES`: Comma-separated times (e.g., "02:00,04:00,07:00")
- `ANALYSIS_TIMEZONE`: Timezone string (default: "America/New_York")

### Reinforcement Learning Components

#### 10. `RecommendationDatabase` (`src/trade_alerts_rl.py`)

**Purpose**: Store and manage all recommendations and outcomes

**Key Methods**:
- `log_recommendation(rec)`: Store new recommendation
- `get_pending_recommendations()`: Get unevaluated recommendations
- `update_outcome(rec_id, outcome, ...)`: Update with outcome

**Database**: SQLite (`trade_alerts_rl.db`)

**Schema**: See [Database Schema](#database-schema)

#### 11. `RecommendationParser` (`src/trade_alerts_rl.py`)

**Purpose**: Parse recommendations from files

**Key Methods**:
- `parse_file(file_path)`: Parse file and extract recommendations
- `_parse_json_file(file_path)`: Parse JSON files
- `_parse_recommendations(text)`: Parse text files
- `_parse_freeform_recommendations(text)`: Extract from unstructured text

**Features**:
- Supports `.txt` and `.json` formats
- Handles various JSON structures
- Flexible regex patterns for text parsing
- Normalizes LLM sources, pairs, directions
- Extracts prices, position size, confidence, rationale

#### 12. `OutcomeEvaluator` (`src/trade_alerts_rl.py`)

**Purpose**: Evaluate trade outcomes using historical market data

**Key Methods**:
- `evaluate_recommendation(rec)`: Evaluate single recommendation
- `evaluate_batch(recs)`: Evaluate multiple recommendations

**Features**:
- Uses `yfinance` for historical data
- Checks if TP1, TP2, or SL were hit
- Calculates P&L in pips
- Tracks max favorable/adverse excursions
- Handles missing data gracefully

**Outcomes**:
- `WIN_TP1`: Take profit 1 hit
- `WIN_TP2`: Take profit 2 hit
- `LOSS_SL`: Stop loss hit
- `NEUTRAL`: No TP/SL hit within timeframe

#### 13. `LLMLearningEngine` (`src/trade_alerts_rl.py`)

**Purpose**: Calculate LLM performance weights and generate insights

**Key Methods**:
- `calculate_llm_weights()`: Calculate performance weights
- `generate_performance_report()`: Generate comprehensive report
- `analyze_consensus()`: Analyze consensus performance

**Weight Calculation**:
- Based on win rate (60%) and profit factor (40%)
- Normalized to sum to 100%
- Minimum 5 samples per LLM required
- Default equal weights if insufficient data

**Features**:
- Consensus analysis (ALL_AGREE, 2_AGREE, ALL_DISAGREE)
- Performance tracking over time
- Learning checkpoints

---

## Data Flow

### Analysis Workflow

```
1. Scheduler triggers analysis
   ↓
2. DriveReader downloads files from Google Drive
   ↓
3. DataFormatter formats files for LLMs
   ↓
4. LLMAnalyzer sends to ChatGPT, Gemini, Claude (parallel)
   ↓
5. GeminiSynthesizer combines recommendations
   ↓
6. LLMLearningEngine enhances with RL insights
   ↓
7. EmailSender sends email
   ↓
8. RecommendationParser extracts recommendations
   ↓
9. RecommendationDatabase logs recommendations
   ↓
10. RecommendationParser extracts entry points
   ↓
11. System starts monitoring entry points
```

### Monitoring Workflow

```
1. Main loop runs every CHECK_INTERVAL seconds
   ↓
2. For each active opportunity:
   ↓
3. PriceMonitor.get_rate(pair) → Current price
   ↓
4. PriceMonitor.check_entry_point() → Hit check
   ↓
5. If hit:
   ↓
6. AlertHistory.has_alerted() → Duplicate check
   ↓
7. AlertManager.send_entry_alert() → Send alert
   ↓
8. AlertHistory.record_alert() → Record sent
```

### Learning Workflow

```
1. Daily learning triggers at 11pm UTC
   ↓
2. RecommendationDatabase.get_pending_recommendations()
   ↓
3. Filter: recommendations 4+ hours old
   ↓
4. OutcomeEvaluator.evaluate_batch() → Evaluate outcomes
   ↓
5. RecommendationDatabase.update_outcome() → Save outcomes
   ↓
6. LLMLearningEngine.calculate_llm_weights() → Update weights
   ↓
7. Save learning checkpoint
```

---

## Database Schema

### `recommendations` Table

Stores all LLM recommendations:

```sql
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- ISO format
    date_generated TEXT NOT NULL,         -- YYYY-MM-DD
    llm_source TEXT NOT NULL,              -- 'chatgpt', 'gemini', 'claude', 'synthesis'
    pair TEXT NOT NULL,                    -- 'EUR/USD'
    direction TEXT NOT NULL,                -- 'LONG', 'SHORT'
    entry_price REAL NOT NULL,
    stop_loss REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    position_size_pct REAL,                -- Percentage of account
    confidence TEXT,                        -- 'High', 'Medium', 'Low'
    rationale TEXT,                         -- Full explanation
    
    -- Market context
    market_session TEXT,                    -- 'Asian', 'European', 'US'
    day_of_week TEXT,                       -- 'Monday', etc.
    
    -- Outcome tracking
    outcome TEXT,                           -- 'WIN_TP1', 'WIN_TP2', 'LOSS_SL', 'NEUTRAL', 'PENDING'
    exit_price REAL,
    pnl_pips REAL,
    bars_held INTEGER,
    max_favorable_pips REAL,
    max_adverse_pips REAL,
    outcome_timestamp TEXT,
    evaluated INTEGER DEFAULT 0,           -- 0 = pending, 1 = evaluated
    
    -- Source tracking
    source_file TEXT,                       -- Path to original file
    
    UNIQUE(timestamp, llm_source, pair, direction, entry_price)
)
```

### `llm_performance` Table

Tracks performance snapshots:

```sql
CREATE TABLE llm_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    llm_source TEXT NOT NULL,
    pair TEXT,                              -- NULL = overall
    total_recommendations INTEGER,
    total_evaluated INTEGER,
    win_rate REAL,
    avg_pnl_pips REAL,
    profit_factor REAL,
    avg_bars_to_tp REAL,
    avg_bars_to_sl REAL,
    accuracy_weight REAL
)
```

### `learning_checkpoints` Table

Records weight updates:

```sql
CREATE TABLE learning_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_recommendations INTEGER,
    total_evaluated INTEGER,
    chatgpt_weight REAL,
    gemini_weight REAL,
    claude_weight REAL,
    synthesis_weight REAL,
    overall_win_rate REAL,
    notes TEXT
)
```

### `consensus_analysis` Table

Analyzes consensus performance:

```sql
CREATE TABLE consensus_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    consensus_type TEXT NOT NULL,           -- 'ALL_AGREE', '2_AGREE', 'ALL_DISAGREE'
    total_trades INTEGER,
    win_rate REAL,
    avg_pnl_pips REAL,
    profit_factor REAL
)
```

---

## API Integrations

### Google Drive API

**Library**: `PyDrive2`

**Authentication**: OAuth 2.0 with refresh token

**Endpoints Used**:
- List files in folder
- Download file content

**Rate Limits**: 
- 1000 requests per 100 seconds per user
- System implements delays between requests

### OpenAI API (ChatGPT)

**Library**: `openai`

**Model**: `gpt-4o-mini` (configurable)

**Endpoints**:
- `POST /v1/chat/completions`

**Rate Limits**:
- Varies by tier
- System implements retry logic

### Google Gemini API

**Library**: `google-generativeai`

**Model**: `gemini-1.5-flash` (auto-detects available models)

**Endpoints**:
- `POST /v1/models/{model}:generateContent`

**Rate Limits**:
- 60 requests per minute (free tier)
- System implements exponential backoff for 429 errors

### Anthropic Claude API

**Library**: `anthropic`

**Model**: `claude-haiku-4-5-20251001` (with fallbacks)

**Endpoints**:
- `POST /v1/messages`

**Rate Limits**:
- Varies by tier
- System implements retry logic

### Frankfurter.app (Price API)

**Library**: `requests`

**Endpoint**: `GET https://api.frankfurter.app/latest`

**Features**:
- Free, no API key required
- Real-time exchange rates
- Supports all major pairs

**Rate Limits**:
- No official limits
- System caches for 60 seconds

### Pushover API

**Library**: `requests`

**Endpoint**: `POST https://api.pushover.net/1/messages.json`

**Rate Limits**:
- 10,000 messages per month (free tier)

### SMTP (Email)

**Library**: Built-in `smtplib`

**Configuration**:
- Gmail: `smtp.gmail.com:587`
- TLS encryption
- App password required for Gmail

---

## Reinforcement Learning System

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Recommendation Flow                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  LLM Recommendations → Parser → Database                │
│                                                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Outcome Evaluation                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Database → Evaluator (yfinance) → Outcomes             │
│                                                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Learning Engine                             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Outcomes → Weight Calculation → Checkpoints              │
│                                                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Enhanced Recommendations                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Weights → Insights → Email Enhancement                   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Weight Calculation Algorithm

```python
def calculate_weights():
    for each LLM:
        win_rate = wins / total_evaluated
        profit_factor = gross_profit / gross_loss
        
        # Normalize profit factor (0-1 scale, assuming max 3.0)
        normalized_pf = min(profit_factor / 3.0, 1.0)
        
        # Combined score (60% win rate, 40% profit factor)
        score = (0.6 * win_rate) + (0.4 * normalized_pf)
        
        # Minimum 5 samples required
        if total_evaluated < 5:
            score = 0.25  # Default equal weight
    
    # Normalize to sum to 1.0
    total_score = sum(all_scores)
    weights = {llm: score / total_score for llm, score in scores.items()}
    
    return weights
```

### Outcome Evaluation Logic

```python
def evaluate_recommendation(rec):
    # Fetch historical data (4-hour candles)
    data = yfinance.fetch(pair, period="5d", interval="1h")
    
    entry_time = rec.timestamp
    entry_price = rec.entry_price
    direction = rec.direction
    
    # Find entry candle
    entry_idx = find_candle_at_time(data, entry_time)
    
    # Check each subsequent candle
    for i in range(entry_idx + 1, len(data)):
        candle = data.iloc[i]
        high = candle['High']
        low = candle['Low']
        
        if direction == 'LONG':
            # Check TP1
            if high >= rec.take_profit_1:
                return 'WIN_TP1', rec.take_profit_1, calculate_pips(...)
            
            # Check TP2
            if high >= rec.take_profit_2:
                return 'WIN_TP2', rec.take_profit_2, calculate_pips(...)
            
            # Check SL
            if low <= rec.stop_loss:
                return 'LOSS_SL', rec.stop_loss, calculate_pips(...)
        
        # Similar logic for SHORT...
    
    # No TP/SL hit within timeframe
    return 'NEUTRAL', current_price, 0
```

---

## File Structure

```
Trade-Alerts/
├── main.py                          # Main application entry point
├── historical_backfill.py           # One-time historical data processing
├── requirements.txt                 # Python dependencies
├── Procfile                         # Render deployment config
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
│
├── src/
│   ├── __init__.py
│   ├── logger.py                    # Logging configuration
│   ├── drive_reader.py              # Google Drive integration
│   ├── data_formatter.py            # Data formatting
│   ├── llm_analyzer.py              # LLM API integration
│   ├── gemini_synthesizer.py        # Recommendation synthesis
│   ├── email_sender.py              # Email notifications
│   ├── recommendation_parser.py     # Entry point extraction
│   ├── price_monitor.py             # Price monitoring
│   ├── alert_manager.py             # Pushover alerts
│   ├── alert_history.py             # Alert tracking
│   ├── scheduler.py                 # Analysis scheduling
│   ├── trade_alerts_rl.py           # RL system (database, parser, evaluator, engine)
│   └── daily_learning.py            # Daily learning job
│
├── data/
│   ├── recommendations/              # Saved recommendation files
│   │   ├── forex_recommendations_YYYYMMDD_HHMMSS.txt
│   │   └── forex_recommendations_YYYYMMDD_HHMMSS.json
│   └── alerts_history.json           # Alert history
│
├── logs/
│   └── trade_alerts_YYYYMMDD.log    # Application logs
│
├── trade_alerts_rl.db               # RL database (SQLite)
│
└── docs/
    ├── USER_GUIDE.md                 # User documentation
    ├── TECHNICAL_DOCUMENTATION.md    # This file
    ├── RL_SETUP_GUIDE.md             # RL setup instructions
    ├── RL_DEPLOYMENT_GUIDE.md        # Deployment guide
    └── ...
```

---

## Configuration Management

### Environment Variables

All configuration is via environment variables (no config files):

**Required**:
- Google Drive: `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_DRIVE_CREDENTIALS_JSON`, `GOOGLE_DRIVE_REFRESH_TOKEN`
- LLM APIs: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`
- Email: `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAIL`
- Pushover: `PUSHOVER_API_TOKEN`, `PUSHOVER_USER_KEY`

**Optional**:
- Schedule: `ANALYSIS_TIMES`, `ANALYSIS_TIMEZONE`
- Monitoring: `CHECK_INTERVAL`
- Models: `OPENAI_MODEL`, `GEMINI_MODEL`, `ANTHROPIC_MODEL`

### Loading Configuration

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads from .env file

value = os.getenv('KEY', 'default_value')
```

### Render Deployment

Environment variables are set in Render Dashboard:
- Dashboard → Service → Environment
- Add each variable
- Restart service after changes

---

## Error Handling

### Strategy

1. **Graceful Degradation**: System continues if one component fails
2. **Retry Logic**: Transient errors are retried with exponential backoff
3. **Comprehensive Logging**: All errors are logged with context
4. **User Notification**: Critical errors are reported via email/alerts

### Error Types

#### 1. API Errors

**Handling**:
- Retry with exponential backoff (10s, 20s, 40s)
- Fallback to alternative models if available
- Continue with available LLMs if one fails

**Example**:
```python
try:
    response = api_call()
except QuotaError as e:
    if retry_count < max_retries:
        time.sleep(backoff_delay)
        retry()
    else:
        logger.error("Quota exceeded")
        return None
```

#### 2. Network Errors

**Handling**:
- Retry with delays
- Cache results when possible
- Use fallback APIs if available

#### 3. Data Errors

**Handling**:
- Validate data before processing
- Skip invalid entries
- Log warnings for review

#### 4. Authentication Errors

**Handling**:
- Clear error messages
- Instructions for fixing
- Graceful failure (don't crash)

---

## Performance Considerations

### Optimization Strategies

1. **Caching**:
   - Price data: 60 seconds TTL
   - LLM responses: Not cached (always fresh)
   - File downloads: Cached locally

2. **Parallel Processing**:
   - LLM analyses run in parallel (not sequential)
   - Price checks are independent

3. **Database**:
   - SQLite with proper indexing
   - Batch operations where possible
   - Connection pooling (single connection per operation)

4. **API Rate Limits**:
   - Delays between requests
   - Exponential backoff on rate limit errors
   - Respect API quotas

### Resource Usage

**Typical**:
- Memory: ~100-200 MB
- CPU: Low (mostly I/O bound)
- Disk: ~50 MB (database + logs)

**Peak**:
- Memory: ~500 MB (during analysis)
- CPU: Medium (LLM API calls)
- Network: Moderate (API requests)

---

## Deployment

### Render Deployment

See `RL_DEPLOYMENT_GUIDE.md` for detailed instructions.

**Key Points**:
- Use `Procfile` for process definition
- Set all environment variables in dashboard
- Use persistent disk for database
- Monitor logs for errors

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file
cp .env.example .env
# Edit .env with your credentials

# Run locally
python main.py
```

### Testing

```bash
# Test individual components
python test_drive_auth.py
python test_parser.py
python verify_credentials.py

# Run historical backfill
python historical_backfill.py
```

---

## Development Guide

### Adding a New LLM

1. **Add API client** in `llm_analyzer.py`:
   ```python
   def analyze_with_newllm(self, data_summary):
       # Implementation
   ```

2. **Add to `analyze_all()`**:
   ```python
   results['newllm'] = self.analyze_with_newllm(data_summary)
   ```

3. **Update RL system** to recognize new LLM source

4. **Update email formatting** to include new LLM

### Adding a New Data Source

1. **Create new reader class** (similar to `DriveReader`)

2. **Integrate in `main.py`**:
   ```python
   data = drive_reader.get_data() + new_source.get_data()
   ```

3. **Update data formatter** if needed

### Modifying RL Algorithm

1. **Edit `LLMLearningEngine.calculate_llm_weights()`**

2. **Update weight calculation formula**

3. **Test with historical data**

4. **Monitor performance**

### Database Migrations

SQLite doesn't support migrations, so:

1. **Backup database** before changes
2. **Add new columns** with `ALTER TABLE`
3. **Update code** to handle new/old schemas
4. **Test thoroughly**

---

## Additional Resources

- **User Guide**: `USER_GUIDE.md`
- **RL Setup**: `RL_SETUP_GUIDE.md`
- **Deployment**: `RL_DEPLOYMENT_GUIDE.md`
- **API Documentation**: See individual component files

---

**Last Updated**: 2025-01-05
**Version**: 2.0 (with RL System)

