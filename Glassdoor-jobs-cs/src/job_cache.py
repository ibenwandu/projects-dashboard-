"""Save and load scraped jobs as JSON for scoring and resumes."""
from __future__ import annotations

import json
from pathlib import Path

from .glassdoor_scraper import JobDetails
from .link_extractor import job_key_from_url


def job_to_dict(job: JobDetails) -> dict:
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
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [job_to_dict(j) for j in jobs]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_jobs_cache(path: Path) -> list[JobDetails]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [dict_to_job(d) for d in data]


def jobs_by_jk(jobs: list[JobDetails]) -> dict[str, JobDetails]:
    out = {}
    for j in jobs:
        jk = job_key_from_url(j.url)
        if jk:
            out[jk] = j
    return out


def load_reported_job_ids(path: Path | None = None) -> set[str]:
    """Load set of job IDs that have already been included in a report (one ID per line)."""
    from .config import REPORTED_JOB_IDS_PATH
    p = Path(path or REPORTED_JOB_IDS_PATH)
    if not p.exists():
        return set()
    ids = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip().split("#")[0].strip()
        if line:
            ids.add(line)
    return ids


def append_reported_job_ids(job_ids: list[str], path: Path | None = None) -> None:
    """Append job IDs to the reported list so they are excluded from future reports."""
    from .config import REPORTED_JOB_IDS_PATH
    p = Path(path or REPORTED_JOB_IDS_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for jk in job_ids:
            if jk:
                f.write(jk + "\n")
