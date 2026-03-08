"""
Backup Statistics Script - Quick health check for Local Backup System

Usage:
    python get_backup_stats.py

This script provides a quick overview of the backup system status,
including file counts, sizes, and latest backup information.
"""

from pathlib import Path
from datetime import datetime

def get_backup_stats():
    """Gather and display backup system statistics."""
    archive = Path('logs_archive')
    
    if not archive.exists():
        print("❌ logs_archive directory not found!")
        return
    
    # Total files and size
    all_files = list(archive.rglob('*'))
    all_files = [f for f in all_files if f.is_file()]
    total_size = sum(f.stat().st_size for f in all_files)
    
    # By directory
    scalp_files = list((archive / 'Scalp-Engine').glob('*')) if (archive / 'Scalp-Engine').exists() else []
    scalp_files = [f for f in scalp_files if f.is_file()]
    scalp_size = sum(f.stat().st_size for f in scalp_files)
    
    trade_files = list((archive / 'Trade-Alerts').glob('*'))
    trade_files = [f for f in trade_files if f.is_file()]
    trade_size = sum(f.stat().st_size for f in trade_files)
    trade_avg = trade_size / len(trade_files) if trade_files else 0
    
    session_files = list((archive / 'sessions').rglob('*.json'))
    session_size = sum(f.stat().st_size for f in session_files)
    
    legacy_files = list((archive / 'logs').glob('*')) if (archive / 'logs').exists() else []
    legacy_files = [f for f in legacy_files if f.is_file()]
    legacy_size = sum(f.stat().st_size for f in legacy_files)
    
    # By date
    dates = ['20260220', '20260221', '20260222', '20260223']
    date_counts = {}
    for d in dates:
        date_dir = archive / 'sessions' / d
        if date_dir.exists():
            date_counts[d] = len(list(date_dir.glob('*.json')))
        else:
            date_counts[d] = 0
    
    # Latest backup
    latest = None
    latest_time = None
    if (archive / 'sessions' / '20260223').exists():
        latest_files = list((archive / 'sessions' / '20260223').glob('*.json'))
        if latest_files:
            latest = max(latest_files, key=lambda p: p.stat().st_mtime)
            latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
    
    # Print results
    print("=" * 70)
    print("BACKUP SYSTEM STATISTICS")
    print("=" * 70)
    print(f"\nTotal Archive:")
    print(f"   Files: {len(all_files)}")
    print(f"   Size: {total_size / (1024*1024):.2f} MB")
    
    print(f"\nBy Directory:")
    print(f"   Scalp-Engine: {len(scalp_files)} files ({scalp_size/1024:.2f} KB)")
    if len(scalp_files) == 0:
        print(f"      WARNING: No files - API endpoints may be down")
    print(f"   Trade-Alerts: {len(trade_files)} files ({trade_size/1024:.2f} KB total, {trade_avg/1024:.2f} KB avg)")
    print(f"   Sessions: {len(session_files)} files ({session_size/1024:.2f} KB)")
    if legacy_files:
        print(f"   Legacy logs/: {len(legacy_files)} files ({legacy_size/1024:.2f} KB) - from initial setup")
    
    print(f"\nBackup History by Date:")
    for d, count in date_counts.items():
        date_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        print(f"   {date_str}: {count} backups")
    
    if latest:
        print(f"\nLatest Backup:")
        print(f"   File: {latest.name}")
        print(f"   Time: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        age_minutes = (datetime.now() - latest_time).total_seconds() / 60
        if age_minutes < 20:
            print(f"   Status: OK - Recent ({age_minutes:.1f} minutes ago)")
        elif age_minutes < 60:
            print(f"   Status: WARNING - Stale ({age_minutes:.1f} minutes ago)")
        else:
            print(f"   Status: ERROR - Very stale ({age_minutes/60:.1f} hours ago)")
    else:
        print(f"\nLatest Backup: None found")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    get_backup_stats()

