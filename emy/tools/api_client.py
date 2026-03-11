"""
API client tools for Emy.

Wrappers for:
- OANDA Forex trading API
- Render deployment API
- Other external services
"""

import os
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger('APIClient')


class OandaClient:
    """OANDA API client for forex trading data."""

    def __init__(self, access_token: str = None, account_id: str = None,
                 environment: str = 'practice'):
        """Initialize OANDA client."""
        self.access_token = access_token or os.getenv('OANDA_ACCESS_TOKEN')
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID')
        self.environment = environment or os.getenv('OANDA_ENV', 'practice')

        # Build base URL
        if self.environment == 'live':
            self.base_url = 'https://api-fxpractice.oanda.com/v3'
        else:
            self.base_url = 'https://api-fxpractice.oanda.com/v3'

        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def get_account_summary(self) -> Optional[Dict]:
        """Get account status: equity, margin, P&L.

        Returns:
            dict with keys: equity, margin_available, margin_used, unrealized_pl
            Returns None if query fails
        """
        if not self.access_token or not self.account_id:
            raise ValueError("OANDA credentials not configured")

        url = f"{self.base_url}/accounts/{self.account_id}/summary"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                account = response.json().get('account', {})
                result = {
                    'equity': float(account.get('balance', 0)),
                    'margin_available': float(account.get('marginAvailable', 0)),
                    'margin_used': float(account.get('marginUsed', 0)),
                    'unrealized_pl': float(account.get('unrealizedPL', 0))
                }
                logger.info(f"Account summary: Equity=${result['equity']:.2f}, P&L=${result['unrealized_pl']:.2f}")
                return result
            else:
                logger.error(f"OANDA account summary failed: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Exception fetching account summary: {e}")
            return None

    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get details for a specific trade."""
        try:
            url = f"{self.base_url}/accounts/{self.account_id}/trades/{trade_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"OANDA get_trade failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"OANDA get_trade error: {e}")
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
        if not self.access_token or not self.account_id:
            raise ValueError("OANDA credentials not configured")

        url = f"{self.base_url}/accounts/{self.account_id}/orders"

        # Determine actual units (positive for BUY, negative for SELL)
        actual_units = units if direction == 'BUY' else -units

        payload = {
            "order": {
                "type": "MARKET",
                "instrument": symbol,
                "units": str(actual_units),
                "takeProfitOnFill": {
                    "price": str(take_profit)
                },
                "stopLossOnFill": {
                    "price": str(stop_loss)
                }
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            if response.status_code == 201:
                data = response.json()
                trade = data.get('orderFillTransaction', {})
                result = {
                    'trade_id': trade.get('id'),
                    'entry_price': float(trade.get('price', 0)),
                    'status': 'OPEN'
                }
                logger.info(f"Trade executed: {symbol} {actual_units} units @ {trade.get('price')}")
                return result
            else:
                logger.error(f"OANDA trade execution failed: {response.status_code} — {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Exception during trade execution: {e}")
            return None

    def get_open_trades(self) -> list:
        """Get list of open trades.

        Returns:
            list of dicts with keys: trade_id, symbol, units, entry_price
            Returns empty list if query fails or no open trades
        """
        if not self.access_token or not self.account_id:
            return []

        url = f"{self.base_url}/accounts/{self.account_id}/openTrades"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                trades = response.json().get('trades', [])
                return [{
                    'trade_id': t.get('id'),
                    'symbol': t.get('instrument'),
                    'units': int(t.get('initialUnits', 0)),
                    'entry_price': float(t.get('price', 0))
                } for t in trades]
            else:
                logger.error(f"OANDA get_open_trades failed: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Exception fetching open trades: {e}")
            return []

    def list_open_trades(self) -> Optional[list]:
        """Get list of open trades (alias for get_open_trades, for backward compatibility)."""
        trades = self.get_open_trades()
        return trades if trades else None


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
