# Tech-Trade Quick Start Guide

## Installation

```bash
cd personal/Tech-Trade
pip install -r requirements.txt
```

## Basic Usage

### Step 1: Download Historical Data

```bash
python main.py --download
```

This will:
- Download 5 years of historical data for all configured pairs
- Use both daily (1DAY) and weekly (1WEEK) timeframes
- Cache data locally to avoid re-downloading
- Save to `data/raw/` directory

### Step 2: Analyze Correlations

```bash
python main.py --analyze
```

This will:
- Analyze correlations between all pair combinations
- Detect patterns with correlation > 0.7 (configurable)
- Identify leading/lagging relationships
- Save results for validation

### Step 3: Validate Patterns

```bash
python main.py --validate
```

This will:
- Validate patterns across daily and weekly timeframes
- Check consistency across different time periods
- Filter out inconsistent patterns
- Keep only reliable, repeatable patterns

### Step 4: Generate Report

```bash
python main.py --report
```

This will:
- Generate summary report
- Save patterns to JSON files
- Display top 10 strongest patterns
- Save to `data/patterns/` directory

## Run All Steps

```bash
python main.py --all
```

This runs download → analyze → validate → report in sequence.

## Configuration

Edit `config.yaml` to:
- Add/remove currency pairs
- Adjust correlation threshold
- Change timeframes
- Modify validation parameters

## Output Files

- **Raw Data**: `data/raw/{PAIR}_{TIMEFRAME}.csv`
- **Patterns**: `data/patterns/patterns_{timestamp}.json`
- **Valid Patterns**: `data/patterns/valid_patterns.json`

## Example Output

```
✅ Pattern found: EUR/USD <-> GBP/USD (corr=0.852, lag=0)
✅ Pattern found: USD/JPY <-> USD/CHF (corr=-0.743, lag=1)
✅ Valid pattern: EUR/USD <-> GBP/USD (consistency: 0.87)
```

## Troubleshooting

**Issue**: "No data retrieved"
- **Solution**: Dukascopy API may be rate-limited. Wait and retry, or use the dukascopy-python library.

**Issue**: "Insufficient data"
- **Solution**: Some pairs may not have 5 years of data. Check config.yaml and reduce years if needed.

**Issue**: "Library not available"
- **Solution**: Install dukascopy-python: `pip install dukascopy-python`, or the system will use direct API calls.

