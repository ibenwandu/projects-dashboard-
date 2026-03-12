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

**LLM architecture (consol-recommend3 Phase 2.2)**:
- **Tier 1 (primary)**: ChatGPT and Gemini—core analysis; both are typically required for consensus.
- **Tier 2 (synthesis)**: Synthesis (Gemini Final) combines Tier 1 outputs and is often in `required_llms`.
- **Tier 3 (optional)**: Claude and DeepSeek—optional; if Claude is skipped (e.g. API credit/billing issue), consensus uses the remaining LLMs. DeepSeek opportunities may not be parsed until its output format matches the parser (see DeepSeek parsing below).
- **Error handling**: When one or more LLMs are unavailable (e.g. "Claude skipped: API credit/billing issue"), the engine logs per-LLM status and continues with available sources; consensus denominator reflects only LLMs that had opportunities for that pair.

**DeepSeek parsing (consol-recommend3 Phase 2.3)**:
- The recommendation parser expects a consistent format (e.g. JSON block or narrative with clear pair/entry/exit). If DeepSeek returns a different format, parsed opportunities for DeepSeek may be 0 until the prompt is updated to request JSON/machine-readable output or a DeepSeek-specific parser is added. Consensus may then use fewer than four base LLMs when DeepSeek is enabled but not parsed.

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

**Config validation (consol-recommend3 Phase 2.4)**:
- At config load, the engine does not change `required_llms` or consensus logic. If you see "Required LLMs: gemini" (only one), that may be intentional or config drift—verify in Config API/UI. Optional: log a warning when only one required LLM is set (e.g. "Only one required LLM (unusual)").

**Claude unavailable**:
- If logs show "Claude skipped: API credit/billing issue", check your Anthropic account (credits, billing). The system continues with other LLMs.

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

### Target Exit Behaviour (Research)

The following targets are from research in `personal/research/` (Exit Strategy, Trailing SL) and are documented for future implementation:

- **First take profit**: 1.5× risk (e.g. close 50% at 1.5× risk in a half-and-run strategy).
- **Runner**: Remaining position trailed with ATR×1.0 distance.
- **Breakeven**: Move SL to entry when unrealized profit ≥ 50 pips (configurable).
- **Trailing activation**: Convert to trailing stop when profit ≥ 100 pips (configurable), in addition to existing min age and OANDA P/L gate.

Market state and opportunities may include `atr` (ATR value) for ATR-based TP and trailing; the engine uses it when available (e.g. ATR_TRAILING, regime).

### Safety: Manual Close of Winners (Phase 3.4)

Research recommends limiting manual closure of trades that are in profit (e.g. > 1 pip) to avoid cutting winners early. When closing via UI or API, consider adding a confirmation or warning when the trade shows positive unrealized P&L. This can be implemented in the Config API or UI as a configurable option.

### Research Documentation (Index)

Research used for exit strategy, trailing stop loss, and position sizing is under the **personal** folder:

| Topic | Index document |
|-------|----------------|
| Exit strategy | `personal/research/EXIT_STRATEGY_DOCUMENTATION_INDEX.md` |
| Trailing stop loss | `personal/research/TRAILING_SL_RESEARCH_INDEX.md` |
| Position sizing | `personal/research/POSITION_SIZING_INDEX.md` |
| Sources | `personal/research/RESEARCH_SOURCES.md` |

See also `personal/TRADING_SYSTEM_IMPROVEMENT_PLAN.md` and `personal/OUTSTANDING_IMPLEMENTATION_PLAN.md` for the phased implementation plan.

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

**Config API log endpoints** (GET /logs/engine, GET /logs/oanda, GET /logs/ui): These serve log content from the config-api service. Expected paths: engine and oanda write to `logs/` (or `/var/data/logs/` on Render); log sync pushes from scalp-engine and scalp-ui to config-api. If no files exist yet, the API returns 404 with message "Logs not available". The UI can show "Logs not available" when it receives 404 from these endpoints.

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

#### 5. UI Database (scalping_rl.db) and Streamlit Session (consol-recommend2 Phase 1.7, cursor6 §5.6)

