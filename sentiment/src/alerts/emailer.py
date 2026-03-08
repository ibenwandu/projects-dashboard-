"""Email alert system"""

import os
import smtplib
from typing import Dict, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailAlerter:
    """Send email alerts for sentiment shifts"""
    
    def __init__(self):
        """Initialize email alerter"""
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.recipient_email = os.getenv('EMAIL_RECIPIENT', self.sender_email)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        self.enabled = bool(self.sender_email and self.sender_password)
        
        if not self.enabled:
            print("⚠️  Email alerts disabled - SENDER_EMAIL or SENDER_PASSWORD not set")
    
    def send_alert(self, alert_data: Dict):
        """
        Send sentiment shift alert email
        
        Args:
            alert_data: Dictionary with alert information
        """
        if not self.enabled:
            print("⚠️  Email alerts disabled - skipping")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            # Create subject
            asset = alert_data.get('asset', 'Unknown')
            sentiment = alert_data.get('sentiment', 'neutral').upper()
            subject = f"🚨 Sentiment Shift Alert – {asset} {alert_data.get('trade_direction', '').upper()} at Risk"
            msg['Subject'] = subject
            
            # Create body
            body = self._create_email_body(alert_data)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, msg.as_string())
            server.quit()
            
            print(f"✅ Sentiment alert email sent for {asset}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email alert: {e}")
            return False
    
    def _create_email_body(self, alert_data: Dict) -> str:
        """Create email body text"""
        asset = alert_data.get('asset', 'Unknown')
        base_currency = asset.split('/')[0] if '/' in asset else asset
        trade_direction = alert_data.get('trade_direction', '').upper()
        sentiment = alert_data.get('sentiment', 'neutral')
        sentiment_direction = alert_data.get('sentiment_direction', 'stable')
        confidence = alert_data.get('confidence', 0.0)
        drivers = alert_data.get('key_drivers', [])
        analysis = alert_data.get('analysis', '')
        current_price = alert_data.get('current_price')
        momentum = alert_data.get('price_momentum_1h')
        detected_at = alert_data.get('detected_at', datetime.now().isoformat())
        
        # Parse detected_at timestamp
        try:
            dt = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        except:
            time_str = detected_at
        
        # Format price and momentum
        price_str = f"{current_price:.5f}" if current_price else "N/A"
        momentum_str = f"{momentum:+.2f}%" if momentum is not None else "N/A"
        
        body = f"""
🚨 SENTIMENT SHIFT ALERT 🚨

Asset: {asset}
Your Position: {trade_direction} {base_currency}
Expected Bias: {alert_data.get('bias_expectation', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DETECTED SHIFT:
{base_currency} sentiment is turning {sentiment_direction.upper()}
Sentiment: {sentiment.upper()}
Confidence: {confidence:.0%}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KEY DRIVERS:
"""
        if drivers:
            for i, driver in enumerate(drivers, 1):
                body += f"  {i}. {driver}\n"
        else:
            body += "  No specific drivers identified\n"
        
        body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MARKET ANALYSIS:
{analysis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRICE DATA:
Current Price: {price_str}
1-Hour Momentum: {momentum_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIME DETECTED: {time_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUGGESTED ACTION:
• Monitor position closely
• Review recent news and macro developments
• Consider reducing exposure if risk tolerance is exceeded
• Reassess trade thesis based on new information

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated alert from the Sentiment-Aware Forex Monitor.
The system detected a sentiment shift that conflicts with your trade position.

"""

        return body

