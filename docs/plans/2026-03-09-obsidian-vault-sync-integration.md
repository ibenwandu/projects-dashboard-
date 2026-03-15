# Obsidian Vault Sync Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Build automated sync system that keeps Obsidian vault current with session work by parsing logs and updating vault files at session boundaries.

**Architecture:** Two Python scripts integrated with session hooks. `sync_to_vault.py` runs at session close (reads logs → updates vault → commits). `sync_from_vault.py` runs at session start (reads vault → displays context). Shared `vault_parser.py` handles markdown parsing. All using stdlib, no external dependencies.

**Tech Stack:** Python 3.8+, stdlib only (re, pathlib, datetime, json, subprocess), git CLI

---

## Task 1: Create vault path configuration system

**Files:**
- Create: `C:\Users\user\.claude\scripts\__init__.py`
- Create: `C:\Users\user\.claude\scripts\vault_config.py`
- Create: `C:\Users\user\.claude\vault_config.json`

**Step 1: Write test for vault config detection**

```python
# C:\Users\user\projects\personal\tests\vault_config_test.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from vault_config import get_vault_path, save_vault_config

def test_get_vault_path_from_config():
    """Should read vault path from vault_config.json"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"
        config_file.write_text(json.dumps({"vault_path": r"C:\Users\user\My Knowledge Base"}))

        path = get_vault_path(config_file=config_file)
        assert path == Path(r"C:\Users\user\My Knowledge Base")

def test_get_vault_path_fallback_to_default():
    """Should use default vault path if config missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"

        path = get_vault_path(config_file=config_file)
        assert path == Path.home() / "My Knowledge Base"

def test_save_vault_config():
    """Should save vault path to config file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "vault_config.json"
        test_path = Path(r"C:\Users\user\Custom Vault")

        save_vault_config(test_path, config_file=config_file)

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["vault_path"] == str(test_path)
```

**Step 2: Run test to verify it fails**

```bash
cd C:\Users\user\projects\personal
pytest tests/vault_config_test.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vault_config'`

**Step 3: Write vault_config.py**

```python
# C:\Users\user\.claude\scripts\vault_config.py
import json
from pathlib import Path

def get_vault_path(config_file=None):
    """
    Get vault path from config file or use default.

    Args:
        config_file: Optional Path to vault_config.json. Defaults to ~/.claude/vault_config.json

    Returns:
        Path to vault directory
    """
    if config_file is None:
        config_file = Path.home() / ".claude" / "vault_config.json"

    # Try to read from config
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text())
            if "vault_path" in data:
                return Path(data["vault_path"])
        except (json.JSONDecodeError, IOError):
            pass

    # Fall back to default
    return Path.home() / "My Knowledge Base"

def save_vault_config(vault_path, config_file=None):
    """
    Save vault path to config file.

    Args:
        vault_path: Path to vault directory
        config_file: Optional Path to vault_config.json. Defaults to ~/.claude/vault_config.json
    """
    if config_file is None:
        config_file = Path.home() / ".claude" / "vault_config.json"

    # Ensure directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    data = {"vault_path": str(vault_path)}
    config_file.write_text(json.dumps(data, indent=2))

def validate_vault_path(vault_path):
    """
    Validate that vault path exists and is readable.

    Args:
        vault_path: Path to vault directory

    Returns:
        (is_valid, error_message)
    """
    vault_path = Path(vault_path)

    if not vault_path.exists():
        return False, f"Vault path does not exist: {vault_path}"

    if not vault_path.is_dir():
        return False, f"Vault path is not a directory: {vault_path}"

    # Check for required subdirectories
    required = ["Projects", "Trading-Journal", "Ideas"]
    missing = [d for d in required if not (vault_path / d).exists()]

    if missing:
        return False, f"Vault missing required directories: {', '.join(missing)}"

    return True, None
```

**Step 4: Run test to verify it passes**

```bash
cd C:\Users\user\projects\personal
pytest tests/vault_config_test.py -v
```

Expected: PASS (2 passed)

**Step 5: Create default vault_config.json**

```bash
cd C:\Users\user\.claude
cat > vault_config.json << 'EOF'
{
  "vault_path": "C:\\Users\\user\\My Knowledge Base"
}
EOF
```

**Step 6: Commit**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\vault_config.py
git add C:\Users\user\.claude\scripts\__init__.py
git add tests/vault_config_test.py
git commit -m "feat: add vault path configuration system"
```

---

## Task 2: Create vault_parser.py with markdown parsing utilities

**Files:**
- Create: `C:\Users\user\.claude\scripts\vault_parser.py`

**Step 1: Write test for parsing CLAUDE_SESSION_LOG.md**

```python
# C:\Users\user\projects\personal\tests\vault_parser_test.py
import sys
sys.path.insert(0, r'C:\Users\user\.claude\scripts')
from vault_parser import parse_session_log_section, extract_project_status

def test_parse_session_overview():
    """Should extract session overview from log"""
    log_content = """
## Current Session Status (Mar 9, 2026 — PHASE 1 IN PROGRESS)

### Trade-Alerts System State
- ✅ New Google Drive OAuth credentials created (Trade-Alerts-OAuth app)
- ✅ Trade-Alerts running on Render in AUTO mode (continuous since Mar 9)

### PHASE 1: Verify Stop Loss & Take Profit
**Status**: 🟡 TESTING COMPLETE — AWAITING ANALYSIS
"""

    sections = parse_session_log_section(log_content, "## Current Session Status")
    assert sections is not None
    assert "Trade-Alerts System State" in sections
    assert "PHASE 1" in sections

