# How to Run Analysis (Trade-Alerts)

## Manual run (includes market state export)

To run analysis **immediately** and export market state for Scalp-Engine (Step 9), use **one** of:

```bash
# From Trade-Alerts repo root
python run_full_analysis.py
```

or

```bash
python run_immediate_analysis.py
```

Both run the **full workflow**: Drive → LLMs → Synthesis → RL enhancement → Email → **Step 9: Export market state** (and optional POST to market-state-api).

## Legacy name

- **`run_analysis_now.py`** – Same as above (delegates to full workflow). Use it if you already have scripts/cron calling this name; it now exports market state. Prefer `run_full_analysis.py` or `run_immediate_analysis.py` for clarity.

## Scheduled analysis

- **`main.py`** runs the analysis loop and triggers at configured times (e.g. 4pm EST).
- Ensure Trade-Alerts service is running and logs show `=== Scheduled Analysis Time: ...` and `Step 9 (NEW): Exporting market state...` then `✅ Market State exported...`.

## If market state is stale

See **DIAGNOSE_MISSING_MARKET_STATE.md** and **MARKET_STATE_STALE_CORRECTION_PLAN.md**.

**Temporary workaround** (timestamp only; content stays old until next full run):

From **repo root** in Render Shell (trade-alerts or scalp-engine-ui):

```bash
python update_market_state_timestamp.py
```

Requires the same disk as the market state file (e.g. shared disk with trade-alerts / scalp-engine-ui).
