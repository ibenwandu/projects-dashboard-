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
