"""
Fisher Activation Monitor
Monitors pending Fisher opportunities for H1/M15 crossover triggers.
Only activates in Semi-Auto or Manual mode — never full-auto.

Trigger semantics: Only activates on a crossover that happens AFTER the user
enabled the trade (stored_at). Stale crossovers that already existed when the
trade was enabled are ignored.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PENDING_SIGNALS_FILE = "/var/data/pending_signals.json"

# UI mode -> wait_for_signal value used in pending storage
TRIGGER_M15 = "M15_CROSSOVER"
TRIGGER_H1 = "H1_CROSSOVER"
TRIGGER_DMI_H1 = "DMI_H1_CROSSOVER"
TRIGGER_DMI_M15 = "DMI_M15_CROSSOVER"

# Bar duration for computing last bar close time (for freshness check)
_GRANULARITY_MINUTES = {'M15': 15, 'H1': 60, 'M5': 5, 'M30': 30}


def _parse_utc(s: str) -> Optional[datetime]:
    """Parse ISO string to datetime (timezone-aware UTC). Returns None on failure."""
    if not s:
        return None
    try:
        s = (s or '').strip().replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _last_bar_close_time(bar_start_str: str, granularity: str) -> Optional[datetime]:
    """Compute close time of a bar from its start time. E.g. M15 bar at 12:00 closes at 12:15."""
    dt = _parse_utc(bar_start_str)
    if not dt:
        return None
    mins = _GRANULARITY_MINUTES.get(granularity, 15)
    return dt + timedelta(minutes=mins)


def _ensure_oldest_first(items: List, times: List[str], granularity: str) -> Tuple[List, Optional[datetime]]:
    """
    Ensure items are ordered oldest-first. If first time > last time, reverse.
    Returns (items, last_bar_close_time) where last_bar_close_time is the close time
    of the last (most recent) bar for freshness check.
    """
    if not items or not times or len(items) != len(times):
        return (items, None)
    t0 = _parse_utc(times[0])
    t1 = _parse_utc(times[-1])
    if t0 is None or t1 is None:
        return (items, None)
    if t0 > t1:
        items = list(reversed(items))
        times = list(reversed(times))
    last_close = _last_bar_close_time(times[-1], granularity)
    return (items, last_close)


def _fetch_candles(oanda_client, pair: str, granularity: str, count: int = 50) -> Optional[Tuple[List[float], Optional[datetime]]]:
    """
    Fetch candle closes for pair/granularity (M15 or H1).
    Returns (closes, last_bar_close_time) with closes oldest-first, or None.
    last_bar_close_time is the close time of the most recent bar (for freshness vs stored_at).
    """
    try:
        from oandapyV20.endpoints.instruments import InstrumentsCandles
        oanda_pair = pair.replace('/', '_')
        params = {"count": count, "granularity": granularity, "price": "M"}
        r = InstrumentsCandles(instrument=oanda_pair, params=params)
        oanda_client.request(r)
        candles = r.response.get('candles', [])
        if not candles:
            return None
        closes = []
        times = []
        for c in candles:
            if isinstance(c, dict):
                mid = c.get('mid') or c.get('bid') or c.get('ask') or {}
                if isinstance(mid, dict):
                    cval = float(mid.get('c', 0) or mid.get('close', 0))
                else:
                    cval = 0.0
                t = c.get('time', '')
                if cval and t:
                    closes.append(cval)
                    times.append(t)
        if len(closes) < 20:
            return None
        closes, last_close = _ensure_oldest_first(closes, times, granularity)
        return (closes, last_close)
    except Exception as e:
        logger.debug("FisherActivationMonitor: fetch candles %s %s failed: %s", pair, granularity, e)
        return None


def _fetch_candles_hlc(oanda_client, pair: str, granularity: str, count: int = 50) -> Optional[Tuple[List[Dict], Optional[datetime]]]:
    """
    Fetch candle high/low/close for pair/granularity.
    Returns (list of dicts with high, low, close, oldest first, last_bar_close_time) or None.
    """
    try:
        from oandapyV20.endpoints.instruments import InstrumentsCandles
        oanda_pair = pair.replace('/', '_')
        params = {"count": count, "granularity": granularity, "price": "M"}
        r = InstrumentsCandles(instrument=oanda_pair, params=params)
        oanda_client.request(r)
        candles = r.response.get('candles', [])
        if not candles:
            return None
        out = []
        times = []
        for c in candles:
            if isinstance(c, dict):
                mid = c.get('mid') or c.get('bid') or c.get('ask') or {}
                if isinstance(mid, dict):
                    h = float(mid.get('h', 0) or mid.get('high', 0))
                    l = float(mid.get('l', 0) or mid.get('low', 0))
                    cl = float(mid.get('c', 0) or mid.get('close', 0))
                else:
                    h = l = cl = 0.0
                t = c.get('time', '')
                if h and l and cl and t:
                    out.append({'high': h, 'low': l, 'close': cl})
                    times.append(t)
        if len(out) < 30:
            return None
        out, last_close = _ensure_oldest_first(out, times, granularity)
        return (out, last_close)
    except Exception as e:
        logger.debug("FisherActivationMonitor: fetch HLC candles %s %s failed: %s", pair, granularity, e)
        return None


def _crossover_is_after_stored_at(stored_at_str: str, last_bar_close_time: Optional[datetime]) -> bool:
    """
    Only treat crossover as valid if it happened after the user enabled the trade.
    Returns True iff last_bar_close_time > stored_at (crossover is new, not stale).
    If last_bar_close_time is None or stored_at cannot be parsed, returns False (don't activate).
    """
    if not last_bar_close_time:
        return False
    stored = _parse_utc(stored_at_str)
    if not stored:
        return False
    return last_bar_close_time > stored


def _fisher_crossover_direction(closes: List[float], period: int = 9) -> Optional[str]:
    """
    Compute Fisher/Trigger on closes and detect crossover on the last bar.
    Returns 'BEARISH' (Fisher crossed below Trigger), 'BULLISH' (Fisher crossed above Trigger), or None.
    """
    try:
        from src.indicators.fisher_reversal_analyzer import _calculate_fisher_trigger
        fisher, trigger = _calculate_fisher_trigger(closes, period=period)
        if fisher is None or len(fisher) < 2:
            return None
        curr_f = float(fisher.iloc[-1])
        curr_t = float(trigger.iloc[-1])
        prev_f = float(fisher.iloc[-2])
        prev_t = float(trigger.iloc[-2])
        if prev_f > prev_t and curr_f < curr_t:
            return 'BEARISH'
        if prev_f < prev_t and curr_f > curr_t:
            return 'BULLISH'
        return None
    except Exception as e:
        logger.debug("FisherActivationMonitor: fisher crossover calc failed: %s", e)
        return None


def _direction_matches_opportunity(crossover: str, direction: str) -> bool:
    """True if crossover direction matches opportunity direction (SHORT->BEARISH, LONG->BULLISH)."""
    d = (direction or '').upper()
    if crossover == 'BEARISH':
        return d in ('SHORT', 'SELL')
    if crossover == 'BULLISH':
        return d in ('LONG', 'BUY')
    return False


def _dmi_crossover_direction(hlc_candles: List[Dict]) -> Optional[str]:
    """+DI/-DI crossover on last bar. Returns 'BULLISH', 'BEARISH', or None."""
    try:
        from src.indicators.dmi_analyzer import dmi_crossover_direction
        return dmi_crossover_direction(hlc_candles)
    except Exception as e:
        logger.debug("FisherActivationMonitor: DMI crossover calc failed: %s", e)
        return None


class FisherActivationMonitor:
    """
    Checks pending Fisher (and other) signals for activation (e.g. H1/M15 crossover).
    Does not execute in AUTO mode; used by scalp_engine when mode is SEMI_AUTO or MANUAL.
    """

    def __init__(self, pending_file: str = PENDING_SIGNALS_FILE):
        self.pending_file = pending_file
        self._pending: Dict = {}
        self._load()

    def _load(self):
        """Load pending signals from disk"""
        try:
            if os.path.exists(self.pending_file):
                with open(self.pending_file, 'r') as f:
                    self._pending = json.load(f)
                logger.debug("FisherActivationMonitor: Loaded %s pending signals", len(self._pending))
            else:
                self._pending = {}
        except Exception as e:
            logger.warning("Could not load pending signals: %s", e)
            self._pending = {}

    def get_pending_signals(self) -> Dict[str, Dict]:
        """Return all pending signals (signal_id -> {opportunity, directive, stored_at})."""
        return dict(self._pending)

    def get_pending_for_trigger(self, trigger: str) -> List[Dict]:
        """Return pending entries waiting for a given trigger (e.g. H1_CROSSOVER, M15_CROSSOVER)."""
        out = []
        for sid, data in self._pending.items():
            wait = (data.get('directive') or {}).get('wait_for_signal')
            if wait == trigger:
                out.append({'signal_id': sid, **data})
        return out

    def remove_pending(self, signal_id: str) -> bool:
        """Remove a pending signal (e.g. after activation or expiry)."""
        if signal_id in self._pending:
            del self._pending[signal_id]
            self._save()
            return True
        return False

    def _save(self):
        """Save pending signals to disk"""
        try:
            os.makedirs(os.path.dirname(self.pending_file) or '.', exist_ok=True)
            with open(self.pending_file, 'w') as f:
                json.dump(self._pending, f, indent=2)
        except Exception as e:
            logger.error("Error saving pending signals: %s", e)

    def check_activations(self, oanda_client, position_manager) -> List[Dict]:
        """
        Check pending Fisher and DMI signals for H1/M15 crossover activation.
        Only activates when:
          (1) crossover direction matches opportunity direction (SHORT->bearish, LONG->bullish), and
          (2) the crossover happened AFTER the user enabled the trade (last bar close time > stored_at).
        Stale crossovers that already existed when the trade was enabled are ignored.
        Returns list of activated items: [{'signal_id': str, 'opportunity': dict, 'directive': dict, 'stored_at': str}, ...].
        Caller must remove from pending and execute (e.g. open_trade with activation_trigger=IMMEDIATE).
        """
        self._load()
        activated: List[Dict] = []
        # Fisher H1/M15 and DMI H1/M15 triggers
        for trigger in (TRIGGER_M15, TRIGGER_H1, TRIGGER_DMI_H1, TRIGGER_DMI_M15):
            granularity = 'M15' if trigger in (TRIGGER_M15, TRIGGER_DMI_M15) else 'H1'
            for item in self.get_pending_for_trigger(trigger):
                signal_id = item.get('signal_id', '')
                opportunity = item.get('opportunity', {})
                directive = item.get('directive', {})
                pair = opportunity.get('pair', '')
                direction = opportunity.get('direction', '').upper()
                stored_at = item.get('stored_at', '')
                if not pair:
                    continue
                if trigger in (TRIGGER_DMI_H1, TRIGGER_DMI_M15):
                    result = _fetch_candles_hlc(oanda_client, pair, granularity, count=50)
                    if not result:
                        continue
                    hlc_candles, last_bar_close_time = result
                    crossover = _dmi_crossover_direction(hlc_candles)
                else:
                    result = _fetch_candles(oanda_client, pair, granularity, count=50)
                    if not result:
                        continue
                    closes, last_bar_close_time = result
                    crossover = _fisher_crossover_direction(closes, period=9)
                if not crossover or not _direction_matches_opportunity(crossover, direction):
                    continue
                # Only trigger on NEW crossover: last bar must have closed after user enabled the trade
                if not _crossover_is_after_stored_at(stored_at, last_bar_close_time):
                    logger.debug(
                        "FisherActivationMonitor: SKIP %s %s - crossover on bar closed before stored_at (stale)",
                        pair, direction
                    )
                    continue
                logger.info(
                    "FisherActivationMonitor: ACTIVATED %s %s (signal_id=%s) - %s crossover on %s (new, after enable)",
                    pair, direction, signal_id, crossover, granularity
                )
                activated.append({
                    'signal_id': signal_id,
                    'opportunity': opportunity,
                    'directive': directive,
                    'stored_at': stored_at,
                })
        return activated


__all__ = [
    'FisherActivationMonitor', 'PENDING_SIGNALS_FILE',
    'TRIGGER_M15', 'TRIGGER_H1', 'TRIGGER_DMI_M15', 'TRIGGER_DMI_H1',
]
