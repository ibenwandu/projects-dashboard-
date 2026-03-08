# Check Scalp-Engine RL Database Status

## How Often Is the Database Updated?

### 1. **Signals Logged** (Event-Driven, Independent of Execution)
- **When**: Every time a trading signal is detected (similar to Trade-Alerts logging recommendations)
- **Method**: `rl_tracker.log_signal()` is called (line 417 in `scalp_engine.py`)
- **Frequency**: Not periodic - happens when:
  - Market conditions meet criteria
  - Signal strength > 0.5
  - RL historical performance check passes (if applicable)
- **Important**: Signals are logged **regardless of whether trades are executed** - this happens **before** trade execution, just like Trade-Alerts logs recommendations regardless of execution

### 2. **Outcomes Updated** (Every 30 seconds - Only for Executed Trades)
- **When**: Every 30 seconds, but **only if trades were actually executed** (not just signals detected)
- **Method**: `_check_closed_trades()` calls `rl_tracker.update_outcome()` (line 301 in `scalp_engine.py`)
- **Frequency**: `trade_check_interval = 30` seconds (line 154)
- **Checks**: Compares executed active trades with OANDA open trades to detect when they close
- **Note**: If a signal is logged but the trade is not executed (e.g., manual mode "no", or risk filter), the outcome remains "PENDING" and is never updated

---

## How to Confirm Database Is Being Populated

### Option 1: Check Database on Render (Recommended)

**On Render Shell:**

```bash
cd /opt/render/project/src
python -c "
import sqlite3
import os

# Database path on Render (shared disk)
db_path = '/var/data/scalping_rl.db'

if not os.path.exists(db_path):
    print('❌ Database file does not exist at:', db_path)
    print('   → Scalp-Engine may not be running')
    print('   → Or database path is different')
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Total signals
cursor.execute('SELECT COUNT(*) FROM signals')
total = cursor.fetchone()[0]
print(f'📊 Total Signals in Database: {total}')

if total > 0:
    # By outcome
    cursor.execute('''
        SELECT outcome, COUNT(*) as count
        FROM signals
        GROUP BY outcome
    ''')
    print('\n📋 Signals by Outcome:')
    for outcome, count in cursor.fetchall():
        status_desc = 'Never executed' if outcome == 'PENDING' else 'Executed & closed'
        print(f'   {outcome}: {count} ({status_desc})')
    
    # By pair
    cursor.execute('''
        SELECT pair, COUNT(*) as count
        FROM signals
        GROUP BY pair
        ORDER BY count DESC
    ''')
    print('\n📊 Signals by Pair:')
    for pair, count in cursor.fetchall():
        print(f'   {pair}: {count}')
    
    # Recent signals
    cursor.execute('''
        SELECT id, timestamp, pair, direction, regime, strength, outcome, pnl
        FROM signals
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    print('\n📅 Recent Signals:')
    for row in cursor.fetchall():
        sig_id, ts, pair, direction, regime, strength, outcome, pnl = row
        print(f'   ID {sig_id}: {pair} {direction} @ {ts[:19]} - {regime} (Strength: {strength:.2f}) - {outcome} (PnL: {pnl:.2f})')
    
    # Performance stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN outcome = \"WIN\" THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = \"LOSS\" THEN 1 ELSE 0 END) as losses,
            AVG(pnl) as avg_pnl
        FROM signals
        WHERE outcome != \"PENDING\"
    ''')
    stats = cursor.fetchone()
    if stats[0] > 0:
        total_completed, wins, losses, avg_pnl = stats
        win_rate = wins / total_completed if total_completed > 0 else 0
        print(f'\n📈 Performance (Completed Trades):')
        print(f'   Total: {total_completed}')
        print(f'   Wins: {wins} ({win_rate:.1%})')
        print(f'   Losses: {losses}')
        print(f'   Avg PnL: {avg_pnl:.2f}')
else:
    print('\n❌ NO SIGNALS IN DATABASE!')
    print('   → Signals are NOT being logged')
    print('   → Check if Scalp-Engine is running')
    print('   → Check if signals are being detected')
    print('   → Look for \"🔔 SIGNAL:\" messages in logs')

conn.close()
"
```

### Option 2: Using SQLite Command Line (If SQLite3 is Available)

```bash
cd /opt/render/project/src

# Check if database exists
ls -lh /var/data/scalping_rl.db

# Total signals
sqlite3 /var/data/scalping_rl.db "SELECT COUNT(*) as total_signals FROM signals;"

# Pending signals
sqlite3 /var/data/scalping_rl.db "SELECT COUNT(*) as pending FROM signals WHERE outcome = 'PENDING';"

# Completed signals
sqlite3 /var/data/scalping_rl.db "SELECT COUNT(*) as completed FROM signals WHERE outcome != 'PENDING';"

# Recent signals
sqlite3 /var/data/scalping_rl.db "SELECT id, timestamp, pair, direction, regime, strength, outcome, pnl FROM signals ORDER BY timestamp DESC LIMIT 5;"
```

### Option 3: Check via Scalp-Engine UI

