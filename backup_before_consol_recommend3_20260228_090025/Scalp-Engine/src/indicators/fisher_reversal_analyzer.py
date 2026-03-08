"""
Fisher Reversal Analyzer - Per User Specification

Uses Fisher Transform as TREND EXHAUSTION DETECTOR and REVERSAL SIGNAL GENERATOR.
Daily timeframe only. NOT a trend follower.

Key logic:
- Extreme zone: Fisher > +1.5 AND Trigger > +1.5 (overbought) or Fisher < -1.5 AND Trigger < -1.5 (oversold)
- Inclusion: Pair must also have 4H +DI/-DI crossover in direction (LONG = bullish, SHORT = bearish).
- Opportunity bucket: Pair stays in bucket from when lines enter extreme zone until they exit (±1.5). Crossover is secondary.
- Reversal opportunity: Pair IN extreme zone AND 4H DMI crossover → opportunity; persists until Fisher/Trigger move past ±1.5.
- Crossover (true/false): Persistent - true while signal line is below Fisher (SHORT) or above Fisher (LONG)
- 4-stage confirmation: FT Crossover → MACD Crossover → Divergence → 1H ADX >20 or rising 4 candles (for confidence)
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# DMI period for 4H/1H filters
FISHER_DMI_PERIOD = 14
FISHER_ADX_1H_THRESHOLD = 20
FISHER_ADX_1H_RISING_CANDLES = 4


def _fetch_ohlc_dataframe(oanda_client, instrument: str, granularity: str, count: int = 50) -> Optional[pd.DataFrame]:
    """Fetch OANDA candles and return a DataFrame with columns high, low, close. instrument e.g. EUR_USD."""
    import time

    from oandapyV20.endpoints.instruments import InstrumentsCandles

    # Retry logic for transient errors (5xx, 429)
    # Increased to 3 attempts to handle OANDA intermittent 500 errors
    max_attempts = 3
    last_exception = None

    for attempt in range(max_attempts):
        try:
            params = {"count": count, "granularity": granularity, "price": "M"}
            if granularity == "D":
                alignment_hour = int(os.environ.get("FISHER_DAILY_ALIGNMENT", "17"))
                alignment_tz = os.environ.get("FISHER_ALIGNMENT_TZ", "America/New_York")
                params["dailyAlignment"] = alignment_hour
                params["alignmentTimezone"] = alignment_tz
            r = InstrumentsCandles(instrument=instrument, params=params)
            oanda_client.request(r)
            candles = r.response.get("candles", [])
            if not candles or len(candles) < FISHER_DMI_PERIOD + 2:
                return None
            highs, lows, closes = [], [], []
            for c in candles:
                if not isinstance(c, dict):
                    continue
                mid = c.get("mid") or c.get("bid") or c.get("ask") or {}
                if not isinstance(mid, dict):
                    continue
                hval = float(mid.get("h", 0) or mid.get("high", 0))
                lval = float(mid.get("l", 0) or mid.get("low", 0))
                cval = float(mid.get("c", 0) or mid.get("close", 0))
                if hval and lval and cval:
                    highs.append(hval)
                    lows.append(lval)
                    closes.append(cval)
            if len(closes) < FISHER_DMI_PERIOD + 2:
                return None
            return pd.DataFrame({"high": highs, "low": lows, "close": closes})

        except Exception as e:
            last_exception = e
            error_msg = str(e)
            status_code = _get_http_status_from_error(e)

            # Check if this is a retryable error (5xx or 429)
            is_retryable = status_code is None or 429 == status_code or (500 <= status_code < 600)

            if is_retryable and attempt < max_attempts - 1:
                # Retry on transient errors
                logger.debug(
                    f"Fetch OHLC {instrument} {granularity} (HTTP {status_code}): transient error. "
                    f"Retrying (attempt {attempt + 1}/{max_attempts})"
                )
                time.sleep(2 * (attempt + 1))
            else:
                # Non-retryable error or last attempt
                logger.debug(f"Fetch OHLC {instrument} {granularity}: {error_msg}")
                return None

    return None


def _get_http_status_from_error(e: Exception) -> Optional[int]:
    """Extract HTTP status code from exception if present"""
    resp = getattr(e, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    return None


def _check_4h_dmi_crossover_from_df(df_4h: pd.DataFrame, direction: str, period: int = FISHER_DMI_PERIOD) -> bool:
    """True if 4H +DI/-DI crossover in direction: LONG = bullish (+DI crossed above -DI), SHORT = bearish (+DI crossed below -DI)."""
    try:
        from src.ft_dmi_ema.indicators_ft_dmi_ema import Indicators
        plus_di, minus_di, _ = Indicators.dmi(df_4h, period=period)
        if plus_di is None or minus_di is None or len(plus_di) < 2 or len(minus_di) < 2:
            return False
        prev_p, prev_m = float(plus_di.iloc[-2]), float(minus_di.iloc[-2])
        curr_p, curr_m = float(plus_di.iloc[-1]), float(minus_di.iloc[-1])
        if direction == "LONG":
            return prev_p <= prev_m and curr_p > curr_m  # bullish crossover
        if direction == "SHORT":
            return prev_p >= prev_m and curr_p < curr_m  # bearish crossover
        return False
    except Exception as e:
        logger.debug("4H DMI crossover check: %s", e)
        return False


def _check_1h_adx_ok_from_df(
    df_1h: pd.DataFrame,
    period: int = FISHER_DMI_PERIOD,
    threshold: int = FISHER_ADX_1H_THRESHOLD,
    rising_candles: int = FISHER_ADX_1H_RISING_CANDLES,
) -> Tuple[bool, float]:
    """Returns (adx_ok, current_adx). adx_ok = (ADX > threshold) or (ADX rising over rising_candles)."""
    try:
        from src.ft_dmi_ema.indicators_ft_dmi_ema import Indicators
        _, _, adx = Indicators.dmi(df_1h, period=period)
        if adx is None or len(adx) < period + rising_candles:
            return False, 0.0
        current_adx = float(adx.iloc[-1])
        above = current_adx > threshold
        rising = Indicators.is_adx_rising(adx, candles=rising_candles)
        return (above or rising, current_adx)
    except Exception as e:
        logger.debug("1H ADX check: %s", e)
        return False, 0.0


def _calculate_fisher_trigger(prices, period: int = 9):
    """Legacy: simple Fisher (Close-based, EMA-3 trigger). Use _calculate_fisher_trigger_ehlers for OANDA alignment."""
    import numpy as np
    import pandas as pd

    if len(prices) < period:
        return None, None

    prices = pd.Series(prices) if not hasattr(prices, 'iloc') else prices
    min_price = prices.rolling(window=period, min_periods=period).min()
    max_price = prices.rolling(window=period, min_periods=period).max()
    price_range = max_price - min_price
    price_range = price_range.replace(0, 1e-10)

    normalized = 2 * ((prices - min_price) / price_range - 0.5)
    normalized = normalized.clip(-0.999, 0.999)

    fisher = 0.5 * np.log((1 + normalized) / (1 - normalized))
    trigger = fisher.ewm(span=3, adjust=False).mean()

    return fisher, trigger


def _calculate_fisher_trigger_ehlers(highs, lows, period: int = 9):
    """
    Ehlers Fisher Transform: matches OANDA / TradingView style (Fisher (9)).

    - Input: median price HL2 = (High + Low) / 2 per bar.
    - Smoothed normalization: xv = 0.33 * 2*((mp-min)/range - 0.5) + 0.67 * xv_prev, clipped ±0.999.
    - Fisher is recursive: Fisher = 0.5*ln((1+xv)/(1-xv)) + 0.5*Fisher_prev.
    - Trigger = previous bar's Fisher (not EMA-3).

    Returns (fisher_series, trigger_series) as pandas Series; first bar has fisher=0, trigger=NaN.
    """
    import numpy as np
    import pandas as pd

    if len(highs) < period or len(lows) != len(highs):
        return None, None

    mp = pd.Series(0.5 * (np.asarray(highs, dtype=float) + np.asarray(lows, dtype=float)))
    n = len(mp)
    xv = np.zeros(n)
    fisher = np.zeros(n)
    trigger = np.full(n, np.nan)

    for i in range(n):
        start = max(0, i - period + 1)
        window = mp.iloc[start : i + 1]
        min_p = window.min()
        max_p = window.max()
        denom = max_p - min_p if (max_p - min_p) > 1e-10 else 1e-10
        raw = 2 * ((mp.iloc[i] - min_p) / denom - 0.5)
        if i > 0:
            xv[i] = 0.33 * raw + 0.67 * xv[i - 1]
        else:
            xv[i] = 0.0
        xv[i] = max(-0.999, min(0.999, xv[i]))
        if i > 0:
            fisher[i] = 0.5 * np.log((1 + xv[i]) / (1 - xv[i])) + 0.5 * fisher[i - 1]
            trigger[i] = fisher[i - 1]
        else:
            fisher[i] = 0.0

    return pd.Series(fisher), pd.Series(trigger)


def _calculate_macd(closes, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
    """
    Calculate MACD. Aligns with OANDA Style labels: "MACD" (blue line), "Signal" (red line), "Histogram".

    Returns dict with:
      macd: MACD line value (OANDA "MACD" = fast EMA - slow EMA)
      signal: Signal line value (OANDA "Signal" = EMA of MACD line)
      previous_macd, previous_signal: prior bar for crossover detection
    """
    import pandas as pd

    if len(closes) < slow + signal + 2:
        return None

    closes = pd.Series(closes) if not hasattr(closes, 'iloc') else closes
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    # OANDA "MACD" = this line (blue); OANDA "Signal" = EMA of this (red)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    return {
        'macd': float(macd_line.iloc[-1]),       # OANDA: MACD line (blue)
        'signal': float(signal_line.iloc[-1]),   # OANDA: Signal line (red)
        'previous_macd': float(macd_line.iloc[-2]),
        'previous_signal': float(signal_line.iloc[-2]),
    }


def _check_macd_crossover(macd_data: Dict, direction: str) -> bool:
    """
    Check if MACD line crossed Signal line in the direction that confirms the Fisher reversal.
    OANDA: MACD = blue line, Signal = red line. Crossover = MACD line crossing Signal line.
    LONG: MACD crosses above Signal (bullish). SHORT: MACD crosses below Signal (bearish).
    """
    if not macd_data:
        return False
    macd_line_val = macd_data['macd']       # OANDA "MACD" (blue)
    signal_line_val = macd_data['signal']   # OANDA "Signal" (red)
    prev_macd = macd_data['previous_macd']
    prev_signal = macd_data['previous_signal']

    if direction == "LONG":
        # Bullish: MACD line was below Signal, now above
        return (prev_macd < prev_signal) and (macd_line_val > signal_line_val)
    elif direction == "SHORT":
        # Bearish: MACD line was above Signal, now below
        return (prev_macd > prev_signal) and (macd_line_val < signal_line_val)
    return False


def _check_divergence(
    prices,
    fisher_series,
    direction: str,
    lookback: int = 15
) -> bool:
    """
    Detect price vs Fisher divergence.
    LONG: Price lower low, Fisher higher low (bullish divergence)
    SHORT: Price higher high, Fisher lower high (bearish divergence)
    """
    import pandas as pd

    prices = pd.Series(prices) if not hasattr(prices, 'iloc') else prices
    fisher = fisher_series if hasattr(fisher_series, 'iloc') else pd.Series(fisher_series)

    if len(prices) < lookback * 2 or len(fisher) < lookback * 2:
        return False

    n = len(prices) - 1
    recent_price = prices.iloc[n]
    recent_fisher = fisher.iloc[n]

    if direction == "LONG":
        # Bullish: recent price low < previous price low, recent fisher low > previous fisher low
        recent_window_p = prices.iloc[-lookback:]
        recent_window_f = fisher.iloc[-lookback:]
        prev_window_p = prices.iloc[-lookback * 2:-lookback]
        prev_window_f = fisher.iloc[-lookback * 2:-lookback]

        if prev_window_p.empty or prev_window_f.empty:
            return False

        recent_price_low = recent_window_p.min()
        previous_price_low = prev_window_p.min()
        recent_fisher_low = recent_window_f.min()
        previous_fisher_low = prev_window_f.min()

        return recent_price_low < previous_price_low and recent_fisher_low > previous_fisher_low

    elif direction == "SHORT":
        # Bearish: recent price high > previous price high, recent fisher high < previous fisher high
        recent_window_p = prices.iloc[-lookback:]
        recent_window_f = fisher.iloc[-lookback:]
        prev_window_p = prices.iloc[-lookback * 2:-lookback]
        prev_window_f = fisher.iloc[-lookback * 2:-lookback]

        if prev_window_p.empty or prev_window_f.empty:
            return False

        recent_price_high = recent_window_p.max()
        previous_price_high = prev_window_p.max()
        recent_fisher_high = recent_window_f.max()
        previous_fisher_high = prev_window_f.max()

        return recent_price_high > previous_price_high and recent_fisher_high < previous_fisher_high

    return False


def analyze_pair_daily(
    oanda_client,
    pair: str,
    count: int = 50
) -> Optional[Dict]:
    """
    Analyze a single pair on Daily timeframe for Fisher reversal signals.

    Returns:
        Dict with fisher_analysis (per-pair data) and optionally opportunity (if crossover from extreme)
        Or None if analysis fails
    """
    try:
        from oandapyV20.endpoints.instruments import InstrumentsCandles

        oanda_pair = pair.replace('/', '_')
        # Daily alignment: MUST match your chart or Fisher values will be wrong (e.g. EUR/USD 2.33 vs -0.08).
        # Default 17/America/New_York = OANDA 5pm ET daily bars (matches OANDA chart). Use 0/UTC for midnight UTC.
        alignment_hour = int(os.environ.get("FISHER_DAILY_ALIGNMENT", "17"))
        alignment_tz = os.environ.get("FISHER_ALIGNMENT_TZ", "America/New_York")
        params = {
            "count": count,
            "granularity": "D",
            "price": "M",
            "dailyAlignment": alignment_hour,
            "alignmentTimezone": alignment_tz,
        }
        r = InstrumentsCandles(instrument=oanda_pair, params=params)
        oanda_client.request(r)
        candles = r.response.get('candles', [])

        if not candles:
            logger.warning(f"Insufficient candles for {pair}")
            return None

        closes = []
        highs = []
        lows = []
        times = []
        for c in candles:
            if isinstance(c, dict):
                # OANDA returns 'mid' when price=M; fallback to bid/ask if structure differs
                mid = c.get('mid') or c.get('bid') or c.get('ask') or {}
                if isinstance(mid, dict):
                    cval = float(mid.get('c', 0) or mid.get('close', 0))
                    hval = float(mid.get('h', 0) or mid.get('high', 0))
                    lval = float(mid.get('l', 0) or mid.get('low', 0))
                else:
                    cval = hval = lval = 0.0
                if cval and hval and lval:
                    closes.append(cval)
                    highs.append(hval)
                    lows.append(lval)
                    times.append(c.get('time', ''))
        # OANDA returns oldest-first; if newest-first, reverse to match chart
        if len(times) >= 2 and times[0] and times[-1] and times[0] > times[-1]:
            closes = closes[::-1]
            highs = highs[::-1]
            lows = lows[::-1]
            times = times[::-1]
            logger.debug("%s: Reversed candle order (newest-first from API)", pair)
        # Include incomplete (current) candle so our values match the live chart.

        if len(closes) < 20:
            return None

        # Debug: verify enough candles and range for Fisher (per FISHER_ACTUAL_CORRECT_FIX.md)
        _log = logging.getLogger('FisherDailyScanner')
        _log.debug(
            "Fisher calc: using %s bars (HL2), period=9; close range %.5f / %.5f",
            len(closes), min(closes), max(closes)
        )
        _log.debug("%s: last 10 closes=%s", pair, [round(c, 5) for c in closes[-10:]])

        # Ehlers Fisher (HL2, smoothed norm, recursive Fisher, trigger=prev) to align with OANDA chart
        fisher, trigger = _calculate_fisher_trigger_ehlers(highs, lows, period=9)
        if fisher is None:
            return None

        curr_f = float(fisher.iloc[-1])
        curr_t = float(trigger.iloc[-1])
        prev_f = float(fisher.iloc[-2])
        prev_t = float(trigger.iloc[-2])
        current_price = closes[-1]

        # Extreme zones (both Fisher AND Trigger in zone)
        extreme_overbought = curr_f > 1.5 and curr_t > 1.5
        prev_extreme_overbought = prev_f > 1.5 and prev_t > 1.5
        extreme_oversold = curr_f < -1.5 and curr_t < -1.5
        prev_extreme_oversold = prev_f < -1.5 and prev_t < -1.5

        # Crossover detection (Fisher vs Trigger)
        bearish_crossover = prev_f > prev_t and curr_f < curr_t  # Fisher crosses below Trigger
        bullish_crossover = prev_f < prev_t and curr_f > curr_t  # Fisher crosses above Trigger

        # Was in extreme zone before crossover? Either line extreme is enough (per FISHER_ACTUAL_CORRECT_FIX.md).
        # Reversals happen AS price exits the extreme zone, not while staying in it.
        was_overbought = (prev_f > 1.5) or (prev_t > 1.5)
        was_oversold = (prev_f < -1.5) or (prev_t < -1.5)

        # Zone classification (both lines for current zone / WARNING)
        if extreme_overbought:
            zone = "EXTREME_OVERBOUGHT"
            warning_active = True
            warning_message = "Long positions at risk. Watching for bearish crossover."
        elif extreme_oversold:
            zone = "EXTREME_OVERSOLD"
            warning_active = True
            warning_message = "Short positions at risk. Watching for bullish crossover."
        else:
            zone = "NEUTRAL"
            warning_active = False
            warning_message = None

        _log = logging.getLogger('FisherDailyScanner')
        _log.info(
            f"{pair}: Fisher={curr_f:.3f} Trigger={curr_t:.3f} (prev {prev_f:.3f}/{prev_t:.3f}) "
            f"→ zone={zone} bearishX={bearish_crossover} bullishX={bullish_crossover}"
        )
        # Diagnostic: last 5 closes for comparison with chart (daily candles)
        last_n = min(5, len(closes))
        last_closes = closes[-last_n:] if closes else []
        last_times = times[-last_n:] if len(times) >= len(closes) else [""] * last_n
        _log.info(f"{pair}: last {last_n} closes={[round(c, 5) for c in last_closes]} times={last_times}")

        # Opportunity persists while IN extreme zone; exits when Fisher/Trigger move past ±1.5.
        # Overbought (both > +1.5) → SHORT opportunity until move below +1.5.
        # Oversold (both < -1.5) → LONG opportunity until move above -1.5.
        opportunity = None
        direction = None
        if extreme_overbought:
            direction = "SHORT"
        elif extreme_oversold:
            direction = "LONG"

        # Inclusion rule: require 4H +DI/-DI crossover in direction (LONG = bullish, SHORT = bearish)
        if direction:
            df_4h = _fetch_ohlc_dataframe(oanda_client, oanda_pair, "H4", count=50)
            if df_4h is None or not _check_4h_dmi_crossover_from_df(df_4h, direction):
                _log = logging.getLogger("FisherDailyScanner")
                _log.info("%s: 4H +DI/-DI crossover not met for %s; skipping opportunity", pair, direction)
                direction = None

        # signal_type: REVERSAL = crossover this bar; IN_ZONE = in extreme, no crossover this bar
        signal_type = None
        if direction:
            signal_type = 'REVERSAL' if ((bearish_crossover and direction == "SHORT") or (bullish_crossover and direction == "LONG")) else 'IN_ZONE'
        elif warning_active:
            signal_type = 'WARNING'

        fisher_analysis = {
            'fisher': curr_f,
            'trigger': curr_t,
            'previous_fisher': prev_f,
            'previous_trigger': prev_t,
            'zone': zone,
            'signal_type': signal_type,
            'crossover_detected': bearish_crossover or bullish_crossover,
            'crossover_type': 'BEARISH' if bearish_crossover else ('BULLISH' if bullish_crossover else None),
            'warning_active': warning_active,
            'warning_message': warning_message,
        }

        if direction:
            # ft_crossover: persistent state - true while Fisher and Trigger are on correct side (align with OANDA chart).
            # OANDA: Fisher = blue line, Trigger = orange line. Fisher above Trigger = bullish; Fisher below Trigger = bearish.
            # LONG (oversold): Fisher above Trigger = bullish confirmed.
            # SHORT (overbought): Fisher below Trigger = bearish confirmed.
            ft_crossover = (curr_f > curr_t and direction == "LONG") or (curr_f < curr_t and direction == "SHORT")

            # MACD confirmation (ensure native Python bool for JSON serialization)
            macd_data = _calculate_macd(closes)
            macd_confirms = bool(_check_macd_crossover(macd_data, direction))

            # Divergence confirmation (ensure native Python bool for JSON serialization)
            divergence_detected = bool(_check_divergence(closes, fisher, direction))

            # 1H ADX confirmation: ADX > 20 or ADX rising over 4 candles
            df_1h = _fetch_ohlc_dataframe(oanda_client, oanda_pair, "H1", count=50)
            adx_1h_ok, adx_1h_val = _check_1h_adx_ok_from_df(df_1h) if df_1h is not None else (False, 0.0)

            # Confidence: 50% base + 5% FT + 25% MACD + 20% divergence + 10% ADX 1H
            confidence = 0.50
            if ft_crossover:
                confidence += 0.05  # Boost when Trigger has crossed and remains on correct side
            if macd_confirms:
                confidence += 0.25
            if divergence_detected:
                confidence += 0.20
            if adx_1h_ok:
                confidence += 0.10
            confidence = min(confidence, 0.95)

            fisher_analysis['macd_crossover'] = macd_confirms
            fisher_analysis['divergence'] = divergence_detected
            fisher_analysis['ft_crossover'] = ft_crossover
            fisher_analysis['adx_1h_ok'] = adx_1h_ok
            adx_1h_num = float(adx_1h_val) if adx_1h_val is not None and adx_1h_val == adx_1h_val else None
            fisher_analysis['adx_1h'] = round(adx_1h_num, 2) if adx_1h_num is not None else None

            # Build rationale
            adx_rationale = f"{'✅' if adx_1h_ok else '❌'} 1H ADX >20 or rising 4c: {adx_1h_ok}"
            if adx_1h_num is not None:
                adx_rationale += f" (ADX={adx_1h_num:.1f})"
            rationale_parts = [
                f"In {'overbought' if direction == 'SHORT' else 'oversold'} zone (both lines {'>' if direction == 'SHORT' else '<'} 1.5); persists until exit past {'+1.5' if direction == 'SHORT' else '-1.5'}",
                f"{'✅' if ft_crossover else '⏳'} FT Crossover: {ft_crossover}",
                f"{'✅' if macd_confirms else '❌'} MACD / Signal Crossover: {macd_confirms}",
                f"{'✅' if divergence_detected else '❌'} Divergence: {divergence_detected}",
                adx_rationale,
            ]

            # Simple SL/TP (1% ATR proxy)
            atr_est = current_price * 0.01
            if direction == "LONG":
                stop_loss = current_price - 2 * atr_est
                take_profit = current_price + 3 * atr_est
            else:
                stop_loss = current_price + 2 * atr_est
                take_profit = current_price - 3 * atr_est

            ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
            opportunity = {
                'id': f"FT_{pair.replace('/', '')}_{direction}_{ts}",
                'pair': pair,
                'direction': direction,
                'signal_source': 'FISHER_REVERSAL',
                'entry_type': 'REVERSAL_FROM_OVERBOUGHT' if direction == 'SHORT' else 'REVERSAL_FROM_OVERSOLD',
                'timeframe': 'DAILY',
                'entry': round(current_price, 5),
                'stop_loss': round(stop_loss, 5),
                'take_profit': round(take_profit, 5),
                'confirmations': {
                    'ft_crossover': ft_crossover,
                    'macd_crossover': macd_confirms,
                    'divergence': divergence_detected,
                },
                'confidence': confidence,
                'rationale': " | ".join(rationale_parts),
                'fisher_data': {
                    'fisher': curr_f,
                    'trigger': curr_t,
                    'zone': zone,
                },
                'fisher_analysis': {
                    'daily_fisher': curr_f,
                    'h1_fisher': None,  # Daily only
                    'm15_fisher': None,
                    'setup_type': 'MEAN_REVERSION',
                    'alignment_quality': 'HIGH' if confidence >= 0.75 else 'MEDIUM',
                    'confirmations': {
                        'ft_crossover': ft_crossover,
                        'macd_crossover': macd_confirms,
                        'divergence': divergence_detected,
                        'adx_1h_ok': adx_1h_ok,
                    },
                },
                'fisher_config': {
                    'activation_trigger': 'MANUAL',
                    'sl_type': 'BE_TO_TRAILING',
                    'enabled': False,
                },
                'execution_config': {
                    'mode': 'SEMI_AUTO',
                    'activation_trigger': 'MANUAL',
                    'max_runs': 1,
                    'enabled': False,
                },
                'fisher_signal': True,
            }

        return {
            'pair': pair,
            'fisher_analysis': fisher_analysis,
            'opportunity': opportunity,
        }

    except Exception as e:
        logger.error(f"Error analyzing {pair}: {e}", exc_info=True)
        return None


def check_fisher_warnings(llm_opportunity: Dict, fisher_data: Dict) -> Dict:
    """
    Check if Fisher Transform warns against an LLM opportunity.
    Modifies opportunity in-place with fisher_warning, fisher_risk_level, adjusted confidence.
    """
    pair = llm_opportunity.get('pair', '')
    direction = llm_opportunity.get('direction', '')

    fa = fisher_data.get(pair, {}) if isinstance(fisher_data.get(pair), dict) else {}
    fisher_value = fa.get('fisher')
    trigger_value = fa.get('trigger')

    if fisher_value is None or trigger_value is None:
        return llm_opportunity

    warning = None
    risk_level = "NORMAL"

    if direction.upper() in ("LONG", "BUY"):
        if fisher_value > 1.5 and trigger_value > 1.5:
            warning = "⚠️ FISHER WARNING: Extreme overbought. Long positions at risk."
            risk_level = "HIGH"
            if fisher_value < trigger_value:
                warning = "🚨 FISHER REVERSAL: Trend has reversed. DO NOT ENTER LONG."
                risk_level = "CRITICAL"

    elif direction.upper() in ("SHORT", "SELL"):
        if fisher_value < -1.5 and trigger_value < -1.5:
            warning = "⚠️ FISHER WARNING: Extreme oversold. Short positions at risk."
            risk_level = "HIGH"
            if fisher_value > trigger_value:
                warning = "🚨 FISHER REVERSAL: Trend has reversed. DO NOT ENTER SHORT."
                risk_level = "CRITICAL"

    llm_opportunity['fisher_warning'] = warning
    llm_opportunity['fisher_risk_level'] = risk_level

    if risk_level == "HIGH":
        orig = llm_opportunity.get('confidence', llm_opportunity.get('original_confidence', 1.0))
        llm_opportunity['original_confidence'] = orig
        llm_opportunity['confidence'] = orig * 0.7
    elif risk_level == "CRITICAL":
        orig = llm_opportunity.get('confidence', llm_opportunity.get('original_confidence', 1.0))
        llm_opportunity['original_confidence'] = orig
        llm_opportunity['confidence'] = orig * 0.3

    return llm_opportunity
