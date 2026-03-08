"""Decision engine for determining when to send alerts"""

from typing import Dict, List, Optional
from datetime import datetime

class DecisionEngine:
    """Make decisions about when to send alerts"""
    
    def __init__(self, confidence_threshold: float = 0.7, momentum_threshold: float = 0.5):
        """
        Initialize decision engine
        
        Args:
            confidence_threshold: Minimum confidence for sentiment analysis
            momentum_threshold: Minimum price momentum to trigger investigation
        """
        self.confidence_threshold = confidence_threshold
        self.momentum_threshold = momentum_threshold
    
    def should_investigate(self, price_signals: Dict) -> bool:
        """
        Determine if we should investigate fundamentals based on price signals
        
        Args:
            price_signals: Dictionary with price signal data
            
        Returns:
            True if we should investigate, False otherwise
        """
        # Investigate if price is moving against trade
        if price_signals.get('moving_against_trade'):
            return True
        
        # Investigate if volatility has increased significantly
        if price_signals.get('volatility_increased'):
            return True
        
        # Investigate if momentum exceeds threshold
        momentum_1h = price_signals.get('momentum_1h')
        if momentum_1h and abs(momentum_1h) > self.momentum_threshold:
            return True
        
        return False
    
    def should_alert(self, price_signals: Dict, sentiment_analysis: Dict) -> bool:
        """
        Determine if we should send an alert
        
        Args:
            price_signals: Dictionary with price signal data
            sentiment_analysis: Dictionary with sentiment analysis results
            
        Returns:
            True if alert should be sent, False otherwise
        """
        # Must have sentiment conflict
        if not sentiment_analysis.get('conflicts_with_trade'):
            return False
        
        # Must meet confidence threshold
        confidence = sentiment_analysis.get('confidence', 0.0)
        if confidence < self.confidence_threshold:
            return False
        
        # Sentiment must be clear (not neutral)
        sentiment = sentiment_analysis.get('sentiment', 'neutral')
        if sentiment == 'neutral':
            return False
        
        # Should have some price movement confirmation (optional but preferred)
        # Price moving against trade strengthens the alert
        if price_signals.get('moving_against_trade'):
            return True
        
        # Even without price confirmation, if sentiment is strong enough, alert
        if confidence >= 0.8:
            return True
        
        return False
    
    def generate_alert_data(self, asset: str, trade_info: Dict, price_signals: Dict, 
                           sentiment_analysis: Dict, news_items: List[Dict]) -> Dict:
        """
        Generate alert data dictionary
        
        Args:
            asset: Forex pair (e.g., "USD/CAD")
            trade_info: Trade information from watchlist
            price_signals: Price signal data
            sentiment_analysis: Sentiment analysis results
            news_items: List of relevant news items
            
        Returns:
            Dictionary with alert data
        """
        base_currency = asset.split('/')[0]
        
        return {
            'asset': asset,
            'trade_direction': trade_info.get('trade_direction'),
            'bias_expectation': trade_info.get('bias_expectation'),
            'current_price': price_signals.get('current_price'),
            'price_momentum_1h': price_signals.get('momentum_1h'),
            'sentiment': sentiment_analysis.get('sentiment'),
            'sentiment_direction': sentiment_analysis.get('direction'),
            'confidence': sentiment_analysis.get('confidence'),
            'key_drivers': sentiment_analysis.get('drivers', []),
            'analysis': sentiment_analysis.get('analysis'),
            'conflicts_with_trade': sentiment_analysis.get('conflicts_with_trade'),
            'news_count': len(news_items),
            'detected_at': datetime.now().isoformat(),
            'sensitivity': trade_info.get('sensitivity', 'medium')
        }






