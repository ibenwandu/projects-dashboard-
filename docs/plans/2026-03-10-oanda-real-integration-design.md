# Enhancement #2 Design: OANDA Real Integration

**Date**: March 10, 2026
**Status**: Approved
**Target**: Practice Account Trading with Risk Management

---

## Overview

Enable Emy to connect to OANDA practice account for real trade monitoring and execution with autonomous risk enforcement. This enhancement upgrades TradingAgent from read-only monitoring to active trading capability.

**Scope**: OANDA practice account only (101-002-38030127-001)
**Environment**: practice (not live)
**Risk Model**: Conservative, practice-focused

---

## Architecture

### Components

**TradingAgent Enhanced:**
- Query account status every 15 minutes (existing job)
- Monitor open positions, equity, margin, P&L
- Execute trades based on signals with risk validation
- Log all transactions to database

**Risk Enforcement Layer:**
- Validate every trade against hard limits before execution
- Reject trades that violate parameters
- Log violations with full context
- Alert via Pushover on limit breaches

**Data Persistence:**
- New table: `oanda_trades` (all executed trades)
- New table: `oanda_limits` (risk parameter history)
- Enhanced: `emy_tasks` table with trade execution records

### Data Flow

```
TradingAgent (15-minute tick)
  ├─ Query OANDA API
  │   ├─ Account status
  │   ├─ Open positions
  │   ├─ Equity & P&L
  │   └─ Available margin
  │
  ├─ Log to database
  │   └─ emy_tasks (query results)
  │
  ├─ Receive trade signal (from Scalp-Engine when integrated)
  │   └─ Symbol, direction, units, SL, TP
  │
  ├─ Risk Validation
  │   ├─ Position size ≤ 10,000 units?
  │   ├─ Daily loss ≤ $100?
  │   └─ Concurrent positions ≤ 5?
  │
  ├─ Execute or Reject
  │   ├─ If PASS → Create order via OANDA API
  │   │   ├─ Set SL & TP on fill
  │   │   └─ Log to oanda_trades
  │   │
  │   └─ If FAIL → Log rejection, send Pushover alert
  │
  └─ Update dashboard
      └─ Display metrics in `python emy.py status`
```

---

## Configuration

### Environment Variables (emy/.env)

Add to existing .env file:

```env
# OANDA Trading Integration
OANDA_ACCESS_TOKEN=OANDA_TOKEN_REMOVED
OANDA_ACCOUNT_ID=101-002-38030127-001
OANDA_ENV=practice

# Risk Parameters (enforced autonomously)
OANDA_MAX_POSITION_SIZE=10000
OANDA_MAX_DAILY_LOSS_USD=100
OANDA_MAX_CONCURRENT_POSITIONS=5
```

### Database Schema

