# Position Sizing Implementation Guide
## Code Integration for Trade-Alerts Scalp-Engine

**Purpose**: Add dynamic position sizing to Scalp-Engine based on account balance, risk tolerance, and volatility

**Status**: Ready for Phase 1 implementation

---

## PHASE 1: FIXED FRACTIONAL RISK (WEEKS 1-4)

### Step 1: Create `Scalp-Engine/src/risk_manager.py`

```python
"""
Position Sizing and Risk Management Module

Implements professional-grade position sizing using fixed fractional risk method.
Formula: Position Size = (Account Equity × Risk %) / (Stop Loss Distance × Pip Value)
"""

import os
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""
    units: int
    risk_amount: float
    potential_profit: float
    potential_loss: float
    risk_reward_ratio: float
    is_valid: bool
    validation_message: str = ""


class RiskManager:
    """
    Manages position sizing and risk limits based on account balance and risk tolerance.

    Uses fixed fractional risk method:
    Position Size = (Account Balance × Risk %) / (Stop Loss Distance × Pip Value)
    """

    # Pip values by pair type
    PIP_VALUES = {
        'JPY': 0.01,          # JPY pairs use 0.01
        'DEFAULT': 0.0001,     # Most other pairs use 0.0001
    }

    # Risk percentage by phase
    PHASE_RISK_PERCENTS = {
        'phase_1': 0.5,  # 0.5% - Recovery phase (weeks 1-4)
        'phase_2': 1.0,  # 1.0% - Proof phase (weeks 5-8)
        'phase_3': 2.0,  # 2.0% - Growth phase (weeks 9+)
    }

    def __init__(self, account_balance: float = 100.0, phase: str = 'phase_1'):
        """
        Initialize risk manager with account balance and trading phase.

        Args:
            account_balance: Current account balance in base currency (default $100)
            phase: Trading phase ('phase_1', 'phase_2', or 'phase_3')
        """
        self.account_balance = account_balance
        self.phase = phase
        self.risk_percent = self.PHASE_RISK_PERCENTS.get(phase, 0.5)
        self.risk_amount = account_balance * (self.risk_percent / 100)

        logger.info(
            f"RiskManager initialized: account=${account_balance:.2f}, "
            f"phase={phase}, risk_percent={self.risk_percent}%, "
            f"risk_amount=${self.risk_amount:.2f}"
        )

    def update_phase(self, new_phase: str):
        """Update trading phase and recalculate risk amount."""
        if new_phase not in self.PHASE_RISK_PERCENTS:
            logger.warning(f"Invalid phase: {new_phase}. Keeping {self.phase}")
            return

        self.phase = new_phase
        self.risk_percent = self.PHASE_RISK_PERCENTS[new_phase]
        self.risk_amount = self.account_balance * (self.risk_percent / 100)
        logger.info(f"Phase updated to {new_phase}, risk_amount=${self.risk_amount:.2f}")

    def update_account_balance(self, new_balance: float):
        """Update account balance and recalculate risk amount."""
        old_balance = self.account_balance
        self.account_balance = new_balance
        self.risk_amount = new_balance * (self.risk_percent / 100)
        logger.info(
            f"Account balance updated: ${old_balance:.2f} → ${new_balance:.2f}, "
            f"risk_amount=${self.risk_amount:.2f}"
        )

    def get_pip_value(self, pair: str) -> float:
        """
        Get pip value for a currency pair.

        Args:
            pair: Currency pair (e.g., 'EUR/USD', 'EUR/JPY')

        Returns:
            Pip value (0.01 for JPY, 0.0001 for others)
        """
        # Normalize pair format
        pair_upper = pair.upper().replace('_', '/').replace('-', '/')

        # Check if JPY is in the pair
        if 'JPY' in pair_upper:
            return self.PIP_VALUES['JPY']
        else:
            return self.PIP_VALUES['DEFAULT']

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        pair: str,
        take_profit_price: Optional[float] = None
    ) -> PositionSizingResult:
        """
        Calculate position size using fixed fractional risk method.

        Formula: Position Size = (Account Equity × Risk %) / (Stop Loss Distance × Pip Value)

        Args:
            entry_price: Trade entry price
            stop_loss_price: Stop loss price
            pair: Currency pair (e.g., 'EUR/USD')
            take_profit_price: Optional take profit price for validation

        Returns:
            PositionSizingResult with units, risk, profit, and validation
        """
        result = PositionSizingResult(
            units=0,
            risk_amount=0,
            potential_profit=0,
            potential_loss=0,
            risk_reward_ratio=0,
            is_valid=False
        )

        # Validate inputs
        if entry_price <= 0 or stop_loss_price <= 0:
            result.validation_message = "Entry and stop loss prices must be positive"
            return result

        if entry_price == stop_loss_price:
            result.validation_message = "Entry price equals stop loss (no risk)"
            return result

        # Get pip value for pair
        pip_value = self.get_pip_value(pair)

        # Calculate stop loss distance in pips
        sl_distance = abs(entry_price - stop_loss_price) / pip_value

        # Validate stop loss distance
        if sl_distance < 1:
            result.validation_message = f"Stop loss distance ({sl_distance:.1f} pips) too small"
            return result

        if sl_distance > 500:  # Max SL distance warning
            result.validation_message = (
                f"Stop loss distance ({sl_distance:.1f} pips) very large. "
                "Consider tighter SL for better risk management."
            )
            # Don't return early - allow but warn

        # Calculate position size
        try:
            position_units = int(self.risk_amount / (sl_distance * pip_value))
        except ZeroDivisionError:
            result.validation_message = "Division by zero in position calculation"
            return result

        if position_units <= 0:
            result.validation_message = (
                f"Calculated position size ({position_units}) is too small. "
                "Cannot trade with account size and stop loss distance."
            )
            return result

        # Calculate potential profit and loss
        potential_loss = sl_distance * pip_value * position_units

        # Calculate RRR if take profit provided
        if take_profit_price and take_profit_price > 0:
            tp_distance = abs(take_profit_price - entry_price) / pip_value
            potential_profit = tp_distance * pip_value * position_units

            if potential_profit > 0:
                risk_reward_ratio = potential_profit / potential_loss
            else:
                risk_reward_ratio = 0
                result.validation_message = "Take profit price equals or worse than entry"
        else:
            # Assume 2:1 ratio (standard)
            tp_distance = sl_distance * 2
            potential_profit = tp_distance * pip_value * position_units
            risk_reward_ratio = 2.0

        # Build successful result
        result.units = position_units
        result.risk_amount = self.risk_amount
        result.potential_loss = round(potential_loss, 2)
        result.potential_profit = round(potential_profit, 2)
        result.risk_reward_ratio = round(risk_reward_ratio, 2)
        result.is_valid = True
        result.validation_message = (
            f"✅ Position size valid: {position_units} units, "
            f"risk=${result.risk_amount:.2f}, profit=${result.potential_profit:.2f}, "
            f"R:R={result.risk_reward_ratio:.2f}:1"
        )

        return result

    def validate_position_size(
        self,
        position_units: int,
        entry_price: float,
        stop_loss_price: float,
        pair: str
    ) -> Tuple[bool, str]:
        """
        Validate if a proposed position size is within risk limits.

        Returns:
            Tuple of (is_valid, reason_message)
        """
        pip_value = self.get_pip_value(pair)
        sl_distance = abs(entry_price - stop_loss_price) / pip_value
        potential_loss = sl_distance * pip_value * position_units

        # Check if loss exceeds risk amount
        if potential_loss > self.risk_amount * 1.05:  # Allow 5% buffer for rounding
            return False, (
                f"Position loss (${potential_loss:.2f}) exceeds risk limit "
                f"(${self.risk_amount:.2f})"
            )

        # Check if position is too large (margin concern)
        if position_units > 100000:  # 1 standard lot
            return True, "⚠️ Large position (>1 standard lot) - verify margin available"

        return True, "✅ Position size valid"


class DailyRiskMonitor:
    """Tracks and enforces daily loss limits and circuit breakers."""

    def __init__(
        self,
        daily_loss_limit_percent: float = 2.0,
        max_consecutive_losses: int = 5
    ):
        """
        Initialize daily risk monitor.

        Args:
            daily_loss_limit_percent: Stop trading after this % daily loss
            max_consecutive_losses: Stop after this many losses in a row
        """
        self.daily_loss_limit_percent = daily_loss_limit_percent
        self.max_consecutive_losses = max_consecutive_losses

        self.reset_daily()

    def reset_daily(self):
        """Reset daily counters (call at end of each trading day)."""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trades_today = 0
        self.wins_today = 0
        self.losses_today = 0

    def record_trade(self, pnl: float, account_balance: float) -> Tuple[bool, str]:
        """
        Record a trade result and check if we should stop trading.

        Args:
            pnl: Profit/loss of the trade
            account_balance: Current account balance

        Returns:
            Tuple of (should_continue_trading, reason_message)
        """
        self.daily_pnl += pnl
        self.trades_today += 1

        if pnl > 0:
            self.consecutive_losses = 0
            self.wins_today += 1
        else:
            self.consecutive_losses += 1
            self.losses_today += 1

        # Check daily loss limit
        daily_limit = account_balance * (self.daily_loss_limit_percent / 100)
        daily_loss_percent = (abs(self.daily_pnl) / account_balance) * 100 if self.daily_pnl < 0 else 0

        if abs(self.daily_pnl) >= daily_limit:
            return False, (
                f"🛑 DAILY LOSS LIMIT HIT: "
                f"Lost ${abs(self.daily_pnl):.2f} ({daily_loss_percent:.1f}%) today. "
                f"Stop trading for the day."
            )

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, (
                f"🛑 CIRCUIT BREAKER: "
                f"{self.consecutive_losses} consecutive losses. "
                f"Stop trading and review system."
            )

        return True, f"✅ Trade recorded: +{pnl:.2f} if win, -{abs(pnl):.2f} if loss"

    def get_daily_summary(self) -> Dict:
        """Get summary of today's trading."""
        win_rate = (self.wins_today / self.trades_today * 100) if self.trades_today > 0 else 0
        return {
            'daily_pnl': round(self.daily_pnl, 2),
            'trades_today': self.trades_today,
            'wins': self.wins_today,
            'losses': self.losses_today,
            'win_rate_percent': round(win_rate, 1),
            'consecutive_losses': self.consecutive_losses,
        }


# Singleton instance for use throughout Scalp-Engine
_risk_manager: Optional[RiskManager] = None
_daily_monitor: Optional[DailyRiskMonitor] = None


def get_risk_manager(
    account_balance: Optional[float] = None,
    phase: Optional[str] = None
) -> RiskManager:
    """Get or create global risk manager instance."""
    global _risk_manager

    if _risk_manager is None:
        balance = account_balance or float(os.getenv('ACCOUNT_BALANCE_CAD', 100))
        phase = phase or os.getenv('TRADING_PHASE', 'phase_1')
        _risk_manager = RiskManager(account_balance=balance, phase=phase)

    if account_balance:
        _risk_manager.update_account_balance(account_balance)
    if phase:
        _risk_manager.update_phase(phase)

    return _risk_manager


def get_daily_monitor() -> DailyRiskMonitor:
    """Get or create global daily risk monitor instance."""
    global _daily_monitor

    if _daily_monitor is None:
        daily_limit = float(os.getenv('DAILY_LOSS_LIMIT_PERCENT', 2.0))
        max_losses = int(os.getenv('MAX_CONSECUTIVE_LOSSES', 5))
        _daily_monitor = DailyRiskMonitor(
            daily_loss_limit_percent=daily_limit,
            max_consecutive_losses=max_losses
        )

    return _daily_monitor
```

