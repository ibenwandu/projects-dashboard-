"""
Trading Hours Manager
Manages trading hours, entry restrictions, and runner exceptions
"""

from datetime import datetime, time
from typing import Literal, Tuple
import pytz

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class TradingHoursManager:
    """
    Trading hours manager with runner exception and entry restrictions
    
    Rules:
    - Trading hours: Monday 01:00 UTC - Friday 21:30 UTC (weekdays only)
    - No new trades: Friday 21:00 UTC - Monday 01:00 UTC (weekend shutdown)
    - Runners (25+ pips): Can hold until 23:00 UTC OR MACD crossover (Mon-Thu only)
    - Friday: ALL trades close at 21:30 UTC (no weekend exposure, no runners)
    - Weekend: NO TRADING - all trades closed immediately (Saturday/Sunday)
    """
    
    def __init__(self):
        self.DAILY_OPEN = time(1, 0)           # 01:00 UTC (Monday start)
        self.NO_ENTRY_START = time(21, 0)     # 21:00 UTC Friday (no-entry zone start - weekend shutdown)
        self.DAILY_CLOSE = time(21, 30)       # 21:30 UTC (Friday end)
        self.RUNNER_HARD_CLOSE = time(23, 0)  # 23:00 UTC (Mon-Thu only)
        self.RUNNER_THRESHOLD_PIPS = 25
        
        # Weekday constants (Monday=0, Friday=4, Saturday=5, Sunday=6)
        self.MONDAY = 0
        self.FRIDAY = 4
        self.SATURDAY = 5
        self.SUNDAY = 6
    
    def should_close_trade(
        self,
        now_utc: datetime,
        profit_pips: float,
        trade_direction: Literal["LONG", "SHORT"],
        df_m5=None,
        current_spread_pips: float = 0
    ) -> Tuple[bool, str]:
        """
        Determines if a trade should be closed based on time and profit rules
        
        Args:
            now_utc: Current UTC datetime
            profit_pips: Current profit in pips
            trade_direction: "LONG" or "SHORT"
            df_m5: DataFrame with 'close' column (M5 timeframe) for EMA crossover check
            current_spread_pips: Current spread in pips (for spread protection)
        
        Returns:
            Tuple[bool, str]: (should_close, reason)
        """
        # Ensure timezone-aware
        if now_utc.tzinfo is None:
            now_utc = pytz.utc.localize(now_utc)
        else:
            now_utc = now_utc.astimezone(pytz.utc)
        
        weekday = now_utc.weekday()
        curr_time = now_utc.time()
        
        # ============================================================
        # PRIORITY 1: Weekend Protection (NO TRADING OVER WEEKEND)
        # ============================================================
        
        # Saturday: Market closed, force close everything
        if weekday == self.SATURDAY:
            return True, "SATURDAY_MARKET_CLOSED"
        
        # Sunday: Always closed (NO TRADING OVER WEEKEND)
        if weekday == self.SUNDAY:
            return True, "SUNDAY_CLOSED"
        
        # Friday after 21:30: HARD CLOSE (no exceptions, no runners)
        if weekday == self.FRIDAY and curr_time >= self.DAILY_CLOSE:
            return True, "FRIDAY_HARD_CLOSE"
        
        # ============================================================
        # PRIORITY 2: Hard Deadline (Mon-Thu only)
        # ============================================================
        
        # After 23:00 UTC (Mon-Thu): Force close all remaining trades
        if weekday != self.FRIDAY and curr_time >= self.RUNNER_HARD_CLOSE:
            return True, "RUNNER_DEADLINE_23:00"
        
        # ============================================================
        # PRIORITY 3: Daily Close Window (21:30 - 23:00 Mon-Thu)
        # ============================================================
        
        if curr_time >= self.DAILY_CLOSE:
            # Friday: NO RUNNERS - all trades close at 21:30 UTC
            if weekday == self.FRIDAY:
                return True, "FRIDAY_HARD_CLOSE_21:30"
            
            # Mon-Thu: Check if this qualifies as a runner
            if profit_pips >= self.RUNNER_THRESHOLD_PIPS:
                # Spread protection: Don't close during extreme spread spikes
                if current_spread_pips > 5.0:
                    return False, "RUNNER_WAITING_BETTER_SPREAD"
                
                # Check for EMA crossover exit signal (if M5 data available)
                if df_m5 is not None and PANDAS_AVAILABLE:
                    if self._check_ema_crossover(df_m5, trade_direction):
                        return True, "RUNNER_EMA_EXIT"
                
                # Runner continues until 23:00 or EMA crossover
                return False, "RUNNER_HOLDING"
            
            # Non-runner: Close immediately at 21:30
            return True, "DAILY_CLOSE_21:30"
        
        # ============================================================
        # PRIORITY 4: Outside Trading Hours (00:00 - 01:00 weekdays)
        # ============================================================
        
        if curr_time < self.DAILY_OPEN:
            # This shouldn't happen in normal operation
            # All trades should close by 23:00 previous day (Mon-Thu) or 21:30 Friday
            return True, "OUTSIDE_TRADING_HOURS"
        
        # ============================================================
        # Normal Trading Hours (Monday 01:00 - Friday 21:30): No forced close
        # ============================================================
        
        return False, "NORMAL_TRADING_HOURS"
    
    def can_open_new_trade(self, now_utc: datetime) -> Tuple[bool, str]:
        """
        Check if new trades can be opened
        
        Rules:
        - Weekdays only: Monday 01:00 UTC - Friday 21:00 UTC
        - No entries: Friday 21:00 UTC - Monday 01:00 UTC (weekend shutdown)
        - Weekend: NO TRADING (Saturday/Sunday)
        
        Args:
            now_utc: Current UTC datetime
        
        Returns:
            Tuple[bool, str]: (can_open_trade, reason)
        """
        # Ensure timezone-aware
        if now_utc.tzinfo is None:
            now_utc = pytz.utc.localize(now_utc)
        else:
            now_utc = now_utc.astimezone(pytz.utc)
        
        weekday = now_utc.weekday()
        curr_time = now_utc.time()
        
        # ============================================================
        # Weekend Restrictions (NO TRADING OVER WEEKEND)
        # ============================================================
        
        # Saturday: No trading
        if weekday == self.SATURDAY:
            return False, "SATURDAY_CLOSED"
        
        # Sunday: No trading (regardless of time)
        if weekday == self.SUNDAY:
            return False, "SUNDAY_CLOSED"
        
        # ============================================================
        # Weekday Time Restrictions
        # ============================================================
        
        # Before Monday open (00:00 - 01:00 UTC)
        if curr_time < self.DAILY_OPEN:
            return False, "BEFORE_DAILY_OPEN"
        
        # Friday 21:00 UTC onwards: No new entries (weekend shutdown begins)
        if weekday == self.FRIDAY and curr_time >= self.NO_ENTRY_START:
            return False, "FRIDAY_WEEKEND_SHUTDOWN_21:00"
        
        # After Friday close (21:30+ UTC) - should not happen (already blocked above)
        if weekday == self.FRIDAY and curr_time >= self.DAILY_CLOSE:
            return False, "AFTER_FRIDAY_CLOSE"
        
        # ============================================================
        # Normal Trading Hours: Monday 01:00 - Friday 21:00 UTC
        # ============================================================
        
        return True, "ENTRY_ALLOWED"
    
    def _check_ema_crossover(
        self, 
        df_m5: pd.DataFrame, 
        trade_direction: Literal["LONG", "SHORT"]
    ) -> bool:
        """
        Detects EMA(9) crossing EMA(26) as exit signal
        
        Args:
            df_m5: DataFrame with 'close' column (M5 timeframe)
            trade_direction: "LONG" or "SHORT"
            
        Returns:
            True if crossover signals exit, False otherwise
        """
        if not PANDAS_AVAILABLE or df_m5 is None or len(df_m5) < 2:
            return False
        
        # Calculate EMAs
        df = df_m5.copy()
        if 'close' not in df.columns:
            return False
        
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # Get last two values
        if len(df) < 2:
            return False
        
        prev_ema9 = df['ema9'].iloc[-2]
        prev_ema26 = df['ema26'].iloc[-2]
        curr_ema9 = df['ema9'].iloc[-1]
        curr_ema26 = df['ema26'].iloc[-1]
        
        # LONG exit: EMA9 crosses below EMA26
        if trade_direction == "LONG":
            return prev_ema9 >= prev_ema26 and curr_ema9 < curr_ema26
        
        # SHORT exit: EMA9 crosses above EMA26
        elif trade_direction == "SHORT":
            return prev_ema9 <= prev_ema26 and curr_ema9 > curr_ema26
        
        return False
