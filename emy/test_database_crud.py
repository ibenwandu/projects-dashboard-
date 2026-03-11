"""Test OANDA CRUD methods."""
import sys
from pathlib import Path

# Add parent directory to path so emy module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    """Test getting daily P&L for profit scenario."""
    db = get_test_db()
    db.initialize_schema()

    # Log a closed trade with profit (positive P&L)
    with db.get_connection() as conn:
        conn.execute("""
        INSERT INTO oanda_trades
        (symbol, units, direction, status, pnl_usd, closed_at)
        VALUES ('EUR_USD', 5000, 'BUY', 'CLOSED', 50.0, CURRENT_TIMESTAMP)
        """)
        conn.commit()

    pnl = db.get_daily_pnl()
    assert pnl == 50.0, f"Expected 50.0 (profit), got {pnl}"
    print("[OK] get_daily_pnl works for profit scenario")


def test_get_daily_pnl_loss():
    """Test P&L calculation correctly returns negative value for losses."""
    db = get_test_db()
    db.initialize_schema()

    # Log a closed trade with loss (negative P&L)
    with db.get_connection() as conn:
        conn.execute("""
        INSERT INTO oanda_trades
        (symbol, units, direction, status, pnl_usd, closed_at)
        VALUES ('EUR_USD', 5000, 'BUY', 'CLOSED', -50.0, CURRENT_TIMESTAMP)
        """)
        conn.commit()

    pnl = db.get_daily_pnl()
    assert pnl == -50.0, f"Expected -50.0 (loss), got {pnl}"
    print("[OK] get_daily_pnl correctly returns negative P&L for losses")


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
    """Test updating daily limits for open positions."""
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
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT * FROM oanda_limits WHERE date = ?", (today,))
        limits = cursor.fetchone()
        assert limits is not None, "Daily limits record not created"
        assert limits[6] == 1, "concurrent_open_count should be 1"  # Column 6 is concurrent_open_count
    print("[OK] update_daily_limits works for open positions")


def test_update_daily_limits_loss_calculation():
    """Test that daily_loss_usd is positive when there's a loss."""
    db = get_test_db()
    db.initialize_schema()

    # Log a closed trade with loss
    with db.get_connection() as conn:
        conn.execute("""
        INSERT INTO oanda_trades
        (symbol, units, direction, status, pnl_usd, closed_at)
        VALUES ('EUR_USD', 5000, 'BUY', 'CLOSED', -100.0, CURRENT_TIMESTAMP)
        """)
        conn.commit()

    # Update limits
    db.update_daily_limits()

    # Verify daily_loss_usd is positive 100 (not negative)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT daily_loss_usd FROM oanda_limits WHERE date = ?", (today,))
        row = cursor.fetchone()
        assert row is not None, "Daily limits record not created"
        daily_loss = row[0]
        assert daily_loss == 100.0, f"Expected daily_loss_usd=100.0, got {daily_loss}"
    print("[OK] update_daily_limits correctly converts -$100 P&L to +$100 loss")


def test_update_daily_limits_profit_no_loss():
    """Test that daily_loss_usd is 0 when there's a profit."""
    db = get_test_db()
    db.initialize_schema()

    # Log a closed trade with profit
    with db.get_connection() as conn:
        conn.execute("""
        INSERT INTO oanda_trades
        (symbol, units, direction, status, pnl_usd, closed_at)
        VALUES ('EUR_USD', 5000, 'BUY', 'CLOSED', 50.0, CURRENT_TIMESTAMP)
        """)
        conn.commit()

    # Update limits
    db.update_daily_limits()

    # Verify daily_loss_usd is 0 (no loss when profit)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT daily_loss_usd FROM oanda_limits WHERE date = ?", (today,))
        row = cursor.fetchone()
        assert row is not None, "Daily limits record not created"
        daily_loss = row[0]
        assert daily_loss == 0.0, f"Expected daily_loss_usd=0.0 for profit, got {daily_loss}"
    print("[OK] update_daily_limits correctly sets daily_loss_usd to 0 for profits")


def test_error_handling_duplicate_trade():
    """Test error handling for duplicate trade_id."""
    db = get_test_db()
    db.initialize_schema()

    # Log first trade
    db.log_oanda_trade('test-dup', '101-002-38030127-001', 'EUR_USD', 5000, 'BUY', 1.0850, 1.0820, 1.0900)

    # Try to log same trade_id (should raise ValueError)
    try:
        db.log_oanda_trade('test-dup', '101-002-38030127-001', 'EUR_USD', 5000, 'BUY', 1.0850, 1.0820, 1.0900)
        assert False, "Should have raised ValueError for duplicate trade_id"
    except ValueError as e:
        assert "already logged" in str(e), f"Error message should mention 'already logged', got: {e}"
        print("[OK] Error handling for duplicate trades works")


if __name__ == '__main__':
    test_log_oanda_trade()
    test_log_trade_rejection()
    test_get_daily_pnl()
    test_get_daily_pnl_loss()
    test_get_open_positions_count()
    test_update_daily_limits()
    test_update_daily_limits_loss_calculation()
    test_update_daily_limits_profit_no_loss()
    test_error_handling_duplicate_trade()
    print("\n[PASS] All CRUD tests passed")
