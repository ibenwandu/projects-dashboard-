# Relating UI "Enabled" Trades to Logs

This doc explains how the **enabled** trades shown in the UI correspond to what appears in the scalp-engine logs.

## Shared sources of truth

| Source | What it holds | Used by |
|--------|----------------|---------|
| **Market state API** | List of all opportunities (e.g. 6 DMI-EMA). Engine POSTs opportunities; UI and engine both read from it. | UI (opportunity list), Engine (which pairs exist) |
| **Semi-auto config** (API or file) | Per-opportunity settings: `enabled`, `mode`, `max_runs`, `sl_type`, etc. Key = stable opportunity ID (e.g. `DMI_EMA_GBP/JPY_SHORT`). | UI (checkbox "Enable this trade"), Engine (filter to only process enabled) |

The **same** semi-auto config is used by the UI (when you check "Enable this trade" and Save) and by the engine (when it decides which opportunities to check). So the two stay in sync.

---

## Log lines that match the UI "Enabled" count

When you see **2 enabled** DMI-EMA trades in the UI (e.g. GBP/JPY SHORT and NZD/JPY SHORT), the logs will show:

| Log line | Meaning |
|----------|--------|
| `DMI-EMA: POSTing 6 DMI-EMA + 0 FT-DMI-EMA to market-state-api` | Engine sent 6 DMI-EMA opportunities to the market-state API. The UI loads this list; you see 6 DMI-EMA rows (some ENABLED, some DISABLED). |
| `SEMI_AUTO: 0 enabled LLM opportunity(ies) (of 4 total)` | LLM opportunities: 4 total, 0 enabled. Matches UI if no LLM trades are enabled. |
| **`DMI-EMA: 2 enabled (of 6 total) from semi-auto config`** | **This is the direct match:** 2 DMI-EMA opportunities are enabled in semi-auto config (same as the 2 you see as ENABLED in the UI). |
| **`DMI-EMA: Checking 2 enabled opportunity(ies)`** | Engine is now processing those same 2 enabled opportunities (GBP/JPY SHORT, NZD/JPY SHORT). |

So: **UI "2 ENABLED"** = **Log "2 enabled (of 6 total) from semi-auto config"** and **"Checking 2 enabled opportunity(ies)"**.

---

## Log lines that match each enabled trade by name

After the "Checking 2 enabled opportunity(ies)" line, you’ll see one or more lines per enabled pair from `PositionManager` or `ScalpEngine`:

| UI trade | Example log lines |
|----------|--------------------|
| **[DMI-EMA] GBP/JPY SHORT @ 208.6495** (ENABLED) | `Execution directive: WAIT_SIGNAL (MARKET) - GBP/JPY SHORT - DMI-EMA: Setup ready, waiting for 15m +DI/-DI crossover`<br>`Stored GBP/JPY SHORT, waiting for DMI_EMA_DMI_M15_TRIGGER` |
| **[DMI-EMA] NZD/JPY SHORT @ 92.4645** (ENABLED) | `Execution directive: WAIT_SIGNAL (MARKET) NZD/JPY SHORT DMI-EMA: Setup ready, waiting for 15m +DI/-DI crossover`<br>`Stored NZD/JPY SHORT, waiting for DMI_EMA_DMI_M15_TRIGGER` |

If you use "Reset run count", you may also see:

- `Reset run count for DMI_EMA_NZD/JPY_SHORT (user requested); opening trade`

So the **pair + direction** in the UI (e.g. GBP/JPY SHORT, NZD/JPY SHORT) is the same as in these log lines.

---

## Flow summary

1. **UI** loads market state → sees 6 DMI-EMA opportunities. For each, it reads semi-auto config by **stable ID** (e.g. `DMI_EMA_GBP/JPY_SHORT`) and shows **ENABLED** if `saved.enabled` is true.
2. **Engine** loads same market state → gets 6 DMI-EMA opportunities. It filters with `semi_auto.is_enabled(opp_id)` → 2 enabled → logs **"2 enabled (of 6 total) from semi-auto config"** and **"Checking 2 enabled opportunity(ies)"**.
3. For each of the 2 enabled opportunities, the engine runs checks and may log **Execution directive** and **Stored … waiting for …** for that pair/direction.

So: **same semi-auto config + same opportunity IDs** keep UI "enabled" and log "enabled" in sync; the log lines above are the ones that correspond to the enabled trades you see in the UI.
