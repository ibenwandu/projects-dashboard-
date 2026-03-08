# Stable opportunity ID

Semi-auto config and run count are keyed by a **stable opportunity ID** so that:

1. **Re-enable** (disabled → enabled + Save) is found by the engine when it looks up config.
2. **Reset run count** (button or re-enable) clears the same run count the enforcer checks.

## Canonical key

- **Definition:** `src/execution/opportunity_id.py` → `get_stable_opportunity_id(opportunity)`.
- **Format:** `{PAIR}_{DIRECTION}` with:
  - **Pair:** `(opportunity['pair'] or '').strip().replace('_', '/').upper()` (e.g. `USD/JPY`).
  - **Direction:** `LONG` for BUY/LONG, `SHORT` for SELL/SHORT.
- **Example:** `USD/JPY_SHORT` for USD/JPY SELL (or SHORT).

Opportunity `id` from market state or API is **not** used for this key, so the same logical trade (pair + direction) always maps to the same key.

## Where it is used

| Component | Use |
|-----------|-----|
| **UI (scalp_ui)** | Semi-Auto Approval: save/load per-opportunity config (enabled, mode, max_runs, reset_run_count_requested) under `get_stable_opportunity_id(opp)`. |
| **Engine (scalp_engine)** | Look up semi-auto config and request run-count reset by the same stable ID before opening a trade. |
| **Enforcer (execution_mode_enforcer)** | Run count (execution history) is keyed by `get_stable_opportunity_id(opportunity)`. |
| **PositionManager (auto_trader_core)** | When recording execution, uses `get_stable_opportunity_id(opportunity)` so the enforcer’s run count uses the same key. |

## Backward compatibility

- `execution_mode_enforcer` still exports `get_stable_opp_id` as an alias of `get_stable_opportunity_id`.
- If `opportunity_id` cannot be imported, call sites fall back to `f"{pair}_{direction}"` (or similar) so behavior degrades gracefully.
