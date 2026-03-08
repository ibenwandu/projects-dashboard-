# oandapyV20 Research: Correct Endpoint for Updating Trade Stop Loss & Trailing Stop

## Executive Summary

The current code in `Scalp-Engine/auto_trader_core.py` is **incorrectly using `trades.TradeClientExtensions`** which is for updating metadata (clientID, tags, comments), NOT for updating trade stop loss or trailing stop values.

## Issue Identified

### Current (Incorrect) Code

**Location:** `Scalp-Engine/auto_trader_core.py` lines 503-556

```python
# WRONG: TradeClientExtensions is for metadata only
def update_stop_loss(self, trade_id: str, new_sl: float, pair: str) -> bool:
    data = {
        "stopLoss": {
            "price": str(rounded_sl)
        }
    }
    r = trades.TradeClientExtensions(accountID=self.account_id, tradeID=trade_id, data=data)
    # This fails because TradeClientExtensions doesn't accept stopLoss parameter

def convert_to_trailing_stop(self, trade_id: str, distance_pips: float, pair: str) -> bool:
    data = {
        "trailingStopLoss": {
            "distance": str(distance)
        }
    }
    r = trades.TradeClientExtensions(accountID=self.account_id, tradeID=trade_id, data=data)
    # Same issue - wrong endpoint
```

## Correct Solution

### The Right Endpoint Class: `trades.TradeCRCDO`

**Full Name:** Trade Create Replace Cancel Dependent Orders

**Import:** `from oandapyV20.endpoints import trades`

**HTTP Method:** PUT

**OANDA v20 API Endpoint:** `v3/accounts/{accountID}/trades/{tradeID}/orders`

### How to Use `TradeCRCDO`

```python
import oandapyV20.endpoints.trades as trades

# For updating stop loss to a fixed price
data = {
    "stopLoss": {
        "price": "1.0850",
        "timeInForce": "GTC"  # Optional, defaults to GTC
    }
}
r = trades.TradeCRCDO(accountID=account_id, tradeID=trade_id, data=data)
response = client.request(r)

# For updating to a trailing stop loss
data = {
    "trailingStopLoss": {
        "distance": "0.0050",  # Distance in price units (not pips)
        "timeInForce": "GTC"   # Optional, defaults to GTC
    }
}
r = trades.TradeCRCDO(accountID=account_id, tradeID=trade_id, data=data)
response = client.request(r)
```

## Data Structure Requirements

### For Fixed Stop Loss

```python
data = {
    "stopLoss": {
        "price": "<decimal>",           # REQUIRED: Fixed price to trigger SL
        "timeInForce": "GTC|GTD|GFD",  # OPTIONAL: Default "GTC"
        "triggerCondition": "TRIGGER_DEFAULT|TRIGGER_BID|TRIGGER_ASK"  # OPTIONAL
    }
}
```

**Fields:**
- `price` (required): The fixed price at which the stop loss triggers
- `timeInForce` (optional, default "GTC"):
  - `GTC` = Good Till Cancelled (no expiry)
  - `GTD` = Good Till Date (requires `gtdTime`)
  - `GFD` = Good For Day (expires at end of trading day)
- `triggerCondition` (optional, default "DEFAULT"): Specifies bid/ask/default

### For Trailing Stop Loss

```python
data = {
    "trailingStopLoss": {
        "distance": "<decimal>",        # REQUIRED: Distance from market price
        "timeInForce": "GTC|GTD|GFD",  # OPTIONAL: Default "GTC"
        "triggerCondition": "TRIGGER_DEFAULT|TRIGGER_BID|TRIGGER_ASK"  # OPTIONAL
    }
}
```

**Fields:**
- `distance` (required): Price distance in quote currency (NOT pips)
  - Example: For EUR/USD, `0.0050` = 50 pips
  - Example: For USD/JPY, `0.50` = 50 pips (different pip size)
- `timeInForce` (optional, default "GTC"): Same options as stopLoss
- `triggerCondition` (optional): Same options as stopLoss

### Cancelling Stop Loss or Trailing Stop Loss

