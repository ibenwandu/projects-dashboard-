#!/usr/bin/env python3
"""Main CLI entry point for job search monorepo."""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from core.cache import load_jobs_cache, save_jobs_cache
from core.config import load_search_config
from core.dedup_engine import deduplicate_jobs, get_all_platform_urls
from core.job_model import JobDetails
from core.profile_loader import load_master_resume, get_candidate_summary
from core.ai_scorer import score_jobs
from core.report_generator import generate_report_markdown, save_report
from core.resume_tailor import write_tailored_resume
from platforms.linkedin.scraper import LinkedInScraper
from platforms.glassdoor.scraper import GlassdoorScraper
from platforms.indeed.scraper import IndeedScraper


class JobSearchCLI:
    """Main CLI handler for job search operations."""

    def __init__(self, profile: str = "cs"):
        self.profile = profile
        self.base_dir = Path("job-search-monorepo")
        self.profile_dir = self.base_dir / "profiles" / profile
        self.cache_dir = self.base_dir / "cache" / profile
        self.reports_dir = self.base_dir / "reports" / profile
        self.tailored_dir = self.base_dir / "tailored_resumes" / profile

    def fetch_jobs(self, platforms: list[str], max_jobs: int = 50, **kwargs):
        """Fetch jobs from specified platforms."""
        jobs = []

        for platform in platforms:
            print(f"\nFetching from {platform}...")

            if platform == "linkedin":
                scraper = LinkedInScraper()
                config = load_search_config(self.profile_dir / "linkedin_search.json")
            elif platform == "glassdoor":
                scraper = GlassdoorScraper()
                config = load_search_config(self.profile_dir / "glassdoor_search.json")
            elif platform == "indeed":
                scraper = IndeedScraper()
                config = load_search_config(self.profile_dir / "indeed_search.json")
            else:
                print(f"Unknown platform: {platform}")
                continue

            try:
                keywords = config.get("keywords", [])
                locations = config.get("locations", [])

                # Search (MVP stub returns empty list)
                urls = scraper.search(keywords, locations, max_results=max_jobs)

                if urls:
                    print(f"  Found {len(urls)} URLs, scraping...")
                    scraped = scraper.scrape_jobs(urls[:max_jobs])
                    jobs.extend(scraped)
                    print(f"  Scraped {len(scraped)} jobs")
                else:
                    print(f"  No URLs found (MVP search stub)")
            except Exception as e:
                print(f"  Error fetching from {platform}: {e}")

        # Deduplicate
        unique_jobs = deduplicate_jobs(jobs)
        print(f"\nTotal unique jobs: {len(unique_jobs)}")

        # Save to cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        save_jobs_cache(unique_jobs, self.cache_dir)

        return unique_jobs

    def score_jobs(self, force: bool = False) -> list:
        """Score jobs using AI scorer."""
        print(f"\nLoading jobs from cache...")
        jobs = load_jobs_cache(self.cache_dir)
        print(f"Loaded {len(jobs)} jobs")

        if not jobs:
            print("No jobs to score")
            return []

        try:
            candidate_summary = get_candidate_summary(self.profile)
            print(f"\nScoring {len(jobs)} jobs...")
            scored_jobs = score_jobs(jobs, candidate_summary)

            # Save scored jobs
            scored_path = self.cache_dir / "scored_jobs.json"
            scored_data = [
                {
                    "job": job.__dict__,
                    "score": scored.score,
                    "reasoning": scored.reasoning,
                }
                for job, scored in zip(jobs, scored_jobs)
            ]
            scored_path.write_text(json.dumps(scored_data, indent=2), encoding="utf-8")
            print(f"Saved {len(scored_jobs)} scored jobs")

            return scored_jobs
        except Exception as e:
            print(f"Error scoring jobs: {e}")
            return []

    def generate_report(self, top_n: int = 10):
        """Generate report from scored jobs."""
        print(f"\nGenerating report...")

        scored_path = self.cache_dir / "scored_jobs.json"
        if not scored_path.exists():
            print("No scored jobs found. Run 'score' phase first.")
            return None

        try:
            from core.ai_scorer import ScoredJob

            scored_data = json.loads(scored_path.read_text(encoding="utf-8"))
            scored_jobs = [
                ScoredJob(
                    job=JobDetails(**item["job"]),
                    score=item["score"],
                    reasoning=item["reasoning"],
                )
                for item in scored_data
            ]

            report_path = save_report(scored_jobs, self.reports_dir, top_n=top_n)
            print(f"Report saved to: {report_path}")

            return report_path
        except Exception as e:
            print(f"Error generating report: {e}")
            return None

    def tailor_resumes(self, top_n: int = 5):
        """Generate tailored resumes for top jobs."""
        print(f"\nTailoring resumes for top {top_n} jobs...")

        scored_path = self.cache_dir / "scored_jobs.json"
        if not scored_path.exists():
            print("No scored jobs found. Run 'score' phase first.")
            return

        try:
            from core.ai_scorer import ScoredJob

            master_resume = load_master_resume(self.profile)
            scored_data = json.loads(scored_path.read_text(encoding="utf-8"))

            scored_jobs = [
                ScoredJob(
                    job=JobDetails(**item["job"]),
                    score=item["score"],
                    reasoning=item["reasoning"],
                )
                for item in scored_data
            ]

            ranked = sorted(scored_jobs, key=lambda x: x.score, reverse=True)

            self.tailored_dir.mkdir(parents=True, exist_ok=True)

            for i, scored in enumerate(ranked[:top_n], 1):
                job = scored.job
                output_path = self.tailored_dir / f"{i}_{job.company}_{job.job_id}.md"

                try:
                    write_tailored_resume(job, master_resume, output_path)
                    print(f"  {i}. Tailored: {output_path.name}")
                except Exception as e:
                    print(f"  {i}. Error tailoring resume: {e}")
        except Exception as e:
            print(f"Error tailoring resumes: {e}")

    def validate_imports(self):
        """Validate all module imports."""
        print("Validating imports...")
        try:
            from core.job_model import JobDetails
            from core.config import load_search_config
            from core.cache import load_jobs_cache
            from core.dedup_engine import deduplicate_jobs
            from core.ai_client import generate
            from core.ai_scorer import score_jobs
            from core.report_generator import generate_report_markdown
            from core.resume_tailor import tailor_resume
            from platforms.linkedin.scraper import LinkedInScraper
            from platforms.glassdoor.scraper import GlassdoorScraper
            from platforms.indeed.scraper import IndeedScraper
            print("[OK] All imports successful")
            return True
        except Exception as e:
            print(f"[FAIL] Import error: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Job Search Monorepo - Multi-platform job search and scoring"
    )

    parser.add_argument(
        "phase",
        choices=["validate", "fetch", "score", "report", "tailor", "full"],
        help="Execution phase"
    )

    parser.add_argument(
        "--profile",
        default="cs",
        choices=["cs", "analyst"],
        help="Candidate profile to use"
    )

    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["linkedin"],
        choices=["linkedin", "glassdoor", "indeed"],
        help="Platforms to fetch from"
    )

    parser.add_argument(
        "--max-jobs",
        type=int,
        default=50,
        help="Maximum jobs to fetch per platform"
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top jobs to report/tailor"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation"
    )

    args = parser.parse_args()

    cli = JobSearchCLI(profile=args.profile)

    try:
        if args.phase == "validate":
            success = cli.validate_imports()
            sys.exit(0 if success else 1)

        elif args.phase == "fetch":
            cli.fetch_jobs(args.platforms, max_jobs=args.max_jobs)

        elif args.phase == "score":
            cli.score_jobs(force=args.force)

        elif args.phase == "report":
            cli.generate_report(top_n=args.top_n)

        elif args.phase == "tailor":
            cli.tailor_resumes(top_n=args.top_n)

        elif args.phase == "full":
            print("Running full pipeline...")
            cli.fetch_jobs(args.platforms, max_jobs=args.max_jobs)
            cli.score_jobs(force=args.force)
            cli.generate_report(top_n=args.top_n)
            cli.tailor_resumes(top_n=args.top_n)

        print("\n[OK] Phase complete")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
