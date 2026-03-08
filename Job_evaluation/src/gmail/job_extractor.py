import re
import logging
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

class JobExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_job_data(self, parsed_email: Dict) -> List[Dict]:
        """Extract job data from parsed email"""
        try:
            jobs = []
            
            # Determine extraction method based on source
            source_type = parsed_email.get('source_type', 'Other')
            
            if source_type == 'LinkedIn':
                jobs = self._extract_linkedin_jobs(parsed_email)
            elif source_type == 'Indeed':
                jobs = self._extract_indeed_jobs(parsed_email)
            elif source_type == 'Glassdoor':
                jobs = self._extract_glassdoor_jobs(parsed_email)
            else:
                jobs = self._extract_generic_jobs(parsed_email)
            
            # Add common metadata to all jobs
            for job in jobs:
                job.update({
                    'email_id': parsed_email.get('email_id'),
                    'source_type': source_type,
                    'sender': parsed_email.get('sender'),
                    'email_date': parsed_email.get('date'),
                    'extraction_method': f'extract_{source_type.lower().replace(" ", "_")}_jobs'
                })
            
            self.logger.info(f"Extracted {len(jobs)} jobs from {source_type} email")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error extracting job data: {str(e)}")
            return []
    
    def _extract_linkedin_jobs(self, email: Dict) -> List[Dict]:
        """Extract jobs from LinkedIn job alert emails"""
        jobs = []
        html_content = email.get('body_html', '')
        
        if not html_content:
            return jobs
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # LinkedIn job alert patterns
            job_containers = soup.find_all(['div', 'td', 'table'], class_=re.compile(r'job|listing|recommendation'))
            
            if not job_containers:
                # Try alternative selectors
                job_containers = soup.find_all('a', href=re.compile(r'linkedin\.com/jobs/view'))
            
            for container in job_containers:
                job = self._extract_linkedin_job_details(container)
                if job and job.get('title'):
                    jobs.append(job)
            
            # If no structured extraction worked, try text-based extraction
            if not jobs:
                jobs = self._extract_jobs_from_text(email.get('body_text', ''), 'LinkedIn')
            
        except Exception as e:
            self.logger.error(f"Error extracting LinkedIn jobs: {str(e)}")
        
        return jobs
    
    def _extract_indeed_jobs(self, email: Dict) -> List[Dict]:
        """Extract jobs from Indeed job alert emails"""
        jobs = []
        html_content = email.get('body_html', '')
        
        if not html_content:
            return jobs
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Indeed job patterns
            job_containers = soup.find_all(['div', 'td'], class_=re.compile(r'job|result|listing'))
            
            for container in job_containers:
                job = self._extract_indeed_job_details(container)
                if job and job.get('title'):
                    jobs.append(job)
            
            if not jobs:
                jobs = self._extract_jobs_from_text(email.get('body_text', ''), 'Indeed')
                
        except Exception as e:
            self.logger.error(f"Error extracting Indeed jobs: {str(e)}")
        
        return jobs
    
    def _extract_glassdoor_jobs(self, email: Dict) -> List[Dict]:
        """Extract jobs from Glassdoor job alert emails"""
        jobs = []
        html_content = email.get('body_html', '')
        
        if not html_content:
            return jobs
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Glassdoor job patterns
            job_containers = soup.find_all(['div', 'td'], class_=re.compile(r'job|listing'))
            
            for container in job_containers:
                job = self._extract_glassdoor_job_details(container)
                if job and job.get('title'):
                    jobs.append(job)
            
            if not jobs:
                jobs = self._extract_jobs_from_text(email.get('body_text', ''), 'Glassdoor')
                
        except Exception as e:
            self.logger.error(f"Error extracting Glassdoor jobs: {str(e)}")
        
        return jobs
    
    def _extract_generic_jobs(self, email: Dict) -> List[Dict]:
        """Extract jobs using generic patterns"""
        return self._extract_jobs_from_text(email.get('body_text', ''), email.get('source_type', 'Other'))
    
    def _extract_linkedin_job_details(self, container) -> Optional[Dict]:
        """Extract job details from LinkedIn container"""
        job = {}
        
        try:
            # Find job title
            title_elem = container.find(['a', 'h1', 'h2', 'h3'], href=re.compile(r'linkedin\.com/jobs/view'))
            if title_elem:
                job['title'] = title_elem.get_text().strip()
                job['url'] = title_elem.get('href', '')
            
            # Find company name
            company_elem = container.find(['a', 'span', 'div'], string=re.compile(r'at\s+|Company:', re.I))
            if company_elem:
                job['company'] = company_elem.get_text().replace('at ', '').replace('Company:', '').strip()
            
            # Find location
            location_elem = container.find(['span', 'div'], string=re.compile(r'[A-Za-z]+,\s*[A-Za-z]{2}'))
            if location_elem:
                job['location'] = location_elem.get_text().strip()
            
            return job if job.get('title') else None
            
        except Exception as e:
            self.logger.debug(f"Error extracting LinkedIn job details: {str(e)}")
            return None
    
    def _extract_indeed_job_details(self, container) -> Optional[Dict]:
        """Extract job details from Indeed container"""
        job = {}
        
        try:
            # Find job title
            title_elem = container.find(['a', 'h1', 'h2', 'h3'], href=re.compile(r'indeed\.com/viewjob'))
            if title_elem:
                job['title'] = title_elem.get_text().strip()
                job['url'] = title_elem.get('href', '')
            
            # Find company name
            company_elem = container.find(['span', 'div'], class_=re.compile(r'company'))
            if company_elem:
                job['company'] = company_elem.get_text().strip()
            
            # Find location
            location_elem = container.find(['span', 'div'], class_=re.compile(r'location'))
            if location_elem:
                job['location'] = location_elem.get_text().strip()
            
            return job if job.get('title') else None
            
        except Exception as e:
            self.logger.debug(f"Error extracting Indeed job details: {str(e)}")
            return None
    
    def _extract_glassdoor_job_details(self, container) -> Optional[Dict]:
        """Extract job details from Glassdoor container"""
        job = {}
        
        try:
            # Find job title
            title_elem = container.find(['a', 'h1', 'h2', 'h3'], href=re.compile(r'glassdoor\.com/job'))
            if title_elem:
                job['title'] = title_elem.get_text().strip()
                job['url'] = title_elem.get('href', '')
            
            # Find company name
            company_elem = container.find(['a', 'span', 'div'], href=re.compile(r'glassdoor\.com/Overview/Working-at'))
            if company_elem:
                job['company'] = company_elem.get_text().strip()
            
            return job if job.get('title') else None
            
        except Exception as e:
            self.logger.debug(f"Error extracting Glassdoor job details: {str(e)}")
            return None
    
    def _extract_jobs_from_text(self, text: str, source: str) -> List[Dict]:
        """Extract job information from plain text using regex patterns"""
        jobs = []
        
        if not text:
            return jobs
        
        try:
            # Common job title patterns
            title_patterns = [
                r'(?:Job Title|Position|Role):\s*([^\n\r]+)',
                r'(?:^|\n)([A-Z][A-Za-z\s]+(?:Analyst|Manager|Developer|Engineer|Specialist|Coordinator|Administrator|Director|Lead|Senior|Junior))',
                r'New job alert:\s*([^\n\r]+)',
                r'We found a job for you:\s*([^\n\r]+)'
            ]
            
            # Company patterns
            company_patterns = [
                r'(?:Company|Employer|Organization):\s*([^\n\r]+)',
                r'at\s+([A-Z][A-Za-z\s&\.]+?)(?:\s*-|\s*\n|\s*,)',
                r'hiring at\s+([A-Z][A-Za-z\s&\.]+)'
            ]
            
            # Location patterns
            location_patterns = [
                r'(?:Location|City):\s*([^\n\r]+)',
                r'([A-Za-z\s]+,\s*[A-Z]{2}(?:\s*\d{5})?)',
                r'([A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2})'
            ]
            
            # URL patterns
            url_patterns = [
                r'(https?://[^\s]+(?:job|career|position)[^\s]*)',
                r'(https?://linkedin\.com/jobs/view/\d+)',
                r'(https?://indeed\.com/viewjob[^\s]*)',
                r'(https?://glassdoor\.com/job[^\s]*)'
            ]
            
            # Find all potential job titles
            titles = []
            for pattern in title_patterns:
                titles.extend(re.findall(pattern, text, re.IGNORECASE | re.MULTILINE))
            
            # Find companies
            companies = []
            for pattern in company_patterns:
                companies.extend(re.findall(pattern, text, re.IGNORECASE))
            
            # Find locations
            locations = []
            for pattern in location_patterns:
                locations.extend(re.findall(pattern, text))
            
            # Find URLs
            urls = []
            for pattern in url_patterns:
                urls.extend(re.findall(pattern, text))
            
            # Combine extracted data into job objects
            max_items = max(len(titles), len(companies), len(locations), len(urls), 1)
            
            for i in range(max_items):
                job = {
                    'title': titles[i] if i < len(titles) else '',
                    'company': companies[i] if i < len(companies) else '',
                    'location': locations[i] if i < len(locations) else '',
                    'url': urls[i] if i < len(urls) else '',
                    'description': text[:500] + '...' if len(text) > 500 else text
                }
                
                # Only add job if it has at least a title
                if job['title'].strip():
                    job['title'] = self._clean_job_title(job['title'])
                    job['company'] = self._clean_company_name(job['company'])
                    jobs.append(job)
            
            # If no structured extraction, create one job with email subject as title
            if not jobs and text:
                jobs.append({
                    'title': 'Job Alert',
                    'company': source,
                    'location': '',
                    'url': '',
                    'description': text[:500] + '...' if len(text) > 500 else text
                })
            
        except Exception as e:
            self.logger.error(f"Error extracting jobs from text: {str(e)}")
        
        return jobs
    
    def _clean_job_title(self, title: str) -> str:
        """Clean and normalize job title"""
        if not title:
            return ''
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(New job alert:?|Job Title:?|Position:?|Role:?)\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*Apply Now.*$', '', title, flags=re.IGNORECASE)
        
        # Clean up whitespace
        title = ' '.join(title.split())
        
        return title.strip()
    
    def _clean_company_name(self, company: str) -> str:
        """Clean and normalize company name"""
        if not company:
            return ''
        
        # Remove common suffixes
        company = re.sub(r'\s*(Inc\.?|LLC\.?|Corp\.?|Ltd\.?|Co\.?)$', '', company, flags=re.IGNORECASE)
        
        # Clean up whitespace
        company = ' '.join(company.split())
        
        return company.strip()
    
    def validate_job_data(self, job: Dict) -> bool:
        """Validate extracted job data"""
        required_fields = ['title']
        
        for field in required_fields:
            if not job.get(field, '').strip():
                return False
        
        # Additional validation rules
        title = job.get('title', '')
        
        # Title should be reasonable length
        if len(title) < 3 or len(title) > 200:
            return False
        
        # Title shouldn't be just numbers or special characters
        if re.match(r'^[0-9\W]+$', title):
            return False
        
        return True