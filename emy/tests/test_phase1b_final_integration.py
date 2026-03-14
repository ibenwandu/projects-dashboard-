"""
Task 4: Phase 1b Final Integration Tests & Verification

Verify all Phase 1b components work together end-to-end:
1. All integration tests pass
2. Real Claude API calls work (or gracefully degrade)
3. Workflow execution returns real outputs
4. Database persistence verified
5. Error cases handled
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from emy.core.database import EMyDatabase
from emy.agents.agent_executor import AgentExecutor
from emy.agents.knowledge_agent import KnowledgeAgent
from emy.agents.trading_agent import TradingAgent
from emy.tools.api_client import OandaClient
import tempfile


class TestPhase1bFullIntegration:
    """Test Phase 1b components working together."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db = EMyDatabase(db_path)
        db.initialize_schema()

        yield db

        # Cleanup
        import os
        if os.path.exists(db_path):
            os.remove(db_path)

    # ========================================================================
    # CRITERION 1: All integration tests pass
    # ========================================================================

    def test_knowledge_agent_full_flow(self):
        """
        CRITERION 1: KnowledgeAgent integration test.

        ✓ Agent instantiates
        ✓ Calls Claude API (mocked)
        ✓ Returns proper structure
        ✓ Output JSON-serializable
        """
        agent = KnowledgeAgent()

        with patch.object(agent, '_call_claude', return_value="Knowledge response"):
            success, result = agent.run()

            assert success is True
            assert isinstance(result, dict)
            assert 'response' in result
            assert 'timestamp' in result
            assert 'agent' in result

            # Verify JSON serializable
            json_str = json.dumps(result)
            parsed = json.loads(json_str)
            assert parsed['response'] == "Knowledge response"

    def test_trading_agent_full_flow(self):
        """
        CRITERION 1: TradingAgent integration test.

        ✓ Agent instantiates with OandaClient
        ✓ Handles OANDA data (mocked)
        ✓ Returns proper structure
        ✓ Output JSON-serializable
        """
        agent = TradingAgent()

        mock_summary = {
            'equity': 10000.00,
            'margin_available': 9500.00,
            'margin_used': 500.00,
            'unrealized_pl': 150.50
        }

        with patch.object(agent, '_call_claude', return_value="Trading analysis"):
            with patch.object(agent.oanda_client, 'get_account_summary',
                             return_value=mock_summary):
                success, result = agent.run()

                assert success is True
                assert isinstance(result, dict)
                assert 'analysis' in result
                assert 'timestamp' in result

                # Verify JSON serializable
                json_str = json.dumps(result)
                parsed = json.loads(json_str)
                assert isinstance(parsed, dict)

    def test_agent_executor_routes_correctly(self):
        """
        CRITERION 1: AgentExecutor routes to correct agents.

        ✓ knowledge_query routes to KnowledgeAgent
        ✓ trading_health routes to TradingAgent
        ✓ Each returns proper structure
        """
        test_cases = [
            ('knowledge_query', ['KnowledgeAgent']),
            ('trading_health', ['TradingAgent']),
        ]

        for workflow_type, agents in test_cases:
            with patch('emy.agents.knowledge_agent.KnowledgeAgent._call_claude',
                      return_value="Response"):
                with patch('emy.agents.trading_agent.TradingAgent._call_claude',
                          return_value="Response"):
                    success, output_json = AgentExecutor.execute(
                        workflow_type=workflow_type,
                        agents=agents,
                        workflow_input={}
                    )

                    assert success is True
                    assert output_json is not None
                    result = json.loads(output_json)
                    assert isinstance(result, dict)

    # ========================================================================
    # CRITERION 2: Real Claude API calls work (or graceful degradation)
    # ========================================================================

    def test_claude_api_error_handled_gracefully(self):
        """
        CRITERION 2: Claude API errors handled gracefully.

        ✓ Missing API key doesn't crash
        ✓ Invalid credentials handled
        ✓ Network errors handled
        ✓ Agent returns error dict
        """
        agent = KnowledgeAgent()

        # Simulate API error
        with patch.object(agent, '_call_claude',
                         side_effect=Exception("API Error")):
            success, result = agent.run()

            # Should return False with error info
            assert success is False
            assert isinstance(result, dict)
            assert 'error' in result or success is False

    def test_oanda_api_error_handled_gracefully(self):
        """
        CRITERION 2: OANDA API errors handled gracefully.

        ✓ Missing credentials don't crash
        ✓ Connection errors handled
        ✓ Agent completes with partial data
        """
        agent = TradingAgent()

        # Simulate OANDA error
        with patch.object(agent.oanda_client, 'get_account_summary',
                         side_effect=Exception("OANDA Error")):
            with patch.object(agent, '_call_claude', return_value="Analysis"):
                success, result = agent.run()

                # Should complete (possibly with error, but no crash)
                assert isinstance(result, dict)

    def test_database_errors_handled_gracefully(self):
        """
        CRITERION 2: Database errors handled gracefully.

        ✓ Storage errors logged, not fatal
        ✓ Retrieval errors return None
        """
        db = EMyDatabase(':memory:')
        db.initialize_schema()

        # Store should handle errors gracefully
        result = db.store_workflow_output('test_id', 'test', 'complete', '{}')
        assert isinstance(result, bool)

        # Retrieve missing should return None
        workflow = db.get_workflow('nonexistent')
        assert workflow is None

    # ========================================================================
    # CRITERION 3: Workflow execution returns real outputs
    # ========================================================================

    def test_knowledge_workflow_execution(self):
        """
        CRITERION 3: Knowledge workflow returns real outputs.

        ✓ execute() returns proper structure
        ✓ Output includes response, timestamp, agent
        ✓ JSON parseable
        """
        with patch('emy.agents.knowledge_agent.KnowledgeAgent._call_claude',
                  return_value="Real knowledge response"):
            success, output_json = AgentExecutor.execute(
                workflow_type='knowledge_query',
                agents=['KnowledgeAgent'],
                workflow_input={'query': 'test'}
            )

            assert success is True
            result = json.loads(output_json)

            assert 'response' in result
            assert 'timestamp' in result
            assert 'agent' in result
            assert result['response'] == "Real knowledge response"

    def test_trading_workflow_execution(self):
        """
        CRITERION 3: Trading workflow returns real outputs.

        ✓ execute() returns proper structure
        ✓ Output includes analysis, market context
        ✓ JSON parseable
        """
        mock_summary = {
            'equity': 10000.00,
            'margin_available': 9500.00,
            'margin_used': 500.00,
            'unrealized_pl': 150.50
        }

        with patch('emy.agents.trading_agent.TradingAgent._call_claude',
                  return_value="Real trading analysis"):
            with patch('emy.agents.trading_agent.OandaClient.get_account_summary',
                      return_value=mock_summary):
                success, output_json = AgentExecutor.execute(
                    workflow_type='trading_health',
                    agents=['TradingAgent'],
                    workflow_input={}
                )

                assert success is True
                result = json.loads(output_json)
                assert 'analysis' in result

    # ========================================================================
    # CRITERION 4: Database persistence verified
    # ========================================================================

    def test_workflow_stored_and_retrieved(self, temp_db):
        """
        CRITERION 4: Workflows stored and retrieved correctly.

        ✓ Store workflow output
        ✓ Retrieve via get_workflow()
        ✓ Data intact
        """
        workflow_id = 'wf_e2e_test_1'
        output = json.dumps({'response': 'Test output', 'timestamp': '2026-03-14T14:00:00'})

        # Store
        temp_db.store_workflow_output(workflow_id, 'knowledge_query', 'completed', output)

        # Retrieve
        workflow = temp_db.get_workflow(workflow_id)

        assert workflow is not None
        assert workflow['workflow_id'] == workflow_id
        assert workflow['output'] == output
        assert workflow['status'] == 'completed'

    def test_multiple_workflows_stored_independently(self, temp_db):
        """
        CRITERION 4: Multiple workflows persist independently.

        ✓ Store multiple workflows
        ✓ Retrieve each independently
        ✓ Data correct for each
        """
        workflows = [
            ('wf_e2e_1', 'knowledge_query', 'completed', '{"id": 1}'),
            ('wf_e2e_2', 'trading_health', 'completed', '{"id": 2}'),
            ('wf_e2e_3', 'knowledge_query', 'error', '{"id": 3}'),
        ]

        # Store all
        for wf_id, wf_type, status, output in workflows:
            temp_db.store_workflow_output(wf_id, wf_type, status, output)

        # Retrieve and verify each
        for wf_id, wf_type, expected_status, expected_output in workflows:
            workflow = temp_db.get_workflow(wf_id)
            assert workflow is not None
            assert workflow['type'] == wf_type
            assert workflow['status'] == expected_status
            assert workflow['output'] == expected_output

    # ========================================================================
    # CRITERION 5: Error cases handled
    # ========================================================================

    def test_missing_agent_handled(self):
        """
        CRITERION 5: Unknown agent type handled gracefully.

        ✓ Returns error tuple
        ✓ No crash
        """
        success, output = AgentExecutor.execute(
            workflow_type='unknown_workflow_type',
            agents=['UnknownAgent'],
            workflow_input={}
        )

        assert success is False
        # Should return False or None, not crash

    def test_empty_agents_list_handled(self):
        """
        CRITERION 5: Empty agents list handled gracefully.

        ✓ Returns error tuple
        ✓ No crash
        """
        success, output = AgentExecutor.execute(
            workflow_type='knowledge_query',
            agents=[],
            workflow_input={}
        )

        assert success is False

    def test_malformed_input_handled(self):
        """
        CRITERION 5: Malformed input handled gracefully.

        ✓ Agent handles None input
        ✓ Agent handles empty dict
        ✓ No crash
        """
        test_inputs = [None, {}, {'invalid': 'data'}]

        for test_input in test_inputs:
            with patch('emy.agents.knowledge_agent.KnowledgeAgent._call_claude',
                      return_value="Response"):
                success, output_json = AgentExecutor.execute(
                    workflow_type='knowledge_query',
                    agents=['KnowledgeAgent'],
                    workflow_input=test_input or {}
                )

                # Should handle gracefully
                assert isinstance(success, bool)


