# Emy Trading System Monitoring Agents — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Implement three independent monitoring agents with Celery Beat scheduling, autonomous trading hours enforcement, and Claude-powered analysis.

**Architecture:** Three separate EMySubAgent classes (TradingHoursMonitorAgent, LogAnalysisAgent, ProfitabilityAgent) scheduled via Celery Beat. Each agent gathers data from OANDA API and RL databases, performs analysis with Claude, stores results in EMyDatabase, and sends Pushover alerts for critical issues.

**Tech Stack:** EMySubAgent framework, Celery Beat, OANDA API, EMyDatabase, Claude (Haiku/Sonnet), Pushover, SQLite

---

## Task 1: Create Database Schema for Monitoring Reports and Audit Trail

**Files:**
- Modify: `emy/core/database.py:initialize_schema()` — add table creation SQL

**Step 1: Write failing test**

```python
# emy/tests/test_monitoring_database.py
import pytest
from emy.core.database import EMyDatabase

def test_monitoring_reports_table_exists():
    """Test that monitoring_reports table is created."""
    db = EMyDatabase()
    db.initialize_schema()

    # Query should return successfully
    result = db.query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='monitoring_reports'"
    )
    assert result is not None
    assert result[0] == 'monitoring_reports'

def test_enforcement_audit_table_exists():
    """Test that enforcement_audit table is created."""
    db = EMyDatabase()
    db.initialize_schema()

    result = db.query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='enforcement_audit'"
    )
    assert result is not None
    assert result[0] == 'enforcement_audit'

def test_insert_monitoring_report():
    """Test inserting a monitoring report."""
    db = EMyDatabase()
    db.initialize_schema()

    db.execute(
        """INSERT INTO monitoring_reports
           (report_type, timestamp, critical, alert_message)
           VALUES (?, ?, ?, ?)""",
        ('trading_hours', '2026-03-16T21:30:00Z', 1, 'Test alert')
    )

    result = db.query_one(
        "SELECT report_type, critical FROM monitoring_reports WHERE report_type='trading_hours'"
    )
    assert result[0] == 'trading_hours'
    assert result[1] == 1

def test_insert_enforcement_audit():
    """Test inserting an enforcement audit record."""
    db = EMyDatabase()
    db.initialize_schema()

    db.execute(
        """INSERT INTO enforcement_audit
           (timestamp, trade_id, pair, direction, entry_price, close_price, realized_pnl, closure_reason)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ('2026-03-16T21:30:00Z', '123456', 'EUR_USD', 'LONG', 1.0950, 1.0965, 45.00, 'Trading window closed')
    )

    result = db.query_one(
        "SELECT trade_id, pair FROM enforcement_audit WHERE trade_id='123456'"
    )
    assert result[0] == '123456'
    assert result[1] == 'EUR_USD'
```

