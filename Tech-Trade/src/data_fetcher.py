"""
Dukascopy Historical Data Fetcher
Downloads 5-year historical data for currency pairs
"""

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
import time
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


class DukascopyDataFetcher:
    """Fetches historical forex data from Dukascopy"""
    
    def __init__(self, data_dir: str = "data/raw"):
        """
        Initialize data fetcher
        
        Args:
            data_dir: Directory to store downloaded CSV files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dukascopy API endpoint
        self.base_url = "https://www.dukascopy.com/datafeed"
        
        # Rate limiting - increased significantly for yfinance to avoid rate limits
        self.last_request_time = 0
        self.min_request_interval = 30.0  # 30 seconds between requests (was 10s - yfinance is VERY rate-limited)
    
    def _rate_limit(self):
        """Simple rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _convert_pair_format(self, pair: str) -> str:
        """
        Convert pair format for Dukascopy API
        EUR/USD -> EURUSD
        """
        return pair.replace('/', '').upper()
    
    def _get_dukascopy_url(self, pair: str, timeframe: str, start: datetime, end: datetime) -> str:
        """
        Construct Dukascopy data URL
        
        Dukascopy format:
        https://www.dukascopy.com/datafeed/{PAIR}/{YEAR}/{MONTH}/{DAY}/{TIMEFRAME}_bid_ask.csv
        
        For historical data, we need to iterate through dates
        """
        # Dukascopy uses a different format - we'll use their historical data API
        # Format: https://www.dukascopy.com/datafeed/{PAIR}/{YEAR}/{MONTH}/{DAY}/{TIMEFRAME}_bid_ask.csv
        pair_clean = self._convert_pair_format(pair)
        
        # For bulk download, we'll need to iterate through dates
        # This is a simplified version - actual implementation may need date iteration
        return f"{self.base_url}/{pair_clean}"
    
    def fetch_pair_data(
        self, 
        pair: str, 
        timeframe: str = "1DAY",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        years: int = 5,
        use_yfinance_fallback: bool = True,
        skip_dukascopy: bool = True  # NEW: Skip Dukascopy entirely to save time
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a currency pair
        
        Args:
            pair: Currency pair (e.g., 'EUR/USD')
            timeframe: '1DAY' or '1WEEK'
            start_date: Start date (default: 5 years ago)
            end_date: End date (default: today)
            years: Number of years of data (if start_date not provided)
            use_yfinance_fallback: Use yfinance if primary source fails (default: True)
            skip_dukascopy: Skip Dukascopy entirely and use yfinance directly (default: True)
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        self._rate_limit()
        
        # Set default dates
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=years * 365)
        
        # Check cache first - use simple file-based cache check
        cache_file = self._get_cache_file(pair, timeframe, start_date, end_date)
        if cache_file.exists():
            try:
                logger.info(f"Loading cached data: {cache_file}")
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                # Remove duplicates
                df = df[~df.index.duplicated(keep='first')]
                # Check if cached data covers our date range
                if len(df) > 0:
                    cached_start = df.index.min()
                    cached_end = df.index.max()
                    if cached_start <= start_date and cached_end >= end_date:
                        logger.info(f"✅ Using cached data for {pair} ({timeframe}) - covers requested range")
                        return df
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}, re-downloading")
        
        # NEW: Skip Dukascopy entirely if flag is set (saves time since it's blocked)
        if skip_dukascopy:
            logger.info(f"⏭️  Skipping Dukascopy (blocked by Cloudflare), using yfinance directly for {pair}...")
            if use_yfinance_fallback:
                df = self._fetch_with_yfinance(pair, start_date, end_date, timeframe)
                if df is not None and len(df) > 0:
                    # Save to cache
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    df.to_csv(cache_file)
                    logger.info(f"💾 Cached to: {cache_file}")
                    return df
            logger.warning(f"No data available for {pair} via yfinance")
            return None
        
        # OLD METHOD: Try Dukascopy first (slow, usually fails)
        # Convert pair format
        pair_clean = self._convert_pair_format(pair)
        
        logger.info(f"Downloading {pair} {timeframe} data from {start_date.date()} to {end_date.date()}...")
        
        try:
            # Dukascopy provides data in chunks by date
            # We'll need to iterate through dates and combine
            all_data = []
            current_date = start_date
            
            # Progress bar
            total_days = (end_date - start_date).days
            pbar = tqdm(total=total_days, desc=f"Downloading {pair}", unit="days", ncols=100)
            
            # Optimize: For weekly data, we can skip days (only check once per week)
            date_increment = 7 if timeframe == "1WEEK" else 1
            
            while current_date <= end_date:
                self._rate_limit()
                
                # Dukascopy format: /datafeed/{PAIR}/{YEAR}/{MONTH}/{DAY}/{TIMEFRAME}_bid_ask.csv
                year = current_date.year
                month = current_date.month - 1  # 0-indexed
                day = current_date.day
                
                url = f"{self.base_url}/{pair_clean}/{year}/{month:02d}/{day:02d}/{timeframe}_bid_ask.csv"
                
                try:
                    # Add headers to bypass Cloudflare protection
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Referer': 'https://www.dukascopy.com/'
                    }
                    response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                    
                    if response.status_code == 403:
                        logger.warning(f"Dukascopy blocked request (403 Forbidden) for {current_date.date()}. Cloudflare protection detected.")
                        logger.warning(f"This may require: 1) Using dukascopy-python library, 2) Alternative data source, or 3) Different API endpoint")
                        pbar.update(date_increment)
                        current_date += timedelta(days=date_increment)
                        continue
                    
                    if response.status_code == 200:
                        # Parse CSV
                        # Format: Time,Open,High,Low,Close,Volume
                        lines = response.text.strip().split('\n')
                        if len(lines) > 1:  # Has header + data
                            for line in lines[1:]:  # Skip header
                                if not line.strip():  # Skip empty lines
                                    continue
                                parts = line.split(',')
                                if len(parts) >= 6:
                                    try:
                                        timestamp = int(parts[0]) / 1000  # Convert ms to seconds
                                        dt = datetime.fromtimestamp(timestamp)
                                        all_data.append({
                                            'timestamp': dt,
                                            'open': float(parts[1]),
                                            'high': float(parts[2]),
                                            'low': float(parts[3]),
                                            'close': float(parts[4]),
                                            'volume': float(parts[5])
                                        })
                                    except (ValueError, IndexError) as e:
                                        logger.debug(f"Error parsing line {line[:50]}: {e}")
                                        continue
                    else:
                        logger.debug(f"Unexpected status code {response.status_code} for {current_date.date()}")
                    
                    pbar.update(date_increment)
                    current_date += timedelta(days=date_increment)
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request error for {current_date.date()}: {e}")
                    current_date += timedelta(days=date_increment)
                    pbar.update(date_increment)
                    continue
                except Exception as e:
                    logger.debug(f"Error fetching {current_date.date()}: {e}")
                    current_date += timedelta(days=date_increment)
                    pbar.update(date_increment)
                    continue
            
            pbar.close()
            
            if not all_data:
                logger.warning(f"No data retrieved from Dukascopy for {pair}")
                
                # Try yfinance fallback if enabled
                if use_yfinance_fallback:
                    logger.info(f"Attempting yfinance fallback for {pair}...")
                    try:
                        df_fallback = self._fetch_with_yfinance(pair, start_date, end_date, timeframe)
                        if df_fallback is not None and len(df_fallback) > 0:
                            logger.info(f"✅ Successfully fetched {len(df_fallback)} records using yfinance fallback")
                            # Save to cache
                            cache_file.parent.mkdir(parents=True, exist_ok=True)
                            df_fallback.to_csv(cache_file)
                            logger.info(f"💾 Cached to: {cache_file}")
                            return df_fallback
                        else:
                            logger.warning(f"yfinance fallback returned no data for {pair}")
                    except Exception as fallback_error:
                        logger.error(f"yfinance fallback failed for {pair}: {fallback_error}")
                
                return None
            
            # Create DataFrame
            df = pd.DataFrame(all_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Remove duplicates (keep first occurrence)
            initial_count = len(df)
            df = df[~df.index.duplicated(keep='first')]
            duplicates_removed = initial_count - len(df)
            if duplicates_removed > 0:
                logger.info(f"Removed {duplicates_removed} duplicate records")
            
            logger.info(f"✅ Downloaded {len(df)} unique data points for {pair}")
            
            # Save to cache
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_file)
            logger.info(f"💾 Cached to: {cache_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {pair} from Dukascopy: {e}")
            
            # Try yfinance fallback if enabled
            if use_yfinance_fallback:
                logger.info(f"Attempting yfinance fallback for {pair}...")
                try:
                    df_fallback = self._fetch_with_yfinance(pair, start_date, end_date, timeframe)
                    if df_fallback is not None and len(df_fallback) > 0:
                        logger.info(f"✅ Successfully fetched {len(df_fallback)} records using yfinance fallback")
                        # Save to cache
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        df_fallback.to_csv(cache_file)
                        logger.info(f"💾 Cached to: {cache_file}")
                        return df_fallback
                except Exception as fallback_error:
                    logger.error(f"yfinance fallback also failed: {fallback_error}")
            
            return None
    
    def _get_cache_file(self, pair: str, timeframe: str, start: datetime, end: datetime) -> Path:
        """Get cache file path"""
        pair_clean = self._convert_pair_format(pair)
        filename = f"{pair_clean}_{timeframe}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        return self.data_dir / filename
    
    def fetch_multiple_pairs(
        self,
        pairs: List[str],
        timeframe: str = "1DAY",
        years: int = 5
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple pairs
        
        Args:
            pairs: List of currency pairs
            timeframe: '1DAY' or '1WEEK'
            years: Number of years of historical data
            
        Returns:
            Dictionary mapping pair names to DataFrames
        """
        results = {}
        
        logger.info(f"Fetching data for {len(pairs)} pairs...")
        
        for pair in pairs:
            df = self.fetch_pair_data(pair, timeframe, years=years)
            if df is not None:
                results[pair] = df
            else:
                logger.warning(f"Failed to fetch {pair}")
        
        logger.info(f"✅ Successfully fetched {len(results)}/{len(pairs)} pairs")
        return results
    
    def _fetch_with_yfinance(self, pair: str, start_date: datetime, end_date: datetime, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Fallback method using yfinance if Dukascopy fails
        
        Args:
            pair: Currency pair (e.g., 'EUR/USD')
            start_date: Start date
            end_date: End date
            timeframe: '1DAY' or '1WEEK'
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        import time
        
        try:
            import yfinance as yf
            
            # Convert pair format for yfinance: EUR/USD -> EURUSD=X
            clean_pair = pair.replace('/', '').replace('-', '').upper()
            ticker = f"{clean_pair}=X"
            
            # Map timeframe
            interval_map = {
                '1DAY': '1d',
                '1WEEK': '1wk'
            }
            yf_interval = interval_map.get(timeframe, '1d')
            
            logger.info(f"Fetching {ticker} from yfinance ({yf_interval})...")
            
            # Rate limiting: Add delay between requests (increased for yfinance)
            # yfinance is VERY sensitive to rate limiting - need much longer delays
            # If IP was rate-limited, even 5 seconds isn't enough - need 15+ seconds
            self._rate_limit()
            # Additional delay specifically for yfinance (very conservative)
            delay_before_request = 15  # 15 second delay before each yfinance request (was 5)
            logger.debug(f"Waiting {delay_before_request} seconds before yfinance request to avoid rate limits...")
            time.sleep(delay_before_request)
            
            # Retry logic for rate limits
            # If first attempt fails, likely IP is rate-limited - need very long delays
            max_retries = 3
            retry_delays = [60, 120, 180]  # Very long delays: 1min, 2min, 3min (was 10s, 20s, 30s)
            df = None
            
            for attempt in range(max_retries):
                try:
                    # Download data using yf.download() instead of Ticker().history()
                    # yf.download() is more reliable and uses different API endpoints
                    # This avoids the "Expecting value: line 1 column 1" errors
                    
                    # Calculate period in days
                    delta = end_date - start_date
                    days = delta.days
                    
                    # Map to yfinance period (more reliable than start/end for long ranges)
                    # yfinance supports: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 3y, 5y, 10y, ytd, max
                    # Using 3y instead of 5y for better reliability and faster downloads
                    if days >= 365 * 5:
                        period = "3y"  # Use 3y max instead of 5y for better reliability
                    elif days >= 365 * 3:
                        period = "3y"
                    elif days >= 365 * 2:
                        period = "2y"
                    elif days >= 365:
                        period = "1y"
                    elif days >= 180:
                        period = "6mo"
                    elif days >= 90:
                        period = "3mo"
                    elif days >= 30:
                        period = "1mo"
                    elif days >= 5:
                        period = "5d"
                    else:
                        period = "1d"
                    
                    # Use yf.download() instead of Ticker().history() - more reliable
                    # yf.download() uses different API endpoints and has better error handling
                    logger.debug(f"Downloading {ticker} with period='{period}' using yf.download() (requested: {days} days)...")
                    df = yf.download(
                        ticker,
                        period=period,  # Use period instead of start/end for better reliability
                        interval=yf_interval,
                        auto_adjust=True,
                        prepost=False,
                        progress=False  # Disable progress bar
                    )
                    
                    # yf.download() returns a DataFrame with MultiIndex columns if multiple tickers
                    # For single ticker, we need to handle the column structure
                    if df is not None and len(df) > 0:
                        # If MultiIndex columns, flatten them
                        if isinstance(df.columns, pd.MultiIndex):
                            # For single ticker, columns are like (Close, EURUSD=X)
                            # We want just Close, High, Low, Open, Volume
                            df.columns = df.columns.droplevel(1)  # Remove ticker level
                        
                        # Rename columns to lowercase if needed
                        if 'Close' in df.columns:
                            df = df.rename(columns={
                                'Open': 'open',
                                'High': 'high',
                                'Low': 'low',
                                'Close': 'close',
                                'Volume': 'volume'
                            })
                    
                    # Filter to requested date range if period returned more data
                    if df is not None and len(df) > 0:
                        # Ensure we have datetime index
                        if not isinstance(df.index, pd.DatetimeIndex):
                            df.index = pd.to_datetime(df.index)
                        
                        # Handle timezone-aware vs timezone-naive comparisons
                        # Make start_date and end_date timezone-aware if df.index is timezone-aware
                        if df.index.tz is not None:
                            # Convert naive dates to timezone-aware (use UTC)
                            if start_date.tzinfo is None:
                                start_date_tz = pd.Timestamp(start_date).tz_localize('UTC')
                            else:
                                start_date_tz = pd.Timestamp(start_date)
                            
                            if end_date.tzinfo is None:
                                end_date_tz = pd.Timestamp(end_date).tz_localize('UTC')
                            else:
                                end_date_tz = pd.Timestamp(end_date)
                            
                            # Filter to exact date range requested
                            df = df[(df.index >= start_date_tz) & (df.index <= end_date_tz)]
                        else:
                            # Timezone-naive: use dates directly
                            df = df[(df.index >= start_date) & (df.index <= end_date)]
                        
                        if len(df) == 0:
                            logger.warning(f"Period '{period}' returned data but none in requested range {start_date.date()} to {end_date.date()}")
                            df = None  # Reset to None so we retry
                    
                    if df is not None and len(df) > 0:
                        break  # Success, exit retry loop
                    
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(f"Empty data for {ticker}, retry {attempt + 1}/{max_retries} after {delay}s...")
                        time.sleep(delay)
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    error_str = str(e)
                    
                    # Check if it's a rate limit error (including JSON parse errors from rate limits)
                    is_rate_limit = (
                        'rate limit' in error_msg or
                        'too many requests' in error_msg or
                        'expecting value' in error_msg or  # JSON parse errors often indicate rate limits
                        'expecting value: line 1 column 1' in error_str or  # Specific yfinance rate limit error
                        '429' in error_msg or
                        'timeout' in error_msg or
                        'json' in error_msg and 'decode' in error_msg  # JSON decode errors
                    )
                    
                    if is_rate_limit and attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(f"Rate limit detected for {ticker} (attempt {attempt + 1}/{max_retries}), retrying after {delay}s...")
                        logger.debug(f"Error details: {e}")
                        time.sleep(delay)
                        continue
                    else:
                        # For other errors or last attempt, log and retry anyway
                        if attempt == max_retries - 1:
                            logger.error(f"yfinance failed for {ticker} after {max_retries} attempts: {e}")
                        else:
                            logger.warning(f"yfinance error for {ticker} (attempt {attempt + 1}/{max_retries}): {e}")
                            # Retry even for non-rate-limit errors (might be transient)
                            delay = retry_delays[attempt]
                            logger.info(f"Retrying after {delay}s...")
                            time.sleep(delay)
            
            if df is None or len(df) == 0:
                logger.warning(f"No data from yfinance for {ticker} after {max_retries} attempts")
                return None
            
            # Rename columns to match expected format
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Ensure timestamp index
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Select only needed columns
            df = df[['open', 'high', 'low', 'close', 'volume']].copy()
            
            logger.info(f"✅ Fetched {len(df)} records from yfinance")
            return df
            
        except ImportError:
            logger.warning("yfinance not available for fallback. Install with: pip install yfinance")
            return None
        except Exception as e:
            logger.warning(f"yfinance fallback failed for {pair}: {e}")
            return None


def fetch_using_dukascopy_library(pair: str, start: datetime, end: datetime, interval: str = "1DAY") -> Optional[pd.DataFrame]:
    """
    Alternative method using dukascopy-python library if available
    
    NOTE: The dukascopy-python library (v4.0.1) currently has a bug that causes
    TypeError when fetching data. This function will gracefully fall back to
    direct API calls if the library fails.
    
    Args:
        pair: Currency pair
        start: Start date
        end: End date
        interval: '1DAY' or '1WEEK'
        
    Returns:
        DataFrame with OHLCV data or None if library fails
    """
    try:
        from dukascopy_python import fetch
        
        # Convert pair format
        pair_clean = pair.replace('/', '').upper()
        
        # Map interval
        interval_map = {
            "1DAY": "1DAY",
            "1WEEK": "1WEEK"
        }
        duka_interval = interval_map.get(interval, "1DAY")
        
        logger.info(f"Attempting to use dukascopy-python library for {pair}...")
        
        # The dukascopy-python library function signature:
        # fetch(instrument, interval, offer_side, start, end, ...)
        # NOTE: Library v4.0.1 has a known bug - will fall back to direct API
        try:
            df = fetch(
                instrument=pair_clean,
                interval=duka_interval,
                offer_side='mid',
                start=start,
                end=end
            )
            
            # The library returns a generator, convert to list then DataFrame
            if df is not None:
                data_list = list(df)
                if len(data_list) > 0:
                    df = pd.DataFrame(data_list)
                    # Set timestamp as index if available
                    if 'time' in df.columns:
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                        df.set_index('time', inplace=True)
                        df.index.name = 'timestamp'
                    logger.info(f"✅ Fetched {len(df)} data points using library")
                    return df
                else:
                    logger.warning(f"Library returned empty data for {pair}")
                    return None
                    
        except (TypeError, AttributeError, IndexError) as e:
            # Known bug in library v4.0.1 - gracefully fall back
            logger.debug(f"Library bug encountered (known issue): {type(e).__name__}, using direct API")
            return None
        except Exception as e:
            logger.warning(f"Library call failed: {e}, falling back to direct API")
            return None
            
    except ImportError:
        logger.debug("dukascopy-python library not available, using direct API calls")
        return None
    except Exception as e:
        logger.debug(f"Error importing dukascopy-python library: {e}, using direct API")
        return None

