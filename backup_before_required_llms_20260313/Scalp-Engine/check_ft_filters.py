"""Print FT-DMI-EMA filter on/off status. Run from Scalp-Engine directory: python check_ft_filters.py"""
import sys
import os
# Ensure project root is on path when run from Scalp-Engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from src.ft_dmi_ema.ft_dmi_ema_config import FilterConfig
    print("FT-DMI-EMA filter status (on/off):")
    print("  FILTER_ADX_4H_MINIMUM:", FilterConfig.FILTER_ADX_4H_MINIMUM)
    print("  FILTER_ADX_FALLING:", FilterConfig.FILTER_ADX_FALLING)
    print("  FILTER_EMA_INTERTWINED:", FilterConfig.FILTER_EMA_INTERTWINED)
    print("  FILTER_SESSION_HOURS:", FilterConfig.FILTER_SESSION_HOURS)
    print("  FILTER_SPREAD:", FilterConfig.FILTER_SPREAD)
except Exception as e:
    print("Error:", e)
    sys.exit(1)
