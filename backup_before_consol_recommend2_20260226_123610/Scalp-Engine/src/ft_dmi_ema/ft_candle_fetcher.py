"""
Robust candle fetcher for FT-DMI-EMA with proper error handling and rate limiting

This fixes the 500 error issue caused by Cursor's broken SimpleOandaWrapper implementation.
"""

import time
import pandas as pd
from typing import Optional, Tuple
from oandapyV20.endpoints import instruments
import logging

logger = logging.getLogger(__name__)


class FTCandleFetcher:
    """
    Fetch candles with retry logic and rate limiting

    This class replaces the broken SimpleOandaWrapper that was causing 500 errors.
    It uses the raw OANDA API directly with proper error handling.
    """

    def __init__(self, oanda_api, account_id):
        """
        Initialize with OANDA API client

        Args:
            oanda_api: oandapyV20.API instance
            account_id: OANDA account ID
        """
        self.api = oanda_api
        self.account_id = account_id
        self.request_delay = 0.5  # 500ms between requests to avoid rate limiting
        self.last_request_time = 0
        logger.info("✅ FTCandleFetcher initialized with rate limiting (500ms between requests)")

    def get_candles(
        self,
        instrument: str,
        granularity: str,
        count: int = 500
    ) -> Optional[list]:
        """
        Fetch candles with rate limiting and retry logic for transient errors

        Args:
            instrument: OANDA format (e.g., EUR_USD)
            granularity: M15, H1, H4, etc.
            count: Number of candles (default 500)

        Returns:
            List of candle dicts with OHLCV data, or None on error
        """
        # Retry logic for transient errors (5xx, 429)
        # Increased to 3 attempts to handle OANDA intermittent 500 errors
        max_attempts = 3
        last_exception = None

        for attempt in range(max_attempts):
            # Rate limiting: ensure minimum delay between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.request_delay:
                sleep_time = self.request_delay - time_since_last
                time.sleep(sleep_time)

            try:
                params = {
                    "count": count,
                    "granularity": granularity,
                    "price": "M"  # Mid prices
                }

                r = instruments.InstrumentsCandles(
                    instrument=instrument,
                    params=params
                )

                # Make the request - this is where the 500 error was happening
                self.api.request(r)
                self.last_request_time = time.time()

                # Extract and validate candles
                candles = []
                raw_candles = r.response.get('candles', [])

                if not raw_candles:
                    logger.warning(f"⚠️ {instrument} @ {granularity}: OANDA returned empty candle list")
                    return None

                for candle in raw_candles:
                    # Only include complete candles
                    if not candle.get('complete', False):
                        continue

                    try:
                        # Extract OHLCV data
                        mid_data = candle.get('mid', {})
                        if not mid_data:
                            logger.warning(f"Skipping candle with no mid data for {instrument}")
                            continue

                        candles.append({
                            'time': candle['time'],
                            'open': float(mid_data['o']),
                            'high': float(mid_data['h']),
                            'low': float(mid_data['l']),
                            'close': float(mid_data['c']),
                            'volume': int(candle.get('volume', 0))
                        })
                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(f"Skipping malformed candle for {instrument}: {e}")
                        continue

                if not candles:
                    logger.warning(f"⚠️ {instrument} @ {granularity}: No valid candles after filtering")
                    return None

                logger.debug(f"✅ Fetched {len(candles)} candles for {instrument} @ {granularity}")
                return candles

            except Exception as e:
                last_exception = e
                error_msg = str(e)
                status_code = self._get_http_status(e)

                # Check if this is a retryable error (5xx or 429)
                is_retryable = self._is_retryable_http(status_code)

                if is_retryable and attempt < max_attempts - 1:
                    # Log at debug level for retryable errors (they'll succeed on retry)
                    logger.debug(
                        f"{instrument} @ {granularity}: Transient error (HTTP {status_code}). "
                        f"Retrying (attempt {attempt + 1}/{max_attempts})"
                    )
                    # Exponential backoff: 2s for first retry, 4s for second
                    time.sleep(2 * (attempt + 1))
                    continue

                # Non-retryable error - log with full context
                if '500' in error_msg or 'HTML' in error_msg or '<!DOCTYPE' in error_msg:
                    logger.error(
                        f"❌ {instrument} @ {granularity}: OANDA API returned HTML error page (500). "
                        f"Possible causes: "
                        f"1) Invalid instrument name (check format: EUR_USD not EUR/USD), "
                        f"2) Wrong environment (practice vs live mismatch), "
                        f"3) OANDA API outage. "
                        f"Error: {error_msg[:200]}"
                    )
                elif '404' in error_msg:
                    logger.error(
                        f"❌ {instrument} @ {granularity}: Instrument not found (404). "
                        f"Check that {instrument} is available on your OANDA account."
                    )
                elif '401' in error_msg or '403' in error_msg:
                    logger.error(
                        f"❌ {instrument} @ {granularity}: Authentication failed ({error_msg}). "
                        f"Check your OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID."
                    )
                elif 'rate limit' in error_msg.lower() or '429' in error_msg:
                    logger.error(
                        f"❌ {instrument} @ {granularity}: Rate limit exceeded. "
                        f"Consider increasing request_delay or reducing monitored pairs."
                    )
                else:
                    logger.error(f"❌ {instrument} @ {granularity}: {error_msg}")

                return None

        # Final attempt failed
        if last_exception:
            logger.debug(f"Candle fetch for {instrument} @ {granularity} failed after {max_attempts} attempts")
        return None

    def _get_http_status(self, e: Exception) -> Optional[int]:
        """Extract HTTP status code from exception if present"""
        resp = getattr(e, "response", None)
        if resp is not None:
            return getattr(resp, "status_code", None)
        return None

    def _is_retryable_http(self, status: Optional[int]) -> bool:
        """True for 5xx and 429 (transient/server/rate-limit)"""
        if status is None:
            return True  # Unknown - retry once
        return 429 == status or (500 <= status < 600)

    def fetch_multi_timeframe(
        self,
        instrument: str,
        granularities: list = None,
        count: int = 500
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Fetch multiple timeframes with rate limiting

        Args:
            instrument: OANDA format (e.g., EUR_USD)
            granularities: List of granularities (default: ["M15", "H1", "H4"])
            count: Number of candles per timeframe

        Returns:
            Tuple of (data_15m, data_1h, data_4h) DataFrames
            Any timeframe can be None if fetching failed
        """
        if granularities is None:
            granularities = ["M15", "H1", "H4"]

        results = []

        for gran in granularities:
            candles = self.get_candles(instrument, gran, count)

            if candles:
                df = self._candles_to_dataframe(candles, instrument, gran)
                results.append(df)
            else:
                results.append(None)

        # Ensure we always return a 3-tuple
        while len(results) < 3:
            results.append(None)

        return tuple(results[:3])

    def _candles_to_dataframe(
        self,
        candles: list,
        instrument: str,
        granularity: str
    ) -> Optional[pd.DataFrame]:
        """
        Convert candle list to validated DataFrame

        Args:
            candles: List of candle dicts
            instrument: Instrument name (for logging)
            granularity: Granularity (for logging)

        Returns:
            pandas DataFrame or None if conversion fails
        """
        try:
            df = pd.DataFrame(candles)

            # Ensure required columns exist
            required = ['open', 'high', 'low', 'close']
            missing = [col for col in required if col not in df.columns]

            if missing:
                logger.error(
                    f"❌ {instrument} @ {granularity}: Missing columns {missing}. "
                    f"Available: {df.columns.tolist()}"
                )
                return None

            # Convert to numeric (handle any string values)
            for col in required:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop rows with NaN values
            original_len = len(df)
            df = df.dropna(subset=required)

            if len(df) < original_len:
                logger.warning(
                    f"⚠️ {instrument} @ {granularity}: Dropped {original_len - len(df)} "
                    f"rows with invalid data"
                )

            if len(df) == 0:
                logger.error(f"❌ {instrument} @ {granularity}: All rows invalid after cleaning")
                return None

            logger.debug(
                f"✅ {instrument} @ {granularity}: Converted {len(df)} candles to DataFrame"
            )
            return df

        except Exception as e:
            logger.error(
                f"❌ {instrument} @ {granularity}: Error converting to DataFrame: {e}"
            )
            return None


# Convenience function for backward compatibility with fetch_ft_dmi_ema_dataframes
def fetch_ft_dmi_ema_dataframes_fixed(
    oanda_api,
    account_id: str,
    instrument: str,
    count: int = 500
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Convenience wrapper matching the old fetch_ft_dmi_ema_dataframes signature

    Args:
        oanda_api: oandapyV20.API instance
        account_id: OANDA account ID
        instrument: OANDA instrument (e.g., EUR_USD)
        count: Number of candles

    Returns:
        Tuple of (data_15m, data_1h, data_4h)
    """
    fetcher = FTCandleFetcher(oanda_api, account_id)
    return fetcher.fetch_multi_timeframe(instrument, count=count)
