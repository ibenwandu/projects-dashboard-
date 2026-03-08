"""
Multi-Timeframe Fisher Analyzer
Coordinates Fisher analysis across Daily, H1, and M15 timeframes
Includes trend context filters and regime detection
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from src.indicators.fisher_transform import FisherTransform, calculate_fisher_transform

logger = logging.getLogger(__name__)

class MultiTimeframeAnalyzer:
    """
    Analyzes Fisher Transform across multiple timeframes
    
    Strategy:
    - Daily: Determine overall bias (trend direction)
    - H1: Confirm entry setup
    - M15: Refine entry timing
    
    Includes:
    - Trend context (EMA alignment)
    - Regime detection
    - Divergence detection
    - Mean reversion vs trend continuation classification
    """
    
    def __init__(self, oanda_client):
        """
        Args:
            oanda_client: Client for fetching candles
        """
        self.oanda = oanda_client
        self.ft_daily = FisherTransform(period=10)
        self.ft_h1 = FisherTransform(period=10)
        self.ft_m15 = FisherTransform(period=10)
        self.logger = logging.getLogger('MultiTimeframeAnalyzer')
    
    def analyze_pair(self, pair: str) -> Optional[Dict]:
        """
        Perform complete multi-timeframe Fisher analysis
        
        Returns:
            {
                'pair': str,
                'timestamp': datetime,
                'daily': {...},
                'h1': {...},
                'm15': {...},
                'alignment': {...},
                'setup_type': 'TREND_CONTINUATION' | 'MEAN_REVERSION' | 'NO_SETUP',
                'signal': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
                'confidence': float (0-1),
                'actionable': bool,
                'warnings': list of str
            }
        """
        
        try:
            # Fetch candles for each timeframe
            daily_candles = self._fetch_candles(pair, 'D', count=50)
            h1_candles = self._fetch_candles(pair, 'H1', count=100)
            m15_candles = self._fetch_candles(pair, 'M15', count=200)
            
            def _invalid(c):
                return c is None or (hasattr(c, 'empty') and c.empty)
            if any(_invalid(c) for c in [daily_candles, h1_candles, m15_candles]):
                self.logger.warning(f"Insufficient data for {pair}")
                return None
            
            # Analyze each timeframe
            daily_analysis = self._analyze_timeframe(daily_candles, 'D')
            h1_analysis = self._analyze_timeframe(h1_candles, 'H1')
            m15_analysis = self._analyze_timeframe(m15_candles, 'M15')
            
            # Check for multi-timeframe alignment
            alignment = self._check_alignment(daily_analysis, h1_analysis, m15_analysis)
            
            # Determine setup type
            setup = self._determine_setup_type(daily_analysis, h1_analysis, m15_analysis)
            
            # Generate trading signal
            signal = self._generate_signal(alignment, setup, daily_analysis, h1_analysis, m15_analysis)
            
            # Collect warnings
            warnings = self._collect_warnings(daily_analysis, h1_analysis, setup)
            
            return {
                'pair': pair,
                'timestamp': datetime.utcnow(),
                'daily': daily_analysis,
                'h1': h1_analysis,
                'm15': m15_analysis,
                'alignment': alignment,
                'setup_type': setup['type'],
                'signal': signal['direction'],
                'confidence': signal['confidence'],
                'actionable': signal['actionable'],
                'entry_timeframe': signal.get('entry_timeframe'),
                'strategy': setup.get('strategy'),
                'warnings': warnings,
                'fisher_signal': True  # Mark as Fisher opportunity
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing {pair}: {e}", exc_info=True)
            return None
    
    def _fetch_candles(self, pair: str, granularity: str, count: int) -> Optional[pd.DataFrame]:
        """Fetch and convert candles to DataFrame with retry logic"""
        import time

        oanda_pair = pair.replace('/', '_')

        # Retry logic for transient errors (5xx, 429)
        # Increased to 3 attempts to handle OANDA intermittent 500 errors
        max_attempts = 3
        last_exception = None

        for attempt in range(max_attempts):
            try:
                from oandapyV20.endpoints.instruments import InstrumentsCandles

                params = {"count": count, "granularity": granularity}

                r = InstrumentsCandles(instrument=oanda_pair, params=params)
                self.oanda.request(r)
                candles = r.response.get('candles', [])

                if not candles:
                    return None

                df = pd.DataFrame(
                    [
                        {
                            'time': c.get('time'),
                            'open': float(c.get('mid', {}).get('o', 0) or c.get('open', 0)),
                            'high': float(c.get('mid', {}).get('h', 0) or c.get('high', 0)),
                            'low': float(c.get('mid', {}).get('l', 0) or c.get('low', 0)),
                            'close': float(c.get('mid', {}).get('c', 0) or c.get('close', 0))
                        }
                        for c in candles
                        if isinstance(c, dict) and c.get('complete', True)
                    ]
                )

                return df

            except Exception as e:
                last_exception = e
                error_msg = str(e)
                status_code = self._get_http_status_from_error(e)

                # Check if this is a retryable error (5xx or 429)
                is_retryable = status_code is None or 429 == status_code or (500 <= status_code < 600)

                if is_retryable and attempt < max_attempts - 1:
                    # Retry on transient errors
                    self.logger.debug(
                        f"Fetch {granularity} candles for {pair} (HTTP {status_code}): transient error. "
                        f"Retrying (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(2 * (attempt + 1))
                else:
                    # Non-retryable error or last attempt
                    self.logger.error(f"Error fetching {granularity} candles for {pair}: {error_msg}")
                    return None

        return None

    def _get_http_status_from_error(self, e: Exception) -> Optional[int]:
        """Extract HTTP status code from exception if present"""
        resp = getattr(e, "response", None)
        if resp is not None:
            return getattr(resp, "status_code", None)
        return None
    
    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> Dict:
        """Analyze single timeframe with trend context"""
        
        # Calculate Fisher Transform (using CLOSE prices - corrected)
        fisher, signal = calculate_fisher_transform(df['close'])
        
        # Get current values
        current_fisher = fisher.iloc[-1]
        current_signal = signal.iloc[-1]
        previous_fisher = fisher.iloc[-2]
        
        # Calculate Fisher derivative (momentum)
        fisher_momentum = current_fisher - previous_fisher
        
        # Detect crossovers
        ft = FisherTransform()
        crossovers = ft.detect_crossovers(fisher, signal, use_dynamic=True)
        recent_crossovers = [c for c in crossovers if c['index'] >= len(fisher) - 5]
        
        # Detect divergence
        divergences = ft.detect_divergence(fisher, df['close'])
        recent_divergences = [d for d in divergences if d['index'] >= len(fisher) - 10]
        
        # Classify regime
        regime = ft.classify_regime(fisher, df['close'])
        
        # Calculate EMA for trend context (CRITICAL for filtering)
        ema_50 = df['close'].ewm(span=50).mean()
        ema_200 = df['close'].ewm(span=200).mean() if len(df) >= 200 else None
        
        trend_direction = None
        if ema_200 is not None:
            if ema_50.iloc[-1] > ema_200.iloc[-1]:
                trend_direction = 'UPTREND'
            else:
                trend_direction = 'DOWNTREND'
        
        return {
            'timeframe': timeframe,
            'fisher': current_fisher,
            'signal': current_signal,
            'previous_fisher': previous_fisher,
            'momentum': fisher_momentum,
            'regime': regime,
            'crossovers': recent_crossovers,
            'divergences': recent_divergences,
            'trend': trend_direction,
            'price': df['close'].iloc[-1],
            'ema_50': ema_50.iloc[-1],
            'ema_200': ema_200.iloc[-1] if ema_200 is not None else None
        }
    
    def _check_alignment(self, daily: Dict, h1: Dict, m15: Dict) -> Dict:
        """
        Check if all timeframes are aligned
        
        Perfect alignment: All Fisher values in same direction and regime
        """
        
        # Direction alignment
        daily_bullish = daily['fisher'] > 0
        h1_bullish = h1['fisher'] > 0
        m15_bullish = m15['fisher'] > 0
        
        direction_aligned = (daily_bullish == h1_bullish == m15_bullish)
        
        # Extreme alignment (all extreme or all neutral)
        daily_extreme = abs(daily['fisher']) > 1.5
        h1_extreme = abs(h1['fisher']) > 1.5
        m15_extreme = abs(m15['fisher']) > 1.5
        
        all_extreme = daily_extreme and h1_extreme and m15_extreme
        
        # Trend alignment
        trend_aligned = (
            daily.get('trend') == h1.get('trend') if daily.get('trend') and h1.get('trend') else False
        )
        
        # Calculate alignment score (0-1)
        alignment_score = 0.0
        if direction_aligned:
            alignment_score += 0.4
        if trend_aligned:
            alignment_score += 0.3
        if all_extreme:
            alignment_score += 0.3
        
        return {
            'direction_aligned': direction_aligned,
            'trend_aligned': trend_aligned,
            'all_extreme': all_extreme,
            'score': alignment_score,
            'quality': 'HIGH' if alignment_score >= 0.7 else 'MEDIUM' if alignment_score >= 0.4 else 'LOW'
        }
    
    def _determine_setup_type(self, daily: Dict, h1: Dict, m15: Dict) -> Dict:
        """
        Determine if setup is trend continuation or mean reversion
        
        Trend Continuation:
        - Daily Fisher trending (>1.5 or <-1.5)
        - H1 pulling back but still in trend
        - M15 showing momentum in trend direction
        - Trend alignment confirmed
        
        Mean Reversion:
        - Daily Fisher extreme (>2.0 or <-2.0)
        - H1/M15 showing divergence or reversal signals
        - Trend weakening or overextended
        """
        
        daily_fisher = daily['fisher']
        h1_fisher = h1['fisher']
        m15_fisher = m15['fisher']
        
        # Check for divergence (mean reversion candidate)
        has_divergence = len(daily.get('divergences', [])) > 0 or len(h1.get('divergences', [])) > 0
        
        # Check for extreme conditions (mean reversion candidate)
        daily_extreme = abs(daily_fisher) > 2.0
        h1_reversal_signal = any(
            c['type'] in ['BEARISH_SIGNAL_CROSS', 'BULLISH_SIGNAL_CROSS']
            for c in h1.get('crossovers', [])
        )
        
        if daily_extreme and (h1_reversal_signal or has_divergence):
            return {
                'type': 'MEAN_REVERSION',
                'strategy': 'FADE_EXTREME',
                'confidence': 'HIGH',
                'rationale': f"Daily Fisher extreme ({daily_fisher:.2f}), H1 showing reversal or divergence"
            }
        
        # Check for trend continuation
        daily_trending = 1.5 < abs(daily_fisher) < 2.0
        same_direction = (
            (daily_fisher > 0 and h1_fisher > 0 and m15_fisher > 0) or
            (daily_fisher < 0 and h1_fisher < 0 and m15_fisher < 0)
        )
        trend_aligned = daily.get('trend') == h1.get('trend')
        
        if daily_trending and same_direction and trend_aligned:
            return {
                'type': 'TREND_CONTINUATION',
                'strategy': 'FOLLOW_TREND',
                'confidence': 'HIGH',
                'rationale': f"Multi-timeframe trend alignment, Daily Fisher trending ({daily_fisher:.2f})"
            }
        
        # No clear setup
        return {
            'type': 'NO_SETUP',
            'strategy': 'WAIT',
            'confidence': 'LOW',
            'rationale': 'No clear trend or mean reversion setup'
        }
    
    def _generate_signal(self, alignment: Dict, setup: Dict, 
                        daily: Dict, h1: Dict, m15: Dict) -> Dict:
        """
        Generate actionable trading signal
        
        Signal is actionable when:
        - Multi-timeframe alignment is MEDIUM or HIGH
        - Clear setup type (trend or mean reversion)
        - H1 or M15 showing entry trigger
        """
        
        # No setup = no signal
        if setup['type'] == 'NO_SETUP':
            return {
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'actionable': False,
                'reason': 'No clear setup'
            }
        
        # Determine direction
        if setup['type'] == 'TREND_CONTINUATION':
            # Follow the trend
            if h1['fisher'] > 0:
                direction = 'BULLISH'
            else:
                direction = 'BEARISH'
        else:  # MEAN_REVERSION
            # Fade the extreme
            if h1['fisher'] > 2.0:
                direction = 'BEARISH'  # Extreme overbought, expect reversal
            elif h1['fisher'] < -2.0:
                direction = 'BULLISH'  # Extreme oversold, expect reversal
            else:
                direction = 'NEUTRAL'
        
        # Calculate confidence
        confidence = 0.5  # Base
        
        if alignment['score'] >= 0.7:
            confidence += 0.2
        elif alignment['score'] >= 0.4:
            confidence += 0.1
        
        if setup['confidence'] == 'HIGH':
            confidence += 0.2
        
        # Check for recent crossover in M15 (immediate trigger)
        m15_has_recent_crossover = len(m15.get('crossovers', [])) > 0
        if m15_has_recent_crossover:
            confidence += 0.1
        
        # Actionable if confidence >= 0.6 and alignment >= MEDIUM
        actionable = (
            confidence >= 0.6 and 
            alignment['quality'] in ['MEDIUM', 'HIGH'] and
            direction != 'NEUTRAL'
        )
        
        # Determine which timeframe should trigger entry
        if m15_has_recent_crossover:
            entry_timeframe = 'M15'
        else:
            entry_timeframe = 'H1'
        
        return {
            'direction': direction,
            'confidence': min(confidence, 1.0),  # Cap at 1.0
            'actionable': actionable,
            'entry_timeframe': entry_timeframe,
            'reason': f"{setup['strategy']} setup with {alignment['quality']} alignment"
        }
    
    def _collect_warnings(self, daily: Dict, h1: Dict, setup: Dict) -> List[str]:
        """Collect all warnings from analysis"""
        warnings = []
        
        # Check crossover warnings
        for crossover in daily.get('crossovers', []):
            if crossover.get('warning'):
                warnings.append(f"Daily: {crossover['warning']}")
        
        for crossover in h1.get('crossovers', []):
            if crossover.get('warning'):
                warnings.append(f"H1: {crossover['warning']}")
        
        # Check divergence warnings
        for divergence in daily.get('divergences', []):
            if divergence.get('warning'):
                warnings.append(f"Daily: {divergence['warning']}")
        
        for divergence in h1.get('divergences', []):
            if divergence.get('warning'):
                warnings.append(f"H1: {divergence['warning']}")
        
        return warnings
