import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from indeed_crawler import IndeedCrawler
from linkedin_crawler import LinkedInCrawler
from skills_matcher import SkillsMatcher
from database import JobDatabase
from config import DEFAULT_SEARCH_CRITERIA, MAX_PAGES_PER_SEARCH

class JobCrawler:
    def __init__(self, db_path: str = "job_database.db"):
        self.indeed_crawler = IndeedCrawler()
        self.linkedin_crawler = LinkedInCrawler()
        self.skills_matcher = SkillsMatcher()
        self.database = JobDatabase(db_path)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('job_crawler.log'),
                logging.StreamHandler()
            ]
        )
    
    def crawl_jobs(self, 
                   search_criteria: Dict = None,
                   sources: List[str] = None,
                   user_skills: List[str] = None) -> Dict:
        """Main method to crawl jobs from multiple sources"""
        
        search_criteria = search_criteria or DEFAULT_SEARCH_CRITERIA
        sources = sources or ['indeed', 'linkedin']
        user_skills = user_skills or []
        
        logging.info("Starting job crawling process...")
        logging.info(f"Search criteria: {search_criteria}")
        logging.info(f"Sources: {sources}")
        
        total_jobs_found = 0
        total_jobs_added = 0
        results = {
            'indeed': {'found': 0, 'added': 0, 'jobs': []},
            'linkedin': {'found': 0, 'added': 0, 'jobs': []}
        }
        
        # Crawl from each source
        for source in sources:
            if source.lower() == 'indeed':
                source_results = self._crawl_indeed(search_criteria, user_skills)
                results['indeed'] = source_results
                total_jobs_found += source_results['found']
                total_jobs_added += source_results['added']
                
            elif source.lower() == 'linkedin':
                source_results = self._crawl_linkedin(search_criteria, user_skills)
                results['linkedin'] = source_results
                total_jobs_found += source_results['found']
                total_jobs_added += source_results['added']
        
        # Log summary
        logging.info(f"Crawling completed. Total jobs found: {total_jobs_found}, Total added: {total_jobs_added}")
        
        return {
            'total_found': total_jobs_found,
            'total_added': total_jobs_added,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _crawl_indeed(self, search_criteria: Dict, user_skills: List[str]) -> Dict:
        """Crawl jobs from Indeed"""
        logging.info("Starting Indeed crawling...")
        
        jobs_found = 0
        jobs_added = 0
        jobs = []
        
        job_titles = search_criteria.get('job_titles', [])
        locations = search_criteria.get('locations', [])
        date_posted = search_criteria.get('date_posted', '7d')
        
        for job_title in job_titles:
            for location in locations:
                try:
                    logging.info(f"Searching Indeed for '{job_title}' in '{location}'")
                    
                    # Search for jobs
                    found_jobs = self.indeed_crawler.search_jobs(
                        job_title=job_title,
                        location=location,
                        date_posted=date_posted,
                        max_pages=MAX_PAGES_PER_SEARCH
                    )
                    
                    jobs_found += len(found_jobs)
                    
                    # Process each job
                    for job in found_jobs:
                        processed_job = self._process_job(job, user_skills)
                        if processed_job:
                            jobs.append(processed_job)
                            if self.database.add_job(processed_job):
                                jobs_added += 1
                    
                    # Add delay between searches
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"Error crawling Indeed for '{job_title}' in '{location}': {e}")
        
        logging.info(f"Indeed crawling completed. Found: {jobs_found}, Added: {jobs_added}")
        
        return {
            'found': jobs_found,
            'added': jobs_added,
            'jobs': jobs
        }
    
    def _crawl_linkedin(self, search_criteria: Dict, user_skills: List[str]) -> Dict:
        """Crawl jobs from LinkedIn"""
        logging.info("Starting LinkedIn crawling...")
        
        jobs_found = 0
        jobs_added = 0
        jobs = []
        
        job_titles = search_criteria.get('job_titles', [])
        locations = search_criteria.get('locations', [])
        date_posted = search_criteria.get('date_posted', '7d')
        
        for job_title in job_titles:
            for location in locations:
                try:
                    logging.info(f"Searching LinkedIn for '{job_title}' in '{location}'")
                    
                    # Search for jobs
                    found_jobs = self.linkedin_crawler.search_jobs(
                        job_title=job_title,
                        location=location,
                        date_posted=date_posted,
                        max_pages=MAX_PAGES_PER_SEARCH
                    )
                    
                    jobs_found += len(found_jobs)
                    
                    # Process each job
                    for job in found_jobs:
                        processed_job = self._process_job(job, user_skills)
                        if processed_job:
                            jobs.append(processed_job)
                            if self.database.add_job(processed_job):
                                jobs_added += 1
                    
                    # Add delay between searches
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"Error crawling LinkedIn for '{job_title}' in '{location}': {e}")
        
        logging.info(f"LinkedIn crawling completed. Found: {jobs_found}, Added: {jobs_added}")
        
        return {
            'found': jobs_found,
            'added': jobs_added,
            'jobs': jobs
        }
    
    def _process_job(self, job: Dict, user_skills: List[str]) -> Optional[Dict]:
        """Process a job by analyzing skills and calculating match score"""
        try:
            # Analyze job description
            job_description = job.get('job_description', '')
            analysis = self.skills_matcher.analyze_job_description(job_description, user_skills)
            
            # Update job with analysis results
            job.update({
                'skills_required': analysis['skills_required'],
                'skills_matched': analysis['skills_matched'],
                'match_score': analysis['match_score'],
                'experience_level': analysis['experience_level']
            })
            
            return job
            
        except Exception as e:
            logging.error(f"Error processing job {job.get('job_id', 'unknown')}: {e}")
            return None
    
    def get_matching_jobs(self, 
                         min_match_score: float = 0.5,
                         filters: Dict = None,
                         limit: int = 50) -> List[Dict]:
        """Get jobs that match user skills above a threshold"""
        return self.database.get_jobs_by_match_score(min_match_score, limit)
    
    def search_jobs_by_criteria(self, 
                               job_title: str = None,
                               location: str = None,
                               company: str = None,
                               experience_level: str = None,
                               limit: int = 100) -> List[Dict]:
        """Search jobs by specific criteria"""
        filters = {}
        
        if job_title:
            filters['title'] = job_title
        if location:
            filters['location'] = location
        if company:
            filters['company'] = company
        if experience_level:
            filters['experience_level'] = experience_level
        
        return self.database.get_jobs(filters, limit)
    
    def get_job_statistics(self) -> Dict:
        """Get statistics about the job database"""
        return self.database.get_statistics()
    
    def export_jobs(self, filename: str = None) -> bool:
        """Export jobs to CSV file"""
        if not filename:
            filename = f"jobs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return self.database.export_to_csv(filename)
    
    def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Remove old jobs from database"""
        return self.database.delete_old_jobs(days_old)
    
    def update_user_skills(self, new_skills: List[str], category: str = None):
        """Update the skills database with new user skills"""
        self.skills_matcher.update_user_skills(new_skills, category)
    
    def get_skills_suggestions(self, job_id: str) -> Dict:
        """Get skill improvement suggestions for a specific job"""
        job = self.database.get_jobs({'job_id': job_id}, limit=1)
        if job:
            job_data = job[0]
            analysis = {
                'skills_required': job_data.get('skills_required', []),
                'skills_matched': job_data.get('skills_matched', []),
                'match_score': job_data.get('match_score', 0.0)
            }
            return self.skills_matcher.suggest_skill_improvements(analysis)
        return {}
























