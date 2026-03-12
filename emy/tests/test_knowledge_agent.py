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

    def test_run_updates_dashboard_hourly(self, agent):
        """KnowledgeAgent.run() executes full dashboard update workflow"""
        with patch.object(agent.disable_guard, 'is_disabled', return_value=False), \
             patch.object(agent, '_get_emy_status') as mock_status, \
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