### Step 2: Update `Scalp-Engine/.env`

Add these environment variables:

```bash
# ===== POSITION SIZING & RISK MANAGEMENT =====
# Risk Management Configuration
ACCOUNT_BALANCE_CAD=100                    # Current account balance (update weekly)
TRADING_PHASE=phase_1                      # phase_1 (0.5%), phase_2 (1%), phase_3 (2%)
RISK_PERCENT_PER_TRADE=0.5                # Phase 1: 0.5%, Phase 2: 1%, Phase 3: 2%

# Daily Risk Limits
DAILY_LOSS_LIMIT_PERCENT=2.0              # Stop trading after 2% daily loss
MAX_CONSECUTIVE_LOSSES=5                  # Circuit breaker: stop after 5 losses

# Position Sizing Behavior
MIN_POSITION_UNITS=1                      # Minimum position size (10 = 0.10 micro lots)
MAX_POSITION_UNITS=100000                 # Maximum position size (1 standard lot)
MAX_STOP_LOSS_PIPS=500                    # Warn if SL > 500 pips
MIN_RISK_REWARD_RATIO=1.5                 # Minimum 1:1.5 R:R ratio (Phase 2 allows 1:1)
```

### Step 3: Integrate into `Scalp-Engine/auto_trader_core.py`