**UI database (scalping_rl.db)**:
- The UI database is created on first use and may be recreated on new deploys or restarts if there is no persistent volume.
- Do not rely on it as the only source of critical state (trade state and config live in the Config API / POST /trades).
- For persistence across restarts, configure a persistent volume for the DB path and document it in deployment.
- **Multiple "Database initialized" / "Opening existing database" per page load (cursor6 §5.6):** The UI may open `scalping_rl.db` per widget or per Streamlit rerun, so several init/open lines per load are expected. Routine open/init is logged at **DEBUG** to reduce noise; "init once" applies to the **engine** side (e.g. Enhanced RL in scalp_engine), not the UI.

**Streamlit "Session already connected"**:
- This message can appear when using multiple tabs or after reconnects.
- Recommendation: use one tab per session or refresh the page if behaviour is odd.

**Config "last updated"**:
- The Config API may expose "last updated" (or `last_updated`) in a separate field (e.g. `meta.updated`).
- The UI can display it (e.g. "Config last updated: &lt;timestamp&gt;").
- The engine must not pass this field into `TradeConfig`; it is stripped when building config for the engine.

**Consensus and required_llms (consol-recommend3 Phase 1.6 / 2.1)**:
- **required_llms**: List of LLM names that must be among the agreeing sources for an opportunity (e.g. `["gemini", "synthesis", "chatgpt"]`). If config shows only one required LLM (e.g. "gemini"), that may be intentional or config drift—check Config API/UI.
- **min_consensus_level**: Minimum number of agreeing *base* LLMs required (e.g. 2 = at least two base LLMs must agree).
- **Consensus denominator (2/3 vs 2/4)**: The denominator is the number of *base* LLMs that had opportunities for that pair in this run (e.g. if ChatGPT, Gemini, and Synthesis had recommendations for EUR/USD, denominator is 3; "2/3" means two of those three agree). Base LLMs typically include chatgpt, gemini, claude, deepseek where applicable; Synthesis is a separate tier. So "2/3" = two of three base LLMs agree; "2/4" = two of four when DeepSeek is included and returning opportunities.
- **Run count reset**: When a trade for (pair, direction) is closed or cancelled and there is no open/pending order, the run count for that opportunity is auto-reset so the same setup can be retried (max_runs no longer blocks permanently when no position).

**OANDA log (0 chars)**:
- The OANDA log file (e.g. served via Config API or backup) may show 0 characters when there has been no OANDA activity in the current sync window (e.g. no orders/trades in the last interval). This is expected. If you need to verify OANDA connectivity, check engine logs for OANDA API calls or run a manual sync from the UI.

---

#### 6. Pending Orders Not Cancelled at Trading Week End

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

#### 7. Trades Opening on Weekend

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

#### 8. Stop Loss Not Active

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

#### 9. Verifying RL (Trade-Alerts learning cycle)

To verify that the reinforcement learning system is running: after **11pm UTC** check Render logs for Trade-Alerts (or Scalp-Engine if it triggers learning) for "LEARNING CYCLE START", "Evaluating recommendation", and "WEIGHTS UPDATED" (or equivalent). The local RL DB may be empty if Trade-Alerts runs only on Render.

---

#### 10. Sync and orphan verification (OANDA vs engine/UI) (consol-recommend4 Phase 3.1)

**(a) GET /trades vs OANDA positions**  
Call Config API **GET `/trades`** (or your market-state/trades endpoint) to get the list of open and pending trades the system tracks. Compare this list with **OANDA positions** (OANDA dashboard or OANDA API) by **pair** and **direction** (LONG/BUY vs SHORT/SELL).

**(b) Candidate orphan**  
Any **OANDA position** that has **no matching trade** in GET `/trades` (same pair and direction) is a **candidate orphan** (opened outside the engine or not yet synced). Reconcile manually: cancel on OANDA if unintended, or allow the engine to add it on next sync (engine will log and track it).

**(c) Cross-check with Manual logs**  
Use **Manual logs** (e.g. `C:\Users\user\Desktop\Test\Manual logs`): **scalp-engine_*.txt** for active trades and decisions, and **oanda_transactions_*.json** for broker-side order/fill/cancel history. Cross-check timestamps and pair/direction to confirm sync or identify orphans.

