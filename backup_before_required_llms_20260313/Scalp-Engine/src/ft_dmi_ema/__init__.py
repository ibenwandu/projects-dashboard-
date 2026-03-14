"""
FT-DMI-EMA-ADX Multi-Timeframe Strategy (optional signal source and stop/profit logic).
"""

from .ft_dmi_ema_config import (
    InstrumentConfig,
    IndicatorConfig,
    TimeframeConfig,
    SessionConfig,
    FilterConfig,
    RiskConfig,
    ProfitProtectionConfig,
    ExitConfig,
)
from .indicators_ft_dmi_ema import Indicators, IndicatorValidator
from .signal_generator_ft_dmi_ema import SignalGenerator, SignalHistory, get_setup_status
from .stop_loss_calculator_ft_dmi_ema import StopLossCalculator, TimeStopMonitor
from .candle_adapter import fetch_ft_dmi_ema_dataframes, fetch_dmi_ema_dataframes
from .dmi_ema_setup import get_dmi_ema_setup_status

__all__ = [
    "InstrumentConfig",
    "IndicatorConfig",
    "TimeframeConfig",
    "SessionConfig",
    "FilterConfig",
    "RiskConfig",
    "ProfitProtectionConfig",
    "ExitConfig",
    "Indicators",
    "IndicatorValidator",
    "SignalGenerator",
    "SignalHistory",
    "get_setup_status",
    "StopLossCalculator",
    "TimeStopMonitor",
    "fetch_ft_dmi_ema_dataframes",
    "fetch_dmi_ema_dataframes",
    "get_dmi_ema_setup_status",
]