At the top of the file:

```python
from src.risk_manager import (
    get_risk_manager,
    get_daily_monitor,
    PositionSizingResult
)
```

In `PositionManager.open_trade()` method, before placing the order:

```python
def open_trade(self, opp: Dict) -> Optional[Tuple[Dict, Optional[str]]]:
    """Open a new trade with risk-managed position sizing."""

    # ... existing validation code ...

    # NEW: Calculate position size using risk manager
    risk_manager = get_risk_manager()

    positioning_result = risk_manager.calculate_position_size(
        entry_price=opp['entry'],
        stop_loss_price=opp['stop_loss'],
        pair=opp['pair'],
        take_profit_price=opp.get('exit')
    )

    if not positioning_result.is_valid:
        self.logger.warning(
            f"Position sizing validation failed for {opp['pair']}: "
            f"{positioning_result.validation_message}"
        )
        self._last_reject_reason = "position_sizing_invalid"
        return None, "position_sizing_invalid"

    self.logger.info(
        f"✅ Position sizing: {positioning_result.units} units, "
        f"risk=${positioning_result.risk_amount:.2f}, "
        f"profit=${positioning_result.potential_profit:.2f}, "
        f"R:R={positioning_result.risk_reward_ratio:.2f}:1"
    )

    # Use calculated position size for the trade
    trade = self.position_manager.create_trade(
        pair=opp['pair'],
        direction=opp['direction'],
        entry=opp['entry'],
        stop_loss=opp['stop_loss'],
        take_profit=opp.get('exit'),
        units=positioning_result.units,  # <-- Use calculated units
        reason=opp.get('recommendation', '')[:200]
    )

    # ... rest of existing code ...
```