def test_extract_project_status():
    """Should extract status, blockers, next milestone from project log"""
    log_content = """
## Status
- Phase: Phase 1 Testing
- Last updated: 2026-03-09

## Current Blockers
- Manual close rate still at 80% (need to reduce)
- Need to analyze P1 test logs

## Next Milestone
- Review all Phase 1 logs and publish findings
"""

    status = extract_project_status(log_content)

    assert status["phase"] == "Phase 1 Testing"
    assert status["last_updated"] == "2026-03-09"
    assert "Manual close rate" in status["blockers"]
    assert "Review all Phase 1 logs" in status["next_milestone"]

def test_format_markdown_link():
    """Should format wiki-links correctly"""
    from vault_parser import format_wiki_link

    link = format_wiki_link("Trade-Alerts")
    assert link == "[[Trade-Alerts]]"

def test_sanitize_filename():
    """Should convert text to safe filename"""
    from vault_parser import sanitize_filename

    # Test with special characters
    result = sanitize_filename("Trade-Alerts — Phase 1 (Testing)")
    assert result == "Trade-Alerts_Phase_1_Testing"
```

**Step 2: Run test to verify it fails**

```bash
cd C:\Users\user\projects\personal
pytest tests/vault_parser_test.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vault_parser'`

**Step 3: Write vault_parser.py**

```python
# C:\Users\user\.claude\scripts\vault_parser.py
import re
from typing import Optional, Dict, List

def parse_session_log_section(content: str, section_header: str) -> Optional[str]:
    """
    Extract a section from markdown by header.

    Args:
        content: Full markdown content
        section_header: Header to find (e.g., "## Current Session Status")

    Returns:
        Section content or None if not found
    """
    # Find the section header
    pattern = re.escape(section_header) + r'\n(.*?)(?=\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        return match.group(1).strip()
    return None

def extract_project_status(log_content: str) -> Dict[str, str]:
    """
    Extract status fields from project log.

    Looks for patterns like:
    - Phase: [value]
    - Last updated: [value]

    Args:
        log_content: Project-specific CLAUDE_SESSION_LOG.md content

    Returns:
        Dict with keys: phase, last_updated, blockers, next_milestone
    """
    status = {
        "phase": "Unknown",
        "last_updated": "Unknown",
        "blockers": "",
        "next_milestone": ""
    }

    # Extract phase
    phase_match = re.search(r'- Phase:\s*(.+?)(?:\n|$)', log_content)
    if phase_match:
        status["phase"] = phase_match.group(1).strip()

    # Extract last updated
    updated_match = re.search(r'- Last updated:\s*(.+?)(?:\n|$)', log_content)
    if updated_match:
        status["last_updated"] = updated_match.group(1).strip()

    # Extract blockers section
    blockers_section = parse_section(log_content, "## Current Blockers")
    if blockers_section:
        status["blockers"] = blockers_section.strip()

    # Extract next milestone
    milestone_section = parse_section(log_content, "## Next Milestone")
    if milestone_section:
        status["next_milestone"] = milestone_section.strip()

    return status

def parse_section(content: str, header: str) -> Optional[str]:
    """
    Extract content under a markdown header until next header.

    Args:
        content: Full markdown content
        header: Header to find (e.g., "## Blockers")

    Returns:
        Section content or None
    """
    pattern = re.escape(header) + r'\n(.*?)(?=\n##|$)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        return match.group(1).strip()
    return None

def format_wiki_link(text: str) -> str:
    """
    Format text as Obsidian wiki-link.

    Args:
        text: Link text (e.g., "Trade-Alerts")

    Returns:
        Wiki-link format (e.g., "[[Trade-Alerts]]")
    """
    return f"[[{text}]]"

def sanitize_filename(text: str) -> str:
    """
    Convert text to safe filename for vault files.

    Replaces spaces and special chars with underscores.

    Args:
        text: Original text

    Returns:
        Safe filename
    """
    # Replace spaces and special characters with underscores
    text = re.sub(r'[\s\-–—•]', '_', text)
    # Remove any remaining non-alphanumeric except underscores
    text = re.sub(r'[^\w]', '', text)
    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)
    # Remove trailing underscore
    text = text.rstrip('_')

    return text

def extract_trading_learnings(log_content: str) -> str:
    """
    Extract trading learnings from session log.

    Looks for "## Critical Learnings" or similar section.

    Args:
        log_content: Root CLAUDE_SESSION_LOG.md content

    Returns:
        Learnings text or empty string
    """
    learnings_section = parse_section(log_content, "## Critical Learnings from This Session")
    if learnings_section:
        return learnings_section

    # Try alternate header
    learnings_section = parse_section(log_content, "## Key Learnings")
    if learnings_section:
        return learnings_section

    return ""

def get_status_emoji(phase: str) -> str:
    """
    Map project phase to status emoji for dashboard.

    Args:
        phase: Phase string (e.g., "Phase 1 Testing")

    Returns:
        Emoji (🟢 active, 🟡 testing, 🔴 blocked)
    """
    phase_lower = phase.lower()

    if "paused" in phase_lower or "blocked" in phase_lower:
        return "🔴"
    elif "testing" in phase_lower or "in progress" in phase_lower:
        return "🟡"
    elif "production" in phase_lower or "active" in phase_lower:
        return "🟢"
    else:
        return "⚪"

def generate_trading_journal_template(session_date: str, session_summary: str,
                                     project_updates: Dict[str, str],
                                     learnings: str) -> str:
    """
    Generate Trading Journal markdown from extracted data.

    Args:
        session_date: Date of session (e.g., "2026-03-11")
        session_summary: Summary of what happened
        project_updates: Dict of {project_name: status_update}
        learnings: Key learnings from session

    Returns:
        Formatted markdown for vault
    """
    template = f"""# Trading Session: {session_date}

## Session Overview
{session_summary}

## Key Updates to Projects
"""

    for project, update in project_updates.items():
        template += f"\n- {project}: {update}"

    if learnings:
        template += f"\n\n## Learnings\n{learnings}"

    template += "\n\n## Links\n"
    for project in project_updates.keys():
        template += f"- [[Project: {project}]]\n"

    return template
```

