# Tech-Trade Implementation Notes

## Overview

Tech-Trade is a technical correlation analysis system that identifies correlative movement patterns between currency pairs using 5 years of historical data across daily and weekly timeframes.

## Architecture

### Core Components

1. **Data Fetcher** (`src/data_fetcher.py`)
   - Downloads historical data from Dukascopy
   - Supports both library-based and direct API calls
   - Implements caching to avoid re-downloading
   - Handles rate limiting

2. **Correlation Analyzer** (`src/correlation_analyzer.py`)
   - Calculates Pearson and Spearman correlations
   - Detects lag correlations (leading/lagging relationships)
   - Identifies patterns above threshold
   - Analyzes rolling correlations for consistency

3. **Pattern Validator** (`src/pattern_validator.py`)
   - Validates patterns across timeframes (daily vs weekly)
   - Validates patterns across time periods (splits data into chunks)
   - Calculates consistency scores
   - Filters out inconsistent patterns

4. **Data Manager** (`src/data_manager.py`)
   - Manages data storage and retrieval
   - Handles caching with expiration
   - Saves/loads patterns as JSON
   - Lists available data files

5. **Main Application** (`main.py`)
   - Command-line interface
   - Orchestrates download → analyze → validate → report workflow
   - Loads configuration from YAML

## Data Source: Dukascopy

### API Format

Dukascopy provides free historical forex data:
- URL format: `https://www.dukascopy.com/datafeed/{PAIR}/{YEAR}/{MONTH}/{DAY}/{TIMEFRAME}_bid_ask.csv`
- Data format: CSV with columns: Time, Open, High, Low, Close, Volume
- Time format: Unix timestamp in milliseconds

### Alternative: dukascopy-python Library

The system tries to use the `dukascopy-python` library first (if installed), then falls back to direct API calls.

```python
from dukascopy_python import fetch
df = fetch("EURUSD", interval="1DAY", start=start, end=end)
```

## Pattern Detection Logic

### Correlation Calculation

1. **Align Data**: Merge two pairs' data by timestamp
2. **Calculate Returns**: Convert prices to percentage returns
3. **Correlation**: Use Pearson or Spearman correlation
4. **Threshold**: Only patterns above threshold (default 0.7) are considered

### Lag Detection

- Checks correlations with lags from -10 to +10 periods
- Identifies if one pair leads or lags the other
- Records best lag and direction

### Validation

1. **Cross-Timeframe**: Compare daily vs weekly correlations
2. **Cross-Period**: Split data into 4 periods, check consistency
3. **Consistency Score**: Low standard deviation = high consistency

## Configuration

Edit `config.yaml` to customize:

- **Currency Pairs**: Add/remove pairs from major, minor, exotic lists
- **Timeframes**: Currently 1DAY and 1WEEK
- **Historical Period**: Default 5 years
- **Correlation Threshold**: Minimum correlation (default 0.7)
- **Consistency Threshold**: Minimum consistency (default 0.6)

## Usage Examples

### Download Only
```bash
python main.py --download
```

### Analyze Existing Data
```bash
python main.py --analyze
```

### Full Workflow
```bash
python main.py --all
```

## Output

### Pattern Structure

```json
{
  "pair1": "EUR/USD",
  "pair2": "GBP/USD",
  "correlation": 0.852,
  "p_value": 0.001,
  "lag": 0,
  "direction": "synchronous",
  "rolling_corr_mean": 0.845,
  "rolling_corr_std": 0.023,
  "data_points": 1825,
  "significance": "high"
}
```

### Validation Results

```json
{
  "pattern": {...},
  "overall_valid": true,
  "overall_consistency": 0.87,
  "timeframe_validation": {
    "valid": true,
    "consistency_score": 0.89,
    "daily_correlation": 0.852,
    "weekly_correlation": 0.841
  },
  "period_validation": {
    "valid": true,
    "consistency_score": 0.85,
    "mean_correlation": 0.848,
    "std_correlation": 0.012
  }
}
```

## Future Enhancements

1. **Visualization**: Add charts for correlation patterns
2. **Real-time Monitoring**: Track live correlations
3. **Machine Learning**: Predict correlation breakdowns
4. **Portfolio Optimization**: Use correlations for risk management
5. **Alert System**: Notify when correlations change significantly

## Troubleshooting

### Dukascopy API Issues

- **Rate Limiting**: System implements 500ms delay between requests
- **Missing Data**: Some pairs may not have full 5-year history
- **Library Alternative**: Install `dukascopy-python` for better reliability

### Data Quality

- **Minimum Data Points**: Requires at least 20 points for correlation
- **Alignment Issues**: System handles missing dates by inner join
- **Outliers**: Consider adding outlier detection in future versions

## Performance

- **Download**: ~1-2 seconds per pair per timeframe
- **Analysis**: ~0.1 seconds per pair combination
- **Validation**: ~0.5 seconds per pattern
- **Total**: ~5-10 minutes for full analysis of 20 pairs

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- pandas: Data manipulation
- numpy: Numerical operations
- scipy: Statistical functions
- requests: HTTP requests
- tqdm: Progress bars
- pyyaml: Configuration parsing

