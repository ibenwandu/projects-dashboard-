#!/usr/bin/env python3
"""
End-to-End Agent Workflow Test

Downloads real logs from Render, runs all 4 agent phases,
validates database population, and tests the complete workflow.

Usage:
    python run_agent_test.py
"""

import os
import sys
import sqlite3
import urllib.request
import urllib.error
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.analyst_agent import AnalystAgent
from agents.forex_trading_expert_agent import ForexTradingExpertAgent
from agents.coding_expert_agent import CodingExpertAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.shared.database import get_database


class AgentWorkflowTest:
    """End-to-end agent workflow test."""

    def __init__(self):
        """Initialize test."""
        self.project_root = Path(__file__).parent
        self.logs_dir = self.project_root / "Scalp-Engine" / "logs"
        self.data_dir = self.project_root / "data"
        self.cycle_number = 1
        self.render_api_url = "https://trade-alerts-api.onrender.com"

        # Create necessary directories
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.log("")
        self.log("=" * 80)
        self.log("END-TO-END AGENT WORKFLOW TEST")
        self.log("=" * 80)
        self.log("")
        self.log(f"Project Root: {self.project_root}")
        self.log(f"Logs Directory: {self.logs_dir}")
        self.log(f"Data Directory: {self.data_dir}")

    def log(self, msg: str = ""):
        """Print timestamped message."""
        if not msg:
            print("")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def download_logs_from_render(self) -> bool:
        """Download logs from Render API."""
        self.log("")
        self.log("-" * 80)
        self.log("STEP 1: Downloading Logs from Render")
        self.log("-" * 80)

        components = {
            "engine": "scalp_engine.log",
            "oanda": "oanda_trades.log",
            "ui": "ui_activity.log"
        }

        success_count = 0

        for component, filename in components.items():
            endpoint = f"{self.render_api_url}/logs/{component}"
            try:
                self.log(f"  Downloading {component} logs...")
                log_file = self.logs_dir / filename
                urllib.request.urlretrieve(endpoint, log_file)

                if log_file.exists() and log_file.stat().st_size > 0:
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    self.log(f"  [OK] Downloaded {filename}: {size_mb:.2f} MB")
                    success_count += 1
                else:
                    self.log(f"  [WARN] Empty response for {component}")

            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                self.log(f"  [WARN] {component} download failed: {e}")
            except Exception as e:
                self.log(f"  [FAIL] Unexpected error downloading {component}: {e}")

        if success_count == 0:
            self.log(f"  [WARN] No logs downloaded from Render")
            self.log(f"  Note: Render API may not be accessible")
            return False

        self.log(f"  [OK] Downloaded {success_count}/{len(components)} log files")
        return success_count > 0

    def verify_logs_exist(self) -> bool:
        """Verify log files exist locally."""
        self.log("")
        self.log("-" * 80)
        self.log("STEP 1B: Verifying Log Files")
        self.log("-" * 80)

        expected_logs = [
            "scalp_engine.log",
            "oanda_trades.log",
            "ui_activity.log"
        ]

        found = 0
        for log_file in expected_logs:
            log_path = self.logs_dir / log_file
            if log_path.exists():
                size_mb = log_path.stat().st_size / (1024 * 1024)
                self.log(f"  [OK] {log_file}: {size_mb:.2f} MB")
                found += 1
            else:
                self.log(f"  [FAIL] {log_file}: NOT FOUND")

        if found == 0:
            self.log(f"  [WARN] No log files found locally")
            self.log(f"  Cannot proceed with agent test without logs")
            return False

        self.log(f"  [OK] Found {found}/{len(expected_logs)} log files")
        return found > 0

    def clear_database(self):
        """Clear test database to start fresh."""
        self.log("")
        self.log("-" * 80)
        self.log("STEP 2: Clearing Database")
        self.log("-" * 80)

        db_path = self.data_dir / "agent_system.db"
        if db_path.exists():
            db_path.unlink()
            self.log(f"  [OK] Cleared database: {db_path}")
        else:
            self.log(f"  [INFO] Database doesn't exist yet (will be created)")

    def run_analyst_agent(self) -> bool:
        """Phase 1: Run Analyst Agent."""
        self.log("")
        self.log("-" * 80)
        self.log("PHASE 1: Running Analyst Agent")
        self.log("-" * 80)

        try:
            analyst = AnalystAgent(log_dir=str(self.logs_dir))
            success = analyst.run(cycle_number=self.cycle_number)

            if success:
                self.log(f"  [OK] Analyst Agent completed successfully")
                return True
            else:
                self.log(f"  [WARN] Analyst Agent completed with warnings")
                return False

        except Exception as e:
            self.log(f"  [FAIL] Analyst Agent failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_forex_expert_agent(self) -> bool:
        """Phase 2: Run Forex Expert Agent."""
        self.log("")
        self.log("-" * 80)
        self.log("PHASE 2: Running Forex Expert Agent")
        self.log("-" * 80)

        try:
            forex = ForexTradingExpertAgent()
            success = forex.run(cycle_number=self.cycle_number)

            if success:
                self.log(f"  [OK] Forex Expert Agent completed successfully")
                return True
            else:
                self.log(f"  [WARN] Forex Expert Agent completed with warnings")
                return False

        except Exception as e:
            self.log(f"  [FAIL] Forex Expert Agent failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_coding_expert_agent(self) -> bool:
        """Phase 3: Run Coding Expert Agent."""
        self.log("")
        self.log("-" * 80)
        self.log("PHASE 3: Running Coding Expert Agent")
        self.log("-" * 80)

        try:
            coding = CodingExpertAgent()
            success = coding.run(cycle_number=self.cycle_number)

            if success:
                self.log(f"  [OK] Coding Expert Agent completed successfully")
                return True
            else:
                self.log(f"  [WARN] Coding Expert Agent completed with warnings")
                return False

        except Exception as e:
            self.log(f"  [FAIL] Coding Expert Agent failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_orchestrator_agent(self) -> bool:
        """Phase 4: Run Orchestrator Agent."""
        self.log("")
        self.log("-" * 80)
        self.log("PHASE 4: Running Orchestrator Agent")
        self.log("-" * 80)

        try:
            orchestrator = OrchestratorAgent()
            success = orchestrator.run_cycle(cycle_number=self.cycle_number)

            if success:
                self.log(f"  [OK] Orchestrator Agent completed successfully")
                return True
            else:
                self.log(f"  [WARN] Orchestrator Agent completed with warnings")
                return False

        except Exception as e:
            self.log(f"  [FAIL] Orchestrator Agent failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def verify_database_population(self) -> bool:
        """Verify all database tables populated."""
        self.log("")
        self.log("-" * 80)
        self.log("STEP 3: Verifying Database Population")
        self.log("-" * 80)

        try:
            db = get_database()
            db.initialize_schema()

            with db.get_connection() as conn:
                cursor = conn.cursor()

                # Check each table
                tables = {
                    "agent_analyses": "Analyst outputs",
                    "agent_recommendations": "Forex Expert outputs",
                    "agent_implementations": "Coding Expert outputs",
                    "approval_history": "Orchestrator approvals"
                }

                all_ok = True
                for table, description in tables.items():
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    count = result[0] if result else 0

                    if count > 0:
                        self.log(f"  [OK] {description}: {count} record(s)")
                    else:
                        self.log(f"  [WARN] {description}: {count} record(s)")
                        all_ok = False

                return all_ok

        except Exception as e:
            self.log(f"  [FAIL] Database verification failed: {e}")
            return False

    def run(self) -> bool:
        """Run complete test."""
        try:
            # Step 1: Download logs
            logs_ok = self.download_logs_from_render()

            # Step 1B: Verify logs exist (download might have failed, but local logs might be available)
            if not self.verify_logs_exist():
                self.log("")
                self.log("[FAIL] Cannot proceed - no log files available")
                return False

            # Step 2: Clear database
            self.clear_database()

            # Step 3: Run agents in sequence
            analyst_ok = self.run_analyst_agent()
            forex_ok = self.run_forex_expert_agent()
            coding_ok = self.run_coding_expert_agent()
            orchestrator_ok = self.run_orchestrator_agent()

            # Step 4: Verify database
            db_ok = self.verify_database_population()

            # Summary
            self.log("")
            self.log("=" * 80)
            self.log("TEST SUMMARY")
            self.log("=" * 80)
            self.log(f"  Phase 1 - Analyst Agent:           {'[OK]' if analyst_ok else '[FAIL]'}")
            self.log(f"  Phase 2 - Forex Expert Agent:      {'[OK]' if forex_ok else '[FAIL]'}")
            self.log(f"  Phase 3 - Coding Expert Agent:     {'[OK]' if coding_ok else '[FAIL]'}")
            self.log(f"  Phase 4 - Orchestrator Agent:      {'[OK]' if orchestrator_ok else '[FAIL]'}")
            self.log(f"  Database Validation:               {'[OK]' if db_ok else '[FAIL]'}")

            # Final summary
            if analyst_ok and forex_ok and coding_ok and orchestrator_ok and db_ok:
                self.log("")
                self.log("[OK] ALL TESTS PASSED - AGENT SYSTEM IS READY FOR PRODUCTION")
                self.log("=" * 80)
                self.log("")
                return True
            else:
                self.log("")
                self.log("[FAIL] SOME TESTS FAILED - REVIEW LOGS ABOVE FOR DETAILS")
                self.log("=" * 80)
                self.log("")
                return False

        except Exception as e:
            self.log("[FAIL] Test failed with exception: {}".format(e))
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    test = AgentWorkflowTest()
    success = test.run()
    sys.exit(0 if success else 1)
