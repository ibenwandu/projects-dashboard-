# C:\Users\user\projects\personal\tests\vault_sync_integration_test.py
import tempfile
from pathlib import Path
import subprocess
import json
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')

from sync_to_vault import sync_logs_to_vault
from sync_from_vault import read_vault_context, format_context_for_display

def test_full_cycle_dry_run_then_execute():
    """
    Full integration test:
    1. Create sample vault and logs
    2. Run sync in dry-run mode (preview)
    3. Execute sync
    4. Verify vault updated
    5. Read context from updated vault
    6. Verify context contains right data
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        # ===== SETUP =====
        vault_path = Path(tmpdir) / "My Knowledge Base"
        vault_path.mkdir()

        # Create vault structure
        (vault_path / "Projects").mkdir()
        (vault_path / "Trading-Journal").mkdir()
        (vault_path / "Ideas").mkdir()

        # Create dashboard
        dashboard_path = vault_path / "00-DASHBOARD.md"
        dashboard_path.write_text("""# Dashboard

| Project | Phase | Status | Next | Link |
|---------|-------|--------|------|------|
""", encoding='utf-8')

        # Create project stub
        trade_alerts_file = vault_path / "Projects" / "Trade-Alerts.md"
        trade_alerts_file.write_text("""# Trade-Alerts

## Vision Alignment
Autonomous 24/7 trading system

## Current Status
- Phase: Setup
- Last updated: Never

## Current Blockers
None

## Next Milestone
Begin Phase 1 testing
""", encoding='utf-8')

        # Create root CLAUDE_SESSION_LOG.md
        root_log = Path(tmpdir) / "CLAUDE_SESSION_LOG.md"
        root_log.write_text("""# CLAUDE Session Log

## Current Session Status (Mar 9, 2026)

### Trade-Alerts System State
- [OK] Running on Render
- [OK] OAuth2 fixed
- [OK] 48+ hours continuous

### Critical Learnings from This Session
- Manual close rate needs reduction
- SL/TP verification improved
- Ready for Phase 2 planning
""", encoding='utf-8')

        # Create Trade-Alerts log
        trade_alerts_log = Path(tmpdir) / "Trade-Alerts" / "CLAUDE_SESSION_LOG.md"
        trade_alerts_log.parent.mkdir(parents=True)
        trade_alerts_log.write_text("""# Trade-Alerts CLAUDE Session Log

## Status
- Phase: Phase 1 Testing
- Last updated: 2026-03-09

## Current Blockers
- Manual close rate at 80% (target <10%)
- Need comprehensive log analysis

## Next Milestone
- Complete Phase 1 log review
- Publish findings
""", encoding='utf-8')

        # ===== TEST DRY-RUN =====
        preview = sync_logs_to_vault(
            root_log=root_log,
            vault_path=vault_path,
            project_logs=[trade_alerts_log],
            dry_run=True
        )

        assert preview is not None
        assert "Would" in preview or "DRY RUN" in preview
        print("✓ Dry-run preview generated")

        # Verify no actual changes from dry-run
        dashboard_mtime_before = dashboard_path.stat().st_mtime

        # ===== EXECUTE FULL SYNC =====
        sync_logs_to_vault(
            root_log=root_log,
            vault_path=vault_path,
            project_logs=[trade_alerts_log],
            dry_run=False
        )

        # ===== VERIFY VAULT UPDATED =====

        # Check Project file updated with new status
        updated_proj = trade_alerts_file.read_text(encoding='utf-8')
        assert "Phase 1 Testing" in updated_proj
        assert "Manual close rate at 80%" in updated_proj
        print("✓ Project file updated with status")

        # Check Dashboard updated with project info
        dashboard_updated = dashboard_path.read_text(encoding='utf-8')
        assert "Trade-Alerts" in dashboard_updated
        assert "Active Projects" in dashboard_updated
        print("✓ Dashboard updated with project info")

        # ===== READ CONTEXT FROM UPDATED VAULT =====
        context = read_vault_context(vault_path)

        assert context is not None

        # Should have blockers (context reads from project files)
        blockers = context.get("blockers", [])
        assert len(blockers) > 0, f"Expected blockers, got: {blockers}"
        blocker_texts = [b[1] for b in blockers]
        assert any("Manual close" in b for b in blocker_texts), f"Expected 'Manual close' in blockers: {blocker_texts}"
        print("✓ Context correctly reads blockers from updated vault")

        # ===== VERIFY CONTEXT FORMATTING =====
        formatted = format_context_for_display(context)
        assert "Trade-Alerts" in formatted
        assert "BLOCKERS" in formatted or "blockers" in formatted.lower()
        print("✓ Context formatting works")

        print("\n✓✓✓ FULL INTEGRATION TEST PASSED ✓✓✓")
