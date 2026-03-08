"""
Pattern Consistency Validator
Validates pattern consistency across different timeframes and time periods
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PatternValidator:
    """Validates pattern consistency across timeframes and time periods"""
    
    def __init__(self, consistency_threshold: float = 0.6):
        """
        Initialize validator
        
        Args:
            consistency_threshold: Minimum consistency score (0.0-1.0)
        """
        self.consistency_threshold = consistency_threshold
    
    def validate_across_timeframes(
        self,
        pattern: Dict,
        daily_data: Dict[str, pd.DataFrame],
        weekly_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Validate pattern consistency across daily and weekly timeframes
        
        Args:
            pattern: Pattern dictionary from correlation analyzer
            daily_data: Dictionary of daily DataFrames
            weekly_data: Dictionary of weekly DataFrames
            
        Returns:
            Validation results with consistency scores
        """
        pair1 = pattern['pair1']
        pair2 = pattern['pair2']
        
        # Check if data exists for both timeframes
        if pair1 not in daily_data or pair2 not in daily_data:
            return {'valid': False, 'reason': 'Missing daily data'}
        
        if pair1 not in weekly_data or pair2 not in weekly_data:
            return {'valid': False, 'reason': 'Missing weekly data'}
        
        # Calculate correlation in daily timeframe
        from src.correlation_analyzer import CorrelationAnalyzer
        analyzer = CorrelationAnalyzer(correlation_threshold=0.0)
        
        daily_corr, _ = analyzer.calculate_correlation(
            daily_data[pair1],
            daily_data[pair2]
        )
        
        # Calculate correlation in weekly timeframe
        weekly_corr, _ = analyzer.calculate_correlation(
            weekly_data[pair1],
            weekly_data[pair2]
        )
        
        # Check consistency
        # Pattern is consistent if correlations are similar in both timeframes
        corr_diff = abs(abs(daily_corr) - abs(weekly_corr))
        consistency_score = 1.0 - min(corr_diff, 1.0)
        
        # Check if both timeframes show significant correlation
        both_significant = (
            abs(daily_corr) >= 0.5 and 
            abs(weekly_corr) >= 0.5
        )
        
        valid = (
            consistency_score >= self.consistency_threshold and
            both_significant
        )
        
        return {
            'valid': valid,
            'consistency_score': consistency_score,
            'daily_correlation': daily_corr,
            'weekly_correlation': weekly_corr,
            'correlation_difference': corr_diff,
            'both_significant': both_significant
        }
    
    def validate_across_time_periods(
        self,
        pattern: Dict,
        data_dict: Dict[str, pd.DataFrame],
        periods: int = 4
    ) -> Dict:
        """
        Validate pattern consistency across different time periods
        Splits data into N periods and checks if correlation holds
        
        Args:
            pattern: Pattern dictionary
            data_dict: Dictionary of DataFrames
            periods: Number of time periods to split into
            
        Returns:
            Validation results with period-by-period analysis
        """
        pair1 = pattern['pair1']
        pair2 = pattern['pair2']
        
        if pair1 not in data_dict or pair2 not in data_dict:
            return {'valid': False, 'reason': 'Missing data'}
        
        df1 = data_dict[pair1]
        df2 = data_dict[pair2]
        
        # Align data
        aligned = pd.merge(
            df1[['close']],
            df2[['close']],
            left_index=True,
            right_index=True,
            how='inner',
            suffixes=('_1', '_2')
        )
        
        if len(aligned) < periods * 20:  # Need enough data
            return {'valid': False, 'reason': 'Insufficient data'}
        
        # Split into periods
        period_length = len(aligned) // periods
        period_correlations = []
        
        from src.correlation_analyzer import CorrelationAnalyzer
        analyzer = CorrelationAnalyzer(correlation_threshold=0.0)
        
        for i in range(periods):
            start_idx = i * period_length
            end_idx = (i + 1) * period_length if i < periods - 1 else len(aligned)
            
            period_df1 = aligned.iloc[start_idx:end_idx][['close_1']].copy()
            period_df2 = aligned.iloc[start_idx:end_idx][['close_2']].copy()
            
            # Calculate correlation for this period
            corr, _ = analyzer.calculate_correlation(
                period_df1.rename(columns={'close_1': 'close'}),
                period_df2.rename(columns={'close_2': 'close'})
            )
            
            period_correlations.append(corr)
        
        # Calculate consistency metrics
        mean_corr = np.mean([abs(c) for c in period_correlations])
        std_corr = np.std([abs(c) for c in period_correlations])
        
        # Consistency: low std means consistent across periods
        consistency_score = 1.0 - min(std_corr, 1.0)
        
        # Check if all periods show significant correlation
        significant_periods = sum([abs(c) >= 0.5 for c in period_correlations])
        all_periods_significant = significant_periods == periods
        
        valid = (
            consistency_score >= self.consistency_threshold and
            mean_corr >= 0.5 and
            all_periods_significant
        )
        
        return {
            'valid': valid,
            'consistency_score': consistency_score,
            'mean_correlation': mean_corr,
            'std_correlation': std_corr,
            'period_correlations': period_correlations,
            'significant_periods': significant_periods,
            'total_periods': periods
        }
    
    def validate_pattern(
        self,
        pattern: Dict,
        daily_data: Dict[str, pd.DataFrame],
        weekly_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Comprehensive pattern validation
        
        Args:
            pattern: Pattern dictionary
            daily_data: Daily timeframe data
            weekly_data: Weekly timeframe data
            
        Returns:
            Complete validation results
        """
        # Validate across timeframes
        timeframe_validation = self.validate_across_timeframes(
            pattern, daily_data, weekly_data
        )
        
        # Validate across time periods (using daily data)
        period_validation = self.validate_across_time_periods(
            pattern, daily_data, periods=4
        )
        
        # Overall validation
        overall_valid = (
            timeframe_validation.get('valid', False) and
            period_validation.get('valid', False)
        )
        
        # Calculate overall consistency score
        timeframe_score = timeframe_validation.get('consistency_score', 0.0)
        period_score = period_validation.get('consistency_score', 0.0)
        overall_consistency = (timeframe_score + period_score) / 2.0
        
        return {
            'pattern': pattern,
            'overall_valid': overall_valid,
            'overall_consistency': overall_consistency,
            'timeframe_validation': timeframe_validation,
            'period_validation': period_validation
        }
    
    def validate_all_patterns(
        self,
        patterns: List[Dict],
        daily_data: Dict[str, pd.DataFrame],
        weekly_data: Dict[str, pd.DataFrame]
    ) -> List[Dict]:
        """
        Validate all patterns
        
        Args:
            patterns: List of pattern dictionaries
            daily_data: Daily timeframe data
            weekly_data: Weekly timeframe data
            
        Returns:
            List of validation results
        """
        logger.info(f"Validating {len(patterns)} patterns...")
        
        validated_patterns = []
        
        for pattern in patterns:
            try:
                validation = self.validate_pattern(
                    pattern, daily_data, weekly_data
                )
                validated_patterns.append(validation)
                
                if validation['overall_valid']:
                    logger.info(
                        f"✅ Valid pattern: {pattern['pair1']} <-> {pattern['pair2']} "
                        f"(consistency: {validation['overall_consistency']:.2f})"
                    )
                else:
                    logger.debug(
                        f"❌ Invalid pattern: {pattern['pair1']} <-> {pattern['pair2']}"
                    )
            
            except Exception as e:
                logger.warning(f"Error validating pattern {pattern.get('pair1', '?')}: {e}")
                continue
        
        valid_count = sum([1 for v in validated_patterns if v['overall_valid']])
        logger.info(f"✅ Validated: {valid_count}/{len(patterns)} patterns are consistent")
        
        return validated_patterns

