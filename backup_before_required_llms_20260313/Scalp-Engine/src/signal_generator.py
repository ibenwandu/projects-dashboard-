"""
Signal generator using EMA Ribbon strategy
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime

class SignalGenerator:
    """Generates trading signals based on EMA Ribbon logic"""
    
    def __init__(self, ema_periods: List[int] = [9, 21, 50]):
        """
        Initialize signal generator
        
        Args:
            ema_periods: List of EMA periods [fast, medium, slow]
        """
        self.ema_periods = ema_periods
        self.ema_fast = ema_periods[0]  # 9
        self.ema_medium = ema_periods[1]  # 21
        self.ema_slow = ema_periods[2]  # 50
        
    def calculate_emas(self, closes: pd.Series) -> Dict[str, float]:
        """
        Calculate EMA values from price series
        
        Args:
            closes: Series of closing prices
            
        Returns:
            Dict with EMA values and current price
        """
        if len(closes) < self.ema_slow:
            return {}
        
        ema9 = closes.ewm(span=self.ema_fast, adjust=False).mean().iloc[-1]
        ema21 = closes.ewm(span=self.ema_medium, adjust=False).mean().iloc[-1]
        ema50 = closes.ewm(span=self.ema_slow, adjust=False).mean().iloc[-1]
        current_price = closes.iloc[-1]
        
        return {
            'ema9': ema9,
            'ema21': ema21,
            'ema50': ema50,
            'current_price': current_price
        }
    
    def check_ribbon_stack(self, ema_values: Dict[str, float]) -> Optional[str]:
        """
        Check if EMA ribbon is stacked (trending)
        
        Args:
            ema_values: Dict with EMA values
            
        Returns:
            'BULLISH' if stacked bullish, 'BEARISH' if stacked bearish, None if not stacked
        """
        if not ema_values:
            return None
        
        ema9 = ema_values['ema9']
        ema21 = ema_values['ema21']
        ema50 = ema_values['ema50']
        
        # Bullish stack: 9 > 21 > 50
        if ema9 > ema21 and ema21 > ema50:
            return 'BULLISH'
        
        # Bearish stack: 9 < 21 < 50
        if ema9 < ema21 and ema21 < ema50:
            return 'BEARISH'
        
        return None  # Not stacked (ranging/chop)
    
    def check_pullback_zone(self, ema_values: Dict[str, float], stack_type: str) -> bool:
        """
        Check if price is in pullback zone (between EMA 9 and 21)
        
        Args:
            ema_values: Dict with EMA values
            stack_type: 'BULLISH' or 'BEARISH'
            
        Returns:
            True if price is in pullback zone
        """
        if not ema_values or not stack_type:
            return False
        
        current_price = ema_values['current_price']
        ema9 = ema_values['ema9']
        ema21 = ema_values['ema21']
        
        if stack_type == 'BULLISH':
            # For bullish, pullback is when price dips into 9-21 zone
            return ema21 <= current_price <= ema9
        
        elif stack_type == 'BEARISH':
            # For bearish, pullback is when price rallies into 9-21 zone
            return ema9 <= current_price <= ema21
        
        return False
    
    def generate_signal(
        self,
        candles: List[Dict],
        regime: str = "NORMAL",
        bias: str = "NEUTRAL"
    ) -> Optional[str]:
        """
        Generate trading signal based on EMA Ribbon logic
        
        Args:
            candles: List of candle dictionaries with 'close' price
            regime: Market regime (TRENDING, RANGING, HIGH_VOL)
            bias: Global bias (BULLISH, BEARISH, NEUTRAL)
            
        Returns:
            'BUY', 'SELL', or None
        """
        if not candles or len(candles) < self.ema_slow:
            return None
        
        # Convert to pandas Series
        closes = pd.Series([c['close'] for c in candles])
        
        # Calculate EMAs
        ema_values = self.calculate_emas(closes)
        if not ema_values:
            return None
        
        # Check ribbon stack
        stack_type = self.check_ribbon_stack(ema_values)
        if not stack_type:
            return None  # No clear trend
        
        # Regime-based filtering
        if regime == "RANGING":
            # In ranging markets, EMA ribbon signals are less reliable
            return None
        
        # Check if bias aligns with stack
        if bias == "BULLISH" and stack_type != "BULLISH":
            return None  # Bias says bullish but ribbon says bearish
        if bias == "BEARISH" and stack_type != "BEARISH":
            return None  # Bias says bearish but ribbon says bullish
        
        # Check pullback zone
        in_pullback = self.check_pullback_zone(ema_values, stack_type)
        if not in_pullback:
            return None  # Not in pullback zone yet
        
        # Generate signal
        if stack_type == "BULLISH" and in_pullback:
            return "BUY"
        elif stack_type == "BEARISH" and in_pullback:
            return "SELL"
        
        return None
    
    def get_signal_strength(self, candles: List[Dict]) -> float:
        """
        Calculate signal strength (0.0 to 1.0)
        
        Args:
            candles: List of candle dictionaries
            
        Returns:
            Signal strength score
        """
        if not candles or len(candles) < self.ema_slow:
            return 0.0
        
        closes = pd.Series([c['close'] for c in candles])
        ema_values = self.calculate_emas(closes)
        
        if not ema_values:
            return 0.0
        
        stack_type = self.check_ribbon_stack(ema_values)
        if not stack_type:
            return 0.0
        
        # Calculate separation between EMAs (stronger trend = higher score)
        if stack_type == "BULLISH":
            separation = (ema_values['ema9'] - ema_values['ema50']) / ema_values['current_price']
        else:
            separation = (ema_values['ema50'] - ema_values['ema9']) / ema_values['current_price']
        
        # Normalize to 0-1 range (assuming max separation of ~0.01 or 1%)
        strength = min(abs(separation) * 100, 1.0)
        
        return strength

