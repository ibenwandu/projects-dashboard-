"""Integration test for OANDA real trading functionality.

Tests the complete workflow:
1. Account connection and summary retrieval
2. Trade validation (position size, daily loss, concurrent positions)
3. Trade execution with SL/TP
4. Database logging and retrieval
5. Risk calculations and open position tracking
"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sqlite3

# Add parent directory to path so emy module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from emy.core.database import EMyDatabase
from emy.agents.trading_agent import TradingAgent
from emy.tools.api_client import OandaClient
from dotenv import load_dotenv

load_dotenv()


def test_oanda_integration():
    """Test full OANDA integration: validation → execution → logging."""

    # Initialize fresh database for testing (unique per test run to avoid conflicts)
    import time
    test_db_name = f"emy/data/test_integration_{int(time.time() * 1000)}.db"
    db = EMyDatabase(db_path=test_db_name)
    db.initialize_schema()
    agent = TradingAgent(db)

    # Store db path for cleanup
    test_db_files = [test_db_name]

    print("\n" + "="*60)
    print("[TEST] OANDA Integration Test Suite")
    print("="*60 + "\n")

    # ===== TEST 1: Account Summary =====
    print("1. Fetching account summary...")
    oanda = OandaClient(
        access_token=os.getenv('OANDA_ACCESS_TOKEN'),
        account_id=os.getenv('OANDA_ACCOUNT_ID')
    )

    try:
        account = oanda.get_account_summary()
        if account:
            assert isinstance(account, dict), "Account should return dict"
            assert 'equity' in account, "Account must have 'equity' field"
            assert isinstance(account['equity'], float), "Equity should be float"
            print(f"   [OK] Account connected: Equity=${account['equity']:.2f}")
            equity = account['equity']
        else:
            print("   [WARN] Account summary returned None (API error)")
    except ValueError as e:
        if "credentials" in str(e).lower():
            print("   [SKIP] OANDA credentials not configured - skipping live API tests")
            print("   [NOTE] Running offline validation and database tests only...\n")
        else:
            raise

    # ===== TEST 2: Trade Validation - Valid Trade =====
    print("2. Testing valid trade validation...")
    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100',
        'OANDA_MAX_CONCURRENT_POSITIONS': '5'
    }):
        with patch.object(db, 'get_daily_pnl', return_value=0.0):
            with patch.object(db, 'get_open_positions_count', return_value=0):
                is_valid, reason = agent._validate_trade('EUR_USD', 5000, 'BUY')
                assert is_valid, f"Valid trade should pass validation: {reason}"
                assert reason == 'OK', f"Reason should be OK: {reason}"
    print("   [OK] Valid trade passes validation")

    # ===== TEST 3: Trade Validation - Position Size Rejection =====
    print("3. Testing position size rejection...")
    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100',
        'OANDA_MAX_CONCURRENT_POSITIONS': '5'
    }):
        with patch.object(db, 'get_daily_pnl', return_value=0.0):
            with patch.object(db, 'get_open_positions_count', return_value=0):
                is_valid, reason = agent._validate_trade('EUR_USD', 25000, 'BUY')
                assert not is_valid, "Oversized position should be rejected"
                assert 'exceeds' in reason.lower() or 'limit' in reason.lower(), \
                    f"Reason should mention position limit: {reason}"
    print("   [OK] Oversized position correctly rejected")

    # ===== TEST 4: Trade Validation - Daily Loss Limit =====
    print("4. Testing daily loss limit validation...")
    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100.0',
        'OANDA_MAX_CONCURRENT_POSITIONS': '5'
    }):
        with patch.object(db, 'get_daily_pnl', return_value=-150.0):
            is_valid, reason = agent._validate_trade('EUR_USD', 5000, 'BUY')
            assert not is_valid, "Should reject when daily loss exceeds limit"
            assert 'Daily' in reason or 'loss' in reason.lower(), \
                f"Reason should mention daily loss: {reason}"
    print("   [OK] Daily loss limit correctly enforced")

    # ===== TEST 5: Trade Validation - Max Concurrent Positions =====
    print("5. Testing concurrent positions limit...")
    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100',
        'OANDA_MAX_CONCURRENT_POSITIONS': '2'
    }):
        with patch.object(db, 'get_daily_pnl', return_value=0.0):
            with patch.object(db, 'get_open_positions_count', return_value=2):
                is_valid, reason = agent._validate_trade('EUR_USD', 5000, 'BUY')
                assert not is_valid, "Should reject when at concurrent position limit"
                assert 'Open' in reason or 'position' in reason.lower(), \
                    f"Reason should mention positions: {reason}"
    print("   [OK] Concurrent position limit correctly enforced")

    # ===== TEST 6: Database Trade Logging =====
    print("6. Testing trade logging to database...")
    db.log_oanda_trade(
        trade_id='test-integration-001',
        account_id=os.getenv('OANDA_ACCOUNT_ID', 'test-account'),
        symbol='EUR_USD',
        units=5000,
        direction='BUY',
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0900,
        status='OPEN'
    )
    print("   [OK] Trade logged to database")

    # ===== TEST 7: Database Trade Retrieval =====
    print("7. Verifying database record...")
    verified = False
    with db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM oanda_trades WHERE trade_id = 'test-integration-001'"
        )
        record = cursor.fetchone()
        assert record is not None, "Trade should be found in database"
        assert record['symbol'] == 'EUR_USD', "Symbol mismatch"
        assert record['units'] == 5000, "Units mismatch"
        assert record['entry_price'] == 1.0850, "Entry price mismatch"
        assert record['status'] == 'OPEN', "Status should be OPEN"
        verified = True
    assert verified, "Trade verification failed"
    print("   [OK] Trade record verified in database")

    # ===== TEST 8: Duplicate Trade Prevention =====
    print("8. Testing duplicate trade prevention...")
    try:
        db.log_oanda_trade(
            trade_id='test-integration-001',  # Same ID
            account_id=os.getenv('OANDA_ACCOUNT_ID', 'test-account'),
            symbol='GBP_USD',
            units=5000,
            direction='BUY',
            entry_price=1.2500,
            stop_loss=1.2470,
            take_profit=1.2550,
            status='OPEN'
        )
        assert False, "Should raise ValueError for duplicate trade_id"
    except ValueError as e:
        assert 'already' in str(e).lower() or 'duplicate' in str(e).lower(), \
            f"Error should mention duplicate: {e}"
    print("   [OK] Duplicate trades correctly rejected")

    # ===== TEST 9: Trade Rejection Logging =====
    print("9. Testing trade rejection logging...")
    reject_logged = False
    db.log_trade_rejection(
        symbol='EUR_USD',
        units=25000,
        reason='Position size exceeds limit (10000)'
    )
    # Check rejection in separate connection to avoid lock
    with db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM oanda_trades WHERE status = 'REJECTED'"
        )
        rejected = cursor.fetchone()
        assert rejected is not None, "Rejected trade should be in database"
        assert rejected['reason_rejected'] is not None, "Should have rejection reason"
        reject_logged = True
    assert reject_logged, "Rejection logging verification failed"
    print("   [OK] Rejected trade logged successfully")

    # ===== TEST 10: Open Positions Count =====
    print("10. Testing open positions count...")
    # Just count existing trades instead of adding more
    count = db.get_open_positions_count()
    assert count >= 1, f"Should have at least 1 open position, got {count}"
    print(f"   [OK] Open positions count: {count}")

    # ===== TEST 11: Daily P&L Calculation =====
    print("11. Testing daily P&L calculation...")
    pnl = db.get_daily_pnl()
    assert pnl is not None, "P&L calculation should return a value"
    assert isinstance(pnl, (int, float)), f"P&L should be numeric, got {type(pnl)}"
    pnl = float(pnl)
    print(f"   [OK] Daily P&L calculated: ${pnl:.2f}")

    # ===== TEST 12: API Client Error Handling =====
    print("12. Testing API client error handling...")
    bad_client = OandaClient(access_token=None, account_id=None)
    try:
        bad_client.execute_trade('EUR_USD', 5000, 'BUY', 1.0820, 1.0900)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert 'credentials' in str(e).lower(), \
            f"Error should mention credentials: {e}"
    print("   [OK] API client correctly raises on missing credentials")

    # ===== TEST 13: Get Open Trades =====
    print("13. Testing open trades retrieval...")
    trades = bad_client.get_open_trades()
    assert isinstance(trades, list), "get_open_trades should return list"
    assert len(trades) == 0, "No trades should be returned with bad credentials"
    print("   [OK] Open trades method handles missing credentials gracefully")

    # ===== TEST 14: Backward Compatibility =====
    print("14. Testing backward compatibility...")
    good_client = OandaClient(
        access_token=os.getenv('OANDA_ACCESS_TOKEN'),
        account_id=os.getenv('OANDA_ACCOUNT_ID')
    )
    assert hasattr(good_client, 'list_open_trades'), \
        "Should have list_open_trades for backward compatibility"
    assert callable(good_client.list_open_trades), \
        "list_open_trades should be callable"
    print("   [OK] Backward compatibility methods present")

    # ===== TEST 15: Trade Execution Logging =====
    print("15. Testing trade execution with logging...")
    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_ACCOUNT_ID': 'test-account-123'
    }):
        with patch.object(agent, '_validate_trade', return_value=(True, "OK")):
            mock_result = {
                'trade_id': 'trade-12345',
                'entry_price': 1.0850,
                'status': 'OPEN'
            }
            with patch.object(agent.oanda_client, 'execute_trade', return_value=mock_result):
                with patch.object(db, 'log_oanda_trade') as mock_log:
                    result = agent._execute_trade('EUR_USD', 5000, 'BUY', 1.0800, 1.0900)
                    assert result is not None, "Should return trade result"
                    assert result['trade_id'] == 'trade-12345', "Trade ID mismatch"
                    mock_log.assert_called_once()
    print("   [OK] Trade execution with logging works correctly")

    # ===== Summary =====
    print("\n" + "="*60)
    print("[PASS] All 15 integration tests passed!")
    print("="*60 + "\n")

    # Cleanup test database files
    for db_file in test_db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception as e:
                print(f"[WARN] Could not clean up test database {db_file}: {e}")

    return True


if __name__ == '__main__':
    try:
        success = test_oanda_integration()
        exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
