# Disk Relationships - All Services

## Current Configuration (from render.yaml)

All 4 services are configured to use the **same disk name**: `shared-market-data`

### Service Relationships:

```
┌─────────────────┐
│  trade-alerts   │  Writes: market_state.json
│  Disk: shared   │  Reads:  (none from disk)
└────────┬────────┘
         │ writes to /var/data/market_state.json
         ▼
┌─────────────────┐
│  scalp-engine   │  Reads:  market_state.json
│  Disk: shared   │  Writes: auto_trader_config.json (read by UI)
│                 │  Writes: trade_states.json
└────────┬────────┘
         │ reads/writes /var/data/auto_trader_config.json
         │
         ▼
┌─────────────────┐
│ scalp-engine-ui │  Reads:  market_state.json
│  Disk: shared   │  Reads:  auto_trader_config.json
│                 │  Writes: auto_trader_config.json (read by engine)
│                 │  Reads:  trade_states.json
└─────────────────┘

┌─────────────────┐
│market-state-api │  Reads:  market_state.json
│  Disk: shared   │  Writes: market_state.json (alternative path)
└─────────────────┘
```

## File Sharing Requirements

### 1. `market_state.json` (Written by trade-alerts, read by others)
- **trade-alerts** → **scalp-engine**: ✅ **MUST SHARE** (critical for trading decisions)
- **trade-alerts** → **scalp-engine-ui**: ✅ **MUST SHARE** (UI displays market state)
- **trade-alerts** → **market-state-api**: ✅ **MUST SHARE** (API reads/writes state)

### 2. `auto_trader_config.json` (Written by UI, read by engine)
- **scalp-engine-ui** → **scalp-engine**: ✅ **MUST SHARE** (engine reads config from UI)
- This is the CURRENT PROBLEM - they're not sharing!

### 3. `trade_states.json` (Written by engine, read by UI)
- **scalp-engine** → **scalp-engine-ui**: ✅ **MUST SHARE** (UI displays active trades)

## Conclusion

**ALL 4 SERVICES MUST SHARE THE SAME DISK** (`shared-market-data`)

The current issue:
- `trade-alerts` ↔ `scalp-engine` → **Working** (they share for market_state.json)
- `scalp-engine` ↔ `scalp-engine-ui` → **NOT Working** (different disk instances!)

## Fix Strategy

Since `scalp-engine` already shares a disk with `trade-alerts`, we need to ensure:

1. **scalp-engine** is attached to the **SAME disk** that `trade-alerts` uses
2. **scalp-engine-ui** is attached to the **SAME disk** that `trade-alerts` uses
3. **market-state-api** is attached to the **SAME disk** that `trade-alerts` uses

**Result**: All 4 services share ONE physical disk → All files visible to all services

## Recommended Fix Steps

### Step 1: Identify the "Source" Disk

Check which service has the correct files:
- `trade-alerts` likely has the disk with `market_state.json`
- Use this as the "source" disk that all others should attach to

### Step 2: Attach All Services to Same Disk

1. Go to Render Dashboard → **Disks** section
2. Find the `shared-market-data` disk (or check which service created it first)
3. **Verify which services are currently attached**:
   - `trade-alerts` → `shared-market-data`
   - `scalp-engine` → `shared-market-data` (might be different instance!)
   - `scalp-engine-ui` → `shared-market-data` (might be different instance!)
   - `market-state-api` → `shared-market-data` (might be different instance!)

4. **Detach any duplicate disks** (if services have separate `shared-market-data` instances)

5. **Attach all 4 services to the SAME `shared-market-data` disk**:
   - Use the one that `trade-alerts` uses (or whichever has the latest `market_state.json`)
   - Mount path: `/var/data` for all services

### Step 3: Verify After Fix

Run in all 4 services' Shell:
```bash
ls -lah /var/data/ | grep -E "(market_state|auto_trader_config|trade_states)"
```

**Expected Result**: All 4 services should see the **SAME files** with **SAME sizes** and **SAME timestamps**

## Current Status

Based on diagnostic output:
- ✅ `trade-alerts` ↔ `scalp-engine`: Likely sharing (for market_state.json)
- ❌ `scalp-engine` ↔ `scalp-engine-ui`: **NOT sharing** (different auto_trader_config.json files)

**Root Cause**: `scalp-engine` and `scalp-engine-ui` are attached to **different disk instances** despite both being named `shared-market-data`.
