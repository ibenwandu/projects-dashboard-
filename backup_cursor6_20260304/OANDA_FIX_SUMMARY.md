# OANDA API Error Handling Fixes

## Problem
The service was repeatedly attempting to fetch forex data from OANDA but getting server errors (5xx) instead of valid trading data. The root cause was missing retry logic for transient errors.

## Root Causes Identified

1. **No retry logic for transient errors**: Code would fail immediately on 5xx or 429 (rate limit) errors without retrying
2. **No request delay/rate limiting**: Rapid successive requests caused rate limiting
3. **Inconsistent error handling**: Different modules had different error handling strategies
4. **No exponential backoff**: Failed requests were retried too quickly

## Files Modified

### 1. `src/price_monitor.py` - PriceMonitor._get_oanda_rate()
**Changes:**
- Added retry logic (max 2 attempts)
- Added exponential backoff (1s, 2s delays)
- Added HTTP status code extraction
- Proper handling of 5xx and 429 errors
- Request delay implementation

**Impact:** Fixes repeated OANDA rate fetching failures during opportunity monitoring

### 2. `Scalp-Engine/src/ft_dmi_ema/ft_candle_fetcher.py` - FTCandleFetcher.get_candles()
**Changes:**
- Added retry logic (max 2 attempts) for transient errors
- Added exponential backoff (2s, 4s delays)
- Added HTTP status code extraction
- Distinguishes between retryable (5xx, 429) and permanent (401, 403, 404) errors
- Helper methods: `_get_http_status()`, `_is_retryable_http()`

**Impact:** Fixes candle fetching timeouts during Fisher Transform analysis

### 3. `Scalp-Engine/auto_trader_core.py` - AutoTrader._get_current_price()
**Changes:**
- Added retry logic (max 2 attempts)
- Added exponential backoff (1s, 2s delays)
- Added HTTP status code extraction
- Proper transient error detection
- Helper methods: `_get_http_status()`, `_is_retryable_http()`

**Impact:** Fixes price fetching for execution directives

### 4. `Scalp-Engine/src/indicators/fisher_reversal_analyzer.py` - _fetch_ohlc_dataframe()
**Changes:**
- Added retry logic (max 2 attempts) for transient errors
- Added exponential backoff (2s, 4s delays)
- Added HTTP status code extraction
- New helper function: `_get_http_status_from_error()`

**Impact:** Fixes candle fetching for Fisher Daily Scanner analysis

### 5. `Scalp-Engine/src/indicators/multi_timeframe_analyzer.py` - MultiTimeframeAnalyzer._fetch_candles()
**Changes:**
- Added retry logic (max 2 attempts)
- Added exponential backoff (2s, 4s delays)
- Added HTTP status code extraction
- New helper method: `_get_http_status_from_error()`

**Impact:** Fixes multi-timeframe candle fetching for trend context

## Retry Strategy Implementation

### Transient Error Detection
```python
def _is_retryable_http(status: Optional[int]) -> bool:
    """True for 5xx and 429 (transient/server/rate-limit)"""
    if status is None:
        return True  # Unknown - retry once
    return 429 == status or (500 <= status < 600)
```

### Backoff Delays
- **PriceMonitor**: 1s, 2s delays (fast recovery for rate monitoring)
- **FT/DMI Analyzers**: 2s, 4s delays (slower recovery for batch analysis)

### Logging Strategy
- **Retryable errors**: Logged at DEBUG level (expected to succeed on retry)
- **Final failures**: Logged at ERROR level (permanent failures)
- **HTTP status codes**: Included in error messages for debugging

## Benefits

1. **Increased Reliability**: Transient server errors no longer cause immediate failures
2. **Better Rate Limit Handling**: Exponential backoff prevents rate limit cascades
3. **Consistent Error Handling**: All OANDA API calls follow the same retry pattern
4. **Improved Debugging**: HTTP status codes and detailed error messages
5. **Non-breaking Change**: Existing code behavior preserved for successful requests

## Testing Recommendations

1. Verify OANDA API calls succeed when service recovers from temporary outages
2. Monitor logs for "Retrying" messages (should be DEBUG level)
3. Check rate limit handling under heavy load
4. Verify final error messages are logged when max attempts exhausted

## Related Configuration

The OANDA request delay can be configured via environment variable:
```bash
OANDA_REQUEST_DELAY_SEC=0.35  # Default in OandaClient (350ms)
```

This delay is enforced between API calls to respect rate limits.