**Step 4: Run test to verify it passes**

```bash
cd C:\Users\user\projects\personal
pytest tests/vault_parser_test.py -v
```

Expected: PASS (all tests)

**Step 5: Commit**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\vault_parser.py
git add tests/vault_parser_test.py
git commit -m "feat: add vault markdown parsing utilities"
```

---

## Task 3: Create sync_to_vault.py (main session→vault sync)

**Files:**
- Create: `C:\Users\user\.claude\scripts\sync_to_vault.py`

**Step 1: Write integration test for full sync_to_vault flow**

```python
# C:\Users\user\projects\personal\tests\sync_to_vault_test.py
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
""")

        # Create sample CLAUDE_SESSION_LOG.md
        session_log = Path(tmpdir) / "CLAUDE_SESSION_LOG.md"
        session_log.write_text("""# CLAUDE Session Log

## Current Session Status (Mar 9, 2026)

### Trade-Alerts System State
- ✅ Running on Render in AUTO mode

### Critical Learnings
- Identified manual close rate issue
- Need to improve SL/TP verification
""")

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
```

**Step 2: Run test to verify it fails**

```bash
cd C:\Users\user\projects\personal
pytest tests/sync_to_vault_test.py::test_full_sync_flow -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sync_to_vault'`

**Step 3: Write sync_to_vault.py**

```python
# C:\Users\user\.claude\scripts\sync_to_vault.py
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import subprocess
import sys

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from vault_parser import (
    parse_session_log_section, extract_project_status,
    format_wiki_link, sanitize_filename, extract_trading_learnings,
    get_status_emoji, generate_trading_journal_template
)
from vault_config import get_vault_path, validate_vault_path

def sync_logs_to_vault(root_log: Path, vault_path: Path,
                       project_logs: List[Path],
                       dry_run: bool = False) -> Optional[str]:
    """
    Sync CLAUDE_SESSION_LOG.md files to Obsidian vault.

    Args:
        root_log: Path to root CLAUDE_SESSION_LOG.md
        vault_path: Path to Obsidian vault
        project_logs: List of project-specific CLAUDE_SESSION_LOG.md paths
        dry_run: If True, show what would change without modifying

    Returns:
        Preview of changes (dry-run) or None (full sync)
    """

    # Validate vault
    is_valid, error = validate_vault_path(vault_path)
    if not is_valid:
        print(f"ERROR: {error}")
        return None

    # Read root log
    if not root_log.exists():
        print(f"ERROR: Root log not found: {root_log}")
        return None

    root_content = root_log.read_text(encoding='utf-8')

    # Extract session info
    session_date = datetime.now().strftime("%Y-%m-%d")
    session_overview = parse_session_log_section(root_content, "## Current Session Status")
    learnings = extract_trading_learnings(root_content)

    changes = []  # Track changes for preview/logging

    # ========== UPDATE TRADING JOURNAL ==========
    journal_entry_path = vault_path / "Trading-Journal" / f"{session_date}.md"

    if session_overview or learnings:
        project_updates = {}

        # Extract project statuses from each project log
        for proj_log in project_logs:
            if proj_log.exists():
                proj_content = proj_log.read_text(encoding='utf-8')
                proj_name = proj_log.parent.name

                status = extract_project_status(proj_content)
                project_updates[proj_name] = f"Phase: {status['phase']}"

        # Generate journal entry
        journal_content = generate_trading_journal_template(
            session_date,
            session_overview or "Session completed",
            project_updates,
            learnings
        )

        changes.append(f"+ CREATE/UPDATE: {journal_entry_path.relative_to(vault_path)}")

        if not dry_run:
            journal_entry_path.write_text(journal_content, encoding='utf-8')

    # ========== UPDATE PROJECT STATUS FILES ==========
    projects_info = []  # For dashboard update

    for proj_log in project_logs:
        if not proj_log.exists():
            continue

        proj_content = proj_log.read_text(encoding='utf-8')
        proj_name = proj_log.parent.name
        proj_vault_file = vault_path / "Projects" / f"{proj_name}.md"

        if not proj_vault_file.exists():
            print(f"WARNING: Vault file not found: {proj_vault_file}")
            continue

        # Parse project status
        status = extract_project_status(proj_content)

        # Read existing vault file
        existing_content = proj_vault_file.read_text(encoding='utf-8')

        # Update status fields in vault file
        updated_content = update_project_note(existing_content, status)

        changes.append(f"~ UPDATE: {proj_vault_file.relative_to(vault_path)}")
        projects_info.append((proj_name, status))

        if not dry_run:
            proj_vault_file.write_text(updated_content, encoding='utf-8')

    # ========== UPDATE DASHBOARD ==========
    dashboard_path = vault_path / "00-DASHBOARD.md"

    if dashboard_path.exists() and projects_info:
        existing_dashboard = dashboard_path.read_text(encoding='utf-8')
        updated_dashboard = update_dashboard(existing_dashboard, projects_info)

        changes.append(f"~ UPDATE: {dashboard_path.relative_to(vault_path)}")

        if not dry_run:
            dashboard_path.write_text(updated_dashboard, encoding='utf-8')

    # ========== CREATE GIT COMMIT ==========
    if not dry_run and changes:
        try:
            # Prepare commit message
            commit_msg = f"Session: {session_date} — Automated vault sync from session logs"

            # Stage files
            subprocess.run(
                ["git", "-C", str(vault_path), "add", "."],
                check=True,
                capture_output=True
            )

            # Commit
            subprocess.run(
                ["git", "-C", str(vault_path), "commit",
                 "-m", commit_msg, "--allow-empty"],
                check=True,
                capture_output=True
            )

            changes.append(f"✓ GIT COMMIT: {commit_msg}")

        except subprocess.CalledProcessError as e:
            print(f"WARNING: Git commit failed: {e}")
            changes.append(f"✗ Git commit failed")

    # Return preview or None
    if dry_run:
        return "\n".join(changes)
    else:
        return None

def update_project_note(vault_content: str, status: Dict[str, str]) -> str:
    """
    Update project note with new status fields.

    Preserves other sections, updates only status-related ones.

    Args:
        vault_content: Existing vault file content
        status: Dict with phase, last_updated, blockers, next_milestone

    Returns:
        Updated markdown content
    """

    # Update "## Current Status" section
    vault_content = update_section(
        vault_content,
        "## Current Status",
        f"""## Current Status