**Step 2: Run test to verify it fails**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_monitoring_database.py -v
```

Expected: FAIL — tables don't exist

**Step 3: Write minimal implementation**

Add to `emy/core/database.py` in the `initialize_schema()` method:

```python
def initialize_schema(self):
    """Create all tables if they don't exist."""
    with self.get_connection() as conn:
        cursor = conn.cursor()

        # ... existing table creation code ...

        # Monitoring Reports Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS monitoring_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            period_start DATETIME,
            period_end DATETIME,
            enforcement_action BOOLEAN DEFAULT 0,
            trades_affected TEXT,
            total_pnl REAL,
            findings TEXT,
            analysis TEXT,
            recommendations TEXT,
            critical BOOLEAN DEFAULT 0,
            alert_message TEXT,
            data_sources TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp
                         ON monitoring_reports(timestamp DESC)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_monitoring_type
                         ON monitoring_reports(report_type)''')

        # Enforcement Audit Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS enforcement_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            trade_id TEXT NOT NULL,
            pair TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            close_price REAL,
            realized_pnl REAL,
            closure_reason TEXT NOT NULL,
            closed_by TEXT DEFAULT 'Emy',
            report_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES monitoring_reports(id)
        )''')

        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                         ON enforcement_audit(timestamp DESC)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_audit_pair
                         ON enforcement_audit(pair)''')

        conn.commit()
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_monitoring_database.py -v
```

Expected: PASS (4/4 tests)

**Step 5: Commit**

```bash
git add emy/core/database.py emy/tests/test_monitoring_database.py
git commit -m "feat: Add monitoring_reports and enforcement_audit database tables

- monitoring_reports: Stores all monitoring agent reports
  * Columns: report_type, timestamp, findings, analysis, critical, alert_message
  * Indexes on timestamp and report_type for quick queries

- enforcement_audit: Audit trail for trade closures
  * Columns: timestamp, trade_id, pair, direction, entry/close price, realized_pnl, reason
  * Indexes on timestamp and pair for compliance review
  * Foreign key to monitoring_reports for linking closures to reports

TDD approach: 4 tests passing"

---

## Task 2: Add close_trade() Method to OandaClient

**Files:**
- Modify: `emy/tools/api_client.py` — add `close_trade(trade_id, reason)` method

**Step 1: Write failing test**

```python
# emy/tests/test_oanda_client.py (add to existing file)
import pytest
from emy.tools.api_client import OandaClient
from unittest.mock import MagicMock, patch

def test_close_trade_success():
    """Test closing a trade successfully."""
    client = OandaClient()

    # Mock the OANDA client
    client.client = MagicMock()
    client.account_id = 'test-account-123'

    # Mock successful close response
    mock_response = {
        'orderFillTransaction': {
            'tradesClosed': [
                {
                    'tradeID': '123456',
                    'realizedPL': '45.00'
                }
            ]
        }
    }

    client.client.request = MagicMock()
    mock_request = MagicMock()
    mock_request.response = mock_response
    client.client.request.return_value = mock_request

    # Test close_trade
    result = client.close_trade(trade_id='123456', reason='Test closure')

    assert result is not None
    assert result.get('success') == True
    assert result.get('realized_pl') == 45.00

def test_close_trade_failure():
    """Test closing a trade with API error."""
    client = OandaClient()
    client.client = MagicMock()
    client.account_id = 'test-account-123'

    # Mock API error
    client.client.request = MagicMock(side_effect=Exception('API Error'))

    result = client.close_trade(trade_id='999999', reason='Test error')

    assert result.get('success') == False
    assert 'error' in result
```

**Step 2: Run test to verify it fails**

```bash
pytest emy/tests/test_oanda_client.py::test_close_trade_success -v
pytest emy/tests/test_oanda_client.py::test_close_trade_failure -v
```

Expected: FAIL — method doesn't exist

**Step 3: Write minimal implementation**

Add to `emy/tools/api_client.py` in OandaClient class:

```python
def close_trade(self, trade_id: str, reason: str = None) -> Dict:
    """
    Close an open trade at market price.

    Args:
        trade_id: OANDA trade ID
        reason: Optional reason for closure (for logging)

    Returns:
        Dict with success status and realized P&L, or error info
    """
    try:
        from oandapyV20.endpoints.trades import TradeClose

        # Close the trade
        r = TradeClose(
            accountID=self.account_id,
            tradeID=trade_id,
            data={'units': 'ALL'}
        )
        self.client.request(r)

        # Extract results
        response = r.response
        trades_closed = response.get('orderFillTransaction', {}).get('tradesClosed', [])

        if trades_closed:
            trade = trades_closed[0]
            realized_pl = float(trade.get('realizedPL', 0))

            return {
                'success': True,
                'trade_id': trade_id,
                'realized_pl': realized_pl,
                'reason': reason
            }
        else:
            return {
                'success': False,
                'error': 'No trades closed',
                'trade_id': trade_id
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'trade_id': trade_id
        }
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_oanda_client.py::test_close_trade_success -v
pytest emy/tests/test_oanda_client.py::test_close_trade_failure -v
```

Expected: PASS (2/2 tests)

**Step 5: Commit**

```bash
git add emy/tools/api_client.py emy/tests/test_oanda_client.py
git commit -m "feat: Add OandaClient.close_trade() method

- Closes open trades at market price via OANDA API
- Accepts optional reason for logging (e.g. 'Trading window closed')
- Returns success status with realized P&L or error details
- Handles API errors gracefully with detailed error messages

Used by TradingHoursMonitorAgent for autonomous enforcement"

---

## Task 3: Implement TradingHoursMonitorAgent Base Class

**Files:**
- Create: `emy/agents/trading_hours_monitor_agent.py`
- Create: `emy/tests/test_trading_hours_monitor_agent.py`

**Step 1: Write failing test**

```python
# emy/tests/test_trading_hours_monitor_agent.py
import pytest
from unittest.mock import MagicMock
from emy.agents.trading_hours_monitor_agent import TradingHoursMonitorAgent
from emy.core.database import EMyDatabase

def test_trading_hours_monitor_agent_init():
    """Test TradingHoursMonitorAgent initialization."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    assert agent.agent_name == 'TradingHoursMonitorAgent'
    assert agent.db is not None
    assert agent.oanda_client is not None
    assert agent.alert_manager is not None

def test_trading_hours_monitor_agent_run_returns_tuple():
    """Test that run() returns (bool, dict)."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    # Mock OANDA client to return no trades
    agent.oanda_client.list_open_trades = MagicMock(return_value=[])

    result = agent.run()

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], dict)
```

**Step 2: Run test to verify it fails**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py -v
```

Expected: FAIL — class doesn't exist

**Step 3: Write minimal implementation**

Create `emy/agents/trading_hours_monitor_agent.py`:

```python
"""
TradingHoursMonitorAgent - Monitors and enforces trading hours compliance.

Responsibilities:
- Monitor: Verify trades are closing at correct times (every 6 hours)
- Enforce: Automatically close non-compliant trades at 21:30 Fri, 23:00 Mon-Thu
- Alert: Send Pushover critical alerts with closure summary
- Audit: Log all enforcement actions to enforcement_audit table
"""

import logging
from typing import Tuple, Dict, Any
from datetime import datetime
import pytz

from emy.agents.base_agent import EMySubAgent
from emy.tools.api_client import OandaClient
from emy.tools.notification_tool import PushoverNotifier
from emy.core.alert_manager import AlertManager

logger = logging.getLogger('TradingHoursMonitorAgent')


class TradingHoursMonitorAgent(EMySubAgent):
    """Agent for monitoring and enforcing trading hours compliance."""

    def __init__(self, db=None):
        """Initialize TradingHoursMonitorAgent.

        Args:
            db: EMyDatabase instance (optional, for testing)
        """
        super().__init__('TradingHoursMonitorAgent', 'claude-haiku-4-5-20251001')
        self.oanda_client = OandaClient()
        self.notifier = PushoverNotifier()

        # Database for storing reports and audit trail
        if db is None:
            from emy.core.database import EMyDatabase
            self.db = EMyDatabase()
            self.db.initialize_schema()
        else:
            self.db = db

        # Initialize AlertManager for centralized throttling
        self.alert_manager = AlertManager(notifier=self.notifier, db=self.db)

    def run(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute trading hours monitoring and enforcement.

        Returns:
            (True, {"status": "monitoring/enforcement", ...})
        """
        try:
            if self.check_disabled():
                self.logger.warning("TradingHoursMonitorAgent disabled")
                return (False, {'reason': 'disabled'})

            # Get current time in UTC
            now_utc = datetime.now(pytz.UTC)

            # Check if this is an enforcement window (21:30 Fri or 23:00 Mon-Thu)
            is_enforcement = self._is_enforcement_window(now_utc)

            if is_enforcement:
                return self._enforce_compliance(now_utc)
            else:
                return self._monitor_compliance(now_utc)

        except Exception as e:
            error_msg = f"TradingHoursMonitorAgent error: {e}"
            self.logger.error(error_msg)
            return (False, {"error": error_msg})

    def _is_enforcement_window(self, now_utc: datetime) -> bool:
        """Check if current time is an enforcement window."""
        weekday = now_utc.weekday()  # 0=Mon, 4=Fri
        hour = now_utc.hour
        minute = now_utc.minute

        # Friday 21:30 UTC
        if weekday == 4 and hour == 21 and minute >= 30:
            return True

        # Mon-Thu 23:00 UTC
        if weekday < 4 and hour == 23:
            return True

        return False

    def _enforce_compliance(self, now_utc: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Enforce trading hours compliance by closing non-compliant trades."""
        # TODO: Implement in next task
        return (True, {"status": "enforcement", "trades_closed": []})

    def _monitor_compliance(self, now_utc: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Monitor for trades that should have been closed."""
        # TODO: Implement in next task
        return (True, {"status": "monitoring", "violations_found": 0})
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py -v
```

Expected: PASS (2/2 tests)

**Step 5: Commit**

```bash
git add emy/agents/trading_hours_monitor_agent.py emy/tests/test_trading_hours_monitor_agent.py
git commit -m "feat: Create TradingHoursMonitorAgent base class

- Inherits from EMySubAgent following Emy agent pattern
- Integrates with OandaClient for trade closure via OANDA API
- Integrates with AlertManager for centralized Pushover alerts
- Detects enforcement windows: Friday 21:30, Mon-Thu 23:00 UTC
- Skeleton run() method dispatches to enforce or monitor modes
- Uses UTC timezone throughout for consistency with trading rules

Next: Implement _enforce_compliance() and _monitor_compliance()"
```

---

## Task 4: Implement TradingHoursMonitorAgent._get_open_trades()

**Files:**
- Modify: `emy/agents/trading_hours_monitor_agent.py` — add method
- Modify: `emy/tests/test_trading_hours_monitor_agent.py` — add test

**Step 1: Write failing test**

```python
def test_get_open_trades_returns_list():
    """Test _get_open_trades returns list of trades."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    # Mock OANDA response
    mock_trades = [
        {
            'id': '123456',
            'instrument': 'EUR_USD',
            'initialUnits': 100,
            'currentUnits': 100,
            'unrealizedPL': '45.00',
            'openTime': '2026-03-16T20:00:00Z'
        },
        {
            'id': '123457',
            'instrument': 'USD_JPY',
            'initialUnits': -50,
            'currentUnits': -50,
            'unrealizedPL': '-12.00',
            'openTime': '2026-03-16T20:30:00Z'
        }
    ]

    agent.oanda_client.list_open_trades = MagicMock(return_value=mock_trades)

    trades = agent._get_open_trades()

    assert len(trades) == 2
    assert trades[0]['id'] == '123456'
    assert trades[1]['id'] == '123457'

def test_get_open_trades_handles_api_error():
    """Test _get_open_trades handles API errors gracefully."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)
    agent.oanda_client.list_open_trades = MagicMock(side_effect=Exception('API Error'))

    trades = agent._get_open_trades()

    assert trades == []
```

**Step 2: Run test to verify it fails**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py::test_get_open_trades_returns_list -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_get_open_trades_handles_api_error -v
```

Expected: FAIL — method doesn't exist

**Step 3: Write minimal implementation**

Add to `emy/agents/trading_hours_monitor_agent.py`:

```python
def _get_open_trades(self) -> list:
    """
    Fetch all open trades from OANDA.

    Returns:
        List of open trade dicts, or empty list if error
    """
    try:
        trades = self.oanda_client.list_open_trades()
        return trades or []
    except Exception as e:
        self.logger.error(f"Error fetching open trades: {e}")
        return []
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py::test_get_open_trades_returns_list -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_get_open_trades_handles_api_error -v
```

Expected: PASS (2/2 tests)

**Step 5: Commit**

```bash
git add emy/agents/trading_hours_monitor_agent.py emy/tests/test_trading_hours_monitor_agent.py
git commit -m "feat: Add TradingHoursMonitorAgent._get_open_trades() method

- Fetches list of all open trades from OANDA API
- Returns empty list if API error (graceful degradation)
- Used by both enforcement and monitoring modes"
```

---

## Task 5: Implement TradingHoursMonitorAgent._check_compliance_status()

**Files:**
- Modify: `emy/agents/trading_hours_monitor_agent.py` — add method
- Modify: `emy/tests/test_trading_hours_monitor_agent.py` — add test

**Step 1: Write failing test**

```python
def test_check_compliance_status_compliant():
    """Test checking compliance for a compliant trade."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    # Monday 10:00 UTC - within trading hours
    now_utc = datetime(2026, 3, 16, 10, 0, 0, tzinfo=pytz.UTC)  # Monday

    trade = {
        'id': '123456',
        'instrument': 'EUR_USD',
        'currentUnits': 100,
        'unrealizedPL': '100.00'  # Runner (25+ pips)
    }

    status = agent._check_compliance_status(trade, now_utc)

    assert status == 'COMPLIANT'

def test_check_compliance_status_noncompliant_weekend():
    """Test checking compliance for trade on weekend."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    # Saturday
    now_utc = datetime(2026, 3, 21, 15, 0, 0, tzinfo=pytz.UTC)  # Saturday

    trade = {
        'id': '123456',
        'instrument': 'EUR_USD',
        'currentUnits': 100,
        'unrealizedPL': '50.00'
    }

    status, reason = agent._check_compliance_status(trade, now_utc)

    assert status == 'NON_COMPLIANT'
    assert reason == 'SATURDAY_MARKET_CLOSED'

def test_check_compliance_status_noncompliant_friday_after_close():
    """Test checking compliance for trade on Friday after 21:30."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    # Friday 22:00 UTC
    now_utc = datetime(2026, 3, 20, 22, 0, 0, tzinfo=pytz.UTC)  # Friday

    trade = {
        'id': '123456',
        'instrument': 'EUR_USD',
        'currentUnits': 100,
        'unrealizedPL': '50.00'
    }

    status, reason = agent._check_compliance_status(trade, now_utc)

    assert status == 'NON_COMPLIANT'
    assert reason == 'FRIDAY_HARD_CLOSE'
```

**Step 2: Run test to verify it fails**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py::test_check_compliance_status_compliant -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_check_compliance_status_noncompliant_weekend -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_check_compliance_status_noncompliant_friday_after_close -v
```

Expected: FAIL — method doesn't exist

**Step 3: Write minimal implementation**

Add to `emy/agents/trading_hours_monitor_agent.py`:

```python
def _check_compliance_status(self, trade: Dict, now_utc: datetime) -> Tuple[str, str]:
    """
    Check if a trade is compliant with trading hours rules.

    Returns:
        ('COMPLIANT', '') or ('NON_COMPLIANT', reason)
    """
    weekday = now_utc.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    hour = now_utc.hour
    minute = now_utc.minute

    # Rule 1: Weekend (Saturday/Sunday)
    if weekday == 5:
        return ('NON_COMPLIANT', 'SATURDAY_MARKET_CLOSED')
    if weekday == 6:
        return ('NON_COMPLIANT', 'SUNDAY_CLOSED')

    # Rule 2: Friday after 21:30
    if weekday == 4 and (hour > 21 or (hour == 21 and minute > 30)):
        return ('NON_COMPLIANT', 'FRIDAY_HARD_CLOSE')

    # Rule 3: Mon-Thu after 23:00
    if weekday < 4 and hour >= 23:
        return ('NON_COMPLIANT', 'RUNNER_DEADLINE_23:00')

    # Rule 4: Mon-Thu 21:30-23:00 (check if runner)
    if weekday < 4 and hour == 21 and minute >= 30:
        # Runner if unrealized P&L >= 25 pips (approx $100+ for EUR/USD)
        unrealized_pl = float(trade.get('unrealizedPL', 0))
        if unrealized_pl < 100:  # Assume ~$4/pip, so 25 pips = ~$100
            return ('NON_COMPLIANT', 'DAILY_CLOSE_21:30')
        # Runner: allowed to hold
        return ('COMPLIANT', '')

    # Rule 5: Before 01:00 on a weekday
    if weekday < 5 and hour < 1:
        return ('NON_COMPLIANT', 'OUTSIDE_TRADING_HOURS')

    # Otherwise: COMPLIANT
    return ('COMPLIANT', '')
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py::test_check_compliance_status_compliant -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_check_compliance_status_noncompliant_weekend -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_check_compliance_status_noncompliant_friday_after_close -v
```

Expected: PASS (3/3 tests)

**Step 5: Commit**

```bash
git add emy/agents/trading_hours_monitor_agent.py emy/tests/test_trading_hours_monitor_agent.py
git commit -m "feat: Add TradingHoursMonitorAgent._check_compliance_status()

Implements trading hours compliance rules:
- Weekend (Sat/Sun): all trades non-compliant
- Friday after 21:30: all trades must close (no runner exception)
- Mon-Thu after 23:00: all trades must close (runner deadline)
- Mon-Thu 21:30-23:00: non-runners close, runners hold
- Before 01:00 Mon: outside trading hours

Returns (status, reason) tuple for detailed reporting"
```

---

## Task 6: Implement TradingHoursMonitorAgent._enforce_compliance()

**Files:**
- Modify: `emy/agents/trading_hours_monitor_agent.py` — implement method
- Modify: `emy/tests/test_trading_hours_monitor_agent.py` — add test

**Step 1: Write failing test**

```python
def test_enforce_compliance_closes_noncompliant_trades():
    """Test enforcement closes non-compliant trades."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    # Friday 21:30 UTC
    now_utc = datetime(2026, 3, 20, 21, 30, 0, tzinfo=pytz.UTC)

    # Mock two trades
    mock_trades = [
        {
            'id': '123456',
            'instrument': 'EUR_USD',
            'currentUnits': 100,
            'unrealizedPL': '45.00'
        },
        {
            'id': '123457',
            'instrument': 'USD_JPY',
            'currentUnits': -50,
            'unrealizedPL': '-12.00'
        }
    ]

    agent.oanda_client.list_open_trades = MagicMock(return_value=mock_trades)
    agent.oanda_client.close_trade = MagicMock(return_value={'success': True, 'realized_pl': 45.00})

    success, result = agent._enforce_compliance(now_utc)

    assert success == True
    assert result['status'] == 'enforcement'
    assert len(result['trades_closed']) == 2
    assert agent.oanda_client.close_trade.call_count == 2

def test_enforce_compliance_stores_audit_trail():
    """Test enforcement stores closure audit trail."""
    db = EMyDatabase(':memory:')
    db.initialize_schema()

    agent = TradingHoursMonitorAgent(db=db)

    now_utc = datetime(2026, 3, 20, 21, 30, 0, tzinfo=pytz.UTC)

    mock_trades = [
        {
            'id': '123456',
            'instrument': 'EUR_USD',
            'currentUnits': 100,
            'unrealizedPL': '45.00'
        }
    ]

    agent.oanda_client.list_open_trades = MagicMock(return_value=mock_trades)
    agent.oanda_client.close_trade = MagicMock(return_value={'success': True, 'realized_pl': 45.00})

    agent._enforce_compliance(now_utc)

    # Check audit trail was created
    audit = db.query_one(
        "SELECT trade_id, realized_pnl FROM enforcement_audit WHERE trade_id='123456'"
    )
    assert audit is not None
    assert audit[0] == '123456'
    assert float(audit[1]) == 45.00
```

**Step 2: Run test to verify it fails**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py::test_enforce_compliance_closes_noncompliant_trades -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_enforce_compliance_stores_audit_trail -v
```

Expected: FAIL — method not fully implemented

**Step 3: Write minimal implementation**

Replace the `_enforce_compliance` stub in `emy/agents/trading_hours_monitor_agent.py`:

```python
def _enforce_compliance(self, now_utc: datetime) -> Tuple[bool, Dict[str, Any]]:
    """Enforce trading hours compliance by closing non-compliant trades."""
    try:
        # Get all open trades
        open_trades = self._get_open_trades()

        if not open_trades:
            return (True, {
                'status': 'enforcement',
                'trades_closed': [],
                'message': 'No open trades to enforce'
            })

        # Identify and close non-compliant trades
        closed_trades = []
        total_pnl = 0.0

        for trade in open_trades:
            status, reason = self._check_compliance_status(trade, now_utc)

            if status == 'NON_COMPLIANT':
                # Close the trade
                close_result = self.oanda_client.close_trade(
                    trade_id=trade['id'],
                    reason=reason
                )

                if close_result.get('success'):
                    realized_pl = close_result.get('realized_pl', 0.0)
                    total_pnl += realized_pl

                    # Store in audit trail
                    self.db.execute(
                        """INSERT INTO enforcement_audit
                           (timestamp, trade_id, pair, direction, realized_pnl, closure_reason)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            now_utc.isoformat(),
                            trade['id'],
                            trade['instrument'],
                            'LONG' if int(trade['currentUnits']) > 0 else 'SHORT',
                            realized_pl,
                            reason
                        )
                    )

                    closed_trades.append({
                        'trade_id': trade['id'],
                        'pair': trade['instrument'],
                        'realized_pl': realized_pl,
                        'reason': reason
                    })

        # Generate Claude analysis
        if closed_trades:
            analysis = self._analyze_enforcement_with_claude(closed_trades, total_pnl)

            # Store report
            self.db.execute(
                """INSERT INTO monitoring_reports
                   (report_type, timestamp, enforcement_action, trades_affected, total_pnl, analysis, critical)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    'trading_hours_enforcement',
                    now_utc.isoformat(),
                    1,
                    str(closed_trades),
                    total_pnl,
                    analysis,
                    1  # Always critical when trades are closed
                )
            )

            # Send alert
            alert_message = f"Trading Hours Enforcement {now_utc.strftime('%H:%M UTC')}: Closed {len(closed_trades)} trades. Total P&L: ${total_pnl:.2f}"
            self.alert_manager.send(
                'trading_hours_enforcement',
                title="Trading Hours Enforcement",
                message=alert_message,
                priority=2  # Emergency
            )

        return (True, {
            'status': 'enforcement',
            'trades_closed': closed_trades,
            'total_pnl': total_pnl,
            'timestamp': now_utc.isoformat()
        })

    except Exception as e:
        self.logger.error(f"Enforcement error: {e}")
        return (False, {'error': str(e)})

def _analyze_enforcement_with_claude(self, closed_trades: list, total_pnl: float) -> str:
    """Analyze enforcement action with Claude (Haiku)."""
    try:
        trade_summary = "\n".join([
            f"- {t['pair']}: {t['reason']} (PL: ${t['realized_pl']:.2f})"
            for t in closed_trades
        ])

        prompt = f"""Analyze these trading hours enforcement actions. Summarize concisely:

Trades Closed ({len(closed_trades)}):
{trade_summary}

Total P&L Impact: ${total_pnl:.2f}

Format as 1-2 sentences. Is this normal enforcement or unusual pattern?"""

        analysis = self._call_claude(prompt, max_tokens=200)
        return analysis

    except Exception as e:
        self.logger.error(f"Claude analysis error: {e}")
        return f"Closed {len(closed_trades)} trades at {closed_trades[0]['reason']} window"
```

**Step 4: Run test to verify it passes**

```bash
pytest emy/tests/test_trading_hours_monitor_agent.py::test_enforce_compliance_closes_noncompliant_trades -v
pytest emy/tests/test_trading_hours_monitor_agent.py::test_enforce_compliance_stores_audit_trail -v
```

Expected: PASS (2/2 tests)

**Step 5: Commit**

```bash
git add emy/agents/trading_hours_monitor_agent.py emy/tests/test_trading_hours_monitor_agent.py
git commit -m "feat: Implement TradingHoursMonitorAgent._enforce_compliance()

Autonomous enforcement of trading hours rules:
- Fetches open trades from OANDA
- Checks compliance status for each trade
- Closes non-compliant trades via OANDA API
- Records closure in enforcement_audit table with details
- Analyzes enforcement action with Claude (Haiku)
- Stores report in monitoring_reports table
- Sends critical Pushover alert with P&L summary

Full audit trail maintained for compliance review"
```

---

## Task 7: Implement TradingHoursMonitorAgent._monitor_compliance()

[Continue with similar pattern for monitoring mode...]

---

## Task 8-10: Implement LogAnalysisAgent and ProfitabilityAgent

[Similar structure to Tasks 3-7, following TDD pattern]

---

## Task 11: Create Celery Task Definitions

**Files:**
- Create: `emy/tasks/monitoring_tasks.py`

**Step 1: Write failing test**

[Test that Celery tasks are created and callable]

**Step 2-5: [Similar TDD flow]**

---

## Task 12: Integration Tests — Full Enforcement Cycle

**Files:**
- Create: `emy/tests/test_monitoring_integration.py`

**Step 1: Write failing test**

[E2E test: detect non-compliant trade → close → store audit → send alert]

**Step 2-5: [Run and fix]**

---

## Execution Options

Plan complete and saved to `docs/plans/2026-03-16-emy-trading-monitoring-agents-plan.md`.

Two execution approaches:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, code review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans skill for batch execution with checkpoints

**Which approach would you prefer?**