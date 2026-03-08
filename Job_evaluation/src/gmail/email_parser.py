import re
import logging
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime

class EmailParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_job_email(self, email: Dict) -> Dict:
        """Parse job alert email and extract basic information"""
        try:
            parsed_data = {
                'email_id': email.get('id'),
                'sender': self._extract_sender_info(email['sender']),
                'subject': email['subject'],
                'date': self._parse_date(email['date']),
                'body_html': email['body'],
                'body_text': self._html_to_text(email['body']),
                'snippet': email['snippet'],
                'raw_email': email
            }
            
            # Extract sender domain
            parsed_data['sender_domain'] = self._extract_domain(email['sender'])
            
            # Determine email source type
            parsed_data['source_type'] = self._identify_source_type(email['sender'])
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing email {email.get('id')}: {str(e)}")
            return {}
    
    def _extract_sender_info(self, sender_string: str) -> Dict:
        """Extract sender name and email from sender string"""
        # Pattern: "Name <email@domain.com>" or just "email@domain.com"
        email_pattern = r'<(.+?)>|([^\s<>]+@[^\s<>]+)'
        name_pattern = r'^(.+?)\s*<'
        
        email_match = re.search(email_pattern, sender_string)
        name_match = re.search(name_pattern, sender_string)
        
        sender_info = {
            'full_string': sender_string,
            'email': '',
            'name': ''
        }
        
        if email_match:
            sender_info['email'] = email_match.group(1) or email_match.group(2)
        
        if name_match:
            sender_info['name'] = name_match.group(1).strip()
        elif not name_match and sender_info['email']:
            sender_info['name'] = sender_info['email'].split('@')[0]
        
        return sender_info
    
    def _extract_domain(self, sender_string: str) -> str:
        """Extract domain from sender email"""
        email_pattern = r'[^\s<>]+@([^\s<>]+)'
        match = re.search(email_pattern, sender_string)
        
        if match:
            return match.group(1).lower()
        return ''
    
    def _identify_source_type(self, sender_string: str) -> str:
        """Identify the type of job alert source"""
        sender_lower = sender_string.lower()
        
        source_mapping = {
            'linkedin': 'LinkedIn',
            'indeed': 'Indeed',
            'glassdoor': 'Glassdoor',
            'monster': 'Monster',
            'ziprecruiter': 'ZipRecruiter',
            'jobleads': 'JobLeads',
            'workopolis': 'Workopolis',
            'careerbuilder': 'CareerBuilder',
            'simplyhired': 'SimplyHired',
            'jobbank': 'Job Bank Canada',
            'dice': 'Dice',
            'stack overflow': 'Stack Overflow Jobs'
        }
        
        for key, value in source_mapping.items():
            if key in sender_lower:
                return value
        
        return 'Other'
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse email date string to datetime object"""
        try:
            return parsedate_to_datetime(date_string)
        except Exception as e:
            self.logger.warning(f"Could not parse date: {date_string}")
            return None
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        if not html_content:
            return ''
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean up whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            self.logger.warning(f"Error converting HTML to text: {str(e)}")
            return html_content
    
    def extract_job_links(self, email: Dict) -> List[str]:
        """Extract job application links from email"""
        links = []
        html_content = email.get('body', '')
        
        if not html_content:
            return links
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text().lower().strip()
                
                # Look for job-related links
                job_indicators = [
                    'apply', 'view job', 'see job', 'job details',
                    'more details', 'full details', 'learn more'
                ]
                
                # Check if link text indicates it's a job link
                if any(indicator in link_text for indicator in job_indicators):
                    links.append(href)
                
                # Also check if URL contains job-related patterns
                if self._is_job_url(href):
                    links.append(href)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)
            
            return unique_links
            
        except Exception as e:
            self.logger.error(f"Error extracting job links: {str(e)}")
            return []
    
    def _is_job_url(self, url: str) -> bool:
        """Check if URL appears to be a job posting URL"""
        job_url_patterns = [
            r'linkedin\.com/jobs/view',
            r'indeed\.com/viewjob',
            r'glassdoor\.com/job',
            r'monster\.com/job-openings',
            r'ziprecruiter\.com/jobs',
            r'jobleads\.ca/job',
            r'workopolis\.com/jobshome/db/work\.job_profile',
            r'careerbuilder\.com/job/'
        ]
        
        url_lower = url.lower()
        return any(re.search(pattern, url_lower) for pattern in job_url_patterns)
    
    def extract_email_metadata(self, email: Dict) -> Dict:
        """Extract metadata from email for analysis"""
        metadata = {
            'word_count': 0,
            'link_count': 0,
            'has_images': False,
            'html_email': False,
            'job_keywords_count': 0
        }
        
        try:
            # Check if HTML email
            if email.get('body', '').strip().startswith('<'):
                metadata['html_email'] = True
                soup = BeautifulSoup(email['body'], 'html.parser')
                text_content = soup.get_text()
                metadata['link_count'] = len(soup.find_all('a'))
                metadata['has_images'] = len(soup.find_all('img')) > 0
            else:
                text_content = email.get('body', '')
            
            # Count words
            metadata['word_count'] = len(text_content.split())
            
            # Count job-related keywords
            job_keywords = [
                'position', 'role', 'opportunity', 'career', 'hiring',
                'salary', 'benefits', 'experience', 'skills', 'qualifications',
                'requirements', 'responsibilities', 'apply', 'application'
            ]
            
            text_lower = text_content.lower()
            for keyword in job_keywords:
                metadata['job_keywords_count'] += text_lower.count(keyword)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting email metadata: {str(e)}")
            return metadata