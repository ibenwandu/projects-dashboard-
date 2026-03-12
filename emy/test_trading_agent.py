"""Test TradingAgent risk validation."""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path so emy module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from emy.agents.trading_agent import TradingAgent
from emy.core.database import EMyDatabase


def test_validate_trade_position_size():
    """Test position size validation rejects oversized trades."""
    db = EMyDatabase()
    db.initialize_schema()
    agent = TradingAgent(db)

    with patch.dict(os.environ, {'OANDA_MAX_POSITION_SIZE': '10000'}):
        is_valid, reason = agent._validate_trade('EUR_USD', 15000, 'BUY')
        assert not is_valid, "Should reject trade exceeding position limit"
        assert 'exceeds limit' in reason, f"Reason should mention limit: {reason}"
    print("[OK] Position size validation")


def test_validate_trade_valid():
    """Test valid trade passes all validation checks."""
    db = EMyDatabase()
    db.initialize_schema()
    agent = TradingAgent(db)

    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100',
        'OANDA_MAX_CONCURRENT_POSITIONS': '5'
    }):
        # Mock the database methods to return good values
        with patch.object(db, 'get_daily_pnl', return_value=0.0):
            with patch.object(db, 'get_open_positions_count', return_value=0):
                is_valid, reason = agent._validate_trade('EUR_USD', 5000, 'BUY')
                assert is_valid, f"Valid trade should pass validation: {reason}"
                assert reason == 'OK', f"Reason should be OK: {reason}"
    print("[OK] Valid trade passes validation")


def test_validate_trade_daily_loss_exceeded():
    """Test daily loss limit validation."""
    db = EMyDatabase()
    db.initialize_schema()
    agent = TradingAgent(db)

    # Mock get_daily_pnl to simulate loss exceeding limit
    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100.0',
        'OANDA_MAX_CONCURRENT_POSITIONS': '5'
    }):
        with patch.object(db, 'get_daily_pnl', return_value=-150.0):
            is_valid, reason = agent._validate_trade('EUR_USD', 5000, 'BUY')
            assert not is_valid, "Should reject when daily loss exceeds limit"
            assert 'Daily loss' in reason, f"Reason should mention daily loss: {reason}"
    print("[OK] Daily loss validation")


def test_validate_trade_max_concurrent():
    """Test concurrent positions limit validation."""
    db = EMyDatabase()
    db.initialize_schema()
    agent = TradingAgent(db)

    with patch.dict(os.environ, {
        'OANDA_MAX_POSITION_SIZE': '10000',
        'OANDA_MAX_DAILY_LOSS_USD': '100',
        'OANDA_MAX_CONCURRENT_POSITIONS': '2'
    }):
        with patch.object(db, 'get_open_positions_count', return_value=2):
            is_valid, reason = agent._validate_trade('EUR_USD', 5000, 'BUY')
            assert not is_valid, "Should reject when at concurrent position limit"
            assert 'Open positions' in reason, f"Reason should mention positions: {reason}"
    print("[OK] Concurrent positions validation")


def test_execute_trade_rejected():
    """Test that rejected trades return None."""
    db = EMyDatabase()
    db.initialize_schema()
    agent = TradingAgent(db)

    with patch.dict(os.environ, {'OANDA_MAX_POSITION_SIZE': '10000'}):
        with patch.object(agent, '_validate_trade', return_value=(False, "Position too large")):
            result = agent._execute_trade('EUR_USD', 15000, 'BUY', 1.0800, 1.0900)
            assert result is None, "Should return None for rejected trade"
    print("[OK] Rejected trade returns None")


def test_execute_trade_success():
    """Test successful trade execution and logging."""
    db = EMyDatabase()
    db.initialize_schema()
    agent = TradingAgent(db)

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
                    assert result['trade_id'] == 'trade-12345'
                    mock_log.assert_called_once()
    print("[OK] Successful trade execution")


if __name__ == '__main__':
    test_validate_trade_position_size()
    test_validate_trade_valid()
    test_validate_trade_daily_loss_exceeded()
    test_validate_trade_max_concurrent()
    test_execute_trade_rejected()
    test_execute_trade_success()
    print("\n[PASS] All TradingAgent validation tests passed")
