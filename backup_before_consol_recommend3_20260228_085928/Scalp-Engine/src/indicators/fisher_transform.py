"""
Fisher Transform Indicator - CORRECTED Implementation
Converts price into a Gaussian normal distribution

CRITICAL: Uses CLOSE prices (not high+low/2)
Signal line is EMA-3 of Fisher (not lagged Fisher)
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class FisherTransform:
    """
    Fisher Transform Indicator - Correct Implementation
    
    Converts prices to approximate Gaussian distribution
    Range: Typically -3 to +3, with ±1.5 considered extreme
    
    Key Features:
    - Uses CLOSE prices (industry standard)
    - Signal line is EMA-3 of Fisher
    - Dynamic thresholds per pair
    - Detects mean reversion, trend continuation, and divergence
    
    References:
    - John Ehlers, "Using The Fisher Transform"
    - Cybernetic Analysis for Stocks and Futures
    """
    
    def __init__(self, period: int = 10):
        """
        Args:
            period: Lookback period for min/max normalization (default: 10)
        """
        self.period = period
        self.logger = logging.getLogger('FisherTransform')
    
    def calculate(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Fisher Transform and Signal line
        
        Args:
            prices: Close prices (NOT high/low midpoint - CORRECTED)
        
        Returns:
            (fisher, signal): Fisher values and signal line (EMA-3)
        """
        
        if len(prices) < self.period:
            raise ValueError(f"Need at least {self.period} prices, got {len(prices)}")
        
        # Step 1: Normalize prices to -1 to +1 range
        min_price = prices.rolling(self.period).min()
        max_price = prices.rolling(self.period).max()
        
        # Avoid division by zero
        price_range = max_price - min_price
        price_range = price_range.replace(0, 1e-10)
        
        # Normalize: -1 to +1
        normalized = 2 * ((prices - min_price) / price_range - 0.5)
        
        # Step 2: Clip to prevent log(0) or log(negative)
        # Must be in range (-0.999, 0.999)
        normalized = normalized.clip(-0.999, 0.999)
        
        # Step 3: Apply Fisher Transform
        # FT = 0.5 * ln((1 + x) / (1 - x))
        fisher = 0.5 * np.log((1 + normalized) / (1 - normalized))
        
        # Step 4: Calculate signal line (EMA-3 of Fisher) - CORRECTED
        signal = fisher.ewm(span=3, adjust=False).mean()
        
        return fisher, signal
    
    def calculate_dynamic_thresholds(self, fisher: pd.Series, 
                                    method: str = 'percentile') -> Tuple[float, float]:
        """
        Calculate pair-specific dynamic thresholds
        
        Args:
            fisher: Fisher Transform series
            method: 'percentile' or 'std'
        
        Returns:
            (upper_threshold, lower_threshold)
        """
        
        if method == 'percentile':
            # Use 85th/15th percentile (more data-driven)
            upper = fisher.quantile(0.85)
            lower = fisher.quantile(0.15)
        else:  # 'std'
            # Use mean ± 1.5 standard deviations
            mean = fisher.mean()
            std = fisher.std()
            upper = mean + 1.5 * std
            lower = mean - 1.5 * std
        
        self.logger.info(
            f"📊 Dynamic thresholds ({method}): Upper={upper:.2f}, Lower={lower:.2f}"
        )
        
        return upper, lower
    
    def detect_crossovers(self, 
                         fisher: pd.Series, 
                         signal: pd.Series,
                         threshold: float = 1.5,
                         use_dynamic: bool = False) -> List[Dict]:
        """
        Detect meaningful Fisher crossovers with safety checks
        
        Types of signals detected:
        1. Fisher crosses above +threshold (potential bullish - check context)
        2. Fisher crosses below -threshold (potential bearish - check context)
        3. Fisher crosses above signal (bullish confirmation)
        4. Fisher crosses below signal (bearish confirmation)
        
        SAFETY CHECKS:
        - Slope validation (not parabolic)
        - Signal line confirmation
        - Momentum reasonableness
        
        Args:
            fisher: Fisher values
            signal: Signal line
            threshold: Extreme level (default: 1.5, or use dynamic)
            use_dynamic: Whether to calculate dynamic thresholds
        
        Returns:
            List of crossover events with context
        """
        
        # Calculate dynamic thresholds if requested
        if use_dynamic:
            upper_threshold, lower_threshold = self.calculate_dynamic_thresholds(fisher)
        else:
            upper_threshold = threshold
            lower_threshold = -threshold
        
        crossovers = []
        
        for i in range(1, len(fisher)):
            prev_f, curr_f = fisher.iloc[i-1], fisher.iloc[i]
            prev_s, curr_s = signal.iloc[i-1], signal.iloc[i]
            
            # Calculate momentum (slope)
            slope = curr_f - prev_f
            
            # 1. Fisher crosses above threshold (BULLISH EXTREME)
            if prev_f < upper_threshold <= curr_f:
                # SAFETY CHECK: Confirm with signal line
                confirmed = curr_f > curr_s
                
                # SAFETY CHECK: Reasonable momentum (not parabolic spike)
                reasonable_momentum = 0.05 < slope < 1.0
                
                if confirmed and reasonable_momentum:
                    # Determine setup type
                    if curr_f > upper_threshold + 0.5:
                        setup_type = "MEAN_REVERSION"  # Extreme overbought
                        trade_direction = "SHORT"  # Fade the extreme
                        warning = "⚠️ EXTREME OVERBOUGHT - Consider mean reversion"
                    else:
                        setup_type = "TREND_CONTINUATION"  # Strong momentum
                        trade_direction = "LONG"  # Follow the trend
                        warning = None
                    
                    crossovers.append({
                        'index': i,
                        'type': 'BULLISH_EXTREME',
                        'setup_type': setup_type,
                        'trade_direction': trade_direction,
                        'fisher': curr_f,
                        'signal': curr_s,
                        'slope': slope,
                        'confidence': 'HIGH' if curr_f > upper_threshold + 0.2 else 'MEDIUM',
                        'warning': warning
                    })
            
            # 2. Fisher crosses below -threshold (BEARISH EXTREME)
            elif prev_f > lower_threshold >= curr_f:
                confirmed = curr_f < curr_s
                reasonable_momentum = -1.0 < slope < -0.05
                
                if confirmed and reasonable_momentum:
                    if curr_f < lower_threshold - 0.5:
                        setup_type = "MEAN_REVERSION"  # Extreme oversold
                        trade_direction = "LONG"  # Fade the extreme
                        warning = "⚠️ EXTREME OVERSOLD - Consider mean reversion"
                    else:
                        setup_type = "TREND_CONTINUATION"  # Strong downtrend
                        trade_direction = "SHORT"  # Follow the trend
                        warning = None
                    
                    crossovers.append({
                        'index': i,
                        'type': 'BEARISH_EXTREME',
                        'setup_type': setup_type,
                        'trade_direction': trade_direction,
                        'fisher': curr_f,
                        'signal': curr_s,
                        'slope': slope,
                        'confidence': 'HIGH' if curr_f < lower_threshold - 0.2 else 'MEDIUM',
                        'warning': warning
                    })
            
            # 3. Fisher crosses above signal (BULLISH SIGNAL CROSS)
            elif prev_f < prev_s and curr_f > curr_s:
                # Additional filter: only near zero line (not at extremes)
                if -1.0 < curr_f < 1.0:
                    crossovers.append({
                        'index': i,
                        'type': 'BULLISH_SIGNAL_CROSS',
                        'setup_type': 'TREND_CONTINUATION',
                        'trade_direction': 'LONG',
                        'fisher': curr_f,
                        'signal': curr_s,
                        'confidence': 'MEDIUM',
                        'warning': None
                    })
            
            # 4. Fisher crosses below signal (BEARISH SIGNAL CROSS)
            elif prev_f > prev_s and curr_f < curr_s:
                if -1.0 < curr_f < 1.0:
                    crossovers.append({
                        'index': i,
                        'type': 'BEARISH_SIGNAL_CROSS',
                        'setup_type': 'TREND_CONTINUATION',
                        'trade_direction': 'SHORT',
                        'fisher': curr_f,
                        'signal': curr_s,
                        'confidence': 'MEDIUM',
                        'warning': None
                    })
        
        return crossovers
    
    def detect_divergence(self, 
                         fisher: pd.Series, 
                         prices: pd.Series,
                         lookback: int = 20) -> List[Dict]:
        """
        Detect Fisher-Price divergence (mean reversion setup)
        
        Types:
        - Bullish divergence: Price makes lower low, Fisher makes higher low
        - Bearish divergence: Price makes higher high, Fisher makes lower high
        
        Args:
            fisher: Fisher Transform series
            prices: Price series
            lookback: Periods to look back for peaks/troughs
        
        Returns:
            List of divergence events
        """
        
        divergences = []
        
        if len(fisher) < lookback * 2:
            return divergences
        
        # Find peaks and troughs
        for i in range(lookback, len(fisher) - lookback):
            # Check for bullish divergence (price low, Fisher higher low)
            price_window = prices.iloc[i-lookback:i+lookback+1]
            fisher_window = fisher.iloc[i-lookback:i+lookback+1]
            
            # Find local minimum in price
            if prices.iloc[i] == price_window.min():
                # Look for previous price low
                for j in range(max(0, i - lookback * 2), i - lookback):
                    if prices.iloc[j] == prices.iloc[j-lookback:j+lookback+1].min():
                        # Found previous low - check if Fisher made higher low
                        if fisher.iloc[i] > fisher.iloc[j] and prices.iloc[i] < prices.iloc[j]:
                            divergences.append({
                                'index': i,
                                'type': 'BULLISH_DIVERGENCE',
                                'setup_type': 'MEAN_REVERSION',
                                'trade_direction': 'LONG',
                                'price_current': prices.iloc[i],
                                'price_previous': prices.iloc[j],
                                'fisher_current': fisher.iloc[i],
                                'fisher_previous': fisher.iloc[j],
                                'confidence': 'HIGH',
                                'warning': '⚠️ DIVERGENCE: Price weakness not confirmed by Fisher - potential reversal'
                            })
                            break
            
            # Check for bearish divergence (price high, Fisher lower high)
            if prices.iloc[i] == price_window.max():
                for j in range(max(0, i - lookback * 2), i - lookback):
                    if prices.iloc[j] == prices.iloc[j-lookback:j+lookback+1].max():
                        # Found previous high - check if Fisher made lower high
                        if fisher.iloc[i] < fisher.iloc[j] and prices.iloc[i] > prices.iloc[j]:
                            divergences.append({
                                'index': i,
                                'type': 'BEARISH_DIVERGENCE',
                                'setup_type': 'MEAN_REVERSION',
                                'trade_direction': 'SHORT',
                                'price_current': prices.iloc[i],
                                'price_previous': prices.iloc[j],
                                'fisher_current': fisher.iloc[i],
                                'fisher_previous': fisher.iloc[j],
                                'confidence': 'HIGH',
                                'warning': '⚠️ DIVERGENCE: Price strength not confirmed by Fisher - potential reversal'
                            })
                            break
        
        return divergences
    
    def classify_regime(self, fisher: pd.Series, 
                       prices: pd.Series = None) -> Dict:
        """
        Classify current market regime based on Fisher
        
        Args:
            fisher: Fisher values
            prices: Optional price series for additional context
        
        Returns:
            {
                'regime': 'TRENDING_UP' | 'TRENDING_DOWN' | 'RANGING' | 'EXTREME_OVERBOUGHT' | 'EXTREME_OVERSOLD',
                'fisher_value': float,
                'strength': 'WEAK' | 'MODERATE' | 'STRONG'
            }
        """
        
        current_fisher = fisher.iloc[-1]
        recent_fisher = fisher.iloc[-5:]  # Last 5 bars
        
        # Extreme levels
        if current_fisher > 2.0:
            return {
                'regime': 'EXTREME_OVERBOUGHT',
                'fisher_value': current_fisher,
                'strength': 'STRONG',
                'strategy': 'MEAN_REVERSION',
                'suggested_direction': 'SHORT'
            }
        elif current_fisher < -2.0:
            return {
                'regime': 'EXTREME_OVERSOLD',
                'fisher_value': current_fisher,
                'strength': 'STRONG',
                'strategy': 'MEAN_REVERSION',
                'suggested_direction': 'LONG'
            }
        
        # Trending
        elif current_fisher > 1.5:
            # Check if consistently high
            consistently_high = (recent_fisher > 1.0).sum() >= 3
            return {
                'regime': 'TRENDING_UP',
                'fisher_value': current_fisher,
                'strength': 'STRONG' if consistently_high else 'MODERATE',
                'strategy': 'TREND_CONTINUATION',
                'suggested_direction': 'LONG'
            }
        elif current_fisher < -1.5:
            consistently_low = (recent_fisher < -1.0).sum() >= 3
            return {
                'regime': 'TRENDING_DOWN',
                'fisher_value': current_fisher,
                'strength': 'STRONG' if consistently_low else 'MODERATE',
                'strategy': 'TREND_CONTINUATION',
                'suggested_direction': 'SHORT'
            }
        
        # Ranging (between -1 and +1)
        else:
            volatility = recent_fisher.std()
            return {
                'regime': 'RANGING',
                'fisher_value': current_fisher,
                'strength': 'WEAK' if volatility < 0.5 else 'MODERATE',
                'strategy': 'WAIT',
                'suggested_direction': 'NEUTRAL'
            }


# Helper function for quick calculation
def calculate_fisher_transform(prices: pd.Series, 
                               period: int = 10) -> Tuple[pd.Series, pd.Series]:
    """
    Quick helper to calculate Fisher Transform
    
    Args:
        prices: Close prices
        period: Lookback period
    
    Returns:
        (fisher, signal)
    """
    ft = FisherTransform(period=period)
    return ft.calculate(prices)
