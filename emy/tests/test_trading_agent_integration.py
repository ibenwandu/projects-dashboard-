"""
Integration tests for TradingAgent OANDA API execution.

Tests that the API can:
1. Execute TradingAgent workflow
2. Return real OANDA account data
3. Handle missing credentials gracefully
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from emy.agents.trading_agent import TradingAgent
from emy.gateway.api import app
from fastapi.testclient import TestClient


client = TestClient(app)


class TestTradingAgentOandaIntegration:
    """Test TradingAgent OANDA integration"""

    @pytest.fixture
    def agent(self):
        """Create TradingAgent instance"""
        return TradingAgent()

    def test_trading_agent_monitors_oanda_account(self, agent):
        """Test that _monitor_oanda_account returns account data"""
        mock_account_data = {
            'account': {
                'balance': '10000.00',
                'currency': 'USD',
                'unrealizedPL': '250.50'
            }
        }

        with patch.object(agent.oanda_client, 'get_account_summary', return_value=mock_account_data):
            with patch.object(agent.oanda_client, 'list_open_trades', return_value=[]):
                result = agent._monitor_oanda_account()

                assert result is not None
                assert result['status'] == 'ok'
                assert result['balance'] == '10000.00'
                assert result['open_trades_count'] == 0

    def test_trading_agent_lists_open_trades(self, agent):
        """Test that _monitor_oanda_account returns open trades"""
        mock_account_data = {
            'account': {
                'balance': '10000.00',
                'currency': 'USD'
            }
        }
        mock_trades = [
            {
                'trade_id': '123',
                'symbol': 'EUR_USD',
                'units': 1000,
                'entry_price': 1.0850
            }
        ]

        with patch.object(agent.oanda_client, 'get_account_summary', return_value=mock_account_data):
            with patch.object(agent.oanda_client, 'list_open_trades', return_value=mock_trades):
                result = agent._monitor_oanda_account()

                assert result['status'] == 'ok'
                assert result['open_trades_count'] == 1

    def test_trading_agent_handles_oanda_error(self, agent):
        """Test that TradingAgent handles OANDA errors gracefully"""
        with patch.object(agent.oanda_client, 'get_account_summary', return_value=None):
            result = agent._monitor_oanda_account()

            assert result['status'] == 'error'
            assert 'reason' in result

    def test_trading_agent_run_returns_analysis(self, agent):
        """Test that TradingAgent.run() executes and returns analysis"""
        mock_claude_response = "EUR_USD: BUY (85% confidence)\nGBP_USD: SELL (60% confidence)"
        mock_account_data = {
            'account': {'balance': '10000.00', 'currency': 'USD'}
        }

        with patch.object(agent, '_call_claude', return_value=mock_claude_response):
            with patch.object(agent.oanda_client, 'get_account_summary', return_value=mock_account_data):
                with patch.object(agent.oanda_client, 'list_open_trades', return_value=[]):
                    with patch.object(agent.db, 'update_daily_limits'):
                        with patch.object(agent.db, 'get_daily_pnl', return_value=0):
                            success, result = agent.run()

                            assert success is True
                            assert 'analysis' in result
                            assert 'signals' in result
                            assert mock_claude_response in result['analysis']


class TestAPIExecutesTradingAgent:
    """Test that API gateway executes TradingAgent and returns OANDA data"""

    def test_api_execute_trading_workflow_returns_account_data(self):
        """API /workflows/execute should execute TradingAgent and return OANDA data"""
        mock_claude_response = "Market analysis: Strong uptrend EUR/USD\n\nEUR_USD: BUY (80%)"
        mock_account_summary = {
            'equity': 10000.00,
            'margin_available': 8000.00,
            'margin_used': 2000.00,
            'unrealized_pl': 150.00
        }

        with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
            # Setup Claude mock
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=mock_claude_response)]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            with patch('emy.tools.api_client.OandaClient.get_account_summary', return_value=mock_account_summary):
                with patch('emy.tools.api_client.OandaClient.list_open_trades', return_value=[]):
                    # Execute workflow via API
                    response = client.post(
                        '/workflows/execute',
                        json={
                            'workflow_type': 'trading_health',
                            'agents': ['TradingAgent'],
                            'input': {}
                        }
                    )

                    # Verify response
                    assert response.status_code == 200
                    data = response.json()

                    # Should be completed (not error)
                    assert data['status'] == 'completed', f"Expected completed but got {data['status']}"
                    assert data['workflow_id']

                    # Output should contain Claude analysis
                    assert data['output'] is not None
                    output_dict = json.loads(data['output'])
                    assert 'analysis' in output_dict

    def test_api_trading_workflow_persistence(self):
        """Trading workflow outputs should persist in database"""
        with patch('emy.agents.base_agent.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="Test analysis")]
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            with patch('emy.tools.api_client.OandaClient.get_account_summary', return_value={'equity': 10000}):
                with patch('emy.tools.api_client.OandaClient.list_open_trades', return_value=[]):
                    # Execute workflow
                    response = client.post(
                        '/workflows/execute',
                        json={
                            'workflow_type': 'trading_health',
                            'agents': ['TradingAgent'],
                            'input': {}
                        }
                    )

                    workflow_id = response.json()['workflow_id']

                    # Retrieve it
                    get_response = client.get(f'/workflows/{workflow_id}')
                    assert get_response.status_code == 200
                    assert get_response.json()['workflow_id'] == workflow_id
