"""
DMI-EMA setup: 1D/4H/1H DMI alignment + 1H EMA (not intertwined). Confidence flags only (FT crossover, ADX>20).
"""

import pandas as pd
from typing import Dict
from datetime import datetime
import logging

from .indicators_ft_dmi_ema import Indicators
from .ft_dmi_ema_config import IndicatorConfig, InstrumentConfig

logger = logging.getLogger(__name__)


def get_dmi_ema_setup_status(
    instrument: str,
    data_1d: pd.DataFrame,
    data_4h: pd.DataFrame,
    data_1h: pd.DataFrame,
    data_15m: pd.DataFrame,
    current_price: float,
    current_spread: float,
    current_time: datetime,
    dmi_period: int = None,
    ema_fast: int = None,
    ema_slow: int = None,
    fisher_period: int = None,
    ema_distance_pips_threshold: float = None,
) -> Dict:
    """
    DMI-EMA: required = +DI>-DI (1D,4H,1H) for long (reverse for short), 1H EMA9>26 (or <26 short), distance >= threshold pips.
    Confidence flags only: ft_1h, ft_15m, adx_15m, adx_1h, adx_4h.
    Returns ft_15m_trigger_met (15m Fisher crossover) for execution path.
    """
    dmi_period = dmi_period or IndicatorConfig.DMI_PERIOD
    ema_fast = ema_fast or IndicatorConfig.EMA_FAST
    ema_slow = ema_slow or IndicatorConfig.EMA_SLOW
    fisher_period = fisher_period or IndicatorConfig.FISHER_PERIOD
    threshold = ema_distance_pips_threshold if ema_distance_pips_threshold is not None else IndicatorConfig.EMA_INTERTWINED_THRESHOLD

    out = {
        "long_setup_ready": False,
        "short_setup_ready": False,
        "long_trigger_met": False,
        "short_trigger_met": False,
        "ft_15m_trigger_met": False,
        "long_dmi_15m_trigger_met": False,
        "short_dmi_15m_trigger_met": False,
        "dmi_15m_trigger_met": False,
        "confidence_flags": {
            "ft_1h": False,
            "ft_15m": False,
            "dmi_15m": False,
            "adx_15m": False,
            "adx_1h": False,
            "adx_4h": False,
        },
    }

    try:
        if data_1d is None or len(data_1d) < 1 or data_4h is None or len(data_4h) < 1:
            return out
        if data_1h is None or len(data_1h) < 1 or data_15m is None or len(data_15m) < 2:
            return out

        # DMI 1D, 4H, 1H
        plus_di_1d, minus_di_1d, adx_1d = Indicators.dmi(data_1d, period=dmi_period)
        plus_di_4h, minus_di_4h, adx_4h = Indicators.dmi(data_4h, period=dmi_period)
        plus_di_1h, minus_di_1h, adx_1h = Indicators.dmi(data_1h, period=dmi_period)
        plus_di_15m, minus_di_15m, adx_15m = Indicators.dmi(data_15m, period=dmi_period)

        # EMA 1H
        ema9_1h = Indicators.ema(data_1h["close"], period=ema_fast)
        ema26_1h = Indicators.ema(data_1h["close"], period=ema_slow)

        pip_value = InstrumentConfig.get_pip_value(instrument)
        ema_dist_pips = abs(ema9_1h.iloc[-1] - ema26_1h.iloc[-1]) / pip_value if len(ema9_1h) and len(ema26_1h) else 0.0

        # Required: 1D/4H/1H +DI > -DI for long
        long_dmi_ok = (
            len(plus_di_1d) and len(minus_di_1d) and plus_di_1d.iloc[-1] > minus_di_1d.iloc[-1]
            and len(plus_di_4h) and len(minus_di_4h) and plus_di_4h.iloc[-1] > minus_di_4h.iloc[-1]
            and len(plus_di_1h) and len(minus_di_1h) and plus_di_1h.iloc[-1] > minus_di_1h.iloc[-1]
        )
        short_dmi_ok = (
            len(minus_di_1d) and len(plus_di_1d) and minus_di_1d.iloc[-1] > plus_di_1d.iloc[-1]
            and len(minus_di_4h) and len(plus_di_4h) and minus_di_4h.iloc[-1] > plus_di_4h.iloc[-1]
            and len(minus_di_1h) and len(plus_di_1h) and minus_di_1h.iloc[-1] > plus_di_1h.iloc[-1]
        )

        long_ema_ok = len(ema9_1h) and len(ema26_1h) and ema9_1h.iloc[-1] > ema26_1h.iloc[-1] and ema_dist_pips >= threshold
        short_ema_ok = len(ema9_1h) and len(ema26_1h) and ema9_1h.iloc[-1] < ema26_1h.iloc[-1] and ema_dist_pips >= threshold

        out["long_setup_ready"] = long_dmi_ok and long_ema_ok
        out["short_setup_ready"] = short_dmi_ok and short_ema_ok

        # Confidence: Fisher crossover 1H and 15m
        fisher_1h, trigger_1h = Indicators.fisher_transform(data_1h, period=fisher_period)
        fisher_15m, trigger_15m = Indicators.fisher_transform(data_15m, period=fisher_period)
        cross_1h = Indicators.detect_crossover(fisher_1h, trigger_1h) if len(fisher_1h) >= 2 and len(trigger_1h) >= 2 else "none"
        cross_15m = Indicators.detect_crossover(fisher_15m, trigger_15m) if len(fisher_15m) >= 2 and len(trigger_15m) >= 2 else "none"

        out["confidence_flags"]["ft_1h"] = cross_1h == "bullish" or cross_1h == "bearish"
        out["confidence_flags"]["ft_15m"] = cross_15m == "bullish" or cross_15m == "bearish"
        out["confidence_flags"]["adx_15m"] = len(adx_15m) and adx_15m.iloc[-1] > 20
        out["confidence_flags"]["adx_1h"] = len(adx_1h) and adx_1h.iloc[-1] > 20
        out["confidence_flags"]["adx_4h"] = len(adx_4h) and adx_4h.iloc[-1] > 20

        # 15m +DI/-DI crossover: confidence flag and trigger option
        dmi_cross_15m = Indicators.detect_crossover(plus_di_15m, minus_di_15m) if len(plus_di_15m) >= 2 and len(minus_di_15m) >= 2 else "none"
        out["confidence_flags"]["dmi_15m"] = dmi_cross_15m == "bullish" or dmi_cross_15m == "bearish"

        # 15m Fisher trigger for execution (same as FT-DMI-EMA)
        long_trigger = out["long_setup_ready"] and cross_15m == "bullish"
        short_trigger = out["short_setup_ready"] and cross_15m == "bearish"
        out["long_trigger_met"] = long_trigger
        out["short_trigger_met"] = short_trigger
        out["ft_15m_trigger_met"] = long_trigger or short_trigger

        # 15m +DI/-DI trigger (alternative to Fisher 15m)
        long_dmi_15m_trigger = out["long_setup_ready"] and dmi_cross_15m == "bullish"
        short_dmi_15m_trigger = out["short_setup_ready"] and dmi_cross_15m == "bearish"
        out["long_dmi_15m_trigger_met"] = long_dmi_15m_trigger
        out["short_dmi_15m_trigger_met"] = short_dmi_15m_trigger
        out["dmi_15m_trigger_met"] = long_dmi_15m_trigger or short_dmi_15m_trigger

        return out
    except Exception as e:
        logger.error(f"Error in get_dmi_ema_setup_status: {e}")
        return out