### Step 4: Add Trade Logging

After trade closes, log the result:

```python
def close_trade(self, trade: Dict, closing_price: float) -> Dict:
    """Close trade and record result with risk monitoring."""

    # ... existing closing code ...

    # NEW: Record trade result with daily monitor
    daily_monitor = get_daily_monitor()
    pnl = trade.get('pnl', 0)
    account_balance = float(os.getenv('ACCOUNT_BALANCE_CAD', 100))

    should_continue, monitor_message = daily_monitor.record_trade(
        pnl=pnl,
        account_balance=account_balance
    )

    if not should_continue:
        self.logger.error(monitor_message)
        return {'status': 'stopped_by_circuit_breaker', 'message': monitor_message}

    self.logger.info(monitor_message)
    return trade_result
```

### Step 5: Add to Scalp-Engine UI (`scalp_ui.py`)

Display position sizing info in sidebar:

```python
import streamlit as st
from src.risk_manager import get_risk_manager, get_daily_monitor

# ... in main() function ...

with st.sidebar:
    st.subheader("📊 Risk Management")

    risk_manager = get_risk_manager()
    daily_monitor = get_daily_monitor()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Account Balance", f"${risk_manager.account_balance:.2f}")
        st.metric("Phase", risk_manager.phase.upper())
    with col2:
        st.metric("Risk per Trade", f"{risk_manager.risk_percent:.1f}%")
        st.metric("Risk Amount", f"${risk_manager.risk_amount:.2f}")

    # Daily summary
    daily_summary = daily_monitor.get_daily_summary()
    st.metric("Daily P&L", f"${daily_summary['daily_pnl']:.2f}")
    st.metric("Trades Today", f"{daily_summary['trades_today']}")
    st.metric("Win Rate (today)", f"{daily_summary['win_rate_percent']:.1f}%")

    if daily_summary['consecutive_losses'] > 2:
        st.warning(f"⚠️ {daily_summary['consecutive_losses']} consecutive losses")
```

