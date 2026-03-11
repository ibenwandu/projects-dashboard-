"""Test OANDA CRUD methods."""
from emy.core.database import EMyDatabase
from datetime import datetime
import os
import tempfile


def get_test_db():
    """Create a fresh database for each test."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_emy.db")
    return EMyDatabase(db_path)


def test_log_oanda_trade():
    """Test logging a trade."""
    db = get_test_db()
    db.initialize_schema()

    # Log a trade
    db.log_oanda_trade(
        trade_id='test-123',
        account_id='101-002-38030127-001',
        symbol='EUR_USD',
        units=5000,
        direction='BUY',
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0900
    )

    # Verify it's in database
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT * FROM oanda_trades WHERE trade_id = 'test-123'")
        trade = cursor.fetchone()
        assert trade is not None, "Trade not found in database"
        assert trade[3] == 'EUR_USD', "Symbol mismatch"
        assert trade[4] == 5000, "Units mismatch"
    print("[OK] log_oanda_trade works")


def test_log_trade_rejection():
    """Test logging a rejected trade."""
    db = get_test_db()
    db.initialize_schema()

    db.log_trade_rejection('GBP_USD', 15000, 'Position size exceeds limit')

    with db.get_connection() as conn:
        cursor = conn.execute("SELECT * FROM oanda_trades WHERE status = 'REJECTED'")
        rejection = cursor.fetchone()
        assert rejection is not None, "Rejection not logged"
        assert rejection[9] == 'REJECTED', "Status not set to REJECTED"
    print("[OK] log_trade_rejection works")


def test_get_daily_pnl():
    """Test getting daily P&L."""
    db = get_test_db()
    db.initialize_schema()

    # Log a closed trade with P&L
    with db.get_connection() as conn:
        conn.execute("""
        INSERT INTO oanda_trades
        (symbol, units, direction, status, pnl_usd, closed_at)
        VALUES ('EUR_USD', 5000, 'BUY', 'CLOSED', 50.0, CURRENT_TIMESTAMP)
        """)
        conn.commit()

    pnl = db.get_daily_pnl()
    assert pnl == 50.0, f"Expected 50.0, got {pnl}"
    print("[OK] get_daily_pnl works")


def test_get_open_positions_count():
    """Test counting open positions."""
    db = get_test_db()
    db.initialize_schema()

    # Log 3 open trades
    for i in range(3):
        db.log_oanda_trade(
            trade_id=f'trade-{i}',
            account_id='101-002-38030127-001',
            symbol='EUR_USD',
            units=1000,
            direction='BUY',
            entry_price=1.0850,
            stop_loss=1.0820,
            take_profit=1.0900,
            status='OPEN'
        )

    count = db.get_open_positions_count()
    assert count == 3, f"Expected 3 open trades, got {count}"
    print("[OK] get_open_positions_count works")


def test_update_daily_limits():
    """Test updating daily limits."""
    db = get_test_db()
    db.initialize_schema()

    # Log an open trade
    db.log_oanda_trade(
        trade_id='limit-test',
        account_id='101-002-38030127-001',
        symbol='EUR_USD',
        units=5000,
        direction='BUY',
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0900,
        status='OPEN'
    )

    # Update limits
    db.update_daily_limits()

    # Verify limits record was created
    today = datetime.now().strftime('%Y-%m-%d')
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT * FROM oanda_limits WHERE date = ?", (today,))
        limits = cursor.fetchone()
        assert limits is not None, "Daily limits record not created"
        assert limits[6] == 1, "concurrent_open_count should be 1"  # Column 6 is concurrent_open_count
    print("[OK] update_daily_limits works")


if __name__ == '__main__':
    test_log_oanda_trade()
    test_log_trade_rejection()
    test_get_daily_pnl()
    test_get_open_positions_count()
    test_update_daily_limits()
    print("\n[PASS] All CRUD tests passed")
