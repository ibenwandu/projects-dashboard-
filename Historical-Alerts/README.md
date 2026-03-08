# Historical Forex News-Price Correlation Prediction System

A machine learning system that analyzes 5 years of historical currency price data correlated with high-impact news events to predict future currency movements.

## Features

- **Historical Data Analysis**: Fetches 5 years of historical price data for major currency pairs
- **News Event Simulation**: Simulates high-impact news events (rate decisions, NFP, CPI, GDP, geopolitical)
- **AI-Powered News Analysis**: Uses Google Gemini AI to analyze news impact on currencies
- **Machine Learning Model**: Random Forest classifier trained on price + news features
- **Trading Signals**: Generates predictions and trading signals based on model confidence
- **Technical Indicators**: Includes RSI, moving averages, volatility, and momentum indicators

## Requirements

- Python 3.8+
- Google Gemini API key (free tier available)
- Internet connection for data fetching

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key"
4. Create a new key or use existing one
5. Copy the API key

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-1.5-flash  # Optional
```

Or copy the example:

```bash
cp .env.example .env
# Then edit .env and add your API key
```

### 4. Run the System

```bash
python main.py
```

## How It Works

### 1. Data Collection
- Downloads 5 years of historical price data for major currency pairs (EUR/USD, GBP/USD, USD/JPY, etc.)
- Calculates technical indicators (RSI, moving averages, volatility)

### 2. News Event Simulation
- Simulates high-impact news events over the historical period
- Event types: interest rate decisions, employment reports, inflation data, GDP, geopolitical events

### 3. Feature Engineering
- Combines price data with news events
- Creates features: technical indicators + news sentiment + news impact
- Classifies price movements (UP, DOWN, NEUTRAL)

### 4. Model Training
- Trains Random Forest classifier on historical data
- Evaluates model performance (accuracy, classification report)
- Shows feature importance

### 5. Prediction
- Uses trained model to predict future movements
- Can analyze recent news using Gemini AI
- Generates trading signals based on confidence threshold

## Currency Pairs

The system analyzes these major pairs:
- EUR/USD
- GBP/USD
- USD/JPY
- AUD/USD
- NZD/USD
- USD/CAD
- USD/CHF

## Usage Examples

### Basic Usage

```python
from src.predictor import ForexNewsPricePredictor

# Initialize
predictor = ForexNewsPricePredictor()

# Fetch data
predictor.fetch_historical_data(years=5)

# Simulate news
predictor.simulate_news_events()

# Build features
predictor.build_features()

# Train model
predictor.train_model()

# Predict
prediction = predictor.predict_future_movement('EURUSD', 1.0850)
print(f"Prediction: {prediction['prediction']}")
print(f"Confidence: {prediction['confidence']:.1%}")
```

### With Recent News Analysis

```python
recent_news = [
    "Federal Reserve signals potential rate cuts",
    "European inflation data higher than expected"
]

prediction = predictor.predict_future_movement(
    'EURUSD',
    1.0850,
    recent_news=recent_news
)
```

### Generate Trading Signals

```python
# Get all signals with confidence >= 60%
signals = predictor.generate_trading_signals(confidence_threshold=0.6)

for signal in signals:
    print(f"{signal['pair']}: {signal['action']} (confidence: {signal['confidence']:.1%})")
```

## Project Structure

```
Historical-Alerts/
├── src/
│   ├── __init__.py
│   ├── logger.py          # Logging configuration
│   └── predictor.py       # Main prediction system
├── data/                  # Data files (gitignored)
├── logs/                  # Log files (gitignored)
├── output/                # Output files (gitignored)
├── main.py                # Main entry point
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Your Google Gemini API key (required for AI analysis)
- `GEMINI_MODEL`: Gemini model to use (optional, default: gemini-1.5-flash)

### Model Parameters

You can adjust model parameters in `src/predictor.py`:
- `n_estimators`: Number of trees in Random Forest (default: 100)
- `max_depth`: Maximum tree depth (default: 10)
- Movement thresholds: `> 0.005` for UP, `< -0.005` for DOWN

## Future Enhancements

- [ ] Integrate real news APIs (NewsAPI, Bloomberg, etc.)
- [ ] Add more sophisticated news sentiment analysis
- [ ] Implement backtesting framework
- [ ] Add risk management and position sizing
- [ ] Web service/API deployment
- [ ] Real-time price monitoring
- [ ] Email/alert notifications
- [ ] Dashboard/visualization

## Notes

- The system currently uses simulated news events. In production, integrate with real news APIs.
- Model accuracy depends on data quality and feature engineering.
- Predictions are based on historical patterns and may not account for unprecedented events.
- Always use proper risk management when trading based on predictions.

## License

This project is for educational and research purposes.







