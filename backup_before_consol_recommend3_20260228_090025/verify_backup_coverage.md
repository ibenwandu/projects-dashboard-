# Backup System Coverage Verification

## Goal
Provide a **single local source** to analyze:
1. **UI inputs** (what user does in the UI)
2. **OANDA activity** (what actually happens on OANDA)
3. **Scalp-Engine logs** (what the engine records)
4. **Trade-Alerts logs** (what Trade-Alerts recommends)

## Current Configuration

### ✅ Source 1: Scalp-Engine UI Logs
- **API Endpoint**: `https://config-api-8n37.onrender.com/logs/ui`
- **Archive Location**: `logs_archive/Scalp-Engine/scalp_ui_YYYYMMDD.log`
- **What it captures**:
  - User interactions (checkboxes, buttons clicked)
  - Trade enable/disable actions
  - Configuration changes
  - UI state changes
  - Trade execution requests from UI
  - Format: `YYYY-MM-DD HH:MM:SS | ACTION | Details`

**Status**: ✅ Configured, but API currently returning 500 errors

### ✅ Source 2: OANDA Logs
- **API Endpoint**: `https://config-api-8n37.onrender.com/logs/oanda`
- **Archive Location**: `logs_archive/Scalp-Engine/oanda_trades_YYYYMMDD.log`
- **What it captures**:
  - Order creation events
  - Trade fills
  - Balance updates
  - Account events
  - Actual trade executions on OANDA
  - Format: `YYYY-MM-DD HH:MM:SS | OANDA_TRADE | JSON_DATA`

**Status**: ✅ Configured, but API currently returning 500 errors

### ✅ Source 3: Scalp-Engine Logs
- **API Endpoint**: `https://config-api-8n37.onrender.com/logs/engine`
- **Archive Location**: `logs_archive/Scalp-Engine/scalp_engine_YYYYMMDD.log`
- **What it captures**:
  - Trade execution logic
  - Signal detection
  - Position management decisions
  - Stop loss updates
  - Trade entry/exit events
  - Risk management actions
  - Format: `YYYY-MM-DD HH:MM:SS | EVENT_TYPE | Details`

**Status**: ✅ Configured, but API currently returning 500 errors

### ✅ Source 4: Trade-Alerts Logs
- **Source**: Local files in `logs/trade_alerts_*.log`
- **Archive Location**: `logs_archive/Trade-Alerts/trade_alerts_YYYYMMDD.log`
- **What it captures**:
  - LLM analysis results
  - Trading recommendations
  - Market state generation
  - Opportunity identification
  - Consensus calculations

**Status**: ✅ Working - Currently backing up successfully

## Archive Structure

```
logs_archive/
├── Scalp-Engine/              # Single location for UI, OANDA, and Engine logs
│   ├── scalp_ui_YYYYMMDD.log      # UI inputs and interactions
│   ├── oanda_trades_YYYYMMDD.log  # OANDA actual executions
│   └── scalp_engine_YYYYMMDD.log  # Engine execution logic
│
├── Trade-Alerts/              # Trade-Alerts recommendations
│   └── trade_alerts_YYYYMMDD.log
│
└── sessions/                  # Backup metadata
    └── YYYYMMDD/
        └── backup_HHMMSS.json
```

## Analysis Capabilities

### ✅ Single Local Source
All logs are backed up to `C:\Users\user\projects\personal\Trade-Alerts\logs_archive\`

### ✅ Timestamp Alignment
All backups use the same timestamp format: `YYYYMMDD_HHMMSS_filename.log`
- This allows correlating events across all 4 sources by timestamp
- Example: `20260223_164807_scalp_ui_20260223.log` and `20260223_164807_oanda_trades_20260223.log` are from the same backup run

### ✅ Cross-Reference Analysis
You can now:
1. **Compare UI inputs vs Engine actions**:
   - Check `scalp_ui_*.log` for what user enabled
   - Check `scalp_engine_*.log` for what engine actually did
   
2. **Compare Engine vs OANDA**:
   - Check `scalp_engine_*.log` for what engine tried to execute
   - Check `oanda_trades_*.log` for what actually happened on OANDA
   
3. **Compare Trade-Alerts recommendations vs Execution**:
   - Check `trade_alerts_*.log` for LLM recommendations
   - Check `scalp_engine_*.log` for whether they were executed
   - Check `oanda_trades_*.log` for actual OANDA results

4. **Trace full workflow**:
   - Trade-Alerts recommends → UI shows opportunity → User enables → Engine executes → OANDA fills
   - All traceable through timestamped logs in single location

## Current Status

### ✅ Configuration: CORRECT
- All 4 sources are properly configured
- All logs go to single local archive location
- Timestamps allow correlation

### ⚠️ API Status: PARTIAL
- Trade-Alerts: ✅ Working (local files)
- Scalp-Engine API: ❌ Returning 500 errors
- OANDA API: ❌ Returning 500 errors  
- UI API: ❌ Returning 500 errors

### Impact
- **When APIs are working**: System achieves full goal - all 4 sources backed up locally
- **Current state**: Only Trade-Alerts logs are being backed up (1 of 4 sources)

## Verification Checklist

- [x] All 4 sources configured in backup agent
- [x] All logs go to single local location (`logs_archive/`)
- [x] Timestamps allow correlation across sources
- [x] Scalp-Engine, OANDA, and UI logs in same directory (easy comparison)
- [x] Trade-Alerts logs in separate but accessible directory
- [ ] APIs need to be fixed to restore full functionality

## Recommendation

The backup system **IS correctly configured** to achieve the goal. However:

1. **API endpoints need to be fixed** to restore full functionality
2. **Once APIs are working**, all 4 sources will be backed up automatically
3. **The structure is correct** - all logs in single location with correlatable timestamps

The system design is sound - it just needs the Render API endpoints to be operational.

