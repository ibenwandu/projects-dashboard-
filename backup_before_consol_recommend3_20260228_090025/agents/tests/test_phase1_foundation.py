"""
Test Phase 1 foundation: Database, backups, audit logging, and Pushover.

Run with: python -m pytest agents/tests/test_phase1_foundation.py -v
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.shared.database import Database
from agents.shared.backup_manager import BackupManager
from agents.shared.audit_logger import AuditLogger
from agents.shared.pushover_notifier import PushoverNotifier
from agents.shared.json_schema import (
    AnalysisSchema,
    RecommendationSchema,
    ImplementationSchema,
    ApprovalSchema,
    AuditEventSchema
)


class TestDatabase:
    """Test database operations."""

    def setup_method(self):
        """Setup for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)

    def test_database_creation(self):
        """Test database is created."""
        self.db.initialize_schema()
        assert os.path.exists(self.db_path)

    def test_schema_initialization(self):
        """Test all tables are created."""
        self.db.initialize_schema()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = {
                "agent_analyses",
                "agent_recommendations",
                "agent_implementations",
                "approval_history",
                "audit_trail",
                "orchestrator_state",
                "config"
            }
            assert expected_tables.issubset(set(tables))

    def test_save_analysis(self):
        """Test saving analysis."""
        self.db.initialize_schema()
        analysis = AnalysisSchema.create_empty()
        analysis_json = json.dumps(analysis)

        result_id = self.db.save_analysis(
            cycle_number=1,
            analysis_json=analysis_json
        )
        assert result_id > 0

        # Retrieve and verify
        retrieved = self.db.get_analysis(cycle_number=1)
        assert retrieved is not None
        assert retrieved["cycle_number"] == 1

    def test_approval_history(self):
        """Test approval history tracking."""
        self.db.initialize_schema()
        approval = ApprovalSchema.create_empty(cycle_number=1, implementation_id=1)
        approval["decision"] = "AUTO_APPROVED"
        approval["test_coverage"] = 0.95

        result_id = self.db.save_approval(approval)
        assert result_id > 0

        # Retrieve and verify
        approvals = self.db.get_approval_history(limit=10)
        assert len(approvals) > 0
        assert approvals[0]["decision"] == "AUTO_APPROVED"

    def test_config_storage(self):
        """Test configuration storage."""
        self.db.initialize_schema()
        self.db.set_config("test_key", "test_value")

        retrieved = self.db.get_config("test_key")
        assert retrieved == "test_value"

    def test_health_check(self):
        """Test database health check."""
        self.db.initialize_schema()
        assert self.db.health_check()


class TestBackupManager:
    """Test git backup and rollback."""

    def setup_method(self):
        """Setup for each test."""
        self.backup_manager = BackupManager(repo_path=".")

    def test_get_current_commit(self):
        """Test getting current commit hash."""
        success, commit = self.backup_manager.get_current_commit()
        assert success
        assert len(commit) == 40  # Git commit hash is 40 chars (SHA-1)

    def test_get_branch_name(self):
        """Test getting branch name."""
        success, branch = self.backup_manager.get_branch_name()
        assert success
        assert branch in ["main", "master", "develop"]  # Common branches

    def test_diff_stats(self):
        """Test getting diff statistics."""
        success, stats = self.backup_manager.get_diff_stats("HEAD~1", "HEAD")
        # May fail if only 1 commit, but that's ok
        if success:
            assert "files_changed" in stats


class TestJsonSchemas:
    """Test JSON schema validation."""

    def test_analysis_schema(self):
        """Test analysis schema."""
        analysis = AnalysisSchema.create_empty()
        assert AnalysisSchema.validate(analysis)

    def test_recommendation_schema(self):
        """Test recommendation schema."""
        rec = RecommendationSchema.create_empty()
        assert RecommendationSchema.validate(rec)

    def test_implementation_schema(self):
        """Test implementation schema."""
        impl = ImplementationSchema.create_empty()
        assert ImplementationSchema.validate(impl)

    def test_approval_schema(self):
        """Test approval schema."""
        approval = ApprovalSchema.create_empty(cycle_number=1, implementation_id=1)
        assert ApprovalSchema.validate(approval)

    def test_audit_event_schema(self):
        """Test audit event schema."""
        event = AuditEventSchema.create_event(
            cycle_number=1,
            event="TEST_EVENT",
            agent="TEST_AGENT",
            phase="TEST_PHASE"
        )
        assert AuditEventSchema.validate(event)


