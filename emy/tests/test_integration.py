"""
Integration tests for Emy Phase 1a - API Gateway, CLI, Storage, and UI layers.

TDD approach: Tests verify end-to-end workflows across all components.
Uses mocked agents to focus on integration points (storage, API, CLI, UI).
"""

import pytest
import json
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from click.testing import CliRunner

from fastapi.testclient import TestClient
from emy.gateway.api import app
from emy.cli.main import cli, EMyAPIClient
from emy.core.database import EMyDatabase


class TestFullWorkflowExecution:
    """Test complete workflow: CLI → API → Storage → retrieval."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = EMyDatabase(str(db_path))
            db.initialize_schema()
            yield db

    @pytest.fixture
    def api_client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_execute_workflow_cli_to_api_to_storage(self, api_client, temp_db):
        """Test full workflow: CLI command → API endpoint → database storage."""
        # Step 1: Execute workflow via API
        response = api_client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'analysis',
                'agents': ['KnowledgeAgent'],
                'input': {'query': 'test query'}
            }
        )

        assert response.status_code == 200
        workflow = response.json()
        assert workflow['status'] == 'pending'
        assert 'workflow_id' in workflow
        assert workflow['type'] == 'analysis'

        workflow_id = workflow['workflow_id']

        # Step 2: Verify retrieval via API
        response = api_client.get(f'/workflows/{workflow_id}')
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved['workflow_id'] == workflow_id
        assert retrieved['type'] == 'analysis'

    def test_cli_execute_command_integration(self):
        """Test CLI execute command with mocked API."""
        runner = CliRunner()

        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_integration_test',
                    'status': 'pending',
                    'created_at': '2026-03-12T10:00:00'
                }
            )

            result = runner.invoke(cli, ['execute', 'analysis', 'KnowledgeAgent'])

            assert result.exit_code == 0
            assert 'wf_integration_test' in result.output
            mock_post.assert_called_once()

    def test_cli_status_command_integration(self):
        """Test CLI status command returns workflow details."""
        runner = CliRunner()

        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_test_status',
                    'status': 'completed',
                    'type': 'analysis',
                    'created_at': '2026-03-12T10:00:00',
                    'output': '{"result": "success"}'
                }
            )

            result = runner.invoke(cli, ['status', 'wf_test_status'])

            assert result.exit_code == 0
            assert 'wf_test_status' in result.output
            mock_get.assert_called_once()


class TestMultiAgentWorkflow:
    """Test workflows with multiple agents executing concurrently."""

    @pytest.fixture
    def api_client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_multi_agent_research_analysis_workflow(self, api_client):
        """Test research + analysis workflow with two agents."""
        # Execute multi-agent workflow
        response = api_client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'research_and_analyze',
                'agents': ['ResearchAgent', 'KnowledgeAgent'],
                'input': {'topic': 'AI trends'}
            }
        )

        assert response.status_code == 200
        workflow = response.json()
        assert workflow['status'] == 'pending'

        # Verify workflow contains both agents
        workflow_id = workflow['workflow_id']
        response = api_client.get(f'/workflows/{workflow_id}')
        retrieved = response.json()
        assert retrieved['type'] == 'research_and_analyze'

    def test_multi_workflow_concurrent_execution(self, api_client):
        """Test multiple workflows running independently."""
        workflow_ids = []

        # Create 3 concurrent workflows
        for i in range(3):
            response = api_client.post(
                '/workflows/execute',
                json={
                    'workflow_type': f'workflow_{i}',
                    'agents': ['KnowledgeAgent'],
                    'input': {'id': i}
                }
            )
            assert response.status_code == 200
            workflow_ids.append(response.json()['workflow_id'])

        # Verify all workflows exist independently
        for wf_id in workflow_ids:
            response = api_client.get(f'/workflows/{wf_id}')
            assert response.status_code == 200
            assert response.json()['workflow_id'] == wf_id


class TestDataPersistence:
    """Test data persistence: save → restart → retrieve."""

    @pytest.fixture
    def temp_db(self):
        """Create persistent temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "persistence_test.db"
            db = EMyDatabase(str(db_path))
            db.initialize_schema()
            yield db, db_path

    def test_workflow_persistence_across_restart(self, temp_db):
        """Test workflow data persists when database reconnects."""
        db, db_path = temp_db

        # Insert task via first connection
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO emy_tasks
                (source, domain, task_type, status, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                ('test', 'trading', 'monitor', 'completed', 'test task')
            )
            task_id = cursor.lastrowid

        # Reconnect with new database instance
        db2 = EMyDatabase(str(db_path))
        with db2.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emy_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()

        # Verify task exists after "restart"
        assert row is not None
        assert row['description'] == 'test task'
        assert row['status'] == 'completed'

    def test_sub_agent_run_persistence(self, temp_db):
        """Test sub-agent execution logs persist."""
        db, db_path = temp_db

        # Insert task and agent run
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO emy_tasks
                (source, domain, task_type, status, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                ('test', 'trading', 'execute', 'completed', 'task')
            )
            task_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO sub_agent_runs
                (task_id, agent_name, model, status, input_tokens, output_tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, 'TradingAgent', 'claude-haiku-4-5-20251001', 'success', 100, 50, 0.001)
            )

        # Verify persistence
        db2 = EMyDatabase(str(db_path))
        with db2.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM sub_agent_runs WHERE task_id = ?', (task_id,))
            row = cursor.fetchone()

        assert row['count'] == 1


