"""Unit tests for MarketBridge utility methods — no file I/O or network required."""

import pytest
from unittest.mock import patch, MagicMock


def make_bridge():
    from src.market_bridge import MarketBridge
    with patch.object(MarketBridge, '__init__', lambda self, *a, **kw: None):
        b = MarketBridge.__new__(MarketBridge)
        b.filename = 'market_state.json'
        b.filepath = MagicMock()
        b.api_url = None
        b.api_key = None
    return b


# ---------------------------------------------------------------------------
# _calculate_usd_exposure
# ---------------------------------------------------------------------------

class TestCalculateUsdExposure:
    def test_usd_quote_buy_is_bearish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('EUR/USD', 'BUY') == 'BEARISH'

    def test_usd_quote_long_is_bearish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('GBP/USD', 'LONG') == 'BEARISH'

    def test_usd_quote_sell_is_bullish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('EUR/USD', 'SELL') == 'BULLISH'

    def test_usd_quote_short_is_bullish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('GBP/USD', 'SHORT') == 'BULLISH'

    def test_usd_base_buy_is_bullish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('USD/JPY', 'BUY') == 'BULLISH'

    def test_usd_base_long_is_bullish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('USD/CAD', 'LONG') == 'BULLISH'

    def test_usd_base_sell_is_bearish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('USD/JPY', 'SELL') == 'BEARISH'

    def test_usd_base_short_is_bearish(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('USD/CHF', 'SHORT') == 'BEARISH'

    def test_non_usd_pair_returns_none(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('EUR/GBP', 'BUY') is None

    def test_no_slash_format_usd_quote(self):
        """EURUSD (no slash) should still detect USD as quote."""
        b = make_bridge()
        assert b._calculate_usd_exposure('EURUSD', 'SELL') == 'BULLISH'

    def test_no_slash_format_usd_base(self):
        """USDJPY (no slash) should still detect USD as base."""
        b = make_bridge()
        assert b._calculate_usd_exposure('USDJPY', 'BUY') == 'BULLISH'

    def test_lowercase_direction(self):
        b = make_bridge()
        assert b._calculate_usd_exposure('EUR/USD', 'buy') == 'BEARISH'
