"""State management for tracking alerts"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class StateManager:
    """Manage application state and alert history"""
    
    def __init__(self, state_file: str = "data/state.json"):
        """
        Initialize state manager
        
        Args:
            state_file: Path to state file
        """
        self.state_file = state_file
        self.state_dir = os.path.dirname(state_file)
        
        # Create directory if it doesn't exist
        if self.state_dir and not os.path.exists(self.state_dir):
            os.makedirs(self.state_dir, exist_ok=True)
        
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading state: {e}")
                return {}
        return {
            'last_check': None,
            'alert_history': [],
            'asset_last_check': {}
        }
    
    def _save_state(self):
        """Save state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def update_last_check(self, asset: str = None):
        """Update last check timestamp"""
        self.state['last_check'] = datetime.now().isoformat()
        if asset:
            self.state['asset_last_check'][asset] = datetime.now().isoformat()
        self._save_state()
    
    def add_alert_to_history(self, alert_data: Dict):
        """Add alert to history"""
        if 'alert_history' not in self.state:
            self.state['alert_history'] = []
        
        alert_entry = {
            'timestamp': datetime.now().isoformat(),
            'asset': alert_data.get('asset'),
            'sentiment': alert_data.get('sentiment'),
            'confidence': alert_data.get('confidence')
        }
        
        self.state['alert_history'].append(alert_entry)
        
        # Keep only last 100 alerts
        if len(self.state['alert_history']) > 100:
            self.state['alert_history'] = self.state['alert_history'][-100:]
        
        self._save_state()
    
    def was_alerted_recently(self, asset: str, minutes: int = 60) -> bool:
        """
        Check if we sent an alert for this asset recently
        
        Args:
            asset: Asset pair
            minutes: Time window in minutes
            
        Returns:
            True if alerted recently, False otherwise
        """
        if 'alert_history' not in self.state:
            return False
        
        cutoff = datetime.now().timestamp() - (minutes * 60)
        
        for alert in reversed(self.state['alert_history']):
            if alert.get('asset') != asset:
                continue
            
            try:
                alert_time = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')).timestamp()
                if alert_time > cutoff:
                    return True
            except Exception:
                continue
        
        return False






