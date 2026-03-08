#!/usr/bin/env python3
"""
Check market state file location and environment
"""
import os
import json
from pathlib import Path

print("=" * 80)
print("Market State File Check")
print("=" * 80)
print()

# Check environment variable
env_path = os.getenv('MARKET_STATE_FILE_PATH')
print(f"1. Environment Variable:")
print(f"   MARKET_STATE_FILE_PATH = {env_path if env_path else 'Not set (using default)'}")
print()

# Default path
default_path = '/var/data/market_state.json'
actual_path = env_path if env_path else default_path
print(f"2. Expected File Path:")
print(f"   {actual_path}")
print()

# Check if directory exists
path_obj = Path(actual_path)
parent_dir = path_obj.parent
print(f"3. Directory Check:")
print(f"   Parent directory: {parent_dir}")
print(f"   Exists: {parent_dir.exists()}")
if parent_dir.exists():
    print(f"   Writable: {os.access(parent_dir, os.W_OK)}")
    print(f"   Files in directory:")
    try:
        files = sorted([f.name for f in parent_dir.iterdir() if f.is_file()])
        if files:
            for f in files[:10]:  # Show first 10
                print(f"     - {f}")
        else:
            print("     (no files found)")
    except Exception as e:
        print(f"     ⚠️ Error listing: {e}")
print()

# Check if file exists
print(f"4. File Check:")
print(f"   File exists: {path_obj.exists()}")
if path_obj.exists():
    print(f"   File size: {path_obj.stat().st_size} bytes")
    print(f"   Readable: {os.access(path_obj, os.R_OK)}")
    
    # Try to read it
    try:
        with open(path_obj) as f:
            state = json.load(f)
        timestamp = state.get('timestamp', 'N/A')
        opportunities = len(state.get('opportunities', []))
        print(f"   ✅ File is valid JSON")
        print(f"   Timestamp: {timestamp}")
        print(f"   Opportunities: {opportunities}")
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
else:
    print(f"   ⚠️ File not found at expected location")
print()

# Check alternative locations
print(f"5. Alternative Locations Check:")
alt_paths = [
    '/var/data/market_state.json',
    './market_state.json',
    '../market_state.json',
    '../Trade-Alerts/market_state.json',
    'market_state.json',
]
for alt_path in alt_paths:
    alt_obj = Path(alt_path)
    if alt_obj.exists() and alt_path != actual_path:
        print(f"   ✅ Found at: {alt_path}")
        try:
            with open(alt_obj) as f:
                state = json.load(f)
            print(f"      Timestamp: {state.get('timestamp', 'N/A')}")
        except:
            pass
print()

print("=" * 80)
print("Summary:")
print("=" * 80)
if path_obj.exists():
    print("✅ Market state file found at expected location")
else:
    print("❌ Market state file NOT found at expected location")
    print("   This could mean:")
    print("   1. Trade-Alerts hasn't generated it yet")
    print("   2. Services are on different disks (not shared)")
    print("   3. File is in a different location")
    print()
    print("   Next steps:")
    print("   1. Check Trade-Alerts service - verify it's writing to /var/data/market_state.json")
    print("   2. Check if services share the same disk in Render")
    print("   3. Run fresh analysis in Trade-Alerts to generate the file")
