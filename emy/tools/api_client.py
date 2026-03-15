"""
API client tools for Emy.

Wrappers for:
- OANDA Forex trading API
- Render deployment API
- Other external services
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import oandapyV20
    import oandapyV20.endpoints.accounts as accounts
    import oandapyV20.endpoints.trades as trades
    import oandapyV20.endpoints.orders as orders
    import oandapyV20.endpoints.pricing as pricing
    from oandapyV20.contrib.requests import MarketOrderRequest, TakeProfitDetails, StopLossDetails
    from oandapyV20.exceptions import V20Error
    OANDAPYV20_AVAILABLE = True
except ImportError:
    OANDAPYV20_AVAILABLE = False
    V20Error = None

logger = logging.getLogger('APIClient')


class OandaClient:
    """OANDA API client for forex trading data (using official oandapyV20 SDK)."""

    def __init__(self, access_token: str = None, account_id: str = None,
                 environment: str = 'practice'):
        """Initialize OANDA client."""
        self.access_token = access_token or os.getenv('OANDA_ACCESS_TOKEN')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID')
        self.environment = environment or os.getenv('OANDA_ENV', 'practice')

        if not OANDAPYV20_AVAILABLE:
            logger.error("oandapyV20 library not installed. Install with: pip install oandapyV20")
            self.client = None
        else:
            try:
                self.client = oandapyV20.API(
                    access_token=self.access_token,
                    environment=self.environment
                )
                logger.info(f"[OandaClient] Connected to {self.environment} environment")
            except Exception as e:
                logger.error(f"[OandaClient] Failed to initialize: {e}")
                self.client = None

    def get_account_summary(self) -> Optional[Dict]:
        """Get account status: equity, margin, P&L.

        Returns:
            dict with keys: equity, margin_available, margin_used, unrealized_pl
            Returns None if query fails
        """
        if not self.client:
            logger.error("[OandaClient] Client not initialized")
            return None

        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            self.client.request(r)

            account = r.response.get('account', {})
            result = {
                'equity': float(account.get('balance', 0)),
                'margin_available': float(account.get('marginAvailable', 0)),
                'margin_used': float(account.get('marginUsed', 0)),
                'unrealized_pl': float(account.get('unrealizedPL', 0))
            }
            logger.info(f"[OandaClient] Account summary: Equity=${result['equity']:.2f}, P&L=${result['unrealized_pl']:.2f}")
            return result
        except Exception as e:
            logger.error(f"[OandaClient] get_account_summary error: {e}")
            return None

    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get trade details by ID.

        Args:
            trade_id: OANDA trade ID (string)

        Returns:
            dict with trade details or None if not found
        """
        if not self.client:
            return None

        try:
            r = trades.TradeDetails(accountID=self.account_id, tradeID=trade_id)
            self.client.request(r)
            return r.response.get('trade', {})
        except Exception as e:
            logger.error(f"[OandaClient] get_trade error: {e}")
            return None

    def execute_trade(self, symbol: str, units: int, direction: str,
                     stop_loss: float, take_profit: float) -> Optional[Dict]:
        """Execute a market order on OANDA with SL/TP.

        Args:
            symbol: Instrument (e.g., 'EUR_USD')
            units: Number of units (positive = BUY, negative = SELL)
            direction: 'BUY' or 'SELL' (for reference)
            stop_loss: SL price
            take_profit: TP price

        Returns:
            dict with keys: trade_id, entry_price, status
            Returns None if execution fails

        Raises:
            ValueError: If credentials not configured
        """
        if not self.client:
            logger.error("[OandaClient] Client not initialized")
            return None

        # Determine actual units (positive for BUY, negative for SELL)
        actual_units = units if direction == 'BUY' else -units

        try:
            mo = MarketOrderRequest(
                instrument=symbol,
                units=actual_units,
                takeProfitOnFill=TakeProfitDetails(price=str(take_profit)).data,
                stopLossOnFill=StopLossDetails(price=str(stop_loss)).data
            )

            r = orders.OrderCreate(accountID=self.account_id, data=mo.data)
            self.client.request(r)

            response = r.response
            trade = response.get('orderFillTransaction', {})
            result = {
                'trade_id': trade.get('id'),
                'entry_price': float(trade.get('price', 0)),
                'status': 'OPEN'
            }
            logger.info(f"[OandaClient] Trade executed: {symbol} {actual_units} units @ {trade.get('price')}")
            return result
        except Exception as e:
            logger.error(f"[OandaClient] execute_trade error: {e}")
            return None

    def get_trades(self) -> List[Dict]:
        """Get list of all open trades with full details from OANDA API.

        Returns:
            list of dicts with full OANDA trade object details including:
            - id, instrument, initialUnits, currentUnits, openTime
            - pricingStatus, unrealizedPL, takeProfitOnFill, stopLossOnFill
            - clientExtensions (optional)
            Returns empty list if query fails or no open trades
        """
        if not self.client:
            return []

        try:
            r = trades.OpenTrades(accountID=self.account_id)
            self.client.request(r)

            trade_list = r.response.get('trades', [])
            return trade_list  # Return full OANDA trade objects
        except Exception as e:
            logger.error(f"[OandaClient] get_trades error: {e}")
            return []

    def get_open_trades(self) -> List[Dict]:
        """Get list of open trades.

        Returns:
            list of dicts with keys: trade_id, symbol, units, entry_price
            Returns empty list if query fails or no open trades
        """
        if not self.client:
            return []

        try:
            r = trades.OpenTrades(accountID=self.account_id)
            self.client.request(r)

            trade_list = r.response.get('trades', [])
            return [{
                'trade_id': t.get('id'),
                'symbol': t.get('instrument'),
                'units': int(t.get('initialUnits', 0)),
                'entry_price': float(t.get('price', 0))
            } for t in trade_list]
        except Exception as e:
            logger.error(f"[OandaClient] get_open_trades error: {e}")
            return []

    def list_open_trades(self) -> Optional[List[Dict]]:
        """Get list of open trades (alias for get_open_trades, for backward compatibility)."""
        trade_list = self.get_open_trades()
        return trade_list if trade_list else None

    def close_trade(self, trade_id: str, reason: str = None) -> Dict:
        """Close an open trade at market price.

        Args:
            trade_id: OANDA trade ID (string)
            reason: Optional reason for closure (for audit logging)

        Returns:
            dict with keys:
                - success (bool): True if closure succeeded
                - trade_id (str): The trade ID that was closed
                - realized_pnl (float or None): Realized profit/loss if successful
                - error (str or None): Error message if closure failed

        Examples:
            >>> result = client.close_trade("123456", reason="End of trading hours")
            >>> if result["success"]:
            ...     print(f"Trade closed with P&L: ${result['realized_pnl']:.2f}")
            ... else:
            ...     print(f"Failed to close trade: {result['error']}")
        """
        if not self.client:
            logger.error("[OandaClient] Client not initialized")
            return {
                "success": False,
                "trade_id": trade_id,
                "realized_pnl": None,
                "error": "Client not initialized"
            }

        # Validate trade_id is a string
        if not isinstance(trade_id, str):
            logger.error(f"[OandaClient] trade_id must be string, got {type(trade_id)}")
            return {
                "success": False,
                "trade_id": str(trade_id),
                "realized_pnl": None,
                "error": "trade_id must be string"
            }

        try:
            # Close the trade by creating a market order at FOK (fill or kill)
            # This sends a PATCH to /v3/accounts/{accountID}/trades/{tradeID}/orders
            r = trades.TradeClose(accountID=self.account_id, tradeID=trade_id)
            self.client.request(r)

            # Extract realized PL from response
            response = r.response
            realized_pnl = None

            # Try to get realized_pnl from orderFillTransaction
            if 'orderFillTransaction' in response:
                realized_pnl_str = response['orderFillTransaction'].get('realizedPL', '0')
                try:
                    realized_pnl = float(realized_pnl_str)
                except (ValueError, TypeError):
                    realized_pnl = 0.0

            # Log closure with reason if provided
            if reason:
                logger.info(f"[OandaClient] Trade {trade_id} closed: {reason} | P&L: ${realized_pnl:.2f}")
            else:
                logger.info(f"[OandaClient] Trade {trade_id} closed | P&L: ${realized_pnl:.2f}")

            return {
                "success": True,
                "trade_id": trade_id,
                "realized_pnl": realized_pnl,
                "error": None
            }

        except Exception as e:
            # Parse error details from exception
            error_msg = str(e)

            # Check for specific OANDA error codes
            if "404" in error_msg or "not found" in error_msg.lower():
                error_msg = "Trade not found"
            elif "400" in error_msg or "already closed" in error_msg.lower():
                error_msg = "Trade already closed"

            logger.error(f"[OandaClient] close_trade error for {trade_id}: {e}")

            return {
                "success": False,
                "trade_id": trade_id,
                "realized_pnl": None,
                "error": error_msg
            }


class RenderClient:
    """Render deployment API client for service monitoring."""

    def __init__(self, api_key: str = None):
        """Initialize Render client."""
        self.api_key = api_key or os.getenv('RENDER_API_KEY')
        self.base_url = 'https://api.render.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        } if self.api_key else {}

    def get_service_status(self, service_id: str) -> Optional[Dict]:
        """Get status of a Render service."""
        if not self.api_key:
            logger.warning("Render API key not configured")
            return None

        try:
            url = f"{self.base_url}/services/{service_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Render service status failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Render service status error: {e}")
            return None

    def list_services(self) -> Optional[list]:
        """List all Render services (placeholder)."""
        logger.warning("list_services not yet implemented")
        return None
