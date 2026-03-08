"""
FT-DMI-EMA candle adapter: fetch 15m/1H/4H (and optional 1D for DMI-EMA) via Scalp-Engine OANDA and return DataFrames.
"""

import pandas as pd
from typing import Optional, Callable, Tuple

# OANDA granularity: M15, H1, H4, D
GRANULARITY_15M = "M15"
GRANULARITY_1H = "H1"
GRANULARITY_4H = "H4"
GRANULARITY_1D = "D"
CANDLE_COUNT = 500


def fetch_dmi_ema_dataframes(
    get_candles_fn: Callable[[str, str, int], Optional[list]],
    instrument_oanda: str,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Fetch 1D, 4H, 1H, 15m candles for DMI-EMA (requires Daily).
    instrument_oanda: OANDA format (e.g. EUR_USD).
    Returns (data_1d, data_4h, data_1h, data_15m); any can be None on failure.
    """
    data_1d = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_1D, CANDLE_COUNT)
    )
    data_4h = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_4H, CANDLE_COUNT)
    )
    data_1h = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_1H, CANDLE_COUNT)
    )
    data_15m = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_15M, CANDLE_COUNT)
    )
    return data_1d, data_4h, data_1h, data_15m


def fetch_ft_dmi_ema_dataframes(
    get_candles_fn: Callable[[str, str, int], Optional[list]],
    instrument_oanda: str,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Fetch 15m, 1H, 4H candles using the provided get_candles function (e.g. OandaClient.get_candles).
    instrument_oanda: OANDA format (e.g. EUR_USD).
    Returns (data_15m, data_1h, data_4h); any can be None on failure.
    """
    data_15m = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_15M, CANDLE_COUNT)
    )
    data_1h = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_1H, CANDLE_COUNT)
    )
    data_4h = _candles_to_dataframe(
        get_candles_fn(instrument_oanda, GRANULARITY_4H, CANDLE_COUNT)
    )
    return data_15m, data_1h, data_4h


def _candles_to_dataframe(candles: Optional[list]) -> Optional[pd.DataFrame]:
    if not candles or len(candles) == 0:
        return None
    try:
        df = pd.DataFrame(candles)
        required = ["open", "high", "low", "close"]
        for col in required:
            if col not in df.columns:
                return None
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=required)
        if len(df) == 0:
            return None
        return df
    except Exception:
        return None


def pair_to_oanda(pair: str) -> str:
    """Convert pair to OANDA instrument (e.g. EUR/USD -> EUR_USD)."""
    return pair.replace("/", "_").replace("-", "_").strip()


def oanda_to_pair(instrument: str) -> str:
    """Convert OANDA instrument to pair (e.g. EUR_USD -> EUR/USD)."""
    return instrument.replace("_", "/")
