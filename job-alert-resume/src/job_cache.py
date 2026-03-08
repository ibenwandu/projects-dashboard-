"""Save and load scraped jobs as JSON so the workflow can score and generate resumes without re-scraping."""
from __future__ import annotations

import json
from pathlib import Path

from .indeed_scraper import JobDetails
from .link_extractor import job_key_from_url


def job_to_dict(job: JobDetails) -> dict:
    """Serialize JobDetails to a JSON-serializable dict including jk."""
    jk = job_key_from_url(job.url) or ""
    return {
        "jk": jk,
        "url": job.url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "job_type": job.job_type,
        "description": job.description,
        "skills": list(job.skills),
    }


def dict_to_job(d: dict) -> JobDetails:
    """Deserialize dict back to JobDetails."""
    return JobDetails(
        url=d.get("url", ""),
        title=d.get("title", ""),
        company=d.get("company", ""),
        location=d.get("location", ""),
        salary=d.get("salary", ""),
        job_type=d.get("job_type", ""),
        description=d.get("description", ""),
        skills=list(d.get("skills", [])),
    )


def save_jobs_cache(jobs: list[JobDetails], path: Path) -> Path:
    """Write list of jobs to JSON file. Path typically: output/jobs_cache.json."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [job_to_dict(j) for j in jobs]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_jobs_cache(path: Path) -> list[JobDetails]:
    """Load jobs from JSON file. Returns list of JobDetails."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [dict_to_job(d) for d in data]


def jobs_by_jk(jobs: list[JobDetails]) -> dict[str, JobDetails]:
    """Return a dict mapping job key (jk) to JobDetails. Jobs without jk are skipped."""
    out = {}
    for j in jobs:
        jk = job_key_from_url(j.url)
        if jk:
            out[jk] = j
    return out
