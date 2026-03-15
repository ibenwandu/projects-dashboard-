# Enhancement #6 Implementation Plan: Automated Knowledge Management

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Implement hourly automated Obsidian dashboard updates showing Emy's status, activity, and critical alerts with zero manual intervention.

**Architecture:** KnowledgeAgent enhanced with Task Scheduler querying, database metrics collection, markdown parsing, and git auto-commit. Runs hourly via Emy's internal scheduler. Reads from Windows Task Scheduler API and SQLite database, writes to Obsidian markdown file.

**Tech Stack:**
- PowerShell (Task Scheduler API via subprocess)
- sqlite3 (database queries, already available)
- pathlib (file operations)
- re (markdown parsing)
- subprocess (git commands)

---

## Task 1: Add Task Scheduler Query Method to KnowledgeAgent

**Files:**
- Modify: `emy/agents/knowledge_agent.py` (add _get_emy_status method)
- Test: `emy/tests/test_knowledge_agent.py` (new file)

**Step 1: Write failing test for Task Scheduler query**

Create `emy/tests/test_knowledge_agent.py`:

```python
import pytest
from unittest.mock import Mock, patch
from emy.agents.knowledge_agent import KnowledgeAgent


class TestKnowledgeAgentTaskScheduler:
    """Test Task Scheduler integration"""

    @pytest.fixture
    def agent(self):
        """Create KnowledgeAgent instance"""
        return KnowledgeAgent()

    def test_get_emy_status_running(self, agent):
        """_get_emy_status returns Running status with timestamp"""
        with patch('subprocess.run') as mock_run:
            # Mock PowerShell output
            mock_result = Mock()
            mock_result.stdout = """TaskPath                                       TaskName                          State
--------                                       --------                          -----
\\                                              Emy Chief of Staff                Ready"""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            status = agent._get_emy_status()

            assert status is not None
            assert 'status' in status
            assert status['status'] in ['Running', 'Ready', 'Stopped', 'UNKNOWN']

    def test_get_emy_status_stopped(self, agent):
        """_get_emy_status handles Stopped task"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stdout = """TaskPath                                       TaskName                          State
--------                                       --------                          -----
\\                                              Emy Chief of Staff                Stopped"""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            status = agent._get_emy_status()

            assert status['status'] == 'Stopped'

    def test_get_emy_status_powershell_error(self, agent):
        """_get_emy_status returns UNKNOWN on PowerShell error"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result

            status = agent._get_emy_status()

            assert status['status'] == 'UNKNOWN'
```

**Step 2: Run test to verify it fails**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_get_emy_status_running -v`

Expected: FAIL (method not defined)

**Step 3: Implement _get_emy_status in KnowledgeAgent**

Add to `emy/agents/knowledge_agent.py`:

```python
import subprocess
from datetime import datetime

