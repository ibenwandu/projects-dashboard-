# Enhancement #3 Design: Pushover Alerts for OANDA Trading

**Date**: March 10, 2026
**Status**: Approved
**Target**: Real-time notifications for trade execution and risk alerts

---

## Overview

Enable Emy to send real-time Pushover notifications for critical OANDA trading events. Alerts use priority differentiation to prevent fatigue while maintaining responsiveness. Throttling prevents duplicate alerts within 60-second windows per event type.

**Scope**: Trade execution, rejection, and daily loss warnings
**Credentials**: User and API token provided and configured

---

## Architecture

### Alert System Components

**Notification Service** (`notification_tool.py`):
- Sends Pushover API requests via HTTPS
- Handles timeouts (5-second max)
- Retries on network failures
- Logs all alert activity to database

**Throttling Engine** (in TradingAgent):
- Tracks last alert time per event type
- Suppresses duplicate alerts within 60-second window
- Independent counters for each event type
- Allows concurrent different event types

**Integration Points**:
- TradingAgent._execute_trade() — sends "Trade Executed" alert
- TradingAgent._validate_trade() — sends "Trade Rejected" alert
- TradingAgent run() — sends "Daily Loss Warning" alerts
- Risk validation checks — triggers "Daily Loss 100%" emergency alert

### Alert Priority Levels

Pushover supports 3 priority levels with different notification behaviors:

| Priority | Level | Notification | Use Case |
|----------|-------|--------------|----------|
| **Normal** | 0 | Default sound, no vibration | Routine events (trade executed, rejected) |
| **High** | 1 | Louder sound, vibration | Warnings that need attention (daily loss 75%) |
| **Emergency** | 2 | Continuous sound, multiple retries | Critical events (daily loss 100%, trading stopped) |

---

## Alert Specifications

### Event 1: Trade Executed

**Trigger**: TradingAgent successfully executes trade on OANDA
**Priority**: Normal (0)
**Message Format**:
```
OANDA: [SYMBOL] [DIRECTION] [UNITS] @ [ENTRY_PRICE]
SL:[STOP_LOSS] TP:[TAKE_PROFIT]
```

**Example**:
```
OANDA: EUR/USD BUY 5,000 @ 1.0850
SL:1.0820 TP:1.0900
```