**Optional orphan WARNING**: The engine logs **once per (pair, direction) per 15 minutes** at WARNING: `Possible orphan: {pair} {direction} on OANDA not in engine state (adding to track).` when it adds an OANDA position it did not previously track. No auto-correction of engine state beyond adding the trade to track.

**(d) Multiple pending same pair – UI shows one row but OANDA has multiple tickets**  
The engine sends **one list entry per trade/order** (each with a unique `trade_id` / order ID). If the **Config API** or the **UI** stores or displays trades keyed by (pair, direction), multiple OANDA orders (e.g. two USD/JPY SELL LIMIT with different ticket IDs) will collapse into one row. **Fix:** The server that stores the trades list (e.g. Config API POST /trades) should keep one entry per `trade_id`/order ID, not merge by (pair, direction). The UI should show one row per list item so each OANDA ticket appears separately. The engine also blocks creating a second pending order for the same (pair, direction) in the final gate (checks OANDA pending orders before send).

**Engine load on restart:** The engine loads all trades (OPEN, AT_BREAKEVEN, TRAILING, and **PENDING**) from its state file on startup. Previously PENDING were not loaded, so after a restart only open positions appeared and the UI could show one row for a pair even when OANDA had multiple orders (e.g. 3× GBP/USD). With PENDING loaded, the engine restores the full list and POSTs it to the Config API so the UI can show one row per ticket.

**Duplicate (pair, direction) cleanup on OANDA:** The system **must never** allow multiple open positions or multiple pending orders for the same (pair, direction) on OANDA or on the UI. **Once a pair has an open position, no pending order is allowed for that pair until the open is closed or cancelled.** On every sync with OANDA, the engine runs a **cleanup** step that: (1) groups OANDA open positions by (pair, direction) and **closes** any extras (keeps one—prefer the one we track in active_trades, otherwise the oldest by id); (2) **cancels any pending order for a pair that has an open position** (no pending allowed while pair is open); (3) groups remaining OANDA pending orders by (pair, direction) and **cancels** any extras (same keep rule). So after each sync, OANDA has at most one open per (pair, direction) and at most one pending per (pair, direction), and **no pair has both an open and a pending**. The engine blocks placing a pending order (LIMIT/STOP) when the pair already has an open position (log: `BLOCKED: {pair} already has an open position. No pending order allowed until that position is closed or cancelled`). It also blocks placing a second order for the same (pair, direction) in the final gate (pre-open and pending-orders checks). Logs: `🧹 Cleaned up duplicate open position` / `🧹 Cleaned up duplicate pending order` / `🧹 Cleaned up pending order: {pair} (pair has open position)` when cleanup runs.

---

#### 11. Manual logs error_log (backup script 401/400/403)

Manual logs `error_log.txt` may show **Render 401 Unauthorized** or **Oanda 400/403** (e.g. "Invalid value specified for 'accountID'", "Forbidden"). These errors come from the **log backup script** (BackupRenderLogs), not from Scalp-Engine or Trade-Alerts. If you need successful backup runs, ensure `RENDER_API_KEY` and `OANDA_ACCOUNT_ID` are set in the backup task environment (e.g. `BackupRenderLogs.env.ps1` or the scheduled task’s environment).

---

#### 12. Market state timestamp and staleness (consol-recommend4 Phase 2.6)

The **market state** timestamp is set when Trade-Alerts (or the market-state API) **writes** or **POSTs** a new state. If no new analysis has run, the timestamp does not change. Scalp-Engine may log a warning when state is older than a threshold (e.g. 4 hours). Check `market_state.json` or API for the `timestamp` field.

---

#### 13. Parser failure and consensus (consol-recommend4 Phase 2.2, 2.3)

When an LLM returns text the **parser** cannot interpret, that LLM contributes **0** opportunities. Consensus is computed from LLMs that did return parseable opportunities. "2/3" means two of three contributing LLMs agreed.

