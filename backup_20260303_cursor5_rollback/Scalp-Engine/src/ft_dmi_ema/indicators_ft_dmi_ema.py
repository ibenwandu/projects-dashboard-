"""
FT-DMI-EMA technical indicators (Fisher, DMI, EMA, ATR, swing, crossover, validators).
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class Indicators:
    @staticmethod
    def fisher_transform(data: pd.DataFrame, period: int = 10) -> Tuple[pd.Series, pd.Series]:
        try:
            hl2 = (data["high"] + data["low"]) / 2
            highest = hl2.rolling(window=period).max()
            lowest = hl2.rolling(window=period).min()
            range_val = highest - lowest
            range_val = range_val.replace(0, 0.001)
            value = 2 * ((hl2 - lowest) / range_val) - 1
            value = value.clip(lower=-0.999, upper=0.999)
            fisher = 0.5 * np.log((1 + value) / (1 - value))
            fisher = fisher.ewm(span=5, adjust=False).mean()
            trigger = fisher.shift(1)
            return fisher, trigger
        except Exception as e:
            logger.error(f"Error calculating Fisher Transform: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float)

    @staticmethod
    def dmi(data: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        try:
            high, low, close = data["high"], data["low"], data["close"]
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            high_diff = high - high.shift(1)
            low_diff = low.shift(1) - low
            plus_dm = pd.Series(0.0, index=data.index)
            plus_dm[(high_diff > low_diff) & (high_diff > 0)] = high_diff
            minus_dm = pd.Series(0.0, index=data.index)
            minus_dm[(low_diff > high_diff) & (low_diff > 0)] = low_diff
            atr = tr.ewm(alpha=1 / period, adjust=False).mean()
            plus_dm_smooth = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
            minus_dm_smooth = minus_dm.ewm(alpha=1 / period, adjust=False).mean()
            plus_di = 100 * (plus_dm_smooth / atr)
            minus_di = 100 * (minus_dm_smooth / atr)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            dx = dx.replace([np.inf, -np.inf], 0)
            adx = dx.ewm(alpha=1 / period, adjust=False).mean()
            return plus_di, minus_di, adx
        except Exception as e:
            logger.error(f"Error calculating DMI: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        try:
            return data.ewm(span=period, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        try:
            tr1 = data["high"] - data["low"]
            tr2 = abs(data["high"] - data["close"].shift(1))
            tr3 = abs(data["low"] - data["close"].shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.ewm(alpha=1 / period, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def find_swing_high(data: pd.DataFrame, lookback: int = 2) -> Optional[float]:
        try:
            if len(data) < lookback * 2 + 1:
                return None
            highs = data["high"].values
            for i in range(len(highs) - lookback - 1, lookback, -1):
                center_high = highs[i]
                if all(highs[j] < center_high for j in range(i - lookback, i)) and all(
                    highs[j] < center_high for j in range(i + 1, min(i + lookback + 1, len(highs)))
                ):
                    return center_high
            return None
        except Exception as e:
            logger.error(f"Error finding swing high: {e}")
            return None

    @staticmethod
    def find_swing_low(data: pd.DataFrame, lookback: int = 2) -> Optional[float]:
        try:
            if len(data) < lookback * 2 + 1:
                return None
            lows = data["low"].values
            for i in range(len(lows) - lookback - 1, lookback, -1):
                center_low = lows[i]
                if all(lows[j] > center_low for j in range(i - lookback, i)) and all(
                    lows[j] > center_low for j in range(i + 1, min(i + lookback + 1, len(lows)))
                ):
                    return center_low
            return None
        except Exception as e:
            logger.error(f"Error finding swing low: {e}")
            return None

    @staticmethod
    def detect_crossover(series1: pd.Series, series2: pd.Series) -> str:
        try:
            if len(series1) < 2 or len(series2) < 2:
                return "none"
            prev_s1, prev_s2 = series1.iloc[-2], series2.iloc[-2]
            current_s1, current_s2 = series1.iloc[-1], series2.iloc[-1]
            if prev_s1 <= prev_s2 and current_s1 > current_s2:
                return "bullish"
            if prev_s1 >= prev_s2 and current_s1 < current_s2:
                return "bearish"
            return "none"
        except Exception as e:
            logger.error(f"Error detecting crossover: {e}")
            return "none"

    @staticmethod
    def is_adx_rising(adx: pd.Series, candles: int = 2) -> bool:
        try:
            if len(adx) < candles + 1:
                return False
            for i in range(candles):
                if adx.iloc[-(i + 1)] <= adx.iloc[-(i + 2)]:
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking ADX rise: {e}")
            return False

    @staticmethod
    def is_adx_falling(adx: pd.Series, candles: int = 3) -> bool:
        try:
            if len(adx) < candles + 1:
                return False
            for i in range(candles):
                if adx.iloc[-(i + 1)] >= adx.iloc[-(i + 2)]:
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking ADX fall: {e}")
            return False


class IndicatorValidator:
    @staticmethod
    def validate_4h_trend_bias_long(plus_di: pd.Series, minus_di: pd.Series, adx: pd.Series) -> bool:
        try:
            if len(plus_di) < 1 or len(minus_di) < 1 or len(adx) < 5:
                return False
            if plus_di.iloc[-1] <= minus_di.iloc[-1]:
                return False
            current_adx = adx.iloc[-1]
            if current_adx >= 25 or (current_adx >= 20 and Indicators.is_adx_rising(adx, candles=2)):
                if not Indicators.is_adx_falling(adx, candles=4):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error validating 4H trend bias long: {e}")
            return False

    @staticmethod
    def validate_4h_trend_bias_short(plus_di: pd.Series, minus_di: pd.Series, adx: pd.Series) -> bool:
        try:
            if len(plus_di) < 1 or len(minus_di) < 1 or len(adx) < 5:
                return False
            if minus_di.iloc[-1] <= plus_di.iloc[-1]:
                return False
            current_adx = adx.iloc[-1]
            if current_adx >= 25 or (current_adx >= 20 and Indicators.is_adx_rising(adx, candles=2)):
                if not Indicators.is_adx_falling(adx, candles=4):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error validating 4H trend bias short: {e}")
            return False

    @staticmethod
    def validate_1h_confirmation_long(
        plus_di: pd.Series,
        minus_di: pd.Series,
        adx: pd.Series,
        ema9: pd.Series,
        ema26: pd.Series,
        current_price: float,
    ) -> bool:
        try:
            if (
                len(plus_di) < 1
                or len(minus_di) < 1
                or len(adx) < 1
                or len(ema9) < 1
                or len(ema26) < 1
            ):
                return False
            if plus_di.iloc[-1] <= minus_di.iloc[-1]:
                return False
            if ema9.iloc[-1] <= ema26.iloc[-1]:
                return False
            if current_price <= ema9.iloc[-1]:
                return False
            if adx.iloc[-1] <= 20:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating 1H confirmation long: {e}")
            return False

    @staticmethod
    def validate_1h_confirmation_short(
        plus_di: pd.Series,
        minus_di: pd.Series,
        adx: pd.Series,
        ema9: pd.Series,
        ema26: pd.Series,
        current_price: float,
    ) -> bool:
        try:
            if (
                len(plus_di) < 1
                or len(minus_di) < 1
                or len(adx) < 1
                or len(ema9) < 1
                or len(ema26) < 1
            ):
                return False
            if minus_di.iloc[-1] <= plus_di.iloc[-1]:
                return False
            if ema9.iloc[-1] >= ema26.iloc[-1]:
                return False
            if current_price >= ema9.iloc[-1]:
                return False
            if adx.iloc[-1] <= 20:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating 1H confirmation short: {e}")
            return False
