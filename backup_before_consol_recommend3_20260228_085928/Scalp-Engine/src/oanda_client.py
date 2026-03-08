"""
OANDA API client for live prices and order execution
"""

import oandapyV20
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.instruments as instruments
from oandapyV20.contrib.requests import MarketOrderRequest, TakeProfitDetails, StopLossDetails
from typing import Dict, Optional, List
import time
import logging
import os

def _sanitize_error(e: Exception, max_len: int = 200) -> str:
    """Avoid logging full HTML/response bodies (e.g. 500 error pages)."""
    s = str(e).strip()
    if not s:
        return type(e).__name__
    if s.lstrip().startswith("<") or "DOCTYPE" in s or "<html" in s.lower():
        return "API returned non-JSON response (e.g. 500/HTML error page)"
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def _get_http_status(e: Exception) -> Optional[int]:
    """Extract HTTP status code from exception if present (e.g. requests.HTTPError or oandapyV20 wrapper)."""
    resp = getattr(e, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    return None


def _is_retryable_http(status: Optional[int]) -> bool:
    """True for 5xx and 429 (transient/server/rate-limit)."""
    if status is None:
        return True  # Unknown - retry once
    return 429 == status or (500 <= status < 600)


# Throttle: delay between Oanda API calls to avoid 500/429 from rate limits or proxy
def _request_delay_sec() -> float:
    try:
        return max(0.0, min(2.0, float(os.getenv("OANDA_REQUEST_DELAY_SEC", "0.35").strip() or "0.35")))
    except (ValueError, TypeError):
        return 0.35


# Dedupe error logs: only log ERROR once per instrument per 5 min; repeat failures at DEBUG
_last_candle_error: Dict[str, float] = {}
_last_price_error: Dict[str, float] = {}
_ERROR_LOG_INTERVAL_SEC = 300  # 5 minutes


def _should_log_error(inst: str, last_map: Dict[str, float]) -> bool:
    now = time.time()
    last = last_map.get(inst, 0)
    if now - last >= _ERROR_LOG_INTERVAL_SEC:
        last_map[inst] = now
        return True
    return False


logger = logging.getLogger("OandaClient")

class OandaClient:
    """OANDA API wrapper for scalping operations"""
    
    def __init__(self, access_token: str, account_id: str, environment: str = "practice"):
        """
        Initialize OANDA client
        
        Args:
            access_token: OANDA API access token
            account_id: OANDA account ID
            environment: "practice" or "live"
        """
        self.client = oandapyV20.API(access_token=access_token, environment=environment)
        self.account_id = account_id
        self.environment = environment
        
    def get_current_price(self, instrument: str) -> Optional[Dict]:
        """Get current bid/ask price for instrument. Retries once on 5xx or 429."""
        last_e = None
        for attempt in range(2):
            try:
                params = {"instruments": instrument}
                r = pricing.PricingInfo(accountID=self.account_id, params=params)
                self.client.request(r)
                if 'prices' in r.response and len(r.response['prices']) > 0:
                    price_data = r.response['prices'][0]
                    bid = float(price_data['bids'][0]['price'])
                    ask = float(price_data['asks'][0]['price'])
                    spread = (ask - bid) * 10000  # Convert to pips
                    return {
                        'bid': bid,
                        'ask': ask,
                        'spread': spread,
                        'instrument': instrument,
                        'time': price_data.get('time')
                    }
                return None
            except Exception as e:
                last_e = e
                status = _get_http_status(e)
                do_log = _should_log_error(instrument, _last_price_error)
                msg = (
                    "Error getting price for %s: HTTP %s - %s%s" if status is not None
                    else "Error getting price for %s: %s"
                )
                args = (
                    (instrument, status, _sanitize_error(e), " (retrying once)" if attempt == 0 and _is_retryable_http(status) else "")
                    if status is not None else (instrument, _sanitize_error(e))
                )
                if do_log:
                    logger.error(msg, *args)
                else:
                    logger.debug(msg, *args)
                if attempt == 0 and _is_retryable_http(status):
                    time.sleep(2)
                    continue
                return None
        return None
    
    def get_candles(self, instrument: str, granularity: str = "M1", count: int = 100) -> Optional[List[Dict]]:
        """
        Get historical candles for indicator calculation.
        Retries once on 5xx or 429 (transient/server/rate-limit).
        """
        params = {
            "count": count,
            "granularity": granularity,
            "price": "M"  # Midpoint price
        }
        last_e = None
        for attempt in range(2):
            try:
                r = instruments.InstrumentsCandles(instrument=instrument, params=params)
                self.client.request(r)
                candles = []
                for candle in r.response.get('candles', []):
                    if candle.get('complete', False):
                        candles.append({
                            'time': candle['time'],
                            'open': float(candle['mid']['o']),
                            'high': float(candle['mid']['h']),
                            'low': float(candle['mid']['l']),
                            'close': float(candle['mid']['c']),
                            'volume': int(candle.get('volume', 0))
                        })
                return candles
            except Exception as e:
                last_e = e
                status = _get_http_status(e)
                do_log = _should_log_error(instrument, _last_candle_error)
                msg = (
                    "Error getting candles for %s: HTTP %s - %s%s" if status is not None
                    else "Error getting candles for %s: %s"
                )
                args = (
                    (instrument, status, _sanitize_error(e), " (retrying once)" if attempt == 0 and _is_retryable_http(status) else "")
                    if status is not None else (instrument, _sanitize_error(e))
                )
                if do_log:
                    logger.error(msg, *args)
                else:
                    logger.debug(msg, *args)
                if attempt == 0 and _is_retryable_http(status):
                    time.sleep(2)
                    continue
                return None
        if last_e is not None:
            status = _get_http_status(last_e)
            do_log = _should_log_error(instrument, _last_candle_error)
            if do_log:
                if status is not None:
                    logger.error("Error getting candles for %s: HTTP %s after retry", instrument, status)
                else:
                    logger.error("Error getting candles for %s: %s", instrument, _sanitize_error(last_e))
            else:
                logger.debug("Error getting candles for %s after retry", instrument)
        return None
    
    def place_market_order(
        self,
        instrument: str,
        units: int,
        stop_loss_pips: float,
        take_profit_pips: float
    ) -> Optional[Dict]:
        """
        Place market order with stop loss and take profit
        
        Args:
            instrument: OANDA instrument (e.g., "EUR_USD")
            units: Positive for long, negative for short
            stop_loss_pips: Stop loss distance in pips
            take_profit_pips: Take profit distance in pips
            
        Returns:
            Order response or None if error
        """
        try:
            # Convert pips to price distance
            # For most pairs, 1 pip = 0.0001, for JPY pairs, 1 pip = 0.01
            pip_value = 0.0001 if "JPY" not in instrument else 0.01
            
            sl_distance = str(stop_loss_pips * pip_value)
            tp_distance = str(take_profit_pips * pip_value)
            
            mo = MarketOrderRequest(
                instrument=instrument,
                units=units,
                takeProfitOnFill=TakeProfitDetails(distance=tp_distance).data,
                stopLossOnFill=StopLossDetails(distance=sl_distance).data
            )
            
            r = orders.OrderCreate(accountID=self.account_id, data=mo.data)
            self.client.request(r)
            
            return r.response
        except Exception as e:
            logger.error("Error placing order for %s: %s", instrument, _sanitize_error(e))
            return None
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information including balance"""
        try:
            from oandapyV20.endpoints.accounts import AccountDetails
            r = AccountDetails(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('account', {})
        except Exception as e:
            print(f"Error getting account info: {e}")
            return None
    
    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions
        
        Returns:
            List of position dictionaries
        """
        try:
            from oandapyV20.endpoints.positions import OpenPositions
            r = OpenPositions(accountID=self.account_id)
            self.client.request(r)
            positions = r.response.get('positions', [])
            
            # Extract trade IDs from positions
            trade_ids = []
            for position in positions:
                # Each position can have multiple trades
                long_trades = position.get('long', {}).get('tradeIDs', [])
                short_trades = position.get('short', {}).get('tradeIDs', [])
                trade_ids.extend(long_trades)
                trade_ids.extend(short_trades)
            
            return trade_ids
        except Exception as e:
            logger.error("Error getting open positions: %s", _sanitize_error(e))
            return []
    
    def get_trade_details(self, trade_id: str) -> Optional[Dict]:
        """
        Get details of a specific trade
        
        Args:
            trade_id: OANDA trade ID
            
        Returns:
            Trade details dictionary or None if error
        """
        try:
            from oandapyV20.endpoints.trades import TradeDetails
            r = TradeDetails(accountID=self.account_id, tradeID=trade_id)
            self.client.request(r)
            return r.response.get('trade', {})
        except Exception as e:
            print(f"Error getting trade details for {trade_id}: {e}")
            return None
    
    def get_open_trades(self) -> List[Dict]:
        """
        Get all open trades
        
        Returns:
            List of trade dictionaries
        """
        try:
            from oandapyV20.endpoints.trades import OpenTrades
            r = OpenTrades(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('trades', [])
        except Exception as e:
            logger.error("Error getting open trades: %s", _sanitize_error(e))
            return []

