# Phase 5: Integration Guide

How to integrate Phase 5 monitoring into Trade-Alerts and Scalp-Engine

---

## Overview

Phase 5 monitoring captures trade data in two ways:

1. **Automatic**: Scalp-Engine logs trades directly to Phase 5 database
2. **Manual**: Phase 5 monitor parses logs and extracts trade data

This guide explains both approaches and how to implement them.

---

## Approach 1: Automatic Integration (Recommended)

Scalp-Engine directly logs trades to Phase 5 database as they execute.

### Implementation

**File**: `Scalp-Engine/auto_trader_core.py`

**In the `close_trade()` method** (after trade closes):

```python
def close_trade(self, trade_id: str, reason: str = "", exit_price: float = None):
    """Close a trade and log to Phase 5"""

    trade = self.active_trades.get(trade_id)
    if not trade:
        return False

    # ... existing close logic ...

    # PHASE 5: Log trade to monitoring database
    from phase5_monitor import Phase5Monitor
    monitor = Phase5Monitor()

    trade_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'pair': trade.pair,
        'direction': trade.direction,
        'entry_price': trade.entry_price,
        'stop_loss': trade.stop_loss,
        'take_profit': trade.take_profit,
        'outcome': trade.outcome,  # WIN_TP1, WIN_TP2, LOSS_SL, etc
        'pnl_pips': trade.unrealized_pnl,
        'confidence': trade.confidence,
        'consensus_level': trade.consensus_level,
        'source': trade.opportunity_source,
        'phase4_filters_passed': True,  # All executed trades passed filters
        'notes': f'Closed by {reason}'
    }

    monitor.log_trade(trade_data)

    return True
```

**In the `open_trade()` method** (when trade is rejected by Phase 4 filter):

```python
def open_trade(self, opportunity: Dict, market_state: Dict):
    """Open trade with Phase 4 filters and Phase 5 logging"""

    # ... existing checks ...

    # PHASE 4 STEP 2A: Check confidence
    should_skip_confidence, confidence_reason = self.should_filter_by_low_confidence(opportunity)
    if should_skip_confidence:
        # PHASE 5: Log rejection
        from phase5_monitor import Phase5Monitor
        monitor = Phase5Monitor()

        rejection_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'pair': opportunity.get('pair', ''),
            'direction': opportunity.get('direction', '').upper(),
            'filter_type': 'CONFIDENCE',
            'reason': confidence_reason,
            'confidence': opportunity.get('confidence'),
            'consensus_level': opportunity.get('consensus_level'),
            'llm_sources': ', '.join(opportunity.get('llm_sources', []))
        }
        monitor.log_rejection(rejection_data)

        self.logger.warning(f"⏭️ SKIPPING: {confidence_reason}")
        return None

    # ... repeat for each filter (LLM accuracy, JPY rules, etc) ...

    # If trade passes all filters
    trade = self._create_trade_from_opportunity(opportunity, market_state)
    # Execute trade...
```

### Benefits

- ✅ Real-time logging as trades complete
- ✅ Automatic and consistent
- ✅ No manual intervention needed
- ✅ Dashboard updates immediately

### Implementation Checklist

- [ ] Import Phase5Monitor in auto_trader_core.py
- [ ] Add trade logging in close_trade()
- [ ] Add rejection logging in open_trade() for each Phase 4 filter
- [ ] Test with a few manual trades
- [ ] Verify phase5_test.db gets populated

---

## Approach 2: Log Parsing (Fallback)

If automatic integration isn't possible, Phase 5 can parse Scalp-Engine logs.

### How It Works

Phase 5 monitor reads logs and extracts:
- Trade executions (from logs like "✅ [TRADE-OPENED]")
- Trade closures (from logs like "✅ [TP-HIT]")
- Rejections (from logs like "⏭️ SKIPPING")

### Implementation

**File**: `phase5_log_parser.py` (create new)

