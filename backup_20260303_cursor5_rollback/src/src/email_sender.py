"""Send email with all LLM recommendations"""

import os
import smtplib
from datetime import datetime
from typing import Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from src.logger import setup_logger

load_dotenv()
logger = setup_logger()

class EmailSender:
    """Send recommendations via email"""
    
    def __init__(self):
        """Initialize email sender"""
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        try:
            self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        except ValueError:
            logger.warning("SMTP_PORT must be an integer — defaulting to 587")
            self.smtp_port = 587
        self.recipient_email = os.getenv('RECIPIENT_EMAIL', self.sender_email)
        
        self.enabled = bool(self.sender_email and self.sender_password)
        
        if not self.enabled:
            logger.warning("Email not configured - set SENDER_EMAIL and SENDER_PASSWORD")
        else:
            logger.info("✅ Email sender initialized")
    
    def send_recommendations(self, llm_recommendations: Dict[str, Optional[str]], 
                           gemini_final: Optional[str]) -> bool:
        """
        Send all recommendations via email
        
        Args:
            llm_recommendations: Dictionary with LLM names and recommendations (ChatGPT, Gemini, Claude)
            gemini_final: Gemini final synthesis
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("Email not enabled - cannot send recommendations")
            return False
        
        try:
            logger.info(f"Preparing to send email to {self.recipient_email}...")
            
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"Forex Trading Recommendations - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Build email body
            body_text = self._create_email_body(llm_recommendations, gemini_final)
            logger.debug(f"Email body length: {len(body_text)} characters")
            
            # Count available recommendations
            available_count = sum(1 for v in llm_recommendations.values() if v)
            logger.info(f"Email contains {available_count}/3 LLM recommendations + {'Gemini final' if gemini_final else 'no Gemini final'}")
            
            # Add body
            msg.attach(MIMEText(body_text, 'plain'))
            
            # Send email
            logger.info(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                logger.debug("Starting TLS...")
                server.starttls()
                logger.debug("Logging in...")
                server.login(self.sender_email, self.sender_password)
                logger.debug("Sending message...")
                server.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to {self.recipient_email}")
            logger.info(f"   Subject: {msg['Subject']}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return False
    
    def _create_email_body(self, llm_recommendations: Dict[str, Optional[str]], 
                          gemini_final: Optional[str]) -> str:
        """Create email body text"""
        body = "=" * 80 + "\n"
        body += "FOREX TRADING RECOMMENDATIONS\n"
        body += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        body += "=" * 80 + "\n\n"
        
        # Track which LLMs provided recommendations
        available_llms = []
        missing_llms = []
        
        # Add individual LLM recommendations (ChatGPT, Gemini, Claude, DeepSeek, etc.)
        for name, recommendation in llm_recommendations.items():
            if recommendation:
                available_llms.append(name)
                body += f"\n{'=' * 80}\n"
                body += f"{name.upper()} RECOMMENDATIONS\n"
                body += f"{'=' * 80}\n\n"
                body += recommendation + "\n\n"
            else:
                missing_llms.append(name)
        
        # Add note about missing recommendations
        if missing_llms:
            body += f"\n{'=' * 80}\n"
            body += "NOTE: MISSING RECOMMENDATIONS\n"
            body += f"{'=' * 80}\n\n"
            body += f"The following LLMs did not provide recommendations: {', '.join(m.upper() for m in missing_llms)}\n"
            body += "This may be due to API errors, rate limits, or model unavailability.\n"
            body += "Please check the logs for more details.\n\n"
        
        # Add Gemini final synthesis
        if gemini_final:
            body += f"\n{'=' * 80}\n"
            body += "GEMINI FINAL RECOMMENDATION\n"
            body += f"{'=' * 80}\n\n"
            body += gemini_final + "\n\n"
        else:
            body += f"\n{'=' * 80}\n"
            body += "NOTE: FINAL SYNTHESIS\n"
            body += f"{'=' * 80}\n\n"
            body += "Gemini final synthesis was not available.\n"
            if available_llms:
                body += f"Using recommendations from: {', '.join(a.upper() for a in available_llms)}\n"
            body += "\n"
        
        body += "=" * 80 + "\n"
        body += "End of Recommendations\n"
        body += "=" * 80 + "\n"
        
        return body