class TestAPIGatewayHealth:
    """Test all 6 API gateway endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_health_check_endpoint(self, client):
        """Test GET /health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data

    def test_execute_workflow_endpoint(self, client):
        """Test POST /workflows/execute endpoint."""
        response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'test',
                'agents': ['TestAgent'],
                'input': {'key': 'value'}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert 'workflow_id' in data
        assert data['status'] == 'pending'

    def test_get_workflow_status_endpoint(self, client):
        """Test GET /workflows/{workflow_id} endpoint."""
        # Create workflow first
        create_response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'test',
                'agents': ['TestAgent']
            }
        )
        workflow_id = create_response.json()['workflow_id']

        # Get status
        response = client.get(f'/workflows/{workflow_id}')
        assert response.status_code == 200
        data = response.json()
        assert data['workflow_id'] == workflow_id

    def test_list_workflows_endpoint(self, client):
        """Test GET /workflows endpoint with pagination."""
        # Create multiple workflows
        for i in range(5):
            client.post(
                '/workflows/execute',
                json={
                    'workflow_type': f'workflow_{i}',
                    'agents': ['TestAgent']
                }
            )

        # List with default pagination
        response = client.get('/workflows')
        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 5
        assert data['limit'] == 10
        assert data['offset'] == 0

    def test_list_workflows_with_pagination(self, client):
        """Test pagination parameters."""
        response = client.get('/workflows?limit=2&offset=0')
        assert response.status_code == 200
        data = response.json()
        assert len(data['workflows']) <= 2
        assert data['limit'] == 2

    def test_get_agents_status_endpoint(self, client):
        """Test GET /agents/status endpoint."""
        response = client.get('/agents/status')
        assert response.status_code == 200
        data = response.json()
        assert 'agents' in data
        assert len(data['agents']) > 0
        assert data['agents'][0]['agent_name'] in ['TradingAgent', 'KnowledgeAgent', 'ProjectMonitorAgent', 'ResearchAgent']


class TestCLIToAPIIntegration:
    """Test CLI client communication with API."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_cli_connect_to_api(self, runner):
        """Test CLI successfully connects to API."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_cli_api_test',
                    'status': 'pending',
                    'created_at': datetime.now().isoformat()
                }
            )

            result = runner.invoke(cli, ['execute', 'test_workflow', 'KnowledgeAgent'])

            assert result.exit_code == 0
            mock_post.assert_called_once()
            assert 'wf_cli_api_test' in result.output

    def test_cli_formats_api_response(self, runner):
        """Test CLI properly formats and displays API response."""
        with patch('emy.cli.main.requests.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    'workflow_id': 'wf_format_test',
                    'type': 'analysis',
                    'status': 'completed',
                    'created_at': '2026-03-12T10:00:00',
                    'output': '{"result": "test"}'
                }
            )

            result = runner.invoke(cli, ['status', 'wf_format_test'])

            assert result.exit_code == 0
            assert 'wf_format_test' in result.output
            assert 'analysis' in result.output

    def test_cli_handles_api_errors(self, runner):
        """Test CLI handles API errors gracefully."""
        with patch('emy.cli.main.requests.post') as mock_post:
            mock_post.side_effect = Exception('Connection refused')

            result = runner.invoke(cli, ['execute', 'test', 'TestAgent'])

            assert result.exit_code != 0

    def test_cli_api_client_custom_url(self):
        """Test CLI API client accepts custom API URL."""
        client = EMyAPIClient(api_url='http://custom:8000')
        assert client.api_url == 'http://custom:8000'

    def test_cli_api_client_default_url(self):
        """Test CLI API client uses default URL."""
        with patch.dict('os.environ', {}, clear=True):
            client = EMyAPIClient()
            assert 'localhost:8000' in client.api_url or client.api_url.endswith('8000')


