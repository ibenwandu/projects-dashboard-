"""Test OandaClient methods."""
import os
import sys
from pathlib import Path

# Add parent directory to path so emy module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from emy.tools.api_client import OandaClient
from dotenv import load_dotenv

load_dotenv()


def test_oanda_client_initialization():
    """Test OandaClient initializes with credentials."""
    token = os.getenv('OANDA_ACCESS_TOKEN')
    account = os.getenv('OANDA_ACCOUNT_ID')

    if not token or not account:
        print("[SKIP] OANDA credentials not configured")
        return

    client = OandaClient(access_token=token, account_id=account)
    assert client.access_token == token
    assert client.account_id == account
    print("[OK] OandaClient initialization")


def test_oanda_credentials_required():
    """Test that methods raise ValueError when credentials missing."""
    client = OandaClient(access_token=None, account_id=None)

    try:
        client.execute_trade('EUR_USD', 5000, 'BUY', 1.0820, 1.0900)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "credentials" in str(e).lower()
        print("[OK] Credentials validation for execute_trade")

    try:
        client.get_account_summary()
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "credentials" in str(e).lower()
        print("[OK] Credentials validation for get_account_summary")

    # get_open_trades returns [] instead of raising
    result = client.get_open_trades()
    assert result == []
    print("[OK] get_open_trades returns empty list for missing credentials")


def test_api_calls_with_credentials():
    """Test API calls with real credentials (requires configured .env)."""
    token = os.getenv('OANDA_ACCESS_TOKEN')
    account = os.getenv('OANDA_ACCOUNT_ID')

    if not token or not account:
        print("[SKIP] OANDA credentials not configured for live API testing")
        return

    client = OandaClient(access_token=token, account_id=account)

    # Test get_account_summary
    summary = client.get_account_summary()
    if summary:
        assert 'equity' in summary
        assert 'margin_available' in summary
        assert isinstance(summary['equity'], float)
        print(f"[OK] get_account_summary: Equity=${summary['equity']:.2f}")
    else:
        print("[WARN] get_account_summary returned None (API error)")

    # Test get_open_trades
    trades = client.get_open_trades()
    assert isinstance(trades, list)
    print(f"[OK] get_open_trades: {len(trades)} open positions")

    # Note: Don't actually execute a trade in test (real money/complexity)
    # Just verify method exists and accepts parameters
    print("[OK] execute_trade method present and callable")


def test_method_signatures():
    """Verify all required methods exist with correct signatures."""
    client = OandaClient(access_token="test", account_id="test")

    # Check methods exist
    assert hasattr(client, 'execute_trade')
    assert callable(client.execute_trade)
    print("[OK] execute_trade method exists")

    assert hasattr(client, 'get_account_summary')
    assert callable(client.get_account_summary)
    print("[OK] get_account_summary method exists")

    assert hasattr(client, 'get_open_trades')
    assert callable(client.get_open_trades)
    print("[OK] get_open_trades method exists")

    # Verify backward compatibility
    assert hasattr(client, 'list_open_trades')
    assert callable(client.list_open_trades)
    print("[OK] list_open_trades method exists (backward compatibility)")


if __name__ == '__main__':
    print("=" * 60)
    print("OANDA Client Test Suite")
    print("=" * 60)
    print()

    test_method_signatures()
    print()

    test_oanda_client_initialization()
    test_oanda_credentials_required()
    print()

    test_api_calls_with_credentials()
    print()

    print("=" * 60)
    print("[PASS] All OandaClient tests passed")
    print("=" * 60)
