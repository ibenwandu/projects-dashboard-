"""Unit tests for src/protocols.py — verify runtime_checkable isinstance checks."""

import pytest
from src.protocols import PriceProvider, NotificationService, MarketStateWriter


# ---------------------------------------------------------------------------
# Helper: minimal concrete implementations
# ---------------------------------------------------------------------------

class GoodPriceProvider:
    def get_rate(self, pair: str):
        return 1.0850


class GoodNotificationService:
    def send_entry_alert(self, opportunity: dict, current_price: float) -> bool:
        return True


class GoodMarketStateWriter:
    def export_market_state(self, *args, **kwargs):
        return {}


class MissingGetRate:
    """Has the wrong method name."""
    def fetch_rate(self, pair: str):
        return 1.0


class MissingSendEntryAlert:
    def notify(self, opp, price):
        return True


class MissingExportMarketState:
    def write_state(self):
        pass


# ---------------------------------------------------------------------------
# PriceProvider
# ---------------------------------------------------------------------------

class TestPriceProviderProtocol:
    def test_conforming_class_passes_isinstance(self):
        assert isinstance(GoodPriceProvider(), PriceProvider)

    def test_non_conforming_class_fails_isinstance(self):
        assert not isinstance(MissingGetRate(), PriceProvider)

    def test_plain_object_fails(self):
        assert not isinstance(object(), PriceProvider)


# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------

class TestNotificationServiceProtocol:
    def test_conforming_class_passes_isinstance(self):
        assert isinstance(GoodNotificationService(), NotificationService)

    def test_non_conforming_class_fails_isinstance(self):
        assert not isinstance(MissingSendEntryAlert(), NotificationService)


# ---------------------------------------------------------------------------
# MarketStateWriter
# ---------------------------------------------------------------------------

class TestMarketStateWriterProtocol:
    def test_conforming_class_passes_isinstance(self):
        assert isinstance(GoodMarketStateWriter(), MarketStateWriter)

    def test_non_conforming_class_fails_isinstance(self):
        assert not isinstance(MissingExportMarketState(), MarketStateWriter)
