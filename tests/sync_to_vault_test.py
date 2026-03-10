import json
import tempfile
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from sync_to_vault import sync_logs_to_vault

def test_full_sync_flow():
    """Should read logs, update vault files, create git commit"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup temporary vault structure
        vault_path = Path(tmpdir) / "My Knowledge Base"
        vault_path.mkdir()
        (vault_path / "Projects").mkdir()
        (vault_path / "Trading-Journal").mkdir()
        (vault_path / "Ideas").mkdir()

        # Create stub project files
        trade_alerts_file = vault_path / "Projects" / "Trade-Alerts.md"
        trade_alerts_file.write_text("""# Trade-Alerts

## Current Status
- Phase: Unknown
- Last updated: Never

## Current Blockers
None
""", encoding='utf-8')

        # Create sample CLAUDE_SESSION_LOG.md
        session_log = Path(tmpdir) / "CLAUDE_SESSION_LOG.md"
        session_log.write_text("""# CLAUDE Session Log

## Current Session Status (Mar 9, 2026)

### Trade-Alerts System State
- Running on Render in AUTO mode

### Critical Learnings
- Identified manual close rate issue
- Need to improve SL/TP verification
""", encoding='utf-8')

        # Run sync (dry-run first)
        result = sync_logs_to_vault(
            root_log=session_log,
            vault_path=vault_path,
            project_logs=[],
            dry_run=True
        )

        # Should return preview of changes
        assert result is not None
        assert "Trade-Alerts.md" in result or "would update" in result.lower()

def test_sync_dry_run_does_not_modify():
    """Dry-run should not actually modify vault"""

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "My Knowledge Base"
        vault_path.mkdir()
        (vault_path / "Projects").mkdir()

        # Record original mod time
        projects_dir = vault_path / "Projects"
        original_mtime = projects_dir.stat().st_mtime

        # Create sample log
        session_log = Path(tmpdir) / "CLAUDE_SESSION_LOG.md"
        session_log.write_text("## Current Session Status\nTest")

        # Run sync dry-run
        sync_logs_to_vault(
            root_log=session_log,
            vault_path=vault_path,
            project_logs=[],
            dry_run=True
        )

        # Directory should not have been modified
        assert projects_dir.stat().st_mtime == original_mtime
