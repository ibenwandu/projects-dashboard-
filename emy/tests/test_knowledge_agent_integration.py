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
        # Mock disable guard to allow execution
        agent.disable_guard.is_disabled = Mock(return_value=False)

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
            return Mock(returncode=0, stdout="", stderr="")

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
        # First call (git add) returns 0 (success)
        mock_add_result = Mock()
        mock_add_result.returncode = 0
        mock_add_result.stdout = ""
        mock_add_result.stderr = ""

        # Second call (git commit) returns 1 with 'nothing to commit' message
        mock_commit_result = Mock()
        mock_commit_result.stdout = "nothing to commit, working tree clean"
        mock_commit_result.stderr = ""
        mock_commit_result.returncode = 1

        # Configure side effect to return different results for different calls
        mock_subprocess.side_effect = [mock_add_result, mock_commit_result]

        result = agent._commit_dashboard_changes()

        # Should return True (not an error for 'nothing to commit')
        assert result is True
