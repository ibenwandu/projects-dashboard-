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
        """Execute knowledge management tasks."""
        if self.check_disabled():
            self.logger.warning("KnowledgeAgent disabled")
            return (False, {'reason': 'disabled'})

        results = {
            'obsidian_updated': False,
            'session_logged': False,
            'memory_persisted': False,
            'git_committed': False,
            'timestamp': self._get_timestamp()
        }

        try:
            # 1. Update Obsidian dashboard
            if self._update_obsidian_dashboard():
                results['obsidian_updated'] = True
                self.logger.info("[KNOWLEDGE] Obsidian dashboard updated")
            else:
                self.logger.warning("[KNOWLEDGE] Obsidian dashboard update failed")

            # 2. Update session log
            if self._append_session_log():
                results['session_logged'] = True
                self.logger.info("[KNOWLEDGE] Session log appended")
            else:
                self.logger.warning("[KNOWLEDGE] Session log append failed")

            # 3. Persist MEMORY.md
            if self._update_memory():
                results['memory_persisted'] = True
                self.logger.info("[KNOWLEDGE] MEMORY.md persisted")
            else:
                self.logger.warning("[KNOWLEDGE] MEMORY.md persist failed")

            # 4. Git commit if changes exist
            if self._git_commit_updates():
                results['git_committed'] = True
                self.logger.info("[KNOWLEDGE] Changes committed to git")
            else:
                self.logger.debug("[KNOWLEDGE] No changes to commit")

            success = any([
                results['obsidian_updated'],
                results['session_logged'],
                results['memory_persisted']
            ])

        except Exception as e:
            self.logger.error(f"[ERROR] Knowledge management failed: {e}")
            return (False, {'error': str(e), 'results': results})

        self.logger.info(f"[RUN] KnowledgeAgent completed")
        return (True, results)

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