**Throttle**: 60 seconds (one per minute max)
**Persistent**: No (doesn't require acknowledgment)

### Event 2: Trade Rejected

**Trigger**: Risk validation blocks trade (position size, daily loss, or concurrent position limit)
**Priority**: Normal (0)
**Message Format**:
```
OANDA: [SYMBOL] [DIRECTION] [UNITS] REJECTED
Reason: [VALIDATION_ERROR]
```

**Example**:
```
OANDA: GBP/USD BUY 15000 REJECTED
Reason: Position size 15,000 exceeds limit 10,000
```

**Throttle**: 60 seconds per rejection type
**Persistent**: No

### Event 3: Daily Loss Warning (75%)

**Trigger**: Daily loss reaches 75% of $100 limit ($75 loss)
**Priority**: High (1)
**Message Format**:
```
OANDA Alert: Daily loss 75% ($75/$100)
Monitor closely. Further losses will trigger emergency stop.
```

**Throttle**: 60 seconds (fires once when hitting 75%)
**Persistent**: No
**Action**: User should review open positions and market conditions

### Event 4: Daily Loss Emergency (100%)

**Trigger**: Daily loss reaches 100% of $100 limit ($100 loss), trading stops
**Priority**: Emergency (2)
**Message Format**:
```
OANDA STOP: Daily loss limit hit ($100)
Trading disabled until market open tomorrow (UTC)
```

**Throttle**: 60 seconds (fires once when hitting 100%)
**Persistent**: Yes (Pushover will retry for 60 minutes)
**Action**: CRITICAL — System has stopped trading; investigate immediately

---

## Configuration

### Environment Variables

Add to `emy/.env`:

```env
# Pushover Notification Integration
PUSHOVER_USER_KEY=uisf5xhhm3ei3bwmj6hf9a2yoy5j
PUSHOVER_API_TOKEN=a5otpscylwh6nve34okvtzo8uv4knn
PUSHOVER_ALERT_ENABLED=true
```

### Optional: Alert Control

```env
# Set to false to disable all Pushover alerts (for testing/maintenance)
PUSHOVER_ALERT_ENABLED=true

# Alert priority overrides (advanced)
# PUSHOVER_OVERRIDE_PRIORITY=normal|high|emergency
```

---

## Data Flow

### Trade Execution Flow

```
TradingAgent._execute_trade()
  ├─ Call OandaClient.execute_trade()
  ├─ Log to oanda_trades table (status='OPEN')
  ├─ Check throttle: should send alert?
  │   ├─ Yes: Send Pushover alert (Normal priority)
  │   └─ No: Skip (within 60-second window)
  └─ Log alert attempt to emy_tasks table
```

### Trade Rejection Flow

```
TradingAgent._validate_trade()
  ├─ Check position size limit
  ├─ Check daily loss limit
  ├─ Check concurrent position limit
  ├─ If rejected:
  │   ├─ Log rejection to oanda_trades (status='REJECTED')
  │   ├─ Check throttle
  │   │   ├─ Yes: Send Pushover alert (Normal priority)
  │   │   └─ No: Skip
  │   └─ Log alert to emy_tasks
  └─ Return (is_valid, reason)
```

### Daily Loss Warning Flow

```
TradingAgent.run()
  ├─ Call db.update_daily_limits()
  ├─ Get daily_pnl from database
  ├─ If daily_loss > $75 AND < $100:
  │   ├─ Check throttle (75% alert)
  │   ├─ Send Pushover (High priority)
  │   └─ Log to emy_tasks
  ├─ Else if daily_loss >= $100:
  │   ├─ Check throttle (100% alert)
  │   ├─ Send Pushover (Emergency priority)
  │   ├─ Disable trading (set .emy_disabled)
  │   └─ Log to emy_tasks
  └─ Continue
```

---

## Throttling Mechanism

### Design

Throttling prevents alert fatigue by suppressing duplicate alerts within a 60-second window. Each event type has independent throttle counter.

### Implementation

**Throttle State Storage**:
```python
self.last_alert_time = {
    'trade_executed': None,
    'trade_rejected': None,
    'daily_loss_75': None,
    'daily_loss_100': None
}
```

**Check Before Alert**:
```python
def should_send_alert(self, alert_type):
    last_time = self.last_alert_time.get(alert_type)
    if last_time is None:
        return True  # First alert of this type

    elapsed = time.time() - last_time
    return elapsed >= 60  # Only send if 60+ seconds passed
```

**Update After Alert**:
```python
if should_send_alert(alert_type):
    send_pushover_alert(...)
    self.last_alert_time[alert_type] = time.time()
```

### Throttle Bypass

For testing/emergency, add environment variable:
```env
# Disable throttling (testing only)
PUSHOVER_NO_THROTTLE=false  # Set to true to bypass throttle
```

---

## Error Handling

### Scenario 1: Pushover API Timeout

**Condition**: API call takes >5 seconds
**Action**:
- Log warning: "Pushover API timeout, alert not sent"
- Continue trading (don't crash)
- Don't retry (alert window will open later)

**Impact**: Alert lost, but trading continues

### Scenario 2: Invalid Credentials

**Condition**: PUSHOVER_USER_KEY or PUSHOVER_API_TOKEN missing/invalid
**Action**:
- Log error on first attempt
- Skip all future Pushover calls
- Continue trading with local logging only
- Operator should check logs and fix credentials

**Impact**: No alerts but system continues

### Scenario 3: Network Failure

**Condition**: No internet connectivity
**Action**:
- Log error: "Network error, Pushover unavailable"
- Continue trading (alerts not critical for safety)
- Retry next alert opportunity (may combine alerts)

**Impact**: Delayed alerts, possible loss of some messages

### Scenario 4: Database Failure While Logging Alert

**Condition**: emy_tasks table insert fails
**Action**:
- Alert already sent to Pushover (independent)
- Log to stderr: "Failed to log alert to database"
- Continue trading

**Impact**: Alert sent but not recorded in database (minor)

---

## Testing Strategy

### Unit Tests

1. **Throttle Logic**
   - First alert fires (no throttle history)
   - Second alert within 60s blocked
   - Third alert after 60s fires
   - Multiple event types independent

2. **Alert Priority Assignment**
   - Trade executed = Normal
   - Trade rejected = Normal
   - Daily loss 75% = High
   - Daily loss 100% = Emergency

3. **Message Formatting**
   - All required fields present
   - Numbers formatted correctly
   - No missing brackets or syntax errors

### Integration Tests

1. **End-to-End Trade Alert**
   - Execute trade → Pushover API called
   - Verify request includes correct priority
   - Check alert logged to database

2. **Rejection Alert**
   - Force position size rejection
   - Verify rejection alert sent
   - Verify separate from execution alerts

3. **Daily Loss Warning**
   - Simulate $75 daily loss
   - Verify High priority alert sent
   - Verify no Emergency alert

4. **Daily Loss Emergency**
   - Simulate $100+ daily loss
   - Verify Emergency priority alert sent
   - Verify .emy_disabled set to disable trading
   - Verify alert logged as critical

### Mock Tests

- Mock Pushover API responses (success, timeout, 401, 500)
- Mock network failures
- Verify retry logic and error handling
- Test throttling with time mocks

---

## Success Criteria

✅ Pushover credentials configured in .env
✅ Notification service sends alerts with correct priorities
✅ Throttling prevents duplicate alerts (60-second window)
✅ Trade execution triggers Normal priority alert
✅ Trade rejection triggers Normal priority alert
✅ Daily loss 75% triggers High priority alert
✅ Daily loss 100% triggers Emergency priority alert + disables trading
✅ All alert activity logged to database
✅ Error handling prevents system crashes
✅ Tests pass (unit + integration)

---

## Dependencies

- **Pushover SDK**: Requires HTTP requests library (already in requirements.txt)
- **Environment**: .env file with Pushover credentials
- **Database**: emy_tasks table for logging alerts
- **TradingAgent**: Integration points for alert triggers

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Alert spam if many trades execute | Throttling (60s per event type) prevents fatigue |
| Pushover API outage = missed alerts | Alerts logged locally; not critical for safety |
| Operator ignores alerts | Emergency priority (99% retry) ensures high visibility |
| Credentials exposed in logs | Never log credential values, only "[configured]" |
| Alert system crashes Emy | All Pushover calls in try/except; trading continues |
| Daily loss triggers trading halt but user doesn't notice | Emergency alert retries for 60 minutes via Pushover |

---

## Timeline

- **Phase 1**: Implement notification service (1 hour)
- **Phase 2**: Integrate alerts into TradingAgent (1.5 hours)
- **Phase 3**: Add throttling logic (30 minutes)
- **Phase 4**: Testing + documentation (1 hour)

**Total**: ~4 hours

---

**Design approved by**: Ibe Nwandu
**Date approved**: March 10, 2026
**Next step**: Implementation planning (writing-plans skill)
