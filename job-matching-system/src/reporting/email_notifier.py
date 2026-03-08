"""
Email notification service for job matching and resume generation updates.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self, sender_email: str, sender_password: str, recipient_email: str,
                 smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
    def send_email(self, subject: str, body: str, is_html: bool = False) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject line
            body: Email body content
            is_html: Whether body is HTML formatted
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
            
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.sender_email, self.recipient_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_job_summary(self, high_scoring_jobs: list, total_jobs: int) -> bool:
        """Send daily job search summary."""
        subject = f"Daily Job Search Summary - {len(high_scoring_jobs)} High-Scoring Jobs Found"
        
        html_body = f"""
        <html>
        <body>
            <h2>Daily Job Search Summary</h2>
            <p><strong>Total jobs scraped:</strong> {total_jobs}</p>
            <p><strong>High-scoring jobs (85+):</strong> {len(high_scoring_jobs)}</p>
            
            {self._format_jobs_html(high_scoring_jobs) if high_scoring_jobs else '<p>No high-scoring jobs found today.</p>'}
            
            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>Review jobs in your Google Sheets</li>
                <li>Check the 'Apply' checkbox for desired positions</li>
                <li>Custom resumes will be generated automatically</li>
            </ul>
        </body>
        </html>
        """
        
        return self.send_email(subject, html_body, is_html=True)
    
    def send_resume_notification(self, job_title: str, company: str, resume_link: str) -> bool:
        """Send notification when a resume is generated."""
        subject = f"Custom Resume Generated - {job_title} at {company}"
        
        html_body = f"""
        <html>
        <body>
            <h2>Custom Resume Generated</h2>
            <p>A tailored resume has been created for:</p>
            
            <ul>
                <li><strong>Position:</strong> {job_title}</li>
                <li><strong>Company:</strong> {company}</li>
                <li><strong>Resume Link:</strong> <a href="{resume_link}">Download Resume</a></li>
            </ul>
            
            <p>The resume has been optimized for this specific role and is ready for your application.</p>
        </body>
        </html>
        """
        
        return self.send_email(subject, html_body, is_html=True)
    
    def send_error_notification(self, error_message: str, component: str) -> bool:
        """Send error notification."""
        subject = f"Job Matching System Error - {component}"
        
        body = f"""
        An error occurred in the Job Matching System:
        
        Component: {component}
        Error: {error_message}
        
        Please check the logs for more details.
        """
        
        return self.send_email(subject, body)
    
    def _format_jobs_html(self, jobs: list) -> str:
        """Format jobs list as HTML."""
        html_parts = ["<h3>High-Scoring Job Opportunities:</h3>"]
        
        for job in jobs[:10]:  # Show top 10 jobs
            html_parts.append(f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0;">
                <h4>{job.get('title', 'N/A')} at {job.get('company', 'N/A')}</h4>
                <p><strong>Score:</strong> {job.get('score', 'N/A')}/100</p>
                <p><strong>Location:</strong> {job.get('location', 'N/A')}</p>
                <p><strong>Match Reasoning:</strong> {job.get('match_reasoning', 'N/A')}</p>
                <p><a href="{job.get('application_link', '#')}">View Job Posting</a></p>
            </div>
            """)
        
        return "".join(html_parts)