#!/usr/bin/env python3
"""
Phase 2 Cleanup Script for Scalp-Engine
Cancels all pending orders and clears state files

Run this in Render Shell for Scalp-Engine service
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, '/opt/render/project/src')

try:
    from auto_trader_core import PositionManager, TradeExecutor, TradeConfig
    from oandapyV20 import API
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this in Render Shell for Scalp-Engine service")
    sys.exit(1)

def main():
    print("=" * 80)
    print("Phase 2: Clear Stale Data and Delete Pending Trades")
    print("=" * 80)
    print()
    
    # Step 1: Cancel all pending orders
    print("Step 1: Cancelling all pending orders...")
    print("-" * 80)
    
    try:
        # Initialize components
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        api_key = os.getenv('OANDA_ACCESS_TOKEN')  # Use OANDA_ACCESS_TOKEN, not OANDA_API_KEY
        
        if not account_id or not api_key:
            print("❌ OANDA_ACCOUNT_ID or OANDA_ACCESS_TOKEN not set in environment")
            return
        
        # Determine environment (practice or live)
        environment = os.getenv('OANDA_ENV', 'practice')  # Use OANDA_ENV, not OANDA_ENVIRONMENT
        client = API(access_token=api_key, environment=environment)
        
        executor = TradeExecutor(account_id, client)
        config = TradeConfig()
        position_manager = PositionManager(executor, config)
        
        # Cancel all pending orders
        cancelled = position_manager.cancel_all_pending_orders(
            reason="Phase 2 cleanup - removing stale pending orders before fresh analysis"
        )
        
        print(f"✅ Cancelled {cancelled} pending order(s)")
        print()
        
    except Exception as e:
        print(f"❌ Error cancelling pending orders: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Step 2: Clear active trades state file
    print("Step 2: Clearing active trades state file...")
    print("-" * 80)
    
    try:
        state_file = Path('/var/data/active_trades.json')
        if state_file.exists():
            # Backup before deleting (optional)
            backup_file = Path('/var/data/active_trades.json.backup')
            if not backup_file.exists():
                import shutil
                shutil.copy2(state_file, backup_file)
                print(f"📦 Created backup: {backup_file}")
            
            state_file.unlink()
            print("✅ Cleared active_trades.json")
        else:
            print("ℹ️ active_trades.json does not exist (nothing to clear)")
        print()
        
    except Exception as e:
        print(f"❌ Error clearing state file: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Step 3: Verify cleanup
    print("Step 3: Verifying cleanup...")
    print("-" * 80)
    
    try:
        # Check for remaining pending orders in OANDA
        from oandapyV20.endpoints import orders
        
        r = orders.OrdersPending(accountID=account_id)
        client.request(r)
        pending_orders = r.response.get('orders', [])
        
        if pending_orders:
            print(f"⚠️ Warning: {len(pending_orders)} pending order(s) still exist in OANDA:")
            for order in pending_orders:
                print(f"  - {order.get('instrument')} {order.get('type')} @ {order.get('price')} (ID: {order.get('id')})")
        else:
            print("✅ No pending orders found in OANDA")
        
        # Check state file
        state_file = Path('/var/data/active_trades.json')
        if state_file.exists():
            print("⚠️ Warning: active_trades.json still exists")
        else:
            print("✅ active_trades.json cleared")
        
    except Exception as e:
        print(f"⚠️ Could not verify cleanup: {e}")
    
    print()
    print("=" * 80)
    print("✅ Phase 2 cleanup complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Go to Render Shell for Trade-Alerts service")
    print("2. Run Phase 2 script to clear market_state.json")
    print("3. Run Phase 3 script to generate fresh analysis")

if __name__ == "__main__":
    main()