The Scalp-Engine UI (`scalp_ui.py`) displays database statistics automatically:
- Total signals
- Win/loss breakdown
- Recent signals
- Performance metrics

**Access**: Go to Scalp-Engine UI URL (usually `https://scalp-engine-ui.onrender.com`)

---

## Expected Behavior

### If Scalp-Engine Is Running and Finding Signals:

1. **Signals Logged** (Like Trade-Alerts Recommendations): You should see new records in the `signals` table when:
   - Market conditions meet criteria
   - Approved pairs are available from Trade-Alerts
   - Signal strength > 0.5
   - **Signals are logged BEFORE execution** - regardless of whether trades are executed (just like Trade-Alerts logs recommendations)
   - **All detected signals are logged**, even if:
     - Manual mode: User says "no"
     - Risk filter: Trade is blocked
     - RL filter: Historical performance is too low

2. **Outcomes Updated** (Only for Executed Trades): Every 30 seconds, **only if trades were actually executed**:
   - `_check_closed_trades()` runs (line 390-392)
   - Only checks trades that were executed and opened on OANDA
   - When a trade closes, the outcome is updated with PnL
   - Status changes from "PENDING" to "WIN" or "LOSS"
   - **Note**: Signals that were logged but never executed will remain "PENDING" forever

### If Database Is Empty:

**Possible Reasons:**
1. **Scalp-Engine not running** - Check Render dashboard
2. **No approved pairs** - Trade-Alerts may not be providing pairs
3. **No signals detected** - Market conditions don't meet criteria
4. **Database path mismatch** - Database may be at different location

---

## Quick Diagnostic Commands

### Check Database File Size

```bash
cd /opt/render/project/src
ls -lh /var/data/scalping_rl.db
```

- **Expected**: File exists and size > 0 bytes
- **If 0 bytes or doesn't exist**: Database not being used

### Check Recent Activity

```bash
cd /opt/render/project/src
python -c "
import sqlite3
from datetime import datetime, timedelta

db_path = '/var/data/scalping_rl.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Signals in last 24 hours
cursor.execute('''
    SELECT COUNT(*) 
    FROM signals 
    WHERE timestamp > datetime('now', '-1 day')
''')
recent = cursor.fetchone()[0]
print(f'Signals in last 24 hours: {recent}')

conn.close()
"
```

### Check for Pending Trades

```bash
cd /opt/render/project/src
python -c "
import sqlite3

db_path = '/var/data/scalping_rl.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM signals WHERE outcome = \"PENDING\"')
pending = cursor.fetchone()[0]
print(f'Pending signals (open trades): {pending}')

if pending > 0:
    cursor.execute('''
        SELECT id, timestamp, pair, direction 
        FROM signals 
        WHERE outcome = \"PENDING\"
        ORDER BY timestamp DESC
    ''')
    print('\nPending signals:')
    for row in cursor.fetchall():
        print(f'   ID {row[0]}: {row[2]} {row[3]} @ {row[1][:19]}')

conn.close()
"
```

---

## Monitoring Logs for Database Activity

Watch Scalp-Engine logs for these messages:

1. **Signal Logged**: 
   ```
   🔔 SIGNAL: BUY GBP/USD (Strength: 0.75)
   ✅ Trade tracking enabled (Signal ID: 1, Trade ID: 67890)
   ```

2. **Outcome Updated**:
   ```
   📊 Trade 67890 closed: PnL = 8.50
   ✅ RL Update: Trade 1 closed as WIN (8.50)
   ```

3. **Database Initialized**:
   ```
   📦 Initializing RL Database...
   ✅ RL Database initialized successfully at: /var/data/scalping_rl.db
   ```

---

## Troubleshooting

### If Database Shows 0 Signals:

1. **Check if Scalp-Engine is running**:
   - Render Dashboard → `scalp-engine` service
   - Should show "Running" status

2. **Check logs for signal detection**:
   - Look for "🔔 SIGNAL:" messages
   - Look for "PAUSED: No approved pairs" (normal if waiting)

3. **Check if approved pairs are available**:
   - Trade-Alerts should provide approved pairs
   - Check `market_state.json` for `approved_pairs`

4. **Check execution mode**:
   - If in "manual" mode, signals may be logged but trades not executed
   - Check `config.yaml` → `execution.mode`

### If Signals Are Logged But Outcomes Never Update:

This is **normal** if trades are not being executed. Outcomes are only updated for signals that:
- Were logged (signal detected) ✅
- AND were executed (trade opened on OANDA) ✅
- AND then closed (trade hit TP/SL or was closed) ✅

If signals are logged but outcomes never update:
1. **Check if trades are actually executing** (look for "EXECUTING:" messages in logs)
2. **Check execution mode** (manual mode may have trades rejected)
3. **Check OANDA connection** (trades may not be opening even if execution attempted)
4. **Check `active_trades` tracking** (trades may not be linked to signals correctly)
5. **Normal behavior**: Many signals may be logged but never executed (similar to Trade-Alerts where recommendations are logged regardless of execution)