```python
data = {
    "stopLoss": None,          # Set to null to cancel
    # OR
    "trailingStopLoss": None   # Set to null to cancel
}
r = trades.TradeCRCDO(accountID=account_id, tradeID=trade_id, data=data)
```

## Complete Fixed Code Example

### For updating fixed stop loss

```python
def update_stop_loss(self, trade_id: str, new_sl: float, pair: str) -> bool:
    """Update stop loss to fixed price using TradeCRCDO"""
    try:
        # Round stop loss to OANDA precision
        rounded_sl = round_price_for_oanda(new_sl, pair)

        # Correct: Use TradeCRCDO for updating stop loss
        data = {
            "stopLoss": {
                "price": str(rounded_sl),
                "timeInForce": "GTC"
            }
        }
        r = trades.TradeCRCDO(accountID=self.account_id, tradeID=trade_id, data=data)

        try:
            self._request_with_retry(r, "update_stop_loss")
            self.logger.info(f"✅ Updated SL for trade {trade_id} to {new_sl}")
            return True
        except V20Error as e:
            error_msg = getattr(e, 'msg', str(e))
            self.logger.error(f"❌ OANDA API error updating SL for trade {trade_id}: {error_msg}")
            return False

    except Exception as e:
        self.logger.error(f"❌ Error updating SL: {e}", exc_info=True)
        return False
```

### For converting to trailing stop loss

```python
def convert_to_trailing_stop(self, trade_id: str, distance_pips: float, pair: str) -> bool:
    """Convert fixed SL to trailing stop using TradeCRCDO"""
    try:
        # Calculate distance in price units (not pips)
        pip_size = 0.01 if "JPY" in pair else 0.0001
        distance = distance_pips * pip_size

        # Correct: Use TradeCRCDO for updating trailing stop
        data = {
            "trailingStopLoss": {
                "distance": str(distance),
                "timeInForce": "GTC"
            }
        }
        r = trades.TradeCRCDO(accountID=self.account_id, tradeID=trade_id, data=data)

        try:
            self._request_with_retry(r, "convert_to_trailing_stop")
            self.logger.info(
                f"🎯 Converted to trailing stop for trade {trade_id}: "
                f"{distance_pips} pips"
            )
            return True
        except V20Error as e:
            error_msg = getattr(e, 'msg', str(e))
            self.logger.error(f"❌ OANDA API error converting to trailing stop: {error_msg}")
            return False

    except Exception as e:
        self.logger.error(f"❌ Error converting to trailing stop: {e}", exc_info=True)
        return False
```

## Alternative Helper Classes (For Comparison)

### TrailingStopLossDetails (for new orders, not trade updates)

**Import:** `from oandapyV20.contrib.requests import TrailingStopLossDetails`

**Use Case:** For attaching trailing stop to NEW orders being created

```python
from oandapyV20.contrib.requests import MarketOrderRequest, TrailingStopLossDetails

# Create trailing stop loss specification
trailingStopLossOnFill = TrailingStopLossDetails(
    distance=0.0050,           # 50 pips for EUR/USD
    timeInForce='GTC',
    clientExtensions=None
)

# Attach to market order
order = MarketOrderRequest(
    instrument="EUR_USD",
    units=10000,
    trailingStopLossOnFill=trailingStopLossOnFill.data
)
```

**Note:** This is for ORDER CREATION, not for updating existing trades. For updating trades, use `TradeCRCDO` directly.

### TrailingStopLossOrderRequest

**Import:** `from oandapyV20.contrib.requests import TrailingStopLossOrderRequest`

**Use Case:** For creating a standalone trailing stop loss order (separate from opening a trade)

```python
from oandapyV20.contrib.requests import TrailingStopLossOrderRequest
import oandapyV20.endpoints.orders as orders

# Create trailing stop loss order for existing trade
ordr = TrailingStopLossOrderRequest(
    tradeID="1234",
    distance=20,
    timeInForce="GTC"
)

# Send via OrderCreate endpoint (NOT TradeCRCDO)
r = orders.OrderCreate(accountID, data=ordr.data)
response = client.request(r)
```