```python
import re
from pathlib import Path
from datetime import datetime
from phase5_monitor import Phase5Monitor

class Phase5LogParser:
    """Parse Scalp-Engine logs for Phase 5 monitoring"""

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.monitor = Phase5Monitor()

    def parse_trades(self):
        """Extract trades from log file"""
        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            # Pattern: [TRADE-OPENED] EUR/USD LONG @ 1.0850 | SL=1.0800
            if '[TRADE-OPENED]' in line:
                self._parse_trade_opened(line)

            # Pattern: [TP-HIT] trade_12345: EUR/USD LONG | P&L: +50.0 pips
            elif '[TP-HIT]' in line:
                self._parse_tp_hit(line)

            # Pattern: [SL-HIT] trade_12345: EUR/USD LONG | P&L: -50.0 pips
            elif '[SL-HIT]' in line:
                self._parse_sl_hit(line)

            # Pattern: ⏭️ SKIPPING: Low consensus (40% < 50%)
            elif 'SKIPPING' in line or 'BLOCKED' in line:
                self._parse_rejection(line)

    def _parse_trade_opened(self, line: str):
        """Parse [TRADE-OPENED] log entry"""
        # Extract: EUR/USD LONG @ 1.0850 | SL=1.0800 | TP=1.0900
        match = re.search(r'(\w+/\w+)\s+(LONG|SHORT)\s+@\s+([0-9.]+).*SL=([0-9.]+).*TP=([0-9.]+)', line)
        if match:
            pair, direction, entry, sl, tp = match.groups()

            trade_data = {
                'timestamp': self._extract_timestamp(line),
                'pair': pair,
                'direction': direction,
                'entry_price': float(entry),
                'stop_loss': float(sl),
                'take_profit': float(tp),
                'outcome': 'PENDING',
                'source': 'LLM'  # or FISHER, DMI_EMA
            }

            self.monitor.log_trade(trade_data)

    def _parse_tp_hit(self, line: str):
        """Parse [TP-HIT] log entry"""
        # Extract PNL and pair info
        match = re.search(r'(\w+/\w+).*P&L:\s+([+-]?[0-9.]+)\s*pips', line)
        if match:
            pair, pnl = match.groups()

            # Update existing trade (mark as WON)
            # This requires tracking open trades separately
            self.monitor.log_trade({
                'timestamp': self._extract_timestamp(line),
                'pair': pair,
                'outcome': 'WIN_TP1',
                'pnl_pips': float(pnl),
            })

    def _parse_rejection(self, line: str):
        """Parse rejection/skip log entry"""
        # Extract filter type and reason
        rejection_data = {
            'timestamp': self._extract_timestamp(line),
            'filter_type': self._extract_filter_type(line),
            'reason': self._extract_reason(line),
        }

        self.monitor.log_rejection(rejection_data)

    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from log line"""
        match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        if match:
            return match.group(1).replace(' ', 'T')
        return datetime.utcnow().isoformat()

    def _extract_filter_type(self, line: str) -> str:
        """Extract filter type from rejection"""
        if 'confidence' in line.lower():
            return 'CONFIDENCE'
        elif 'llm' in line.lower():
            return 'LLM_ACCURACY'
        elif 'jpy' in line.lower():
            return 'JPY_DIRECTION'
        elif 'regime' in line.lower():
            return 'MARKET_REGIME'
        else:
            return 'OTHER'

    def _extract_reason(self, line: str) -> str:
        """Extract reason from log"""
        match = re.search(r'(SKIPPING|BLOCKED):\s+(.+?)(?:\s*$|,|;)', line)
        if match:
            return match.group(2)
        return 'Unknown'


# Usage
if __name__ == '__main__':
    parser = Phase5LogParser('Scalp-Engine/logs/scalp_engine.log')
    parser.parse_trades()
    print("✅ Trades parsed and logged")
```

### Usage

```bash
# Parse current log file
python phase5_log_parser.py

# Or run continuously (every 30 seconds)
watch -n 30 'python phase5_log_parser.py'
```

### Benefits

- ✅ Works without modifying Scalp-Engine code
- ✅ Backward compatible
- ⚠️ Slight delay (not real-time)
- ⚠️ Requires log file to be complete

---

## Approach 3: Hybrid (Recommended for Safety)

Use both automatic and log parsing for redundancy:

1. Scalp-Engine logs trades directly (fast)
2. Phase 5 log parser runs on schedule (validation)
3. Discrepancies are logged for investigation

**Implementation**:
```python
# In phase5_monitor.py add:
def validate_against_logs(self, log_file: str):
    """Validate database against log file"""
    parser = Phase5LogParser(log_file)
    parsed_trades = parser.get_all_trades()
    db_trades = self.get_all_trades()

    # Compare and log discrepancies
    if len(parsed_trades) != len(db_trades):
        print(f"⚠️  Log has {len(parsed_trades)} trades, DB has {len(db_trades)}")
        # Sync missing trades
```

---

## Log Format Requirements

Scalp-Engine must log trades in a consistent format for Phase 5 to parse:

### Trade Opened Log

```
✅ [TRADE-OPENED] 12345: EUR/USD LONG 1000u @ 1.0855 | SL=1.0800 | TP=1.0900
```

