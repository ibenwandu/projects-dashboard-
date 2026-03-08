"""
Demo script to show how the job matching system works with mock job data.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load .env at the very top
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.job_matching_agent import JobMatchingAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Mock job data for demonstration
MOCK_JOBS = [
    {
        'title': 'Senior Business Analyst',
        'company': 'Tech Solutions Inc.',
        'location': 'Toronto, ON',
        'description': '''We are seeking a Senior Business Analyst to join our growing team. The ideal candidate will have experience in process analysis, requirements gathering, and stakeholder management. Key responsibilities include:
        
        • Analyze business processes and identify improvement opportunities
        • Gather and document business requirements from stakeholders
        • Work with development teams to ensure requirements are properly implemented
        • Create process documentation and user stories
        • Facilitate meetings with cross-functional teams
        • Support project management activities
        
        Required Skills:
        • Bachelor's degree in Business Administration or related field
        • 3+ years of business analysis experience
        • Strong analytical and problem-solving skills
        • Experience with process mapping and documentation
        • Excellent communication and presentation skills
        • Knowledge of Agile/Scrum methodologies
        • Experience with SQL and data analysis tools
        
        Preferred Skills:
        • Project management experience
        • Knowledge of banking or financial services
        • Experience with Tableau or Power BI
        • Certification in business analysis (CBAP, PMI-PBA)''',
        'application_link': 'https://example.com/job1',
        'posting_date': '2025-01-26',
        'source': 'Mock Data'
    },
    {
        'title': 'Data Analyst - Marketing',
        'company': 'Marketing Innovations Ltd.',
        'location': 'Remote',
        'description': '''Join our dynamic marketing team as a Data Analyst! You'll be responsible for analyzing marketing campaigns, customer behavior, and business performance metrics.
        
        Key Responsibilities:
        • Analyze marketing campaign performance and ROI
        • Create dashboards and reports for stakeholders
        • Perform customer segmentation and behavior analysis
        • Support A/B testing and experimentation
        • Collaborate with marketing teams on data-driven strategies
        • Maintain data quality and integrity
        
        Requirements:
        • Bachelor's degree in Statistics, Mathematics, or related field
        • 2+ years of data analysis experience
        • Proficiency in SQL, Python, or R
        • Experience with visualization tools (Tableau, Power BI, or similar)
        • Strong understanding of statistical concepts
        • Experience with Google Analytics and marketing tools
        • Excellent communication skills
        
        Nice to Have:
        • Experience with machine learning algorithms
        • Knowledge of digital marketing channels
        • Experience with cloud platforms (AWS, Azure, GCP)''',
        'application_link': 'https://example.com/job2',
        'posting_date': '2025-01-25',
        'source': 'Mock Data'
    },
    {
        'title': 'Junior Software Developer',
        'company': 'Startup Hub',
        'location': 'Toronto, ON',
        'description': '''We're looking for a passionate Junior Software Developer to join our innovative startup. This is an entry-level position perfect for recent graduates or career changers.
        
        What you'll do:
        • Develop web applications using modern JavaScript frameworks
        • Write clean, maintainable code following best practices
        • Participate in code reviews and team meetings
        • Learn from senior developers and contribute to team projects
        • Help with testing and debugging applications
        
        Requirements:
        • Computer Science degree or equivalent experience
        • Basic knowledge of JavaScript, HTML, CSS
        • Familiarity with version control (Git)
        • Problem-solving mindset
        • Eagerness to learn new technologies
        
        Bonus Points:
        • Experience with React, Node.js, or similar frameworks
        • Understanding of databases and SQL
        • Previous internship or project experience''',
        'application_link': 'https://example.com/job3',
        'posting_date': '2025-01-24',
        'source': 'Mock Data'
    }
]

class DemoJobMatchingAgent(JobMatchingAgent):
    """Demo job matching agent that uses mock data."""
    def _load_config(self) -> dict:
        config = super()._load_config()
        min_match_score = int(os.getenv('MIN_MATCH_SCORE', '50'))
        logging.info(f"[DEMO] Loaded min_match_score: {min_match_score}")
        config['min_match_score'] = min_match_score
        return config
    
    def run_demo_evaluation(self):
        """Demo version that evaluates mock jobs."""
        logger = logging.getLogger(__name__)
        logger.info("Starting demo job evaluation with mock data")
        
        try:
            # Step 1: Load user profile
            logger.info("Loading user profile...")
            profile = self.profile_manager.load_profile()
            profile_summary = self.profile_manager.get_profile_summary()
            logger.info(f"Profile loaded: {len(profile.get('skills', []))} skills found")
            
            # Show profile summary (first 300 chars)
            logger.info("Profile Summary Preview:")
            logger.info(profile_summary[:300] + "...")
            logger.info("")
            
            # Step 2: Evaluate mock jobs
            logger.info(f"Evaluating {len(MOCK_JOBS)} mock jobs...")
            evaluated_jobs = []
            
            for i, job in enumerate(MOCK_JOBS):
                try:
                    logger.info(f"\nEvaluating job {i+1}/{len(MOCK_JOBS)}: {job['title']} at {job['company']}")
                    score, reasoning = self.job_evaluator.evaluate_job_fit(job, profile_summary)
                    
                    job_with_score = job.copy()
                    job_with_score.update({
                        'score': score,
                        'match_reasoning': reasoning
                    })
                    evaluated_jobs.append(job_with_score)
                    
                    logger.info(f"Score: {score}/100")
                    logger.info(f"Reasoning: {reasoning}")
                    
                except Exception as e:
                    logger.error(f"Error evaluating job: {e}")
                    continue
            
            # Step 3: Show results
            logger.info("\n" + "="*60)
            logger.info("FINAL EVALUATION RESULTS")
            logger.info("="*60)
            
            # Sort by score
            evaluated_jobs.sort(key=lambda x: x['score'], reverse=True)
            
            for i, job in enumerate(evaluated_jobs, 1):
                logger.info(f"\n{i}. {job['title']} at {job['company']}")
                logger.info(f"   Location: {job['location']}")
                logger.info(f"   Score: {job['score']}/100")
                logger.info(f"   Match Reasoning: {job['match_reasoning']}")
                
                # Show if it would be added to spreadsheet
                if job['score'] >= self.config['min_match_score']:
                    logger.info(f"   ✅ HIGH MATCH - Would be added to Google Sheets")
                else:
                    logger.info(f"   ❌ Below threshold ({self.config['min_match_score']})")
            
            # Step 4: Demonstrate adding high-scoring jobs to sheets (if any)
            high_scoring_jobs = [job for job in evaluated_jobs if job['score'] >= self.config['min_match_score']]
            
            if high_scoring_jobs:
                logger.info(f"\n📊 Found {len(high_scoring_jobs)} high-scoring jobs that would be added to Google Sheets")
                
                # Uncomment the line below to actually add jobs to your sheet
                # self.sheets_manager.add_job_data(high_scoring_jobs)
                # logger.info("✅ Jobs added to Google Sheets!")
                
                logger.info("(Uncomment the sheet update code in demo_with_mock_data.py to actually add jobs)")
            else:
                logger.info(f"\n📊 No jobs scored above the threshold of {self.config['min_match_score']}")
            
            logger.info("\n🎉 Demo completed successfully!")
            
        except Exception as e:
            logger.error(f"Error in demo: {e}")
            raise

def main():
    load_dotenv()
    
    try:
        agent = DemoJobMatchingAgent()
        agent.run_demo_evaluation()
    except Exception as e:
        logging.error(f"Demo failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()