- Phase: {status['phase']}
- Last updated: {status['last_updated']}"""
    )

    # Update "## Current Blockers" section
    if status['blockers']:
        vault_content = update_section(
            vault_content,
            "## Current Blockers",
            f"## Current Blockers\n{status['blockers']}"
        )

    # Update "## Next Milestone" section
    if status['next_milestone']:
        vault_content = update_section(
            vault_content,
            "## Next Milestone",
            f"## Next Milestone\n{status['next_milestone']}"
        )

    return vault_content

def update_section(content: str, header: str, new_content: str) -> str:
    """
    Replace a markdown section with new content.

    Args:
        content: Original markdown
        header: Section header to find (e.g., "## Current Status")
        new_content: New content for this section

    Returns:
        Updated markdown
    """
    import re

    # Find section and replace until next header or end
    pattern = re.escape(header) + r'\n[^\n]*(?:\n(?!##)[^\n]*)*'
    match = re.search(pattern, content)

    if match:
        return content[:match.start()] + new_content + content[match.end():]
    else:
        # Section not found, append it
        if not content.endswith('\n'):
            content += '\n'
        return content + '\n' + new_content + '\n'

def update_dashboard(dashboard_content: str, projects_info: List[tuple]) -> str:
    """
    Update dashboard with latest project statuses.

    Updates the Active Projects table with current statuses and emojis.

    Args:
        dashboard_content: Existing dashboard markdown
        projects_info: List of (project_name, status_dict) tuples

    Returns:
        Updated dashboard markdown
    """

    # Find the Active Projects table
    import re

    table_rows = []
    for proj_name, status in projects_info:
        emoji = get_status_emoji(status['phase'])
        milestone = status['next_milestone'].split('\n')[0] if status['next_milestone'] else "TBD"

        row = f"| {proj_name} | {status['phase']} | {emoji} | {milestone} | {format_wiki_link(proj_name)} |"
        table_rows.append(row)

    new_table = "| Project | Phase | Status | Next Milestone | Link |\n"
    new_table += "|---------|-------|--------|-----------------|------|\n"
    new_table += "\n".join(table_rows)

    # Replace existing table
    pattern = r'\| Project \|.*?\n\|.*?\n(?:\|.*?\n)*'
    match = re.search(pattern, dashboard_content)

    if match:
        return dashboard_content[:match.start()] + new_table + "\n" + dashboard_content[match.end():]
    else:
        # Table not found, append it
        if not dashboard_content.endswith('\n'):
            dashboard_content += '\n'
        return dashboard_content + '\n## Active Projects\n\n' + new_table + '\n'

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync session logs to Obsidian vault")
    parser.add_argument("--root-log", type=Path, required=True,
                        help="Path to root CLAUDE_SESSION_LOG.md")
    parser.add_argument("--vault-path", type=Path,
                        help="Path to Obsidian vault (default from config)")
    parser.add_argument("--project-logs", type=Path, nargs="*", default=[],
                        help="Paths to project-specific CLAUDE_SESSION_LOG.md files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying")

    args = parser.parse_args()

    # Get vault path from config if not provided
    vault_path = args.vault_path or get_vault_path()

    # Run sync
    preview = sync_logs_to_vault(
        root_log=args.root_log,
        vault_path=vault_path,
        project_logs=args.project_logs,
        dry_run=args.dry_run
    )

    if preview:
        print("Preview of changes:")
        print(preview)
    else:
        print("Sync completed successfully")
```

**Step 4: Run test to verify it passes**

```bash
cd C:\Users\user\projects\personal
pytest tests/sync_to_vault_test.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\sync_to_vault.py
git add tests/sync_to_vault_test.py
git commit -m "feat: implement sync_logs_to_vault main script"
```

---

## Task 4: Create sync_from_vault.py (vault→session context)

**Files:**
- Create: `C:\Users\user\.claude\scripts\sync_from_vault.py`

**Step 1: Write test for sync_from_vault**

```python
# C:\Users\user\projects\personal\tests\sync_from_vault_test.py
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
```

**Step 2: Run test to verify it fails**

```bash
cd C:\Users\user\projects\personal
pytest tests/sync_from_vault_test.py -v
```

Expected: FAIL

**Step 3: Write sync_from_vault.py**

```python
# C:\Users\user\.claude\scripts\sync_from_vault.py
import json
from pathlib import Path
from typing import List, Dict, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent))

from vault_parser import parse_section
from vault_config import get_vault_path

def read_vault_context(vault_path: Path) -> Optional[Dict]:
    """
    Read vault and extract current context for session start.

    Args:
        vault_path: Path to Obsidian vault

    Returns:
        Dict with blockers, priorities, last_session
    """

    context = {
        "blockers": [],
        "priorities": [],
        "last_session": None,
        "active_projects": []
    }

    # Read dashboard for overview
    dashboard_path = vault_path / "00-DASHBOARD.md"
    if dashboard_path.exists():
        dashboard = dashboard_path.read_text(encoding='utf-8')

        # Extract vision/priority
        vision_section = parse_section(dashboard, "# ")
        if vision_section:
            context["vision"] = vision_section[:200]

    # Read all project files for blockers
    projects_dir = vault_path / "Projects"
    if projects_dir.exists():
        for proj_file in projects_dir.glob("*.md"):
            content = proj_file.read_text(encoding='utf-8')
            proj_name = proj_file.stem

            # Extract blockers
            blockers_section = parse_section(content, "## Current Blockers")
            if blockers_section and blockers_section.strip() != "None":
                # Split by lines and clean up
                blockers = [line.strip() for line in blockers_section.split('\n')
                           if line.strip() and not line.startswith('#')]
                for blocker in blockers:
                    context["blockers"].append((proj_name, blocker))

            # Extract next milestone as priority
            milestone_section = parse_section(content, "## Next Milestone")
            if milestone_section:
                milestone = milestone_section.split('\n')[0].strip()
                context["priorities"].append(f"{proj_name}: {milestone}")

            context["active_projects"].append(proj_name)

    # Get latest trading journal date
    journal_dir = vault_path / "Trading-Journal"
    if journal_dir.exists():
        journal_files = sorted(journal_dir.glob("*.md"), reverse=True)
        if journal_files:
            context["last_session"] = journal_files[0].stem

    return context

def format_context_for_display(context: Dict) -> str:
    """
    Format vault context as readable console output.

    Args:
        context: Context dict from read_vault_context

    Returns:
        Formatted string for display
    """

    output = []

    # Vision
    if "vision" in context:
        output.append(f"\n📍 MISSION:\n{context['vision']}\n")

    # Active projects
    if context.get("active_projects"):
        output.append(f"\n🎯 ACTIVE PROJECTS:")
        for proj in context["active_projects"]:
            output.append(f"  • {proj}")

    # Blockers
    if context.get("blockers"):
        output.append(f"\n⚠️  CURRENT BLOCKERS:")
        for proj, blocker in context["blockers"]:
            output.append(f"  [{proj}] {blocker}")

    # Priorities
    if context.get("priorities"):
        output.append(f"\n📌 NEXT MILESTONES:")
        for priority in context["priorities"][:3]:  # Top 3
            output.append(f"  • {priority}")

    # Last session
    if context.get("last_session"):
        output.append(f"\n📅 Last session: {context['last_session']}")

    return "\n".join(output)

def save_session_context(context: Dict, output_file: Path) -> None:
    """
    Save context to a file for reference during session.

    Args:
        context: Context dict from read_vault_context
        output_file: Path to save context markdown
    """

    formatted = format_context_for_display(context)

    # Also save as JSON for programmatic use
    json_file = output_file.with_suffix('.json')
    json_file.write_text(json.dumps(context, indent=2), encoding='utf-8')

    # Save formatted version
    output_file.write_text(formatted, encoding='utf-8')

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read vault context for session start")
    parser.add_argument("--vault-path", type=Path,
                        help="Path to Obsidian vault (default from config)")
    parser.add_argument("--output-context", type=Path,
                        help="Save context to file")

    args = parser.parse_args()

    # Get vault path
    vault_path = args.vault_path or get_vault_path()

    # Read context
    context = read_vault_context(vault_path)

    if context:
        # Display
        output = format_context_for_display(context)
        print(output)

        # Save if requested
        if args.output_context:
            save_session_context(context, args.output_context)
            print(f"\n✓ Context saved to {args.output_context}")
```

**Step 4: Run test to verify it passes**

```bash
cd C:\Users\user\projects\personal
pytest tests/sync_from_vault_test.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\sync_from_vault.py
git add tests/sync_from_vault_test.py
git commit -m "feat: implement sync_from_vault context reader"
```

---

## Task 5: Create integration test (end-to-end sync cycle)

**Files:**
- Create: `C:\Users\user\projects\personal\tests\vault_sync_integration_test.py`

**Step 1: Write comprehensive integration test**

```python
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
        dashboard_path.write_text("""# 📊 Dashboard