**Required Fields**:
- Trade ID: `12345`
- Pair: `EUR/USD`
- Direction: `LONG` or `SHORT`
- Units: `1000u`
- Entry: `@ 1.0855`
- Stop Loss: `SL=1.0800`
- Take Profit: `TP=1.0900`

### Trade Closed Log

```
✅ [TP-HIT] trade_12345: EUR/USD LONG TP hit at 1.0900 | P&L: +45.0 pips
❌ [SL-HIT] trade_12345: EUR/USD LONG SL hit at 1.0800 | P&L: -50.0 pips
```

**Required Fields**:
- Trade ID: `trade_12345`
- Outcome: `TP-HIT` or `SL-HIT`
- P&L: `+45.0 pips` or `-50.0 pips`

### Rejection Log

```
⏭️ SKIPPING: Low consensus (40% < 50%)
❌ [BLOCKED] EUR/USD: GBP/JPY SHORT has 0% win rate - BLOCK
```

**Required Fields**:
- Action: `SKIPPING` or `BLOCKED`
- Reason: Clear description

---

## Integration Checklist

### Phase 1: Verify Logging

- [ ] Scalp-Engine logs trades in expected format
- [ ] Check log file: `Scalp-Engine/logs/scalp_engine.log`
- [ ] Verify Phase 4 rejections are logged
- [ ] Confirm logs contain all required fields

### Phase 2: Choose Integration Method

- [ ] Option A: Auto logging (modify auto_trader_core.py)
- [ ] Option B: Log parsing (create phase5_log_parser.py)
- [ ] Option C: Hybrid (both for safety)

### Phase 3: Implement & Test

- [ ] Create Phase5Monitor class ✅ (already done)
- [ ] Integrate with Scalp-Engine
- [ ] Test with manual trades
- [ ] Verify phase5_test.db gets populated

### Phase 4: Validate Data

```bash
# Check database has data
python phase5_monitor.py --report 2026-02-23

# Compare against logs
python phase5_log_parser.py
# Check for discrepancies
```

---

## Troubleshooting Integration

### Issue: No trades in Phase 5 database

**Check**:
1. Are trades executing? (Check Scalp-Engine logs)
2. Is Phase5Monitor being called? (Add debug logging)
3. Is database path correct?

**Fix**:
```bash
# Verify database exists and is writable
ls -la data/phase5_test.db
python -c "import phase5_monitor; m = phase5_monitor.Phase5Monitor(); print(m.db_path)"

# Try manual insertion
python << 'EOF'
from phase5_monitor import Phase5Monitor
m = Phase5Monitor()
m.log_trade({
    'timestamp': '2026-02-23T10:00:00',
    'pair': 'EUR/USD',
    'direction': 'LONG',
    'entry_price': 1.0850,
    'stop_loss': 1.0800,
    'take_profit': 1.0900,
    'outcome': 'WIN_TP1',
    'pnl_pips': 50.0
})
print("✅ Test trade inserted")
EOF
```

### Issue: Log parsing not extracting trades

**Check**:
1. Log file has correct format
2. Regex patterns match log entries
3. Timestamps are correct

**Fix**:
```bash
# Check log format
tail -20 Scalp-Engine/logs/scalp_engine.log

# Test regex extraction
python << 'EOF'
import re
line = "✅ [TRADE-OPENED] 12345: EUR/USD LONG 1000u @ 1.0855 | SL=1.0800 | TP=1.0900"
match = re.search(r'(\w+/\w+)\s+(LONG|SHORT)', line)
print(match.groups() if match else "No match")
EOF
```

---

## Data Sync Strategy

If running Trade-Alerts on Render and Scalp-Engine locally:

**Option 1: Push to Cloud DB**
- Phase 5 writes to cloud database
- Render can read for analysis
- Real-time sync

**Option 2: Pull from Logs**
- Download Render logs hourly
- Parse locally
- Populate Phase 5 DB

**Implementation**:
```bash
# Hourly sync from Render
0 * * * * python sync_phase5_from_render.py
```

---

## Summary

**Phase 5 monitoring integration options**:

1. **Auto logging** (Recommended)
   - Modify auto_trader_core.py
   - Direct database writes
   - Real-time updates
   - Cleanest approach

2. **Log parsing** (Fallback)
   - No code modification
   - Parses existing logs
   - Slight delay
   - Good for validation

3. **Hybrid** (Best for Safety)
   - Both methods running
   - Redundancy built in
   - Catches errors

**Next**: Choose integration method and implement in Scalp-Engine

