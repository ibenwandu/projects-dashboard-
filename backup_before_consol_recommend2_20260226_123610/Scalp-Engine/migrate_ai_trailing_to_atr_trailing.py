#!/usr/bin/env python3
"""
Migration script to rename AI_TRAILING to ATR_TRAILING in persisted config files.
Run this in Render shell to fix the persisted config.

Usage:
  python migrate_ai_trailing_to_atr_trailing.py
"""

import os
import json
from pathlib import Path

def migrate_config_file(filepath):
    """Migrate AI_TRAILING to ATR_TRAILING in a config file"""
    try:
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filepath}")
            return False

        with open(filepath, 'r') as f:
            config = json.load(f)

        if 'stop_loss_type' not in config:
            print(f"⚠️  No stop_loss_type in {filepath}")
            return False

        old_value = config['stop_loss_type']

        if old_value == 'AI_TRAILING':
            config['stop_loss_type'] = 'ATR_TRAILING'
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Updated {filepath}: AI_TRAILING → ATR_TRAILING")
            return True
        elif old_value == 'ATR_TRAILING':
            print(f"✅ {filepath}: Already using ATR_TRAILING")
            return True
        else:
            print(f"ℹ️  {filepath}: Using {old_value} (no change needed)")
            return True

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """Migrate all config files"""
    print("=" * 60)
    print("AI_TRAILING → ATR_TRAILING Migration Script")
    print("=" * 60)
    print()

    files_to_migrate = [
        '/var/data/auto_trader_config.json',
        '/var/data/semi_auto_config.json',
        '/var/data/trade_states.json',
    ]

    success_count = 0
    for filepath in files_to_migrate:
        if migrate_config_file(filepath):
            success_count += 1

    print()
    print("=" * 60)
    if success_count == len(files_to_migrate):
        print("✅ Migration complete! Restart config-api service.")
    else:
        print(f"⚠️  Partial success: {success_count}/{len(files_to_migrate)} files")
    print("=" * 60)

if __name__ == '__main__':
    main()