---

## PHASE 2: ATR-BASED SIZING (WEEKS 5-8)

### Create `Scalp-Engine/src/atr_position_sizer.py`

This file implements volatility-adjusted position sizing (advanced):

```python
"""
ATR-Based Position Sizing for volatility-adjusted risk management.

Formula: Position Size = Account Risk / (ATR × ATR_Multiple × Conversion_Factor)
"""

import os
from typing import Optional, Dict
from src.risk_manager import RiskManager
from src.indicators.atr_calculator import calculate_atr


class ATRPositionSizer(RiskManager):
    """
    Extends RiskManager with ATR-based volatility adjustment.

    Keeps dollar risk constant despite volatility changes.
    Higher volatility = Smaller position size
    Lower volatility = Larger position size
    """

    def __init__(self, account_balance: float = 100.0, phase: str = 'phase_2'):
        super().__init__(account_balance, phase)
        self.atr_period = int(os.getenv('ATR_PERIOD', 14))
        self.atr_multiple = float(os.getenv('ATR_MULTIPLE', 1.5))

    def calculate_atr_position_size(
        self,
        pair: str,
        recent_prices: list,
        take_profit_price: Optional[float] = None
    ) -> Dict:
        """
        Calculate position size using ATR-based volatility adjustment.

        Args:
            pair: Currency pair
            recent_prices: List of recent OHLC prices for ATR calculation
            take_profit_price: Optional TP for validation

        Returns:
            Dict with position details and volatility info
        """
        # Calculate ATR
        atr = calculate_atr(recent_prices, period=self.atr_period)

        if atr <= 0:
            return {
                'error': 'ATR calculation failed',
                'units': 0,
                'is_valid': False
            }

        # Calculate stop loss distance based on ATR
        sl_distance = atr * self.atr_multiple

        # Get pip value
        pip_value = self.get_pip_value(pair)

        # Calculate position size: Risk / (ATR × Multiple × Pip Value)
        position_units = int(self.risk_amount / (atr * self.atr_multiple * pip_value))

        if position_units <= 0:
            return {
                'error': 'Position size calculation resulted in 0 units',
                'units': 0,
                'is_valid': False
            }

        return {
            'units': position_units,
            'atr': round(atr, 6),
            'sl_distance': round(sl_distance, 6),
            'risk_amount': self.risk_amount,
            'is_valid': True,
            'volatility_note': f"ATR={atr:.6f} → {position_units} units "
                               f"(volatility-adjusted)"
        }
```

---

## TESTING POSITION SIZING

### Create `Scalp-Engine/test_position_sizing.py`

