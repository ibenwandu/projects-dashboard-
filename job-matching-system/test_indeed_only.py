"""
Test script to run job matching with Indeed scraper only (skip LinkedIn to avoid Chrome issues).
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.job_matching_agent import JobMatchingAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class TestJobMatchingAgent(JobMatchingAgent):
    """Modified job matching agent that skips LinkedIn scraping."""
    
    def run_daily_job_search(self):
        """Modified version that skips LinkedIn."""
        logger = logging.getLogger(__name__)
        logger.info("Starting test job search process (Indeed only)")
        
        try:
            # Step 1: Load user profile
            logger.info("Loading user profile...")
            profile = self.profile_manager.load_profile()
            profile_summary = self.profile_manager.get_profile_summary()
            logger.info(f"Profile loaded: {len(profile.get('skills', []))} skills found")
            
            # Step 2: Define search terms
            search_terms = ["Business Analyst", "Data Analyst"]  # Reduced for testing
            
            # Step 3: Scrape jobs from Indeed only
            logger.info("Scraping jobs from Indeed only...")
            all_jobs = []
            
            try:
                indeed_scraper = self.scrapers['indeed']
                jobs = indeed_scraper.search_jobs(
                    search_terms=search_terms,
                    locations=['Toronto,ON', 'Remote'],  # Reduced locations
                    days_back=7
                )
                all_jobs.extend(jobs)
                indeed_scraper.close()
            except Exception as e:
                logger.error(f"Error scraping from Indeed: {e}")
            
            logger.info(f"Total jobs scraped: {len(all_jobs)}")
            
            # Step 4: Filter new jobs (first 5 for testing)
            test_jobs = all_jobs[:5]
            logger.info(f"Testing with first {len(test_jobs)} jobs")
            
            # Step 5: Evaluate jobs using AI
            logger.info("Evaluating job fit with AI...")
            evaluated_jobs = []
            
            for i, job in enumerate(test_jobs):
                try:
                    logger.info(f"Evaluating job {i+1}/{len(test_jobs)}: {job.get('title', 'Unknown')}")
                    score, reasoning = self.job_evaluator.evaluate_job_fit(job, profile_summary)
                    
                    job_with_score = job.copy()
                    job_with_score.update({
                        'score': score,
                        'match_reasoning': reasoning
                    })
                    evaluated_jobs.append(job_with_score)
                    
                    logger.info(f"Score: {score}/100 - {job['title']} at {job['company']}")
                    
                except Exception as e:
                    logger.error(f"Error evaluating job: {e}")
                    continue
            
            logger.info(f"Evaluation complete. {len(evaluated_jobs)} jobs evaluated")
            
            # Show results
            logger.info("=== EVALUATION RESULTS ===")
            for job in evaluated_jobs:
                logger.info(f"• {job['title']} at {job['company']}")
                logger.info(f"  Score: {job['score']}/100")
                logger.info(f"  Reasoning: {job['match_reasoning'][:100]}...")
                logger.info("")
            
        except Exception as e:
            logger.error(f"Error in test job search: {e}")
            raise

def main():
    load_dotenv()
    
    try:
        agent = TestJobMatchingAgent()
        agent.run_daily_job_search()
    except Exception as e:
        logging.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()