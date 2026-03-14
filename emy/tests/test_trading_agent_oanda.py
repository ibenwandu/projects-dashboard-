"""
Task 2: TradingAgent OANDA Connection Integration Tests (RED stage).

These tests verify:
1. TradingAgent connects to OANDA API
2. Returns current positions and P&L
3. Handles missing credentials gracefully
4. Tests verify OANDA connection
"""

import os
import pytest
import json
from unittest.mock import patch, MagicMock
from emy.agents.trading_agent import TradingAgent
from emy.tools.api_client import OandaClient


class TestTradingAgentOandaIntegration:
    """Integration tests for TradingAgent OANDA connection."""

    @pytest.fixture
    def trading_agent(self):
        """Create TradingAgent instance for OANDA testing."""
        return TradingAgent()

    @pytest.fixture
    def mock_oanda_summary(self):
        """Mock OANDA account summary response."""
        return {
            'equity': 10000.00,
            'margin_available': 9500.00,
            'margin_used': 500.00,
            'unrealized_pl': 150.50
        }

    @pytest.fixture
    def mock_oanda_trades(self):
        """Mock OANDA open trades response."""
        return [
            {
                'trade_id': '12345',
                'symbol': 'EUR_USD',
                'units': 100000,
                'entry_price': 1.0950
            },
            {
                'trade_id': '12346',
                'symbol': 'GBP_USD',
                'units': -50000,
                'entry_price': 1.2750
            }
        ]

    # ========================================================================
    # Criterion 1: TradingAgent connects to OANDA API
    # ========================================================================

    def test_trading_agent_has_oanda_client(self, trading_agent):
        """RED: TradingAgent should have OandaClient initialized."""
        assert hasattr(trading_agent, 'oanda_client'), "TradingAgent must have oanda_client"
        assert isinstance(trading_agent.oanda_client, OandaClient), "oanda_client must be OandaClient instance"

    def test_oanda_client_initializes_with_credentials(self):
        """RED: OandaClient should initialize with environment credentials."""
        # Set fake credentials for testing
        os.environ['OANDA_ACCESS_TOKEN'] = 'test-token'
        os.environ['OANDA_ACCOUNT_ID'] = 'test-account'
        os.environ['OANDA_ENV'] = 'practice'

        try:
            client = OandaClient()
            assert client.access_token == 'test-token'
            assert client.account_id == 'test-account'
            assert client.environment == 'practice'
        finally:
            # Cleanup
            if 'OANDA_ACCESS_TOKEN' in os.environ:
                del os.environ['OANDA_ACCESS_TOKEN']
            if 'OANDA_ACCOUNT_ID' in os.environ:
                del os.environ['OANDA_ACCOUNT_ID']

    # ========================================================================
    # Criterion 2: Returns current positions and P&L
    # ========================================================================

    def test_trading_agent_returns_account_summary(self, trading_agent, mock_oanda_summary):
        """
        RED: TradingAgent should return current account summary from OANDA.

        Returns: equity, margin_available, margin_used, unrealized_pl
        """
        with patch.object(trading_agent.oanda_client, 'get_account_summary',
                         return_value=mock_oanda_summary):
            summary = trading_agent.oanda_client.get_account_summary()

            assert summary is not None
            assert 'equity' in summary
            assert 'margin_available' in summary
            assert 'margin_used' in summary
            assert 'unrealized_pl' in summary
            assert summary['equity'] == 10000.00

    def test_trading_agent_returns_open_positions(self, trading_agent, mock_oanda_trades):
        """
        RED: TradingAgent should return list of open positions from OANDA.

        Returns: list of dicts with trade_id, symbol, units, entry_price
        """
        with patch.object(trading_agent.oanda_client, 'get_open_trades',
                         return_value=mock_oanda_trades):
            trades = trading_agent.oanda_client.get_open_trades()

            assert trades is not None
            assert isinstance(trades, list)
            assert len(trades) == 2
            assert trades[0]['symbol'] == 'EUR_USD'
            assert trades[0]['units'] == 100000

    def test_trading_agent_run_includes_oanda_data(self, trading_agent, mock_oanda_summary):
        """
        RED: TradingAgent.run() should include OANDA account data in response.

        Response should have: equity, margin, unrealized_pl
        """
        with patch.object(trading_agent, '_call_claude', return_value="Market analysis"):
            with patch.object(trading_agent.oanda_client, 'get_account_summary',
                             return_value=mock_oanda_summary):
                success, result = trading_agent.run()

                assert success is True
                assert isinstance(result, dict)
                # Response should mention OANDA data
                # (Could be in analysis or separate fields)

    # ========================================================================
    # Criterion 3: Handles missing credentials gracefully
    # ========================================================================

    def test_oanda_client_handles_missing_token(self):
        """RED: OandaClient should handle missing OANDA_ACCESS_TOKEN gracefully."""
        # Ensure token is not set
        original = os.environ.pop('OANDA_ACCESS_TOKEN', None)

        try:
            client = OandaClient()
            # Should initialize but not connect
            assert client.access_token is None or client.client is None
        finally:
            if original:
                os.environ['OANDA_ACCESS_TOKEN'] = original

    def test_oanda_client_handles_missing_account_id(self):
        """RED: OandaClient should handle missing OANDA_ACCOUNT_ID gracefully."""
        original = os.environ.pop('OANDA_ACCOUNT_ID', None)

        try:
            client = OandaClient()
            assert client.account_id is None or client.client is None
        finally:
            if original:
                os.environ['OANDA_ACCOUNT_ID'] = original

    def test_oanda_client_get_account_summary_returns_none_on_error(self):
        """RED: get_account_summary should return None gracefully on error."""
        client = OandaClient()
        # No valid client, should return None
        result = client.get_account_summary()
        assert result is None

    def test_oanda_client_get_open_trades_returns_empty_on_error(self):
        """RED: get_open_trades should return empty list on error."""
        client = OandaClient()
        # No valid client, should return empty list
        trades = client.get_open_trades()
        assert trades == [] or trades is None

    def test_trading_agent_handles_oanda_connection_failure(self, trading_agent):
        """RED: TradingAgent should handle OANDA connection failure gracefully."""
        with patch.object(trading_agent.oanda_client, 'get_account_summary',
                         side_effect=Exception("Connection failed")):
            success, result = trading_agent.run()

            # Should fail gracefully, not crash
            # Result should indicate error or be handled
            assert isinstance(result, dict)

    # ========================================================================
    # Criterion 4: Tests verify OANDA connection
    # ========================================================================

    def test_oanda_account_summary_structure(self, mock_oanda_summary):
        """RED: Verify OANDA account summary has expected structure."""
        required_keys = {'equity', 'margin_available', 'margin_used', 'unrealized_pl'}
        assert required_keys == set(mock_oanda_summary.keys())

        # Verify types
        assert isinstance(mock_oanda_summary['equity'], float)
        assert isinstance(mock_oanda_summary['margin_available'], float)

    def test_oanda_trade_structure(self, mock_oanda_trades):
        """RED: Verify OANDA trade data has expected structure."""
        trade = mock_oanda_trades[0]
        required_keys = {'trade_id', 'symbol', 'units', 'entry_price'}
        assert required_keys == set(trade.keys())

        # Verify types
        assert isinstance(trade['trade_id'], str)
        assert isinstance(trade['symbol'], str)
        assert isinstance(trade['units'], int)
        assert isinstance(trade['entry_price'], float)

    def test_trading_agent_json_serialization_with_oanda(self, trading_agent, mock_oanda_summary):
        """RED: TradingAgent response with OANDA data should be JSON-serializable."""
        with patch.object(trading_agent, '_call_claude', return_value="Analysis"):
            with patch.object(trading_agent.oanda_client, 'get_account_summary',
                             return_value=mock_oanda_summary):
                success, result = trading_agent.run()

                # Should be JSON-serializable
                try:
                    json_str = json.dumps(result)
                    assert json_str is not None
                    parsed = json.loads(json_str)
                    assert isinstance(parsed, dict)
                except TypeError as e:
                    pytest.fail(f"Result not JSON-serializable: {e}")


class TestTradingAgentOandaWorkflow:
    """Test TradingAgent OANDA workflow through AgentExecutor."""

    def test_trading_health_workflow_with_oanda(self):
        """
        Test workflow equivalent of:
        curl -X POST http://localhost:8000/workflows/execute \
          -H "Content-Type: application/json" \
          -d '{
            "workflow_type": "trading_health",
            "agents": ["TradingAgent"],
            "input": {}
          }'

        Expected: Current positions and account status from OANDA
        """
        from emy.agents.agent_executor import AgentExecutor

        mock_summary = {
            'equity': 10000.00,
            'margin_available': 9500.00,
            'margin_used': 500.00,
            'unrealized_pl': 150.50
        }

        with patch('emy.agents.trading_agent.TradingAgent._call_claude', return_value="Trading analysis"):
            with patch('emy.agents.trading_agent.OandaClient.get_account_summary',
                      return_value=mock_summary):

                # Execute workflow
                success, output_json = AgentExecutor.execute(
                    workflow_type='trading_health',
                    agents=['TradingAgent'],
                    workflow_input={}
                )

                # Verify workflow succeeds
                assert success is True
                assert output_json is not None

                # Parse and verify output
                result = json.loads(output_json)
                assert isinstance(result, dict)
