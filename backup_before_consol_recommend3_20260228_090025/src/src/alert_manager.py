"""Send Pushover alerts"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

class AlertManager:
    """Manage Pushover alerts"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.api_token = os.getenv('PUSHOVER_API_TOKEN', '')
        self.user_key = os.getenv('PUSHOVER_USER_KEY', '')
        self.enabled = bool(self.api_token and self.user_key)
        
        if not self.enabled:
            logger.warning("Pushover not configured - alerts will not be sent")
            logger.warning("Set PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY in .env")
        else:
            logger.info("✅ Pushover alert manager initialized")
    
    def send_alert(self, title: str, message: str, priority: int = 0) -> bool:
        """
        Send Pushover alert
        
        Args:
            title: Alert title
            message: Alert message
            priority: Priority (0=normal, 1=high, 2=emergency)
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.debug("Pushover not enabled, skipping alert")
            return False
        
        try:
            url = "https://api.pushover.net/1/messages.json"
            data = {
                'token': self.api_token,
                'user': self.user_key,
                'title': title,
                'message': message,
                'priority': priority
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 1:
                logger.info(f"✅ Pushover alert sent: {title}")
                return True
            else:
                logger.error(f"❌ Pushover API error: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Error sending Pushover alert: {e}")
            return False
    
    def send_entry_alert(self, opportunity: dict, current_price: float) -> bool:
        """
        Send alert for entry point hit
        
        Args:
            opportunity: Trading opportunity dictionary
            current_price: Current market price
            
        Returns:
            True if sent successfully
        """
        pair = opportunity['pair']
        entry = opportunity['entry']
        direction = opportunity['direction']
        
        title = f"🚨 Entry Point Hit: {pair} {direction}"
        
        message = f"""
{pair} Entry Point Triggered!

Direction: {direction}
Entry Price: {entry}
Current Price: {current_price:.5f}
"""
        
        if opportunity.get('exit'):
            message += f"Target: {opportunity['exit']}\n"
        
        if opportunity.get('stop_loss'):
            message += f"Stop Loss: {opportunity['stop_loss']}\n"
        
        if opportunity.get('position_size'):
            message += f"Position Size: {opportunity['position_size']}\n"
        
        if opportunity.get('recommendation'):
            rec = opportunity['recommendation'][:200]  # First 200 chars
            message += f"\nRecommendation: {rec}"
        
        return self.send_alert(title, message.strip(), priority=1)  # High priority

