#!/usr/bin/env python
"""
Database Sync Script - Phase 2: Restore Local Visibility

Downloads RL database from Render production to local development environment.
This enables local analysis without running the full Trade-Alerts system.

Usage:
  Local: python sync_database_from_render.py [render_url]
  Examples:
    python sync_database_from_render.py https://trade-alerts.onrender.com
    python sync_database_from_render.py http://localhost:5001 (for local testing)

Behavior:
  - Detects if running on Render or locally
  - On Render: No-op (database is already local at /var/data)
  - Local: Downloads from Render URL, saves to data/trade_alerts_rl.db
  - Creates backup of existing local database before overwriting
  - Verifies download integrity
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import requests
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_on_render():
    """Check if running on Render"""
    return os.path.exists('/var/data') or os.getenv('RENDER') == 'true'


def get_render_url():
    """Get Render service URL from environment or arguments"""
    # First, check if explicitly provided as argument
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Try environment variables
    render_url = os.getenv('RENDER_DEPLOYMENT_URL')
    if render_url:
        return render_url

    # Try to infer from internal service name
    service_name = os.getenv('RENDER_SERVICE_NAME')
    if service_name:
        return f"https://{service_name}.onrender.com"

    # Default (user needs to provide)
    return None


def verify_database_integrity(db_path):
    """Verify database file is valid SQLite"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Try to query the schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()

        if not tables:
            logger.warning("⚠️  Database has no tables - may be empty or invalid")
            return False

        logger.info(f"✅ Database valid: {len(tables)} tables found")
        return True

    except Exception as e:
        logger.error(f"❌ Database integrity check failed: {e}")
        return False


def download_database(render_url, local_path):
    """Download database from Render"""
    # Ensure URL has protocol
    if not render_url.startswith('http'):
        render_url = f"https://{render_url}"

    download_url = f"{render_url.rstrip('/')}/download-database"

    logger.info(f"📥 Downloading from: {download_url}")

    try:
        response = requests.get(download_url, timeout=30)

        if response.status_code == 404:
            logger.error("❌ Database not found on Render")
            logger.error(f"   URL: {download_url}")
            logger.error("   Check that:")
            logger.error("   1. Render service is running")
            logger.error("   2. Service URL is correct")
            logger.error("   3. /var/data/trade_alerts_rl.db exists on Render")
            return False

        if response.status_code != 200:
            logger.error(f"❌ Download failed: HTTP {response.status_code}")
            logger.error(f"   Response: {response.text}")
            return False

        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup of existing database
        if local_path.exists():
            backup_path = local_path.parent / f"trade_alerts_rl.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"💾 Backing up existing database to {backup_path.name}")
            shutil.copy2(local_path, backup_path)

        # Write downloaded content
        with open(local_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"✅ Downloaded {len(response.content):,} bytes")
        logger.info(f"✅ Saved to {local_path}")

        # Verify integrity
        if verify_database_integrity(local_path):
            logger.info("✅ Database download successful and verified")
            return True
        else:
            logger.warning("⚠️  Database downloaded but integrity check failed")
            return False

    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Connection error: Cannot reach {render_url}")
        logger.error("   Check that:")
        logger.error("   1. Render service is running")
        logger.error("   2. URL is correct")
        logger.error("   3. Network connection is available")
        return False

    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout: Service took too long to respond")
        return False

    except Exception as e:
        logger.error(f"❌ Download failed: {type(e).__name__}: {e}")
        return False


def main():
    logger.info("="*80)
    logger.info("RL DATABASE SYNC - Phase 2: Restore Local Visibility")
    logger.info("="*80)
    logger.info("")

    # Check if running on Render
    if is_on_render():
        logger.info("ℹ️  Running on Render - database is already at /var/data/trade_alerts_rl.db")
        logger.info("   No sync needed")
        return 0

    logger.info("🖥️  Running locally - downloading database from Render...")
    logger.info("")

    # Get Render URL
    render_url = get_render_url()
    if not render_url:
        logger.error("❌ No Render URL provided")
        logger.error("   Usage: python sync_database_from_render.py <render_url>")
        logger.error("   Example: python sync_database_from_render.py https://trade-alerts.onrender.com")
        return 1

    # Define local database path
    local_path = Path('data/trade_alerts_rl.db')

    # Download
    success = download_database(render_url, local_path)

    if success:
        logger.info("")
        logger.info("="*80)
        logger.info("✅ DATABASE SYNC COMPLETE")
        logger.info("="*80)
        logger.info("")
        logger.info("You can now run local analysis tools:")
        logger.info("  python trade-alerts-review")
        logger.info("  python trading-analysis")
        logger.info("")
        return 0
    else:
        logger.info("")
        logger.info("="*80)
        logger.info("❌ DATABASE SYNC FAILED")
        logger.info("="*80)
        logger.info("")
        return 1


if __name__ == '__main__':
    sys.exit(main())
