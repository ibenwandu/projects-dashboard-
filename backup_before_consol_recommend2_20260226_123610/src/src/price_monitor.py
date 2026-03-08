"""Monitor real-time currency prices using OANDA API (primary) or Frankfurter.app (fallback)"""

import os
import requests
from typing import Optional, Dict
from dotenv import load_dotenv
from src.logger import setup_logger
import yfinance as yf
import pandas as pd

load_dotenv()
logger = setup_logger()

class PriceMonitor:
    """Monitor current market prices using OANDA API (primary) or Frankfurter.app (fallback)"""
    
    def __init__(self):
        """Initialize price monitor"""
        # Try to initialize OANDA API (primary source for live prices)
        self.oanda_client = None
        self.oanda_account_id = None
        try:
            from oandapyV20 import API
            from oandapyV20.endpoints import pricing
            
            access_token = os.getenv('OANDA_ACCESS_TOKEN')
            account_id = os.getenv('OANDA_ACCOUNT_ID')
            environment = os.getenv('OANDA_ENV', 'practice')
            
            if access_token and account_id:
                self.oanda_client = API(access_token=access_token, environment=environment)
                self.oanda_account_id = account_id
                self.pricing_endpoint = pricing
                logger.info("✅ PriceMonitor: OANDA API initialized (primary source for live prices)")
            else:
                logger.warning("⚠️ PriceMonitor: OANDA credentials not available, using Frankfurter.app fallback")
        except ImportError:
            logger.warning("⚠️ PriceMonitor: oandapyV20 not available, using Frankfurter.app fallback")
        except Exception as e:
            logger.warning(f"⚠️ PriceMonitor: Failed to initialize OANDA API: {e}, using Frankfurter.app fallback")
        
        # Frankfurter.app API (fallback, free, no API key needed)
        # Documentation: https://www.frankfurter.app/
        self.base_url = 'https://api.frankfurter.app/latest'
        self.cache = {}
        self.cache_time = 0
        self.cache_ttl = 60  # Cache for 60 seconds
        
        # ATR cache for dynamic tolerance calculation
        self.atr_cache = {}
        self.atr_cache_ttl = 3600  # Cache ATR for 1 hour
    
    def get_rate(self, pair: str) -> Optional[float]:
        """
        Get current exchange rate for a currency pair using OANDA API (primary) or Frankfurter.app (fallback)
        
        Args:
            pair: Currency pair (e.g., 'EUR/USD')
            
        Returns:
            Exchange rate or None if failed
        """
        # Try OANDA API first (most accurate, live prices)
        if self.oanda_client and self.oanda_account_id:
            try:
                rate = self._get_oanda_rate(pair)
                if rate:
                    return rate
            except Exception as e:
                logger.debug(f"OANDA API failed for {pair}: {e}, falling back to Frankfurter.app")
        
        # Fallback to Frankfurter.app
        try:
            # Normalize pair
            base, quote = pair.split('/')
            
            # Frankfurter.app uses EUR as base, so we need to convert
            # For pairs with EUR, get directly
            if base == 'EUR':
                rate = self._get_frankfurter_rate('EUR', quote)
                return rate if rate else None
            elif quote == 'EUR':
                rate = self._get_frankfurter_rate('EUR', base)
                return 1.0 / rate if rate else None
            else:
                # Cross rate: XXX/YYY = (EUR/YYY) / (EUR/XXX)
                rate_base = self._get_frankfurter_rate('EUR', base)
                rate_quote = self._get_frankfurter_rate('EUR', quote)
                if rate_base and rate_quote:
                    return rate_quote / rate_base
                return None
        except Exception as e:
            logger.error(f"Error getting rate for {pair}: {e}")
            return None
    
    def _get_oanda_rate(self, pair: str) -> Optional[float]:
        """Get exchange rate from OANDA API (live prices) with retry logic"""
        import time

        # Check cache first
        cache_key = f"oanda_{pair}"
        current_time = time.time()
        if cache_key in self.cache and (current_time - self.cache_time) < self.cache_ttl:
            return self.cache[cache_key]

        # Convert pair format: EUR/USD -> EUR_USD for OANDA
        oanda_pair = pair.replace('/', '_').replace('-', '_')

        # Retry logic for transient errors (5xx, 429)
        # Increased to 3 attempts to handle OANDA intermittent 500 errors
        max_attempts = 3
        last_exception = None

        for attempt in range(max_attempts):
            try:
                # Get pricing from OANDA
                params = {"instruments": oanda_pair}
                req = self.pricing_endpoint.PricingInfo(accountID=self.oanda_account_id, params=params)
                self.oanda_client.request(req)

                response = req.response
                if 'prices' in response and len(response['prices']) > 0:
                    price_data = response['prices'][0]
                    bid = float(price_data['bids'][0]['price'])
                    ask = float(price_data['asks'][0]['price'])
                    mid = (bid + ask) / 2

                    # Update cache
                    self.cache[cache_key] = mid
                    self.cache_time = current_time

                    logger.debug(f"✅ OANDA: {pair} = {mid:.5f} (bid: {bid:.5f}, ask: {ask:.5f})")
                    return mid
                else:
                    logger.warning(f"OANDA: No price data for {pair}")
                    return None

            except Exception as e:
                last_exception = e
                error_msg = str(e)
                status_code = self._get_http_status(e)

                # Check if this is a retryable error (5xx or 429)
                is_retryable = self._is_retryable_http(status_code)

                if is_retryable and attempt < max_attempts - 1:
                    # Log at debug level for retryable errors (they'll succeed on retry)
                    logger.debug(
                        f"OANDA error for {pair} (HTTP {status_code}): {error_msg}. "
                        f"Retrying (attempt {attempt + 1}/{max_attempts})"
                    )
                    # Exponential backoff: 1s for first retry, 2s for second
                    time.sleep(1 * (attempt + 1))
                else:
                    # Non-retryable error or last attempt
                    logger.debug(f"Error fetching rate from OANDA for {pair}: {error_msg}")
                    return None

        # Final attempt failed
        if last_exception:
            logger.debug(f"OANDA rate fetch for {pair} failed after {max_attempts} attempts")
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
    
    def _get_frankfurter_rate(self, base: str, quote: str) -> Optional[float]:
        """Get exchange rate from Frankfurter.app"""
        import time
        
        # Check cache
        cache_key = f"{base}/{quote}"
        current_time = time.time()
        if cache_key in self.cache and (current_time - self.cache_time) < self.cache_ttl:
            return self.cache[cache_key]
        
        try:
            # Frankfurter.app: https://api.frankfurter.app/latest?from=EUR&to=USD
            url = f"{self.base_url}?from={base}&to={quote}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and quote in data['rates']:
                rate = float(data['rates'][quote])
                # Update cache
                self.cache[cache_key] = rate
                self.cache_time = current_time
                return rate
            else:
                logger.warning(f"Rate {base}/{quote} not found in API response")
        except Exception as e:
            logger.error(f"Error fetching rate from Frankfurter.app: {e}")
        
        return None
    
    def get_atr(self, pair: str, period: int = 14) -> float:
        """
        Calculate Daily ATR (Average True Range) for dynamic tolerance sizing
        
        Args:
            pair: Currency pair (e.g., 'EUR/USD')
            period: ATR period (default: 14)
            
        Returns:
            ATR value in absolute terms (same units as price)
        """
        import time
        
        # Check cache first
        cache_key = f"{pair}_{period}"
        current_time = time.time()
        if cache_key in self.atr_cache:
            cached_atr, cached_time = self.atr_cache[cache_key]
            if (current_time - cached_time) < self.atr_cache_ttl:
                return cached_atr
        
        try:
            # Convert pair format for yfinance: EUR/USD -> EURUSD=X (strip whitespace to avoid "possibly delisted")
            clean_pair = (pair or '').strip().replace('/', '').replace('-', '').replace(' ', '')
            if not clean_pair:
                return 0.0010
            ticker = f"{clean_pair}=X"
            df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
            if df is None or df.empty or len(df) < period:
                logger.warning(f"Insufficient data for ATR calculation for {pair}, using fallback")
                return 0.0010  # Fallback to 10 pips equivalent
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            # Calculate True Range
            high_low = df['High'] - df['Low']
            high_close = abs(df['High'] - df['Close'].shift())
            low_close = abs(df['Low'] - df['Close'].shift())
            
            # True Range is the maximum of the three
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # ATR is the rolling mean of True Range
            atr = tr.rolling(window=period).mean().iloc[-1]
            
            # Handle NaN or invalid values
            if pd.isna(atr) or atr <= 0:
                logger.warning(f"Invalid ATR for {pair}, using fallback")
                return 0.0010
            
            # Cache the result
            self.atr_cache[cache_key] = (atr, current_time)
            
            logger.debug(f"ATR for {pair}: {atr:.6f}")
            return float(atr)
            
        except Exception as e:
            logger.warning(f"Failed to calculate ATR for {pair}: {e}, using fallback")
            return 0.0010  # Fallback default (10 pips equivalent)
    
    def check_entry_point(self, pair: str, entry_price: float, direction: str,
                         tolerance_pips: Optional[float] = None, 
                         tolerance_percent: float = 0.1,
                         confidence_score: float = 0.75,
                         timeframe: str = 'INTRADAY') -> bool:
        """
        Check if current price has hit entry point using dynamic ATR-based tolerance
        
        Logic Update + Rec 1: Uses ATR for physics, Confidence for tolerance scaling, and Timeframe for different rules.
        
        Args:
            pair: Currency pair
            entry_price: Target entry price
            direction: 'BUY' or 'SELL'
            tolerance_pips: Tolerance in pips (optional, overrides ATR if provided)
            tolerance_percent: Tolerance as percentage (default: 0.1%)
            confidence_score: Confidence score from LLM (0.0-1.0, default: 0.75)
                              High confidence (>0.8) widens tolerance by 50%
            timeframe: 'INTRADAY' or 'SWING' (default: 'INTRADAY')
                       INTRADAY: Wider tolerance (ATR x 0.5) - needs to trigger fast
                       SWING: Stricter tolerance (ATR x 0.1) - can wait for perfect entry
            
        Returns:
            True if entry point is hit
        """
        current_price = self.get_rate(pair)
        if not current_price:
            return False
        
        # Step 1: Get Base Physics (ATR-based tolerance) - Different rules for different timeframes
        if tolerance_pips is None:
            # Use ATR-based dynamic tolerance (Logic Update)
            atr = self.get_atr(pair)
            
            # Different Physics for Different Timeframes
            if timeframe.upper() == 'INTRADAY':
                # Wider tolerance to ensure we get in - we don't want to miss a 30-pip move waiting for 2 pips
                base_tolerance = atr * 0.5  # 50% of ATR for intraday
            elif timeframe.upper() == 'SWING':
                # Stricter tolerance - we can afford to wait for the perfect entry for a multi-day hold
                base_tolerance = atr * 0.1  # 10% of ATR for swing
            else:
                # Default to moderate tolerance
                base_tolerance = atr * 0.20  # 20% of ATR default
        else:
            # Fallback to fixed pips if provided
            if 'JPY' in pair:
                pip_value = 0.01
            else:
                pip_value = 0.0001
            base_tolerance = tolerance_pips * pip_value
        
        # Step 2: Apply RL Intelligence (Rec 1)
        # If confidence is high (>0.8), widen the net by 50%
        confidence_multiplier = 1.5 if confidence_score > 0.8 else 1.0
        
        # Step 3: Calculate final tolerance
        final_tolerance = base_tolerance * confidence_multiplier
        
        # Also consider percentage-based tolerance as minimum
        percent_tolerance = entry_price * (tolerance_percent / 100.0)
        final_tolerance = max(final_tolerance, percent_tolerance)
        
        # Check Entry
        if direction.upper() in ['BUY', 'LONG']:
            # For BUY, price should be at or below entry + tolerance
            hit = current_price <= (entry_price + final_tolerance)
            logger.debug(
                f"{pair} BUY check ({timeframe}): current={current_price:.5f}, entry={entry_price:.5f}, "
                f"tolerance={final_tolerance:.5f} (ATR-based, timeframe={timeframe}, conf={confidence_score:.2f}), hit={hit}"
            )
        else:  # SELL or SHORT
            # For SELL, price should be at or above entry - tolerance
            hit = current_price >= (entry_price - final_tolerance)
            logger.debug(
                f"{pair} SELL check ({timeframe}): current={current_price:.5f}, entry={entry_price:.5f}, "
                f"tolerance={final_tolerance:.5f} (ATR-based, timeframe={timeframe}, conf={confidence_score:.2f}), hit={hit}"
            )
        
        return hit
