#!/usr/bin/env python3
"""
Phase 2 Cleanup Script for Trade-Alerts
Clears stale market state file

Run this in Render Shell for Trade-Alerts service
"""

import os
from pathlib import Path
from datetime import datetime

def main():
    print("=" * 80)
    print("Phase 2: Clear Stale Market State File")
    print("=" * 80)
    print()
    
    # Determine market state file path
    market_state_path = os.getenv('MARKET_STATE_FILE_PATH', '/var/data/market_state.json')
    market_state_file = Path(market_state_path)
    
    print(f"Market state file: {market_state_file}")
    print()
    
    # Check if file exists
    if not market_state_file.exists():
        print("ℹ️ market_state.json does not exist (nothing to clear)")
        print("   This is OK - fresh analysis will create a new file")
        return
    
    # Show current file info
    try:
        import json
        with open(market_state_file, 'r') as f:
            state = json.load(f)
        
        timestamp = state.get('timestamp', 'Unknown')
        opportunities_count = len(state.get('opportunities', []))
        
        print(f"Current market state info:")
        print(f"  - Timestamp: {timestamp}")
        print(f"  - Opportunities: {opportunities_count}")
        print()
        
        # Calculate age
        try:
            from datetime import datetime, timezone
            if timestamp and timestamp != 'Unknown':
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                age = now - ts
                age_hours = age.total_seconds() / 3600
                print(f"  - Age: {age_hours:.1f} hours")
        except:
            pass
        
    except Exception as e:
        print(f"⚠️ Could not read market state file: {e}")
        print("   Proceeding with deletion anyway...")
        print()
    
    # Create backup
    print("Step 1: Creating backup...")
    backup_file = Path(f"{market_state_path}.backup")
    try:
        import shutil
        shutil.copy2(market_state_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
    except Exception as e:
        print(f"⚠️ Could not create backup: {e}")
        print("   Proceeding without backup...")
    print()
    
    # Delete stale market state
    print("Step 2: Deleting stale market state file...")
    try:
        market_state_file.unlink()
        print("✅ Deleted stale market_state.json")
    except Exception as e:
        print(f"❌ Error deleting file: {e}")
        return
    print()
    
    # Verify deletion
    print("Step 3: Verifying deletion...")
    if market_state_file.exists():
        print("⚠️ Warning: File still exists after deletion attempt")
    else:
        print("✅ market_state.json successfully deleted")
    print()
    
    print("=" * 80)
    print("✅ Phase 2 cleanup complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run Phase 3 script to generate fresh analysis")
    print("2. Verify fresh market_state.json is created with current prices")

if __name__ == "__main__":
    main()
