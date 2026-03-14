# Pair lists: Fisher vs FT-DMI-EMA

The codebase uses **two separate** environment variables for pair lists. There is no sharing between them.

## Fisher Transform (reversal opportunities)

| What | Source |
|------|--------|
| **Env var** | `FISHER_PAIRS` |
| **Code** | `src/scanners/fisher_daily_scanner.py` → `_get_fisher_pairs_from_env()` |
| **Default** | `DEFAULT_FISHER_PAIRS` (10 pairs: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY) |

**Used by:**

- `run_fisher_scan.py` – manual Fisher scan (creates `FisherDailyScanner(api)`; scanner uses `FISHER_PAIRS` or default).
- `scalp_engine.py` – hourly Fisher scan in trading hours (same: `FisherDailyScanner(self.oanda_api)` with no pairs arg).

Fisher opportunities are **never** built from `FT_DMI_EMA_PAIRS`.

---

## FT-DMI-EMA (4H+1H setup, 15m Fisher trigger)

| What | Source |
|------|--------|
| **Env var** | `FT_DMI_EMA_PAIRS` |
| **Code** | `src/ft_dmi_ema/ft_dmi_ema_config.py` → `InstrumentConfig.get_monitored_pairs()` → `_get_monitored_pairs()` |
| **Default** | `["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]` |

**Used by:**

- `run_ft_dmi_ema_scan.py` – manual FT-DMI-EMA scan.
- `scalp_engine.py` – `_inject_ft_dmi_ema_opportunities()` and `_check_ft_dmi_ema_opportunities_auto()` (via `FTInstrumentConfig` = same `InstrumentConfig`).

FT-DMI-EMA opportunities are **never** built from `FISHER_PAIRS`.

---

## Summary

- **Fisher** → **FISHER_PAIRS** only.
- **FT-DMI-EMA** → **FT_DMI_EMA_PAIRS** only.

You can set different lists per strategy (e.g. a shorter list for FT-DMI-EMA and a longer one for Fisher, or the other way around).