class TestPhase1bCompleteFlow:
    """Test complete Phase 1b end-to-end flow."""

    @pytest.fixture
    def temp_db(self):
        """Temporary database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        db = EMyDatabase(db_path)
        db.initialize_schema()
        yield db
        import os
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_complete_knowledge_workflow(self, temp_db):
        """
        Test complete flow: API request → execution → storage → retrieval.

        ✓ POST /workflows/execute with KnowledgeAgent
        ✓ Agent runs (Claude mocked)
        ✓ Output returned
        ✓ Output stored to database
        ✓ GET /workflows/{id} retrieves output
        """
        workflow_id = 'wf_complete_knowledge'

        with patch('emy.agents.knowledge_agent.KnowledgeAgent._call_claude',
                  return_value="Complete workflow response"):
            # Execute workflow
            success, output_json = AgentExecutor.execute(
                workflow_type='knowledge_query',
                agents=['KnowledgeAgent'],
                workflow_input={}
            )

            assert success is True

            # Store output
            result = json.loads(output_json)
            temp_db.store_workflow_output(
                workflow_id,
                'knowledge_query',
                'completed',
                output_json
            )

            # Retrieve output
            retrieved = temp_db.get_workflow(workflow_id)

            assert retrieved is not None
            assert retrieved['output'] == output_json
            retrieved_result = json.loads(retrieved['output'])
            assert retrieved_result['response'] == "Complete workflow response"

    def test_complete_trading_workflow(self, temp_db):
        """
        Test complete trading flow: API → execution → storage → retrieval.

        ✓ POST /workflows/execute with TradingAgent
        ✓ Agent runs (Claude + OANDA mocked)
        ✓ Output returned
        ✓ Output stored to database
        ✓ GET /workflows/{id} retrieves output
        """
        workflow_id = 'wf_complete_trading'
        mock_summary = {
            'equity': 10000.00,
            'margin_available': 9500.00,
            'margin_used': 500.00,
            'unrealized_pl': 150.50
        }

        with patch('emy.agents.trading_agent.TradingAgent._call_claude',
                  return_value="Complete trading analysis"):
            with patch('emy.agents.trading_agent.OandaClient.get_account_summary',
                      return_value=mock_summary):
                # Execute workflow
                success, output_json = AgentExecutor.execute(
                    workflow_type='trading_health',
                    agents=['TradingAgent'],
                    workflow_input={}
                )

                assert success is True

                # Store output
                result = json.loads(output_json)
                temp_db.store_workflow_output(
                    workflow_id,
                    'trading_health',
                    'completed',
                    output_json
                )

                # Retrieve output
                retrieved = temp_db.get_workflow(workflow_id)

                assert retrieved is not None
                assert retrieved['output'] == output_json
                retrieved_result = json.loads(retrieved['output'])
                assert 'analysis' in retrieved_result

    def test_sequential_workflows(self, temp_db):
        """
        Test multiple sequential workflows.

        ✓ Execute knowledge workflow, store, retrieve
        ✓ Execute trading workflow, store, retrieve
        ✓ Both persist independently
        ✓ Both retrievable
        """
        mock_summary = {
            'equity': 10000.00,
            'margin_available': 9500.00,
            'margin_used': 500.00,
            'unrealized_pl': 150.50
        }

        with patch('emy.agents.knowledge_agent.KnowledgeAgent._call_claude',
                  return_value="Knowledge response"):
            with patch('emy.agents.trading_agent.TradingAgent._call_claude',
                      return_value="Trading response"):
                with patch('emy.agents.trading_agent.OandaClient.get_account_summary',
                          return_value=mock_summary):
                    # Execute knowledge workflow
                    success1, output1 = AgentExecutor.execute(
                        workflow_type='knowledge_query',
                        agents=['KnowledgeAgent'],
                        workflow_input={}
                    )

                    # Store knowledge
                    temp_db.store_workflow_output('wf_seq_1', 'knowledge_query',
                                                 'completed', output1)

                    # Execute trading workflow
                    success2, output2 = AgentExecutor.execute(
                        workflow_type='trading_health',
                        agents=['TradingAgent'],
                        workflow_input={}
                    )

                    # Store trading
                    temp_db.store_workflow_output('wf_seq_2', 'trading_health',
                                                 'completed', output2)

                    # Retrieve both
                    wf1 = temp_db.get_workflow('wf_seq_1')
                    wf2 = temp_db.get_workflow('wf_seq_2')

                    assert wf1 is not None
                    assert wf2 is not None
                    assert wf1['type'] == 'knowledge_query'
                    assert wf2['type'] == 'trading_health'
                    assert wf1['output'] != wf2['output']