```python
"""
Test position sizing calculations.

Run: python Scalp-Engine/test_position_sizing.py
"""

from src.risk_manager import RiskManager, DailyRiskMonitor


def test_position_sizing():
    """Test position size calculations for various scenarios."""

    print("\n" + "="*60)
    print("POSITION SIZING TEST SUITE")
    print("="*60)

    # Test 1: Phase 1 EUR/USD (0.5% risk)
    print("\n📊 Test 1: Phase 1 EUR/USD Trade")
    print("-" * 40)
    rm = RiskManager(account_balance=100, phase='phase_1')
    result = rm.calculate_position_size(
        entry_price=1.0850,
        stop_loss_price=1.0840,  # 10 pips
        pair='EUR/USD',
        take_profit_price=1.0870  # 20 pips
    )
    print(f"Entry: 1.0850, SL: 1.0840 (10 pips), TP: 1.0870 (20 pips)")
    print(f"Position: {result.units} units")
    print(f"Risk: ${result.risk_amount:.2f}")
    print(f"Profit: ${result.potential_profit:.2f}")
    print(f"R:R Ratio: 1:{result.risk_reward_ratio:.2f}")
    assert result.is_valid, "Test 1 failed"
    assert result.units == 500, f"Expected 500 units, got {result.units}"
    print("✅ PASSED")

    # Test 2: Phase 2 GBP/USD (1% risk)
    print("\n📊 Test 2: Phase 2 GBP/USD Trade")
    print("-" * 40)
    rm = RiskManager(account_balance=125, phase='phase_2')
    result = rm.calculate_position_size(
        entry_price=1.2750,
        stop_loss_price=1.2730,  # 20 pips
        pair='GBP/USD',
        take_profit_price=1.2790  # 40 pips
    )
    print(f"Entry: 1.2750, SL: 1.2730 (20 pips), TP: 1.2790 (40 pips)")
    print(f"Position: {result.units} units")
    print(f"Risk: ${result.risk_amount:.2f}")
    print(f"Profit: ${result.potential_profit:.2f}")
    print(f"R:R Ratio: 1:{result.risk_reward_ratio:.2f}")
    assert result.is_valid, "Test 2 failed"
    assert result.units == 625, f"Expected 625 units, got {result.units}"
    print("✅ PASSED")

    # Test 3: JPY pair (different pip value)
    print("\n📊 Test 3: USD/JPY Trade (JPY pip value)")
    print("-" * 40)
    rm = RiskManager(account_balance=100, phase='phase_1')
    result = rm.calculate_position_size(
        entry_price=150.50,
        stop_loss_price=150.00,  # 50 pips (but 0.50 in price)
        pair='USD/JPY',
        take_profit_price=151.50  # 100 pips
    )
    print(f"Entry: 150.50, SL: 150.00 (50 pips), TP: 151.50 (100 pips)")
    print(f"Pip value: {rm.get_pip_value('USD/JPY')}")
    print(f"Position: {result.units} units")
    print(f"Risk: ${result.risk_amount:.2f}")
    print(f"Profit: ${result.potential_profit:.2f}")
    print(f"R:R Ratio: 1:{result.risk_reward_ratio:.2f}")
    assert result.is_valid, "Test 3 failed"
    print("✅ PASSED")

    # Test 4: Daily monitor - win/loss tracking
    print("\n📊 Test 4: Daily Risk Monitor")
    print("-" * 40)
    monitor = DailyRiskMonitor(daily_loss_limit_percent=2.0, max_consecutive_losses=5)
    account = 100

    # Simulate trades
    trades = [
        (1.50, "Win"),
        (-0.50, "Loss"),
        (-0.50, "Loss"),
        (1.00, "Win"),
        (-0.50, "Loss"),
    ]

    for pnl, label in trades:
        should_continue, msg = monitor.record_trade(pnl, account)
        print(f"  Trade: {label:6} {pnl:+.2f} → {msg}")
        assert should_continue, f"Should continue after {label}"

    summary = monitor.get_daily_summary()
    print(f"\nDaily Summary:")
    print(f"  P&L: ${summary['daily_pnl']:.2f}")
    print(f"  Trades: {summary['trades_today']}")
    print(f"  Win Rate: {summary['win_rate_percent']:.1f}%")
    print(f"  Consecutive Losses: {summary['consecutive_losses']}")
    assert summary['trades_today'] == 5, "Should have 5 trades"
    assert summary['wins'] == 2, "Should have 2 wins"
    assert summary['losses'] == 3, "Should have 3 losses"
    print("✅ PASSED")

    # Test 5: Circuit breaker - 5 consecutive losses
    print("\n📊 Test 5: Circuit Breaker (5 consecutive losses)")
    print("-" * 40)
    monitor = DailyRiskMonitor(daily_loss_limit_percent=2.0, max_consecutive_losses=5)
    account = 100

    for i in range(5):
        should_continue, msg = monitor.record_trade(-0.40, account)
        print(f"  Loss {i+1}: {msg}")
        if i < 4:
            assert should_continue, f"Should continue after loss {i+1}"
        else:
            assert not should_continue, "Should trigger circuit breaker on 5th loss"
            print("  ✅ Circuit breaker triggered!")

    print("✅ PASSED")

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60 + "\n")


if __name__ == '__main__':
    test_position_sizing()
```

