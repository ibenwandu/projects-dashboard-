import requests
import time
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import random
from config import INDEED_BASE_URL, INDEED_SEARCH_URL, USER_AGENTS, REQUEST_DELAY

class IndeedCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = INDEED_BASE_URL
        self.search_url = INDEED_SEARCH_URL
        
    def _get_random_user_agent(self) -> str:
        """Get a random user agent to avoid detection"""
        return random.choice(USER_AGENTS)
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[requests.Response]:
        """Make a request with proper headers and error handling"""
        try:
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Add delay to be respectful
            time.sleep(random.uniform(1, REQUEST_DELAY))
            
            return response
            
        except requests.RequestException as e:
            logging.error(f"Request failed for {url}: {e}")
            return None
    
    def _parse_date_posted(self, date_text: str) -> str:
        """Parse Indeed's date format"""
        if not date_text:
            return datetime.now().strftime("%Y-%m-%d")
        
        date_text = date_text.lower().strip()
        
        # Handle various date formats
        if 'today' in date_text or 'just posted' in date_text:
            return datetime.now().strftime("%Y-%m-%d")
        elif 'yesterday' in date_text:
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif 'days ago' in date_text:
            days = re.search(r'(\d+)', date_text)
            if days:
                days_num = int(days.group(1))
                return (datetime.now() - timedelta(days=days_num)).strftime("%Y-%m-%d")
        elif 'week' in date_text:
            weeks = re.search(r'(\d+)', date_text)
            if weeks:
                weeks_num = int(weeks.group(1))
                return (datetime.now() - timedelta(weeks=weeks_num)).strftime("%Y-%m-%d")
        
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_job_id(self, job_url: str) -> str:
        """Extract job ID from Indeed URL"""
        # Indeed URLs typically contain job IDs like: /viewjob?jk=abc123
        match = re.search(r'jk=([a-zA-Z0-9]+)', job_url)
        if match:
            return match.group(1)
        
        # Fallback: use URL hash
        return str(hash(job_url))
    
    def _parse_job_listing(self, job_element) -> Optional[Dict]:
        """Parse individual job listing from search results"""
        try:
            # Extract job title
            title_element = job_element.find('h2', class_='jobTitle')
            if not title_element:
                title_element = job_element.find('a', class_='jcs-JobTitle')
            
            title = title_element.get_text(strip=True) if title_element else "Unknown Title"
            
            # Extract company name
            company_element = job_element.find('span', class_='companyName')
            if not company_element:
                company_element = job_element.find('div', class_='company')
            
            company = company_element.get_text(strip=True) if company_element else "Unknown Company"
            
            # Extract location
            location_element = job_element.find('div', class_='companyLocation')
            if not location_element:
                location_element = job_element.find('span', class_='location')
            
            location = location_element.get_text(strip=True) if location_element else "Unknown Location"
            
            # Extract job URL
            job_link = job_element.find('a', class_='jcs-JobTitle')
            if not job_link:
                job_link = job_element.find('h2').find('a') if job_element.find('h2') else None
            
            job_url = urljoin(self.base_url, job_link['href']) if job_link else ""
            job_id = self._extract_job_id(job_url)
            
            # Extract date posted
            date_element = job_element.find('span', class_='date')
            if not date_element:
                date_element = job_element.find('div', class_='date')
            
            date_posted = self._parse_date_posted(date_element.get_text(strip=True) if date_element else "")
            
            # Extract salary (if available)
            salary_element = job_element.find('div', class_='salary-snippet')
            salary = salary_element.get_text(strip=True) if salary_element else ""
            
            return {
                'job_id': job_id,
                'title': title,
                'company': company,
                'location': location,
                'date_posted': date_posted,
                'salary': salary,
                'url': job_url,
                'source': 'Indeed'
            }
            
        except Exception as e:
            logging.error(f"Error parsing job listing: {e}")
            return None
    
    def _get_job_description(self, job_url: str) -> str:
        """Get detailed job description from job page"""
        try:
            response = self._make_request(job_url)
            if not response:
                return ""
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for job description in various possible containers
            description_selectors = [
                'div[data-testid="job-description"]',
                'div.job-description',
                'div#jobDescriptionText',
                'div.description',
                'div[class*="description"]'
            ]
            
            for selector in description_selectors:
                desc_element = soup.select_one(selector)
                if desc_element:
                    return desc_element.get_text(strip=True)
            
            # Fallback: look for any div with substantial text
            content_divs = soup.find_all('div')
            for div in content_divs:
                text = div.get_text(strip=True)
                if len(text) > 200 and 'job' in text.lower():
                    return text
            
            return ""
            
        except Exception as e:
            logging.error(f"Error getting job description from {job_url}: {e}")
            return ""
    
    def search_jobs(self, 
                   job_title: str, 
                   location: str = "", 
                   date_posted: str = "7d",
                   max_pages: int = 5) -> List[Dict]:
        """Search for jobs on Indeed"""
        jobs = []
        
        try:
            for page in range(max_pages):
                params = {
                    'q': job_title,
                    'l': location,
                    'fromage': date_posted,
                    'start': page * 10  # Indeed shows 10 jobs per page
                }
                
                logging.info(f"Searching Indeed page {page + 1} for '{job_title}' in '{location}'")
                
                response = self._make_request(self.search_url, params)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find job listings
                job_elements = soup.find_all('div', class_='job_seen_beacon')
                if not job_elements:
                    job_elements = soup.find_all('div', {'data-jk': True})
                
                if not job_elements:
                    logging.warning(f"No job elements found on page {page + 1}")
                    break
                
                page_jobs = 0
                for job_element in job_elements:
                    job_data = self._parse_job_listing(job_element)
                    if job_data:
                        # Get detailed description
                        if job_data.get('url'):
                            job_data['job_description'] = self._get_job_description(job_data['url'])
                        
                        jobs.append(job_data)
                        page_jobs += 1
                
                logging.info(f"Found {page_jobs} jobs on page {page + 1}")
                
                # If no jobs found on this page, stop
                if page_jobs == 0:
                    break
                
                # Add delay between pages
                time.sleep(random.uniform(2, 4))
            
            logging.info(f"Total jobs found on Indeed: {len(jobs)}")
            return jobs
            
        except Exception as e:
            logging.error(f"Error searching Indeed jobs: {e}")
            return jobs
    
    def get_job_details(self, job_url: str) -> Optional[Dict]:
        """Get detailed information for a specific job"""
        try:
            response = self._make_request(job_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic info
            job_data = {
                'url': job_url,
                'job_id': self._extract_job_id(job_url),
                'source': 'Indeed'
            }
            
            # Extract title
            title_element = soup.find('h1')
            if title_element:
                job_data['title'] = title_element.get_text(strip=True)
            
            # Extract company
            company_element = soup.find('div', class_='company')
            if company_element:
                job_data['company'] = company_element.get_text(strip=True)
            
            # Extract location
            location_element = soup.find('div', class_='location')
            if location_element:
                job_data['location'] = location_element.get_text(strip=True)
            
            # Extract description
            job_data['job_description'] = self._get_job_description(job_url)
            
            return job_data
            
        except Exception as e:
            logging.error(f"Error getting job details from {job_url}: {e}")
            return None