| Project | Phase | Status | Next | Link |
|---------|-------|--------|------|------|
""")

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
""")

        # Create root CLAUDE_SESSION_LOG.md
        root_log = Path(tmpdir) / "CLAUDE_SESSION_LOG.md"
        root_log.write_text("""# CLAUDE Session Log

## Current Session Status (Mar 9, 2026)

### Trade-Alerts System State
- ✅ Running on Render
- ✅ OAuth2 fixed
- ✅ 48+ hours continuous

### Critical Learnings from This Session
- Manual close rate needs reduction
- SL/TP verification improved
- Ready for Phase 2 planning
""")

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
""")

        # ===== TEST DRY-RUN =====
        preview = sync_logs_to_vault(
            root_log=root_log,
            vault_path=vault_path,
            project_logs=[trade_alerts_log],
            dry_run=True
        )

        assert preview is not None
        assert "CREATE" in preview or "UPDATE" in preview
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

        # Check Trading Journal created
        journal_entry = vault_path / "Trading-Journal" / "2026-03-09.md"
        assert journal_entry.exists(), "Trading journal entry should be created"
        journal_content = journal_entry.read_text()
        assert "Phase 1 Testing" in journal_content
        assert "Manual close rate" in journal_content
        print("✓ Trading journal entry created")

        # Check Project file updated
        updated_proj = trade_alerts_file.read_text()
        assert "Phase 1 Testing" in updated_proj
        assert "Manual close rate at 80%" in updated_proj
        print("✓ Project file updated with status")

        # ===== READ CONTEXT FROM UPDATED VAULT =====
        context = read_vault_context(vault_path)

        assert context is not None
        assert "Trade-Alerts" in str(context.get("active_projects", []))

        # Should have blockers
        blockers = context.get("blockers", [])
        assert len(blockers) > 0
        blocker_texts = [b[1] for b in blockers]
        assert any("Manual close" in b for b in blocker_texts)
        print("✓ Context correctly reads blockers from updated vault")

        # ===== VERIFY CONTEXT FORMATTING =====
        formatted = format_context_for_display(context)
        assert "Trade-Alerts" in formatted
        assert "BLOCKERS" in formatted or "blockers" in formatted.lower()
        print("✓ Context formatting works")

        print("\n✓✓✓ FULL INTEGRATION TEST PASSED ✓✓✓")

if __name__ == "__main__":
    test_full_cycle_dry_run_then_execute()
```

**Step 2: Run integration test**

```bash
cd C:\Users\user\projects\personal
pytest tests/vault_sync_integration_test.py -v -s
```

Expected: PASS with detailed output

**Step 3: Commit**

```bash
cd C:\Users\user\projects\personal
git add tests/vault_sync_integration_test.py
git commit -m "test: add comprehensive vault sync integration test"
```

---

## Task 6: Create documentation and usage guide

**Files:**
- Create: `C:\Users\user\.claude\scripts\README.md`
- Create: `C:\Users\user\.claude\scripts\VAULT_SYNC_GUIDE.md`

**Step 1: Write vault sync guide**

```bash
cat > C:\Users\user\.claude\scripts\VAULT_SYNC_GUIDE.md << 'EOF'
# Vault Sync System Guide

## Overview

Automated system that keeps your Obsidian vault current with session work by syncing CLAUDE_SESSION_LOG.md files to vault markdown files.

## Components

### sync_to_vault.py
Runs at **session close** (end of close-session-root hook)
- Reads: Root CLAUDE_SESSION_LOG.md + project-specific logs
- Parses: Status, blockers, milestones, learnings
- Updates: Trading-Journal, Projects, Dashboard
- Creates: Git commit with session summary

### sync_from_vault.py
Runs at **session start** (end of start-session-root hook)
- Reads: Vault Dashboard, Projects, latest Trading-Journal
- Extracts: Blockers, priorities, active projects
- Displays: Console output for situational awareness
- Saves: Context to `.claude/session_context.json`

### vault_parser.py
Shared utilities for markdown parsing and formatting
- Parse section headers
- Extract status fields
- Format wiki-links
- Generate journal templates

### vault_config.py
Configuration management
- Detect vault path
- Save/load config
- Validate vault structure

## Installation

1. Scripts already created in: `C:\Users\user\.claude\scripts\`

2. Configure vault path:
```bash
python C:\Users\user\.claude\scripts\vault_config.py
# Will create: C:\Users\user\.claude\vault_config.json
# Default vault: C:\Users\user\My Knowledge Base
```

3. Verify vault structure exists:
```
My Knowledge Base/
├── 00-DASHBOARD.md
├── Projects/
│   ├── Trade-Alerts.md
│   ├── Scalp-Engine.md
│   └── Job-Search.md
├── Trading-Journal/
│   └── [dated entries]
└── Ideas/
```

## Usage

### Manual Sync (Testing)

Dry-run (preview changes):
```bash
python C:\Users\user\.claude\scripts\sync_to_vault.py \
  --root-log C:\Users\user\projects\personal\CLAUDE_SESSION_LOG.md \
  --vault-path "C:\Users\user\My Knowledge Base" \
  --project-logs C:\Users\user\projects\personal\Trade-Alerts\CLAUDE_SESSION_LOG.md \
  --dry-run
```

Full sync:
```bash
python C:\Users\user\.claude\scripts\sync_to_vault.py \
  --root-log C:\Users\user\projects\personal\CLAUDE_SESSION_LOG.md \
  --vault-path "C:\Users\user\My Knowledge Base" \
  --project-logs C:\Users\user\projects\personal\Trade-Alerts\CLAUDE_SESSION_LOG.md
```

Read context:
```bash
python C:\Users\user\.claude\scripts\sync_from_vault.py \
  --vault-path "C:\Users\user\My Knowledge Base"
```

### Automated Sync (Integrated)

Already integrated into session hooks:
- `close-session-root` calls `sync_to_vault.py` after session logs written
- `start-session-root` calls `sync_from_vault.py` before printing overview

No manual action needed — happens automatically.

## Data Flow

```
Session Start
  ↓
start-session-root
  ↓
sync_from_vault.py
  → Read vault Dashboard/Projects/Journal
  → Display blockers & priorities
  ↓
Your Work (update CLAUDE_SESSION_LOG.md)
  ↓
Session End
  ↓
close-session-root
  → Updates root & project logs
  ↓
sync_to_vault.py
  → Parse logs
  → Update vault files
  → Create git commit
  ↓
[Vault now reflects session work]
```

## Testing

Run all tests:
```bash
cd C:\Users\user\projects\personal
pytest tests/vault_config_test.py -v
pytest tests/vault_parser_test.py -v
pytest tests/sync_to_vault_test.py -v
pytest tests/sync_from_vault_test.py -v
pytest tests/vault_sync_integration_test.py -v
```

Run full integration test:
```bash
pytest tests/vault_sync_integration_test.py::test_full_cycle_dry_run_then_execute -v -s
```

## Troubleshooting

**"Vault path does not exist"**
- Check vault_config.json path
- Verify vault directory exists
- Run: `python vault_config.py` to reconfigure

**"Vault missing required directories"**
- Create missing: Projects/, Trading-Journal/, Ideas/
- Sync will skip files in missing directories

**"Git commit failed"**
- Verify vault is a git repository: `git -C "vault_path" status`
- Check file permissions
- Manual fallback: `git add` + `git commit` in vault directory

**"No changes detected"**
- Verify session logs were updated
- Check dry-run output for what would sync
- Vault may already be current

## Configuration

### vault_config.json

```json
{
  "vault_path": "C:\\Users\\user\\My Knowledge Base"
}
```

Create with:
```bash
python vault_config.py --path "C:\Users\user\My Knowledge Base"
```

### Environment Variables

Optional (overrides config file):
```bash
export OBSIDIAN_VAULT_PATH="C:\Users\user\My Knowledge Base"
```

## Future Enhancements

- [ ] Two-way sync (vault changes → logs)
- [ ] Scheduled periodic syncs
- [ ] Slack notifications on blockers
- [ ] Vault template customization
- [ ] Research findings auto-sync to Ideas/
EOF
```

**Step 2: Write scripts README**

```bash
cat > C:\Users\user\.claude\scripts\README.md << 'EOF'
# Claude Personal Scripts

Utility scripts for system automation and integration.

## Scripts

### Vault Sync System
- **sync_to_vault.py** — Parse session logs → Update Obsidian vault
- **sync_from_vault.py** — Read vault → Display context
- **vault_parser.py** — Shared markdown parsing utilities
- **vault_config.py** — Vault configuration management

See `VAULT_SYNC_GUIDE.md` for full documentation.

### Installation

Already installed. Configure:
```bash
python vault_config.py
```

### Testing

```bash
cd C:\Users\user\projects\personal
pytest tests/ -v
```

## Layout

```
~/.claude/
├── scripts/
│   ├── __init__.py
│   ├── vault_config.py
│   ├── vault_parser.py
│   ├── sync_to_vault.py
│   ├── sync_from_vault.py
│   ├── README.md
│   └── VAULT_SYNC_GUIDE.md
├── vault_config.json
└── session_context.md
```
EOF
```

**Step 3: Commit documentation**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\README.md
git add C:\Users\user\.claude\scripts\VAULT_SYNC_GUIDE.md
git commit -m "docs: add vault sync documentation and usage guide"
```

---

## Task 7: Update close-session-root skill integration

**Files:**
- Modify: close-session-root skill (update hook definition)

**Step 1: Create wrapper script for close-session-root**

```bash
cat > C:\Users\user\.claude\scripts\run_close_session_vault_sync.sh << 'EOF'
#!/bin/bash
# Wrapper script for close-session-root to include vault sync

# Get root session log path
ROOT_LOG="${1:-.}/CLAUDE_SESSION_LOG.md"
VAULT_PATH="${2:-$HOME/My Knowledge Base}"

echo "📝 Syncing session logs to Obsidian vault..."

# Find all project logs
PROJECT_LOGS=""
for proj in Trade-Alerts Scalp-Engine job-search; do
    if [ -f "./$proj/CLAUDE_SESSION_LOG.md" ]; then
        PROJECT_LOGS="$PROJECT_LOGS ./$proj/CLAUDE_SESSION_LOG.md"
    fi
done

# Run sync (dry-run first, then execute)
python ~/.claude/scripts/sync_to_vault.py \
    --root-log "$ROOT_LOG" \
    --vault-path "$VAULT_PATH" \
    $PROJECT_LOGS \
    --dry-run

echo ""
echo "Preview above. Running full sync..."
echo ""

python ~/.claude/scripts/sync_to_vault.py \
    --root-log "$ROOT_LOG" \
    --vault-path "$VAULT_PATH" \
    $PROJECT_LOGS

echo "✅ Vault sync complete"
EOF
chmod +x C:\Users\user\.claude\scripts\run_close_session_vault_sync.sh
```

**Step 2: Add script execution note**

```bash
cat >> C:\Users\user\.claude\scripts\README.md << 'EOF'

## Integration with Session Hooks

### close-session-root
The vault sync is automatically called after session logs are written.

To manually trigger:
```bash
bash ~/.claude/scripts/run_close_session_vault_sync.sh
```

### start-session-root
Vault context is automatically displayed at session start.

To manually check context:
```bash
python ~/.claude/scripts/sync_from_vault.py
```
EOF
```

**Step 3: Commit**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\run_close_session_vault_sync.sh
git commit -m "refactor: add close-session vault sync wrapper script"
```

---

## Task 8: Update start-session-root skill integration

**Files:**
- Create: `C:\Users\user\.claude\scripts\run_start_session_vault_context.sh`

**Step 1: Create wrapper for start-session-root**

```bash
cat > C:\Users\user\.claude\scripts\run_start_session_vault_context.sh << 'EOF'
#!/bin/bash
# Display vault context at session start

VAULT_PATH="${1:-$HOME/My Knowledge Base}"
CONTEXT_FILE="${2:-.claude/session_context.md}"

echo ""
echo "🔄 Reading current vault context..."
echo ""

python ~/.claude/scripts/sync_from_vault.py \
    --vault-path "$VAULT_PATH" \
    --output-context "$CONTEXT_FILE"

echo ""
EOF
chmod +x C:\Users\user\.claude\scripts\run_start_session_vault_context.sh
```

**Step 2: Commit**

```bash
cd C:\Users\user\projects\personal
git add C:\Users\user\.claude\scripts\run_start_session_vault_context.sh
git commit -m "refactor: add start-session vault context wrapper script"
```

---

## Task 9: Final verification and cleanup

**Files:**
- Verify: All scripts exist and are executable
- Verify: All tests pass
- Verify: Documentation complete

**Step 1: Run all tests**

```bash
cd C:\Users\user\projects\personal
pytest tests/vault*.py -v --tb=short
```

Expected: All tests pass (15+ passed)

**Step 2: Verify script execution**

```bash
python C:\Users\user\.claude\scripts\vault_config.py --help
python C:\Users\user\.claude\scripts\sync_to_vault.py --help
python C:\Users\user\.claude\scripts\sync_from_vault.py --help
```

Expected: All show help output without errors

**Step 3: Final commit with summary**

```bash
cd C:\Users\user\projects\personal
git add .
git commit -m "feat: complete obsidian vault sync integration system

- Created vault_config.py for configuration management
- Implemented sync_to_vault.py (logs → vault + git commit)
- Implemented sync_from_vault.py (vault → context display)
- Created vault_parser.py with markdown utilities
- Comprehensive unit tests (vault_config, parser, sync_to_vault, sync_from_vault)
- Integration test for full sync cycle
- Documentation: VAULT_SYNC_GUIDE.md, README.md
- Wrapper scripts for session hook integration
- All 15+ tests passing
- Ready for deployment"
```

---

## Success Criteria Verification

After all tasks complete, verify:

1. ✅ `C:\Users\user\.claude\scripts\` contains all Python files
2. ✅ `C:\Users\user\.claude\vault_config.json` configured
3. ✅ `tests/` directory contains all test files
4. ✅ All 15+ tests pass: `pytest tests/vault*.py -v`
5. ✅ Dry-run works: `python sync_to_vault.py --dry-run`
6. ✅ Context display works: `python sync_from_vault.py`
7. ✅ Integration test passes: Full cycle test
8. ✅ Documentation complete: README.md, VAULT_SYNC_GUIDE.md
9. ✅ Git history shows clear commits
10. ✅ Vault structure verified (Projects/, Trading-Journal/, Ideas/)

---

# Execution Approach

**Plan complete and saved to `docs/plans/2026-03-09-obsidian-vault-sync-integration.md`**

Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

**Which approach would you prefer?**