"""
Indeed Jobs scraper using requests and BeautifulSoup.
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, quote_plus

logger = logging.getLogger(__name__)

class IndeedScraper:
    def __init__(self, user_agent: str = None):
        self.session = requests.Session()
        self.base_url = "https://ca.indeed.com"
        
        # Set up headers
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session.headers.update(headers)
    
    def search_jobs(self, search_terms: List[str], locations: List[str], 
                   days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Search for jobs on Indeed.
        
        Args:
            search_terms: List of job titles to search for
            locations: List of locations to search in
            days_back: Number of days back to search
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        
        for search_term in search_terms:
            for location in locations:
                try:
                    jobs = self._search_jobs_for_term(search_term, location, days_back)
                    all_jobs.extend(jobs)
                    time.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error searching for '{search_term}' in '{location}': {e}")
                    continue
        
        # Remove duplicates based on job URL
        seen_urls = set()
        unique_jobs = []
        
        for job in all_jobs:
            job_url = job.get('application_link', '')
            if job_url not in seen_urls:
                seen_urls.add(job_url)
                unique_jobs.append(job)
        
        logger.info(f"Found {len(unique_jobs)} unique jobs on Indeed")
        return unique_jobs
    
    def _search_jobs_for_term(self, search_term: str, location: str, days_back: int) -> List[Dict[str, Any]]:
        """Search jobs for a specific term and location."""
        jobs = []
        
        try:
            # Map days to Indeed's date filter values
            date_filter = self._get_date_filter(days_back)
            
            # Construct search URL
            params = {
                'q': search_term,
                'l': location,
                'fromage': date_filter,
                'sort': 'date',
                'limit': '50'
            }
            
            search_url = f"{self.base_url}/jobs?" + "&".join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
            
            # Get search results
            response = self.session.get(search_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            for card in job_cards:
                try:
                    job_data = self._extract_job_data(card)
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    logger.warning(f"Error extracting job data: {e}")
                    continue
            
            logger.info(f"Extracted {len(jobs)} jobs for '{search_term}' in '{location}'")
            
        except requests.RequestException as e:
            logger.error(f"Network error in Indeed search: {e}")
        except Exception as e:
            logger.error(f"Error in _search_jobs_for_term: {e}")
        
        return jobs
    
    def _get_date_filter(self, days_back: int) -> str:
        """Convert days back to Indeed's date filter format."""
        if days_back <= 1:
            return '1'
        elif days_back <= 3:
            return '3'
        elif days_back <= 7:
            return '7'
        elif days_back <= 14:
            return '14'
        else:
            return '30'
    
    def _extract_job_data(self, card_element) -> Optional[Dict[str, Any]]:
        """Extract job data from a job card element."""
        try:
            job_data = {}
            
            # Extract job title and link
            title_link = card_element.find('h2', class_='jobTitle')
            if title_link:
                title_anchor = title_link.find('a')
                if title_anchor:
                    job_data['title'] = title_anchor.get('title', '').strip()
                    relative_url = title_anchor.get('href', '')
                    job_data['application_link'] = urljoin(self.base_url, relative_url)
                else:
                    job_data['title'] = title_link.get_text().strip()
                    job_data['application_link'] = ""
            else:
                return None
            
            # Extract company name
            company_element = card_element.find('span', {'data-testid': 'company-name'})
            if not company_element:
                company_element = card_element.find('a', {'data-testid': 'company-name'})
            if company_element:
                job_data['company'] = company_element.get_text().strip()
            else:
                job_data['company'] = "Company not found"
            
            # Extract location
            location_element = card_element.find('div', {'data-testid': 'job-location'})
            if location_element:
                job_data['location'] = location_element.get_text().strip()
            else:
                job_data['location'] = "Location not found"
            
            # Extract job snippet/description
            snippet_element = card_element.find('div', class_='job-snippet')
            if snippet_element:
                job_data['description'] = snippet_element.get_text().strip()
            else:
                job_data['description'] = "Description not available"
            
            # Extract posting date
            date_element = card_element.find('span', class_='date')
            if date_element:
                job_data['posting_date'] = self._parse_posting_date(date_element.get_text())
            else:
                job_data['posting_date'] = datetime.now().strftime('%Y-%m-%d')
            
            job_data['source'] = 'Indeed'
            
            # Get full job description if we have a link
            if job_data.get('application_link'):
                full_description = self._get_full_job_description(job_data['application_link'])
                if full_description:
                    job_data['description'] = full_description
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Error extracting job data: {e}")
            return None
    
    def _get_full_job_description(self, job_url: str) -> Optional[str]:
        """Get full job description from job detail page."""
        try:
            response = self.session.get(job_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try different selectors for job description
            description_selectors = [
                'div[id="jobDescriptionText"]',
                'div.jobsearch-jobDescriptionText',
                'div.job-description',
                'div[data-testid="jobDescriptionText"]'
            ]
            
            for selector in description_selectors:
                description_element = soup.select_one(selector)
                if description_element:
                    return description_element.get_text().strip()
            
            logger.warning(f"Could not find job description for {job_url}")
            return None
            
        except Exception as e:
            logger.warning(f"Error getting full job description: {e}")
            return None
    
    def _parse_posting_date(self, date_text: str) -> str:
        """Parse posting date text to standard format."""
        try:
            date_text = date_text.lower().strip()
            now = datetime.now()
            
            if 'today' in date_text or 'just posted' in date_text:
                return now.strftime('%Y-%m-%d')
            elif 'yesterday' in date_text:
                return (now - timedelta(days=1)).strftime('%Y-%m-%d')
            elif 'day' in date_text and 'ago' in date_text:
                # Extract number of days
                days_match = re.search(r'(\d+)\s*day', date_text)
                if days_match:
                    days = int(days_match.group(1))
                    return (now - timedelta(days=days)).strftime('%Y-%m-%d')
            elif '+' in date_text:
                # "30+ days ago" format
                days_match = re.search(r'(\d+)\+', date_text)
                if days_match:
                    days = int(days_match.group(1))
                    return (now - timedelta(days=days)).strftime('%Y-%m-%d')
            
            return now.strftime('%Y-%m-%d')
            
        except Exception:
            return datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("Indeed scraper session closed")