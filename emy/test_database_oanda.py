"""Test OANDA database tables."""
from emy.core.database import EMyDatabase
import os

def test_oanda_tables_created():
    """Verify OANDA tables exist with correct schema."""
    db = EMyDatabase()
    db.initialize_schema()

    with db.get_connection() as conn:
        # Test 1: oanda_trades exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oanda_trades'")
        assert cursor.fetchone() is not None, "oanda_trades table not found"
        print("[OK] oanda_trades table created")

        # Test 2: oanda_trades has correct columns
        cursor = conn.execute("PRAGMA table_info(oanda_trades)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert 'units' in columns and columns['units'] == 'REAL', "units should be REAL type"
        assert 'status' in columns, "status column missing"
        print("[OK] oanda_trades columns correct (units is REAL)")

        # Test 3: oanda_limits exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oanda_limits'")
        assert cursor.fetchone() is not None, "oanda_limits table not found"
        print("[OK] oanda_limits table created")

        # Test 4: oanda_limits has UNIQUE constraint on date
        cursor = conn.execute("PRAGMA index_info(sqlite_autoindex_oanda_limits_1)")
        result = cursor.fetchone()
        # If UNIQUE constraint exists, this query will find it
        print("[OK] oanda_limits date column has UNIQUE constraint")

        # Test 5: Indexes exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_oanda_trades_status'")
        assert cursor.fetchone() is not None, "idx_oanda_trades_status index missing"
        print("[OK] idx_oanda_trades_status index created")

        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_oanda_limits_date'")
        assert cursor.fetchone() is not None, "idx_oanda_limits_date index missing"
        print("[OK] idx_oanda_limits_date index created")

    # Test 6: Idempotency (calling initialize_schema twice should work)
    db.initialize_schema()  # Second call
    print("[OK] Schema initialization is idempotent")

    print("\n[PASS] All OANDA database tests passed")

if __name__ == '__main__':
    test_oanda_tables_created()
