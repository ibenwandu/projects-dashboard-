import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

class TextProcessor:
    """Utility class for text processing and cleaning"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def clean_html(html_content: str) -> str:
        """Convert HTML to clean text"""
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
        except Exception:
            return html_content
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 3) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + ',}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one',
            'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see',
            'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'will',
            'with', 'have', 'this', 'that', 'they', 'from', 'been', 'said', 'each', 'which', 'their',
            'time', 'would', 'there', 'could', 'other', 'after', 'first', 'well', 'water', 'very', 'what'
        }
        
        # Filter out stop words and get unique keywords
        keywords = list(set(word for word in words if word not in stop_words))
        keywords.sort()
        
        return keywords
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
        """Truncate text to specified length"""
        if not text or len(text) <= max_length:
            return text
        
        # Try to truncate at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can truncate at a nearby word boundary
            return truncated[:last_space] + suffix
        else:
            return truncated + suffix
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace in text"""
        if not text:
            return ''
        
        # Replace multiple whitespace characters with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def extract_email_addresses(text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    @staticmethod
    def clean_job_title(title: str) -> str:
        """Clean and standardize job title"""
        if not title:
            return ''
        
        # Remove common prefixes
        title = re.sub(r'^(Job Alert:?|New Job:?|Position:?|Role:?)\s*', '', title, flags=re.IGNORECASE)
        
        # Remove application-related suffixes
        title = re.sub(r'\s*-\s*(Apply Now|Apply Today|Click to Apply).*$', '', title, flags=re.IGNORECASE)
        
        # Clean up whitespace
        title = TextProcessor.normalize_whitespace(title)
        
        return title.strip()
    
    @staticmethod
    def clean_company_name(company: str) -> str:
        """Clean and standardize company name"""
        if not company:
            return ''
        
        # Remove common corporate suffixes
        company = re.sub(r'\s*(Inc\.?|LLC\.?|Corp\.?|Ltd\.?|Co\.?|Corporation|Limited)$', '', company, flags=re.IGNORECASE)
        
        # Clean up whitespace
        company = TextProcessor.normalize_whitespace(company)
        
        return company.strip()
    
    @staticmethod
    def extract_salary_info(text: str) -> Optional[Dict]:
        """Extract salary information from text"""
        salary_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $50,000 - $60,000
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:per|\/)\s*(year|month|hour)',  # $50,000 per year
            r'(\d{1,3}(?:,\d{3})*)k?\s*-\s*(\d{1,3}(?:,\d{3})*)k?',  # 50k - 60k
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'found': True,
                    'text': match.group(0),
                    'min_value': match.group(1) if len(match.groups()) >= 1 else None,
                    'max_value': match.group(2) if len(match.groups()) >= 2 else None
                }
        
        return None