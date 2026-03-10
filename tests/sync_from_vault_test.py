import tempfile
from pathlib import Path
import json
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from sync_from_vault import read_vault_context, format_context_for_display

def test_read_vault_context():
    """Should read dashboard and extract current blockers"""

    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "My Knowledge Base"
        vault_path.mkdir()
        (vault_path / "Projects").mkdir()

        # Create sample project file
        proj_file = vault_path / "Projects" / "Trade-Alerts.md"
        proj_file.write_text("""# Trade-Alerts

## Current Status
- Phase: Phase 1 Testing
- Last updated: 2026-03-09

## Current Blockers
- Manual close rate at 80%
- Need log analysis
""")

        # Read context
        context = read_vault_context(vault_path)

        assert context is not None
        assert "Trade-Alerts" in str(context)
        assert "blockers" in str(context).lower()

def test_format_context_for_display():
    """Should format context nicely for console display"""

    context = {
        "blockers": [
            ("Trade-Alerts", "Manual close rate at 80%"),
            ("Scalp-Engine", "Need to improve win rate")
        ],
        "last_session": "2026-03-09",
        "priorities": ["Review Phase 1 logs"]
    }

    formatted = format_context_for_display(context)

    assert "Trade-Alerts" in formatted
    assert "Manual close rate" in formatted
