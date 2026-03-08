"""
LinkedIn Jobs scraper using Selenium.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, email: str, password: str, headless: bool = True):
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = None
        self.wait = None
    
    def setup_driver(self):
        """Initialize Chrome WebDriver with appropriate settings."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        
        logger.info("Chrome WebDriver initialized")
    
    def login(self):
        """Login to LinkedIn."""
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if we're on the feed page (successful login)
            if "/feed/" in self.driver.current_url or "/in/" in self.driver.current_url:
                logger.info("LinkedIn login successful")
                return True
            else:
                logger.error("LinkedIn login failed - unexpected redirect")
                return False
                
        except Exception as e:
            logger.error(f"LinkedIn login error: {e}")
            return False
    
    def search_jobs(self, search_terms: List[str], locations: List[str], 
                   days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Search for jobs on LinkedIn.
        
        Args:
            search_terms: List of job titles to search for
            locations: List of locations to search in
            days_back: Number of days back to search (1, 7, 30)
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        
        for search_term in search_terms:
            for location in locations:
                try:
                    jobs = self._search_jobs_for_term(search_term, location, days_back)
                    all_jobs.extend(jobs)
                    time.sleep(3)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error searching for '{search_term}' in '{location}': {e}")
                    continue
        
        # Remove duplicates based on job ID or URL
        seen_urls = set()
        unique_jobs = []
        
        for job in all_jobs:
            job_url = job.get('application_link', '')
            if job_url not in seen_urls:
                seen_urls.add(job_url)
                unique_jobs.append(job)
        
        logger.info(f"Found {len(unique_jobs)} unique jobs on LinkedIn")
        return unique_jobs
    
    def _search_jobs_for_term(self, search_term: str, location: str, days_back: int) -> List[Dict[str, Any]]:
        """Search jobs for a specific term and location."""
        jobs = []
        
        try:
            # Construct search URL
            base_url = "https://www.linkedin.com/jobs/search/"
            params = {
                'keywords': search_term,
                'location': location,
                'f_TPR': f'r{days_back * 86400}',  # Convert days to seconds
                'f_LF': 'f_AL',  # Easy Apply filter (optional)
                'sortBy': 'DD'  # Sort by date
            }
            
            # Build URL with parameters
            param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            search_url = f"{base_url}?{param_string}"
            
            self.driver.get(search_url)
            time.sleep(3)
            
            # Scroll and load more jobs
            self._scroll_and_load_jobs()
            
            # Extract job cards
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[data-job-id]")
            
            for card in job_cards[:50]:  # Limit to first 50 jobs
                try:
                    job_data = self._extract_job_data(card)
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    logger.warning(f"Error extracting job data: {e}")
                    continue
            
            logger.info(f"Extracted {len(jobs)} jobs for '{search_term}' in '{location}'")
            
        except Exception as e:
            logger.error(f"Error in _search_jobs_for_term: {e}")
        
        return jobs
    
    def _scroll_and_load_jobs(self):
        """Scroll down to load more job listings."""
        try:
            for i in range(3):  # Scroll 3 times
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try to click "See more jobs" button if it exists
                try:
                    see_more_button = self.driver.find_element(
                        By.XPATH, "//button[contains(@aria-label, 'See more jobs')]"
                    )
                    if see_more_button.is_displayed():
                        see_more_button.click()
                        time.sleep(3)
                except NoSuchElementException:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error scrolling and loading jobs: {e}")
    
    def _extract_job_data(self, card_element) -> Optional[Dict[str, Any]]:
        """Extract job data from a job card element."""
        try:
            job_data = {}
            
            # Get job ID
            job_id = card_element.get_attribute('data-job-id')
            
            # Click on the job card to load details
            card_element.click()
            time.sleep(2)
            
            # Extract job title
            try:
                title_element = self.driver.find_element(
                    By.CSS_SELECTOR, "h1[data-test-id='job-title']"
                )
                job_data['title'] = title_element.text.strip()
            except NoSuchElementException:
                job_data['title'] = "Title not found"
            
            # Extract company name
            try:
                company_element = self.driver.find_element(
                    By.CSS_SELECTOR, "a[data-test-id='job-details-company-name']"
                )
                job_data['company'] = company_element.text.strip()
            except NoSuchElementException:
                job_data['company'] = "Company not found"
            
            # Extract location
            try:
                location_element = self.driver.find_element(
                    By.CSS_SELECTOR, "span[data-test-id='job-details-location']"
                )
                job_data['location'] = location_element.text.strip()
            except NoSuchElementException:
                job_data['location'] = "Location not found"
            
            # Extract job description
            try:
                description_element = self.driver.find_element(
                    By.CSS_SELECTOR, "div[data-test-id='job-details-description']"
                )
                job_data['description'] = description_element.text.strip()
            except NoSuchElementException:
                job_data['description'] = "Description not available"
            
            # Extract posting date
            try:
                date_element = self.driver.find_element(
                    By.CSS_SELECTOR, "span[data-test-id='job-details-posted-date']"
                )
                job_data['posting_date'] = self._parse_posting_date(date_element.text)
            except NoSuchElementException:
                job_data['posting_date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Construct application link
            job_data['application_link'] = f"https://www.linkedin.com/jobs/view/{job_id}/"
            job_data['source'] = 'LinkedIn'
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Error extracting job data: {e}")
            return None
    
    def _parse_posting_date(self, date_text: str) -> str:
        """Parse posting date text to standard format."""
        try:
            date_text = date_text.lower().strip()
            now = datetime.now()
            
            if 'today' in date_text or 'just now' in date_text:
                return now.strftime('%Y-%m-%d')
            elif 'yesterday' in date_text:
                return (now - timedelta(days=1)).strftime('%Y-%m-%d')
            elif 'day' in date_text:
                # Extract number of days
                days_match = re.search(r'(\d+)\s*day', date_text)
                if days_match:
                    days = int(days_match.group(1))
                    return (now - timedelta(days=days)).strftime('%Y-%m-%d')
            elif 'week' in date_text:
                # Extract number of weeks
                weeks_match = re.search(r'(\d+)\s*week', date_text)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    return (now - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
            
            return now.strftime('%Y-%m-%d')
            
        except Exception:
            return datetime.now().strftime('%Y-%m-%d')
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            logger.info("LinkedIn scraper browser closed")