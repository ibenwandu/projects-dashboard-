import requests
import time
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
import random
from config import LINKEDIN_BASE_URL, LINKEDIN_JOBS_URL, USER_AGENTS, REQUEST_DELAY

class LinkedInCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = LINKEDIN_BASE_URL
        self.jobs_url = LINKEDIN_JOBS_URL
        
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
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
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
        """Parse LinkedIn's date format"""
        if not date_text:
            return datetime.now().strftime("%Y-%m-%d")
        
        date_text = date_text.lower().strip()
        
        # Handle various date formats
        if 'today' in date_text or 'just now' in date_text:
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
        elif 'month' in date_text:
            months = re.search(r'(\d+)', date_text)
            if months:
                months_num = int(months.group(1))
                return (datetime.now() - timedelta(days=months_num*30)).strftime("%Y-%m-%d")
        
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_job_id(self, job_url: str) -> str:
        """Extract job ID from LinkedIn URL"""
        # LinkedIn URLs typically contain job IDs like: /jobs/view/123456789
        match = re.search(r'/jobs/view/(\d+)', job_url)
        if match:
            return match.group(1)
        
        # Alternative pattern
        match = re.search(r'/jobs/(\d+)', job_url)
        if match:
            return match.group(1)
        
        # Fallback: use URL hash
        return str(hash(job_url))
    
    def _parse_job_listing(self, job_element) -> Optional[Dict]:
        """Parse individual job listing from search results"""
        try:
            # Extract job title
            title_element = job_element.find('h3', class_='base-search-card__title')
            if not title_element:
                title_element = job_element.find('a', class_='job-card-container__link')
            
            title = title_element.get_text(strip=True) if title_element else "Unknown Title"
            
            # Extract company name
            company_element = job_element.find('h4', class_='base-search-card__subtitle')
            if not company_element:
                company_element = job_element.find('span', class_='job-card-container__company-name')
            
            company = company_element.get_text(strip=True) if company_element else "Unknown Company"
            
            # Extract location
            location_element = job_element.find('span', class_='job-search-card__location')
            if not location_element:
                location_element = job_element.find('span', class_='job-card-container__metadata-item')
            
            location = location_element.get_text(strip=True) if location_element else "Unknown Location"
            
            # Extract job URL
            job_link = job_element.find('a', class_='base-card__full-link')
            if not job_link:
                job_link = job_element.find('a', class_='job-card-container__link')
            
            job_url = urljoin(self.base_url, job_link['href']) if job_link else ""
            job_id = self._extract_job_id(job_url)
            
            # Extract date posted
            date_element = job_element.find('time')
            if not date_element:
                date_element = job_element.find('span', class_='job-search-card__listdate')
            
            date_posted = self._parse_date_posted(date_element.get_text(strip=True) if date_element else "")
            
            # Extract job type (if available)
            job_type_element = job_element.find('span', class_='job-search-card__job-type')
            job_type = job_type_element.get_text(strip=True) if job_type_element else ""
            
            return {
                'job_id': job_id,
                'title': title,
                'company': company,
                'location': location,
                'date_posted': date_posted,
                'job_type': job_type,
                'url': job_url,
                'source': 'LinkedIn'
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
                'div[class*="description__text"]',
                'div[class*="job-description"]',
                'div[class*="show-more-less-html"]',
                'div.description',
                'section[class*="description"]'
            ]
            
            for selector in description_selectors:
                desc_element = soup.select_one(selector)
                if desc_element:
                    return desc_element.get_text(strip=True)
            
            # Fallback: look for any div with substantial text
            content_divs = soup.find_all('div')
            for div in content_divs:
                text = div.get_text(strip=True)
                if len(text) > 200 and ('job' in text.lower() or 'responsibilities' in text.lower()):
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
        """Search for jobs on LinkedIn"""
        jobs = []
        
        try:
            for page in range(max_pages):
                params = {
                    'keywords': job_title,
                    'location': location,
                    'f_TPR': date_posted,
                    'start': page * 25  # LinkedIn shows 25 jobs per page
                }
                
                logging.info(f"Searching LinkedIn page {page + 1} for '{job_title}' in '{location}'")
                
                response = self._make_request(self.jobs_url, params)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find job listings
                job_elements = soup.find_all('div', class_='base-card')
                if not job_elements:
                    job_elements = soup.find_all('div', {'data-job-id': True})
                
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
            
            logging.info(f"Total jobs found on LinkedIn: {len(jobs)}")
            return jobs
            
        except Exception as e:
            logging.error(f"Error searching LinkedIn jobs: {e}")
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
                'source': 'LinkedIn'
            }
            
            # Extract title
            title_element = soup.find('h1', class_='top-card-layout__title')
            if title_element:
                job_data['title'] = title_element.get_text(strip=True)
            
            # Extract company
            company_element = soup.find('a', class_='topcard__org-name-link')
            if company_element:
                job_data['company'] = company_element.get_text(strip=True)
            
            # Extract location
            location_element = soup.find('span', class_='topcard__flavor--bullet')
            if location_element:
                job_data['location'] = location_element.get_text(strip=True)
            
            # Extract description
            job_data['job_description'] = self._get_job_description(job_url)
            
            return job_data
            
        except Exception as e:
            logging.error(f"Error getting job details from {job_url}: {e}")
            return None
























