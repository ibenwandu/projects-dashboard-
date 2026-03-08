"""
Correlation Pattern Analyzer
Detects correlative movement patterns between currency pairs
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from itertools import combinations
import logging
from scipy.stats import pearsonr, spearmanr
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Analyzes correlations and patterns between currency pairs"""
    
    def __init__(self, correlation_threshold: float = 0.7):
        """
        Initialize analyzer
        
        Args:
            correlation_threshold: Minimum correlation to consider (0.0-1.0)
        """
        self.correlation_threshold = correlation_threshold
        self.detected_patterns = []
    
    def calculate_correlation(
        self, 
        df1: pd.DataFrame, 
        df2: pd.DataFrame,
        method: str = 'pearson'
    ) -> Tuple[float, float]:
        """
        Calculate correlation between two price series
        
        Args:
            df1: First pair's price data
            df2: Second pair's price data
            method: 'pearson' or 'spearman'
            
        Returns:
            Tuple of (correlation_coefficient, p_value)
        """
        # Align data by timestamp
        aligned = pd.merge(
            df1[['close']], 
            df2[['close']], 
            left_index=True, 
            right_index=True, 
            how='inner',
            suffixes=('_1', '_2')
        )
        
        if len(aligned) < 20:  # Need minimum data points
            return 0.0, 1.0
        
        # Calculate returns for better correlation
        returns1 = aligned['close_1'].pct_change().dropna()
        returns2 = aligned['close_2'].pct_change().dropna()
        
        # Align returns
        aligned_returns = pd.merge(
            returns1.to_frame('returns_1'),
            returns2.to_frame('returns_2'),
            left_index=True,
            right_index=True,
            how='inner'
        )
        
        if len(aligned_returns) < 20:
            return 0.0, 1.0
        
        # Calculate correlation
        if method == 'pearson':
            corr, p_value = pearsonr(
                aligned_returns['returns_1'],
                aligned_returns['returns_2']
            )
        else:  # spearman
            corr, p_value = spearmanr(
                aligned_returns['returns_1'],
                aligned_returns['returns_2']
            )
        
        return corr, p_value
    
    def detect_lag_correlation(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        max_lag: int = 10
    ) -> Dict:
        """
        Detect correlation with lag (leading/lagging relationships)
        
        Args:
            df1: First pair's data
            df2: Second pair's data
            max_lag: Maximum lag periods to check
            
        Returns:
            Dictionary with best lag, correlation, and direction
        """
        # Align data
        aligned = pd.merge(
            df1[['close']],
            df2[['close']],
            left_index=True,
            right_index=True,
            how='inner',
            suffixes=('_1', '_2')
        )
        
        if len(aligned) < max_lag * 2:
            return {'lag': 0, 'correlation': 0.0, 'direction': 'none'}
        
        # Calculate returns
        returns1 = aligned['close_1'].pct_change().dropna()
        returns2 = aligned['close_2'].pct_change().dropna()
        
        best_lag = 0
        best_corr = 0.0
        best_direction = 'none'
        
        # Check positive lags (df1 leads df2)
        for lag in range(0, max_lag + 1):
            if lag == 0:
                returns1_shifted = returns1
                returns2_shifted = returns2
            else:
                returns1_shifted = returns1.shift(-lag)
                returns2_shifted = returns2
            
            # Align
            aligned_ret = pd.merge(
                returns1_shifted.to_frame('r1'),
                returns2_shifted.to_frame('r2'),
                left_index=True,
                right_index=True,
                how='inner'
            ).dropna()
            
            if len(aligned_ret) < 20:
                continue
            
            corr, _ = pearsonr(aligned_ret['r1'], aligned_ret['r2'])
            abs_corr = abs(corr)
            
            if abs_corr > abs(best_corr):
                best_corr = corr
                best_lag = lag
                best_direction = 'df1_leads_df2' if lag > 0 else 'synchronous'
        
        # Check negative lags (df2 leads df1)
        for lag in range(1, max_lag + 1):
            returns1_shifted = returns1
            returns2_shifted = returns2.shift(-lag)
            
            aligned_ret = pd.merge(
                returns1_shifted.to_frame('r1'),
                returns2_shifted.to_frame('r2'),
                left_index=True,
                right_index=True,
                how='inner'
            ).dropna()
            
            if len(aligned_ret) < 20:
                continue
            
            corr, _ = pearsonr(aligned_ret['r1'], aligned_ret['r2'])
            abs_corr = abs(corr)
            
            if abs_corr > abs(best_corr):
                best_corr = corr
                best_lag = -lag
                best_direction = 'df2_leads_df1'
        
        return {
            'lag': best_lag,
            'correlation': best_corr,
            'direction': best_direction
        }
    
    def detect_pattern(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        pair1: str,
        pair2: str
    ) -> Optional[Dict]:
        """
        Detect correlative pattern between two pairs
        
        Args:
            df1: First pair's data
            df2: Second pair's data
            pair1: Name of first pair
            pair2: Name of second pair
            
        Returns:
            Pattern dictionary or None if no significant pattern
        """
        # Calculate basic correlation
        corr, p_value = self.calculate_correlation(df1, df2)
        
        if abs(corr) < self.correlation_threshold:
            return None
        
        # Detect lag correlation
        lag_info = self.detect_lag_correlation(df1, df2)
        
        # Calculate additional metrics
        aligned = pd.merge(
            df1[['close']],
            df2[['close']],
            left_index=True,
            right_index=True,
            how='inner',
            suffixes=('_1', '_2')
        )
        
        # Calculate rolling correlation (consistency check)
        returns1 = aligned['close_1'].pct_change()
        returns2 = aligned['close_2'].pct_change()
        
        aligned_returns = pd.merge(
            returns1.to_frame('r1'),
            returns2.to_frame('r2'),
            left_index=True,
            right_index=True,
            how='inner'
        ).dropna()
        
        if len(aligned_returns) < 50:
            rolling_corr_mean = corr
            rolling_corr_std = 0.0
        else:
            rolling_corr = aligned_returns['r1'].rolling(window=20).corr(aligned_returns['r2'])
            rolling_corr_mean = rolling_corr.mean()
            rolling_corr_std = rolling_corr.std()
        
        pattern = {
            'pair1': pair1,
            'pair2': pair2,
            'correlation': corr,
            'p_value': p_value,
            'lag': lag_info['lag'],
            'direction': lag_info['direction'],
            'rolling_corr_mean': rolling_corr_mean,
            'rolling_corr_std': rolling_corr_std,
            'data_points': len(aligned),
            'significance': 'high' if p_value < 0.01 else 'medium' if p_value < 0.05 else 'low'
        }
        
        return pattern
    
    def analyze_all_pairs(
        self,
        data_dict: Dict[str, pd.DataFrame],
        max_combinations: Optional[int] = None
    ) -> List[Dict]:
        """
        Analyze correlations between all pair combinations
        
        Args:
            data_dict: Dictionary mapping pair names to DataFrames
            max_combinations: Maximum number of combinations to analyze (None = all)
            
        Returns:
            List of detected patterns
        """
        pairs = list(data_dict.keys())
        
        # Generate all combinations
        all_combinations = list(combinations(pairs, 2))
        
        if max_combinations:
            all_combinations = all_combinations[:max_combinations]
        
        logger.info(f"Analyzing {len(all_combinations)} pair combinations...")
        
        patterns = []
        
        for pair1, pair2 in all_combinations:
            try:
                df1 = data_dict[pair1]
                df2 = data_dict[pair2]
                
                pattern = self.detect_pattern(df1, df2, pair1, pair2)
                
                if pattern:
                    patterns.append(pattern)
                    logger.info(
                        f"✅ Pattern found: {pair1} <-> {pair2} "
                        f"(corr={pattern['correlation']:.3f}, lag={pattern['lag']})"
                    )
            
            except Exception as e:
                logger.warning(f"Error analyzing {pair1} <-> {pair2}: {e}")
                continue
        
        logger.info(f"✅ Detected {len(patterns)} significant patterns")
        self.detected_patterns = patterns
        
        return patterns
    
    def get_strongest_patterns(self, top_n: int = 10) -> List[Dict]:
        """
        Get top N strongest correlation patterns
        
        Args:
            top_n: Number of top patterns to return
            
        Returns:
            List of patterns sorted by correlation strength
        """
        if not self.detected_patterns:
            return []
        
        # Sort by absolute correlation
        sorted_patterns = sorted(
            self.detected_patterns,
            key=lambda x: abs(x['correlation']),
            reverse=True
        )
        
        return sorted_patterns[:top_n]

