import pytest
from emy.core.database import EMyDatabase


def test_monitoring_reports_table_exists():
    """Test that monitoring_reports table is created."""
    db = EMyDatabase()
    db.initialize_schema()
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
