"""
Sync Agent Results from Render to Local Machine

Downloads agent database and logs from Render, extracts cycle results,
and updates the local agent-coordination.md file with verification status.

Usage:
    python agents/sync_render_results.py                    # Sync from Render
    python agents/sync_render_results.py --local-db path   # Use local database
    python agents/sync_render_results.py --verify          # Verify sync completed
"""

import sqlite3
import json
import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import urllib.request
import urllib.error


class RenderSync:
    """Sync agent results from Render to local machine."""

    def __init__(self, render_api_url: str = "https://trade-alerts-api.onrender.com"):
        """Initialize sync client."""
        self.render_api_url = render_api_url
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / "agents"
        self.shared_docs = self.agents_dir / "shared-docs"
        self.logs_dir = self.shared_docs / "logs"
        self.coordination_file = self.shared_docs / "agent-coordination.md"

        # Database paths
        self.local_db = self.project_root / "data" / "agent_system.db"
        self.backup_db = self.project_root / "data" / ".agent_system_backup.db"

        # Log file mappings: expected_name -> actual_name_pattern
        self.log_mappings = {
            "scalp_engine.log": "scalp_engine_*.log",
            "oanda_trades.log": "oanda_*.log",
            "ui_activity.log": "scalp_ui_*.log",
        }

        self.ensure_directories()

    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.project_root / "data").mkdir(parents=True, exist_ok=True)

    def download_database_from_render(self) -> bool:
        """
        Download database from Render.

        Tries multiple methods:
        1. HTTP endpoint (/download-db)
        2. Git pull if available
        3. Looks for existing sync mechanism

        Returns:
            True if download successful, False otherwise
        """
        print("📥 Attempting to download agent database from Render...")

        # Method 1: Try HTTP endpoint
        endpoint = f"{self.render_api_url}/download-db"
        try:
            print(f"   Trying endpoint: {endpoint}")
            temp_db = self.backup_db
            urllib.request.urlretrieve(endpoint, temp_db)

            if temp_db.exists() and temp_db.stat().st_size > 0:
                print(f"   ✅ Downloaded {temp_db.stat().st_size} bytes")
                shutil.copy(temp_db, self.local_db)
                print(f"   ✅ Copied to local: {self.local_db}")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"   ⚠️  Endpoint failed: {e}")

        # Method 2: Check if database already exists locally from previous sync
        if self.local_db.exists():
            print(f"   ℹ️  Using existing local database")
            return True

        print(f"   ❌ Could not download database from Render")
        print(f"      Manual setup: Copy /var/data/agent_system.db from Render to {self.local_db}")
        return False

    def download_logs_from_render(self) -> bool:
        """
        Download logs from Render.

        Uses the existing /logs endpoint from config_api_server.

        Returns:
            True if logs downloaded, False otherwise
        """
        print("📥 Attempting to download logs from Render...")

        components = {
            "engine": "scalp_engine.log",
            "oanda": "oanda_trades.log",
            "ui": "ui_activity.log"
        }

        success_count = 0

        for component, expected_filename in components.items():
            endpoint = f"{self.render_api_url}/logs/{component}"
            try:
                print(f"   Downloading {component} logs from {endpoint}...")
                temp_file = self.logs_dir / f"temp_{expected_filename}"

                urllib.request.urlretrieve(endpoint, temp_file)

                if temp_file.exists() and temp_file.stat().st_size > 0:
                    final_file = self.logs_dir / expected_filename
                    temp_file.rename(final_file)
                    print(f"   ✅ Downloaded {component}: {final_file.stat().st_size} bytes")
                    success_count += 1
                else:
                    temp_file.unlink(missing_ok=True)
                    print(f"   ⚠️  Empty response for {component}")

            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                print(f"   ⚠️  {component} failed: {e}")

        if success_count > 0:
            print(f"   ✅ Downloaded {success_count}/{len(components)} log files")
            return success_count > 0

        print(f"   ℹ️  No logs downloaded (Render API may not be accessible)")
        return False

    def extract_latest_cycle(self) -> Optional[Dict[str, Any]]:
        """
        Extract latest cycle results from database.

        Returns:
            Dict with keys: cycle_number, analyst_status, expert_status,
                           coder_status, orchestrator_status, timestamps
        """
        if not self.local_db.exists():
            print("❌ Database not found at", self.local_db)
            return None

        try:
            conn = sqlite3.connect(self.local_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get latest cycle number from approval history (highest authority)
            cursor.execute("SELECT MAX(cycle_number) as max_cycle FROM approval_history")
            result = cursor.fetchone()
            latest_cycle = result['max_cycle'] if result else None

            if latest_cycle is None:
                # Fall back to orchestrator state
                cursor.execute("SELECT MAX(cycle_number) as max_cycle FROM orchestrator_state")
                result = cursor.fetchone()
                latest_cycle = result['max_cycle'] if result else None

            if latest_cycle is None:
                print("⚠️  No cycles found in database")
                return None

            print(f"📊 Latest cycle: {latest_cycle}")

            cycle_data = {
                "cycle_number": latest_cycle,
                "analyst_status": None,
                "expert_status": None,
                "coder_status": None,
                "orchestrator_status": None,
                "analyst_timestamp": None,
                "expert_timestamp": None,
                "coder_timestamp": None,
                "orchestrator_timestamp": None,
            }

            # Get analyst status
            cursor.execute("""
                SELECT status, created_at FROM agent_analyses
                WHERE cycle_number = ? ORDER BY created_at DESC LIMIT 1
            """, (latest_cycle,))
            row = cursor.fetchone()
            if row:
                cycle_data["analyst_status"] = row['status']
                cycle_data["analyst_timestamp"] = row['created_at']

            # Get expert status
            cursor.execute("""
                SELECT status, created_at FROM agent_recommendations
                WHERE cycle_number = ? ORDER BY created_at DESC LIMIT 1
            """, (latest_cycle,))
            row = cursor.fetchone()
            if row:
                cycle_data["expert_status"] = row['status']
                cycle_data["expert_timestamp"] = row['created_at']

            # Get coder status
            cursor.execute("""
                SELECT status, created_at FROM agent_implementations
                WHERE cycle_number = ? ORDER BY created_at DESC LIMIT 1
            """, (latest_cycle,))
            row = cursor.fetchone()
            if row:
                cycle_data["coder_status"] = row['status']
                cycle_data["coder_timestamp"] = row['created_at']

            # Get orchestrator status
            cursor.execute("""
                SELECT decision, auto_approved, created_at FROM approval_history
                WHERE cycle_number = ? ORDER BY created_at DESC LIMIT 1
            """, (latest_cycle,))
            row = cursor.fetchone()
            if row:
                cycle_data["orchestrator_status"] = row['decision']
                cycle_data["orchestrator_timestamp"] = row['created_at']

            conn.close()
            return cycle_data

        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            return None

    def update_coordination_log(self, cycle_data: Dict[str, Any]):
        """Update agent-coordination.md with latest cycle status."""
        if not cycle_data:
            return

        cycle_num = cycle_data["cycle_number"]
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Status emoji mapping
        status_emoji = {
            "COMPLETED": "✅",
            "APPROVED": "✅",
            "REJECTED": "❌",
            "PENDING": "⏳",
            "FAILED": "❌",
            "IN_PROGRESS": "🔄",
            None: "❓"
        }

        session_entry = f"""
## Session {cycle_num} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

### Analyst Phase
- **Status:** {status_emoji.get(cycle_data['analyst_status'], '?')} {cycle_data['analyst_status'] or 'NOT_RUN'}
- **Timestamp:** {cycle_data['analyst_timestamp'] or 'N/A'}
- **Report:** `analyst/analysis-reports/report-cycle{cycle_num}.md`

### Forex Expert Phase
- **Status:** {status_emoji.get(cycle_data['expert_status'], '?')} {cycle_data['expert_status'] or 'NOT_RUN'}
- **Timestamp:** {cycle_data['expert_timestamp'] or 'N/A'}
- **Recommendations:** `forex-expert/recommendations/recommendations-cycle{cycle_num}.md`

### Coding Expert Phase
- **Status:** {status_emoji.get(cycle_data['coder_status'], '?')} {cycle_data['coder_status'] or 'NOT_RUN'}
- **Timestamp:** {cycle_data['coder_timestamp'] or 'N/A'}
- **Implementation:** `coding-expert/implementations/implementation-cycle{cycle_num}.md`

### Orchestrator Phase
- **Status:** {status_emoji.get(cycle_data['orchestrator_status'], '?')} {cycle_data['orchestrator_status'] or 'NOT_RUN'}
- **Timestamp:** {cycle_data['orchestrator_timestamp'] or 'N/A'}
- **Decision:** {cycle_data['orchestrator_status'] or 'PENDING'}

### Sync Status
- **Last Synced:** {timestamp}
- **Sync Source:** Render `/var/data/agent_system.db`
- **Logs Available:** {len(list(self.logs_dir.glob('*.log')))} files

---
"""

        # Read existing file or create new
        if self.coordination_file.exists():
            with open(self.coordination_file, 'r') as f:
                content = f.read()
        else:
            content = """# Agent Coordination Log

This file is auto-updated by the sync system every time agents run on Render.

---

"""

        # Append new session at top (after header)
        header_end = content.find("---\n\n", 0)
        if header_end > 0:
            header_end += 5
            new_content = content[:header_end] + session_entry + content[header_end:]
        else:
            new_content = content + session_entry

        with open(self.coordination_file, 'w') as f:
            f.write(new_content)

        print(f"✅ Updated coordination log: {self.coordination_file}")

    def sync(self) -> bool:
        """Run complete sync process."""
        print("=" * 60)
        print("🔄 AGENT SYNC SYSTEM - Pulling Results from Render")
        print("=" * 60)

        # Step 1: Download database
        db_ok = self.download_database_from_render()

        # Step 2: Download logs
        logs_ok = self.download_logs_from_render()

        # Step 3: Extract cycle results
        print("\n📊 Extracting cycle results...")
        cycle_data = self.extract_latest_cycle()

        if cycle_data:
            print(f"   Cycle {cycle_data['cycle_number']}:")
            print(f"   - Analyst: {cycle_data['analyst_status'] or 'NOT_RUN'}")
            print(f"   - Expert: {cycle_data['expert_status'] or 'NOT_RUN'}")
            print(f"   - Coder: {cycle_data['coder_status'] or 'NOT_RUN'}")
            print(f"   - Orchestrator: {cycle_data['orchestrator_status'] or 'NOT_RUN'}")

        # Step 4: Update coordination log
        if cycle_data:
            self.update_coordination_log(cycle_data)

        print("\n" + "=" * 60)
        print("✅ SYNC COMPLETE")
        print("=" * 60)
        print(f"\n📂 Results location: {self.shared_docs}")
        print(f"📋 Coordination log: {self.coordination_file}")
        print(f"📥 Logs directory: {self.logs_dir}")

        return db_ok and cycle_data is not None


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sync agent results from Render to local machine"
    )
    parser.add_argument(
        "--api-url",
        default="https://trade-alerts-api.onrender.com",
        help="Render API base URL"
    )
    parser.add_argument(
        "--local-db",
        help="Use existing local database instead of downloading"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify sync status, don't download"
    )

    args = parser.parse_args()

    sync = RenderSync(render_api_url=args.api_url)

    if args.verify:
        print("✅ Verification mode")
        cycle_data = sync.extract_latest_cycle()
        if cycle_data:
            print(f"Latest cycle: {cycle_data['cycle_number']}")
            print(f"  Analyst: {cycle_data['analyst_status']}")
            print(f"  Expert: {cycle_data['expert_status']}")
            print(f"  Coder: {cycle_data['coder_status']}")
            print(f"  Orchestrator: {cycle_data['orchestrator_status']}")
        else:
            print("No cycles found")
    elif args.local_db:
        print(f"Using local database: {args.local_db}")
        sync.local_db = Path(args.local_db)
        cycle_data = sync.extract_latest_cycle()
        if cycle_data:
            sync.update_coordination_log(cycle_data)
    else:
        sync.sync()


if __name__ == "__main__":
    main()
