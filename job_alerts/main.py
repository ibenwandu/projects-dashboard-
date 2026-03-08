#!/usr/bin/env python3
"""
Job Alerts Application
A comprehensive job crawling and matching system for Indeed and LinkedIn
"""

import argparse
import logging
import sys
from datetime import datetime
from job_crawler import JobCrawler
from config import DEFAULT_SEARCH_CRITERIA, SKILLS_DATABASE

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('job_alerts.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("           JOB ALERTS APPLICATION")
    print("     Indeed & LinkedIn Job Crawler & Matcher")
    print("=" * 60)
    print()

def crawl_jobs_command(args):
    """Execute job crawling command"""
    print("🚀 Starting job crawling process...")
    
    crawler = JobCrawler()
    
    # Define search criteria
    search_criteria = {
        'job_titles': args.job_titles or DEFAULT_SEARCH_CRITERIA['job_titles'],
        'locations': args.locations or DEFAULT_SEARCH_CRITERIA['locations'],
        'date_posted': args.date_posted or DEFAULT_SEARCH_CRITERIA['date_posted']
    }
    
    # Define user skills
    user_skills = args.user_skills or []
    
    # Execute crawling
    results = crawler.crawl_jobs(
        search_criteria=search_criteria,
        sources=args.sources,
        user_skills=user_skills
    )
    
    # Print results
    print("\n📊 Crawling Results:")
    print(f"Total jobs found: {results['total_found']}")
    print(f"Total jobs added: {results['total_added']}")
    print(f"Timestamp: {results['timestamp']}")
    
    for source, data in results['results'].items():
        print(f"\n{source.upper()}:")
        print(f"  Jobs found: {data['found']}")
        print(f"  Jobs added: {data['added']}")
    
    return results

def search_jobs_command(args):
    """Execute job search command"""
    print("🔍 Searching for jobs...")
    
    crawler = JobCrawler()
    
    if args.matching:
        # Get matching jobs
        jobs = crawler.get_matching_jobs(
            min_match_score=args.min_score,
            limit=args.limit
        )
        print(f"Found {len(jobs)} jobs matching your skills (score >= {args.min_score})")
    else:
        # Search by criteria
        jobs = crawler.search_jobs_by_criteria(
            job_title=args.job_title,
            location=args.location,
            company=args.company,
            experience_level=args.experience_level,
            limit=args.limit
        )
        print(f"Found {len(jobs)} jobs matching your criteria")
    
    # Display jobs
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job['title']} at {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Posted: {job['date_posted']}")
        print(f"   Source: {job['source']}")
        if job.get('match_score'):
            print(f"   Match Score: {job['match_score']:.2f}")
        if job.get('skills_required'):
            print(f"   Skills: {', '.join(job['skills_required'][:5])}")
        print(f"   URL: {job['url']}")
    
    return jobs

def statistics_command(args):
    """Execute statistics command"""
    print("📈 Getting job statistics...")
    
    crawler = JobCrawler()
    stats = crawler.get_job_statistics()
    
    print("\n📊 Database Statistics:")
    print(f"Total jobs: {stats.get('total_jobs', 0)}")
    print(f"Recent jobs (7 days): {stats.get('recent_jobs', 0)}")
    print(f"Average match score: {stats.get('avg_match_score', 0)}")
    
    if stats.get('jobs_by_source'):
        print("\nJobs by source:")
        for source, count in stats['jobs_by_source'].items():
            print(f"  {source}: {count}")
    
    return stats

def export_command(args):
    """Execute export command"""
    print("📤 Exporting jobs to CSV...")
    
    crawler = JobCrawler()
    filename = args.filename or f"jobs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    success = crawler.export_jobs(filename)
    
    if success:
        print(f"✅ Jobs exported successfully to {filename}")
    else:
        print("❌ Failed to export jobs")
    
    return success

def cleanup_command(args):
    """Execute cleanup command"""
    print("🧹 Cleaning up old jobs...")
    
    crawler = JobCrawler()
    deleted_count = crawler.cleanup_old_jobs(args.days)
    
    print(f"✅ Deleted {deleted_count} old jobs (older than {args.days} days)")
    
    return deleted_count

def main():
    """Main function"""
    setup_logging()
    print_banner()
    
    parser = argparse.ArgumentParser(description='Job Alerts Application')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Crawl jobs from Indeed and LinkedIn')
    crawl_parser.add_argument('--job-titles', nargs='+', help='Job titles to search for')
    crawl_parser.add_argument('--locations', nargs='+', help='Locations to search in')
    crawl_parser.add_argument('--date-posted', default='7d', help='Date filter (e.g., 7d, 30d)')
    crawl_parser.add_argument('--sources', nargs='+', default=['indeed', 'linkedin'], 
                             choices=['indeed', 'linkedin'], help='Sources to crawl')
    crawl_parser.add_argument('--user-skills', nargs='+', help='User skills for matching')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search jobs in database')
    search_parser.add_argument('--matching', action='store_true', help='Search by skill matching')
    search_parser.add_argument('--min-score', type=float, default=0.5, help='Minimum match score')
    search_parser.add_argument('--job-title', help='Job title filter')
    search_parser.add_argument('--location', help='Location filter')
    search_parser.add_argument('--company', help='Company filter')
    search_parser.add_argument('--experience-level', help='Experience level filter')
    search_parser.add_argument('--limit', type=int, default=50, help='Maximum number of results')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export jobs to CSV')
    export_parser.add_argument('--filename', help='Output filename')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old jobs')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete jobs older than N days')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'crawl':
            crawl_jobs_command(args)
        elif args.command == 'search':
            search_jobs_command(args)
        elif args.command == 'stats':
            statistics_command(args)
        elif args.command == 'export':
            export_command(args)
        elif args.command == 'cleanup':
            cleanup_command(args)
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
    except Exception as e:
        logging.error(f"Error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
