#!/usr/bin/env python3
"""Generate mock scored jobs for testing without API keys."""
import json
from pathlib import Path
from core.ai_scorer import ScoredJob
from core.cache import load_jobs_cache
from core.config import PROFILES_DIR

def create_mock_scores(profile: str = "cs"):
    """Create mock scored jobs for testing."""
    cache_dir = Path("cache") / profile
    cache_file = cache_dir / "jobs_cache.json"

    # Load test jobs
    jobs = load_jobs_cache(cache_file)

    if not jobs:
        print("[FAIL] No jobs found in cache. Run test_data.py first.")
        return

    # Create mock scores
    mock_scores = [
        (jobs[0], 95, "Excellent match - all required skills, great salary, remote-friendly location"),
        (jobs[1], 87, "Strong match - good salary, relevant tech stack, well-known company"),
        (jobs[2], 78, "Good match - competitive salary, but less familiar with Spark ecosystem"),
        (jobs[3], 85, "Strong match - DevOps skills align well, good salary range"),
        (jobs[4], 92, "Excellent match - cutting-edge role, highest salary, perfect skill alignment"),
    ]

    # Save mock scored data
    scored_path = cache_dir / "scored_jobs.json"
    scored_data = [
        {
            "job": job.to_dict(),
            "score": score,
            "reasoning": reasoning,
        }
        for job, score, reasoning in mock_scores
    ]

    scored_path.write_text(json.dumps(scored_data, indent=2), encoding="utf-8")
    print(f"[OK] Created mock scored jobs in {scored_path}")
    print("\nMock scores:")
    for job, score, reasoning in mock_scores:
        print(f"  {score}/100 - {job.title} at {job.company}")
        print(f"           {reasoning}\n")

if __name__ == "__main__":
    create_mock_scores("cs")