**Note:** This creates a NEW order linked to a trade, rather than updating the trade's dependent orders directly.

## Key Differences

| Aspect | TradeClientExtensions | TradeCRCDO | TrailingStopLossOrderRequest |
|--------|----------------------|-----------|------------------------------|
| **Purpose** | Update metadata (tags, comments) | Update dependent orders (SL, TP, TSL) | Create standalone TSL order |
| **What Updates** | clientExtensions only | stopLoss, takeProfit, trailingStopLoss | Creates new order |
| **Endpoint** | PUT /trades/{tradeID}/clientExtensions | PUT /trades/{tradeID}/orders | POST /orders |
| **Accept stopLoss** | NO | YES | N/A (creates order) |
| **Accept trailingStopLoss** | NO | YES | YES |

## OANDA API Response Example

After successfully calling `TradeCRCDO` with trailing stop loss data:

```json
{
  "tradeOrdersCancelled": [],
  "createRelatedTransactions": [],
  "trailingStopLossOrderTransaction": {
    "id": "248",
    "time": "2016-10-17T19:35:40.195676713Z",
    "type": "CREATE_ORDER",
    "instrument": "EUR_USD",
    "accountID": "101-004-1000000-001",
    "userID": "user-123",
    "batchID": "248",
    "requestID": "65432100",
    "tradeID": "247",
    "clientTradeID": "trade-247",
    "type": "TRAILING_STOP_LOSS",
    "instrument": "EUR_USD",
    "units": "0",
    "timeInForce": "GTC",
    "triggerCondition": "DEFAULT",
    "trailingStopValue": "1.05298",
    "distance": "0.00500",
    "priceBound": "0",
    "reason": "TRADE_ON_FILL",
    "clientExtensions": null,
    "orderFillTransactionID": "248",
    "tradeOpenedID": "",
    "tradeReducedID": "",
    "tradeClosedIDs": [
      "247"
    ],
    "cancellingTransactionID": "",
    "cancelledTime": ""
  },
  "relatedTransactionIDs": [ "248" ]
}
```

## Important Notes

1. **Distance vs Price:** For trailing stop loss, the `distance` parameter is in price units (quote currency), NOT pips. For EUR/USD, 50 pips = 0.0050. For USD/JPY, 50 pips = 0.50.

2. **Pip Size Calculation:**
   - For JPY pairs: 1 pip = 0.01
   - For non-JPY pairs: 1 pip = 0.0001

3. **Cancelling Orders:** Set stopLoss or trailingStopLoss to `null` to cancel the order, or omit the field to leave it unchanged.

4. **Modifying without cancelling:** If you set both `stopLoss` and `trailingStopLoss` in the same request, the first successfully replaces the stop loss order and the second replaces or creates the trailing stop loss order.

5. **TradeClientExtensions Purpose:** This endpoint is ONLY for updating metadata like `clientID`, `comment`, and other custom metadata tags - NOT for updating price-based orders.

## References

- [TradeCRCDO Endpoint Documentation](https://oanda-api-v20.readthedocs.io/en/latest/endpoints/trades/tradeCRCDO.html)
- [TrailingStopLossDetails Helper Class](https://oanda-api-v20.readthedocs.io/en/latest/contrib/support/trailingstoplossdetails.html)
- [StopLossDetails Helper Class](https://oanda-api-v20.readthedocs.io/en/latest/contrib/support/stoplossdetails.html)
- [OANDA Trade Endpoint (v20 API)](https://developer.oanda.com/rest-live-v20/trade-ep/)
- [oandapyV20 GitHub Repository](https://github.com/hootnot/oanda-api-v20)
- [OANDA v20 Python Samples](https://github.com/oanda/v20-python-samples/blob/master/src/order/trailing_stop_loss.py)

## Summary

**Fix Required:** Replace `trades.TradeClientExtensions` with `trades.TradeCRCDO` in both `update_stop_loss()` and `convert_to_trailing_stop()` methods.

This is a critical bug fix because `TradeClientExtensions` doesn't support stop loss parameters and will either throw an error or silently fail to update the stop loss/trailing stop values.