**DeepSeek (Phase 2.3)**: The parser tries **MACHINE_READABLE** JSON first, then multiple narrative patterns (ChatGPT, Gemini, Claude, and DeepSeek-friendly patterns such as `Pair: X/Y`, `**Pair:** X/Y`, and `- X/Y Long`). If DeepSeek still returns 0 opportunities, ensure the DeepSeek prompt asks for **structured output** (e.g. a MACHINE_READABLE JSON block or one of the supported narrative formats). The analysis pipeline logs an INFO message when DeepSeek returns non-empty text but 0 parsed opportunities. See §5 for base LLMs and denominator.

**AUD/CHF vs AUD/USD (cursor6 §5.4)**: AUD/CHF and AUD/USD are easy to confuse in LLM or parser output. If DeepSeek (or another LLM) outputs **AUD/CHF** where others output **AUD/USD** for the same direction, consensus for AUD/USD will be one lower (e.g. 3/4 instead of 4/4). No formula change; this is a known forex naming/typo issue. If you see "deepseek: NO MATCH" for AUD/USD while another opportunity shows AUD/CHF from DeepSeek, treat as possible pair mismatch and check LLM output.

---

#### 14. Trading hours and replace-threshold (consol-recommend4 Phase 2.4, 2.5)

**Trading hours**: The engine calls `can_open_new_trade()` before placing orders (Monday 01:00 UTC – Friday 21:30 UTC). Look for "Trading hours" skip or "WEEKEND SHUTDOWN" in logs.

**Replace-only-when-needed**: Pending orders are replaced only when entry improves by ≥ **REPLACE_ENTRY_MIN_PIPS** (default 5), or SL/TP change by ≥ **REPLACE_SL_TP_MIN_PIPS** (default 5). Set via env if needed.

---

#### 15. Position sizing and AUTO mode (consol-recommend4 Phase 3.2, 3.6)

**Position sizing**: See Configuration and Risk Management. Audit compliance with risk standards (e.g. 1–2% per trade).

**AUTO mode**: In AUTO, manual close should be the exception. If many closures are "manual", investigate source (UI, risk logic, orphan handling) before changing code. Confirm mode in UI Configuration tab.

---

#### 16. OANDA app log and transaction history (consol-recommend4 Phase 3.5, cursor5 §5.9)

The **OANDA app log** (Config API `/logs/oanda`) may be empty when there is no recent activity; the backup script may write "(Oanda app log empty - Config API returned 200 with no content...)". For broker-side checks use **OANDA transaction history** (e.g. `oanda_transactions_*.json` from backup or OANDA API).

---

#### 17. Trailing SL verification and trade-close audit log (consol-recommend4 Phase 1.4)

**Trailing SL**: The engine applies trailing stop logic in the **main monitoring loop** for each open trade. For **BE_TO_TRAILING**: when price reaches breakeven (configurable `be_min_pips`), SL is moved to entry; conversion to **trailing stop** happens only when profit ≥ `trailing_activation_min_pips` (default 100). For **ATR_TRAILING**, conversion to trailing uses ATR-based distance and requires **(1)** min age (e.g. 120s), **(2)** OANDA unrealized P/L > 0, and **(3)** profit ≥ **max(trailing_activation_min_pips, trailing distance in pips)** (default 100 pips when config missing). That ensures the initial trailing stop is never placed below entry, avoiding a tiny cushion on retrace. For **longs**, SL moves up (breakeven then trails below price); for **shorts**, SL moves down. Verify in OANDA or logs for "converted to trailing stop" / "profit >= … pips (activation/distance)".

**Trade-close audit log**: Every time a trade is closed (SL, TP, manual, or strategy exit), the engine logs **one INFO line**: `Trade closed: {pair} {direction} exit_reason={reason} final_PnL={pips}`. Use this to audit closure reasons and P&L without changing execution logic.

---

#### 18. OANDA 502 / bad gateway (cursor6 §5.5)

Occasional **502 Bad Gateway** (or 503/504) from OANDA or a proxy is **transient**. The engine retries requests with backoff and does not log raw HTML in the log. You may see a WARNING such as: `OANDA … 502 bad gateway / server error — retry later`. If 502s are **persistent**, check OANDA broker status and your network; the engine will keep retrying up to the configured retry count.

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
