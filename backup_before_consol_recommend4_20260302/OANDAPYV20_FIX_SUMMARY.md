# Quick Fix Summary: oandapyV20 Trailing Stop Loss Bug

## The Problem

**Files affected:**
- `Scalp-Engine/auto_trader_core.py` - Lines 514 & 542

**Current incorrect code:**
```python
r = trades.TradeClientExtensions(accountID=self.account_id, tradeID=trade_id, data=data)
```

**Why it's wrong:**
`TradeClientExtensions` is for updating trade metadata only (comments, tags). It does NOT support `stopLoss` or `trailingStopLoss` parameters. This endpoint only accepts `clientExtensions` field.

## The Solution

**Replace with:**
```python
r = trades.TradeCRCDO(accountID=self.account_id, tradeID=trade_id, data=data)
```

**What TradeCRCDO means:** "Trade Create/Replace/Cancel Dependent Orders"

**API Endpoint:** `PUT /v3/accounts/{accountID}/trades/{tradeID}/orders`

## Correct Data Structures

### For Fixed Stop Loss
```python
data = {
    "stopLoss": {
        "price": "1.0850",
        "timeInForce": "GTC"
    }
}
```

### For Trailing Stop Loss
```python
data = {
    "trailingStopLoss": {
        "distance": "0.0050",  # In price units, not pips!
        "timeInForce": "GTC"
    }
}
```

## Critical: Distance vs Pips

The `distance` field is in **quote currency units**, NOT pips:

- **EUR/USD:** 50 pips = `0.0050` distance
- **USD/JPY:** 50 pips = `0.50` distance (JPY has different pip size)
- **General formula:** distance_pips × pip_size = distance
  - pip_size = 0.01 for JPY pairs
  - pip_size = 0.0001 for non-JPY pairs

The current code correctly calculates this:
```python
pip_size = 0.01 if "JPY" in pair else 0.0001
distance = distance_pips * pip_size
```

## Changes Required

1. **Line 514** in `auto_trader_core.py`:
   ```python
   # Change FROM:
   r = trades.TradeClientExtensions(accountID=self.account_id, tradeID=trade_id, data=data)

   # Change TO:
   r = trades.TradeCRCDO(accountID=self.account_id, tradeID=trade_id, data=data)
   ```

2. **Line 542** in `auto_trader_core.py`:
   ```python
   # Change FROM:
   r = trades.TradeClientExtensions(accountID=self.account_id, tradeID=trade_id, data=data)

   # Change TO:
   r = trades.TradeCRCDO(accountID=self.account_id, tradeID=trade_id, data=data)
   ```

No other code changes are needed - the data structures are already correct!

## Reference Comparison

| Use Case | Endpoint Class | HTTP Verb | Purpose |
|----------|---|---|---|
| Update trade metadata (comments, tags) | `TradeClientExtensions` | PUT `/trades/{ID}/clientExtensions` | Metadata only |
| Update stop loss / trailing stop | `TradeCRCDO` | PUT `/trades/{ID}/orders` | Dependent orders |
| Create standalone order | `OrderCreate` | POST `/orders` | New orders |

## External Resources

- [TradeCRCDO Documentation](https://oanda-api-v20.readthedocs.io/en/latest/endpoints/trades/tradeCRCDO.html)
- [OANDA Trade Endpoint](https://developer.oanda.com/rest-live-v20/trade-ep/)
- [oandapyV20 Repository](https://github.com/hootnot/oanda-api-v20)
