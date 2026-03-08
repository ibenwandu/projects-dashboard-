#!/usr/bin/env python3
"""Generate test job data for pipeline testing."""
import json
from pathlib import Path
from core.job_model import JobDetails
from core.cache import save_jobs_cache
from core.config import PROFILES_DIR

# Sample test jobs
TEST_JOBS = [
    JobDetails(
        url="https://indeed.com/viewjob?jk=test1",
        platform="indeed",
        job_id="test1",
        title="Senior Python Engineer",
        company="Google",
        location="Mountain View, CA",
        salary="$180k - $220k",
        job_type="Full-time",
        description="Build scalable systems with Python and Go. Experience with Kubernetes required.",
        skills=["Python", "Go", "Kubernetes", "Docker"],
        fetched_at="2026-03-08T10:00:00Z"
    ),
    JobDetails(
        url="https://linkedin.com/jobs/view/test2",
        platform="linkedin",
        job_id="test2",
        title="Full Stack Engineer",
        company="Meta",
        location="Menlo Park, CA",
        salary="$160k - $200k",
        job_type="Full-time",
        description="Join our team to build products used by billions. Work with React, Python, and distributed systems.",
        skills=["Python", "React", "PostgreSQL", "AWS"],
        fetched_at="2026-03-08T10:05:00Z"
    ),
    JobDetails(
        url="https://glassdoor.com/jobs/test3",
        platform="glassdoor",
        job_id="test3",
        title="Data Engineer",
        company="Netflix",
        location="Los Gatos, CA",
        salary="$150k - $190k",
        job_type="Full-time",
        description="Design and implement data pipelines for our streaming platform. Spark, Python, Scala experience required.",
        skills=["Python", "Spark", "Scala", "SQL"],
        fetched_at="2026-03-08T10:10:00Z"
    ),
    JobDetails(
        url="https://indeed.com/viewjob?jk=test4",
        platform="indeed",
        job_id="test4",
        title="DevOps Engineer",
        company="Amazon",
        location="Seattle, WA",
        salary="$140k - $180k",
        job_type="Full-time",
        description="Manage AWS infrastructure, CI/CD pipelines, and Kubernetes clusters for our services.",
        skills=["Kubernetes", "Docker", "AWS", "Python"],
        fetched_at="2026-03-08T10:15:00Z"
    ),
    JobDetails(
        url="https://linkedin.com/jobs/view/test5",
        platform="linkedin",
        job_id="test5",
        title="ML Engineer",
        company="OpenAI",
        location="San Francisco, CA",
        salary="$200k - $250k",
        job_type="Full-time",
        description="Work on cutting-edge AI models. Python, PyTorch, CUDA experience essential.",
        skills=["Python", "PyTorch", "CUDA", "TensorFlow"],
        fetched_at="2026-03-08T10:20:00Z"
    ),
]

def create_test_data(profile: str = "cs"):
    """Create test job data in cache."""
    profile_dir = PROFILES_DIR / profile
    cache_dir = Path("cache") / profile
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / "jobs_cache.json"
    save_jobs_cache(TEST_JOBS, cache_file)

    print(f"[OK] Created {len(TEST_JOBS)} test jobs in {cache_file}")
    print("\nTest jobs:")
    for job in TEST_JOBS:
        print(f"  - {job.title} at {job.company}")

if __name__ == "__main__":
    create_test_data("cs")