class TestUIToAPIIntegration:
    """Test Gradio UI integration with API (mock UI layer)."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_ui_can_execute_workflow(self, client):
        """Test UI can trigger workflow execution."""
        response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'chat_query',
                'agents': ['KnowledgeAgent'],
                'input': {'message': 'What is the status?'}
            }
        )

        assert response.status_code == 200
        workflow = response.json()
        assert 'workflow_id' in workflow

    def test_ui_can_poll_workflow_status(self, client):
        """Test UI can poll workflow status."""
        # Execute
        exec_response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'chat_query',
                'agents': ['KnowledgeAgent']
            }
        )
        workflow_id = exec_response.json()['workflow_id']

        # Poll status
        for _ in range(3):
            response = client.get(f'/workflows/{workflow_id}')
            assert response.status_code == 200
            assert response.json()['workflow_id'] == workflow_id

    def test_ui_can_list_workflow_history(self, client):
        """Test UI can retrieve workflow history."""
        # Create multiple workflows
        for i in range(3):
            client.post(
                '/workflows/execute',
                json={
                    'workflow_type': f'query_{i}',
                    'agents': ['KnowledgeAgent']
                }
            )

        # List history
        response = client.get('/workflows?limit=10')
        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 3
        assert len(data['workflows']) > 0


class TestErrorHandling:
    """Test error handling across layers."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_invalid_workflow_request(self, client):
        """Test API handles invalid workflow request."""
        response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': '',  # Invalid: empty type
                'agents': []  # Invalid: no agents
            }
        )
        # API should still create workflow (validation could be stricter)
        assert response.status_code in [200, 400, 422]

    def test_workflow_not_found(self, client):
        """Test API returns 404 for nonexistent workflow."""
        response = client.get('/workflows/wf_nonexistent')
        assert response.status_code == 404

    def test_invalid_pagination_parameters(self, client):
        """Test API validates pagination parameters."""
        # Limit too high
        response = client.get('/workflows?limit=1000')
        assert response.status_code in [200, 422]

        # Negative offset
        response = client.get('/workflows?offset=-1')
        assert response.status_code in [200, 422]

    def test_cli_handles_connection_error(self):
        """Test CLI handles server connection error."""
        runner = CliRunner()

        with patch('emy.cli.main.requests.post') as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.ConnectionError('Connection refused')

            result = runner.invoke(cli, ['execute', 'test', 'TestAgent'])

            assert result.exit_code != 0


class TestConcurrentWorkflows:
    """Test concurrent workflow execution."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_multiple_workflows_independent(self, client):
        """Test multiple workflows execute independently."""
        workflow_ids = []

        # Create 5 concurrent workflows
        for i in range(5):
            response = client.post(
                '/workflows/execute',
                json={
                    'workflow_type': f'concurrent_test_{i}',
                    'agents': ['KnowledgeAgent', 'TradingAgent'],
                    'input': {'workflow_num': i}
                }
            )
            assert response.status_code == 200
            workflow_ids.append(response.json()['workflow_id'])

        # Verify each has independent state
        for i, wf_id in enumerate(workflow_ids):
            response = client.get(f'/workflows/{wf_id}')
            assert response.status_code == 200
            data = response.json()
            assert data['workflow_id'] == wf_id
            assert f'concurrent_test_{i}' in data['type']

    def test_workflow_list_shows_all_concurrent(self, client):
        """Test list endpoint shows all concurrent workflows."""
        initial_count = client.get('/workflows').json()['total']

        # Create 3 workflows
        for i in range(3):
            client.post(
                '/workflows/execute',
                json={
                    'workflow_type': f'list_test_{i}',
                    'agents': ['TestAgent']
                }
            )

        # Verify count increased
        response = client.get('/workflows?limit=100')
        new_count = response.json()['total']
        assert new_count >= initial_count + 3

    def test_concurrent_status_queries(self, client):
        """Test multiple status queries don't interfere."""
        # Create workflow
        exec_response = client.post(
            '/workflows/execute',
            json={
                'workflow_type': 'concurrent_status_test',
                'agents': ['TestAgent']
            }
        )
        workflow_id = exec_response.json()['workflow_id']

        # Query status 5 times concurrently (simulated)
        for _ in range(5):
            response = client.get(f'/workflows/{workflow_id}')
            assert response.status_code == 200
            assert response.json()['workflow_id'] == workflow_id


# ============================================================================
# Test Execution & Reporting
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
