"""
FT-DMI-EMA signal generator: two-stage (setup ready + 15m trigger) and full signal.
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, time
import logging

from .indicators_ft_dmi_ema import Indicators, IndicatorValidator
from .ft_dmi_ema_config import (
    IndicatorConfig,
    FilterConfig,
    SessionConfig,
    InstrumentConfig,
)

logger = logging.getLogger(__name__)


def get_setup_status(
    instrument: str,
    data_15m: pd.DataFrame,
    data_1h: pd.DataFrame,
    data_4h: pd.DataFrame,
    current_price: float,
    current_spread: float,
    current_time: datetime,
    fisher_period: int = None,
    dmi_period: int = None,
    ema_fast: int = None,
    ema_slow: int = None,
    atr_period: int = None,
) -> Dict:
    """
    Two-stage status: setup ready (filters + 4H + 1H) and 15m Fisher trigger met.
    Returns:
        {
            'long_setup_ready': bool,
            'short_setup_ready': bool,
            'long_trigger_met': bool,
            'short_trigger_met': bool,
            'indicators': dict,
            'filters_passed': bool,
            'filter_failures': list,
        }
    """
    fisher_period = fisher_period or IndicatorConfig.FISHER_PERIOD
    dmi_period = dmi_period or IndicatorConfig.DMI_PERIOD
    ema_fast = ema_fast or IndicatorConfig.EMA_FAST
    ema_slow = ema_slow or IndicatorConfig.EMA_SLOW
    atr_period = atr_period or IndicatorConfig.ATR_PERIOD

    out = {
        "long_setup_ready": False,
        "short_setup_ready": False,
        "long_trigger_met": False,
        "short_trigger_met": False,
        "indicators": {},
        "filters_passed": False,
        "filter_failures": [],
    }

    try:
        # Calculate indicators
        indicators = _calculate_all_indicators(
            data_15m, data_1h, data_4h, current_price, fisher_period, dmi_period, ema_fast, ema_slow, atr_period
        )
        out["indicators"] = indicators
        if not indicators:
            return out

        filters_passed, failures = _check_filters_static(
            instrument, indicators, current_spread, current_time
        )
        out["filters_passed"] = filters_passed
        out["filter_failures"] = failures
        if not filters_passed:
            return out

        # 15m Fisher crossover (trigger)
        ft_crossover = Indicators.detect_crossover(
            indicators["fisher_15m"], indicators["fisher_trigger_15m"]
        )
        long_trigger_met = ft_crossover == "bullish"
        short_trigger_met = ft_crossover == "bearish"

        # Setup ready (no 15m required): 4H bias + 1H confirmation
        long_setup_ready = (
            IndicatorValidator.validate_4h_trend_bias_long(
                indicators["plus_di_4h"], indicators["minus_di_4h"], indicators["adx_4h"]
            )
            and IndicatorValidator.validate_1h_confirmation_long(
                indicators["plus_di_1h"],
                indicators["minus_di_1h"],
                indicators["adx_1h"],
                indicators["ema9_1h"],
                indicators["ema26_1h"],
                current_price,
            )
        )
        short_setup_ready = (
            IndicatorValidator.validate_4h_trend_bias_short(
                indicators["plus_di_4h"], indicators["minus_di_4h"], indicators["adx_4h"]
            )
            and IndicatorValidator.validate_1h_confirmation_short(
                indicators["plus_di_1h"],
                indicators["minus_di_1h"],
                indicators["adx_1h"],
                indicators["ema9_1h"],
                indicators["ema26_1h"],
                current_price,
            )
        )

        out["long_setup_ready"] = long_setup_ready
        out["short_setup_ready"] = short_setup_ready
        out["long_trigger_met"] = long_trigger_met and long_setup_ready
        out["short_trigger_met"] = short_trigger_met and short_setup_ready
        return out
    except Exception as e:
        logger.error(f"Error in get_setup_status: {e}")
        return out


def _calculate_all_indicators(
    data_15m: pd.DataFrame,
    data_1h: pd.DataFrame,
    data_4h: pd.DataFrame,
    current_price: float,
    fisher_period: int,
    dmi_period: int,
    ema_fast: int,
    ema_slow: int,
    atr_period: int,
) -> Dict:
    try:
        indicators = {}
        fisher_15m, fisher_trigger_15m = Indicators.fisher_transform(data_15m, period=fisher_period)
        indicators["fisher_15m"] = fisher_15m
        indicators["fisher_trigger_15m"] = fisher_trigger_15m
        plus_di_1h, minus_di_1h, adx_1h = Indicators.dmi(data_1h, period=dmi_period)
        indicators["plus_di_1h"] = plus_di_1h
        indicators["minus_di_1h"] = minus_di_1h
        indicators["adx_1h"] = adx_1h
        indicators["ema9_1h"] = Indicators.ema(data_1h["close"], period=ema_fast)
        indicators["ema26_1h"] = Indicators.ema(data_1h["close"], period=ema_slow)
        indicators["atr_1h"] = Indicators.atr(data_1h, period=atr_period)
        plus_di_4h, minus_di_4h, adx_4h = Indicators.dmi(data_4h, period=dmi_period)
        indicators["plus_di_4h"] = plus_di_4h
        indicators["minus_di_4h"] = minus_di_4h
        indicators["adx_4h"] = adx_4h
        indicators["current_price"] = current_price
        return indicators
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return {}


def _check_filters_static(
    instrument: str,
    indicators: Dict,
    current_spread: float,
    current_time: datetime,
) -> tuple:
    failures = []
    if FilterConfig.FILTER_ADX_4H_MINIMUM:
        adx_4h = indicators.get("adx_4h")
        if adx_4h is not None and len(adx_4h) > 0 and adx_4h.iloc[-1] < IndicatorConfig.ADX_THRESHOLD_MINIMUM:
            failures.append(f"ADX 4H ({adx_4h.iloc[-1]:.1f}) < {IndicatorConfig.ADX_THRESHOLD_MINIMUM}")
    if FilterConfig.FILTER_ADX_FALLING:
        adx_1h = indicators.get("adx_1h")
        if adx_1h is not None and len(adx_1h) >= 5 and Indicators.is_adx_falling(adx_1h, candles=4):
            failures.append("ADX 1H falling 4+ candles")
    if FilterConfig.FILTER_EMA_INTERTWINED:
        ema9 = indicators.get("ema9_1h")
        ema26 = indicators.get("ema26_1h")
        if ema9 is not None and ema26 is not None and len(ema9) > 0 and len(ema26) > 0:
            pip_value = InstrumentConfig.get_pip_value(instrument)
            ema_distance_pips = abs(ema9.iloc[-1] - ema26.iloc[-1]) / pip_value
            if ema_distance_pips < IndicatorConfig.EMA_INTERTWINED_THRESHOLD:
                failures.append(f"EMAs too close ({ema_distance_pips:.1f} pips)")
    if FilterConfig.FILTER_SESSION_HOURS:
        if not _is_approved_session(current_time):
            failures.append("Outside approved session")
    if FilterConfig.FILTER_SPREAD:
        max_spread = InstrumentConfig.MAX_SPREAD.get(instrument, 2.0)
        if current_spread > max_spread:
            failures.append(f"Spread {current_spread:.1f} > {max_spread} pips")
    return (len(failures) == 0, failures)


def _is_approved_session(current_time: datetime) -> bool:
    try:
        t = current_time.time()
        if SessionConfig.APPROVED_HOURS_START <= t <= SessionConfig.APPROVED_HOURS_END:
            if current_time.weekday() == 4 and t >= SessionConfig.FRIDAY_CUTOFF:
                return False
            if current_time.weekday() == 6 and t < time(SessionConfig.SUNDAY_BUFFER_HOURS, 0):
                return False
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking session: {e}")
        return False


class SignalGenerator:
    def __init__(self):
        self.fisher_period = IndicatorConfig.FISHER_PERIOD
        self.dmi_period = IndicatorConfig.DMI_PERIOD
        self.ema_fast = IndicatorConfig.EMA_FAST
        self.ema_slow = IndicatorConfig.EMA_SLOW
        self.atr_period = IndicatorConfig.ATR_PERIOD

    def generate_signal(
        self,
        instrument: str,
        data_15m: pd.DataFrame,
        data_1h: pd.DataFrame,
        data_4h: pd.DataFrame,
        current_price: float,
        current_spread: float,
        current_time: datetime,
    ) -> Dict:
        status = get_setup_status(
            instrument, data_15m, data_1h, data_4h, current_price, current_spread, current_time,
            self.fisher_period, self.dmi_period, self.ema_fast, self.ema_slow, self.atr_period,
        )
        signal = {
            "signal": "none",
            "confidence": "low",
            "reasons": [],
            "indicators": status.get("indicators", {}),
            "filters_passed": status["filters_passed"],
            "filter_failures": status.get("filter_failures", []),
        }
        if not status["filters_passed"]:
            signal["reasons"].append("Trade filters failed")
            return signal
        if status["long_trigger_met"]:
            signal["signal"] = "long"
            signal["confidence"] = "medium"
            signal["reasons"] = [
                "Fisher Transform bullish crossover (15m)",
                "4H trend bias confirmed",
                "1H confirmation validated",
                "All filters passed",
            ]
        elif status["short_trigger_met"]:
            signal["signal"] = "short"
            signal["confidence"] = "medium"
            signal["reasons"] = [
                "Fisher Transform bearish crossover (15m)",
                "4H trend bias confirmed",
                "1H confirmation validated",
                "All filters passed",
            ]
        else:
            if status["long_setup_ready"] and not status["long_trigger_met"]:
                signal["reasons"].append("Long setup ready; wait for 15m Fisher bullish crossover")
            elif status["short_setup_ready"] and not status["short_trigger_met"]:
                signal["reasons"].append("Short setup ready; wait for 15m Fisher bearish crossover")
            else:
                signal["reasons"].append("No setup ready or trigger")
        return signal


class SignalHistory:
    def __init__(self, max_history: int = 10):
        self.history: List[Dict] = []
        self.max_history = max_history

    def add_signal(self, instrument: str, signal: Dict, timestamp: datetime):
        self.history.append({
            "instrument": instrument,
            "signal": signal.get("signal", "none"),
            "timestamp": timestamp,
            "confidence": signal.get("confidence", "low"),
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

    def was_recent_signal(self, instrument: str, direction: str, minutes_ago: int = 30) -> bool:
        from datetime import datetime
        now = datetime.utcnow()
        for entry in reversed(self.history):
            if entry["instrument"] == instrument and entry["signal"] == direction:
                delta = (now - entry["timestamp"]).total_seconds() / 60
                if delta <= minutes_ago:
                    return True
        return False
