"""
FT-DMI-EMA strategy configuration (strategy params only; OANDA creds from env/Scalp-Engine).
"""

import os
from datetime import time

# Pairs: env first, then default list (no config file).
# Set FT_DMI_EMA_PAIRS (comma-separated, e.g. EUR_USD,GBP_USD) to use env; if empty/unset, use default below.
def _get_monitored_pairs():
    env_pairs = os.getenv("FT_DMI_EMA_PAIRS", "").strip()
    if env_pairs:
        return [p.strip().replace("/", "_") for p in env_pairs.split(",") if p.strip()]
    return ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]


class InstrumentConfig:
    MAX_SPREAD = {
        "EUR_USD": 1.5,
        "GBP_USD": 2.0,
        "USD_JPY": 1.8,
        "AUD_USD": 1.8,
        "EUR_GBP": 2.0,
        "USD_CAD": 2.0,
        "NZD_USD": 2.0,
    }
    PIP_LOCATION = {"JPY": 0.01, "default": 0.0001}

    @classmethod
    def get_pip_value(cls, instrument: str) -> float:
        if "JPY" in instrument:
            return cls.PIP_LOCATION["JPY"]
        return cls.PIP_LOCATION["default"]

    @classmethod
    def get_monitored_pairs(cls) -> list:
        return _get_monitored_pairs()


class IndicatorConfig:
    FISHER_PERIOD = 10
    DMI_PERIOD = 14
    ADX_THRESHOLD_STRONG = 25
    ADX_THRESHOLD_EMERGING = 20
    ADX_THRESHOLD_MINIMUM = 18
    ADX_FALLING_CANDLES = 4
    EMA_FAST = 9
    EMA_SLOW = 26
    EMA_INTERTWINED_THRESHOLD = 5
    ATR_PERIOD = 14
    ATR_MULTIPLIER_STRUCTURE = 2.0
    ATR_MULTIPLIER_SESSION = 2.2
    ATR_MULTIPLIER_SIMPLIFIED = 1.8
    TIME_STOP_ENABLED = True


class TimeframeConfig:
    GRANULARITY_MAP = {"15m": "M15", "1H": "H1", "4H": "H4", "D": "D"}
    CANDLE_COUNTS = {"15m": 500, "1H": 500, "4H": 500, "D": 500}
    SWING_LOOKBACK = 2


class SessionConfig:
    APPROVED_HOURS_START = time(8, 0)
    APPROVED_HOURS_END = time(20, 0)
    SESSION_OPEN_WINDOWS = [(time(8, 0), time(9, 0)), (time(13, 0), time(14, 0))]
    FRIDAY_CUTOFF = time(16, 0)
    SUNDAY_BUFFER_HOURS = 4


class FilterConfig:
    FILTER_ADX_4H_MINIMUM = True
    FILTER_ADX_FALLING = True  # ADX 1H must not be falling for 4 candles
    FILTER_EMA_INTERTWINED = True
    FILTER_SESSION_HOURS = True
    FILTER_SPREAD = True


class RiskConfig:
    RISK_PER_TRADE_DEFAULT = 0.01
    MAX_OPEN_POSITIONS = 3
    MAX_STOP_DISTANCE_PERCENT = 0.025
    MIN_STOP_DISTANCE_PERCENT = 0.005


class ProfitProtectionConfig:
    BREAKEVEN_R_MULTIPLE = 1.0
    PARTIAL_PROFIT_R_MULTIPLE = 2.0
    PARTIAL_PROFIT_CLOSE_PERCENT = 0.5
    TRAILING_R_MULTIPLE = 3.0
    TIME_STOP_ENABLED = True
    TIME_STOP_HOURS = 8
    TIME_STOP_R_RANGE = (-0.3, 0.3)


class ExitConfig:
    SPREAD_SPIKE_MULTIPLIER = 3.0
    ADX_COLLAPSE_THRESHOLD = 15
