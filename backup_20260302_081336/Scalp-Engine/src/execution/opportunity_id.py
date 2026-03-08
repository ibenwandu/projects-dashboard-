"""
Canonical opportunity ID for run count and semi-auto config.

Single source of truth: UI (Semi-Auto Approval), engine (scalp_engine, _maybe_reset_run_count),
enforcer (get_execution_directive, execution_history), and auto_trader_core (record_execution)
must all use this same key so that:
- Re-enabling an opportunity in the UI finds the same semi-auto config and reset_run_count_requested.
- Run count is checked and recorded under the same key, so "Reset run count" and re-enable work.

IDs are source-aware: format is {source}_{pair}_{direction} so that LLM and DMI-EMA (and Fisher,
FT-DMI-EMA) each have separate config and run count for the same pair/direction.
"""

from typing import Dict, Optional

# Canonical source labels (storage/API). UI may display e.g. "FT-DMI-EMA" or "DMI-EMA".
CANONICAL_SOURCES = ('LLM', 'Fisher', 'FT_DMI_EMA', 'DMI_EMA')


def _normalize_pair_direction(opportunity: Dict) -> tuple:
    """Return (pair, direction) normalized. pair e.g. USD/JPY, direction LONG or SHORT."""
    pair_raw = (opportunity.get('pair') or '').strip().replace('_', '/')
    pair = pair_raw.upper() if pair_raw else ''
    direction_raw = (opportunity.get('direction') or '').strip().upper()
    direction = (
        'LONG' if direction_raw in ('LONG', 'BUY') else
        'SHORT' if direction_raw in ('SHORT', 'SELL') else
        direction_raw
    )
    return pair, direction


def get_stable_opportunity_id(opportunity: Dict, source: Optional[str] = None) -> str:
    """
    Stable opportunity ID from source + pair + direction.
    Normalizes so UI and engine always use the same key for config and run count.

    - source: LLM | Fisher | FT_DMI_EMA | DMI_EMA. If None, derived from opportunity.get('source').
    - Pair: strip, replace '_' with '/', uppercase (e.g. USD_JPY -> USD/JPY).
    - Direction: LONG for BUY/LONG, SHORT for SELL/SHORT.

    Returns:
        e.g. "LLM_USD/JPY_SHORT", "DMI_EMA_USD/JPY_SHORT".
        Fallback to opportunity.get('id') or '' if pair/direction empty.
    """
    pair, direction = _normalize_pair_direction(opportunity)
    if not pair or not direction:
        return (opportunity.get('id') or '')

    if source is None:
        raw = (opportunity.get('source') or '').strip()
        if raw in CANONICAL_SOURCES:
            source = raw
        elif raw in ('FT-DMI-EMA', 'FT_DMI_EMA'):
            source = 'FT_DMI_EMA'
        elif raw in ('DMI-EMA', 'DMI_EMA'):
            source = 'DMI_EMA'
        else:
            source = 'LLM'

    return f"{source}_{pair}_{direction}"


def get_legacy_opportunity_id(opportunity: Dict) -> str:
    """
    Legacy ID (pair_direction only, no source). Used for backward-compat config/run-count lookup.
    """
    pair, direction = _normalize_pair_direction(opportunity)
    if pair and direction:
        return f"{pair}_{direction}"
    return (opportunity.get('id') or '')


__all__ = ['get_stable_opportunity_id', 'get_legacy_opportunity_id', 'CANONICAL_SOURCES']
