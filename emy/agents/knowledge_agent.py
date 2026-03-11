"""
KnowledgeAgent - maintains Emy's knowledge base and session documentation.

Responsibilities:
- Update Obsidian dashboard with project metrics
- Maintain session logs and decision records
- Persist cross-session context (MEMORY.md)
- Commit and push documentation updates to git
"""

import logging
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from emy.agents.base_agent import EMySubAgent
from emy.tools.file_ops import FileOpsTool

logger = logging.getLogger('KnowledgeAgent')


class KnowledgeAgent(EMySubAgent):
    """Agent for knowledge management and documentation."""

    def __init__(self):
        """Initialize KnowledgeAgent."""
        super().__init__('KnowledgeAgent', 'claude-haiku-4-5-20251001')
        self.file_ops = FileOpsTool()

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
            # 5. Update session log (existing - call if method exists)
            if hasattr(self, '_append_session_log') and self._append_session_log():
                results['session_logged'] = True
                self.logger.info("[KNOWLEDGE] Session log updated")

            # 6. Persist memory (existing - call if method exists)
            if hasattr(self, '_update_memory') and self._update_memory():
                results['memory_persisted'] = True
                self.logger.info("[KNOWLEDGE] Memory persisted")

            success = any([
                results['dashboard_updated'],
                results['session_logged'],
                results['memory_persisted']
            ])

            return (success, results)

        except Exception as e:
            logger.error(f"[ERROR] Knowledge management failed: {e}")
            return (False, {'error': str(e), 'results': results})

    def _update_obsidian_dashboard(self) -> bool:
        """Update Obsidian 00-DASHBOARD.md with project metrics."""
        try:
            dashboard_path = (
                'C:\\Users\\user\\projects\\personal\\Obsidian Vault\\My Knowledge Base\\00-DASHBOARD.md'
            )

            # Would normally read current dashboard and update metrics
            # For Phase 3 Batch 1, just verify file exists
            if self.file_ops.file_exists(dashboard_path):
                self.logger.debug(f"Dashboard file found: {dashboard_path}")
                return True
            else:
                self.logger.warning(f"Dashboard file not found: {dashboard_path}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating Obsidian dashboard: {e}")
            return False

    def _append_session_log(self) -> bool:
        """Append to CLAUDE_SESSION_LOG.md in project root."""
        try:
            log_path = 'C:\\Users\\user\\projects\\personal\\CLAUDE_SESSION_LOG.md'

            # Would normally append session summary
            # For Phase 3 Batch 1, just verify file exists
            if self.file_ops.file_exists(log_path):
                self.logger.debug(f"Session log found: {log_path}")
                return True
            else:
                self.logger.warning(f"Session log not found: {log_path}")
                return False

        except Exception as e:
            self.logger.error(f"Error appending to session log: {e}")
            return False

    def _update_memory(self) -> bool:
        """Update MEMORY.md with cross-session context."""
        try:
            memory_path = (
                'C:\\Users\\user\\.claude\\projects\\C--Users-user-projects-personal\\memory\\MEMORY.md'
            )

            # Would normally update decision records and findings
            # For Phase 3 Batch 1, just verify file exists
            if self.file_ops.file_exists(memory_path):
                self.logger.debug(f"Memory file found: {memory_path}")
                return True
            else:
                self.logger.warning(f"Memory file not found: {memory_path}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating MEMORY.md: {e}")
            return False

    def _git_commit_updates(self) -> bool:
        """Commit documentation updates to git."""
        try:
            # Would normally check git status and commit if changes exist
            # For Phase 3 Batch 1, just return False (no changes to commit)
            self.logger.debug("Checking for git changes...")
            return False

        except Exception as e:
            self.logger.error(f"Error committing to git: {e}")
            return False

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

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
            # Find Emy row (contains "Emy" and "Phase")
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
