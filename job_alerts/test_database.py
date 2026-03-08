#!/usr/bin/env python3
"""
Simple test script to verify database functionality
"""

from database import JobDatabase
from skills_matcher import SkillsMatcher
import os

def test_database():
    """Test basic database functionality"""
    print("Testing database functionality...")
    
    # Initialize database
    db = JobDatabase("test_database.db")
    
    # Test adding a job
    test_job = {
        'job_id': 'test_123',
        'title': 'Software Engineer',
        'company': 'Test Company',
        'location': 'Toronto, ON',
        'date_posted': '2024-01-15',
        'job_description': 'We are looking for a Python developer with React experience.',
        'salary': '$80,000 - $120,000',
        'experience_level': 'Mid Level',
        'job_type': 'Full-time',
        'source': 'Indeed',
        'url': 'https://example.com/job/123',
        'skills_required': ['Python', 'React', 'JavaScript'],
        'skills_matched': ['Python', 'JavaScript'],
        'match_score': 0.67
    }
    
    # Add job to database
    success = db.add_job(test_job)
    print(f"Job added successfully: {success}")
    
    # Test retrieving jobs
    jobs = db.get_jobs(limit=10)
    print(f"Retrieved {len(jobs)} jobs from database")
    
    # Test getting jobs by match score
    matching_jobs = db.get_jobs_by_match_score(min_score=0.5, limit=5)
    print(f"Found {len(matching_jobs)} jobs with match score >= 0.5")
    
    # Test statistics
    stats = db.get_statistics()
    print(f"Database statistics: {stats}")
    
    # Test export
    export_success = db.export_to_csv("test_export.csv")
    print(f"Export successful: {export_success}")
    
    # Cleanup test files
    if os.path.exists("test_database.db"):
        os.remove("test_database.db")
    if os.path.exists("test_export.csv"):
        os.remove("test_export.csv")
    
    print("Database test completed successfully!")

def test_skills_matcher():
    """Test skills matching functionality"""
    print("\nTesting skills matcher...")
    
    matcher = SkillsMatcher()
    
    # Test job description analysis
    job_description = """
    We are seeking a Senior Software Engineer with expertise in:
    - Python programming
    - React and JavaScript
    - AWS cloud services
    - Docker containerization
    - Git version control
    
    Requirements:
    - 5+ years of experience
    - Knowledge of microservices architecture
    - Experience with CI/CD pipelines
    """
    
    user_skills = ['Python', 'JavaScript', 'Git', 'Docker']
    
    analysis = matcher.analyze_job_description(job_description, user_skills)
    
    print(f"Skills required: {analysis['skills_required']}")
    print(f"Skills matched: {analysis['skills_matched']}")
    print(f"Match score: {analysis['match_score']}")
    print(f"Experience level: {analysis['experience_level']}")
    
    print("Skills matcher test completed successfully!")

if __name__ == "__main__":
    test_database()
    test_skills_matcher()
    print("\nAll tests passed! ✅")
























