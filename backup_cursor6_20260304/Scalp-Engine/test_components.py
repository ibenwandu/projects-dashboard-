"""
Quick diagnostic script to test Scalp-Engine components individually
This helps identify where it's hanging
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 80)
print("Scalp-Engine Component Test")
print("=" * 80)
print()

# Step 1: Test imports
print("Step 1: Testing imports...")
try:
    from src.state_reader import MarketStateReader
    print("  [OK] MarketStateReader imported")
except Exception as e:
    print(f"  [FAIL] MarketStateReader failed: {e}")
    sys.exit(1)

try:
    from src.oanda_client import OandaClient
    print("  [OK] OandaClient imported")
except Exception as e:
    print(f"  [FAIL] OandaClient failed: {e}")
    sys.exit(1)

try:
    from src.signal_generator import SignalGenerator
    print("  [OK] SignalGenerator imported")
except Exception as e:
    print(f"  [FAIL] SignalGenerator failed: {e}")
    sys.exit(1)

try:
    from src.risk_manager import RiskManager
    print("  [OK] RiskManager imported")
except Exception as e:
    print(f"  [FAIL] RiskManager failed: {e}")
    sys.exit(1)

print()

# Step 2: Test environment variables
print("Step 2: Testing environment variables...")
load_dotenv()
oanda_token = os.getenv('OANDA_ACCESS_TOKEN')
oanda_account = os.getenv('OANDA_ACCOUNT_ID')
oanda_env = os.getenv('OANDA_ENV', 'practice')

if oanda_token and oanda_token != 'your_oanda_token_here':
    print(f"  [OK] OANDA_ACCESS_TOKEN: SET (length: {len(oanda_token)})")
else:
    print("  [FAIL] OANDA_ACCESS_TOKEN: NOT SET or placeholder")

if oanda_account:
    print(f"  [OK] OANDA_ACCOUNT_ID: {oanda_account}")
else:
    print("  [FAIL] OANDA_ACCOUNT_ID: NOT SET")

print(f"  [OK] OANDA_ENV: {oanda_env}")
print()

# Step 3: Test config file
print("Step 3: Testing config file...")
try:
    import yaml
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    print("  [OK] config.yaml loaded")
    print(f"  [OK] Trading pairs: {config.get('pairs', {}).get('primary', [])}")
except Exception as e:
    print(f"  [FAIL] config.yaml failed: {e}")
    sys.exit(1)
print()

# Step 4: Test market state file
print("Step 4: Testing market state file...")
try:
    state_reader = MarketStateReader()
    state = state_reader.load_state()
    if state:
        print("  [OK] market_state.json found and loaded")
        print(f"    - Regime: {state.get('regime', 'N/A')}")
        print(f"    - Bias: {state.get('global_bias', 'N/A')}")
        print(f"    - Approved Pairs: {state.get('approved_pairs', [])}")
    else:
        print("  [WARN] market_state.json not found (this is OK for testing)")
except Exception as e:
    print(f"  [FAIL] Market state failed: {e}")
print()

# Step 5: Test OANDA connection (quick test)
print("Step 5: Testing OANDA connection (quick test)...")
if oanda_token and oanda_account:
    try:
        oanda_client = OandaClient(
            access_token=oanda_token,
            account_id=oanda_account,
            environment=oanda_env
        )
        print("  [OK] OandaClient initialized")
        
        # Try to get account info (this will test the connection)
        print("  -> Testing API connection...")
        account_info = oanda_client.get_account_info()
        if account_info:
            print(f"  [OK] OANDA connection successful")
            print(f"    - Account Balance: {account_info.get('balance', 'N/A')}")
        else:
            print("  [WARN] OANDA connection failed (check credentials)")
    except Exception as e:
        print(f"  [FAIL] OANDA connection error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  [WARN] Skipping OANDA test (credentials not set)")
print()

# Step 6: Test signal generator
print("Step 6: Testing signal generator...")
try:
    signal_gen = SignalGenerator(ema_periods=[9, 21, 50])
    print("  [OK] SignalGenerator initialized")
except Exception as e:
    print(f"  [FAIL] SignalGenerator failed: {e}")
print()

# Step 7: Test risk manager
print("Step 7: Testing risk manager...")
try:
    risk_mgr = RiskManager(
        risk_per_trade_pct=0.5,
        daily_max_loss_pct=2.0,
        stop_loss_pips=5.0,
        take_profit_pips=8.0,
        max_consecutive_losses=3
    )
    print("  [OK] RiskManager initialized")
except Exception as e:
    print(f"  [FAIL] RiskManager failed: {e}")
print()

print("=" * 80)
print("All components tested!")
print("=" * 80)
print()
print("If all tests passed, Scalp-Engine should work.")
print("If it's still hanging, the issue is likely in the main loop logic.")
print()

