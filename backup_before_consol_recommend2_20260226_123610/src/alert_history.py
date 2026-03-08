"""Manage alert history to prevent duplicate alerts"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from src.logger import setup_logger

logger = setup_logger()

class AlertHistory:
    """Track which alerts have been sent"""
    
    def __init__(self, history_file: str = None):
        """
        Initialize alert history
        
        Args:
            history_file: Path to history JSON file
        """
        if history_file is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            history_file = os.path.join(data_dir, 'alerts_history.json')
        
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load alert history from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading alert history: {e}")
        return []
    
    def _save_history(self):
        """Save alert history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving alert history: {e}")
    
    def _create_alert_key(self, opportunity: Dict) -> str:
        """Create unique key for an alert"""
        pair = opportunity['pair']
        entry = opportunity['entry']
        direction = opportunity['direction']
        return f"{pair}_{direction}_{entry:.5f}"
    
    def has_alerted(self, opportunity: Dict) -> bool:
        """
        Check if alert has already been sent for this opportunity
        
        Args:
            opportunity: Trading opportunity dictionary
            
        Returns:
            True if already alerted
        """
        key = self._create_alert_key(opportunity)
        
        for entry in self.history:
            if entry.get('key') == key and entry.get('sent'):
                return True
        
        return False
    
    def record_alert(self, opportunity: Dict, current_price: float):
        """
        Record that an alert was sent
        
        Args:
            opportunity: Trading opportunity dictionary
            current_price: Current price when alert was sent
        """
        key = self._create_alert_key(opportunity)
        
        entry = {
            'key': key,
            'pair': opportunity['pair'],
            'entry': opportunity['entry'],
            'direction': opportunity['direction'],
            'current_price': current_price,
            'sent_at': datetime.now().isoformat(),
            'sent': True
        }
        
        self.history.append(entry)
        self._save_history()
        logger.info(f"Recorded alert: {key}")
    
    def cleanup_old_alerts(self, days: int = 7):
        """
        Remove alerts older than specified days
        
        Args:
            days: Number of days to keep alerts
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        original_count = len(self.history)
        self.history = [
            entry for entry in self.history
            if entry.get('sent_at', '') >= cutoff_str
        ]
        
        removed = original_count - len(self.history)
        if removed > 0:
            self._save_history()
            logger.info(f"Cleaned up {removed} old alerts (older than {days} days)")

