# Tech-Trade: Technical Correlation Analysis System

## Overview

Tech-Trade analyzes historical currency data to identify correlative movement patterns between currency pairs. The system downloads 5-year historical data, detects patterns, and evaluates their consistency across different timeframes.

## Features

- **Historical Data Collection**: Downloads 5-year data for major, minor, and exotic currency pairs
- **Multi-Timeframe Analysis**: Analyzes both daily (1D) and weekly (1W) timeframes
- **Pattern Detection**: Identifies correlative movement patterns between currency pairs
- **Consistency Analysis**: Evaluates pattern consistency across weeks, months, and years
- **Automated Updates**: Keeps historical data current using Dukascopy API

## Data Source

- **Dukascopy**: Free historical forex data
- **Timeframes**: 1 day and 1 week
- **Period**: 5 years of historical data
- **Pairs**: Major, minor, and exotic currency pairs

## Project Structure

```
Tech-Trade/
├── src/
│   ├── __init__.py
│   ├── data_fetcher.py      # Dukascopy data download
│   ├── correlation_analyzer.py  # Pattern detection
│   ├── pattern_validator.py     # Consistency analysis
│   ├── data_manager.py          # Data storage/caching
│   └── visualizer.py            # Pattern visualization
├── data/
│   ├── raw/                     # Raw CSV files
│   ├── processed/               # Processed data
│   └── patterns/                # Detected patterns
├── requirements.txt
├── config.yaml                  # Configuration
└── main.py                      # Main entry point
```

## Installation

```bash
cd personal/Tech-Trade
pip install -r requirements.txt
```

## Usage

```bash
# Download historical data
python main.py --download

# Analyze correlations
python main.py --analyze

# Generate report
python main.py --report
```

## Configuration

Edit `config.yaml` to:
- Select currency pairs to analyze
- Set timeframes
- Configure pattern detection parameters
- Set data storage paths