**New Table: `oanda_trades`**
```sql
CREATE TABLE oanda_trades (
    id INTEGER PRIMARY KEY,
    trade_id TEXT UNIQUE,
    account_id TEXT,
    symbol TEXT,
    units INTEGER,
    direction TEXT,  -- BUY/SELL
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT,  -- OPEN/CLOSED/REJECTED
    reason_rejected TEXT,
    opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    pnl_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**New Table: `oanda_limits`**
```sql
CREATE TABLE oanda_limits (
    id INTEGER PRIMARY KEY,
    date TEXT,
    max_position_size INTEGER,
    max_daily_loss_usd REAL,
    max_concurrent_positions INTEGER,
    daily_loss_usd REAL,
    concurrent_open_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Risk Enforcement

### Hard Limits (Non-negotiable)

All limits are **hard stops** — trades exceeding limits are automatically rejected.

**Validation Sequence:**
```
1. Position Size Check
   IF units > OANDA_MAX_POSITION_SIZE:
       REJECT trade
       LOG: "Position size {units} exceeds limit {max}"
       ALERT: Pushover notification
       RETURN

2. Daily Loss Check
   IF cumulative_daily_loss > OANDA_MAX_DAILY_LOSS_USD:
       REJECT trade
       LOG: "Daily loss limit reached"
       ALERT: Pushover notification
       RETURN

3. Concurrent Position Check
   IF open_position_count >= OANDA_MAX_CONCURRENT_POSITIONS:
       REJECT trade
       LOG: "Max concurrent positions ({count}) reached"
       ALERT: Pushover notification
       RETURN

4. Margin Check (OANDA API validates)
   IF available_margin < required_margin:
       REJECT trade (API error)
       LOG: "Insufficient margin"
       ALERT: Pushover notification
       RETURN

5. ALL CHECKS PASS
   → Execute trade via OANDA API
   → Set SL & TP on fill
   → Log to oanda_trades table
   → Return trade_id and confirmation
```

### Monitoring Daily Limits

- **Reset**: Every day at 00:00 EST
- **Tracking**: Query `oanda_trades` WHERE DATE(opened_at) = TODAY()
- **Calculation**: SUM(pnl_usd WHERE status='CLOSED') + mark-to-market unrealized loss
- **Enforcement**: Check at trade time against daily total

### Violation Handling

**Automatic Actions:**
1. Reject trade (do not send to OANDA)
2. Log violation to `oanda_trades` with status='REJECTED' and reason
3. Send Pushover alert with violation details
4. Continue monitoring (do not halt system)

**Manual Override:**
- User can temporarily increase limits via `.env` adjustment
- Requires manual `.env` edit + system restart
- No dynamic runtime adjustments (for safety)

---

## Monitoring & Alerting

### Real-Time Monitoring

**TradingAgent every 15 minutes:**
- Query account equity, margin, P&L
- Count open positions
- Detect closed trades
- Log all metrics to `emy_tasks` table

**Daily Summary:**
- Equity change from start of day
- P&L (realized + unrealized)
- Number of trades executed
- Number of trades rejected
- Risk violations (if any)

### Alerts via Pushover

**Sent when:**
1. Trade executed successfully
2. Trade rejected (limit violation)
3. Account equity drops below threshold
4. Margin utilization exceeds 80%
5. Daily loss approaches limit (75% used)

**Format:**
```
[OANDA] Trade Executed: EURUSD BUY 5,000 units @ 1.0850, SL:1.0820, TP:1.0900

[OANDA] Trade Rejected: Position size 12,000 exceeds limit 10,000

[OANDA] Alert: Daily loss reached $75/$100 (75%)
```

### Dashboard Integration

`python emy.py status` displays:
```
[OANDA Account]
  Equity: $50,234
  Available Margin: $45,000
  Margin Utilization: 10%
  P&L Today: +$234
  Daily Loss Limit: $100 (0% used)
  Open Positions: 2
  Position Limit: 5 (40% used)

[Recent Trades]
  EUR/USD BUY 5,000 — OPEN (SL:1.0820, TP:1.0900)
  USD/JPY SELL 3,000 — CLOSED, P&L: +$45
```

---

## Implementation Components

### 1. Update emy/tools/api_client.py

**OandaClient class enhancements:**
- `execute_trade()` — Create market order with SL/TP
- `get_account_summary()` — Equity, margin, P&L
- `get_open_positions()` — List current trades
- `close_trade()` — Exit position
- `validate_order()` — Pre-flight checks (margin, limits)

### 2. Update emy/agents/trading_agent.py

**TradingAgent enhancements:**
- Add `_validate_trade()` method (risk enforcement)
- Add `_execute_trade()` method (OANDA API call)
- Add `_monitor_account()` method (status queries)
- Update existing `run()` to call new methods

### 3. Update emy/core/database.py

**EMyDatabase enhancements:**
- Add `create_oanda_trades_table()` migration
- Add `create_oanda_limits_table()` migration
- Add CRUD methods: log_trade, get_daily_pnl, get_open_positions
- Add risk check methods: check_position_size, check_daily_loss, check_concurrent

### 4. Update emy/.env

**Add OANDA configuration** (credentials + risk parameters)

### 5. Testing

**Unit tests:**
- Risk validation logic (position size, daily loss, concurrent count)
- Margin calculation
- Trade rejection scenarios

**Integration tests:**
- Connect to OANDA practice API (requires credentials)
- Validate account query
- Execute test trade (1 unit)
- Verify trade logged to database
- Verify SL/TP set correctly

**Smoke test:**
- Deploy to Windows Task Scheduler
- Monitor 24 hours of autonomous operation
- Verify database records match OANDA API history
- Check Pushover alerts firing correctly

---

## Success Criteria

✓ OANDA credentials configured in .env
✓ Risk validation logic passes unit tests
✓ Test trade executes successfully with SL/TP
✓ Trade logged to `oanda_trades` table with all details
✓ Dashboard shows live account metrics
✓ Trade rejection triggers Pushover alert
✓ Daily limit reset works at midnight
✓ 24-hour autonomous operation without errors

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| API credential exposure | Stored in .env (gitignored), never logged |
| Runaway trading (no SL) | Enforced at TradingAgent level; all trades require SL/TP |
| Margin call | Daily loss + concurrent position limits prevent overleverage |
| API errors | Wrapped in try-catch; failures logged + alert sent |
| Practice account equity depletion | Daily $100 loss limit prevents > $700/week loss |
| Time zone confusion | All timestamps in EST, clearly marked in logs |

---

## Timeline

- **Phase 1**: Database schema + OandaClient (1-2 hours)
- **Phase 2**: TradingAgent enhancement + risk validation (2-3 hours)
- **Phase 3**: Testing + integration (1-2 hours)
- **Phase 4**: Deployment + 24-hour monitoring (ongoing)

**Estimated Total**: 4-7 hours implementation + validation

---

## Notes

- This is **practice account only** — no live funds at risk
- Risk parameters are conservative to enable learning
- Autonomous enforcement prevents human error
- All trades logged for analysis and improvement
- System continues operating even if a trade is rejected (fail-safe)

---

**Design approved by**: Ibe Nwandu
**Date approved**: March 10, 2026
**Next step**: Implementation planning (writing-plans skill)