class TestAuditLogger:
    """Test audit logging."""

    def setup_method(self):
        """Setup for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db = Database(self.db_path)
        self.db.initialize_schema()

        self.export_dir = os.path.join(self.temp_dir, "exports")
        self.audit_logger = AuditLogger(export_dir=self.export_dir)
        self.audit_logger.db = self.db  # Use test database

    def test_log_event(self):
        """Test logging event."""
        success = self.audit_logger.log_event(
            cycle_number=1,
            event="TEST_EVENT",
            agent="TEST_AGENT",
            phase="TEST_PHASE",
            print_to_console=False
        )
        assert success

    def test_log_workflow_started(self):
        """Test logging workflow started."""
        success = self.audit_logger.log_workflow_started(cycle_number=1)
        assert success

    def test_export_audit_trail(self):
        """Test exporting audit trail."""
        self.audit_logger.log_workflow_started(cycle_number=1)

        success = self.audit_logger.export_audit_trail()
        assert success
        assert os.path.exists(os.path.join(self.export_dir, "audit_trail.json"))

    def test_cycle_summary(self):
        """Test getting cycle summary."""
        self.audit_logger.log_workflow_started(cycle_number=1)
        self.audit_logger.log_agent_started(cycle_number=1, agent="ANALYST", phase="ANALYSIS")

        summary = self.audit_logger.get_cycle_summary(cycle_number=1)
        assert summary["cycle_number"] == 1
        assert summary["total_events"] >= 2


class TestPushoverNotifier:
    """Test Pushover integration."""

    def setup_method(self):
        """Setup for each test."""
        # Use dummy credentials for testing
        self.notifier = PushoverNotifier(
            api_token="test_token",
            user_key="test_key",
            enabled=True
        )

    def test_notifier_initialization(self):
        """Test notifier initialization."""
        assert self.notifier.api_token == "test_token"
        assert self.notifier.user_key == "test_key"
        assert self.notifier.is_enabled()

    def test_notifier_disabled(self):
        """Test notifier disabled."""
        notifier = PushoverNotifier(enabled=False)
        assert not notifier.is_enabled()


def run_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PHASE 1 FOUNDATION TEST SUITE")
    print("=" * 70 + "\n")

    # Test database
    print("[OK] Testing Database...")
    db_test = TestDatabase()
    db_test.setup_method()
    db_test.test_database_creation()
    db_test.test_schema_initialization()
    db_test.test_save_analysis()
    db_test.test_approval_history()
    db_test.test_config_storage()
    db_test.test_health_check()
    print("   PASS: All database tests passed\n")

    # Test backup manager
    print("[OK] Testing Backup Manager...")
    backup_test = TestBackupManager()
    backup_test.setup_method()
    backup_test.test_get_current_commit()
    backup_test.test_get_branch_name()
    backup_test.test_diff_stats()
    print("   PASS: All backup manager tests passed\n")

    # Test JSON schemas
    print("[OK] Testing JSON Schemas...")
    schema_test = TestJsonSchemas()
    schema_test.test_analysis_schema()
    schema_test.test_recommendation_schema()
    schema_test.test_implementation_schema()
    schema_test.test_approval_schema()
    schema_test.test_audit_event_schema()
    print("   PASS: All schema tests passed\n")

    # Test audit logger
    print("[OK] Testing Audit Logger...")
    audit_test = TestAuditLogger()
    audit_test.setup_method()
    audit_test.test_log_event()
    audit_test.test_log_workflow_started()
    audit_test.test_export_audit_trail()
    audit_test.test_cycle_summary()
    print("   PASS: All audit logger tests passed\n")

    # Test Pushover notifier
    print("[OK] Testing Pushover Notifier...")
    notifier_test = TestPushoverNotifier()
    notifier_test.setup_method()
    notifier_test.test_notifier_initialization()
    notifier_test.test_notifier_disabled()
    print("   PASS: All Pushover notifier tests passed\n")

    print("=" * 70)
    print("[SUCCESS] ALL PHASE 1 FOUNDATION TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
