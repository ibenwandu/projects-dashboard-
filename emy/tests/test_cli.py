"""
Tests for Emy CLI client.

TDD approach - tests written first, CLI implementation follows.
"""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, Mock
from emy.cli.main import cli


class TestCliExecuteCommand:
    """Test 'emy execute' command."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_execute_basic(self, runner):
        """Test basic execute command with valid inputs."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_123abc',
                    'status': 'pending',
                    'created_at': '2026-03-11T12:00:00'
                }
            )

            result = runner.invoke(cli, ['execute', 'analysis', 'KnowledgeAgent'])

            assert result.exit_code == 0
            assert 'wf_123abc' in result.output
            assert 'pending' in result.output
            mock_post.assert_called_once()

    def test_execute_with_json_input(self, runner):
        """Test execute command with JSON input."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_456def',
                    'status': 'pending',
                    'created_at': '2026-03-11T12:00:00'
                }
            )

            input_json = '{"query":"test"}'
            result = runner.invoke(cli, ['execute', 'analysis', 'KnowledgeAgent', input_json])

            assert result.exit_code == 0
            assert 'wf_456def' in result.output

    def test_execute_invalid_json_input(self, runner):
        """Test execute command with invalid JSON input."""
        result = runner.invoke(cli, [
            'execute', 'analysis', 'KnowledgeAgent', '{invalid json}'
        ])

        assert result.exit_code != 0
        assert 'invalid JSON' in result.output.lower() or 'error' in result.output.lower()

    def test_execute_server_unavailable(self, runner):
        """Test execute command when server is unavailable."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.side_effect = ConnectionError('Connection refused')

            result = runner.invoke(cli, ['execute', 'analysis', 'KnowledgeAgent'])

            assert result.exit_code != 0
            assert 'unavailable' in result.output.lower() or 'error' in result.output.lower()

    def test_execute_verbose_error(self, runner):
        """Test execute command with --verbose flag shows detailed error."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=500,
                text='Internal Server Error',
                json=lambda: {'error': 'Database connection failed'}
            )

            result = runner.invoke(cli, [
                'execute', 'analysis', 'KnowledgeAgent', '--verbose'
            ])

            assert result.exit_code != 0
            assert 'error' in result.output.lower()


class TestCliStatusCommand:
    """Test 'emy status' command."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_status_found(self, runner):
        """Test status command with valid workflow ID."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_123abc',
                    'type': 'analysis',
                    'status': 'completed',
                    'created_at': '2026-03-11T12:00:00',
                    'updated_at': '2026-03-11T12:05:00',
                    'input': '{"query":"test"}',
                    'output': '{"result":"success"}'
                }
            )

            result = runner.invoke(cli, ['status', 'wf_123abc'])

            assert result.exit_code == 0
            assert 'wf_123abc' in result.output
            assert 'completed' in result.output

    def test_status_not_found(self, runner):
        """Test status command with non-existent workflow ID."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=404,
                json=lambda: {'error': 'Workflow not found'}
            )

            result = runner.invoke(cli, ['status', 'wf_nonexistent'])

            assert result.exit_code != 0
            assert 'not found' in result.output.lower()

    def test_status_server_error(self, runner):
        """Test status command with server error."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.side_effect = ConnectionError('Connection refused')

            result = runner.invoke(cli, ['status', 'wf_123abc'])

            assert result.exit_code != 0


class TestCliListCommand:
    """Test 'emy list' command."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_list_default(self, runner):
        """Test list command with default pagination."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflows': [
                        {
                            'workflow_id': 'wf_001',
                            'type': 'analysis',
                            'status': 'completed',
                            'created_at': '2026-03-11T12:00:00'
                        },
                        {
                            'workflow_id': 'wf_002',
                            'type': 'health_check',
                            'status': 'pending',
                            'created_at': '2026-03-11T12:01:00'
                        }
                    ],
                    'total': 2,
                    'limit': 10,
                    'offset': 0
                }
            )

            result = runner.invoke(cli, ['list'])

            assert result.exit_code == 0
            assert 'wf_001' in result.output
            assert 'wf_002' in result.output
            mock_get.assert_called_once()

    def test_list_with_pagination(self, runner):
        """Test list command with custom limit and offset."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflows': [],
                    'total': 0,
                    'limit': 5,
                    'offset': 10
                }
            )

            result = runner.invoke(cli, ['list', '--limit', '5', '--offset', '10'])

            assert result.exit_code == 0
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert 'limit=5' in call_args[0][0] or call_args[1].get('params', {}).get('limit') == 5

    def test_list_empty(self, runner):
        """Test list command with empty results."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflows': [],
                    'total': 0,
                    'limit': 10,
                    'offset': 0
                }
            )

            result = runner.invoke(cli, ['list'])

            assert result.exit_code == 0
            assert 'no workflows' in result.output.lower() or '0' in result.output


class TestCliAgentsCommand:
    """Test 'emy agents' command."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_agents_list(self, runner):
        """Test agents command shows agent status."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'agents': [
                        {
                            'agent_name': 'TradingAgent',
                            'status': 'healthy',
                            'tasks_completed': 42,
                            'tasks_failed': 1,
                            'last_activity': '2026-03-11T12:00:00'
                        },
                        {
                            'agent_name': 'KnowledgeAgent',
                            'status': 'healthy',
                            'tasks_completed': 15,
                            'tasks_failed': 0,
                            'last_activity': '2026-03-11T11:55:00'
                        }
                    ]
                }
            )

            result = runner.invoke(cli, ['agents'])

            assert result.exit_code == 0
            assert 'TradingAgent' in result.output
            assert 'KnowledgeAgent' in result.output
            assert 'healthy' in result.output

    def test_agents_server_error(self, runner):
        """Test agents command with server error."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.side_effect = ConnectionError('Connection refused')

            result = runner.invoke(cli, ['agents'])

            assert result.exit_code != 0


