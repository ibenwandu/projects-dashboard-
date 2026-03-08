# Update Market State Timestamp

## Problem

The test `market_state.json` file has timestamp `"2025-01-10T12:00:00Z"`, which is likely older than 4 hours. The `MarketStateReader` considers states older than 4 hours as "stale" and returns `None`, even though the file exists and is readable.

## Solution: Update Timestamp to Current Time

**In Trade-Alerts Shell (or Scalp-Engine UI Shell):**

```bash
cat > /var/data/market_state.json << 'EOF'
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "global_bias": "NEUTRAL",
    "regime": "NORMAL",
    "approved_pairs": ["EUR/USD", "USD/JPY"],
    "opportunities": [],
    "long_count": 0,
    "short_count": 0,
    "total_opportunities": 0
}
EOF
```

**OR use Python to generate with current timestamp:**

```bash
python3 << 'PYTHON_SCRIPT'
import json
from datetime import datetime

state = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "global_bias": "NEUTRAL",
    "regime": "NORMAL",
    "approved_pairs": ["EUR/USD", "USD/JPY"],
    "opportunities": [],
    "long_count": 0,
    "short_count": 0,
    "total_opportunities": 0
}

with open('/var/data/market_state.json', 'w') as f:
    json.dump(state, f, indent=4)

print("✅ Market state file updated with current timestamp")
print(f"   Timestamp: {state['timestamp']}")
PYTHON_SCRIPT

# Verify it was created
cat /var/data/market_state.json
```

---

## Alternative: Disable Staleness Check (For Testing Only)

If you want to disable the staleness check temporarily for testing, you can modify the `state_reader.py`:

**In `state_reader.py`, line ~136, change:**
```python
if age_hours > 4:
    return None  # State is too old
```

**To:**
```python
if age_hours > 4:
    # Temporarily disable staleness check for testing
    # return None  # State is too old
    pass  # Allow stale states for testing
```

**⚠️ WARNING**: Only do this for testing! In production, you should always have a fresh state or update the timestamp.

---

## Expected Result

After updating the timestamp:
- ✅ File exists: True
- ✅ File is readable: True
- ✅ Timestamp is current: True (less than 4 hours old)
- ✅ State loads successfully: True
- ✅ UI displays market state: True
- ✅ No warning message: True

---

**Last Updated**: 2025-01-10