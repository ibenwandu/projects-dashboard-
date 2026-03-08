"""
DMI (Directional Movement) analyzer - ADX, +DI, -DI for crossover detection.
Uses Wilder smoothing (period 14). +DI above -DI = bullish; +DI below -DI = bearish.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DMI_PERIOD = 14


def _wilder_smooth(prev: float, current: float, period: int = DMI_PERIOD) -> float:
    """Wilder's smoothing: prev + (current - prev) / period = prev * (1 - 1/period) + current/period."""
    return prev - (prev / period) + (current / period)


def calculate_dmi(
    candles: List[Dict],
    period: int = DMI_PERIOD,
) -> Optional[Dict]:
    """
    Compute +DI and -DI from candles (list of dict with 'high', 'low', 'close').
    Returns dict with plus_di, minus_di, adx (optional), and crossover info for last bar.
    """
    if not candles or len(candles) < period + 2:
        return None
    try:
        highs = []
        lows = []
        closes = []
        for c in candles:
            h = c.get('high') if isinstance(c.get('high'), (int, float)) else float(c.get('high', 0))
            l = c.get('low') if isinstance(c.get('low'), (int, float)) else float(c.get('low', 0))
            cl = c.get('close') if isinstance(c.get('close'), (int, float)) else float(c.get('close', 0))
            if h and l and cl:
                highs.append(h)
                lows.append(l)
                closes.append(cl)
        if len(highs) < period + 2:
            return None

        # True Range, +DM, -DM per bar
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        for i in range(len(highs)):
            h, l, c = highs[i], lows[i], closes[i]
            if i == 0:
                tr_list.append(h - l)
                plus_dm_list.append(0.0)
                minus_dm_list.append(0.0)
                continue
            prev_h, prev_l, prev_c = highs[i - 1], lows[i - 1], closes[i - 1]
            tr_list.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
            plus_dm = (h - prev_h) if (h > prev_h and (h - prev_h) >= (prev_l - l)) else 0.0
            minus_dm = (prev_l - l) if (l < prev_l and (prev_l - l) >= (h - prev_h)) else 0.0
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        # Wilder smoothing: first smoothed = sum of first period values; then smooth
        def smooth_series(vals: List[float]) -> List[float]:
            out = []
            s = sum(vals[:period])
            out.append(s)
            for i in range(period, len(vals)):
                s = _wilder_smooth(s, vals[i], period)
                out.append(s)
            return out

        tr_sm = smooth_series(tr_list)
        plus_sm = smooth_series(plus_dm_list)
        minus_sm = smooth_series(minus_dm_list)

        # +DI, -DI from smoothed values (we have period-1 smoothed then rest)
        idx_last = len(tr_sm) - 1
        tr_smooth = tr_sm[idx_last]
        plus_dm_smooth = plus_sm[idx_last]
        minus_dm_smooth = minus_sm[idx_last]
        if tr_smooth <= 0:
            return None
        plus_di = 100.0 * plus_dm_smooth / tr_smooth
        minus_di = 100.0 * minus_dm_smooth / tr_smooth
        curr_above = plus_di > minus_di

        # Previous bar +DI/-DI for crossover
        prev_above = False
        if idx_last >= 1 and tr_sm[idx_last - 1] > 0:
            pdi = 100.0 * plus_sm[idx_last - 1] / tr_sm[idx_last - 1]
            mdi = 100.0 * minus_sm[idx_last - 1] / tr_sm[idx_last - 1]
            prev_above = pdi > mdi
        crossover_bullish = not prev_above and curr_above
        crossover_bearish = prev_above and not curr_above

        return {
            'plus_di': plus_di,
            'minus_di': minus_di,
            'plus_di_above_minus_di': curr_above,
            'crossover_bullish': crossover_bullish,
            'crossover_bearish': crossover_bearish,
        }
    except Exception as e:
        logger.debug("DMI calculation failed: %s", e)
        return None


def dmi_crossover_direction(candles: List[Dict], period: int = DMI_PERIOD) -> Optional[str]:
    """
    Detect +DI/-DI crossover on the last bar.
    Returns 'BULLISH' (+DI crossed above -DI), 'BEARISH' (+DI crossed below -DI), or None.
    """
    d = calculate_dmi(candles, period=period)
    if not d:
        return None
    if d.get('crossover_bullish'):
        return 'BULLISH'
    if d.get('crossover_bearish'):
        return 'BEARISH'
    return None