Run tests:

```bash
cd Scalp-Engine
python test_position_sizing.py
```

---

## IMPLEMENTATION TIMELINE

### Week 1-4 (Phase 1): Recovery

- [ ] Create `src/risk_manager.py` (RiskManager, DailyRiskMonitor classes)
- [ ] Add env variables to `.env`
- [ ] Integrate position sizing into `auto_trader_core.py`
- [ ] Add daily risk monitoring
- [ ] Test with test suite
- [ ] Deploy to demo account
- [ ] Monitor for 50+ trades at 0.5% risk
- [ ] Verify win rate reaches 40%

### Week 5-8 (Phase 2): Proof

- [ ] Update `.env`: Change to `TRADING_PHASE=phase_2`
- [ ] Increase `RISK_PERCENT_PER_TRADE=1.0`
- [ ] Create `src/atr_position_sizer.py` (optional)
- [ ] Test on demo for 50+ trades at 1% risk
- [ ] Verify 40% win rate maintained
- [ ] Calculate profit factor (should be >1.5)

### Week 9+ (Phase 3): Growth

- [ ] Update `.env`: Change to `TRADING_PHASE=phase_3`
- [ ] Increase `RISK_PERCENT_PER_TRADE=2.0`
- [ ] Enable ATR-based position sizing
- [ ] Monitor 200+ trades for profitability
- [ ] Plan quarterly scale-up

---

## VERIFICATION CHECKLIST

Before deploying position sizing:

- [ ] Position size formula works: `Position = (Account × Risk%) / (SL_pips × pip_value)`
- [ ] All currency pairs: tested EUR/USD, GBP/USD, USD/JPY
- [ ] Risk amounts match: 0.5% phase 1, 1% phase 2, 2% phase 3
- [ ] Daily loss limit enforced: stops after 2% loss
- [ ] Circuit breaker works: stops after 5 consecutive losses
- [ ] Logging works: each trade shows position size, risk, profit
- [ ] UI displays: shows account balance, phase, risk %, daily P&L
- [ ] Tests pass: run `python test_position_sizing.py`

---

## TROUBLESHOOTING

### "Position size came out as 0 units"

**Cause**: Stop loss distance is too large relative to account size.

**Fix**:
- Reduce stop loss distance
- Increase account balance
- Move to Phase 2 (higher risk %) for higher unit counts

### "Daily loss limit triggered too early"

**Cause**: Account balance is outdated or risk % is wrong.

**Fix**:
- Update `ACCOUNT_BALANCE_CAD` to current balance
- Check `RISK_PERCENT_PER_TRADE` matches phase
- Verify calculation: Account × Risk% ÷ 100 = Daily limit

### "R:R ratio is too low"

**Cause**: Take profit is too close to entry.

**Fix**:
- Set TP at 2× stop loss distance (1:2 ratio minimum)
- For Phase 2+, 1.5× is acceptable
- Formula: TP = Entry + (Entry - SL) × 2

---

## REFERENCES

This implementation is based on professional position sizing practices from:
- Professional forex broker guides (Myfxbook, Babypips, ACY)
- Risk management best practices (1-2% rule standard)
- Volatility-adjusted sizing (ATR-based approaches)
- Kelly Criterion for aggressive traders (Phase 3 optional)

---

**Status**: Ready for implementation
**Difficulty**: Moderate (1-2 days for Phase 1)
**Impact**: High (prevents account blowup, enables scaling)

Last updated: March 6, 2026