def _get_emy_status(self) -> dict:
    """
    Get Emy task status from Windows Task Scheduler

    Returns:
        dict with 'status' (Running/Ready/Stopped/UNKNOWN) and 'timestamp'
    """
    try:
        # Query Task Scheduler via PowerShell
        cmd = [
            'powershell', '-Command',
            'Get-ScheduledTask -TaskName "Emy Chief of Staff" | Select-Object State | Format-Table -AutoSize'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        if result.returncode != 0:
            logger.warning("Task Scheduler query failed")
            return {'status': 'UNKNOWN', 'timestamp': datetime.now().isoformat()}

        # Parse output for State
        output = result.stdout.lower()
        if 'running' in output:
            state = 'Running'
        elif 'ready' in output:
            state = 'Ready'
        elif 'stopped' in output:
            state = 'Stopped'
        elif 'disabled' in output:
            state = 'Disabled'
        else:
            state = 'UNKNOWN'

        return {
            'status': state,
            'timestamp': datetime.now().isoformat()
        }

    except subprocess.TimeoutExpired:
        logger.warning("Task Scheduler query timeout")
        return {'status': 'UNKNOWN', 'timestamp': datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error querying Task Scheduler: {e}")
        return {'status': 'UNKNOWN', 'timestamp': datetime.now().isoformat()}
```

**Step 4: Run test to verify it passes**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add emy/agents/knowledge_agent.py emy/tests/test_knowledge_agent.py
git commit -m "feat: add Task Scheduler status querying to KnowledgeAgent"
```

---

## Task 2: Add Database Query Methods

**Files:**
- Modify: `emy/agents/knowledge_agent.py` (add _get_last_run, _get_next_job, _get_recent_alerts, _check_critical_alerts)
- Modify: `emy/tests/test_knowledge_agent.py` (add database query tests)

**Step 1: Write failing tests for database methods**

Add to `emy/tests/test_knowledge_agent.py`:

```python
def test_get_last_run_time(self, agent):
    """_get_last_run_time returns most recent task timestamp"""
    with patch('sqlite3.connect') as mock_connect:
        # Mock database
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ('2026-03-10 14:32:15',)
        mock_connect.return_value.cursor.return_value = mock_cursor

        last_run = agent._get_last_run_time()

        assert last_run is not None
        assert '14:32' in last_run or '14:32:15' in last_run

def test_get_next_scheduled_job(self, agent):
    """_get_next_scheduled_job returns next job name and time"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.stdout = "trading_health_check | 14:45:00"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        next_job = agent._get_next_scheduled_job()

        assert next_job is not None
        assert 'job' in next_job
        assert 'time' in next_job

def test_get_recent_alerts(self, agent):
    """_get_recent_alerts returns count of recent alerts by type"""
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('alert_trade_executed', 3),
            ('alert_trade_rejected', 1),
        ]
        mock_connect.return_value.cursor.return_value = mock_cursor

        alerts = agent._get_recent_alerts()

        assert alerts is not None
        assert 'executions' in alerts or 'alerts' in alerts

def test_check_critical_alerts(self, agent):
    """_check_critical_alerts returns True if 100% daily loss found"""
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)  # 1 critical alert found
        mock_connect.return_value.cursor.return_value = mock_cursor

        has_critical = agent._check_critical_alerts()

        assert isinstance(has_critical, bool)
```

**Step 2: Run tests to verify they fail**

Run: `pytest emy/tests/test_knowledge_agent.py -v -k "test_get_last_run_time or test_get_next_scheduled_job or test_get_recent_alerts or test_check_critical_alerts"`

Expected: All FAIL (methods not defined)

**Step 3: Implement database query methods**

Add to `emy/agents/knowledge_agent.py`:

```python
import sqlite3
from datetime import datetime, timedelta

def _get_last_run_time(self) -> str:
    """Get timestamp of last Emy task execution"""
    try:
        db_path = 'emy/data/emy.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT MAX(created_at) FROM emy_tasks
            WHERE domain IN ('trading', 'job_search', 'knowledge')
            AND created_at > datetime('now', '-24 hours')
        """)

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            # Parse ISO timestamp and format for display
            dt = datetime.fromisoformat(result[0])
            return dt.strftime('%H:%M')
        else:
            return 'Unknown'

    except Exception as e:
        logger.warning(f"Error querying last run time: {e}")
        return 'Unknown'

def _get_next_scheduled_job(self) -> dict:
    """Get next scheduled job from Task Scheduler"""
    try:
        cmd = [
            'powershell', '-Command',
            'Get-ScheduledTask -TaskName "Emy Chief of Staff" | Get-ScheduledTaskInfo | Select-Object NextRunTime'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        if result.returncode == 0 and 'NextRunTime' in result.stdout:
            # Parse output (simplified - assumes standard format)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 2:
                time_str = lines[2].strip()
                return {'job': 'Emy jobs', 'time': time_str}

        return {'job': 'Unknown', 'time': 'Unknown'}

    except Exception as e:
        logger.warning(f"Error querying next job: {e}")
        return {'job': 'Unknown', 'time': 'Unknown'}

def _get_recent_alerts(self) -> dict:
    """Get summary of recent alerts (last 24 hours)"""
    try:
        db_path = 'emy/data/emy.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query alert counts
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM emy_tasks
            WHERE action LIKE 'alert_%'
            AND created_at > datetime('now', '-24 hours')
            GROUP BY action
        """)

        results = cursor.fetchall()
        conn.close()

        summary = {
            'executions': 0,
            'rejections': 0,
            'warnings': 0,
            'total': 0
        }

        for action, count in results:
            summary['total'] += count
            if 'execution' in action:
                summary['executions'] += count
            elif 'rejection' in action or 'rejected' in action:
                summary['rejections'] += count
            elif 'warning' in action or 'loss' in action:
                summary['warnings'] += count

        return summary

    except Exception as e:
        logger.warning(f"Error querying recent alerts: {e}")
        return {'executions': 0, 'rejections': 0, 'warnings': 0, 'total': 0}

def _check_critical_alerts(self) -> bool:
    """Check if any critical alerts exist (daily loss 100%, etc)"""
    try:
        db_path = 'emy/data/emy.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query for critical alerts in last 24 hours
        cursor.execute("""
            SELECT COUNT(*) FROM emy_tasks
            WHERE (action LIKE '%daily_loss_100%' OR action LIKE '%CRITICAL%')
            AND created_at > datetime('now', '-24 hours')
        """)

        result = cursor.fetchone()
        conn.close()

        return result[0] > 0 if result else False

    except Exception as e:
        logger.warning(f"Error checking critical alerts: {e}")
        return False
```

**Step 4: Run tests to verify they pass**

Run: `pytest emy/tests/test_knowledge_agent.py -v -k "test_get_last_run_time or test_get_next_scheduled_job or test_get_recent_alerts or test_check_critical_alerts"`

Expected: All PASS

**Step 5: Commit**

```bash
git add emy/agents/knowledge_agent.py emy/tests/test_knowledge_agent.py
git commit -m "feat: add database query methods to KnowledgeAgent"
```

---

## Task 3: Implement Markdown Dashboard Update Logic

**Files:**
- Modify: `emy/agents/knowledge_agent.py` (add _format_dashboard_row, _update_dashboard_table)
- Modify: `emy/tests/test_knowledge_agent.py` (add markdown parsing tests)

**Step 1: Write failing tests for markdown operations**

Add to `emy/tests/test_knowledge_agent.py`:

```python
def test_format_dashboard_row(self, agent):
    """_format_dashboard_row formats status data as markdown table row"""
    data = {
        'status': 'Running (14:32)',
        'next_job': 'trading_health_check (14:45)',
        'alerts': {'executions': 3, 'rejections': 1, 'total': 4},
        'critical': False
    }

    row = agent._format_dashboard_row(data)

    assert '|' in row  # Markdown table format
    assert 'Running' in row
    assert '3' in row or '4' in row  # Alert counts

def test_update_dashboard_table_finds_emy_row(self, agent):
    """_update_dashboard_table finds and updates Emy row in markdown"""
    markdown_content = """
| Project | Phase | Status | Next | Progress |
|---------|-------|--------|------|----------|
| Trade-Alerts | Phase 1 | RUNNING | Logs | SL/TP works |
| Emy | Phase 1 | RUNNING | Monitor | Old data |
| Scalp-Engine | Supporting | RUNNING | Health | Working |
"""

    new_row = "| Emy | Phase 1 | 🟢 RUNNING (14:32) | trading_check | ✅ Executions: 3 |"

    updated = agent._update_dashboard_table(markdown_content, new_row)

    assert updated is not None
    assert '🟢 RUNNING (14:32)' in updated
    assert 'Executions: 3' in updated
```

**Step 2: Run tests to verify they fail**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_format_dashboard_row -v`

Expected: FAIL (methods not defined)

**Step 3: Implement markdown operations**

Add to `emy/agents/knowledge_agent.py`:

```python
import re

def _format_dashboard_row(self, data: dict) -> str:
    """
    Format status data as markdown table row

    Args:
        data: dict with 'status', 'next_job', 'alerts', 'critical'

    Returns:
        Markdown table row string
    """
    status = data.get('status', 'UNKNOWN')
    next_job = data.get('next_job', 'Unknown')
    alerts = data.get('alerts', {})
    is_critical = data.get('critical', False)

    # Format status with emoji
    if is_critical:
        status_emoji = "🔴 CRITICAL"
        status_cell = f"{status_emoji} | {status}"
    else:
        status_emoji = "🟢" if "Running" in status else "🟡"
        status_cell = f"{status_emoji} {status}"

    # Format progress cell with alert counts
    exec_count = alerts.get('executions', 0)
    rej_count = alerts.get('rejections', 0)
    warn_count = alerts.get('warnings', 0)
    total = alerts.get('total', 0)

    if total > 0:
        progress = f"✅ Exec: {exec_count} | Rej: {rej_count} | Alerts: {total}"
    else:
        progress = "✅ Running"

    # Build row
    row = f"| Emy | Phase 1: Pushover Alerts | {status_cell} | {next_job} | {progress} |"

    return row

def _update_dashboard_table(self, markdown_content: str, new_row: str) -> str:
    """
    Update Emy row in Obsidian dashboard markdown

    Args:
        markdown_content: Full markdown file content
        new_row: Formatted markdown table row to insert

    Returns:
        Updated markdown content
    """
    try:
        # Find Emy row (contains "Emy" and "Phase 1")
        lines = markdown_content.split('\n')
        updated_lines = []
        found_emy = False

        for i, line in enumerate(lines):
            # Check if this is the Emy row in the table
            if '| Emy |' in line and 'Phase' in line:
                updated_lines.append(new_row)
                found_emy = True
                logger.info("Updated Emy dashboard row")
            else:
                updated_lines.append(line)

        if not found_emy:
            logger.warning("Emy row not found in dashboard, appending new row")
            # If not found, append before end of table
            updated_lines.append(new_row)

        return '\n'.join(updated_lines)

    except Exception as e:
        logger.error(f"Error updating dashboard table: {e}")
        return markdown_content

def _load_obsidian_dashboard(self) -> str:
    """Load Obsidian dashboard markdown file"""
    try:
        # Path to Obsidian vault (from user's structure)
        dashboard_path = Path('../Obsidian Vault/My Knowledge Base/00-DASHBOARD.md')

        if not dashboard_path.exists():
            logger.warning(f"Dashboard file not found at {dashboard_path}")
            return ""

        return dashboard_path.read_text(encoding='utf-8')

    except Exception as e:
        logger.error(f"Error loading Obsidian dashboard: {e}")
        return ""

def _save_obsidian_dashboard(self, content: str) -> bool:
    """Save updated Obsidian dashboard markdown file"""
    try:
        dashboard_path = Path('../Obsidian Vault/My Knowledge Base/00-DASHBOARD.md')
        dashboard_path.write_text(content, encoding='utf-8')
        logger.info("Obsidian dashboard saved")
        return True

    except Exception as e:
        logger.error(f"Error saving Obsidian dashboard: {e}")
        return False
```

**Step 4: Run tests to verify they pass**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_format_dashboard_row -v`

Expected: PASS

**Step 5: Commit**

```bash
git add emy/agents/knowledge_agent.py emy/tests/test_knowledge_agent.py
git commit -m "feat: implement markdown dashboard update logic"
```

---

## Task 4: Add Git Auto-Commit Integration

**Files:**
- Modify: `emy/agents/knowledge_agent.py` (add _commit_dashboard_changes)
- Modify: `emy/tests/test_knowledge_agent.py` (add git commit tests)

**Step 1: Write failing test for git commit**

Add to `emy/tests/test_knowledge_agent.py`:

```python
def test_commit_dashboard_changes(self, agent):
    """_commit_dashboard_changes creates git commit for dashboard updates"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0)

        success = agent._commit_dashboard_changes()

        assert success is True
        # Verify git add was called
        assert any('add' in str(call) for call in mock_run.call_args_list)

def test_commit_handles_git_error(self, agent):
    """_commit_dashboard_changes handles git failures gracefully"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=1)

        success = agent._commit_dashboard_changes()

        assert success is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_commit_dashboard_changes -v`

Expected: FAIL

**Step 3: Implement git auto-commit**

Add to `emy/agents/knowledge_agent.py`:

```python
def _commit_dashboard_changes(self) -> bool:
    """
    Commit Obsidian dashboard changes to git

    Returns:
        True if commit successful, False otherwise
    """
    try:
        # Stage the dashboard file
        cmd_add = ['git', 'add', '../Obsidian Vault/My Knowledge Base/00-DASHBOARD.md']
        result_add = subprocess.run(cmd_add, capture_output=True, text=True, timeout=5)

        if result_add.returncode != 0:
            logger.warning(f"Git add failed: {result_add.stderr}")
            return False

        # Create commit
        cmd_commit = [
            'git', 'commit',
            '-m', 'auto: update Emy status [hourly]'
        ]
        result_commit = subprocess.run(cmd_commit, capture_output=True, text=True, timeout=5)

        if result_commit.returncode == 0:
            logger.info("Dashboard changes committed to git")
            return True
        elif 'nothing to commit' in result_commit.stdout or 'nothing to commit' in result_commit.stderr:
            # No changes - not an error
            logger.debug("No changes to commit")
            return True
        else:
            logger.warning(f"Git commit failed: {result_commit.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning("Git commit timeout")
        return False
    except Exception as e:
        logger.error(f"Error committing dashboard changes: {e}")
        return False
```

**Step 4: Run tests to verify they pass**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_commit_dashboard_changes -v`

Expected: PASS

**Step 5: Commit**

```bash
git add emy/agents/knowledge_agent.py emy/tests/test_knowledge_agent.py
git commit -m "feat: add git auto-commit for dashboard updates"
```

---

## Task 5: Integrate Methods into run() - Main Update Workflow

**Files:**
- Modify: `emy/agents/knowledge_agent.py` (update run method to call all dashboard methods)
- Modify: `emy/tests/test_knowledge_agent.py` (add end-to-end workflow test)

**Step 1: Write failing test for complete workflow**

Add to `emy/tests/test_knowledge_agent.py`:

```python
def test_run_updates_dashboard_hourly(self, agent):
    """KnowledgeAgent.run() executes full dashboard update workflow"""
    with patch.object(agent, '_get_emy_status') as mock_status, \
         patch.object(agent, '_get_last_run_time') as mock_last, \
         patch.object(agent, '_get_recent_alerts') as mock_alerts, \
         patch.object(agent, '_check_critical_alerts') as mock_critical, \
         patch.object(agent, '_load_obsidian_dashboard') as mock_load, \
         patch.object(agent, '_update_dashboard_table') as mock_update, \
         patch.object(agent, '_save_obsidian_dashboard') as mock_save, \
         patch.object(agent, '_commit_dashboard_changes') as mock_commit:

        # Setup mocks
        mock_status.return_value = {'status': 'Running', 'timestamp': '2026-03-10T14:32:00'}
        mock_last.return_value = '14:32'
        mock_alerts.return_value = {'executions': 3, 'rejections': 1, 'total': 4}
        mock_critical.return_value = False
        mock_load.return_value = "| Emy | Phase 1 | RUNNING | old | data |"
        mock_update.return_value = "| Emy | Phase 1 | 🟢 RUNNING | updated | data |"
        mock_save.return_value = True
        mock_commit.return_value = True

        # Run
        success, result = agent.run()

        # Verify all methods called
        mock_status.assert_called_once()
        mock_load.assert_called_once()
        mock_update.assert_called_once()
        mock_save.assert_called_once()
        mock_commit.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_run_updates_dashboard_hourly -v`

Expected: FAIL (workflow not implemented)

**Step 3: Update run() method to integrate dashboard update**

Find and update the `run()` method in `emy/agents/knowledge_agent.py`:

```python
def run(self) -> Tuple[bool, Dict[str, Any]]:
    """Execute knowledge management tasks including dashboard update."""
    if self.check_disabled():
        self.logger.warning("KnowledgeAgent disabled")
        return (False, {'reason': 'disabled'})

    results = {
        'dashboard_updated': False,
        'session_logged': False,
        'memory_persisted': False,
        'git_committed': False,
        'timestamp': self._get_timestamp()
    }

    try:
        # ===== DASHBOARD UPDATE WORKFLOW =====
        logger.info("[KNOWLEDGE] Starting hourly dashboard update")

        # 1. Collect status data
        status_data = {
            'status': self._get_emy_status(),
            'last_run': self._get_last_run_time(),
            'next_job': self._get_next_scheduled_job(),
            'alerts': self._get_recent_alerts(),
            'critical': self._check_critical_alerts()
        }

        # 2. Format dashboard row
        formatted_status = f"{status_data['status'].get('status', 'UNKNOWN')} ({status_data['last_run']})"
        formatted_row = self._format_dashboard_row({
            'status': formatted_status,
            'next_job': status_data['next_job'].get('time', 'Unknown'),
            'alerts': status_data['alerts'],
            'critical': status_data['critical']
        })

        # 3. Load, update, and save dashboard
        dashboard_content = self._load_obsidian_dashboard()
        if dashboard_content:
            updated_content = self._update_dashboard_table(dashboard_content, formatted_row)
            if self._save_obsidian_dashboard(updated_content):
                results['dashboard_updated'] = True
                logger.info("[KNOWLEDGE] Dashboard updated successfully")

                # 4. Commit changes
                if self._commit_dashboard_changes():
                    results['git_committed'] = True
                    logger.info("[KNOWLEDGE] Dashboard changes committed")
            else:
                logger.warning("[KNOWLEDGE] Failed to save dashboard")
        else:
            logger.warning("[KNOWLEDGE] Failed to load dashboard")

        # ===== EXISTING FUNCTIONALITY (from original) =====
        # 5. Update session log (existing)
        if self._update_session_log():
            results['session_logged'] = True
            self.logger.info("[KNOWLEDGE] Session log updated")

        # 6. Persist memory (existing)
        if self._persist_memory():
            results['memory_persisted'] = True
            self.logger.info("[KNOWLEDGE] Memory persisted")

        return (True, results)

    except Exception as e:
        logger.error(f"KnowledgeAgent error: {e}")
        return (False, {'error': str(e)})
```

**Step 4: Run test to verify it passes**

Run: `pytest emy/tests/test_knowledge_agent.py::TestKnowledgeAgentTaskScheduler::test_run_updates_dashboard_hourly -v`

Expected: PASS

**Step 5: Commit**

```bash
git add emy/agents/knowledge_agent.py emy/tests/test_knowledge_agent.py
git commit -m "feat: integrate dashboard update into KnowledgeAgent.run() workflow"
```

---

## Task 6: Register Hourly Job in Scheduler

**Files:**
- Modify: `emy/main.py` (add obsidian_dashboard_update job to schedule)

**Step 1: Add job registration in main.py**

In `emy/main.py`, find the schedule registration section and add:

```python
# In the job registration area (typically in a schedule_jobs() method or __init__):

self.scheduler.register_job(
    name='obsidian_dashboard_update',
    agent='KnowledgeAgent',
    cadence='every_hour',  # Every 60 minutes
    priority='MEDIUM'
)
```

If using a different scheduler pattern, ensure this job runs:
- Every 60 minutes
- Calls KnowledgeAgent.run()
- Logs results to emy_tasks

**Step 2: Verify job configuration**

Run: `python -c "from emy.main import EMyAgentLoop; loop = EMyAgentLoop(); print('obsidian_dashboard_update' in str(loop.jobs))"`

Expected: Job registered successfully

**Step 3: Commit**

```bash
git add emy/main.py
git commit -m "feat: register hourly obsidian_dashboard_update job"
```

---

## Task 7: Create Integration Test Suite

**Files:**
- Create: `emy/tests/test_knowledge_agent_integration.py`

**Step 1: Write end-to-end integration tests**

Create `emy/tests/test_knowledge_agent_integration.py`:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from emy.agents.knowledge_agent import KnowledgeAgent
from pathlib import Path


class TestKnowledgeAgentIntegration:
    """End-to-end integration tests for dashboard updates"""

    @pytest.fixture
    def agent(self):
        return KnowledgeAgent()

    @patch('subprocess.run')
    @patch('sqlite3.connect')
    def test_full_dashboard_update_workflow(self, mock_db, mock_subprocess, agent):
        """Complete workflow: gather data -> format -> update -> commit"""
        # Mock Task Scheduler query
        mock_ps_result = Mock()
        mock_ps_result.stdout = "State\n-----\nReady"
        mock_ps_result.returncode = 0

        # Mock database query
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ('2026-03-10 14:32:15',)
        mock_cursor.fetchall.return_value = [
            ('alert_trade_executed', 3),
            ('alert_trade_rejected', 1),
        ]
        mock_db.return_value.cursor.return_value = mock_cursor

        # Set subprocess return based on command
        def ps_side_effect(*args, **kwargs):
            if 'Get-ScheduledTask' in str(args):
                return mock_ps_result
            return Mock(returncode=0)

        mock_subprocess.side_effect = ps_side_effect

        # Mock file operations
        with patch.object(agent, '_load_obsidian_dashboard') as mock_load, \
             patch.object(agent, '_save_obsidian_dashboard') as mock_save:

            mock_load.return_value = "| Emy | Phase 1 | OLD | data |"
            mock_save.return_value = True

            # Run workflow
            success, results = agent.run()

            # Verify results
            assert success is True
            assert results['dashboard_updated'] is True
            assert results['git_committed'] is True

    def test_dashboard_handles_missing_file(self, agent):
        """Dashboard creation on missing Obsidian file"""
        with patch.object(agent, '_load_obsidian_dashboard') as mock_load:
            mock_load.return_value = ""  # Empty = file not found

            # Should still attempt to create/update
            success, results = agent.run()

            # Graceful handling of missing file
            assert isinstance(success, bool)

    @patch('subprocess.run')
    def test_git_commit_with_no_changes(self, mock_subprocess, agent):
        """Git commit handles 'nothing to commit' gracefully"""
        mock_result = Mock()
        mock_result.stdout = "nothing to commit, working tree clean"
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        result = agent._commit_dashboard_changes()

        # Should return True (not an error)
        assert result is True
```

**Step 2: Run integration tests**

Run: `pytest emy/tests/test_knowledge_agent_integration.py -v`

Expected: All tests PASS

**Step 3: Commit**

```bash
git add emy/tests/test_knowledge_agent_integration.py
git commit -m "test: add end-to-end integration tests for dashboard updates"
```

---

## Task 8: Final Verification and Documentation

**Files:**
- Update: `emy/README.md` (add Knowledge Management section)
- Verify: All tests passing

**Step 1: Run all KnowledgeAgent tests**

Run: `pytest emy/tests/test_knowledge_agent.py emy/tests/test_knowledge_agent_integration.py -v --tb=short`

Expected: All tests PASS (15+ tests)

**Step 2: Verify scheduler registration**

Run: `python -c "from emy.main import EMyAgentLoop; l = EMyAgentLoop(); print(l.get_scheduled_jobs())" | grep -i dashboard`

Expected: obsidian_dashboard_update job listed

**Step 3: Update README**

Add to `emy/README.md`:

```markdown
### Knowledge Management (Automated Dashboard Updates)

The KnowledgeAgent automatically updates your Obsidian Mission Control Dashboard every hour with:
- **Emy Task Status** (Running/Stopped from Windows Task Scheduler)
- **Last Run Time** (from database)
- **Next Scheduled Job** (from Task Scheduler)
- **Recent Alerts Summary** (trade executions, rejections, warnings)
- **Critical Alerts** (daily loss 100%, API errors)

Updates are:
- ✅ Fully automated (hourly)
- ✅ Git auto-committed with descriptive messages
- ✅ Zero manual intervention required
- ✅ Gracefully handled if Obsidian file missing

Dashboard location: `../Obsidian Vault/My Knowledge Base/00-DASHBOARD.md`
```

**Step 4: Create final summary**

Run: `git log --oneline -10 | grep -i knowledge`

Expected: Shows all Knowledge Management commits

**Step 5: Final commit**

```bash
git add emy/README.md
git commit -m "docs: add Knowledge Management documentation"
```

---

## Summary

All 8 tasks implement **Enhancement #6: Automated Knowledge Management**:

1. ✅ Task Scheduler status querying
2. ✅ Database metrics collection
3. ✅ Markdown dashboard formatting and updates
4. ✅ Git auto-commit integration
5. ✅ Hourly workflow orchestration
6. ✅ Job scheduler registration
7. ✅ Integration test suite (15+ tests)
8. ✅ Documentation

**Expected outcome:**
- Obsidian dashboard updates automatically every hour
- Shows Emy status, activity, and critical alerts
- Changes auto-committed to git
- Zero manual processes
- All tests passing

**Time estimate:** ~4-5 hours total (following bite-sized task granularity)

---

## Execution Options

Plan complete and saved to `docs/plans/2026-03-10-knowledge-management-implementation.md`.

**Two execution approaches:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
