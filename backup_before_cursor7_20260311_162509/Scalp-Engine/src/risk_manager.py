"""
Risk management for scalping trades
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

class RiskManager:
    """Manages risk parameters and position sizing"""
    
    def __init__(
        self,
        risk_per_trade_pct: float = 0.5,
        daily_max_loss_pct: float = 2.0,
        stop_loss_pips: float = 5.0,
        take_profit_pips: float = 8.0,
        max_consecutive_losses: int = 3
    ):
        """
        Initialize risk manager
        
        Args:
            risk_per_trade_pct: Percentage of account to risk per trade
            daily_max_loss_pct: Maximum daily loss percentage
            stop_loss_pips: Stop loss in pips
            take_profit_pips: Take profit in pips
            max_consecutive_losses: Stop trading after N consecutive losses
        """
        self.risk_per_trade_pct = risk_per_trade_pct
        self.daily_max_loss_pct = daily_max_loss_pct
        self.stop_loss_pips = stop_loss_pips
        self.take_profit_pips = take_profit_pips
        self.max_consecutive_losses = max_consecutive_losses
        
        # Track daily performance
        self.daily_pnl = 0.0
        self.daily_start_balance = None
        self.consecutive_losses = 0
        self.last_reset_date = datetime.now().date()
        
    def reset_daily_stats(self):
        """Reset daily statistics"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_start_balance = None
            self.consecutive_losses = 0
            self.last_reset_date = today
    
    def calculate_position_size(
        self,
        account_balance: float,
        stop_loss_pips: float = None,
        pip_value: float = 10.0
    ) -> int:
        """
        Calculate position size based on risk
        
        Args:
            account_balance: Current account balance
            stop_loss_pips: Stop loss in pips (uses default if None)
            pip_value: Value of 1 pip in account currency (default: $10 for standard lot)
            
        Returns:
            Position size in units
        """
        self.reset_daily_stats()
        
        if stop_loss_pips is None:
            stop_loss_pips = self.stop_loss_pips
        
        # Calculate risk amount
        risk_amount = account_balance * (self.risk_per_trade_pct / 100.0)
        
        # Calculate position size
        # Risk = Position Size * Stop Loss Pips * Pip Value
        # Position Size = Risk / (Stop Loss Pips * Pip Value)
        position_size = int(risk_amount / (stop_loss_pips * pip_value))
        
        # For micro lots, ensure minimum size
        if position_size < 1:
            position_size = 1
        
        return position_size
    
    def can_trade(self, account_balance: float, current_pnl: float = None):
        """
        Check if trading is allowed based on risk limits
        
        Args:
            account_balance: Current account balance
            current_pnl: Current P&L for the day (if None, uses tracked P&L)
            
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        self.reset_daily_stats()
        
        if current_pnl is not None:
            self.daily_pnl = current_pnl
        
        # Check daily loss limit
        if self.daily_start_balance is None:
            self.daily_start_balance = account_balance
        
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_balance * 100.0
        if daily_loss_pct >= self.daily_max_loss_pct:
            return False, f"Daily loss limit reached ({daily_loss_pct:.2f}%)"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses reached ({self.consecutive_losses})"
        
        return True, "OK"
    
    def record_trade_outcome(self, pnl: float):
        """
        Record trade outcome for risk tracking
        
        Args:
            pnl: Profit/loss from the trade
        """
        self.daily_pnl += pnl
        
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
    
    def get_risk_parameters(self) -> Dict:
        """Get current risk parameters"""
        return {
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'daily_max_loss_pct': self.daily_max_loss_pct,
            'stop_loss_pips': self.stop_loss_pips,
            'take_profit_pips': self.take_profit_pips,
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses
        }