class TestCliHealthCommand:
    """Test 'emy health' command."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_health_server_ok(self, runner):
        """Test health command when server is healthy."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {'status': 'ok', 'timestamp': '2026-03-11T12:00:00'}
            )

            result = runner.invoke(cli, ['health'])

            assert result.exit_code == 0
            assert 'healthy' in result.output.lower() or 'ok' in result.output.lower()

    def test_health_server_down(self, runner):
        """Test health command when server is down."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.side_effect = ConnectionError('Connection refused')

            result = runner.invoke(cli, ['health'])

            assert result.exit_code != 0
            assert 'error' in result.output.lower()

    def test_health_server_error(self, runner):
        """Test health command with server error."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=500,
                text='Internal Server Error'
            )

            result = runner.invoke(cli, ['health'])

            assert result.exit_code != 0


class TestCliEnvironmentConfiguration:
    """Test CLI environment configuration."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_api_url_from_env(self, runner):
        """Test API URL is read from EMY_API_URL environment variable."""
        with patch.dict('os.environ', {'EMY_API_URL': 'http://api.example.com:9000'}):
            with patch('emy.cli.main.requests.get') as mock_get:
                mock_get.return_value = Mock(
                    status_code=200,
                    json=lambda: {'status': 'ok'}
                )

                result = runner.invoke(cli, ['health'])

                assert result.exit_code == 0
                # Verify custom URL was used
                call_url = mock_get.call_args[0][0]
                assert 'api.example.com:9000' in call_url

    def test_api_url_default(self, runner):
        """Test API URL defaults to localhost:8000."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('emy.cli.main.requests.get') as mock_get:
                mock_get.return_value = Mock(
                    status_code=200,
                    json=lambda: {'status': 'ok'}
                )

                result = runner.invoke(cli, ['health'])

                assert result.exit_code == 0
                call_url = mock_get.call_args[0][0]
                assert 'localhost:8000' in call_url


class TestCliErrorHandling:
    """Test CLI error handling and user-friendly messages."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_missing_required_argument(self, runner):
        """Test missing required arguments are handled gracefully."""
        result = runner.invoke(cli, ['execute'])

        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'missing' in result.output.lower()

    def test_invalid_command(self, runner):
        """Test invalid command shows help."""
        result = runner.invoke(cli, ['invalid_command'])

        assert result.exit_code != 0

    def test_verbose_flag_available(self, runner):
        """Test --verbose flag is available."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=400,
                json=lambda: {'error': 'Bad request'}
            )

            result = runner.invoke(cli, ['execute', 'analysis', 'Agent', '--verbose'])

            # Should not raise an error about unknown option
            assert '--verbose' not in result.output


class TestCliPrettyOutput:
    """Test CLI pretty output formatting."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_list_output_is_table(self, runner):
        """Test list command outputs data in table format."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflows': [
                        {
                            'workflow_id': 'wf_001',
                            'type': 'analysis',
                            'status': 'completed',
                            'created_at': '2026-03-11T12:00:00'
                        }
                    ],
                    'total': 1,
                    'limit': 10,
                    'offset': 0
                }
            )

            result = runner.invoke(cli, ['list'])

            assert result.exit_code == 0
            # Table should have headers or structured format
            assert 'workflow_id' in result.output.lower() or 'id' in result.output.lower()

    def test_status_output_is_table(self, runner):
        """Test status command outputs data in table format."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_123abc',
                    'type': 'analysis',
                    'status': 'completed',
                    'created_at': '2026-03-11T12:00:00',
                    'updated_at': '2026-03-11T12:05:00',
                    'input': '{"query":"test"}',
                    'output': '{"result":"success"}'
                }
            )

            result = runner.invoke(cli, ['status', 'wf_123abc'])

            assert result.exit_code == 0
            # Output should contain key information
            assert 'wf_123abc' in result.output
            assert 'completed' in result.output
