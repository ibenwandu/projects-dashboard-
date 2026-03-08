#!/usr/bin/env python3
"""
Utility script to update the timestamp in market_state.json to current time.
This is a temporary workaround if Trade-Alerts hasn't run recently.

WARNING: This only updates the timestamp - it doesn't regenerate market analysis.
The real fix is to ensure Trade-Alerts runs successfully at scheduled times.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def update_timestamp(file_path: str = None):
    """Update timestamp in market_state.json to current time"""
    
    # Get file path from environment or use default
    if file_path is None:
        file_path = os.getenv('MARKET_STATE_FILE_PATH', '/var/data/market_state.json')
    
    file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        print(f"❌ Error: Market state file not found at: {file_path}")
        print(f"   Check if Trade-Alerts has generated the file yet.")
        return False
    
    try:
        # Read existing state
        with open(file_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # Store old timestamp
        old_timestamp = state.get('timestamp', 'Unknown')
        
        # Update timestamp to current time
        state['timestamp'] = datetime.utcnow().isoformat() + "Z"
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        
        print(f"✅ Market state timestamp updated successfully")
        print(f"   File: {file_path}")
        print(f"   Old timestamp: {old_timestamp}")
        print(f"   New timestamp: {state['timestamp']}")
        print(f"")
        print(f"⚠️  WARNING: This is a temporary workaround!")
        print(f"   The file content (bias, regime, opportunities) is still old.")
        print(f"   The real fix is to check why Trade-Alerts didn't run at 4pm:")
        print(f"   1. Check Trade-Alerts logs for scheduled analysis")
        print(f"   2. Look for '=== Scheduled Analysis Time: ... 16:XX:XX EST ==='")
        print(f"   3. Check if analysis completed all steps (especially Step 9)")
        print(f"   4. See DIAGNOSE_MISSING_MARKET_STATE.md for details")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in market state file: {e}")
        return False
    except PermissionError as e:
        print(f"❌ Error: Permission denied writing to {file_path}: {e}")
        print(f"   Check disk mount permissions")
        return False
    except Exception as e:
        print(f"❌ Error updating timestamp: {e}")
        return False

if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = update_timestamp(file_path)
    sys.exit(0 if success else 1)
