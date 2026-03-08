# Scalp-Engine & Scalp UI - Complete User Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Getting Started](#getting-started)
4. [Trading Modes](#trading-modes)
5. [Configuration Guide](#configuration-guide)
6. [Using the UI Dashboard](#using-the-ui-dashboard)
7. [Stop Loss Strategies](#stop-loss-strategies)
8. [Trading Hours Management](#trading-hours-management)
9. [Risk Management](#risk-management)
10. [Monitoring & Logs](#monitoring--logs)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

---

## System Overview

The Scalp-Engine is an automated forex trading system that combines AI-powered market analysis with automated trade execution through OANDA. The system consists of two main components:

### Components

1. **Scalp-Engine (Backend)**
   - Monitors market intelligence from multiple LLM sources
   - Executes trades automatically based on configured rules
   - Manages open positions and stop losses
   - Syncs with OANDA trading platform
   - Enforces trading hours and risk limits

2. **Scalp UI (Frontend)**
   - Web dashboard for monitoring and control
   - Configuration management
   - Real-time trade monitoring
   - Performance analytics
   - Market intelligence display

### Key Features

- **Multi-LLM Intelligence**: Combines signals from multiple AI models (GPT-4, Claude, Gemini)
- **Automated Execution**: Opens and manages trades automatically
- **Dynamic Stop Loss**: Multiple strategies (Fixed, Trailing, Breakeven-to-Trailing, AI-Trailing, MACD Crossover)
- **Trading Hours Control**: Enforces trading hours with "runner" exceptions
- **Risk Management**: Position sizing, max trades limit, duplicate prevention
- **One Order Per Pair**: Strict rule prevents multiple orders for the same currency pair
- **State Persistence**: Survives restarts without losing track of open trades

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Scalp UI (Frontend)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Dashboard    │  │ Config       │  │ Performance  │     │
│  │              │  │ Editor       │  │ Analytics    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP API
┌─────────────────────────────────────────────────────────────┐
│                     Config API (Backend)                    │
│  - Stores configuration                                     │
│  - Exposes REST endpoints                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓ Polling
┌─────────────────────────────────────────────────────────────┐
│                   Scalp-Engine (Auto-Trader)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Market       │→│ Trade         │→│ Position      │     │
│  │ Monitor      │  │ Executor      │  │ Manager       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Risk         │  │ Trading Hours │  │ OANDA Sync   │     │
│  │ Controller   │  │ Manager       │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓ OANDA v20 API
┌─────────────────────────────────────────────────────────────┐
│                    OANDA Trading Platform                   │
│  - Executes trades                                          │
│  - Manages positions                                        │
│  - Provides market data                                     │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Market Intelligence**: Scalp-Engine polls the Market State API for trading opportunities
2. **Configuration**: Scalp-Engine loads config from Config API every 30 seconds
3. **Trade Execution**: Opportunities are evaluated and executed via OANDA API
4. **Position Monitoring**: Active trades are monitored every 60 seconds
5. **UI Updates**: UI polls both Config API and Scalp-Engine's state file for real-time updates
6. **OANDA Sync**: Every monitoring cycle syncs in-memory trades with OANDA's actual positions

---

## Getting Started

### Prerequisites

- OANDA trading account (Practice or Live)
- OANDA API access token
- Node.js and Python installed
- Access to deployed services (Render or local)

### Initial Setup

1. **Configure OANDA Credentials**
   
   Set environment variables:
   ```bash
   OANDA_ACCESS_TOKEN=your_token_here
   OANDA_ACCOUNT_ID=your_account_id
   OANDA_ENV=practice  # or 'live'
   ```

2. **Set Configuration API URL**
   
   ```bash
   CONFIG_API_URL=https://your-config-api.onrender.com/config
   ```

3. **Start Scalp-Engine**
   
   The service will automatically:
   - Load configuration from API
   - Sync with OANDA
   - Begin monitoring market state
   - Execute trades based on mode (AUTO/MANUAL/MONITOR)

4. **Access the UI**
   
   Navigate to your deployed UI URL to access the dashboard.

---

## Trading Modes

The system supports three trading modes:

### 1. MONITOR Mode

**Purpose**: Observation only, no trading

**Behavior**:
- Monitors market intelligence
- Logs opportunities
- Does NOT open or manage trades
- Useful for testing and observation

**When to Use**:
- Initial setup and testing
- Observing market conditions
- Validating intelligence sources

### 2. MANUAL Mode

**Purpose**: Generate trade proposals for manual approval

**Behavior**:
- Evaluates opportunities
- Logs trade recommendations
- Waits for manual execution
- You must open trades manually in OANDA

**When to Use**:
- Learning the system
- Low confidence in current market
- Want full control over each trade

### 3. AUTO Mode

**Purpose**: Fully automated trading

**Behavior**:
- Automatically opens trades based on opportunities
- Manages stop losses and take profits
- Closes trades based on:
  - Stop loss hit
  - Take profit hit
  - Trading hours restrictions
  - Trend reversals (MACD, intelligence validity)
  - Manual intervention

**When to Use**:
- After validating system performance
- During active trading hours
- When you trust the intelligence sources

**⚠️ Important**: Start with MANUAL or MONITOR mode to understand the system before enabling AUTO mode.

---

## Configuration Guide

### Configuration Structure

Configuration is stored in the Config API and loaded by Scalp-Engine every 30 seconds. Changes in the UI are reflected in the backend automatically.

### Key Configuration Parameters

#### Trading Mode
```
trading_mode: AUTO | MANUAL | MONITOR
```
- **AUTO**: Fully automated trading
- **MANUAL**: Generate proposals only
- **MONITOR**: Observation only

#### Execution Mode
```
execution_mode: MARKET | RECOMMENDED | HYBRID
```
- **MARKET**: Execute immediately at market price
- **RECOMMENDED**: Place LIMIT order at recommended entry price
- **HYBRID**: Place pending order + watch for MACD crossover (whichever triggers first)

#### Stop Loss Type
```
stop_loss_type: FIXED | TRAILING | BE_TO_TRAILING | AI_TRAILING | MACD_CROSSOVER
```

**FIXED**: Static stop loss at initial distance
- Simple and predictable
- Set once, never moves

**TRAILING**: Follows price at fixed distance
- Locks in profits as price moves
- Set `hard_trailing_pips` (e.g., 20 pips)

**BE_TO_TRAILING**: Breakeven → Trailing Stop
- Moves to breakeven when `be_trigger_pips` in profit
- Converts to trailing stop when profit exceeds threshold (default 10 pips)
- Recommended for most strategies

**AI_TRAILING**: AI-adjusted trailing distance
- Adjusts trailing distance based on market conditions
- Not yet fully implemented

**MACD_CROSSOVER**: Close on MACD reverse crossover
- Closes trade when MACD crosses back against trade direction
- Protects against trend reversals

#### Position Sizing
```
base_position_size: 5000  # Base units to trade
consensus_multiplier: true  # Multiply by consensus level
```

**Example**:
- `base_position_size: 5000`
- `consensus_level: 3` (3 LLMs agree)
- `consensus_multiplier: true`
- **Result**: 15,000 units

**Consensus Levels**:
- 1: Single LLM recommendation
- 2: Two LLMs agree
- 3: Three LLMs agree (strongest signal)

#### Risk Limits
```
max_open_trades: 5  # Maximum concurrent trades
min_consensus: 1    # Minimum LLMs required to agree
```

- **max_open_trades**: Hard limit on concurrent positions
- **min_consensus**: Filter opportunities by agreement level

#### Required LLMs
```
required_llms: ["gemini", "synthesis"]
```
- Opportunities must come from specified LLM sources
- Use to trust only certain models

#### MACD Settings (for HYBRID mode)
```
macd_timeframe: M5  # M1, M5, M15, H1
```
- Timeframe for MACD crossover detection
- Lower timeframes = faster signals
- Higher timeframes = more stable signals

### Updating Configuration

**Via UI**:
1. Go to "Configuration" tab
2. Modify settings
3. Click "Save Configuration"
4. Changes apply within 30 seconds

**Via API**:
```bash
curl -X POST https://config-api.onrender.com/config \
  -H "Content-Type: application/json" \
  -d '{
    "trading_mode": "AUTO",
    "base_position_size": 5000,
    ...
  }'
```

**Important**: Scalp-Engine reloads config every 30 seconds. Changes are logged when detected.

---

## Using the UI Dashboard

### Dashboard Overview

The UI provides real-time visibility into the trading system.

### Main Tabs

#### 1. Auto-Trader Tab

**Status Indicators**:
- System status (Active/Inactive)
- Trading mode (AUTO/MANUAL/MONITOR)
- Configuration file status

**Active Trades Monitor**:
- Real-time list of open trades
- Current P&L in pips
- Trade state (OPEN, AT_BREAKEVEN, TRAILING, PENDING)
- Entry price and direction
- Time opened

**Trade Details**:
Click on any trade to view:
- Full trade details
- Entry/exit prices
- Stop loss position
- Take profit target
- Rationale from LLMs
- Consensus level

#### 2. Opportunities Tab

Shows current trading opportunities from market intelligence:
- Currency pair
- Direction (LONG/SHORT)
- Entry price
- Stop loss / Take profit
- Confidence level
- Consensus level
- LLM sources
- Rationale

**Color Coding**:
- 🟢 Green: High consensus (3 LLMs)
- 🟡 Yellow: Medium consensus (2 LLMs)
- 🔵 Blue: Low consensus (1 LLM)

#### 3. Performance Tab

**Metrics**:
- Total trades executed
- Win rate %
- Average profit per trade
- Total realized P&L
- Best/worst trades
- Performance by pair

**Charts**:
- P&L over time
- Trades by pair
- Win/loss distribution

#### 4. Market State Tab

**Intelligence Overview**:
- Global market bias (BULLISH/BEARISH/NEUTRAL)
- Active opportunities count
- LLM agreement levels
- Last update timestamp

**Recent Signals**:
- Historical opportunity signals
- Signal quality over time
- LLM performance comparison

### Controls

**Refresh Data**:
- Manual refresh button
- Auto-refresh toggle (30s interval)

**Settings**:
- Show/hide pending trades
- Show/hide closed trades
- Recent signals limit (slider)

### Configuration Tab

**Edit Mode**:
- Modify all system parameters
- Real-time validation
- Save changes to Config API

**Parameters Visible**:
- Trading mode
- Execution mode
- Stop loss type
- Position sizing
- Risk limits
- MACD settings
- Required LLMs

---

## Stop Loss Strategies

### 1. FIXED Stop Loss

**How it Works**:
- Set once at trade open
- Never moves
- Simple and predictable

**When to Use**:
- Short-term scalps
- High volatility markets
- Quick in-and-out trades

**Configuration**:
```
stop_loss_type: FIXED
fixed_sl_pips: 20  # Distance from entry
```

**Example**:
- Entry: 1.1000
- Stop Loss: 1.0980 (20 pips)
- Remains at 1.0980 regardless of price movement

---

### 2. TRAILING Stop Loss

**How it Works**:
- Follows price at fixed distance
- Only moves in profit direction
- Never moves back toward entry

**When to Use**:
- Trending markets
- Want to capture large moves
- Willing to give back some profit

**Configuration**:
```
stop_loss_type: TRAILING
hard_trailing_pips: 20
```

**Example**:
- Entry: 1.1000 (LONG)
- Initial SL: 1.0980 (20 pips below)
- Price moves to 1.1050
- SL moves to 1.1030 (20 pips below current)
- Price moves to 1.1100
- SL moves to 1.1080
- If price drops to 1.1080, trade closes with 80 pips profit

---

### 3. BE_TO_TRAILING (Recommended)

**How it Works**:
1. **Phase 1 - Breakeven**:
   - When price moves `be_trigger_pips` in profit
   - Move stop loss to entry price (breakeven)
   - Protects against loss

2. **Phase 2 - Trailing**:
   - When price moves 10+ pips beyond breakeven
   - Convert to trailing stop at `hard_trailing_pips` distance
   - Locks in profits

**When to Use**:
- Most trading scenarios (recommended default)
- Balances risk protection and profit capture
- Reduces risk of loss while allowing runners

**Configuration**:
```
stop_loss_type: BE_TO_TRAILING
be_trigger_pips: 10  # When to move to BE
hard_trailing_pips: 20  # Trailing distance after conversion
```

**Example**:
- Entry: 1.1000 (LONG)
- Initial SL: 1.0980 (20 pips below)

**Step 1 - Move to Breakeven**:
- Price reaches 1.1010 (10 pips profit)
- SL moves to 1.1000 (breakeven)
- Trade is now risk-free

**Step 2 - Convert to Trailing**:
- Price reaches 1.1020 (20 pips profit, 10 beyond BE)
- SL converts to trailing stop
- SL is now 1.1000 (20 pips below 1.1020)

**Step 3 - Trail Profits**:
- Price moves to 1.1050
- SL trails to 1.1030
- If price drops to 1.1030, trade closes with 30 pips profit

---

### 4. AI_TRAILING

**How it Works**:
- AI adjusts trailing distance based on:
  - Market volatility
  - Time of day
  - Pair characteristics
  - Current market state

**Status**: Experimental (not fully implemented)

---

### 5. MACD_CROSSOVER

**How it Works**:
- Monitors MACD indicator on specified timeframe
- Closes trade when MACD crosses AGAINST trade direction
- Protects against trend reversals

**When to Use**:
- Trend-following strategies
- Want to exit before major reversals
- Longer-term holds

**Configuration**:
```
stop_loss_type: MACD_CROSSOVER
macd_timeframe: M5  # M1, M5, M15, H1
```

**Example (LONG trade)**:
- MACD crosses above signal line → Trade opened
- Trade runs in profit
- MACD crosses BACK below signal line → Trade closed
- Prevents giving back profits from reversals

---

## Trading Hours Management

### Overview

The system enforces strict weekday-only trading hours to:
- Avoid low-liquidity periods
- Prevent weekend gaps and high spreads
- Protect profits with "runner" exceptions (Mon-Thu only)
- Ensure fresh market state is used

### Trading Hours Rules

#### Weekly Trading Hours (Weekdays Only)
```
Trading Hours: Monday 01:00 UTC - Friday 21:30 UTC
No Entry Zone:  Friday 21:00 UTC - Monday 01:00 UTC (weekend shutdown)
```

- **Monday 01:00 UTC**: Trading week begins (1 hour after Tokyo open)
- **Friday 21:00 UTC**: No new entries (existing trades can continue until 21:30)
- **Friday 21:30 UTC**: All trades closed, all pending orders cancelled
- **Saturday/Sunday**: NO TRADING - complete shutdown

#### Weekend Rules

**Friday**:
- 21:00 UTC: No new entries allowed (weekend shutdown begins)
- 21:30 UTC: All trades closed (no exceptions, no runners)
- Prevents weekend exposure

**Saturday**:
- Market closed, NO TRADING
- Any remaining trades are closed immediately
- All pending orders cancelled

**Sunday**:
- Market closed, NO TRADING
- Any remaining trades are closed immediately
- All pending orders cancelled
- Trading resumes Monday 01:00 UTC

### Runner Exception (Mon-Thu Only)

**What is a Runner?**
- A trade with 25+ pips profit at daily close time (21:30 UTC)
- **Friday**: NO RUNNERS - all trades close at 21:30 UTC regardless of profit

**Runner Privileges (Mon-Thu only)**:
- Can continue beyond 21:30 UTC
- Must close by 23:00 UTC (hard deadline)
- May close earlier if:
  - EMA(9) crosses EMA(26) (exit signal)
  - Spread exceeds 5 pips (waits for better spread)

**Example (Monday-Thursday)**:
- 21:30 UTC: Trade has 30 pips profit
- Status: RUNNER - can continue
- 22:00 UTC: EMA crossover detected
- Result: Trade closed with 35 pips profit

**Example (Friday)**:
- 21:30 UTC: Trade has 30 pips profit
- Status: CLOSED (no runners on Friday)
- Result: Trade closed at 21:30 UTC regardless of profit

### New Entry Restrictions

**No Entry Zone (Friday 21:00 UTC - Monday 01:00 UTC)**:
- No new trades opened
- Prevents opening trades right before weekend shutdown
- Existing trades continue until Friday 21:30 UTC

**After Friday Close (21:30+ UTC)**:
- No new trades until Monday 01:00 UTC
- All pending orders cancelled
- Weekend shutdown enforced

### Pending Orders Cleanup

**End of Trading Week (Friday 21:30 UTC)**:
- All pending orders cancelled
- All open trades closed
- Prevents stale orders from filling over weekend

**Start of Trading Week (Monday 01:00 UTC)**:
- Safety check: Cancel any remaining stale pending orders
- Ensures only fresh market state is used
- Logged as WARNING if any found

**Weekend Shutdown (Saturday/Sunday)**:
- Continuous monitoring: Cancel any pending orders found
- Close any remaining open trades
- Enforces "NO TRADING OVER WEEKEND" rule

**Why This Matters**:
- Prevents trading with stale market intelligence
- Each trading week starts with fresh opportunities
- Old pending orders don't unexpectedly fill
- Weekend protection against low liquidity and high spreads

### Example Timeline

**Monday 01:00 UTC**:
- Trading week begins
- Safety check: Cancel stale pending orders (if any)
- New market state loaded
- New trades can begin

**Monday 21:30 UTC**:
- Non-runners (< 25 pips): Closed immediately
- Runners (≥ 25 pips): Can continue until 23:00 UTC
- All pending orders cancelled

**Monday 22:45 UTC**:
- Runner hits 40 pips profit
- EMA crossover detected
- Trade closed with 40 pips

**Monday 23:00 UTC**:
- Any remaining trades closed (hard deadline)

**Friday 21:00 UTC**:
- No new entries allowed (weekend shutdown begins)
- Existing trades continue until 21:30 UTC

**Friday 21:30 UTC**:
- ALL trades closed (no exceptions, no runners)
- All pending orders cancelled
- Trading week ends

**Saturday/Sunday**:
- NO TRADING - complete shutdown
- Any remaining trades closed immediately
- All pending orders cancelled

**Monday 01:00 UTC**:
- Trading week begins again
- Safety check: Cancel stale pending orders (if any)
- New market state loaded
- New trades can begin

---

## Risk Management

### Position Sizing

**Base Position Size**:
```
base_position_size: 5000  # Units per trade
```

**Consensus Multiplier**:
```
consensus_multiplier: true
```

When enabled:
- Consensus 1: 1x base size (5,000 units)
- Consensus 2: 2x base size (10,000 units)
- Consensus 3: 3x base size (15,000 units)

**Calculating Risk**:
```
Risk per trade = (Position Size × Pip Value × Stop Loss Pips)
```

Example (EUR/USD):
- Position: 10,000 units
- SL: 20 pips
- Pip value: $1 per pip (at 10k units)
- Risk: 10,000 × $0.0001 × 20 = $20

### Maximum Open Trades

```
max_open_trades: 5
```

**How it Works**:
- Hard limit on concurrent positions
- Includes both OPEN and PENDING trades
- When limit reached:
  - New opportunities are BLOCKED
  - Logged as "Max trades limit reached"
  - Must wait for existing trade to close

**Excess Trade Handling**:
If sync finds more than `max_open_trades`:
- Calculates relevance score for each trade
- Closes least relevant trades first
- Based on:
  - Current opportunities (is pair still recommended?)
  - Market bias alignment
  - Trade age
  - P&L status
  - Consensus level
  - Trade state

### One Order Per Pair Rule

**Strict Rule**: Only ONE order (pending or open) per currency pair

**Enforcement**:
1. Before opening new trade: Check if pair already has an order
2. During OANDA sync: Detect duplicates from both sides
3. On state load: Prevent duplicates from file
4. Regular cleanup: Remove any duplicates found

**If Duplicate Detected**:
- Logged as 🚨 RED FLAG
- Keeps most recent order
- Cancels/closes older order(s)
- Prevents over-exposure to single pair

### Stop Loss Protection

**Always Set**:
- Every trade has a stop loss (no exceptions)
- Set at trade open
- Managed by OANDA (survives connection loss)

**Types of Protection**:
1. **Initial SL**: Set at trade open based on opportunity
2. **Trailing SL**: Follows price to lock profits
3. **Breakeven SL**: Risk-free after initial profit
4. **MACD SL**: Exits on trend reversal

**Verification**:
- System continuously checks SL is active on OANDA
- Re-applies if missing (every 2 minutes)
- Logs verification attempts

### Trend Reversal Protection

**1. MACD Reverse Crossover**:
- Monitors MACD on configured timeframe
- Closes trade if MACD crosses against trade direction
- Active for all trades (regardless of SL type)

**2. Intelligence Validity Check**:
- Checks if pair/direction still in current market state
- If LLMs changed recommendation: Trade closed
- Prevents holding trades against new intelligence

**3. Global Bias Reversal**:
- If market bias shifts dramatically
- Less relevant trades may be closed first

### Account Protection

**Balance Check**:
- Monitors account balance before each trade
- Logs balance and unrealized P&L

**API Error Handling**:
- All OANDA calls wrapped in error handling
- Retries on temporary failures
- Logs all API errors

**State Persistence**:
- Trade states saved to disk regularly
- Survives service restarts
- Syncs with OANDA on startup

---

## Monitoring & Logs

### Log Levels

**INFO** (Green):
- Normal operations
- Trade execution
- Configuration updates
- Market state changes

**WARNING** (Orange):
- Non-critical issues
- Missing optional data
- Sync discrepancies

**ERROR** (Red):
- Failed trade execution
- API errors
- Critical sync issues
- Stop loss problems

**RED FLAG** (Red):
- Duplicate order violations
- State inconsistencies
- Critical rule violations

### Key Log Messages

#### Startup
```
✅ Auto-trader components initialized
📥 Loaded X active trades from disk
🔄 Syncing with OANDA on startup
✅ Startup sync complete - X total (Y open, Z pending)
```

#### Configuration
```
🔄 Configuration reloaded from API:
  Mode: MANUAL -> AUTO
  Base Position Size: 1000 -> 5000
```

#### Trade Execution
```
📊 Opening trade: EUR/USD LONG, units=5000, entry=1.1000
✅ Opened trade T123456: EUR/USD LONG @ 1.1000
```

#### Position Monitoring
```
🎯 Trade T123456 at breakeven - SL moved to entry
📈 Trade T123456 converted to trailing stop (20 pips)
```

#### Trading Hours
```
⏩ Skipped GBP/USD BUY - Trading hours: AFTER_DAILY_CLOSE
🕐 Trading hours: Closing trade T123456 - DAILY_CLOSE_21:30
```

#### OANDA Sync
```
📋 Found 2 pending orders in OANDA for sync check
🔄 Detected externally closed trade: EUR/USD LONG (ID: T123456)
🔄 DETECTED PENDING ORDER FROM OANDA: USD/JPY SHORT
💾 Saved state after sync: Removed 1 trades, Added 0 open trades
```

#### Duplicates (RED FLAG)
```
🚨 RED FLAG: Found existing OANDA position for EUR/USD
🚨 RED FLAG: BLOCKED DUPLICATE order for GBP/USD LONG
🗑️ CANCELLED duplicate order 123 (EUR/USD LONG) - RED FLAG violation
```

#### Cleanup
```
🕐 21:30 UTC - End of trading hours: Cancelling all pending orders
✅ End-of-day cleanup complete: 3 pending order(s) cancelled

🕐 01:00 UTC - Start of trading hours: Safety check
⚠️ Found 1 stale pending order(s) at start of trading hours - cancelled
```

### Monitoring via UI

**Active Trades Monitor**:
- Real-time P&L
- Current state
- Time in trade
- Entry price

**Indicators**:
- 🟢 Trade in profit
- 🔴 Trade in loss
- ⚪ At breakeven

### Monitoring via Logs (Render Dashboard)

**Access Logs**:
1. Go to Render dashboard
2. Select "scalp-engine" service
3. Click "Logs" in sidebar
4. Use "Live tail" for real-time
5. Use "Search" to filter

**Useful Search Terms**:
- `RED FLAG` - Find duplicate violations
- `ERROR` - Find errors only
- `Opening trade` - Find new trades
- `Cancelled` - Find cancelled orders
- `Cleanup` - Find cleanup operations
- `sync` - Find sync operations

### Log Files (Local)

If running locally:
```
logs/scalp-engine.log  # All logs
logs/trade-execution.log  # Trade-specific logs
```

---

## Troubleshooting

### Common Issues

#### 1. Configuration Not Updating

**Symptoms**:
- Changes in UI not reflected in backend
- Old values still being used

**Checks**:
1. Verify Config API URL is set correctly
2. Check logs for "Configuration reloaded" messages
3. Wait 30 seconds (config reload interval)
4. Verify API returns correct config:
   ```bash
   curl https://config-api.onrender.com/config
   ```

**Solution**:
- Config reloads every 30 seconds
- Look for log: `🔄 Configuration reloaded from API`
- If not appearing, check API connectivity

---

#### 2. UI Shows Trades OANDA Doesn't

**Symptoms**:
- UI displays open trades
- OANDA shows no open trades
- State file out of sync

**Cause**:
- Trades were closed externally (manual close in OANDA)
- Sync not detecting the closure

**Solution**:
1. Check logs for sync messages:
   ```
   🔄 Detected externally closed trade: [pair] [direction]
   ```
2. If not appearing, sync may have failed
3. Service will auto-sync on next cycle (60 seconds)
4. Or restart service to force sync

**Prevention**:
- Avoid manual closes in OANDA
- Let system manage trades
- If manual close needed, expect UI to catch up in 60s

---

#### 3. OANDA Shows Trades UI Doesn't

**Symptoms**:
- OANDA has open trades
- UI doesn't show them
- Trades opened externally or not tracked

**Cause**:
- Trades opened manually in OANDA
- Service restarted and didn't load trades
- Sync failed to add them

**Solution**:
1. Check logs for:
   ```
   🔄 DETECTED EXISTING OANDA TRADE: [pair] [direction]
   ```
2. Service should auto-add within 60 seconds
3. If not, check:
   - OANDA API credentials
   - Network connectivity
   - Sync error messages

**Prevention**:
- Don't open trades manually in OANDA
- Let system manage all trades
- System will auto-sync on startup

---

#### 4. Duplicate Pending Orders

**Symptoms**:
- Multiple pending orders for same pair
- RED FLAG logs appearing

**Cause**:
- Service restarted mid-order
- Sync issue
- Duplicate from external source

**Detection**:
Look for logs:
```
🚨 RED FLAG: Found X orders for [pair] (should be only 1)
```

**Solution**:
- System automatically cancels duplicates
- Keeps most recent order
- Check logs for:
  ```
  🗑️ CANCELLED duplicate order [ID]
  ```

**Prevention**:
- One-order-per-pair rule is enforced
- Automatic cleanup on every sync
- Duplicates are blocked before creation

---

#### 5. Pending Orders Not Cancelled at Trading Week End

**Symptoms**:
- Pending orders still active after Friday 21:30 UTC
- Stale orders from previous week

**Cause**:
- Cleanup didn't run
- Service was offline during cleanup time
- Cleanup failed

**Solution**:
1. Check if service was running at Friday 21:30 UTC
2. Look for cleanup logs:
   ```
   🕐 Friday 21:30 UTC - End of trading week: Closing all trades and cancelling all pending orders
   ```
3. Weekend shutdown will catch stragglers:
   ```
   🚫 WEEKEND SHUTDOWN - No trading allowed
   🚫 Weekend shutdown: Cancelled X pending order(s)
   ```
4. Safety check at Monday 01:00 UTC will catch any remaining:
   ```
   🕐 Monday 01:00 UTC - Start of trading week: Safety check
   ```
5. Manual cleanup:
   - Cancel orders in OANDA manually
   - Service will sync within 60 seconds

**Prevention**:
- Ensure service runs 24/7
- Monitor cleanup logs weekly
- Three cleanup times (Friday 21:30, weekend monitoring, Monday 01:00) provide redundancy

---

#### 6. Trades Opening on Weekend

**Symptoms**:
- Trades opening on Saturday or Sunday
- System not respecting weekend shutdown

**Cause**:
- Trading hours logic not properly enforced
- Service restarted and didn't check weekday

**Solution**:
1. Check logs for weekend shutdown messages:
   ```
   🚫 WEEKEND SHUTDOWN - No trading allowed
   ```
2. Verify `can_open_new_trade()` is blocking weekend entries
3. Check if trades are being closed by `should_close_trade()`

**Prevention**:
- Weekend shutdown is enforced in main loop
- Trading hours manager blocks all weekend entries
- Monitoring cycle closes any remaining trades

---

#### 6. Stop Loss Not Active

**Symptoms**:
- Trade shows TRAILING state
- OANDA shows no trailing stop
- Logs show "Trailing stop not found"

**Cause**:
- OANDA API failed to set stop
- Stop was removed externally
- API delay in propagation

**Detection**:
```
⚠️ Trailing stop not found for trade [ID]
🔧 Re-applying trailing stop
```

**Solution**:
- System automatically re-applies (every 2 minutes)
- Check logs for verification attempts
- If repeated failures, check OANDA API status

**Prevention**:
- System continuously verifies
- Automatic re-application
- Logs all verification attempts

---

#### 7. Trades Not Opening (AUTO Mode)

**Symptoms**:
- Opportunities appear
- No trades executed
- Mode is AUTO

**Possible Causes**:

**A. Trading Hours**:
```
⏩ Skipped [pair] [direction] - Trading hours: SUNDAY_CLOSED
⏩ Skipped [pair] [direction] - Trading hours: FRIDAY_WEEKEND_SHUTDOWN_21:00
```
- Check current day vs trading hours (Monday 01:00 UTC - Friday 21:00 UTC)
- Weekend (Saturday/Sunday): NO TRADING

**B. Max Trades Limit**:
```
⚠️ Max open trades limit reached (5/5)
```
- Close some trades or increase `max_open_trades`

**C. Duplicate Detection**:
```
🚨 RED FLAG: BLOCKED DUPLICATE order for [pair]
```
- System preventing duplicate order
- Check if pair already has position

**D. Insufficient Consensus**:
```
⏭️ Skipped [pair] - Consensus 1 < Min 2
```
- Increase `min_consensus` or wait for more LLM agreement

**E. Required LLMs Missing**:
```
⏭️ Skipped [pair] - LLM source [source] not in required list
```
- Adjust `required_llms` config

**Solution**:
1. Check logs for skip reason
2. Verify configuration matches intent
3. Ensure trading hours are active
4. Check no existing position for same pair

---

#### 8. Service Keeps Restarting

**Symptoms**:
- Render shows frequent restarts
- "Instance failed" messages
- Service unstable

**Causes**:
- Syntax errors in code
- Import errors
- API connectivity issues
- Memory issues

**Solution**:
1. Check Render logs for error messages
2. Look for Python exceptions
3. Verify OANDA credentials
4. Check API endpoints are accessible
5. Review recent deployments

**Recent Fixes**:
- PendingOrders import error (now using OrdersPending)
- Unreachable code in normalize_pair (fixed)
- Duplicate else blocks (fixed)

---

### Getting Help

**Check Logs First**:
- Most issues have clear log messages
- Search for ERROR or RED FLAG
- Check timestamps around issue time

**Common Fixes**:
1. Wait 30-60 seconds (sync interval)
2. Check config is correct
3. Verify OANDA API is working
4. Ensure service is running

**If Issue Persists**:
- Collect relevant logs
- Note exact time of issue
- Document expected vs actual behavior
- Check OANDA platform directly

---

## Best Practices

### Starting Out

1. **Begin with MONITOR Mode**
   - Observe system behavior
   - Understand opportunity generation
   - Review trade logic

2. **Test with MANUAL Mode**
   - Verify trade signals make sense
   - Understand entry/exit logic
   - Build confidence

3. **Start Small in AUTO Mode**
   - Use small `base_position_size` (1000-2000)
   - Set low `max_open_trades` (2-3)
   - Monitor closely for first week

### Configuration Recommendations

**Conservative Settings**:
```
trading_mode: AUTO
execution_mode: MARKET
stop_loss_type: BE_TO_TRAILING
base_position_size: 2000
max_open_trades: 3
min_consensus: 2
be_trigger_pips: 10
hard_trailing_pips: 20
consensus_multiplier: false
```

**Moderate Settings**:
```
trading_mode: AUTO
execution_mode: HYBRID
stop_loss_type: BE_TO_TRAILING
base_position_size: 5000
max_open_trades: 5
min_consensus: 1
be_trigger_pips: 10
hard_trailing_pips: 20
consensus_multiplier: true
required_llms: ["gemini", "synthesis"]
```

**Aggressive Settings**:
```
trading_mode: AUTO
execution_mode: MARKET
stop_loss_type: TRAILING
base_position_size: 10000
max_open_trades: 8
min_consensus: 1
be_trigger_pips: 5
hard_trailing_pips: 30
consensus_multiplier: true
```

### Daily Routine

**Morning (Before 01:00 UTC)**:
1. Check overnight performance
2. Review closed trades
3. Verify configuration is correct
4. Check OANDA account balance

**During Trading Hours (01:00 - 21:30 UTC)**:
1. Monitor active trades
2. Watch for RED FLAG logs
3. Check P&L regularly
4. Verify auto-refresh is on in UI

**Evening (After 21:30 UTC)**:
1. Review day's performance
2. Check cleanup logs
3. Verify all pending orders were cancelled
4. Adjust configuration if needed

### Risk Management Tips

1. **Never Risk More Than 2% Per Trade**
   - Calculate: Account × 2% / (SL pips × pip value)
   - Adjust `base_position_size` accordingly

2. **Diversify Across Pairs**
   - Don't concentrate on single pair
   - Let system choose best opportunities

3. **Monitor Correlation**
   - EUR/USD and GBP/USD are correlated
   - Avoid multiple correlated pairs

4. **Use Stop Losses Always**
   - Never disable stop losses
   - BE_TO_TRAILING recommended
   - Protects capital automatically

5. **Respect Trading Hours**
   - Don't override restrictions
   - System enforces for good reason
   - Weekend gaps can be costly

### Monitoring Best Practices

1. **Check Logs Daily**
   - Look for RED FLAG messages
   - Review trade execution
   - Verify cleanup ran

2. **Enable Auto-Refresh**
   - Keep UI updated
   - 30-second interval recommended
   - Catches issues quickly

3. **Set Alerts** (if available)
   - Large losses
   - Duplicate detections
   - Service restarts

4. **Keep Records**
   - Screenshot configuration
   - Note major changes
   - Track performance metrics

### When to Intervene

**✅ Safe to Intervene**:
- Changing configuration
- Stopping service for maintenance
- Reviewing logs and performance

**⚠️ Be Careful**:
- Closing trades manually in OANDA (UI will sync)
- Changing stop losses in OANDA (may be overwritten)
- Restarting service mid-trade (state persists)

**❌ Avoid**:
- Opening trades manually in OANDA (creates duplicates)
- Editing state file manually (can corrupt)
- Multiple order for same pair (system blocks)

---

## Appendix: Configuration Reference

### Complete Configuration Schema

```json
{
  "trading_mode": "AUTO",
  "execution_mode": "HYBRID",
  "stop_loss_type": "BE_TO_TRAILING",
  "base_position_size": 5000,
  "max_open_trades": 5,
  "min_consensus": 1,
  "consensus_multiplier": true,
  "be_trigger_pips": 10,
  "hard_trailing_pips": 20,
  "fixed_sl_pips": 20,
  "macd_timeframe": "M5",
  "required_llms": ["gemini", "synthesis"]
}
```

### Enum Values

**TradingMode**:
- `MONITOR` - Observation only
- `MANUAL` - Generate proposals
- `AUTO` - Fully automated

**ExecutionMode**:
- `MARKET` - Immediate execution
- `RECOMMENDED` - LIMIT order at recommended price
- `HYBRID` - Pending order + MACD trigger

**StopLossType**:
- `FIXED` - Static stop loss
- `TRAILING` - Follows price
- `BE_TO_TRAILING` - Breakeven → Trailing (recommended)
- `AI_TRAILING` - AI-adjusted (experimental)
- `MACD_CROSSOVER` - Close on MACD reversal

**MACD Timeframe**:
- `M1` - 1 minute
- `M5` - 5 minutes (recommended)
- `M15` - 15 minutes
- `H1` - 1 hour

### Units and Conversions

**Pip Calculations**:
- Most pairs: 1 pip = 0.0001
- JPY pairs: 1 pip = 0.01

**Position Size to Units**:
- `base_position_size: 5000` = 5,000 units = 0.05 lots

**Risk Calculation**:
```
Risk = Position Size × Pip Value × SL Pips

Example (EUR/USD):
Position: 10,000 units
SL: 20 pips
Pip Value: $1 per pip (at 10k units)
Risk: $20
```

**Time Zones**:
- System uses UTC internally
- Trading hours: Monday 01:00 UTC - Friday 21:30 UTC (weekdays only)
- Cleanup: Friday 21:30 UTC (end of week) and Monday 01:00 UTC (start of week)
- Weekend shutdown: Saturday/Sunday (no trading)

---

## Conclusion

The Scalp-Engine trading system provides a robust, automated solution for forex trading with built-in risk management and intelligent execution. By following this guide and best practices, you can safely and effectively use the system to execute your trading strategy.

Remember:
- Start small and scale up
- Monitor regularly
- Trust the system's protections
- Review performance frequently
- Adjust configuration based on results

For issues or questions, check the Troubleshooting section or review the logs for detailed error messages.

Happy trading! 🚀
