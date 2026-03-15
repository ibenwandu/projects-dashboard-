"""Unit tests for OandaClient."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from emy.tools.api_client import OandaClient


class TestCloseTradeSuccess:
    """Test close_trade() method - success case."""

    def test_close_trade_success(self):
        """Test successful trade closure.

        Verifies:
        - Trade exists on OANDA
        - API returns 200 with realized_pnl
        - Method returns {"success": True, "trade_id": "123456", "realized_pnl": 45.50, "error": None}
        """
        # Arrange
        client = OandaClient(
            access_token="test_token",
            account_id="test_account",
            environment="practice"
        )

        # Mock the client.request method
        mock_response = {
            'orderFillTransaction': {
                'id': '789012',
                'tradesClosed': [{'tradeID': '123456', 'realizedPL': '45.50'}],
                'realizedPL': '45.50'
            }
        }

        with patch.object(client.client, 'request') as mock_request:
            # Setup the mock to populate response attribute
            def set_response(request_obj):
                request_obj.response = mock_response

            mock_request.side_effect = set_response

            # Act
            result = client.close_trade(trade_id="123456", reason="End of trading hours")

            # Assert
            assert result is not None
            assert result["success"] is True
            assert result["trade_id"] == "123456"
            assert result["realized_pnl"] == 45.50
            assert result["error"] is None

    def test_close_trade_not_found(self):
        """Test closing a trade that doesn't exist.

        Verifies:
        - API returns 404
        - Method returns {"success": False, "trade_id": "999999", "realized_pnl": None, "error": "Trade not found"}
        """
        # Arrange
        client = OandaClient(
            access_token="test_token",
            account_id="test_account",
            environment="practice"
        )

        # Mock the client.request method to raise 404 error
        with patch.object(client.client, 'request') as mock_request:
            from oandapyV20.exceptions import V20Error

            mock_request.side_effect = V20Error("Trade not found", 404)

            # Act
            result = client.close_trade(trade_id="999999")

            # Assert
            assert result is not None
            assert result["success"] is False
            assert result["trade_id"] == "999999"
            assert result["realized_pnl"] is None
            assert result["error"] is not None
            assert "not found" in result["error"].lower() or "404" in result["error"]

    def test_close_trade_already_closed(self):
        """Test closing a trade that's already closed.

        Verifies:
        - API returns 400
        - Method returns {"success": False, "trade_id": "123456", "realized_pnl": None, "error": "Trade already closed"}
        """
        # Arrange
        client = OandaClient(
            access_token="test_token",
            account_id="test_account",
            environment="practice"
        )

        # Mock the client.request method to raise 400 error
        with patch.object(client.client, 'request') as mock_request:
            from oandapyV20.exceptions import V20Error

            mock_request.side_effect = V20Error("Trade already closed", 400)

            # Act
            result = client.close_trade(trade_id="123456")

            # Assert
            assert result is not None
            assert result["success"] is False
            assert result["trade_id"] == "123456"
            assert result["realized_pnl"] is None
            assert result["error"] is not None
            assert "closed" in result["error"].lower() or "400" in result["error"]
