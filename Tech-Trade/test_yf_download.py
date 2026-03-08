"""Test yf.download() method to see if it works better than Ticker().history()"""

import sys
sys.path.insert(0, 'src')

from data_fetcher import DukascopyDataFetcher
from datetime import datetime, timedelta
import time

print("=" * 80)
print("Testing yf.download() method vs Ticker().history()")
print("=" * 80)

# Wait to reset any rate limits
print("\nWaiting 30 seconds to reset any rate limits...")
time.sleep(30)

fetcher = DukascopyDataFetcher()
end_date = datetime.now()
start_date = end_date - timedelta(days=365*3)

print(f"\nDate range: {start_date.date()} to {end_date.date()}")
print(f"Testing EUR/USD with 1DAY timeframe...\n")

df = fetcher._fetch_with_yfinance('EUR/USD', start_date, end_date, '1DAY')

if df is not None and len(df) > 0:
    print(f"SUCCESS: {len(df)} records downloaded")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Columns: {list(df.columns)}")
    print(f"Sample data:")
    print(df.head())
else:
    print("FAILED: No data downloaded")
    print("This suggests yfinance is still rate-limiting or blocking your IP")

print("\n" + "=" * 80)

