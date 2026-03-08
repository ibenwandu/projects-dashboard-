#!/usr/bin/env python3
"""
Example usage of the Job Alerts Application
This script demonstrates how to use the application programmatically
"""

from job_crawler import JobCrawler
from config import DEFAULT_SEARCH_CRITERIA
import logging

def main():
    """Example usage of the Job Alerts application"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the job crawler
    crawler = JobCrawler()
    
    # Example 1: Crawl jobs with default criteria
    print("=== Example 1: Crawling jobs with default criteria ===")
    results = crawler.crawl_jobs()
    print(f"Found {results['total_found']} jobs, added {results['total_added']} to database")
    
    # Example 2: Search for jobs matching your skills
    print("\n=== Example 2: Finding jobs that match your skills ===")
    user_skills = ["Python", "JavaScript", "React", "Node.js", "AWS", "Docker"]
    matching_jobs = crawler.get_matching_jobs(min_match_score=0.6, limit=10)
    
    print(f"Found {len(matching_jobs)} jobs matching your skills:")
    for i, job in enumerate(matching_jobs[:5], 1):
        print(f"{i}. {job['title']} at {job['company']}")
        print(f"   Match Score: {job['match_score']:.2f}")
        print(f"   Skills Required: {', '.join(job['skills_required'][:3])}")
        print()
    
    # Example 3: Search by specific criteria
    print("=== Example 3: Searching for Python developer jobs in Toronto ===")
    python_jobs = crawler.search_jobs_by_criteria(
        job_title="Python",
        location="Toronto",
        limit=5
    )
    
    print(f"Found {len(python_jobs)} Python jobs in Toronto:")
    for i, job in enumerate(python_jobs, 1):
        print(f"{i}. {job['title']} at {job['company']}")
        print(f"   Posted: {job['date_posted']}")
        print(f"   Source: {job['source']}")
        print()
    
    # Example 4: Get database statistics
    print("=== Example 4: Database Statistics ===")
    stats = crawler.get_job_statistics()
    print(f"Total jobs in database: {stats.get('total_jobs', 0)}")
    print(f"Recent jobs (7 days): {stats.get('recent_jobs', 0)}")
    print(f"Average match score: {stats.get('avg_match_score', 0)}")
    
    if stats.get('jobs_by_source'):
        print("Jobs by source:")
        for source, count in stats['jobs_by_source'].items():
            print(f"  {source}: {count}")
    
    # Example 5: Export jobs to CSV
    print("\n=== Example 5: Exporting jobs to CSV ===")
    success = crawler.export_jobs("example_export.csv")
    if success:
        print("✅ Jobs exported successfully to example_export.csv")
    else:
        print("❌ Failed to export jobs")
    
    # Example 6: Custom search criteria
    print("\n=== Example 6: Custom search criteria ===")
    custom_criteria = {
        'job_titles': ['Software Engineer', 'Full Stack Developer'],
        'locations': ['Remote', 'Toronto, ON'],
        'date_posted': '3d'  # Last 3 days
    }
    
    custom_results = crawler.crawl_jobs(
        search_criteria=custom_criteria,
        sources=['indeed'],  # Only search Indeed
        user_skills=user_skills
    )
    
    print(f"Custom search found {custom_results['total_found']} jobs")
    
    # Example 7: Get skill improvement suggestions
    print("\n=== Example 7: Skill improvement suggestions ===")
    if matching_jobs:
        job_id = matching_jobs[0]['job_id']
        suggestions = crawler.get_skills_suggestions(job_id)
        
        if suggestions.get('priority_skills'):
            print("Priority skills to learn:")
            for skill in suggestions['priority_skills'][:5]:
                print(f"  - {skill}")
        
        print(f"Potential match improvement: {suggestions.get('match_improvement', 0):.2f}")
    
    print("\n=== Example completed successfully! ===")

if __name__ == "__main__":
    main()
























