"""
FT-DMI-EMA stop loss: Structure + ATR buffer and TimeStopMonitor.
"""

import pandas as pd
from typing import Optional, Tuple, Dict
from datetime import datetime
import logging

from .indicators_ft_dmi_ema import Indicators
from .ft_dmi_ema_config import (
    IndicatorConfig,
    TimeframeConfig,
    InstrumentConfig,
    RiskConfig,
    SessionConfig,
    ProfitProtectionConfig,
)

logger = logging.getLogger(__name__)


class StopLossCalculator:
    def __init__(self):
        self.atr_multiplier_normal = IndicatorConfig.ATR_MULTIPLIER_STRUCTURE
        self.atr_multiplier_session = IndicatorConfig.ATR_MULTIPLIER_SESSION
        self.swing_lookback = TimeframeConfig.SWING_LOOKBACK

    def calculate_stop_loss(
        self,
        data_1h: pd.DataFrame,
        entry_price: float,
        direction: str,
        entry_time: Optional[datetime] = None,
        instrument: str = "EUR_USD",
    ) -> Dict:
        try:
            atr = Indicators.atr(data_1h, period=IndicatorConfig.ATR_PERIOD)
            current_atr = atr.iloc[-1]
            if pd.isna(current_atr) or current_atr <= 0:
                return self._fallback_stop_loss(entry_price, direction, instrument)
            atr_multiplier = self._get_atr_multiplier(entry_time)
            if direction == "long":
                structural_level = Indicators.find_swing_low(data_1h, lookback=self.swing_lookback)
                if structural_level is None:
                    structural_level = data_1h["low"].tail(20).min()
                stop_loss_price = structural_level - (current_atr * atr_multiplier)
            else:
                structural_level = Indicators.find_swing_high(data_1h, lookback=self.swing_lookback)
                if structural_level is None:
                    structural_level = data_1h["high"].tail(20).max()
                stop_loss_price = structural_level + (current_atr * atr_multiplier)
            pip_value = InstrumentConfig.get_pip_value(instrument)
            stop_distance_pips = abs(entry_price - stop_loss_price) / pip_value
            return {
                "stop_loss_price": round(stop_loss_price, 5),
                "stop_distance_pips": stop_distance_pips,
                "method": "Structure + ATR Buffer",
                "structural_level": structural_level,
                "atr_value": current_atr,
                "atr_multiplier": atr_multiplier,
                "details": f"Structural: {structural_level:.5f}, ATR: {current_atr:.5f}, Distance: {stop_distance_pips:.1f} pips",
            }
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return self._fallback_stop_loss(entry_price, direction, instrument)

    def _get_atr_multiplier(self, entry_time: Optional[datetime]) -> float:
        if entry_time is None:
            return self.atr_multiplier_normal
        t = entry_time.time()
        for window_start, window_end in SessionConfig.SESSION_OPEN_WINDOWS:
            if window_start <= t <= window_end:
                return self.atr_multiplier_session
        return self.atr_multiplier_normal

    def _fallback_stop_loss(self, entry_price: float, direction: str, instrument: str = "EUR_USD") -> Dict:
        assumed_atr = 0.0015
        multiplier = IndicatorConfig.ATR_MULTIPLIER_SIMPLIFIED
        if direction == "long":
            stop_loss_price = entry_price - (assumed_atr * multiplier)
        else:
            stop_loss_price = entry_price + (assumed_atr * multiplier)
        pip_value = InstrumentConfig.get_pip_value(instrument)
        stop_distance_pips = abs(entry_price - stop_loss_price) / pip_value
        return {
            "stop_loss_price": round(stop_loss_price, 5),
            "stop_distance_pips": stop_distance_pips,
            "method": "Simplified ATR (Fallback)",
            "structural_level": None,
            "atr_value": assumed_atr,
            "atr_multiplier": multiplier,
            "details": f"Fallback, Distance: {stop_distance_pips:.1f} pips",
        }

    def validate_stop_distance(
        self,
        stop_distance_pips: float,
        account_balance: float,
        instrument: str,
    ) -> Tuple[bool, str]:
        try:
            max_risk_dollars = account_balance * RiskConfig.MAX_STOP_DISTANCE_PERCENT
            estimated_dollar_per_pip = 1.0
            max_stop_pips = max_risk_dollars / estimated_dollar_per_pip
            if stop_distance_pips > max_stop_pips:
                return False, f"Stop too wide: {stop_distance_pips:.1f} pips exceeds max {max_stop_pips:.1f} pips"
            min_risk_dollars = account_balance * RiskConfig.MIN_STOP_DISTANCE_PERCENT
            min_stop_pips = min_risk_dollars / estimated_dollar_per_pip
            if stop_distance_pips < min_stop_pips:
                return False, f"Stop too tight: {stop_distance_pips:.1f} pips below min {min_stop_pips:.1f} pips"
            return True, "Stop distance acceptable"
        except Exception as e:
            logger.error(f"Error validating stop distance: {e}")
            return False, str(e)


class TimeStopMonitor:
    def __init__(self):
        self.enabled = getattr(ProfitProtectionConfig, "TIME_STOP_ENABLED", True)
        self.time_stop_hours = getattr(ProfitProtectionConfig, "TIME_STOP_HOURS", 8)
        self.r_range = getattr(ProfitProtectionConfig, "TIME_STOP_R_RANGE", (-0.3, 0.3))

    def should_exit_on_time(
        self,
        entry_time: datetime,
        current_time: datetime,
        current_r_multiple: float,
    ) -> Tuple[bool, str]:
        if not self.enabled:
            return False, "Time stop disabled"
        try:
            hours_elapsed = (current_time - entry_time).total_seconds() / 3600
            if hours_elapsed < self.time_stop_hours:
                return False, f"Time elapsed: {hours_elapsed:.1f}h < {self.time_stop_hours}h"
            if self.r_range[0] <= current_r_multiple <= self.r_range[1]:
                return True, (
                    f"Time stop: {hours_elapsed:.1f}h elapsed, R={current_r_multiple:.2f} in stagnation range"
                )
            return False, f"R-multiple {current_r_multiple:.2f}R outside stagnation range"
        except Exception as e:
            logger.error(f"Error checking time stop: {e}")
            return False, str(e)
