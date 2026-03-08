"""
Protocol definitions for Trade-Alerts components.

These Protocols describe the interfaces that core components must satisfy,
enabling type-safe dependency injection, mocking in tests, and future
alternative implementations without touching call sites.

Usage:
    from src.protocols import PriceProvider, NotificationService

    def check_entry(pair: str, monitor: PriceProvider) -> bool:
        rate = monitor.get_rate(pair)
        ...
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class PriceProvider(Protocol):
    """Interface for anything that can supply live currency exchange rates."""

    def get_rate(self, pair: str) -> Optional[float]:
        """Return the current mid-price for *pair* (e.g. 'EUR/USD'), or None on failure."""
        ...


@runtime_checkable
class NotificationService(Protocol):
    """Interface for alert/notification delivery."""

    def send_entry_alert(self, opportunity: dict, current_price: float) -> bool:
        """Send an entry-point alert for *opportunity*. Returns True on success."""
        ...


@runtime_checkable
class MarketStateWriter(Protocol):
    """Interface for anything that persists the market state for downstream consumers."""

    def export_market_state(self, *args, **kwargs) -> Optional[dict]:
        """Export the current market state. Returns the state dict, or None on failure."""
        ...
